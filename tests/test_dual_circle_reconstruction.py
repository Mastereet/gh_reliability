import pytest
import numpy as np

from gh_reliability.ellipse_fit import fit_ellipse_with_covariance
from gh_reliability.evaluate import fit_dual_scene_ellipses, reconstruct_scene_for_validation
from gh_reliability.reconstruct import reconstruct_scene
from gh_reliability.simulation import generate_scene


def _dual_circle_scene():
    return generate_scene(
        num_circles=1,
        num_views=5,
        contour_samples_per_observation=64,
        contour_noise_sigma=0.1,
        camera_center_noise_sigma=0.004,
        seed=123,
        scene_config={
            "scenario": "non_coplanar",
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


def _fit_contour_stack(contour_points: np.ndarray, point_sigma: float):
    contour_points = np.asarray(contour_points, dtype=np.float64)
    return [
        [
            fit_ellipse_with_covariance(contour_points[circle_index, view_index], point_sigma=point_sigma)
            for view_index in range(contour_points.shape[1])
        ]
        for circle_index in range(contour_points.shape[0])
    ]


def test_reconstruct_scene_supports_outer_only_and_dual_joint_modes_on_dual_circle_scene():
    scene = _dual_circle_scene()
    outer_ellipse_results, inner_ellipse_results = fit_dual_scene_ellipses(scene, point_sigma=0.1)

    outer_only_results = reconstruct_scene(
        scene=scene,
        ellipse_results=outer_ellipse_results,
        camera_center_sigma=0.004,
        reconstruction_mode="outer_only",
    )
    dual_joint_results = reconstruct_scene(
        scene=scene,
        ellipse_results=outer_ellipse_results,
        inner_ellipse_results=inner_ellipse_results,
        camera_center_sigma=0.004,
        reconstruction_mode="dual_joint",
    )

    assert len(outer_only_results) == 1
    assert len(dual_joint_results) == 1

    outer_only = outer_only_results[0]
    dual_joint = dual_joint_results[0]

    for reconstruction in (outer_only, dual_joint):
        assert reconstruction.center.shape == (3,)
        assert reconstruction.normal.shape == (3,)
        assert np.isfinite(reconstruction.radius)
        assert np.all(np.isfinite(reconstruction.center))
        assert np.all(np.isfinite(reconstruction.normal))
        assert reconstruction.radius > 0.0

    num_views = scene.observations["contour_points_outer"].shape[1]
    assert outer_only.residual_vector.shape == (5 * num_views,)
    assert dual_joint.residual_vector.shape == (10 * num_views,)
    assert np.linalg.norm(dual_joint.residual_vector[: 5 * num_views]) > 0.0
    assert np.linalg.norm(dual_joint.residual_vector[5 * num_views :]) > 0.0


def test_fit_dual_scene_ellipses_and_validation_wrapper_support_dual_joint_mode():
    scene = _dual_circle_scene()

    outer_ellipse_results, inner_ellipse_results = fit_dual_scene_ellipses(scene, point_sigma=0.1)
    wrapper_results = reconstruct_scene_for_validation(
        scene=scene,
        ellipse_results=outer_ellipse_results,
        inner_ellipse_results=inner_ellipse_results,
        camera_center_sigma=0.004,
        reconstruction_mode="dual_joint",
    )

    assert len(outer_ellipse_results) == 1
    assert len(inner_ellipse_results) == 1
    assert len(outer_ellipse_results[0]) == scene.observations["contour_points_outer"].shape[1]
    assert len(inner_ellipse_results[0]) == scene.observations["contour_points_inner"].shape[1]
    assert wrapper_results[0].residual_vector.shape == (10 * scene.observations["contour_points_outer"].shape[1],)
    assert np.all(np.isfinite(wrapper_results[0].center))
    assert np.all(np.isfinite(wrapper_results[0].normal))
    assert np.isfinite(wrapper_results[0].radius)


def test_reconstruct_scene_dual_joint_rejects_malformed_inner_ellipse_results():
    scene = _dual_circle_scene()
    outer_ellipse_results, inner_ellipse_results = fit_dual_scene_ellipses(scene, point_sigma=0.1)
    malformed_inner_results = [inner_ellipse_results[0][:-1]]

    with pytest.raises(ValueError, match="inner_ellipse_results"):
        reconstruct_scene(
            scene=scene,
            ellipse_results=outer_ellipse_results,
            inner_ellipse_results=malformed_inner_results,
            camera_center_sigma=0.004,
            reconstruction_mode="dual_joint",
        )
