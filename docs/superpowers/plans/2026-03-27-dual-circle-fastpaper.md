# Dual-Circle Fast Paper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-day pure-simulation experiment profile that compares an outer-only single-circle baseline against a concentric dual-circle joint reconstruction method and emits stable paper-ready artifacts.

**Architecture:** Extend the current synthetic scene generator so it can emit concentric ring targets and two fixed camera-network scenarios, add a dual-circle reconstruction path alongside the existing single-circle solver, and extend the evaluation/runner stack to compare both methods under a fixed camera-center noise sweep. Keep the CLI entrypoint and output contract deterministic through one dedicated config file and one dedicated output directory.

**Tech Stack:** Python, `uv`, `pytest`, `numpy`, `scipy`, Markdown, JSON, Matplotlib

---

### Task 1: Record planning state and paper experiment contract

**Files:**
- Create: `short-term-memory/task_plan.current.md`
- Create: `short-term-memory/findings.current.md`
- Create: `short-term-memory/progress.current.md`
- Modify: `docs/superpowers/specs/2026-03-27-dual-circle-fastpaper-design.md`
- Modify: `docs/superpowers/plans/2026-03-27-dual-circle-fastpaper.md`

- [ ] **Step 1: Write the current planning files**

Record the fixed one-day scope, canonical command, output directory, acceptance checks, and current research findings in `short-term-memory/`.

- [ ] **Step 2: Verify the planning files exist**

Run: `find short-term-memory -maxdepth 1 -type f | sort`
Expected: the three `*.current.md` files are present alongside any history files.

### Task 2: Add dual-circle simulation support and scenario presets

**Files:**
- Modify: `src/gh_reliability/simulation.py`
- Modify: `tests/test_simulation.py`
- Create: `tests/test_dual_circle_simulation.py`

- [ ] **Step 1: Write the failing simulation test**

Add a test that requests a concentric dual-circle scene with `near_coplanar` and `non_coplanar` presets and asserts:
- both inner and outer radii are present
- both contours exist for every circle-view pair
- the non-coplanar preset changes camera height geometry

- [ ] **Step 2: Run the new test to verify it fails**

Run: `pytest tests/test_dual_circle_simulation.py -q`
Expected: FAIL because the simulator does not yet expose dual-circle scene data.

- [ ] **Step 3: Implement the minimal scene extension**

Update `simulation.py` so the scene metadata and observations can represent:
- outer and inner radii for each target
- per-view contours for both boundaries
- named scenario presets for near-coplanar and non-coplanar camera layouts

- [ ] **Step 4: Run focused simulation tests**

Run: `pytest tests/test_simulation.py tests/test_dual_circle_simulation.py -q`
Expected: PASS.

### Task 3: Add outer-only and dual-joint reconstruction modes

**Files:**
- Modify: `src/gh_reliability/reconstruct.py`
- Modify: `src/gh_reliability/evaluate.py`
- Create: `tests/test_dual_circle_reconstruction.py`

- [ ] **Step 1: Write the failing reconstruction tests**

Add tests that:
- run the existing outer-only path on a dual-circle scene
- run the new dual-joint path on the same scene
- assert both return finite center, normal, and radius-like outputs
- assert the dual-joint path consumes both inner and outer observations

- [ ] **Step 2: Run the new reconstruction tests to verify failure**

Run: `pytest tests/test_dual_circle_reconstruction.py -q`
Expected: FAIL because no dual-joint reconstruction mode exists yet.

- [ ] **Step 3: Implement the minimal dual-joint solver path**

Extend reconstruction and evaluation so the runner can select:
- `outer_only`
- `dual_joint`

Keep the implementation close to the current optimizer:
- preserve the existing single-circle path for `outer_only`
- add a shared-center/shared-orientation dual-branch residual for `dual_joint`
- use the known inner-to-outer radius ratio in the dual residual construction

- [ ] **Step 4: Run focused reconstruction tests**

Run: `pytest tests/test_reconstruction.py tests/test_dual_circle_reconstruction.py -q`
Expected: PASS.

### Task 4: Add the fast-paper experiment profile, config, and reporting

**Files:**
- Modify: `src/gh_reliability/run.py`
- Modify: `src/gh_reliability/cli.py`
- Modify: `src/gh_reliability/evaluate.py`
- Create: `configs/dual_circle_fastpaper.json`
- Modify: `README.md`
- Create: `tests/test_dual_circle_cli.py`

- [ ] **Step 1: Write the failing CLI/profile test**

Add a test that loads `configs/dual_circle_fastpaper.json`, runs the CLI through the existing entrypoint, and asserts that the summary contains both methods and both scenarios.

- [ ] **Step 2: Run the new CLI/profile test to verify failure**

Run: `pytest tests/test_dual_circle_cli.py -q`
Expected: FAIL because the config profile and summary schema do not exist yet.

- [ ] **Step 3: Implement the paper experiment runner**

Add one dedicated run path that:
- sweeps the fixed camera-center noise levels
- runs both methods on both scenarios
- aggregates center, normal-angle, radius, and convergence metrics
- saves plots into `outputs/dual_circle_fastpaper/`

- [ ] **Step 4: Add the reproducible config and README note**

Create `configs/dual_circle_fastpaper.json` and document the canonical run command and artifact location in `README.md`.

- [ ] **Step 5: Run focused CLI tests**

Run: `pytest tests/test_cli.py tests/test_dual_circle_cli.py -q`
Expected: PASS.

### Task 5: Verify the minimum paper artifact set

**Files:**
- Verify only

- [ ] **Step 1: Run the targeted dual-circle test slice**

Run: `pytest tests/test_dual_circle_simulation.py tests/test_dual_circle_reconstruction.py tests/test_dual_circle_cli.py -q`
Expected: PASS.

- [ ] **Step 2: Run the full regression suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 3: Run the development-scale paper experiment**

Run: `scripts/run_validation_uv.sh --config configs/dual_circle_fastpaper.json`
Expected: exit code `0` and a summary JSON plus plot files under `outputs/dual_circle_fastpaper/`.

- [ ] **Step 4: Confirm artifacts exist**

Run: `find outputs/dual_circle_fastpaper -maxdepth 2 -type f | sort`
Expected: summary JSON and the expected plot files are present.

- [ ] **Step 5: Sanity-check the comparison outcome**

Run: `python3 - <<'PY'\nimport json\nfrom pathlib import Path\np = Path('outputs/dual_circle_fastpaper/summary.json')\nobj = json.loads(p.read_text())\nprint(sorted(obj.keys()))\nPY`
Expected: the summary contains both scenarios, both methods, and metric aggregates needed for the paper figures.
