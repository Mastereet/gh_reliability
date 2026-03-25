import numpy as np

from gh_reliability.simulation import generate_scene


def test_generate_scene_returns_deterministic_two_circle_three_view_schema():
    first = generate_scene()
    second = generate_scene()

    assert np.array_equal(first.circles["centers"], second.circles["centers"])
    assert np.array_equal(first.circles["normals"], second.circles["normals"])
    assert np.array_equal(first.circles["radii"], second.circles["radii"])
    assert np.array_equal(first.cameras["intrinsics"], second.cameras["intrinsics"])
    assert np.array_equal(first.cameras["rotations"], second.cameras["rotations"])
    assert np.array_equal(first.cameras["camera_centers_true"], second.cameras["camera_centers_true"])
    assert np.array_equal(first.observations["camera_centers_noisy"], second.observations["camera_centers_noisy"])
    assert np.array_equal(first.observations["contour_points"], second.observations["contour_points"])

    assert first.circles["centers"].shape == (2, 3)
    assert first.circles["normals"].shape == (2, 3)
    assert first.circles["radii"].shape == (2,)
    assert first.cameras["intrinsics"].shape == (3, 3)
    assert first.cameras["rotations"].shape == (3, 3, 3)
    assert first.cameras["camera_centers_true"].shape == (3, 3)
    assert first.observations["camera_centers_noisy"].shape == (3, 3)
    assert first.observations["contour_points"].shape == (2, 3, 64, 2)
    assert first.observations["projected_centers"].shape == (2, 3, 2)

    assert first.metadata["num_circles"] == 2
    assert first.metadata["num_views"] == 3
    assert first.metadata["contour_samples_per_observation"] == 64
    assert first.metadata["fixed_intrinsics"] is True
    assert first.metadata["fixed_rotations"] is True
    assert first.metadata["camera_noise_model"] == "gaussian_camera_center_noise"
    assert first.metadata["contour_noise_model"] == "gaussian_image_noise"
    assert "local_simulation_choices" in first.metadata


def test_generate_scene_supports_requested_circle_and_view_counts():
    scene = generate_scene(
        num_circles=4,
        num_views=5,
        contour_samples_per_observation=40,
        seed=7,
    )

    assert scene.circles["centers"].shape == (4, 3)
    assert scene.circles["normals"].shape == (4, 3)
    assert scene.circles["radii"].shape == (4,)
    assert scene.cameras["rotations"].shape == (5, 3, 3)
    assert scene.cameras["camera_centers_true"].shape == (5, 3)
    assert scene.observations["camera_centers_noisy"].shape == (5, 3)
    assert scene.observations["contour_points"].shape == (4, 5, 40, 2)
    assert scene.observations["projected_centers"].shape == (4, 5, 2)
    assert scene.metadata["num_circles"] == 4
    assert scene.metadata["num_views"] == 5


def test_generate_scene_rejects_too_few_views_for_stable_reconstruction():
    try:
        generate_scene(num_views=2)
    except ValueError as exc:
        assert "num_views" in str(exc)
    else:  # pragma: no cover - red/green assertion
        raise AssertionError("expected ValueError for num_views < 3")


def test_generate_scene_accepts_explicit_pose_config_and_emits_pose_covariances():
    scene = generate_scene(
        contour_samples_per_observation=32,
        contour_noise_sigma=0.1,
        camera_center_noise_sigma=0.004,
        rotation_noise_sigma_deg=0.5,
        seed=13,
        scene_config={
            "circles": [
                {"center": [-0.3, 0.1, 4.5], "normal": [0.1, -0.1, 0.99], "radius": 0.6},
                {"center": [0.7, -0.15, 5.1], "normal": [-0.15, 0.05, 0.99], "radius": 0.7},
            ],
            "intrinsics": [[850.0, 0.0, 300.0], [0.0, 840.0, 220.0], [0.0, 0.0, 1.0]],
            "cameras": [
                {
                    "center": [0.0, 0.0, 0.0],
                    "rotation": [[-1.0, 0.0, 0.0], [0.0, -0.2, 0.98], [0.0, 0.98, 0.2]],
                    "center_perturbation": [0.01, 0.0, 0.0],
                    "rotation_perturbation_rotvec": [0.0, 0.02, 0.0],
                },
                {
                    "center": [0.9, -0.2, 0.1],
                    "rotation": [[-0.95, 0.05, 0.3], [0.0, -0.98, 0.2], [0.31, 0.19, 0.93]],
                },
                {
                    "center": [-0.8, 0.3, -0.1],
                    "rotation": [[-0.9, -0.1, -0.42], [0.0, -0.97, 0.24], [-0.44, 0.22, 0.87]],
                },
            ],
        },
    )

    assert scene.cameras["camera_centers_true"].shape == (3, 3)
    assert scene.cameras["rotations_true"].shape == (3, 3, 3)
    assert scene.cameras["rotations"].shape == (3, 3, 3)
    assert scene.observations["pose_covariances"].shape == (3, 6, 6)
    assert scene.metadata["fixed_rotations"] is False
    assert scene.metadata["rotation_noise_model"] == "gaussian_axis_angle_noise"
    assert np.allclose(scene.observations["pose_covariances"][:, :3, :3], (0.004**2) * np.eye(3), atol=1e-12)
    assert np.min(np.linalg.eigvalsh(scene.observations["pose_covariances"][0])) >= -1e-12
