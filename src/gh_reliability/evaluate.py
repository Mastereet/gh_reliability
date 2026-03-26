from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.spatial.transform import Rotation

from gh_reliability.ellipse_fit import EllipseFitResult, fit_ellipse_with_covariance
from gh_reliability.reconstruct import reconstruct_scene
from gh_reliability.simulation import SceneData


CHI2_99_DOFS_3 = 11.344866730144373
CHI2_99_DOFS_6 = 16.811893829770927


def _symmetrize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float64)
    return 0.5 * (matrix + matrix.T)


def _project_psd(matrix: np.ndarray) -> np.ndarray:
    matrix = _symmetrize(matrix)
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    eigenvalues[eigenvalues < 0.0] = 0.0
    return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float64)
    norm = np.linalg.norm(vector)
    if norm <= 0.0:
        raise ValueError("vector norm must be positive")
    return vector / norm


def _largest_axis_99(covariance: np.ndarray, dof: int) -> float:
    covariance = _symmetrize(covariance)
    eigenvalues = np.linalg.eigvalsh(covariance)
    largest = float(np.max(np.maximum(eigenvalues, 0.0)))
    if largest == 0.0:
        return 0.0
    chi2 = CHI2_99_DOFS_3 if dof == 3 else CHI2_99_DOFS_6
    return float(np.sqrt(chi2 * largest))


def _angle_degrees(first: np.ndarray, second: np.ndarray) -> float:
    first = _normalize_vector(first)
    second = _normalize_vector(second)
    cosine = float(np.clip(abs(np.dot(first, second)), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def _residual_norm(residual_vector: Any) -> float:
    if residual_vector is None:
        return 0.0
    array = np.asarray(residual_vector, dtype=np.float64)
    return float(np.linalg.norm(array))


def _rotation_error_degrees(first: np.ndarray, second: np.ndarray) -> float:
    first = np.asarray(first, dtype=np.float64)
    second = np.asarray(second, dtype=np.float64)
    relative = Rotation.from_matrix(first @ second.T)
    return float(np.degrees(relative.magnitude()))


def _fit_contour_stack(contour_points: np.ndarray, point_sigma: float) -> list[list[EllipseFitResult]]:
    contour_points = np.asarray(contour_points, dtype=np.float64)
    return [
        [
            fit_ellipse_with_covariance(contour_points[circle_index, view_index], point_sigma=point_sigma)
            for view_index in range(contour_points.shape[1])
        ]
        for circle_index in range(contour_points.shape[0])
    ]


def fit_scene_ellipses(scene: SceneData, point_sigma: float) -> list[list[EllipseFitResult]]:
    return _fit_contour_stack(scene.observations["contour_points"], point_sigma=point_sigma)


def fit_dual_scene_ellipses(
    scene: SceneData,
    point_sigma: float,
) -> tuple[list[list[EllipseFitResult]], list[list[EllipseFitResult]]]:
    return (
        _fit_contour_stack(scene.observations["contour_points_outer"], point_sigma=point_sigma),
        _fit_contour_stack(scene.observations["contour_points_inner"], point_sigma=point_sigma),
    )


def reconstruct_scene_for_validation(
    scene: SceneData,
    ellipse_results: list[list[EllipseFitResult]],
    camera_center_sigma: float,
    refinement_mode: str = "algebraic_then_geometric",
    reconstruction_mode: str = "outer_only",
    inner_ellipse_results: list[list[EllipseFitResult]] | None = None,
) -> list[Any]:
    """Run the real 3D reconstruction path used by the validation prototype."""
    return reconstruct_scene(
        scene=scene,
        ellipse_results=ellipse_results,
        camera_center_sigma=camera_center_sigma,
        refinement_mode=refinement_mode,
        reconstruction_mode=reconstruction_mode,
        inner_ellipse_results=inner_ellipse_results,
    )


def summarize_reconstruction(
    scene: SceneData,
    ellipse_results: list[list[EllipseFitResult]],
    reconstruction_results: list[Any],
    camera_center_sigma: float,
    contour_noise_sigma: float,
) -> dict[str, Any]:
    circles: list[dict[str, Any]] = []
    truth_centers = np.asarray(scene.circles["centers"], dtype=np.float64)
    truth_normals = np.asarray(scene.circles["normals"], dtype=np.float64)
    truth_radii = np.asarray(scene.circles["radii"], dtype=np.float64)
    truth_camera_centers = np.asarray(scene.cameras["camera_centers_true"], dtype=np.float64)
    truth_rotations = np.asarray(
        scene.cameras.get("rotations_true", scene.cameras["rotations"]),
        dtype=np.float64,
    )
    pose_covariances = np.asarray(scene.observations.get("pose_covariances", []), dtype=np.float64)

    for circle_index, reconstruction in enumerate(reconstruction_results):
        covariance = _symmetrize(np.asarray(reconstruction.covariance, dtype=np.float64))
        center = np.asarray(reconstruction.center, dtype=np.float64)
        normal = np.asarray(reconstruction.normal, dtype=np.float64)
        radius = float(reconstruction.radius)
        adjusted_camera_centers = np.asarray(reconstruction.adjusted_camera_centers, dtype=np.float64)
        adjusted_rotation_rotvecs = np.asarray(reconstruction.adjusted_rotation_rotvecs, dtype=np.float64)
        adjusted_rotations = Rotation.from_rotvec(adjusted_rotation_rotvecs).as_matrix()
        adjusted_camera_center_errors = np.linalg.norm(adjusted_camera_centers - truth_camera_centers, axis=1)
        adjusted_rotation_error_degrees = [
            _rotation_error_degrees(adjusted_rotation, truth_rotation)
            for adjusted_rotation, truth_rotation in zip(adjusted_rotations, truth_rotations, strict=True)
        ]
        circles.append(
            {
                "circle_index": circle_index,
                "center": center.tolist(),
                "scaled_normal": np.asarray(reconstruction.scaled_normal, dtype=np.float64).tolist(),
                "normal": normal.tolist(),
                "radius": radius,
                "covariance": covariance.tolist(),
                "center_error_norm": float(np.linalg.norm(center - truth_centers[circle_index])),
                "normal_angle_degrees": _angle_degrees(normal, truth_normals[circle_index]),
                "radius_error_abs": float(abs(radius - float(truth_radii[circle_index]))),
                "center_axis_99": _largest_axis_99(covariance[:3, :3], dof=3),
                "state_axis_99": _largest_axis_99(covariance, dof=6),
                "converged": bool(reconstruction.converged),
                "iterations": int(reconstruction.iterations),
                "residual_norm": _residual_norm(reconstruction.residual_vector),
                "adjusted_camera_centers": adjusted_camera_centers.tolist(),
                "adjusted_rotation_rotvecs": adjusted_rotation_rotvecs.tolist(),
                "adjusted_rotations": np.asarray(adjusted_rotations, dtype=np.float64).tolist(),
                "adjusted_camera_center_errors": adjusted_camera_center_errors.tolist(),
                "adjusted_camera_center_error_mean": float(np.mean(adjusted_camera_center_errors)),
                "adjusted_rotation_error_degrees": adjusted_rotation_error_degrees,
                "adjusted_rotation_error_mean_degrees": float(np.mean(adjusted_rotation_error_degrees)),
                "adjusted_dual_conics": np.asarray(reconstruction.adjusted_dual_conics, dtype=np.float64).tolist(),
            }
        )

    return {
        "camera_center_sigma": float(camera_center_sigma),
        "contour_noise_sigma": float(contour_noise_sigma),
        "camera_centers_noisy": np.asarray(scene.observations["camera_centers_noisy"], dtype=np.float64).tolist(),
        "camera_centers_true": np.asarray(scene.cameras["camera_centers_true"], dtype=np.float64).tolist(),
        "rotations": np.asarray(scene.cameras["rotations"], dtype=np.float64).tolist(),
        "rotations_true": np.asarray(
            scene.cameras.get("rotations_true", scene.cameras["rotations"]),
            dtype=np.float64,
        ).tolist(),
        "pose_covariances": pose_covariances.tolist(),
        "scene_metadata": dict(scene.metadata),
        "circles": circles,
    }


def _is_non_decreasing(values: Iterable[float], tolerance: float = 1e-9) -> bool:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size < 2:
        return True
    return bool(np.all(np.diff(array) >= -tolerance))


def _monotone_envelope(values: Iterable[float]) -> list[float]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        return []
    return np.maximum.accumulate(array).astype(np.float64).tolist()


def summarize_noise_trends(
    noise_levels: Iterable[float],
    repeated_circle_summaries: list[list[list[dict[str, Any]]]],
) -> dict[str, Any]:
    noise_levels = [float(level) for level in noise_levels]
    if not repeated_circle_summaries:
        return {
            "camera_center_noise_levels": noise_levels,
            "repeat_count": 0,
            "per_circle": [],
        }

    num_circles = len(repeated_circle_summaries[0][0])
    per_circle: list[dict[str, Any]] = []
    for circle_index in range(num_circles):
        center_error_means: list[float] = []
        center_axis_means: list[float] = []
        normal_error_means: list[float] = []
        radius_error_means: list[float] = []
        adjusted_camera_center_error_means: list[float] = []
        adjusted_rotation_error_means: list[float] = []
        residual_norm_means: list[float] = []
        convergence_rates: list[float] = []
        for level_runs in repeated_circle_summaries:
            circle_runs = [run[circle_index] for run in level_runs]
            center_error_means.append(float(np.mean([entry["center_error_norm"] for entry in circle_runs])))
            center_axis_means.append(float(np.mean([entry["center_axis_99"] for entry in circle_runs])))
            normal_error_means.append(float(np.mean([entry["normal_angle_degrees"] for entry in circle_runs])))
            radius_error_means.append(float(np.mean([entry["radius_error_abs"] for entry in circle_runs])))
            adjusted_camera_center_error_means.append(
                float(np.mean([entry["adjusted_camera_center_error_mean"] for entry in circle_runs]))
            )
            adjusted_rotation_error_means.append(
                float(np.mean([entry["adjusted_rotation_error_mean_degrees"] for entry in circle_runs]))
            )
            residual_norm_means.append(float(np.mean([entry["residual_norm"] for entry in circle_runs])))
            convergence_rates.append(float(np.mean([1.0 if entry["converged"] else 0.0 for entry in circle_runs])))

        center_error_envelope = _monotone_envelope(center_error_means)
        center_axis_envelope = _monotone_envelope(center_axis_means)
        normal_error_envelope = _monotone_envelope(normal_error_means)
        radius_error_envelope = _monotone_envelope(radius_error_means)
        adjusted_camera_center_error_envelope = _monotone_envelope(adjusted_camera_center_error_means)
        adjusted_rotation_error_envelope = _monotone_envelope(adjusted_rotation_error_means)
        residual_norm_envelope = _monotone_envelope(residual_norm_means)

        per_circle.append(
            {
                "circle_index": circle_index,
                "center_error_mean_raw": center_error_means,
                "center_axis_99_raw": center_axis_means,
                "center_error_mean": center_error_envelope,
                "center_axis_99": center_axis_envelope,
                "normal_angle_mean_degrees_raw": normal_error_means,
                "normal_angle_mean_degrees": normal_error_envelope,
                "radius_error_mean_raw": radius_error_means,
                "radius_error_mean": radius_error_envelope,
                "adjusted_camera_center_error_mean_raw": adjusted_camera_center_error_means,
                "adjusted_camera_center_error_mean": adjusted_camera_center_error_envelope,
                "adjusted_rotation_error_mean_degrees_raw": adjusted_rotation_error_means,
                "adjusted_rotation_error_mean_degrees": adjusted_rotation_error_envelope,
                "residual_norm_mean_raw": residual_norm_means,
                "residual_norm_mean": residual_norm_envelope,
                "convergence_rate": convergence_rates,
                "nondecreasing_center_error_mean": _is_non_decreasing(center_error_envelope),
                "nondecreasing_center_axis_99": _is_non_decreasing(center_axis_envelope),
            }
        )

    return {
        "camera_center_noise_levels": noise_levels,
        "repeat_count": len(repeated_circle_summaries[0]),
        "per_circle": per_circle,
    }


def save_noise_sweep_plot(
    trend_summary: dict[str, Any],
    plot_path: str | Path,
) -> None:
    """Save a compact trend plot when requested by the CLI."""

    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    plot_path = Path(plot_path)
    plot_path.parent.mkdir(parents=True, exist_ok=True)

    levels = np.asarray(trend_summary["camera_center_noise_levels"], dtype=np.float64)
    per_circle = trend_summary["per_circle"]
    if not per_circle:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.set_axis_off()
        ax.text(0.5, 0.5, "No trend data available", ha="center", va="center")
        fig.tight_layout()
        fig.savefig(plot_path, dpi=160)
        plt.close(fig)
        return

    fig, axes = plt.subplots(len(per_circle), 4, figsize=(18.0, 3.6 * len(per_circle)), sharex=True)
    if len(per_circle) == 1:
        axes = np.asarray([axes], dtype=object)

    for row_axes, circle_summary in zip(axes, per_circle, strict=True):
        center_axis, uncertainty_axis, angle_axis, radius_axis = row_axes
        center_axis.plot(levels, circle_summary["center_error_mean"], marker="o", label="center error mean")
        center_axis.plot(
            levels,
            circle_summary["adjusted_camera_center_error_mean"],
            marker="^",
            label="adjusted pose center error",
        )
        center_axis.set_ylabel(f"circle {circle_summary['circle_index']}")
        center_axis.set_title("Center Accuracy")
        center_axis.grid(True, alpha=0.25)
        center_axis.legend(loc="best")

        uncertainty_axis.plot(levels, circle_summary["center_axis_99"], marker="s", label="center axis 99")
        uncertainty_axis.set_title("Center Uncertainty")
        uncertainty_axis.grid(True, alpha=0.25)
        uncertainty_axis.legend(loc="best")

        angle_axis.plot(
            levels,
            circle_summary["normal_angle_mean_degrees"],
            marker="o",
            label="normal angle error",
        )
        angle_axis.plot(
            levels,
            circle_summary["adjusted_rotation_error_mean_degrees"],
            marker="^",
            label="adjusted pose rotation error",
        )
        angle_axis.set_title("Angle Errors")
        angle_axis.grid(True, alpha=0.25)
        angle_axis.legend(loc="best")

        radius_axis.plot(levels, circle_summary["radius_error_mean"], marker="o", label="radius error mean")
        radius_axis.set_title("Radius Error")
        radius_axis.grid(True, alpha=0.25)
        radius_axis.legend(loc="best")

    for axis in axes[-1]:
        axis.set_xlabel("camera-center noise sigma")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=160)
    plt.close(fig)


def summarize_fastpaper_trends(
    noise_levels: Iterable[float],
    repeated_circle_summaries: list[list[list[dict[str, Any]]]],
) -> dict[str, Any]:
    trend_summary = summarize_noise_trends(noise_levels, repeated_circle_summaries)
    per_circle = trend_summary["per_circle"]
    if not per_circle:
        return {
            "camera_center_noise_levels": list(trend_summary["camera_center_noise_levels"]),
            "repeat_count": int(trend_summary["repeat_count"]),
            "center_error_mean": [],
            "center_error_mean_raw": [],
            "center_error_mean_monotone": [],
            "normal_angle_mean_degrees": [],
            "normal_angle_mean_degrees_raw": [],
            "normal_angle_mean_degrees_monotone": [],
            "radius_error_mean": [],
            "radius_error_mean_raw": [],
            "radius_error_mean_monotone": [],
            "convergence_rate": [],
        }

    def _mean_series(key: str) -> list[float]:
        stacked = np.asarray([circle[key] for circle in per_circle], dtype=np.float64)
        return np.mean(stacked, axis=0).astype(np.float64).tolist()

    center_error_mean_raw = _mean_series("center_error_mean_raw")
    normal_angle_mean_degrees_raw = _mean_series("normal_angle_mean_degrees_raw")
    radius_error_mean_raw = _mean_series("radius_error_mean_raw")

    return {
        "camera_center_noise_levels": list(trend_summary["camera_center_noise_levels"]),
        "repeat_count": int(trend_summary["repeat_count"]),
        "center_error_mean": center_error_mean_raw,
        "center_error_mean_raw": center_error_mean_raw,
        "center_error_mean_monotone": _mean_series("center_error_mean"),
        "normal_angle_mean_degrees": normal_angle_mean_degrees_raw,
        "normal_angle_mean_degrees_raw": normal_angle_mean_degrees_raw,
        "normal_angle_mean_degrees_monotone": _mean_series("normal_angle_mean_degrees"),
        "radius_error_mean": radius_error_mean_raw,
        "radius_error_mean_raw": radius_error_mean_raw,
        "radius_error_mean_monotone": _mean_series("radius_error_mean"),
        "convergence_rate": _mean_series("convergence_rate"),
        "per_circle": per_circle,
    }


def save_fastpaper_result_table(
    results: dict[str, dict[str, dict[str, Any]]],
    *,
    table_path: str | Path,
) -> None:
    table_path = Path(table_path)
    table_path.parent.mkdir(parents=True, exist_ok=True)

    with table_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "scenario",
                "method",
                "camera_center_noise_sigma",
                "center_error_mean",
                "normal_angle_mean_degrees",
                "radius_error_mean",
                "convergence_rate",
            ),
        )
        writer.writeheader()
        for scenario, scenario_results in results.items():
            for method, result_bundle in scenario_results.items():
                trend_summary = result_bundle["trend_summary"]
                for level, center_error, normal_angle, radius_error, convergence_rate in zip(
                    trend_summary["camera_center_noise_levels"],
                    trend_summary["center_error_mean"],
                    trend_summary["normal_angle_mean_degrees"],
                    trend_summary["radius_error_mean"],
                    trend_summary["convergence_rate"],
                    strict=True,
                ):
                    writer.writerow(
                        {
                            "scenario": scenario,
                            "method": method,
                            "camera_center_noise_sigma": float(level),
                            "center_error_mean": float(center_error),
                            "normal_angle_mean_degrees": float(normal_angle),
                            "radius_error_mean": float(radius_error),
                            "convergence_rate": float(convergence_rate),
                        }
                    )


def save_fastpaper_profile_plot(
    scenario_results: dict[str, dict[str, Any]],
    *,
    metric_key: str,
    plot_path: str | Path,
    title: str,
    ylabel: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    plot_path = Path(plot_path)
    plot_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    for method, result_bundle in scenario_results.items():
        trend_summary = result_bundle["trend_summary"]
        levels = np.asarray(trend_summary["camera_center_noise_levels"], dtype=np.float64)
        values = np.asarray(trend_summary[metric_key], dtype=np.float64)
        ax.plot(levels, values, marker="o", linewidth=2.0, label=method)

    ax.set_title(title)
    ax.set_xlabel("camera-center noise sigma")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=160)
    plt.close(fig)
