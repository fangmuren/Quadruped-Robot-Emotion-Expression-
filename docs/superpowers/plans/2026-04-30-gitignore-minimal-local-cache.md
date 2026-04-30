# Minimal `.gitignore` Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the repository `.gitignore` for the approved narrow set of local artifacts by keeping the existing cache-directory rules, adding `.worktrees/` for project-local worktrees, and adding Python bytecode file patterns.

**Architecture:** This is a single-file change in the repository root `.gitignore`. Verification relies on `git check-ignore` against representative ignored and non-ignored paths so the change stays narrow: it covers the approved project-local worktree directory and Python bytecode artifacts without hiding source files, docs, or broader local tooling artifacts.

**Tech Stack:** Git ignore rules, Bash, Python bytecode artifacts

---

### Task 1: Update and verify root `.gitignore`

**Files:**
- Modify: `.gitignore:1-4`
- Reference: `docs/superpowers/specs/2026-04-30-gitignore-minimal-local-cache-design.md`
- Verify: `git check-ignore -v` against representative paths

- [ ] **Step 1: Confirm the current `.gitignore` contents**

```gitignore
__pycache__/
tests/__pycache__/
.pytest_cache/
```

- [ ] **Step 2: Run the pre-change ignore check that should fail**

Run: `git check-ignore -v ".worktrees/example/README" "scratch.pyc" "scratch.pyo"; test $? -ne 0`
Expected: no matching rule is reported for any of these paths, and the command exits non-zero

- [ ] **Step 3: Edit `.gitignore` with the minimal approved additions**

```gitignore
__pycache__/
tests/__pycache__/
.pytest_cache/
.worktrees/
*.pyc
*.pyo
```

- [ ] **Step 4: Run the post-change ignore check that should pass**

Run: `git check-ignore -v ".worktrees/example/README" "scratch.pyc" "scratch.pyo"`
Expected:
- output points to `.gitignore` rules for `.worktrees/`, `*.pyc`, and `*.pyo`
- command exits zero

- [ ] **Step 5: Run the regression check for files that must remain trackable**

Run: `git check-ignore -v "main.py" "模式对应图.png" "docs/superpowers/specs/2026-04-30-gitignore-minimal-local-cache-design.md"; test $? -ne 0`
Expected: no output, non-zero exit status, and none of these paths are ignored

- [ ] **Step 6: Review the diff**

Run: `git diff -- .gitignore`
Expected: the diff shows only the three added lines `.worktrees/`, `*.pyc`, and `*.pyo`

- [ ] **Step 7: Commit only if the user explicitly requests it**

```bash
git add .gitignore
git commit -m "chore: ignore Python bytecode artifacts"
```
