from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.spatial.transform import Rotation

from gh_reliability.projection import look_at_rotation, normalize_vector, project_circle_contour, project_points


@dataclass(frozen=True)
class SceneData:
    circles: dict[str, np.ndarray]
    cameras: dict[str, np.ndarray]
    observations: dict[str, np.ndarray]
    metadata: dict[str, object]


def _parse_circle_configuration(
    scene_config: dict[str, Any] | None,
    num_circles: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    def _parse_dual_radius(circle: dict[str, Any]) -> tuple[float, float]:
        has_radius = "radius" in circle
        has_outer_radius = "outer_radius" in circle
        has_inner_radius = "inner_radius" in circle

        if has_inner_radius and not has_outer_radius:
            raise ValueError("circle inner_radius requires explicit outer_radius")

        if has_outer_radius:
            outer_radius = float(circle["outer_radius"])
            if has_radius and not np.isclose(float(circle["radius"]), outer_radius):
                raise ValueError("circle radius and outer_radius must match when both are provided")
            inner_radius = float(circle.get("inner_radius", 0.72 * outer_radius))
        else:
            outer_radius = float(circle["radius"])
            inner_radius = 0.72 * outer_radius
        if outer_radius <= 0.0:
            raise ValueError("circle outer radius must be positive")
        if inner_radius <= 0.0:
            raise ValueError("circle inner radius must be positive")
        if inner_radius >= outer_radius:
            raise ValueError("circle inner radius must be smaller than outer radius")
        return outer_radius, inner_radius

    if scene_config is not None and "circles" in scene_config:
        circles = list(scene_config["circles"])
        if not circles:
            raise ValueError("scene_config circles must be non-empty")
        centers = []
        normals = []
        outer_radii = []
        inner_radii = []
        for circle in circles:
            center = np.asarray(circle["center"], dtype=np.float64)
            normal = normalize_vector(np.asarray(circle["normal"], dtype=np.float64))
            if center.shape != (3,):
                raise ValueError("each circle center must have shape (3,)")
            outer_radius, inner_radius = _parse_dual_radius(circle)
            centers.append(center)
            normals.append(normal)
            outer_radii.append(outer_radius)
            inner_radii.append(inner_radius)
        return (
            np.asarray(centers, dtype=np.float64),
            np.asarray(normals, dtype=np.float64),
            np.asarray(outer_radii, dtype=np.float64),
            np.asarray(inner_radii, dtype=np.float64),
        )

    if num_circles <= 0:
        raise ValueError("num_circles must be positive")

    circle_indices = np.arange(num_circles, dtype=np.float64)
    if num_circles == 1:
        x_positions = np.array([0.0], dtype=np.float64)
    else:
        x_positions = np.linspace(-0.85, 0.85, num_circles, dtype=np.float64)
    circle_centers = np.column_stack(
        [
            x_positions,
            0.28 * np.sin(0.9 * circle_indices - 0.5),
            4.6 + 0.32 * circle_indices,
        ]
    ).astype(np.float64)
    circle_normals = np.stack(
        [
            normalize_vector(
                np.array(
                    [
                        0.22 * np.cos(0.8 * index + 0.4),
                        0.18 * np.sin(0.6 * index - 0.2),
                        0.96,
                    ],
                    dtype=np.float64,
                )
            )
            for index in circle_indices
        ],
        axis=0,
    )
    circle_outer_radii = (0.52 + 0.07 * (circle_indices % 4) + 0.015 * np.floor(circle_indices / 4.0)).astype(np.float64)
    circle_inner_radii = (0.72 * circle_outer_radii).astype(np.float64)
    return circle_centers, circle_normals, circle_outer_radii, circle_inner_radii


def _parse_intrinsics(scene_config: dict[str, Any] | None) -> np.ndarray:
    if scene_config is not None and "intrinsics" in scene_config:
        intrinsics = np.asarray(scene_config["intrinsics"], dtype=np.float64)
        if intrinsics.shape != (3, 3):
            raise ValueError("scene_config intrinsics must have shape (3, 3)")
        return intrinsics

    return np.array(
        [
            [900.0, 0.0, 320.0],
            [0.0, 880.0, 240.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def _orthonormalize_rotation(rotation_matrix: np.ndarray) -> np.ndarray:
    rotation_matrix = np.asarray(rotation_matrix, dtype=np.float64)
    if rotation_matrix.shape != (3, 3):
        raise ValueError("camera rotation must have shape (3, 3)")
    return Rotation.from_matrix(rotation_matrix).as_matrix()


def _parse_camera_configuration(
    scene_config: dict[str, Any] | None,
    num_views: int,
    target: np.ndarray,
    rng: np.random.Generator,
    camera_center_noise_sigma: float,
    rotation_noise_sigma_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if num_views < 3:
        raise ValueError("num_views must be at least 3 for stable reconstruction")

    cameras = None if scene_config is None else scene_config.get("cameras")
    scenario = None if scene_config is None else scene_config.get("scenario")
    if scenario is not None and scenario not in {"near_coplanar", "non_coplanar"}:
        raise ValueError("scene_config scenario must be one of: near_coplanar, non_coplanar")
    rotation_noise_sigma_rad = float(np.deg2rad(rotation_noise_sigma_deg))
    translation_covariance = (float(camera_center_noise_sigma) ** 2) * np.eye(3, dtype=np.float64)
    rotation_covariance = (rotation_noise_sigma_rad**2) * np.eye(3, dtype=np.float64)

    if cameras is None:
        view_angles = np.linspace(0.0, 2.0 * np.pi, num_views, endpoint=False, dtype=np.float64)
        if scenario == "near_coplanar":
            camera_centers_true = np.stack(
                [
                    0.95 * np.cos(view_angles),
                    0.42 * np.sin(view_angles),
                    0.02 * np.sin(2.0 * view_angles),
                ],
                axis=1,
            ).astype(np.float64)
        elif scenario == "non_coplanar":
            camera_centers_true = np.stack(
                [
                    0.92 * np.cos(view_angles),
                    0.38 * np.sin(view_angles),
                    0.34 + 0.24 * np.sin(2.0 * view_angles),
                ],
                axis=1,
            ).astype(np.float64)
        else:
            camera_centers_true = np.stack(
                [
                    0.95 * np.cos(view_angles),
                    0.42 * np.sin(view_angles),
                    0.18 * np.sin(2.0 * view_angles),
                ],
                axis=1,
            ).astype(np.float64)
        rotations_true = np.stack([look_at_rotation(center, target) for center in camera_centers_true], axis=0)
        center_perturbations = np.zeros_like(camera_centers_true)
        rotation_perturbations = np.zeros_like(camera_centers_true)
    else:
        camera_specs = list(cameras)
        if len(camera_specs) < 3:
            raise ValueError("scene_config cameras must contain at least 3 views")
        camera_centers_true = []
        rotations_true = []
        center_perturbations = []
        rotation_perturbations = []
        for camera in camera_specs:
            center = np.asarray(camera["center"], dtype=np.float64)
            if center.shape != (3,):
                raise ValueError("camera center must have shape (3,)")
            camera_centers_true.append(center)
            rotations_true.append(_orthonormalize_rotation(np.asarray(camera["rotation"], dtype=np.float64)))
            center_perturbations.append(
                np.asarray(camera.get("center_perturbation", np.zeros(3, dtype=np.float64)), dtype=np.float64)
            )
            rotation_perturbations.append(
                np.asarray(
                    camera.get("rotation_perturbation_rotvec", np.zeros(3, dtype=np.float64)),
                    dtype=np.float64,
                )
            )
        camera_centers_true = np.asarray(camera_centers_true, dtype=np.float64)
        rotations_true = np.asarray(rotations_true, dtype=np.float64)
        center_perturbations = np.asarray(center_perturbations, dtype=np.float64)
        rotation_perturbations = np.asarray(rotation_perturbations, dtype=np.float64)

    random_center_noise = rng.normal(scale=camera_center_noise_sigma, size=camera_centers_true.shape)
    random_rotation_noise = rng.normal(scale=rotation_noise_sigma_rad, size=camera_centers_true.shape)

    camera_centers_noisy = camera_centers_true + center_perturbations + random_center_noise
    total_rotation_perturbation = rotation_perturbations + random_rotation_noise
    rotations_noisy = np.stack(
        [
            Rotation.from_rotvec(rotation_delta).as_matrix() @ rotation_true
            for rotation_delta, rotation_true in zip(total_rotation_perturbation, rotations_true, strict=True)
        ],
        axis=0,
    )

    pose_covariances = np.zeros((camera_centers_true.shape[0], 6, 6), dtype=np.float64)
    pose_covariances[:, :3, :3] = translation_covariance
    pose_covariances[:, 3:, 3:] = rotation_covariance
    return camera_centers_true, rotations_true, camera_centers_noisy, rotations_noisy, pose_covariances


def generate_scene(
    num_circles: int = 2,
    num_views: int = 3,
    contour_samples_per_observation: int = 64,
    contour_noise_sigma: float = 0.35,
    camera_center_noise_sigma: float = 0.01,
    rotation_noise_sigma_deg: float = 0.0,
    seed: int = 20260325,
    scene_config: dict[str, Any] | None = None,
) -> SceneData:
    rng = np.random.default_rng(seed)
    circle_centers, circle_normals, circle_outer_radii, circle_inner_radii = _parse_circle_configuration(
        scene_config, num_circles
    )
    intrinsics = _parse_intrinsics(scene_config)
    target = circle_centers.mean(axis=0)
    (
        camera_centers_true,
        rotations_true,
        camera_centers_noisy,
        rotations,
        pose_covariances,
    ) = _parse_camera_configuration(
        scene_config=scene_config,
        num_views=num_views,
        target=target,
        rng=rng,
        camera_center_noise_sigma=camera_center_noise_sigma,
        rotation_noise_sigma_deg=rotation_noise_sigma_deg,
    )
    num_circles = int(circle_centers.shape[0])
    num_views = int(camera_centers_true.shape[0])

    contour_points_outer = np.empty((num_circles, num_views, contour_samples_per_observation, 2), dtype=np.float64)
    contour_points_inner = np.empty((num_circles, num_views, contour_samples_per_observation, 2), dtype=np.float64)
    projected_centers = np.empty((num_circles, num_views, 2), dtype=np.float64)

    for circle_index in range(num_circles):
        center = circle_centers[circle_index]
        normal = circle_normals[circle_index]
        outer_radius = circle_outer_radii[circle_index]
        inner_radius = circle_inner_radii[circle_index]
        center_world = center[None, :]
        for view_index in range(num_views):
            rotation = rotations_true[view_index]
            camera_center = camera_centers_true[view_index]
            outer_contour = project_circle_contour(
                center=center,
                normal=normal,
                radius=outer_radius,
                intrinsics=intrinsics,
                rotation=rotation,
                camera_center=camera_center,
                num_samples=contour_samples_per_observation,
            )
            inner_contour = project_circle_contour(
                center=center,
                normal=normal,
                radius=inner_radius,
                intrinsics=intrinsics,
                rotation=rotation,
                camera_center=camera_center,
                num_samples=contour_samples_per_observation,
            )
            outer_contour += rng.normal(scale=contour_noise_sigma, size=outer_contour.shape)
            inner_contour += rng.normal(scale=contour_noise_sigma, size=inner_contour.shape)
            contour_points_outer[circle_index, view_index] = outer_contour
            contour_points_inner[circle_index, view_index] = inner_contour
            projected_centers[circle_index, view_index] = project_points(
                center_world,
                intrinsics=intrinsics,
                rotation=rotation,
                camera_center=camera_center,
            )[0]

    fixed_rotations = bool(np.allclose(rotations, rotations_true, atol=1e-12))
    rotation_noise_model = "none"
    if rotation_noise_sigma_deg > 0.0:
        rotation_noise_model = "gaussian_axis_angle_noise"
    elif not fixed_rotations:
        rotation_noise_model = "deterministic_axis_angle_perturbation"

    metadata = {
        "num_circles": int(num_circles),
        "num_views": int(num_views),
        "contour_samples_per_observation": contour_samples_per_observation,
        "fixed_intrinsics": True,
        "fixed_rotations": fixed_rotations,
        "camera_noise_model": "gaussian_camera_center_noise",
        "contour_noise_model": "gaussian_image_noise",
        "rotation_noise_model": rotation_noise_model,
        "seed": seed,
        "local_simulation_choices": {
            "intrinsics_model": "single fixed calibration matrix",
            "rotation_model": (
                "true camera rotations with optional deterministic and gaussian axis-angle perturbations"
                if not fixed_rotations
                else "deterministic rotations used without perturbation"
            ),
            "camera_noise_sigma": camera_center_noise_sigma,
            "rotation_noise_sigma_deg": rotation_noise_sigma_deg,
            "contour_noise_sigma": contour_noise_sigma,
            "num_circles": int(num_circles),
            "num_views": int(num_views),
            "scenario": None if scene_config is None else scene_config.get("scenario"),
            "projection_source": "ground-truth circles projected with true camera centers, then perturbed in image space",
        },
    }

    return SceneData(
        circles={
            "centers": circle_centers,
            "normals": circle_normals,
            "radii": circle_outer_radii,
            "outer_radii": circle_outer_radii,
            "inner_radii": circle_inner_radii,
        },
        cameras={
            "intrinsics": intrinsics,
            "rotations_true": rotations_true,
            "rotations": rotations,
            "camera_centers_true": camera_centers_true,
        },
        observations={
            "camera_centers_noisy": camera_centers_noisy,
            "pose_covariances": pose_covariances,
            "contour_points": contour_points_outer,
            "contour_points_outer": contour_points_outer,
            "contour_points_inner": contour_points_inner,
            "projected_centers": projected_centers,
        },
        metadata=metadata,
    )
