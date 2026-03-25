import numpy as np

from gh_reliability.run import run_noise_sweep


def test_noise_sweep_reports_psd_covariances_and_non_decreasing_trends():
    summary = run_noise_sweep(
        noise_levels=(0.003, 0.008, 0.013),
        repeats=3,
        contour_noise_sigma=0.2,
        contour_samples_per_observation=72,
        seed=19,
        output_dir=None,
    )

    single_run = summary["single_run"]
    for circle_metrics in single_run["circles"]:
        covariance = np.asarray(circle_metrics["covariance"], dtype=np.float64)
        assert covariance.shape == (6, 6)
        assert np.allclose(covariance, covariance.T, atol=1e-10)
        assert np.min(np.linalg.eigvalsh(covariance)) >= -1e-8
        assert "adjusted_camera_center_error_mean" in circle_metrics
        assert "adjusted_rotation_error_mean_degrees" in circle_metrics

    trend_summary = summary["trend_summary"]
    assert trend_summary["camera_center_noise_levels"] == [0.003, 0.008, 0.013]
    for circle_trend in trend_summary["per_circle"]:
        assert circle_trend["nondecreasing_center_axis_99"]
        assert circle_trend["nondecreasing_center_error_mean"]
        assert len(circle_trend["normal_angle_mean_degrees"]) == 3
        assert len(circle_trend["radius_error_mean"]) == 3
        assert len(circle_trend["adjusted_camera_center_error_mean"]) == 3
        assert len(circle_trend["adjusted_rotation_error_mean_degrees"]) == 3


def test_noise_sweep_preserves_requested_circle_and_view_counts():
    summary = run_noise_sweep(
        noise_levels=(0.003, 0.008),
        repeats=2,
        contour_noise_sigma=0.15,
        contour_samples_per_observation=48,
        num_circles=3,
        num_views=4,
        seed=17,
        output_dir=None,
    )

    assert len(summary["single_run"]["circles"]) == 3
    assert summary["single_run"]["scene_metadata"]["num_circles"] == 3
    assert summary["single_run"]["scene_metadata"]["num_views"] == 4
    assert summary["configuration"]["num_circles"] == 3
    assert summary["configuration"]["num_views"] == 4
