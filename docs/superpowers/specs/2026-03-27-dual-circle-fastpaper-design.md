# Dual-Circle Fast Paper Design

**Date:** 2026-03-27
**Scope:** Deliver a one-day, pure-simulation experiment path for a four-quartile paper comparing a single-circle baseline against a concentric dual-circle joint reconstruction method derived from `reference/GH.pdf` and `reference/gh-improve.md`.

## Goals

- Produce a stable, fixed-seed simulation experiment that compares a single-circle baseline against a dual-circle joint method.
- Keep the method close to the current repo structure so implementation risk stays low and results can be generated in one day.
- Generate directly usable paper artifacts: JSON summaries, trend plots, and one compact comparison table source.
- Preserve the GH-inspired uncertainty-aware framing without blocking on a full strict Gauss-Helmert reimplementation.

## Constraints

- Pure simulation only.
- One-day implementation window with deterministic outputs.
- Prefer incremental changes on top of the current runner, simulator, evaluator, and reconstruction code.
- No dependency installation outside the project.
- Keep generated outputs under `outputs/dual_circle_fastpaper/`.

## Non-Goals

- No real-data experiments in this phase.
- No strict dual-branch Gauss-Helmert observation-correction implementation.
- No full paper writing workflow in this change.
- No broad refactor of the existing experiment package.

## Options Considered

### Option 1: Strict dual-branch GH implementation first

Pros:
- Strongest theory alignment.
- Best long-term method story.

Cons:
- Too much implementation and debugging risk for one day.
- High chance of unstable convergence or incomplete verification.

### Option 2: Approximate GH-inspired joint optimization for a fast simulation paper

Pros:
- Reuses the current codebase shape.
- Fastest path to stable curves, tables, and reproducible outputs.
- Sufficient for a pure-simulation four-quartile methods paper if claims stay narrow.

Cons:
- Theory story must be phrased carefully.
- Some covariance handling remains approximate.

### Option 3: Baseline-only reproduction of GH(2014)

Pros:
- Lowest engineering risk.

Cons:
- No novel paper angle.
- Does not test the user's improved method.

## Decision

Choose Option 2.

The target is not a perfect theory-complete implementation. The target is a reproducible methods paper with clear simulation evidence that concentric dual-circle joint reconstruction improves over a single-circle baseline under pose uncertainty. The current repo already has reusable simulation, fitting, reconstruction, evaluation, and CLI scaffolding; the fastest credible route is to extend those pieces with a dual-circle experiment profile and keep the method framing explicit about approximation.

## Method Scope

- `Baseline`: use only the outer circle boundary and preserve the current single-circle reconstruction path as much as possible.
- `Ours`: use the outer and inner circle boundaries jointly, share the 3D center and orientation, and inject the known inner/outer radius relationship into the optimization.
- Do not add more baselines unless time remains after the minimum artifact set is verified.

## Acceptance Checks

- A fixed-seed command produces the same JSON and plot artifacts on repeated runs.
- The experiment supports two camera-network scenarios: near-coplanar and non-coplanar.
- The experiment sweeps camera-center noise and reports center, normal-angle, and radius error.
- The dual-circle method runs to completion and outperforms the outer-only baseline on the main metrics in most tested noise levels.
- CLI/config paths are documented and runnable from the repo.

## Reproducibility Path

- Canonical entrypoint: `scripts/run_validation_uv.sh --config configs/dual_circle_fastpaper.json`
- Parameters/config: `configs/dual_circle_fastpaper.json`
- Validation: fixed-seed noise sweep, JSON artifact existence, plot artifact existence, and targeted tests for the dual-circle pipeline
- Generated outputs: `outputs/dual_circle_fastpaper/`

## Experiment Matrix

- Methods:
  - `outer_only`
  - `dual_joint`
- Scenarios:
  - `near_coplanar`
  - `non_coplanar`
- Primary noise sweep:
  - camera-center Gaussian sigma in meters: `0.0, 0.005, 0.01, 0.02, 0.03`
- Repeats:
  - development: `10`
  - final paper plots: `30`
- Fixed random seed:
  - single base seed stored in the config

## Paper Deliverables

- One summary JSON with per-scenario and per-method metrics.
- One compact result table source derived from that JSON.
- Four core plots:
  - near-coplanar center error
  - near-coplanar normal-angle error
  - non-coplanar center error
  - non-coplanar normal-angle error

## Risks And Rollback

- Risk: the dual-circle optimizer may be numerically fragile.
  - Mitigation: keep the baseline path intact, use deterministic initialization, and fail fast with targeted tests.
- Risk: the inner-circle branch may not deliver a visible gain in all conditions.
  - Mitigation: start with the cleanest simulation assumptions and the two network geometries most likely to separate the methods.
- Risk: approximate covariance handling may oversell the method.
  - Mitigation: keep paper claims focused on accuracy and stability, not on full GH closure.
- Rollback: if the dual-circle method is not stable, preserve the added scenario/config/reporting infrastructure and reduce the paper claim to a preliminary simulation study.
