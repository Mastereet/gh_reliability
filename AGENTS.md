# AGENTS.md

## Mission

- Work like a disciplined senior Python engineer and experiment builder.
- Default to the Superpowers workflow: design first -> plan -> execute in small steps -> verify -> review -> deliver.
- Treat this repository as a Python experiment workspace. Optimize for reproducibility, safe testing, and promotion of stable logic out of notebooks.

## Default Repository Shape

When creating or reorganizing content in this repo, prefer:

- `src/` for reusable Python packages and modules
- `scripts/` for reproducible experiment entrypoints
- `configs/` for experiment configuration files
- `tests/` for unit, integration, and smoke checks
- `notebooks/` for exploration and visualization only
- `docs/` for specs, method notes, and experiment records
- `outputs/` or `artifacts/` for generated results; do not treat generated artifacts as source by default

If the repo later establishes a different structure, follow the local convention already in use.

## Superpowers Workflow (MANDATORY for non-trivial changes)

Trigger this workflow when:

- adding a feature, refactoring, changing behavior, implementing a method from a paper, restructuring experiment code, or fixing a non-trivial bug.

Workflow (must follow this order):

0) Task Entry (Superpowers):
   - Apply `using-superpowers` before any other response, exploration, question, or edit.
   - Use it to decide which additional skills are mandatory for the task.
   - Repo instructions in this file override generic skill defaults when they conflict.
1) Idea:
   - Capture the problem statement, target outcome, constraints, scope boundary, and reproducibility expectation.
2) Brainstorming (Superpowers):
   - Produce a short spec covering goals, constraints, non-goals, acceptance checks, reproducibility path, and risks/rollback.
   - Propose 1-3 options, choose one, and justify the trade-off.
   - If the task begins from a paper, method section, equations, pseudocode, or training recipe, also apply `theory-to-code-spec` before implementation.
   - Output checkpoint: Design Confirmed.
3) Writing Plans (Superpowers):
   - Write an implementation plan doc to the repo (see "Artifacts" below).
   - Plan must be taskized into small steps; each step includes:
     - files to touch
     - commands to run
     - expected result or acceptance
   - For complex, research-heavy, or multi-phase experiment work, also apply `planning-with-files` and keep the repo-specific planning-memory files in sync during execution.
   - Output checkpoint: Implementation Plan.
4) Executing Plans (Superpowers):
   - Before isolated feature work or separate workspace execution, apply `using-git-worktrees` if the repo is git-backed and the task is not explicitly staying in the current workspace.
   - For feature work, bug fixes, refactors, or behavior changes, apply `test-driven-development` unless the edit is a tiny mechanical change or the user explicitly waives TDD.
   - Before testing or debugging, apply `testing-safe-protocol`.
   - Use `writing-python` before editing Python modules or scripts.
   - Use `uv` when package management, virtual environments, Python versions, or Python tooling choices are in scope.
   - Notebook work must follow the Notebook Promotion Gate below.
   - For each task, implement plus run the relevant verification commands from the plan step.
   - Output checkpoint: Implementation + Verification Slice.
5) Debugging (if needed):
   - If any test, smoke check, or experiment verification fails, use `systematic-debugging` before applying fixes.
   - Reproduce -> isolate root cause -> apply the minimal fix -> re-run the failed check.
   - If multiple failures are independent and delegation is explicitly allowed, use `dispatching-parallel-agents` to investigate them in parallel.
   - Output checkpoint: Fix Bugs.
6) Verification:
   - Use `verification-before-completion` and execute the full relevant quality gates.
   - For experiment tasks, start with the smallest safe smoke run, then escalate only when needed.
   - Output checkpoint: Quality Gate.
7) Finish:
   - If review feedback arrives from the user or a reviewer, apply `receiving-code-review` before implementing suggestions.
   - Request final review with `requesting-code-review` when review tooling or delegated review is available.
   - Before any `git add` or `git commit`, apply `committer`.
   - Complete delivery using `finishing-a-development-branch` when branch or merge workflow exists.
   - Output checkpoint: Merge / Deliver.

If a user explicitly requests skipping planning, you may do it only for tiny mechanical edits or trivial documentation wording changes.

## Artifacts

For non-trivial work, prefer these repo-local workflow artifacts:

- Spec: `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Plan: `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
- Local short-term memory when `planning-with-files` is used in this repo:
  - `short-term-memory/task_plan.current.md`
  - `short-term-memory/findings.current.md`
  - `short-term-memory/progress.current.md`
  - `short-term-memory/task_plan.history.md`
  - `short-term-memory/findings.history.md`
  - `short-term-memory/progress.history.md`
  - Keep these files inside the current workspace only.
  - Treat `*.current.md` as the active task working set.
  - Treat `*.history.md` as append-only short-term workspace history.
  - If a generic skill or template creates repo-root `task_plan.md`, `findings.md`, or `progress.md`, move or copy the active contents into the matching `*.current.md` files immediately and continue using `short-term-memory/` as the canonical location.
  - Keep `short-term-memory/` ignored by git and do not commit it.
- Long-term planning memory:
  - `docs/long-term-memory/<scope>/task_plan.md`
  - `docs/long-term-memory/<scope>/findings.md`
  - `docs/long-term-memory/<scope>/progress.md`
  - `docs/long-term-memory/cross-scope/<name>/task_plan.md`
  - `docs/long-term-memory/cross-scope/<name>/findings.md`
  - `docs/long-term-memory/cross-scope/<name>/progress.md`
  - `docs/long-term-memory/repo/task_plan.md`
  - `docs/long-term-memory/repo/findings.md`
  - `docs/long-term-memory/repo/progress.md`
  - Use `<scope>` for a single experiment, script, module, config family, or notebook-owned line of work.
  - Use `cross-scope/<name>` for work that spans multiple areas without one clear owner.
  - Use `repo` for repo-wide tooling, workflow, environment, CI, or documentation tasks.
  - If the target scope directory or any long-term memory files do not exist yet, create them before appending archive content.
- Planning-memory lifecycle:
  - During active work, write the current task into `short-term-memory/*.current.md`.
  - At task completion, compress `task_plan.current.md` and `findings.current.md`, then append those refined entries to the corresponding `*.history.md` files in chronological order.
  - At task completion, append `progress.current.md` to `progress.history.md` in chronological order without compression.
  - After a task has been folded into short-term history, the `*.current.md` files may be reset or overwritten for the next task.
  - Before any workspace destruction, worktree deletion, or equivalent cleanup, archive the workspace-local `short-term-memory/*.history.md` files to the correct long-term memory target.
  - `task_plan.history.md` and `findings.history.md` should be appended to long-term memory as compressed entries.
  - `progress.history.md` should be appended to long-term memory as a raw chronological log.

## Repo-Relevant Skill Coverage (Hard)

For routine development in this repo, the following skills are considered in scope and MUST be applied when their trigger conditions match.

### Task-entry skill

- `using-superpowers` is mandatory at task start.

### Core workflow skills

- `brainstorming`
- `writing-plans`
- `executing-plans`
- `subagent-driven-development` when delegation is explicitly allowed
- `systematic-debugging`
- `verification-before-completion`
- `requesting-code-review` when review tooling or delegated review is available
- `finishing-a-development-branch`

### Python and experiment skills

- `writing-python` before editing Python source, scripts, or Python-based experiment utilities.
- `uv` when package management, virtual environments, Python version selection, or Python tooling setup are involved.
- `testing-safe-protocol` before running tests, smoke checks, debug scripts, or local servers that could have side effects.
- `theory-to-code-spec` before implementing from papers, equations, pseudocode, algorithm boxes, method sections, or training recipes.
- `planning-with-files` for complex, research-heavy, long-running, or multi-phase experiment tasks.
- `installing-dependencies` before any dependency or tool installation command.
- `setup-fresh-project` when initializing the repo, creating the base project layout, or establishing the first Python tooling/configuration baseline.
- `committer` before any `git add` or `git commit`.
- `defining-requirements` when the user goal is still mostly a research intent or desired outcome and the task is primarily about turning that into concrete requirements.

### Conditional planning and execution skills

- `using-git-worktrees` before isolated feature work in a git-backed repo.
- `test-driven-development` for features, bug fixes, refactors, or behavior changes before production code edits.
- `dispatching-parallel-agents` only for 2+ independent tasks or failures that can safely proceed in parallel and only when delegation is explicitly allowed.
- `receiving-code-review` before implementing review feedback, especially when suggestions are broad, ambiguous, or technically questionable.
- `cli-creator` when designing a new CLI surface for experiment entrypoints, batch runners, reporting tools, or repo utilities.
- `cli-guideline` when implementing or reviewing a user-facing CLI in Python, Bash, JS/TS, or Go.

## Mandatory Pre-Edit Checklist (Hard)

Before any non-trivial change under `src/`, `scripts/`, `tests/`, `configs/`, or `notebooks/`, the agent MUST complete this checklist before the first edit:

1. Explicitly state in commentary:
   - the resolved workspace path
   - whether the workspace is a git repo or a plain directory
   - the primary execution path being changed (module, script, notebook, or config)
2. Identify the companion artifacts that must stay in sync:
   - tests or smoke checks
   - configs
   - docs or experiment notes
   - output or artifact location if the task generates results
3. If the task is paper- or method-driven, explicitly state that `theory-to-code-spec` is being applied.
4. If the task will run tests, debugging commands, or local servers, explicitly state that `testing-safe-protocol` is being applied.

Blocking rule:

- If the agent has not explicitly named these items in commentary, it MUST NOT start editing implementation files yet.

## Mandatory Experiment Reproducibility Gate (Hard)

Before any non-trivial experiment implementation, the agent MUST explicitly state in commentary:

- the canonical entrypoint to reproduce the work
- where the parameters or config will live
- how the work will be validated
- where generated outputs will go

Blocking rule:

- If reproducibility is not named up front, the task is not ready for implementation.

## Notebook Promotion Gate (Hard)

- `notebooks/` are for exploration, visualization, debugging, and temporary analysis.
- Reusable logic must not live only in notebook cells. Stable preprocessing, model code, metrics, evaluation loops, and result aggregation belong in `src/` or `scripts/`.
- Stable experiment parameters must not exist only as notebook-local constants. Promote them to config files, script arguments, or reusable modules.
- If a notebook is the first place where an idea is explored, the task is not complete until the stable parts have a canonical script/module/config path.
- Notebook output alone is not verification evidence for completion unless the task is explicitly notebook-only and the user agrees.

## Mandatory Dependency and Environment Gate (Hard)

- Apply `installing-dependencies` before any install command.
- Prefer `uv` with a project-local `.venv` for Python environments.
- Do not run global or user-level Python installs such as `pip install`, `pip install --user`, or `uv tool install` without explicit user approval when they write outside the project.
- If a required runtime or system tool is missing, ask the user to install it or approve the install rather than mutating the host system silently.
- If Python version or tooling policy changes, document the decision in repo docs such as `README.md` or a relevant file under `docs/`.

## Mandatory Safe Testing Gate (Hard)

- Before testing, debugging, smoke runs, or starting a local server, apply `testing-safe-protocol`.
- Default test pyramid: unit -> integration with controlled local substitutes -> heavier end-to-end or experiment runs only when necessary.
- No outbound network, real credentials, destructive database operations, or writes outside the project unless the user explicitly authorizes them.
- Local servers must bind to `127.0.0.1` or `localhost`, use a high unprivileged port, and be shut down after the test.
- Do not claim success from reasoning alone; report the exact verification command and what it proved.

## Mandatory Theory-to-Code Gate (Hard)

If a task originates from a paper, derivation, method section, equation set, pseudocode, benchmark protocol, or training recipe:

- apply `theory-to-code-spec` before editing code
- identify the method archetype and the missing closure items
- do not silently invent unresolved details
- surface any open assumptions or implementation gaps before coding

## Verification Expectations

- For library and script changes, prefer unit tests plus the smallest useful smoke check.
- For experiment changes, verify the smallest reproducible run first before scaling up.
- Before claiming completion, run the actual verification command in the current session.
- If you cannot run the full experiment because data, time, hardware, or permissions are missing, say exactly what you did verify and what remains unverified.

## Workspace Locality Constraints (Hard)

- Resolve the active workspace path from the runtime-provided current directory or `pwd`.
- Treat that resolved path as the execution boundary for the task.
- You may read files outside the repo as read-only reference, but do not modify them.
- If the repo later uses git worktrees, do not edit sibling worktrees from the current workspace unless the user explicitly asks for that operation.
- Before destroying a workspace, deleting a worktree, or otherwise cleaning up a workspace that may discard planning memory, first fold any active `short-term-memory/*.current.md` files into the corresponding `*.history.md` files and then archive that short-term history to the correct long-term memory target.

## Rules (Hard)

- Prefer minimal, incremental changes unless the user explicitly asks for a broad refactor.
- Ask only when required by ambiguity, safety, or destructive consequences.
- Favor deterministic experiments: set or surface seeds where meaningful, isolate config, and avoid hidden global state.
- Generated outputs, caches, checkpoints, logs, and executed notebook artifacts should usually not be committed unless the user explicitly requests them.
