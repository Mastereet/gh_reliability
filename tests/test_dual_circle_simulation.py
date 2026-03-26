import numpy as np

from gh_reliability.simulation import generate_scene


def _dual_circle_scene(preset: str):
    return generate_scene(
        num_circles=1,
        num_views=5,
        contour_samples_per_observation=48,
        seed=123,
        scene_config={
            "scenario": preset,
            "circles": [
                {
                    "center": [0.15, -0.08, 4.9],
                    "normal": [0.04, -0.03, 0.9987],
                    "outer_radius": 0.9,
                    "inner_radius": 0.58,
                }
            ],
        },
    )


def test_generate_scene_supports_dual_circle_presets_and_contours():
    near = _dual_circle_scene("near_coplanar")
    non_coplanar = _dual_circle_scene("non_coplanar")

    assert np.array_equal(near.circles["radii"], near.circles["outer_radii"])
    assert np.array_equal(near.circles["outer_radii"], np.array([0.9]))
    assert np.array_equal(near.circles["inner_radii"], np.array([0.58]))
    assert near.observations["contour_points_outer"].shape == (1, 5, 48, 2)
    assert near.observations["contour_points_inner"].shape == (1, 5, 48, 2)
    assert np.array_equal(near.observations["contour_points"], near.observations["contour_points_outer"])

    assert non_coplanar.observations["contour_points_outer"].shape == (1, 5, 48, 2)
    assert non_coplanar.observations["contour_points_inner"].shape == (1, 5, 48, 2)
    expected_near_z = 0.02 * np.sin(np.array([0.0, 4.0 * np.pi / 5.0, 8.0 * np.pi / 5.0, 12.0 * np.pi / 5.0, 16.0 * np.pi / 5.0]))
    expected_non_coplanar_z = 0.34 + 0.24 * np.sin(
        np.array([0.0, 4.0 * np.pi / 5.0, 8.0 * np.pi / 5.0, 12.0 * np.pi / 5.0, 16.0 * np.pi / 5.0])
    )
    assert np.allclose(near.cameras["camera_centers_true"][:, 2], expected_near_z, atol=1e-12)
    assert np.allclose(non_coplanar.cameras["camera_centers_true"][:, 2], expected_non_coplanar_z, atol=1e-12)
    assert np.ptp(non_coplanar.cameras["camera_centers_true"][:, 2]) > np.ptp(near.cameras["camera_centers_true"][:, 2])


def test_generate_scene_rejects_unknown_scenario_preset():
    try:
        generate_scene(scene_config={"scenario": "unknown_preset"})
    except ValueError as exc:
        assert "scenario" in str(exc)
    else:  # pragma: no cover - red/green assertion
        raise AssertionError("expected ValueError for unknown scenario preset")
