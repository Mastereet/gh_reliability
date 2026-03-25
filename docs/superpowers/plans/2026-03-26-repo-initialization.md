# Repository Initialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Copy the required `AGENTS.md` into this repo and establish the minimum repository baseline for a Python experiment workspace.

**Architecture:** Keep current experiment code in place and initialize only the repository scaffold, docs, and tooling policy. Treat this as a non-behavioral repo-baseline task so verification can stay lightweight and safe.

**Tech Stack:** Python, `uv`, `pytest`, `ruff`, `pyright`, Markdown

---

### Task 1: Add workflow artifacts

**Files:**
- Create: `docs/superpowers/specs/2026-03-26-repo-initialization-design.md`
- Create: `docs/superpowers/plans/2026-03-26-repo-initialization.md`

- [ ] **Step 1: Write the design doc**

Write the design doc covering goals, constraints, non-goals, acceptance checks, reproducibility path, and rollback.

- [ ] **Step 2: Write the implementation plan**

Write the implementation plan with exact files and verification commands.

- [ ] **Step 3: Verify artifact paths exist**

Run: `find docs/superpowers -maxdepth 2 -type f | sort`
Expected: the spec and plan files are listed at the expected paths.

### Task 2: Copy repository instructions and baseline directories

**Files:**
- Create: `AGENTS.md`
- Create: `src/.gitkeep`
- Create: `scripts/.gitkeep`
- Create: `configs/.gitkeep`
- Create: `notebooks/.gitkeep`
- Create: `outputs/.gitkeep`
- Create: `docs/long-term-memory/repo/.gitkeep`
- Create: `short-term-memory/.gitkeep`

- [ ] **Step 1: Copy the upstream AGENTS file**

Run: `cp /home/master/codes/conicfront/AGENTS.md /home/master/codes/gh_reliability/AGENTS.md`
Expected: `AGENTS.md` exists at repo root.

- [ ] **Step 2: Create baseline directories**

Run: `mkdir -p docs/superpowers/specs docs/superpowers/plans docs/long-term-memory/repo short-term-memory src scripts configs notebooks outputs`
Expected: all directories exist.

- [ ] **Step 3: Keep empty directories trackable**

Create `.gitkeep` files in the empty baseline directories.

### Task 3: Add repo docs and Python tooling config

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `pyrightconfig.json`

- [ ] **Step 1: Write `.gitignore`**

Ignore Python caches, local virtualenvs, generated experiment outputs, and `short-term-memory/`.

- [ ] **Step 2: Write `README.md`**

Document current repo purpose, current layout, target layout, safe commands, and output location.

- [ ] **Step 3: Write Python tooling config**

Add a minimal `pyproject.toml` for `uv`, `pytest`, `ruff`, and project metadata, plus `pyrightconfig.json` for `.venv`.

- [ ] **Step 4: Verify config files are present**

Run: `ls README.md .gitignore pyproject.toml pyrightconfig.json`
Expected: all four files are listed.

### Task 4: Run safe verification

**Files:**
- Verify only

- [ ] **Step 1: Verify copied AGENTS file**

Run: `cmp -s AGENTS.md /home/master/codes/conicfront/AGENTS.md`
Expected: exit code `0`.

- [ ] **Step 2: Verify repo baseline files**

Run: `find . -maxdepth 2 \\( -name AGENTS.md -o -name README.md -o -name .gitignore -o -name pyproject.toml -o -name pyrightconfig.json \\) | sort`
Expected: the baseline files appear in the repo.

- [ ] **Step 3: Verify git status**

Run: `git status --short`
Expected: only expected initialization additions or pre-existing untracked project files appear.
