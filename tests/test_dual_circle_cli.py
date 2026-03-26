import csv
import json
import math
from pathlib import Path

import pytest

from gh_reliability.cli import main
from gh_reliability.run import run_dual_circle_fastpaper


def _assert_nested_close(first, second) -> None:
    assert type(first) is type(second)
    if isinstance(first, dict):
        assert set(first) == set(second)
        for key in first:
            _assert_nested_close(first[key], second[key])
        return
    if isinstance(first, list):
        assert len(first) == len(second)
        for left, right in zip(first, second, strict=True):
            _assert_nested_close(left, right)
        return
    if isinstance(first, float):
        assert math.isclose(first, second, rel_tol=1e-4, abs_tol=1e-9)
        return
    assert first == second


def test_cli_runs_dual_circle_fastpaper_profile_and_reports_methods_and_scenarios(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    source_config_path = repo_root / "configs" / "dual_circle_fastpaper.json"
    payload = json.loads(source_config_path.read_text())
    payload["output_dir"] = str(tmp_path / "dual_circle_fastpaper")
    payload["output_json"] = "summary.json"
    payload["repeats"] = 1
    payload["noise_levels"] = [0.0, 0.01]
    payload["scene"]["contour_samples_per_observation"] = 24
    payload["scene"]["num_views"] = 3
    config_path = tmp_path / "dual_circle_fastpaper.json"
    config_path.write_text(json.dumps(payload))

    exit_code = main(["--config", str(config_path)])

    assert exit_code == 0

    output_json = Path(payload["output_dir"]) / payload["output_json"]
    summary = json.loads(output_json.read_text())
    assert summary["experiment_profile"] == "dual_circle_fastpaper"
    assert summary["scenarios"] == ["near_coplanar", "non_coplanar"]
    assert summary["methods"] == ["outer_only", "dual_joint"]
    assert summary["artifacts"]["output_dir"] == str(Path(payload["output_dir"]))
    assert summary["reproducibility"]["canonical_entrypoint"] == (
        "scripts/run_validation_uv.sh --config configs/dual_circle_fastpaper.json"
    )
    assert summary["comparison"]["reference_method"] == "outer_only"
    assert summary["comparison"]["candidate_method"] == "dual_joint"
    assert set(summary["results"]) == {"near_coplanar", "non_coplanar"}
    for scenario in summary["scenarios"]:
        assert set(summary["results"][scenario]) == {"outer_only", "dual_joint"}
        plots = summary["artifacts"]["plots"][scenario]
        assert Path(plots["center_error_mean"]).exists()
        assert Path(plots["normal_angle_mean_degrees"]).exists()
        metric_comparison = summary["comparison"]["by_scenario"][scenario]
        assert set(metric_comparison) == {
            "center_error_mean",
            "normal_angle_mean_degrees",
            "radius_error_mean",
        }
        for method in summary["methods"]:
            trend_summary = summary["results"][scenario][method]["trend_summary"]
            assert "center_error_mean_raw" in trend_summary
            assert "normal_angle_mean_degrees_raw" in trend_summary
            assert "radius_error_mean_raw" in trend_summary
            assert "convergence_rate" in trend_summary

    table_path = Path(summary["artifacts"]["table_csv"])
    assert table_path.is_file()
    rows = list(csv.DictReader(table_path.open()))
    assert len(rows) == len(summary["scenarios"]) * len(summary["methods"]) * len(payload["noise_levels"])
    assert set(rows[0].keys()) == {
        "scenario",
        "method",
        "camera_center_noise_sigma",
        "center_error_mean",
        "normal_angle_mean_degrees",
        "radius_error_mean",
        "convergence_rate",
    }


def test_cli_rejects_unknown_experiment_profile(tmp_path):
    config_path = tmp_path / "unknown_profile.json"
    config_path.write_text(
        json.dumps(
            {
                "experiment_profile": "dual_circle_fastpapre",
                "output_json": "unused.json",
            }
        )
    )

    with pytest.raises(SystemExit):
        main(["--config", str(config_path)])


def test_fastpaper_runner_is_deterministic_for_fixed_seed(tmp_path):
    output_dir = tmp_path / "deterministic_fastpaper"
    first = run_dual_circle_fastpaper(
        noise_levels=[0.0, 0.01],
        repeats=1,
        contour_noise_sigma=0.1,
        contour_samples_per_observation=24,
        seed=20260327,
        num_circles=1,
        num_views=3,
        refinement_mode="algebraic_then_geometric",
        output_dir=output_dir,
    )
    second = run_dual_circle_fastpaper(
        noise_levels=[0.0, 0.01],
        repeats=1,
        contour_noise_sigma=0.1,
        contour_samples_per_observation=24,
        seed=20260327,
        num_circles=1,
        num_views=3,
        refinement_mode="algebraic_then_geometric",
        output_dir=output_dir,
    )

    _assert_nested_close(first, second)
