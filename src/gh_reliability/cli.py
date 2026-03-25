from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from gh_reliability.run import run_noise_sweep

REFINEMENT_MODES = ("algebraic_only", "geometric_only", "algebraic_then_geometric")


def _parse_noise_levels(value: str) -> list[float]:
    levels = [part.strip() for part in value.split(",") if part.strip()]
    if not levels:
        raise argparse.ArgumentTypeError("at least one noise level is required")
    try:
        parsed = [float(level) for level in levels]
    except ValueError as exc:  # pragma: no cover - argparse surfaces the message
        raise argparse.ArgumentTypeError("noise levels must be comma-separated floats") from exc
    if any(level < 0.0 for level in parsed):
        raise argparse.ArgumentTypeError("noise levels must be non-negative")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the GH reliability validation sweep.")
    parser.add_argument("--config", type=Path, default=None, help="JSON config file for the full validation run.")
    parser.add_argument(
        "--refinement-mode",
        choices=REFINEMENT_MODES,
        default="algebraic_then_geometric",
        help="Reconstruction mode: stop after algebraic optimization or run geometric refinement afterward.",
    )
    parser.add_argument(
        "--compare-refinement-modes",
        action="store_true",
        help="Run both refinement modes on the same synthetic scenes and emit a comparison section in the JSON output.",
    )
    parser.add_argument(
        "--noise-levels",
        type=_parse_noise_levels,
        default=_parse_noise_levels("0.003,0.008,0.013"),
        help="Comma-separated camera-center noise sigmas.",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Number of repeated runs per noise level.")
    parser.add_argument(
        "--contour-noise-sigma",
        type=float,
        default=0.2,
        help="Gaussian contour noise used when simulating image observations.",
    )
    parser.add_argument(
        "--contour-samples",
        type=int,
        default=72,
        help="Number of contour samples per circle observation.",
    )
    parser.add_argument("--num-circles", type=int, default=2, help="Number of synthetic 3D circles to generate.")
    parser.add_argument("--num-views", type=int, default=3, help="Number of synthetic camera views to generate.")
    parser.add_argument("--seed", type=int, default=20260325, help="Base random seed.")
    parser.add_argument("--output-json", type=Path, default=None, help="Path to the summary JSON file.")
    parser.add_argument("--plot-path", type=Path, default=None, help="Optional trend plot output path.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Optional output directory for artifacts.")
    return parser


def _resolve_config_relative_path(config_path: Path, raw_path: str | None) -> Path | None:
    if raw_path is None:
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return config_path.parent / candidate


def _parse_run_request_from_config(config_path: Path) -> tuple[Path, dict[str, Any]]:
    payload = json.loads(config_path.read_text())
    output_json_raw = payload.get("output_json")
    if output_json_raw is None:
        raise ValueError("config must define output_json")

    scene_section = dict(payload.get("scene", payload.get("scene_config", {})))
    contour_samples = scene_section.pop(
        "contour_samples_per_observation",
        scene_section.pop("contour_samples", 72),
    )
    contour_noise_sigma = scene_section.pop("contour_noise_sigma", 0.2)
    num_circles = scene_section.pop("num_circles", 2)
    num_views = scene_section.pop("num_views", 3)
    rotation_noise_sigma_deg = scene_section.pop("rotation_noise_sigma_deg", 0.0)
    default_camera_sigma = scene_section.pop("camera_center_noise_sigma", None)
    noise_levels = payload.get("noise_levels")
    if noise_levels is None:
        if default_camera_sigma is None:
            raise ValueError("config must define noise_levels or scene.camera_center_noise_sigma")
        noise_levels = [float(default_camera_sigma)]
    refinement_mode = payload.get("refinement_mode", "algebraic_then_geometric")
    if refinement_mode not in REFINEMENT_MODES:
        raise ValueError(f"refinement_mode must be one of: {', '.join(REFINEMENT_MODES)}")
    compare_refinement_modes = bool(payload.get("compare_refinement_modes", False))

    run_kwargs: dict[str, Any] = {
        "noise_levels": noise_levels,
        "repeats": int(payload.get("repeats", 3)),
        "contour_noise_sigma": float(contour_noise_sigma),
        "contour_samples_per_observation": int(contour_samples),
        "num_circles": int(num_circles),
        "num_views": int(num_views),
        "rotation_noise_sigma_deg": float(rotation_noise_sigma_deg),
        "refinement_mode": refinement_mode,
        "compare_refinement_modes": compare_refinement_modes,
        "seed": int(payload.get("seed", 20260325)),
        "output_dir": _resolve_config_relative_path(config_path, payload.get("output_dir")),
        "plot_path": _resolve_config_relative_path(config_path, payload.get("plot_path")),
        "scene_config": scene_section or None,
    }
    output_json = _resolve_config_relative_path(config_path, str(output_json_raw))
    if output_json is None:
        raise ValueError("config must define output_json")
    return output_json, run_kwargs


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.config is not None:
            output_json, run_kwargs = _parse_run_request_from_config(args.config)
        else:
            if args.output_json is None:
                parser.error("--output-json is required unless --config is provided")
            output_json = args.output_json
            run_kwargs = {
                "noise_levels": args.noise_levels,
                "repeats": args.repeats,
                "contour_noise_sigma": args.contour_noise_sigma,
                "contour_samples_per_observation": args.contour_samples,
                "num_circles": args.num_circles,
                "num_views": args.num_views,
                "refinement_mode": args.refinement_mode,
                "compare_refinement_modes": args.compare_refinement_modes,
                "seed": args.seed,
                "output_dir": args.output_dir,
                "plot_path": args.plot_path,
            }
    except ValueError as exc:
        parser.error(str(exc))

    summary = run_noise_sweep(**run_kwargs)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
