# Project Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `gh_reliability` into a standard Python experiment package layout and verify that both tests and a smoke experiment run succeed.

**Architecture:** Keep current library logic intact while moving reusable modules into `src/gh_reliability/`, promote the reproducible run path into `scripts/`, move stable config into `configs/`, and adjust tests and docs to use the new package boundary. Verification will use existing tests as regression coverage plus one smallest useful script smoke run.

**Tech Stack:** Python, `uv`, `pytest`, `numpy`, `scipy`, Markdown

---

### Task 1: Record planning state and target file map

**Files:**
- Create: `short-term-memory/task_plan.current.md`
- Create: `short-term-memory/findings.current.md`
- Create: `short-term-memory/progress.current.md`
- Modify: `docs/superpowers/specs/2026-03-26-project-restructure-design.md`
- Modify: `docs/superpowers/plans/2026-03-26-project-restructure.md`

- [ ] **Step 1: Write active short-term planning files**

Capture scope, risks, current findings, and the expected verification path in `short-term-memory/`.

- [ ] **Step 2: Verify planning files exist**

Run: `find short-term-memory -maxdepth 1 -type f | sort`
Expected: the three `*.current.md` files are present.

### Task 2: Preserve regression coverage and expose the package boundary

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_ellipse_fit.py`
- Modify: `tests/test_reconstruction.py`
- Modify: `tests/test_simulation.py`
- Modify: `tests/test_uncertainty.py`

- [ ] **Step 1: Keep regression tests but remove duplicated path bootstrapping**

Use a shared `tests/conftest.py` to add `src/` once, then remove per-test `sys.path` setup.

- [ ] **Step 2: Run one representative test before production moves**

Run: `pytest tests/test_cli.py -q`
Expected: may fail on import or package path before the move, which confirms the current boundary issue.

### Task 3: Move package code into `src/gh_reliability/`

**Files:**
- Create: `src/gh_reliability/__init__.py`
- Create: `src/gh_reliability/cli.py`
- Create: `src/gh_reliability/ellipse_fit.py`
- Create: `src/gh_reliability/evaluate.py`
- Create: `src/gh_reliability/projection.py`
- Create: `src/gh_reliability/reconstruct.py`
- Create: `src/gh_reliability/run.py`
- Create: `src/gh_reliability/simulation.py`
- Delete: `__init__.py`
- Delete: `cli.py`
- Delete: `ellipse_fit.py`
- Delete: `evaluate.py`
- Delete: `projection.py`
- Delete: `reconstruct.py`
- Delete: `run.py`
- Delete: `simulation.py`

- [ ] **Step 1: Create the package directory and move the library modules**

Relocate the current root-level library files into `src/gh_reliability/` without changing behavior.

- [ ] **Step 2: Run focused package regression tests**

Run: `pytest tests/test_simulation.py tests/test_ellipse_fit.py -q`
Expected: PASS.

### Task 4: Add stable run script and config layout

**Files:**
- Create: `scripts/run_validation.py`
- Create: `configs/gh_scene_config.json`
- Modify: `README.md`

- [ ] **Step 1: Add a thin script entrypoint**

Create a script that imports `gh_reliability.cli.main` and delegates to it.

- [ ] **Step 2: Promote the example config**

Move or copy the reproducible example config into `configs/`.

- [ ] **Step 3: Update README**

Document the new directory layout, canonical command, and output location.

- [ ] **Step 4: Run a CLI-focused regression test**

Run: `pytest tests/test_cli.py -q`
Expected: PASS.

### Task 5: Full verification and smoke run

**Files:**
- Verify only

- [ ] **Step 1: Run the full test suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 2: Run the smallest useful smoke experiment**

Run: `python scripts/run_validation.py --config configs/gh_scene_config.json`
Expected: exit code `0` and output artifacts written to the configured location.

- [ ] **Step 3: Confirm output artifacts**

Run: `find outputs -maxdepth 2 -type f | sort`
Expected: the smoke run artifacts are present.
