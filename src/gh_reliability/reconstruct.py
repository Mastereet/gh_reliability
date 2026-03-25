from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import block_diag
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from gh_reliability.ellipse_fit import EllipseFitResult
from gh_reliability.projection import (
    backproject_pixel_to_world_ray,
    normalize_vector,
    skew_symmetric,
    triangulate_rays_least_squares,
)
from gh_reliability.simulation import SceneData


@dataclass(frozen=True)
class CircleObservation:
    intrinsics: np.ndarray
    camera_center: np.ndarray
    camera_center_covariance: np.ndarray
    rotation_rotvec: np.ndarray
    rotation_covariance: np.ndarray
    dual_conic_vec5: np.ndarray
    dual_conic_covariance: np.ndarray


@dataclass(frozen=True)
class ReconstructionResult:
    center: np.ndarray
    scaled_normal: np.ndarray
    covariance: np.ndarray
    adjusted_camera_centers: np.ndarray
    adjusted_rotation_rotvecs: np.ndarray
    adjusted_dual_conics: np.ndarray
    converged: bool
    iterations: int
    residual_vector: np.ndarray

    @property
    def normal(self) -> np.ndarray:
        norm = np.linalg.norm(self.scaled_normal)
        if norm <= 0.0:
            return self.scaled_normal
        return self.scaled_normal / norm

    @property
    def radius(self) -> float:
        return float(np.linalg.norm(self.scaled_normal))


def _symmetrize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float64)
    return 0.5 * (matrix + matrix.T)


def _project_psd(matrix: np.ndarray) -> np.ndarray:
    matrix = _symmetrize(matrix)
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    eigenvalues[eigenvalues < 0.0] = 0.0
    return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T


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


def _vec5_from_dual_conic_matrix(dual_conic: np.ndarray) -> np.ndarray:
    return np.array(
        [dual_conic[0, 0], dual_conic[0, 1], dual_conic[1, 1], dual_conic[0, 2], dual_conic[1, 2]],
        dtype=np.float64,
    )


def _projected_dual_conic_matrix(
    center: np.ndarray,
    scaled_normal: np.ndarray,
    matrix_m: np.ndarray,
    camera_center: np.ndarray,
) -> np.ndarray:
    delta = np.asarray(center, dtype=np.float64) - np.asarray(camera_center, dtype=np.float64)
    skew_normal = skew_symmetric(scaled_normal)
    circle_dual = np.outer(delta, delta) + skew_normal @ skew_normal
    return _symmetrize(np.asarray(matrix_m, dtype=np.float64) @ circle_dual @ np.asarray(matrix_m, dtype=np.float64).T)


def _view_residual_from_state_and_observation(state: np.ndarray, observation_vector: np.ndarray, matrix_m: np.ndarray) -> np.ndarray:
    center = np.asarray(state[:3], dtype=np.float64)
    scaled_normal = np.asarray(state[3:], dtype=np.float64)
    camera_center = np.asarray(observation_vector[:3], dtype=np.float64)
    rotation_rotvec = np.asarray(observation_vector[3:6], dtype=np.float64)
    observed_dual = np.asarray(observation_vector[6:], dtype=np.float64)
    matrix_m = np.asarray(matrix_m, dtype=np.float64) @ Rotation.from_rotvec(rotation_rotvec).as_matrix()
    predicted_dual = _projected_dual_conic_matrix(center, scaled_normal, matrix_m=matrix_m, camera_center=camera_center)
    return _vec5_from_dual_conic_matrix(predicted_dual) - predicted_dual[2, 2] * observed_dual


def _view_residual(state: np.ndarray, observation: CircleObservation) -> np.ndarray:
    observation_vector = np.concatenate([observation.camera_center, observation.rotation_rotvec, observation.dual_conic_vec5])
    return _view_residual_from_state_and_observation(state, observation_vector, matrix_m=observation.intrinsics)


def _observation_covariance(observation: CircleObservation) -> np.ndarray:
    return block_diag(observation.camera_center_covariance, observation.rotation_covariance, observation.dual_conic_covariance)


def _observation_jacobian(state: np.ndarray, observation: CircleObservation) -> np.ndarray:
    observation_vector = np.concatenate([observation.camera_center, observation.rotation_rotvec, observation.dual_conic_vec5])
    return _finite_difference_jacobian(
        lambda vector: _view_residual_from_state_and_observation(state, vector, matrix_m=observation.intrinsics),
        observation_vector,
        step=1e-6,
    )


def _state_jacobian(state: np.ndarray, observation: CircleObservation) -> np.ndarray:
    return _finite_difference_jacobian(lambda vector: _view_residual(vector, observation), state, step=1e-6)


def _inverse_sqrt(matrix: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    eigenvalues, eigenvectors = np.linalg.eigh(_symmetrize(matrix))
    eigenvalues[eigenvalues < floor] = floor
    return eigenvectors @ np.diag(1.0 / np.sqrt(eigenvalues)) @ eigenvectors.T


def _whitened_residual_vector(state: np.ndarray, observations: list[CircleObservation]) -> np.ndarray:
    whitened: list[np.ndarray] = []
    for observation in observations:
        residual = _view_residual(state, observation)
        observation_jacobian = _observation_jacobian(state, observation)
        residual_covariance = _project_psd(
            observation_jacobian @ _observation_covariance(observation) @ observation_jacobian.T
            + 1e-9 * np.eye(5, dtype=np.float64)
        )
        whitened.append(_inverse_sqrt(residual_covariance) @ residual)
    return np.concatenate(whitened, axis=0)


def _stacked_residual_vector(state: np.ndarray, observations: list[CircleObservation]) -> np.ndarray:
    return np.concatenate([_view_residual(state, observation) for observation in observations], axis=0)


def _ellipse_center(point_conic_matrix: np.ndarray) -> np.ndarray:
    quadratic = np.asarray(point_conic_matrix[:2, :2], dtype=np.float64)
    linear = np.asarray(point_conic_matrix[:2, 2], dtype=np.float64)
    return -np.linalg.solve(quadratic, linear)


def _ellipse_axes_lengths(point_conic_matrix: np.ndarray) -> np.ndarray:
    quadratic = np.asarray(point_conic_matrix[:2, :2], dtype=np.float64)
    linear = np.asarray(point_conic_matrix[:2, 2], dtype=np.float64)
    offset = float(point_conic_matrix[2, 2] - linear.T @ np.linalg.solve(quadratic, linear))
    if offset >= 0.0:
        raise ValueError("point conic does not represent a proper ellipse")
    eigenvalues = np.linalg.eigvalsh(_symmetrize(quadratic))
    return np.sqrt(np.maximum(-offset / eigenvalues, 1e-12))


def _algebraic_initial_state(scene: SceneData, ellipse_results: list[EllipseFitResult]) -> np.ndarray:
    matrix_k = np.asarray(scene.cameras["intrinsics"], dtype=np.float64)
    rotations = np.asarray(scene.cameras["rotations"], dtype=np.float64)
    matrix_ms = np.stack([matrix_k @ rotation for rotation in rotations], axis=0)
    camera_centers = np.asarray(scene.observations["camera_centers_noisy"], dtype=np.float64)
    num_views = len(ellipse_results)

    rows = []
    rhs = []
    symmetric_indices = ((0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2))
    index_lookup = {pair: index for index, pair in enumerate(symmetric_indices)}

    for view_index, (matrix_m, camera_center, ellipse_result) in enumerate(
        zip(matrix_ms, camera_centers, ellipse_results, strict=True)
    ):
        backprojected_dual = np.linalg.solve(matrix_m, ellipse_result.dual_conic_matrix @ np.linalg.inv(matrix_m.T))
        for row_index, column_index in symmetric_indices:
            row = np.zeros(9 + num_views, dtype=np.float64)
            row[index_lookup[(row_index, column_index)]] = 1.0
            if row_index == column_index:
                row[6 + row_index] += -2.0 * camera_center[row_index]
            else:
                row[6 + row_index] += -camera_center[column_index]
                row[6 + column_index] += -camera_center[row_index]
            row[9 + view_index] = -backprojected_dual[row_index, column_index]
            rows.append(row)
            rhs.append(-camera_center[row_index] * camera_center[column_index])

    solution, *_ = np.linalg.lstsq(np.asarray(rows), np.asarray(rhs), rcond=None)
    block_matrix = np.array(
        [
            [solution[0], solution[1], solution[2]],
            [solution[1], solution[3], solution[4]],
            [solution[2], solution[4], solution[5]],
        ],
        dtype=np.float64,
    )
    center = solution[6:9]

    # Practical initializer: solve the per-view scale factors jointly with a
    # free symmetric block, then recover the circle normal/radius by projecting
    # that block back to the expected circle eigenspectrum.
    circle_block = _symmetrize(block_matrix - np.outer(center, center))
    eigenvalues, eigenvectors = np.linalg.eigh(circle_block)
    normal_index = int(np.argmax(eigenvalues))
    radius = float(np.sqrt(max(1e-6, -np.mean(np.delete(eigenvalues, normal_index)))))
    scaled_normal = radius * eigenvectors[:, normal_index]
    return np.concatenate([center, scaled_normal], axis=0)


def _initial_state_from_scene(scene: SceneData, circle_index: int, ellipse_results: list[EllipseFitResult]) -> np.ndarray:
    try:
        return _algebraic_initial_state(scene, ellipse_results)
    except np.linalg.LinAlgError:
        pass

    intrinsics = np.asarray(scene.cameras["intrinsics"], dtype=np.float64)
    rotations = np.asarray(scene.cameras["rotations"], dtype=np.float64)
    camera_centers = np.asarray(scene.observations["camera_centers_noisy"], dtype=np.float64)
    rays = []
    major_axes = []
    for view_index, ellipse_result in enumerate(ellipse_results):
        try:
            pixel_center = _ellipse_center(ellipse_result.point_conic_matrix)
        except np.linalg.LinAlgError:
            pixel_center = np.asarray(scene.observations["projected_centers"][circle_index, view_index], dtype=np.float64)
        rays.append(backproject_pixel_to_world_ray(pixel_center, intrinsics=intrinsics, rotation=rotations[view_index]))
        try:
            major_axes.append(float(np.max(_ellipse_axes_lengths(ellipse_result.point_conic_matrix))))
        except (np.linalg.LinAlgError, ValueError):
            major_axes.append(10.0)
    center = triangulate_rays_least_squares(camera_centers, np.asarray(rays, dtype=np.float64))

    depths = []
    for rotation, camera_center in zip(rotations, camera_centers, strict=True):
        camera_point = rotation @ (center - camera_center)
        if camera_point[2] > 1e-6:
            depths.append(float(camera_point[2]))
    mean_focal = float(0.5 * (intrinsics[0, 0] + intrinsics[1, 1]))
    radius = float(np.mean(np.asarray(depths, dtype=np.float64) * np.asarray(major_axes, dtype=np.float64) / mean_focal))
    if not np.isfinite(radius) or radius <= 1e-6:
        radius = 0.5

    # The local validation scene keeps circles close to fronto-parallel, so a
    # +Z prior is a more stable initializer than a general pose-derived normal
    # estimate. This is an explicit prototype assumption, not a claim of paper
    # closure for arbitrary circle orientations.
    normal_hint = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    return np.concatenate([center, radius * normal_hint], axis=0)


def _solve_circle(observations: list[CircleObservation], initial_state: np.ndarray) -> least_squares:
    return least_squares(
        fun=lambda state: _whitened_residual_vector(state, observations),
        x0=np.asarray(initial_state, dtype=np.float64),
        method="lm",
        max_nfev=200,
        xtol=1e-10,
        ftol=1e-10,
        gtol=1e-10,
    )


def _parameter_covariance(state: np.ndarray, observations: list[CircleObservation]) -> np.ndarray:
    normal_matrix = np.zeros((6, 6), dtype=np.float64)
    for observation in observations:
        state_jacobian = _state_jacobian(state, observation)
        observation_jacobian = _observation_jacobian(state, observation)
        residual_covariance = _project_psd(
            observation_jacobian @ _observation_covariance(observation) @ observation_jacobian.T
            + 1e-9 * np.eye(5, dtype=np.float64)
        )
        precision = np.linalg.pinv(residual_covariance, hermitian=True)
        normal_matrix += state_jacobian.T @ precision @ state_jacobian
    return _project_psd(np.linalg.pinv(normal_matrix, hermitian=True))


def _adjusted_observations(state: np.ndarray, observations: list[CircleObservation]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    adjusted_centers = []
    adjusted_rotations = []
    adjusted_duals = []
    for observation in observations:
        residual = _view_residual(state, observation)
        observation_jacobian = _observation_jacobian(state, observation)
        observation_covariance = _observation_covariance(observation)
        residual_covariance = _project_psd(
            observation_jacobian @ observation_covariance @ observation_jacobian.T
            + 1e-9 * np.eye(5, dtype=np.float64)
        )
        correction = -observation_covariance @ observation_jacobian.T @ np.linalg.pinv(
            residual_covariance,
            hermitian=True,
        ) @ residual
        adjusted_centers.append(observation.camera_center + correction[:3])
        adjusted_rotations.append(observation.rotation_rotvec + correction[3:6])
        adjusted_duals.append(observation.dual_conic_vec5 + correction[6:])
    return (
        np.asarray(adjusted_centers, dtype=np.float64),
        np.asarray(adjusted_rotations, dtype=np.float64),
        np.asarray(adjusted_duals, dtype=np.float64),
    )


def _build_circle_observations(
    scene: SceneData,
    ellipse_results: list[EllipseFitResult],
    camera_center_sigma: float,
) -> list[CircleObservation]:
    intrinsics = np.asarray(scene.cameras["intrinsics"], dtype=np.float64)
    rotations = np.asarray(scene.cameras["rotations"], dtype=np.float64)
    rotation_rotvecs = Rotation.from_matrix(rotations).as_rotvec()
    noisy_centers = np.asarray(scene.observations["camera_centers_noisy"], dtype=np.float64)
    pose_covariances = np.asarray(
        scene.observations.get("pose_covariances", np.zeros((noisy_centers.shape[0], 6, 6), dtype=np.float64)),
        dtype=np.float64,
    )
    observations = []
    for view_index, ellipse_result in enumerate(ellipse_results):
        if pose_covariances.shape[0] != noisy_centers.shape[0]:
            raise ValueError("pose_covariances must match the number of views")
        center_covariance = pose_covariances[view_index, :3, :3]
        rotation_covariance = pose_covariances[view_index, 3:, 3:]
        if not np.any(center_covariance):
            center_covariance = (camera_center_sigma**2) * np.eye(3, dtype=np.float64)
        observations.append(
            CircleObservation(
                intrinsics=intrinsics,
                camera_center=noisy_centers[view_index],
                camera_center_covariance=np.asarray(center_covariance, dtype=np.float64),
                rotation_rotvec=np.asarray(rotation_rotvecs[view_index], dtype=np.float64),
                rotation_covariance=np.asarray(rotation_covariance, dtype=np.float64),
                dual_conic_vec5=np.asarray(ellipse_result.dual_conic_vec5, dtype=np.float64),
                dual_conic_covariance=np.asarray(ellipse_result.dual_conic_covariance, dtype=np.float64),
            )
        )
    return observations


def _pack_joint_state(
    circle_states: np.ndarray,
    pose_centers: np.ndarray,
    pose_rotvecs: np.ndarray,
) -> np.ndarray:
    return np.concatenate(
        [
            np.asarray(circle_states, dtype=np.float64).reshape(-1),
            np.asarray(pose_centers, dtype=np.float64).reshape(-1),
            np.asarray(pose_rotvecs, dtype=np.float64).reshape(-1),
        ],
        axis=0,
    )


def _unpack_joint_state(
    state: np.ndarray,
    num_circles: int,
    num_views: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    state = np.asarray(state, dtype=np.float64)
    circle_width = 6 * num_circles
    center_width = 3 * num_views
    circle_states = state[:circle_width].reshape(num_circles, 6)
    pose_centers = state[circle_width : circle_width + center_width].reshape(num_views, 3)
    pose_rotvecs = state[circle_width + center_width :].reshape(num_views, 3)
    return circle_states, pose_centers, pose_rotvecs


def _normalized_dual_vec5(dual_conic: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    dual_conic = np.asarray(dual_conic, dtype=np.float64)
    scale = float(dual_conic[2, 2])
    if abs(scale) < floor:
        scale = floor if scale >= 0.0 else -floor
    return _vec5_from_dual_conic_matrix(dual_conic) / scale


def _joint_residual_vector(
    state: np.ndarray,
    *,
    num_circles: int,
    num_views: int,
    intrinsics: np.ndarray,
    observed_centers: np.ndarray,
    observed_rotvecs: np.ndarray,
    observed_duals: np.ndarray,
    center_whiteners: np.ndarray,
    rotation_whiteners: np.ndarray,
    dual_whiteners: np.ndarray,
) -> np.ndarray:
    circle_states, pose_centers, pose_rotvecs = _unpack_joint_state(state, num_circles=num_circles, num_views=num_views)
    residuals: list[np.ndarray] = []

    for view_index in range(num_views):
        residuals.append(center_whiteners[view_index] @ (pose_centers[view_index] - observed_centers[view_index]))
        residuals.append(rotation_whiteners[view_index] @ (pose_rotvecs[view_index] - observed_rotvecs[view_index]))

    for circle_index in range(num_circles):
        center = circle_states[circle_index, :3]
        scaled_normal = circle_states[circle_index, 3:]
        for view_index in range(num_views):
            matrix_m = intrinsics @ Rotation.from_rotvec(pose_rotvecs[view_index]).as_matrix()
            predicted_dual = _projected_dual_conic_matrix(
                center,
                scaled_normal,
                matrix_m=matrix_m,
                camera_center=pose_centers[view_index],
            )
            raw_residual = _vec5_from_dual_conic_matrix(predicted_dual) - predicted_dual[2, 2] * observed_duals[circle_index, view_index]
            residuals.append(dual_whiteners[circle_index, view_index] @ raw_residual)

    return np.concatenate(residuals, axis=0)


def _point_conic_from_dual(dual_conic: np.ndarray) -> np.ndarray:
    dual_conic = _symmetrize(np.asarray(dual_conic, dtype=np.float64))
    return _symmetrize(np.linalg.pinv(dual_conic, hermitian=True))


def _sampson_point_residuals(point_conic: np.ndarray, contour_points: np.ndarray, point_sigma: float) -> np.ndarray:
    point_conic = _symmetrize(np.asarray(point_conic, dtype=np.float64))
    contour_points = np.asarray(contour_points, dtype=np.float64)
    homogeneous_points = np.column_stack([contour_points, np.ones(contour_points.shape[0], dtype=np.float64)])
    conic_products = homogeneous_points @ point_conic
    algebraic_values = np.sum(conic_products * homogeneous_points, axis=1)
    gradients = 2.0 * conic_products[:, :2]
    gradient_norms = np.linalg.norm(gradients, axis=1)
    safe_norms = np.maximum(gradient_norms, 1e-9)
    safe_sigma = max(float(point_sigma), 1e-9)
    return algebraic_values / (safe_norms * safe_sigma)


def _joint_geometric_residual_vector(
    state: np.ndarray,
    *,
    num_circles: int,
    num_views: int,
    intrinsics: np.ndarray,
    observed_centers: np.ndarray,
    observed_rotvecs: np.ndarray,
    contour_points: np.ndarray,
    point_sigma: float,
    center_whiteners: np.ndarray,
    rotation_whiteners: np.ndarray,
) -> np.ndarray:
    circle_states, pose_centers, pose_rotvecs = _unpack_joint_state(state, num_circles=num_circles, num_views=num_views)
    residuals: list[np.ndarray] = []

    for view_index in range(num_views):
        residuals.append(center_whiteners[view_index] @ (pose_centers[view_index] - observed_centers[view_index]))
        residuals.append(rotation_whiteners[view_index] @ (pose_rotvecs[view_index] - observed_rotvecs[view_index]))

    for circle_index in range(num_circles):
        center = circle_states[circle_index, :3]
        scaled_normal = circle_states[circle_index, 3:]
        for view_index in range(num_views):
            matrix_m = intrinsics @ Rotation.from_rotvec(pose_rotvecs[view_index]).as_matrix()
            predicted_dual = _projected_dual_conic_matrix(
                center,
                scaled_normal,
                matrix_m=matrix_m,
                camera_center=pose_centers[view_index],
            )
            point_conic = _point_conic_from_dual(predicted_dual)
            residuals.append(
                _sampson_point_residuals(
                    point_conic,
                    contour_points[circle_index, view_index],
                    point_sigma=point_sigma,
                )
            )

    return np.concatenate(residuals, axis=0)


def _joint_raw_circle_residuals(
    circle_state: np.ndarray,
    pose_centers: np.ndarray,
    pose_rotvecs: np.ndarray,
    intrinsics: np.ndarray,
    observed_duals: np.ndarray,
) -> np.ndarray:
    center = np.asarray(circle_state[:3], dtype=np.float64)
    scaled_normal = np.asarray(circle_state[3:], dtype=np.float64)
    residuals = []
    for view_index in range(pose_centers.shape[0]):
        matrix_m = intrinsics @ Rotation.from_rotvec(pose_rotvecs[view_index]).as_matrix()
        predicted_dual = _projected_dual_conic_matrix(
            center,
            scaled_normal,
            matrix_m=matrix_m,
            camera_center=pose_centers[view_index],
        )
        residuals.append(_vec5_from_dual_conic_matrix(predicted_dual) - predicted_dual[2, 2] * observed_duals[view_index])
    return np.concatenate(residuals, axis=0)


def reconstruct_scene(
    scene: SceneData,
    ellipse_results: list[list[EllipseFitResult]],
    camera_center_sigma: float,
    refinement_mode: str = "algebraic_then_geometric",
) -> list[ReconstructionResult]:
    if refinement_mode not in {"algebraic_only", "geometric_only", "algebraic_then_geometric"}:
        raise ValueError(
            "refinement_mode must be 'algebraic_only', 'geometric_only', or 'algebraic_then_geometric'"
        )
    num_circles = len(ellipse_results)
    if num_circles == 0:
        return []

    intrinsics = np.asarray(scene.cameras["intrinsics"], dtype=np.float64)
    observed_centers = np.asarray(scene.observations["camera_centers_noisy"], dtype=np.float64)
    observed_rotvecs = Rotation.from_matrix(np.asarray(scene.cameras["rotations"], dtype=np.float64)).as_rotvec()
    pose_covariances = np.asarray(scene.observations.get("pose_covariances"), dtype=np.float64)
    if pose_covariances.ndim != 3 or pose_covariances.shape[1:] != (6, 6):
        raise ValueError("scene observations must include pose_covariances with shape (num_views, 6, 6)")
    num_views = observed_centers.shape[0]
    contour_points = np.asarray(scene.observations["contour_points"], dtype=np.float64)
    point_sigma = float(scene.metadata.get("local_simulation_choices", {}).get("contour_noise_sigma", 1.0))

    observed_duals = np.asarray(
        [
            [np.asarray(result.dual_conic_vec5, dtype=np.float64) for result in circle_results]
            for circle_results in ellipse_results
        ],
        dtype=np.float64,
    )
    dual_covariances = np.asarray(
        [
            [np.asarray(result.dual_conic_covariance, dtype=np.float64) for result in circle_results]
            for circle_results in ellipse_results
        ],
        dtype=np.float64,
    )

    center_whiteners = np.asarray(
        [_inverse_sqrt(_project_psd(pose_covariances[view_index, :3, :3] + 1e-12 * np.eye(3))) for view_index in range(num_views)],
        dtype=np.float64,
    )
    rotation_whiteners = np.asarray(
        [_inverse_sqrt(_project_psd(pose_covariances[view_index, 3:, 3:] + 1e-12 * np.eye(3))) for view_index in range(num_views)],
        dtype=np.float64,
    )
    dual_whiteners = np.asarray(
        [
            [
                _inverse_sqrt(_project_psd(dual_covariances[circle_index, view_index] + 1e-12 * np.eye(5)))
                for view_index in range(num_views)
            ]
            for circle_index in range(num_circles)
        ],
        dtype=np.float64,
    )

    initial_circle_states = np.asarray(
        [_initial_state_from_scene(scene, circle_index, circle_ellipse_results) for circle_index, circle_ellipse_results in enumerate(ellipse_results)],
        dtype=np.float64,
    )
    initial_state = _pack_joint_state(initial_circle_states, observed_centers, observed_rotvecs)
    pose_sigma_scale = 8.0
    center_sigmas = np.sqrt(np.maximum(np.diagonal(pose_covariances[:, :3, :3], axis1=1, axis2=2), 1e-12))
    rotation_sigmas = np.sqrt(np.maximum(np.diagonal(pose_covariances[:, 3:, 3:], axis1=1, axis2=2), 1e-12))
    lower_bounds = _pack_joint_state(
        np.full_like(initial_circle_states, -np.inf, dtype=np.float64),
        observed_centers - pose_sigma_scale * center_sigmas,
        observed_rotvecs - pose_sigma_scale * rotation_sigmas,
    )
    upper_bounds = _pack_joint_state(
        np.full_like(initial_circle_states, np.inf, dtype=np.float64),
        observed_centers + pose_sigma_scale * center_sigmas,
        observed_rotvecs + pose_sigma_scale * rotation_sigmas,
    )

    def _solve_algebraic(x0: np.ndarray):
        return least_squares(
            fun=lambda state: _joint_residual_vector(
                state,
                num_circles=num_circles,
                num_views=num_views,
                intrinsics=intrinsics,
                observed_centers=observed_centers,
                observed_rotvecs=observed_rotvecs,
                observed_duals=observed_duals,
                center_whiteners=center_whiteners,
                rotation_whiteners=rotation_whiteners,
                dual_whiteners=dual_whiteners,
            ),
            x0=x0,
            bounds=(lower_bounds, upper_bounds),
            method="trf",
            max_nfev=300,
            xtol=1e-10,
            ftol=1e-10,
            gtol=1e-10,
        )

    def _solve_geometric(x0: np.ndarray):
        return least_squares(
            fun=lambda state: _joint_geometric_residual_vector(
                state,
                num_circles=num_circles,
                num_views=num_views,
                intrinsics=intrinsics,
                observed_centers=observed_centers,
                observed_rotvecs=observed_rotvecs,
                contour_points=contour_points,
                point_sigma=point_sigma,
                center_whiteners=center_whiteners,
                rotation_whiteners=rotation_whiteners,
            ),
            x0=x0,
            bounds=(lower_bounds, upper_bounds),
            method="trf",
            max_nfev=300,
            xtol=1e-10,
            ftol=1e-10,
            gtol=1e-10,
        )
    selected_result = None
    if refinement_mode == "algebraic_only":
        selected_result = _solve_algebraic(initial_state)
    elif refinement_mode == "geometric_only":
        selected_result = _solve_geometric(initial_state)
    else:
        algebraic_result = _solve_algebraic(initial_state)
        geometric_result = _solve_geometric(np.asarray(algebraic_result.x, dtype=np.float64))
        if geometric_result.success and np.all(np.isfinite(geometric_result.x)):
            selected_result = geometric_result
        else:
            selected_result = algebraic_result

    final_state = np.asarray(selected_result.x, dtype=np.float64)
    final_circle_states, adjusted_centers, adjusted_rotvecs = _unpack_joint_state(
        final_state,
        num_circles=num_circles,
        num_views=num_views,
    )
    joint_covariance = _project_psd(
        np.linalg.pinv(
            np.asarray(selected_result.jac, dtype=np.float64).T @ np.asarray(selected_result.jac, dtype=np.float64),
            hermitian=True,
        )
    )

    results = []
    for circle_index in range(num_circles):
        circle_state = final_circle_states[circle_index]
        state_slice = slice(6 * circle_index, 6 * (circle_index + 1))
        adjusted_duals = []
        for view_index in range(num_views):
            matrix_m = intrinsics @ Rotation.from_rotvec(adjusted_rotvecs[view_index]).as_matrix()
            predicted_dual = _projected_dual_conic_matrix(
                circle_state[:3],
                circle_state[3:],
                matrix_m=matrix_m,
                camera_center=adjusted_centers[view_index],
            )
            adjusted_duals.append(_normalized_dual_vec5(predicted_dual))
        results.append(
            ReconstructionResult(
                center=circle_state[:3],
                scaled_normal=circle_state[3:],
                covariance=joint_covariance[state_slice, state_slice],
                adjusted_camera_centers=np.asarray(adjusted_centers, dtype=np.float64),
                adjusted_rotation_rotvecs=np.asarray(adjusted_rotvecs, dtype=np.float64),
                adjusted_dual_conics=np.asarray(adjusted_duals, dtype=np.float64),
                converged=bool(selected_result.success),
                iterations=int(selected_result.nfev),
                residual_vector=_joint_raw_circle_residuals(
                    circle_state,
                    pose_centers=np.asarray(adjusted_centers, dtype=np.float64),
                    pose_rotvecs=np.asarray(adjusted_rotvecs, dtype=np.float64),
                    intrinsics=intrinsics,
                    observed_duals=observed_duals[circle_index],
                ),
            )
        )
    return results
