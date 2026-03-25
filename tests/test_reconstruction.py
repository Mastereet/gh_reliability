import numpy as np
from scipy.spatial.transform import Rotation

from gh_reliability.ellipse_fit import fit_ellipse_with_covariance
from gh_reliability.reconstruct import reconstruct_scene
from gh_reliability.simulation import generate_scene


def _fit_scene_ellipses(scene, point_sigma):
    contour_points = scene.observations["contour_points"]
    return [
        [
            fit_ellipse_with_covariance(contour_points[circle_index, view_index], point_sigma=point_sigma)
            for view_index in range(contour_points.shape[1])
        ]
        for circle_index in range(contour_points.shape[0])
    ]


def _normal_angle_degrees(estimate, truth):
    estimate = estimate / np.linalg.norm(estimate)
    truth = truth / np.linalg.norm(truth)
    cosine = np.clip(abs(np.dot(estimate, truth)), -1.0, 1.0)
    return np.degrees(np.arccos(cosine))


def test_reconstruct_scene_returns_finite_circle_parameters_and_covariance():
    scene = generate_scene(
        contour_samples_per_observation=80,
        contour_noise_sigma=0.2,
        camera_center_noise_sigma=0.005,
        seed=11,
    )
    ellipse_results = _fit_scene_ellipses(scene, point_sigma=0.2)

    reconstruction_results = reconstruct_scene(
        scene=scene,
        ellipse_results=ellipse_results,
        camera_center_sigma=0.005,
    )

    assert len(reconstruction_results) == 2

    for circle_index, reconstruction in enumerate(reconstruction_results):
        true_center = scene.circles["centers"][circle_index]
        true_normal = scene.circles["normals"][circle_index]
        true_radius = scene.circles["radii"][circle_index]

        assert reconstruction.converged
        assert reconstruction.center.shape == (3,)
        assert reconstruction.scaled_normal.shape == (3,)
        assert reconstruction.covariance.shape == (6, 6)
        assert reconstruction.adjusted_camera_centers.shape == (3, 3)
        assert reconstruction.adjusted_rotation_rotvecs.shape == (3, 3)
        assert reconstruction.adjusted_dual_conics.shape == (3, 5)
        assert np.all(np.isfinite(reconstruction.center))
        assert np.all(np.isfinite(reconstruction.scaled_normal))
        assert np.all(np.isfinite(reconstruction.covariance))
        assert np.min(np.linalg.eigvalsh(reconstruction.covariance)) >= -1e-8
        assert np.linalg.norm(reconstruction.center - true_center) < 0.35
        assert abs(reconstruction.radius - true_radius) < 0.25
        assert _normal_angle_degrees(reconstruction.normal, true_normal) < 20.0


def test_reconstruct_scene_supports_more_circles_and_views():
    scene = generate_scene(
        num_circles=3,
        num_views=4,
        contour_samples_per_observation=72,
        contour_noise_sigma=0.15,
        camera_center_noise_sigma=0.004,
        seed=5,
    )
    ellipse_results = _fit_scene_ellipses(scene, point_sigma=0.15)

    reconstruction_results = reconstruct_scene(
        scene=scene,
        ellipse_results=ellipse_results,
        camera_center_sigma=0.004,
    )

    assert len(reconstruction_results) == 3
    for reconstruction in reconstruction_results:
        assert reconstruction.converged
        assert reconstruction.adjusted_camera_centers.shape == (4, 3)
        assert reconstruction.adjusted_rotation_rotvecs.shape == (4, 3)
        assert reconstruction.adjusted_dual_conics.shape == (4, 5)
        assert reconstruction.covariance.shape == (6, 6)
        assert np.min(np.linalg.eigvalsh(reconstruction.covariance)) >= -1e-8


def test_reconstruct_scene_uses_shared_global_pose_across_circles():
    scene = generate_scene(
        num_circles=2,
        num_views=10,
        contour_samples_per_observation=48,
        contour_noise_sigma=0.12,
        camera_center_noise_sigma=0.003,
        rotation_noise_sigma_deg=0.35,
        seed=31,
    )
    ellipse_results = _fit_scene_ellipses(scene, point_sigma=0.12)

    reconstruction_results = reconstruct_scene(
        scene=scene,
        ellipse_results=ellipse_results,
        camera_center_sigma=0.003,
    )

    reference_centers = reconstruction_results[0].adjusted_camera_centers
    reference_rotations = reconstruction_results[0].adjusted_rotation_rotvecs
    for reconstruction in reconstruction_results[1:]:
        assert np.allclose(reconstruction.adjusted_camera_centers, reference_centers, atol=1e-8)
        assert np.allclose(reconstruction.adjusted_rotation_rotvecs, reference_rotations, atol=1e-8)


def test_reconstruct_scene_shared_pose_stays_close_to_true_pose_under_small_noise():
    scene = generate_scene(
        num_circles=2,
        num_views=10,
        contour_samples_per_observation=48,
        contour_noise_sigma=0.12,
        camera_center_noise_sigma=0.003,
        rotation_noise_sigma_deg=0.35,
        seed=31,
    )
    ellipse_results = _fit_scene_ellipses(scene, point_sigma=0.12)

    reconstruction_results = reconstruct_scene(
        scene=scene,
        ellipse_results=ellipse_results,
        camera_center_sigma=0.003,
    )

    truth_centers = scene.cameras["camera_centers_true"]
    truth_rotations = scene.cameras["rotations_true"]
    adjusted_centers = reconstruction_results[0].adjusted_camera_centers
    adjusted_rotations = reconstruction_results[0].adjusted_rotation_rotvecs
    adjusted_rotation_matrices = Rotation.from_rotvec(adjusted_rotations).as_matrix()

    center_error_mean = float(np.mean(np.linalg.norm(adjusted_centers - truth_centers, axis=1)))
    rotation_error_mean_degrees = float(
        np.mean(
            [
                np.degrees((Rotation.from_matrix(estimated @ truth.T)).magnitude())
                for estimated, truth in zip(adjusted_rotation_matrices, truth_rotations, strict=True)
            ]
        )
    )

    assert center_error_mean < 0.05
    assert rotation_error_mean_degrees < 1.0
    for circle_index, reconstruction in enumerate(reconstruction_results):
        assert np.linalg.norm(reconstruction.center - scene.circles["centers"][circle_index]) < 0.2


def test_geometric_refinement_reduces_center_error_against_algebraic_only():
    scene = generate_scene(
        num_circles=2,
        num_views=10,
        contour_samples_per_observation=48,
        contour_noise_sigma=0.12,
        camera_center_noise_sigma=0.003,
        rotation_noise_sigma_deg=0.35,
        seed=31,
    )
    ellipse_results = _fit_scene_ellipses(scene, point_sigma=0.12)

    algebraic_results = reconstruct_scene(
        scene=scene,
        ellipse_results=ellipse_results,
        camera_center_sigma=0.003,
        refinement_mode="algebraic_only",
    )
    refined_results = reconstruct_scene(
        scene=scene,
        ellipse_results=ellipse_results,
        camera_center_sigma=0.003,
        refinement_mode="algebraic_then_geometric",
    )
    geometric_only_results = reconstruct_scene(
        scene=scene,
        ellipse_results=ellipse_results,
        camera_center_sigma=0.003,
        refinement_mode="geometric_only",
    )

    truth_centers = scene.circles["centers"]
    algebraic_center_error_mean = float(
        np.mean(
            [
                np.linalg.norm(reconstruction.center - truth_center)
                for reconstruction, truth_center in zip(algebraic_results, truth_centers, strict=True)
            ]
        )
    )
    refined_center_error_mean = float(
        np.mean(
            [
                np.linalg.norm(reconstruction.center - truth_center)
                for reconstruction, truth_center in zip(refined_results, truth_centers, strict=True)
            ]
        )
    )
    geometric_only_center_error_mean = float(
        np.mean(
            [
                np.linalg.norm(reconstruction.center - truth_center)
                for reconstruction, truth_center in zip(geometric_only_results, truth_centers, strict=True)
            ]
        )
    )

    assert refined_center_error_mean < algebraic_center_error_mean
    assert refined_center_error_mean < geometric_only_center_error_mean
