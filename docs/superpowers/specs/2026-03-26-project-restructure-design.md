# Project Restructure Design

**Date:** 2026-03-26
**Scope:** Reorganize `gh_reliability` into a stable Python experiment layout and make the project runnable through standard package and script entrypoints.

## Goals

- Move reusable Python modules into `src/gh_reliability/`.
- Add a stable reproducible entrypoint under `scripts/`.
- Move reproducible example configuration into `configs/`.
- Update tests to import the package without per-file `sys.path` hacks.
- Make the project runnable and verifiable with a documented command flow.

## Constraints

- Preserve current algorithm behavior.
- Keep changes incremental and reversible.
- Avoid introducing new experimental methods or changing existing semantics.
- Keep output artifacts under `outputs/`.

## Non-Goals

- No algorithm redesign.
- No large internal module split beyond what the package move requires.
- No dependency installation outside the project.

## Options Considered

### Option 1: Minimal move only

Move files into `src/gh_reliability/` and patch imports just enough to pass.

Pros:
- Smallest code delta.

Cons:
- Leaves reproducibility story weak.
- Leaves example config and script paths underspecified.

### Option 2: Moderate package-and-entrypoint reorganization

Move library code into `src/gh_reliability/`, add a script entrypoint, normalize config location, update docs and tests, and verify both tests and a smoke run.

Pros:
- Gives the repo a durable base for more complex experiments.
- Keeps behavioral risk lower than a deep redesign.
- Aligns with `AGENTS.md` default repo shape.

Cons:
- Slightly broader surface area than a bare move.

### Option 3: Deep experiment framework refactor

Restructure modules into smaller subsystems and add a more opinionated experiment runner abstraction now.

Pros:
- Potentially cleaner long-term architecture.

Cons:
- Too much change for the current codebase size.
- Higher breakage risk and longer verification cycle.

## Decision

Choose Option 2.

This repo needs a reliable base for future experiment validation, not just a cosmetic directory shuffle. The package move, stable script entrypoint, config normalization, and test cleanup provide that base without mixing in unnecessary algorithm work.

## Acceptance Checks

- Importable package lives at `src/gh_reliability/`.
- `pytest` runs against the reorganized layout without test-local path injection.
- A documented script entrypoint can execute a smoke configuration successfully.
- Example config needed for reproducibility lives under `configs/`.
- README reflects the new structure and commands.

## Reproducibility Path

- Canonical entrypoint: `uv run python scripts/run_validation.py --config configs/gh_scene_config.json`
- Parameters/config: `configs/`
- Validation: unit test suite plus one minimal smoke run through the script entrypoint
- Generated outputs: `outputs/`

## Risks And Rollback

- Risk: import resolution changes may break tests or CLI execution.
  - Mitigation: use existing tests as regression coverage and add a script smoke run.
- Risk: moving config/example files may break paths referenced in docs.
  - Mitigation: update README and script/config references in the same change.
- Rollback: move files back to repo root, restore test path setup, and remove the new script/config layout.
