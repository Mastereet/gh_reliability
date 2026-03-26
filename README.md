# gh_reliability

`gh_reliability` is a Python experiment workspace for validating generalized homography reconstruction reliability under synthetic perturbations.

## Repository Shape

The project now follows this structure:

- `src/` for reusable Python packages and modules
- `scripts/` for reproducible experiment entrypoints
- `configs/` for experiment configuration files
- `tests/` for unit, integration, and smoke checks
- `notebooks/` for exploration and visualization only
- `docs/` for specs, notes, and experiment records
- `outputs/` for generated results and artifacts

The Python package lives at `src/gh_reliability/`.

## Execution Path

The canonical reproducible run path is:

```bash
scripts/run_validation_uv.sh --config configs/gh_scene_config.json
```

That configuration writes artifacts into `outputs/`.

The fast-paper dual-circle profile uses:

```bash
scripts/run_validation_uv.sh --config configs/dual_circle_fastpaper.json
```

That profile writes the summary JSON, comparison CSV, and plot artifacts into `outputs/dual_circle_fastpaper/`.

## Development Workflow

- Use the repo-local `AGENTS.md` instructions for task workflow.
- Prefer `uv` with a local `.venv` when available.
- Keep generated outputs, caches, and short-term planning memory out of git.
- Treat notebooks as exploratory only; promote stable logic into modules or scripts.

## Suggested Local Setup

```bash
UV_CACHE_DIR=.uv-cache uv sync --group dev
UV_CACHE_DIR=.uv-cache uv run pytest -q
scripts/run_validation_uv.sh --config configs/gh_scene_config.json
```

## Repository Notes

- Stable library code belongs in `src/gh_reliability/`.
- Stable experiment entrypoints belong in `scripts/`.
- Stable reproducibility configs belong in `configs/`.
