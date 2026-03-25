import numpy as np

from gh_reliability.ellipse_fit import fit_ellipse_with_covariance


def _conic_from_center_axes_angle(center, axes, angle_radians):
    cos_theta = np.cos(angle_radians)
    sin_theta = np.sin(angle_radians)
    rotation = np.array(
        [[cos_theta, -sin_theta, 0.0], [sin_theta, cos_theta, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    translation = np.array(
        [[1.0, 0.0, center[0]], [0.0, 1.0, center[1]], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    canonical = np.diag([1.0 / (axes[0] ** 2), 1.0 / (axes[1] ** 2), -1.0])
    transform = translation @ rotation
    return np.linalg.inv(transform).T @ canonical @ np.linalg.inv(transform)


def _sample_ellipse_points(center, axes, angle_radians, num_points):
    theta = np.linspace(0.0, 2.0 * np.pi, num_points, endpoint=False)
    unit = np.stack([axes[0] * np.cos(theta), axes[1] * np.sin(theta)], axis=1)
    cos_theta = np.cos(angle_radians)
    sin_theta = np.sin(angle_radians)
    rotation = np.array([[cos_theta, -sin_theta], [sin_theta, cos_theta]], dtype=np.float64)
    return unit @ rotation.T + np.asarray(center, dtype=np.float64)


def _conic_matrix_from_coefficients(coefficients):
    a, b, c, d, e, f = coefficients
    return np.array([[a, b, d], [b, c, e], [d, e, f]], dtype=np.float64)


def _normalize_point_conic(conic):
    scale = conic[0, 0] * conic[1, 1] - conic[0, 1] ** 2
    return conic / np.sqrt(scale)


def test_fit_ellipse_returns_finite_normalized_coefficients_close_to_target():
    points = _sample_ellipse_points(center=(0.2, -0.1), axes=(1.4, 0.8), angle_radians=0.45, num_points=96)
    points += np.array([0.01, -0.015])

    result = fit_ellipse_with_covariance(points, point_sigma=0.01)

    fitted_conic = _conic_matrix_from_coefficients(result.point_conic_coefficients)
    target_conic = _normalize_point_conic(
        _conic_from_center_axes_angle(center=(0.21, -0.115), axes=(1.4, 0.8), angle_radians=0.45)
    )

    assert np.all(np.isfinite(result.point_conic_coefficients))
    assert np.all(np.isfinite(result.dual_conic_vec5))
    assert np.isclose(
        result.point_conic_coefficients[0] * result.point_conic_coefficients[2]
        - result.point_conic_coefficients[1] ** 2,
        1.0,
        atol=1e-3,
    )
    assert np.allclose(_normalize_point_conic(fitted_conic), target_conic, atol=6e-2)


def test_fit_ellipse_returns_symmetric_positive_semidefinite_covariances():
    points = _sample_ellipse_points(center=(-0.3, 0.25), axes=(1.1, 0.6), angle_radians=-0.35, num_points=128)
    noise = np.column_stack(
        [
            0.01 * np.sin(np.linspace(0.0, 2.0 * np.pi, len(points), endpoint=False)),
            0.01 * np.cos(np.linspace(0.0, 2.0 * np.pi, len(points), endpoint=False)),
        ]
    )

    result = fit_ellipse_with_covariance(points + noise, point_sigma=0.015)

    assert result.point_conic_covariance.shape == (6, 6)
    assert result.dual_conic_covariance.shape == (5, 5)
    assert np.allclose(result.point_conic_covariance, result.point_conic_covariance.T, atol=1e-10)
    assert np.allclose(result.dual_conic_covariance, result.dual_conic_covariance.T, atol=1e-10)
    assert np.min(np.linalg.eigvalsh(result.point_conic_covariance)) >= -1e-9
    assert np.min(np.linalg.eigvalsh(result.dual_conic_covariance)) >= -1e-9


def test_fit_ellipse_covariance_is_consistent_under_uniform_scene_scaling():
    points = _sample_ellipse_points(center=(0.15, -0.25), axes=(1.25, 0.7), angle_radians=0.3, num_points=96)

    baseline = fit_ellipse_with_covariance(points, point_sigma=0.01)
    scaled = fit_ellipse_with_covariance(points * 20.0, point_sigma=0.2)

    assert np.allclose(
        baseline.normalized_point_conic_coefficients,
        scaled.normalized_point_conic_coefficients,
        atol=1e-3,
    )
    assert np.allclose(
        baseline.normalized_point_conic_covariance,
        scaled.normalized_point_conic_covariance,
        rtol=1e-2,
        atol=1e-6,
    )
