import json
import subprocess
import sys
from pathlib import Path

from gh_reliability.cli import main


def test_cli_writes_summary_json_and_plot(tmp_path):
    output_json = tmp_path / "gh_summary.json"
    plot_path = tmp_path / "gh_center_trend.png"
    config_path = tmp_path / "gh_config.json"
    config_path.write_text(
        json.dumps(
            {
                "output_json": output_json.name,
                "plot_path": plot_path.name,
                "refinement_mode": "algebraic_only",
                "noise_levels": [0.003, 0.008],
                "repeats": 2,
                "seed": 29,
                "scene": {
                    "contour_noise_sigma": 0.2,
                    "contour_samples_per_observation": 64,
                    "camera_center_noise_sigma": 0.003,
                    "rotation_noise_sigma_deg": 0.5,
                    "num_circles": 3,
                    "num_views": 4,
                },
            }
        )
    )

    exit_code = main(
        [
            "--config",
            str(config_path),
        ]
    )

    assert exit_code == 0
    assert output_json.exists()
    assert plot_path.exists()

    payload = json.loads(output_json.read_text())
    assert "single_run" in payload
    assert "trend_summary" in payload
    assert len(payload["single_run"]["circles"]) == 3
    assert payload["configuration"]["num_circles"] == 3
    assert payload["configuration"]["num_views"] == 4
    assert payload["configuration"]["refinement_mode"] == "algebraic_only"
    assert len(payload["single_run"]["pose_covariances"]) == 4
    assert payload["artifacts"]["plot_path"] == str(plot_path)


def test_cli_can_emit_refinement_mode_comparison(tmp_path):
    output_json = tmp_path / "gh_comparison_summary.json"
    config_path = tmp_path / "gh_compare_config.json"
    config_path.write_text(
        json.dumps(
            {
                "output_json": output_json.name,
                "refinement_mode": "algebraic_then_geometric",
                "compare_refinement_modes": True,
                "noise_levels": [0.003, 0.008],
                "repeats": 1,
                "seed": 31,
                "scene": {
                    "contour_noise_sigma": 0.12,
                    "contour_samples_per_observation": 48,
                    "rotation_noise_sigma_deg": 0.35,
                    "num_circles": 2,
                    "num_views": 10,
                },
            }
        )
    )

    exit_code = main(["--config", str(config_path)])

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["configuration"]["compare_refinement_modes"] is True
    assert payload["comparison"]["modes"] == ["algebraic_only", "geometric_only", "algebraic_then_geometric"]
    assert "algebraic_only" in payload["comparison"]["single_run_by_mode"]
    assert "geometric_only" in payload["comparison"]["single_run_by_mode"]
    assert "algebraic_then_geometric" in payload["comparison"]["single_run_by_mode"]
    assert "geometric_only" in payload["comparison"]["delta_summary"]["by_candidate"]
    assert payload["comparison"]["delta_summary"]["by_candidate"]["algebraic_then_geometric"]["single_run"]["center_error_mean_improvement"] > 0.0


def test_run_validation_script_executes_configured_run(tmp_path):
    output_json = tmp_path / "script_summary.json"
    plot_path = tmp_path / "script_trend.png"
    config_path = tmp_path / "script_config.json"
    config_path.write_text(
        json.dumps(
            {
                "output_json": str(output_json),
                "plot_path": str(plot_path),
                "refinement_mode": "algebraic_only",
                "noise_levels": [0.003],
                "repeats": 1,
                "seed": 41,
                "scene": {
                    "contour_noise_sigma": 0.12,
                    "contour_samples_per_observation": 32,
                    "num_circles": 2,
                    "num_views": 3,
                },
            }
        )
    )

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_validation.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--config", str(config_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output_json.exists()
    assert plot_path.exists()
