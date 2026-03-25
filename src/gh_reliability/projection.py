from __future__ import annotations

import numpy as np


def normalize_vector(vector: np.ndarray) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float64)
    norm = np.linalg.norm(array)
    if norm <= 0.0:
        raise ValueError("vector norm must be positive")
    return array / norm


def look_at_rotation(
    camera_center: np.ndarray,
    target: np.ndarray,
    up_hint: np.ndarray = np.array([0.0, 0.0, 1.0], dtype=np.float64),
) -> np.ndarray:
    eye = np.asarray(camera_center, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    up_hint = np.asarray(up_hint, dtype=np.float64)

    forward = normalize_vector(target - eye)
    right = np.cross(up_hint, forward)
    if np.linalg.norm(right) < 1e-10:
        up_hint = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        right = np.cross(up_hint, forward)
    right = normalize_vector(right)
    up = normalize_vector(np.cross(forward, right))
    return np.stack([right, up, forward], axis=0)


def orthonormal_circle_basis(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    normal = normalize_vector(normal)
    seed = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    if abs(np.dot(seed, normal)) > 0.9:
        seed = np.array([0.0, 1.0, 0.0], dtype=np.float64)
    tangent = normalize_vector(np.cross(normal, seed))
    bitangent = normalize_vector(np.cross(normal, tangent))
    return tangent, bitangent


def conic_matrix_to_vec5(conic: np.ndarray) -> np.ndarray:
    conic = np.asarray(conic, dtype=np.float64)
    return np.array(
        [conic[0, 0], conic[0, 1], conic[1, 1], conic[0, 2], conic[1, 2]],
        dtype=np.float64,
    )


def dual_conic_from_vec5(vec5: np.ndarray, e33: float = 1.0) -> np.ndarray:
    a, b, c, d, e = np.asarray(vec5, dtype=np.float64)
    return np.array(
        [[a, b, d], [b, c, e], [d, e, e33]],
        dtype=np.float64,
    )


def point_conic_center(point_conic: np.ndarray) -> np.ndarray:
    point_conic = np.asarray(point_conic, dtype=np.float64)
    return -np.linalg.solve(point_conic[:2, :2], point_conic[:2, 2])


def point_conic_axes(point_conic: np.ndarray) -> np.ndarray:
    point_conic = np.asarray(point_conic, dtype=np.float64)
    center = point_conic_center(point_conic)
    quadratic = point_conic[:2, :2]
    linear = point_conic[:2, 2]
    constant = center @ quadratic @ center + 2.0 * linear @ center + point_conic[2, 2]
    eigenvalues, _ = np.linalg.eigh(quadratic / -constant)
    axes = 1.0 / np.sqrt(eigenvalues)
    return np.sort(axes)[::-1]


def image_point_to_world_ray(
    image_point: np.ndarray,
    intrinsics: np.ndarray,
    rotation: np.ndarray,
) -> np.ndarray:
    image_point = np.asarray(image_point, dtype=np.float64)
    pixel_h = np.array([image_point[0], image_point[1], 1.0], dtype=np.float64)
    direction_camera = np.linalg.solve(intrinsics, pixel_h)
    direction_world = rotation.T @ direction_camera
    return normalize_vector(direction_world)


def triangulate_rays(camera_centers: np.ndarray, ray_directions: np.ndarray) -> np.ndarray:
    camera_centers = np.asarray(camera_centers, dtype=np.float64)
    ray_directions = np.asarray(ray_directions, dtype=np.float64)

    lhs = np.zeros((3, 3), dtype=np.float64)
    rhs = np.zeros(3, dtype=np.float64)
    identity = np.eye(3, dtype=np.float64)

    for camera_center, direction in zip(camera_centers, ray_directions, strict=True):
        projector = identity - np.outer(direction, direction)
        lhs += projector
        rhs += projector @ camera_center

    return np.linalg.solve(lhs, rhs)


def circle_projected_dual_conic(
    center: np.ndarray,
    scaled_normal: np.ndarray,
    projection_block: np.ndarray,
    camera_center: np.ndarray,
) -> np.ndarray:
    center = np.asarray(center, dtype=np.float64)
    scaled_normal = np.asarray(scaled_normal, dtype=np.float64)
    projection_block = np.asarray(projection_block, dtype=np.float64)
    camera_center = np.asarray(camera_center, dtype=np.float64)

    delta = center - camera_center
    radius_squared = float(np.dot(scaled_normal, scaled_normal))
    circle_block = (
        np.outer(delta, delta)
        + np.outer(scaled_normal, scaled_normal)
        - radius_squared * np.eye(3, dtype=np.float64)
    )
    return projection_block @ circle_block @ projection_block.T


def sample_circle_points_3d(
    center: np.ndarray,
    normal: np.ndarray,
    radius: float,
    num_samples: int,
) -> np.ndarray:
    center = np.asarray(center, dtype=np.float64)
    tangent, bitangent = orthonormal_circle_basis(normal)
    theta = np.linspace(0.0, 2.0 * np.pi, num_samples, endpoint=False)
    return center + radius * (
        np.outer(np.cos(theta), tangent) + np.outer(np.sin(theta), bitangent)
    )


def project_points(
    points_3d: np.ndarray,
    intrinsics: np.ndarray,
    rotation: np.ndarray,
    camera_center: np.ndarray,
) -> np.ndarray:
    points_3d = np.asarray(points_3d, dtype=np.float64)
    intrinsics = np.asarray(intrinsics, dtype=np.float64)
    rotation = np.asarray(rotation, dtype=np.float64)
    camera_center = np.asarray(camera_center, dtype=np.float64)

    camera_points = (rotation @ (points_3d - camera_center).T).T
    if np.any(camera_points[:, 2] <= 0.0):
        raise ValueError("all points must lie in front of the camera")

    homogeneous = (intrinsics @ camera_points.T).T
    return homogeneous[:, :2] / homogeneous[:, 2:3]


def project_circle_contour(
    center: np.ndarray,
    normal: np.ndarray,
    radius: float,
    intrinsics: np.ndarray,
    rotation: np.ndarray,
    camera_center: np.ndarray,
    num_samples: int,
) -> np.ndarray:
    points_3d = sample_circle_points_3d(
        center=center,
        normal=normal,
        radius=radius,
        num_samples=num_samples,
    )
    return project_points(points_3d, intrinsics=intrinsics, rotation=rotation, camera_center=camera_center)


def skew_symmetric(vector: np.ndarray) -> np.ndarray:
    x, y, z = np.asarray(vector, dtype=np.float64)
    return np.array(
        [
            [0.0, -z, y],
            [z, 0.0, -x],
            [-y, x, 0.0],
        ],
        dtype=np.float64,
    )


def backproject_pixel_to_world_ray(
    pixel: np.ndarray,
    intrinsics: np.ndarray,
    rotation: np.ndarray,
) -> np.ndarray:
    pixel = np.asarray(pixel, dtype=np.float64)
    intrinsics = np.asarray(intrinsics, dtype=np.float64)
    rotation = np.asarray(rotation, dtype=np.float64)
    camera_ray = np.linalg.solve(intrinsics, np.array([pixel[0], pixel[1], 1.0], dtype=np.float64))
    return normalize_vector(rotation.T @ camera_ray)


def triangulate_rays_least_squares(camera_centers: np.ndarray, ray_directions: np.ndarray) -> np.ndarray:
    camera_centers = np.asarray(camera_centers, dtype=np.float64)
    ray_directions = np.asarray(ray_directions, dtype=np.float64)
    lhs = np.zeros((3, 3), dtype=np.float64)
    rhs = np.zeros(3, dtype=np.float64)
    for center, direction in zip(camera_centers, ray_directions, strict=True):
        direction = normalize_vector(direction)
        projector = np.eye(3, dtype=np.float64) - np.outer(direction, direction)
        lhs += projector
        rhs += projector @ center
    return np.linalg.solve(lhs, rhs)
