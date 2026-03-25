from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np

from gh_reliability.evaluate import (
    fit_scene_ellipses,
    reconstruct_scene_for_validation,
    save_noise_sweep_plot,
    summarize_noise_trends,
    summarize_reconstruction,
)
from gh_reliability.simulation import generate_scene

COMPARISON_REFINEMENT_MODES = ("algebraic_only", "geometric_only", "algebraic_then_geometric")


def _parse_noise_levels(noise_levels: Iterable[float]) -> list[float]:
    parsed = [float(level) for level in noise_levels]
    if not parsed:
        raise ValueError("at least one camera-center noise level is required")
    if any(level < 0.0 for level in parsed):
        raise ValueError("noise levels must be non-negative")
    return parsed


def _run_single_case(
    *,
    num_circles: int,
    num_views: int,
    camera_center_sigma: float,
    contour_noise_sigma: float,
    contour_samples_per_observation: int,
    seed: int,
    rotation_noise_sigma_deg: float = 0.0,
    refinement_mode: str = "algebraic_then_geometric",
    scene_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scene = generate_scene(
        num_circles=num_circles,
        num_views=num_views,
        contour_samples_per_observation=contour_samples_per_observation,
        contour_noise_sigma=contour_noise_sigma,
        camera_center_noise_sigma=camera_center_sigma,
        rotation_noise_sigma_deg=rotation_noise_sigma_deg,
        seed=seed,
        scene_config=scene_config,
    )
    ellipse_results = fit_scene_ellipses(scene, point_sigma=contour_noise_sigma)
    reconstruction_results = reconstruct_scene_for_validation(
        scene=scene,
        ellipse_results=ellipse_results,
        camera_center_sigma=camera_center_sigma,
        refinement_mode=refinement_mode,
    )
    return summarize_reconstruction(
        scene=scene,
        ellipse_results=ellipse_results,
        reconstruction_results=reconstruction_results,
        camera_center_sigma=camera_center_sigma,
        contour_noise_sigma=contour_noise_sigma,
    )


def _run_mode_sweep(
    *,
    noise_levels: list[float],
    repeats: int,
    contour_noise_sigma: float,
    contour_samples_per_observation: int,
    seed: int,
    num_circles: int,
    num_views: int,
    rotation_noise_sigma_deg: float,
    refinement_mode: str,
    scene_config: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    single_run = _run_single_case(
        num_circles=num_circles,
        num_views=num_views,
        camera_center_sigma=noise_levels[0],
        rotation_noise_sigma_deg=rotation_noise_sigma_deg,
        refinement_mode=refinement_mode,
        contour_noise_sigma=contour_noise_sigma,
        contour_samples_per_observation=contour_samples_per_observation,
        seed=seed,
        scene_config=scene_config,
    )

    repeated_circle_summaries: list[list[list[dict[str, Any]]]] = []
    for camera_center_sigma in noise_levels:
        level_runs: list[list[dict[str, Any]]] = []
        for repeat_index in range(repeats):
            run_seed = seed + repeat_index
            run_summary = _run_single_case(
                num_circles=num_circles,
                num_views=num_views,
                camera_center_sigma=camera_center_sigma,
                rotation_noise_sigma_deg=rotation_noise_sigma_deg,
                refinement_mode=refinement_mode,
                contour_noise_sigma=contour_noise_sigma,
                contour_samples_per_observation=contour_samples_per_observation,
                seed=run_seed,
                scene_config=scene_config,
            )
            level_runs.append(run_summary["circles"])
        repeated_circle_summaries.append(level_runs)

    return single_run, summarize_noise_trends(noise_levels, repeated_circle_summaries)


def _build_pairwise_refinement_delta_summary(
    *,
    reference_mode: str,
    candidate_mode: str,
    reference_single_run: dict[str, Any],
    candidate_single_run: dict[str, Any],
    reference_trend_summary: dict[str, Any],
    candidate_trend_summary: dict[str, Any],
) -> dict[str, Any]:
    single_run_per_circle = []
    for reference_circle, candidate_circle in zip(
        reference_single_run["circles"],
        candidate_single_run["circles"],
        strict=True,
    ):
        single_run_per_circle.append(
            {
                "circle_index": int(reference_circle["circle_index"]),
                "center_error_improvement": float(
                    reference_circle["center_error_norm"] - candidate_circle["center_error_norm"]
                ),
                "normal_angle_improvement_degrees": float(
                    reference_circle["normal_angle_degrees"] - candidate_circle["normal_angle_degrees"]
                ),
                "radius_error_improvement": float(
                    reference_circle["radius_error_abs"] - candidate_circle["radius_error_abs"]
                ),
                "adjusted_pose_center_error_mean_improvement": float(
                    reference_circle["adjusted_camera_center_error_mean"]
                    - candidate_circle["adjusted_camera_center_error_mean"]
                ),
                "adjusted_pose_rotation_error_mean_degrees_improvement": float(
                    reference_circle["adjusted_rotation_error_mean_degrees"]
                    - candidate_circle["adjusted_rotation_error_mean_degrees"]
                ),
            }
        )

    trend_per_circle = []
    for reference_circle, candidate_circle in zip(
        reference_trend_summary["per_circle"],
        candidate_trend_summary["per_circle"],
        strict=True,
    ):
        trend_per_circle.append(
            {
                "circle_index": int(reference_circle["circle_index"]),
                "center_error_mean_improvement": (
                    np.asarray(reference_circle["center_error_mean"], dtype=np.float64)
                    - np.asarray(candidate_circle["center_error_mean"], dtype=np.float64)
                ).tolist(),
                "normal_angle_mean_degrees_improvement": (
                    np.asarray(reference_circle["normal_angle_mean_degrees"], dtype=np.float64)
                    - np.asarray(candidate_circle["normal_angle_mean_degrees"], dtype=np.float64)
                ).tolist(),
                "radius_error_mean_improvement": (
                    np.asarray(reference_circle["radius_error_mean"], dtype=np.float64)
                    - np.asarray(candidate_circle["radius_error_mean"], dtype=np.float64)
                ).tolist(),
                "adjusted_pose_center_error_mean_improvement": (
                    np.asarray(reference_circle["adjusted_camera_center_error_mean"], dtype=np.float64)
                    - np.asarray(candidate_circle["adjusted_camera_center_error_mean"], dtype=np.float64)
                ).tolist(),
                "adjusted_pose_rotation_error_mean_degrees_improvement": (
                    np.asarray(reference_circle["adjusted_rotation_error_mean_degrees"], dtype=np.float64)
                    - np.asarray(candidate_circle["adjusted_rotation_error_mean_degrees"], dtype=np.float64)
                ).tolist(),
            }
        )

    reference_center_error_mean = float(
        np.mean([circle["center_error_norm"] for circle in reference_single_run["circles"]])
    )
    candidate_center_error_mean = float(
        np.mean([circle["center_error_norm"] for circle in candidate_single_run["circles"]])
    )
    reference_pose_center_error_mean = float(
        np.mean([circle["adjusted_camera_center_error_mean"] for circle in reference_single_run["circles"]])
    )
    candidate_pose_center_error_mean = float(
        np.mean([circle["adjusted_camera_center_error_mean"] for circle in candidate_single_run["circles"]])
    )

    return {
        "reference_mode": reference_mode,
        "candidate_mode": candidate_mode,
        "single_run": {
            "center_error_mean_improvement": reference_center_error_mean - candidate_center_error_mean,
            "adjusted_pose_center_error_mean_improvement": (
                reference_pose_center_error_mean - candidate_pose_center_error_mean
            ),
            "per_circle": single_run_per_circle,
        },
        "trend": {
            "camera_center_noise_levels": list(reference_trend_summary["camera_center_noise_levels"]),
            "per_circle": trend_per_circle,
        },
    }


def run_noise_sweep(
    *,
    noise_levels: Iterable[float],
    repeats: int,
    contour_noise_sigma: float,
    contour_samples_per_observation: int,
    seed: int,
    num_circles: int = 2,
    num_views: int = 3,
    rotation_noise_sigma_deg: float = 0.0,
    refinement_mode: str = "algebraic_then_geometric",
    compare_refinement_modes: bool = False,
    output_dir: str | Path | None = None,
    plot_path: str | Path | None = None,
    scene_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the compact GH reliability validation sweep.

    The implementation intentionally keeps the reporting compact: one baseline
    run, repeated noise-level sweeps, and a small set of monotonicity checks
    instead of the full paper tables. That matches the fixed validation tests
    and keeps the output usable from the CLI.
    """

    parsed_noise_levels = _parse_noise_levels(noise_levels)
    if repeats <= 0:
        raise ValueError("repeats must be positive")

    if output_dir is not None:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    single_run, trend_summary = _run_mode_sweep(
        noise_levels=parsed_noise_levels,
        repeats=repeats,
        contour_noise_sigma=contour_noise_sigma,
        contour_samples_per_observation=contour_samples_per_observation,
        seed=seed,
        num_circles=num_circles,
        num_views=num_views,
        rotation_noise_sigma_deg=rotation_noise_sigma_deg,
        refinement_mode=refinement_mode,
        scene_config=scene_config,
    )

    artifacts: dict[str, Any] = {"plot_path": None}
    if plot_path is not None:
        save_noise_sweep_plot(trend_summary, plot_path)
        artifacts["plot_path"] = str(Path(plot_path))

    comparison: dict[str, Any] | None = None
    if compare_refinement_modes:
        single_run_by_mode: dict[str, Any] = {}
        trend_summary_by_mode: dict[str, Any] = {}
        for mode in COMPARISON_REFINEMENT_MODES:
            mode_single_run, mode_trend_summary = _run_mode_sweep(
                noise_levels=parsed_noise_levels,
                repeats=repeats,
                contour_noise_sigma=contour_noise_sigma,
                contour_samples_per_observation=contour_samples_per_observation,
                seed=seed,
                num_circles=num_circles,
                num_views=num_views,
                rotation_noise_sigma_deg=rotation_noise_sigma_deg,
                refinement_mode=mode,
                scene_config=scene_config,
            )
            single_run_by_mode[mode] = mode_single_run
            trend_summary_by_mode[mode] = mode_trend_summary
        reference_mode = "algebraic_only"
        candidate_modes = [mode for mode in COMPARISON_REFINEMENT_MODES if mode != reference_mode]
        comparison = {
            "modes": list(COMPARISON_REFINEMENT_MODES),
            "single_run_by_mode": single_run_by_mode,
            "trend_summary_by_mode": trend_summary_by_mode,
            "delta_summary": {
                "reference_mode": reference_mode,
                "candidate_modes": candidate_modes,
                "by_candidate": {
                    mode: _build_pairwise_refinement_delta_summary(
                        reference_mode=reference_mode,
                        candidate_mode=mode,
                        reference_single_run=single_run_by_mode[reference_mode],
                        candidate_single_run=single_run_by_mode[mode],
                        reference_trend_summary=trend_summary_by_mode[reference_mode],
                        candidate_trend_summary=trend_summary_by_mode[mode],
                    )
                    for mode in candidate_modes
                },
            },
        }

    return {
        "single_run": single_run,
        "trend_summary": trend_summary,
        "comparison": comparison,
        "artifacts": artifacts,
        "configuration": {
            "noise_levels": parsed_noise_levels,
            "repeats": repeats,
            "contour_noise_sigma": float(contour_noise_sigma),
            "contour_samples_per_observation": int(contour_samples_per_observation),
            "num_circles": int(num_circles),
            "num_views": int(num_views),
            "rotation_noise_sigma_deg": float(rotation_noise_sigma_deg),
            "refinement_mode": refinement_mode,
            "compare_refinement_modes": bool(compare_refinement_modes),
            "seed": int(seed),
            "output_dir": str(output_dir) if output_dir is not None else None,
            "scene_config_provided": scene_config is not None,
        },
    }
