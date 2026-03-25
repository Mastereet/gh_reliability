# Repository Initialization Design

**Date:** 2026-03-26
**Scope:** Establish the baseline repository workflow and tooling for `gh_reliability` without changing current experiment behavior.

## Goals

- Copy the upstream `AGENTS.md` into this workspace.
- Initialize the repository with the minimum Python experiment baseline required by the repo policy.
- Make the expected workflow and output locations explicit.
- Avoid risky source-layout refactors during initialization.

## Constraints

- Preserve the current Python files and tests in place.
- Do not change runtime behavior as part of initialization.
- Keep generated outputs, caches, and short-term planning memory out of git.
- Prefer a local `uv` + `.venv` workflow, but do not install or mutate the host system.

## Non-Goals

- No migration of existing top-level modules into `src/` in this task.
- No package install, dependency sync, or system-level tooling changes.
- No feature or algorithm changes.

## Options Considered

### Option 1: Full repo restructure now

Move current modules into `src/`, relocate entrypoints into `scripts/`, and repair imports immediately.

Why not:
- Too much behavioral risk for an initialization-only task.
- Would require a broader TDD/refactor cycle and a larger validation surface.

### Option 2: Minimal compliant baseline now

Copy `AGENTS.md`, create the baseline directories, add root documentation and Python tooling config, and document that future work should converge on the preferred layout.

Why chosen:
- Matches the user request.
- Satisfies the repo workflow requirements with minimal disruption.
- Leaves existing experiment code runnable while making the intended structure explicit.

## Acceptance Checks

- `AGENTS.md` exists at repo root and matches the reference file.
- Repo contains `README.md`, `.gitignore`, `pyproject.toml`, and `pyrightconfig.json`.
- Planning artifact directories exist under `docs/superpowers/`.
- `short-term-memory/` is present and ignored.
- The repository status reflects only the expected initialization additions.

## Reproducibility Path

- Canonical current experiment entrypoint remains the existing CLI module and tests.
- Future reproducible entrypoints should live under `scripts/`.
- Parameters should live in `configs/`.
- Generated outputs should go under `outputs/`.

## Risks And Rollback

- Risk: tooling config may imply a future layout that the current code has not yet adopted.
  - Mitigation: document the current state clearly in `README.md`.
- Risk: `.gitignore` could accidentally hide source files.
  - Mitigation: keep ignore rules narrow and standard.
- Rollback: remove the added baseline files and directories if the repo chooses a different initialization scheme.
