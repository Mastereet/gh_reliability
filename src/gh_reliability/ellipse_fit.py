from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EllipseFitResult:
    point_conic_coefficients: np.ndarray
    point_conic_matrix: np.ndarray
    point_conic_covariance: np.ndarray
    dual_conic_vec5: np.ndarray
    dual_conic_matrix: np.ndarray
    dual_conic_covariance: np.ndarray
    normalization_transform: np.ndarray
    normalized_point_conic_coefficients: np.ndarray
    normalized_point_conic_covariance: np.ndarray


def _coefficients_to_matrix(coefficients: np.ndarray) -> np.ndarray:
    a, b, c, d, e, f = np.asarray(coefficients, dtype=np.float64)
    return np.array([[a, b, d], [b, c, e], [d, e, f]], dtype=np.float64)


def _matrix_to_coefficients(conic: np.ndarray) -> np.ndarray:
    return np.array(
        [conic[0, 0], conic[0, 1], conic[1, 1], conic[0, 2], conic[1, 2], conic[2, 2]],
        dtype=np.float64,
    )


def _normalize_conic_coefficients(coefficients: np.ndarray) -> np.ndarray:
    coefficients = np.asarray(coefficients, dtype=np.float64)
    scale = coefficients[0] * coefficients[2] - coefficients[1] ** 2
    if scale <= 0.0:
        raise ValueError("fitted conic is not an ellipse")
    normalized = coefficients / np.sqrt(scale)
    if normalized[0] < 0.0:
        normalized = -normalized
    return normalized


def _normalization_transform(points: np.ndarray) -> np.ndarray:
    center = points.mean(axis=0)
    centered = points - center
    rms_radius = np.sqrt(np.mean(np.sum(centered**2, axis=1)))
    if rms_radius <= 0.0:
        raise ValueError("point cloud must not collapse to a single location")
    scale = np.sqrt(2.0) / rms_radius
    return np.array(
        [
            [scale, 0.0, -scale * center[0]],
            [0.0, scale, -scale * center[1]],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def _fit_direct_normalized(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    transform = _normalization_transform(points)
    homogeneous = np.column_stack([points, np.ones(len(points), dtype=np.float64)])
    normalized_points = (transform @ homogeneous.T).T
    x = normalized_points[:, 0]
    y = normalized_points[:, 1]

    design_quadratic = np.column_stack([x**2, x * y, y**2])
    design_linear = np.column_stack([x, y, np.ones_like(x)])
    scatter_qq = design_quadratic.T @ design_quadratic
    scatter_qr = design_quadratic.T @ design_linear
    scatter_rr = design_linear.T @ design_linear

    reduced = scatter_qq - scatter_qr @ np.linalg.solve(scatter_rr, scatter_qr.T)
    constraint = np.array([[0.0, 0.0, 2.0], [0.0, -1.0, 0.0], [2.0, 0.0, 0.0]], dtype=np.float64)

    _, eigenvectors = np.linalg.eig(np.linalg.solve(constraint, reduced))
    quadratic = None
    for vector in eigenvectors.T:
        if np.max(np.abs(np.imag(vector))) > 1e-9:
            continue
        candidate = np.real(vector)
        if 4.0 * candidate[0] * candidate[2] - candidate[1] ** 2 > 0.0:
            quadratic = candidate
            break
    if quadratic is None:
        raise ValueError("unable to fit a valid ellipse")

    linear = -np.linalg.solve(scatter_rr, scatter_qr.T @ quadratic)
    standard_coefficients = np.concatenate([quadratic, linear])
    gh_coefficients = np.array(
        [
            standard_coefficients[0],
            0.5 * standard_coefficients[1],
            standard_coefficients[2],
            0.5 * standard_coefficients[3],
            0.5 * standard_coefficients[4],
            standard_coefficients[5],
        ],
        dtype=np.float64,
    )
    gh_coefficients = _normalize_conic_coefficients(gh_coefficients)
    return gh_coefficients, transform


def _denormalize_coefficients(normalized_coefficients: np.ndarray, transform: np.ndarray) -> np.ndarray:
    conic_normalized = _coefficients_to_matrix(normalized_coefficients)
    conic = transform.T @ conic_normalized @ transform
    return _normalize_conic_coefficients(_matrix_to_coefficients(conic))


def _finite_difference_jacobian(function, x0: np.ndarray, step: float = 1e-6) -> np.ndarray:
    x0 = np.asarray(x0, dtype=np.float64)
    baseline = np.asarray(function(x0), dtype=np.float64)
    jacobian = np.empty((baseline.size, x0.size), dtype=np.float64)
    for index in range(x0.size):
        delta = np.zeros_like(x0)
        delta[index] = step
        forward = np.asarray(function(x0 + delta), dtype=np.float64)
        backward = np.asarray(function(x0 - delta), dtype=np.float64)
        jacobian[:, index] = (forward - backward) / (2.0 * step)
    return jacobian


def _project_psd(matrix: np.ndarray) -> np.ndarray:
    matrix = 0.5 * (matrix + matrix.T)
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    eigenvalues[eigenvalues < 0.0] = 0.0
    return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T


def _point_conic_covariance(points: np.ndarray, coefficients: np.ndarray, point_sigma: float) -> np.ndarray:
    x = points[:, 0]
    y = points[:, 1]
    design = np.column_stack([x**2, 2.0 * x * y, y**2, 2.0 * x, 2.0 * y, np.ones_like(x)])
    constraint_gradient = np.array(
        [[coefficients[2], -2.0 * coefficients[1], coefficients[0], 0.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    augmented = np.vstack([design, constraint_gradient])
    covariance = (point_sigma**2) * np.linalg.pinv(augmented.T @ augmented)
    return _project_psd(covariance)


def _dual_conic_vector(coefficients: np.ndarray) -> np.ndarray:
    dual_matrix = np.linalg.inv(_coefficients_to_matrix(coefficients))
    dual_matrix = dual_matrix / dual_matrix[2, 2]
    return np.array(
        [dual_matrix[0, 0], dual_matrix[0, 1], dual_matrix[1, 1], dual_matrix[0, 2], dual_matrix[1, 2]],
        dtype=np.float64,
    )


def fit_ellipse_with_covariance(points: np.ndarray, point_sigma: float = 1.0) -> EllipseFitResult:
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points must have shape (N, 2)")
    if len(points) < 6:
        raise ValueError("at least six points are required to fit an ellipse")
    if point_sigma <= 0.0:
        raise ValueError("point_sigma must be positive")

    normalized_coefficients, transform = _fit_direct_normalized(points)
    denormalized_coefficients = _denormalize_coefficients(normalized_coefficients, transform)
    normalized_points = (transform @ np.column_stack([points, np.ones(len(points), dtype=np.float64)]).T).T[:, :2]
    normalized_point_sigma = abs(transform[0, 0]) * point_sigma

    covariance_normalized = _point_conic_covariance(
        points=normalized_points,
        coefficients=normalized_coefficients,
        point_sigma=normalized_point_sigma,
    )
    denormalization_jacobian = _finite_difference_jacobian(
        lambda coefficient_vector: _denormalize_coefficients(coefficient_vector, transform),
        normalized_coefficients,
    )
    point_covariance = _project_psd(denormalization_jacobian @ covariance_normalized @ denormalization_jacobian.T)

    dual_jacobian = _finite_difference_jacobian(_dual_conic_vector, denormalized_coefficients)
    dual_covariance = _project_psd(dual_jacobian @ point_covariance @ dual_jacobian.T)

    point_conic_matrix = _coefficients_to_matrix(denormalized_coefficients)
    dual_conic_matrix = np.linalg.inv(point_conic_matrix)
    dual_conic_matrix = dual_conic_matrix / dual_conic_matrix[2, 2]

    return EllipseFitResult(
        point_conic_coefficients=denormalized_coefficients,
        point_conic_matrix=point_conic_matrix,
        point_conic_covariance=point_covariance,
        dual_conic_vec5=_dual_conic_vector(denormalized_coefficients),
        dual_conic_matrix=dual_conic_matrix,
        dual_conic_covariance=dual_covariance,
        normalization_transform=transform,
        normalized_point_conic_coefficients=normalized_coefficients,
        normalized_point_conic_covariance=covariance_normalized,
    )
