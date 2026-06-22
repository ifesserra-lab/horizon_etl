---
name: "lint-python"
description: "Lint and auto-format Python code following CI rules exactly (black, isort, flake8)."
compatibility: "Requires dev dependencies (black==24.10.0, isort==5.13.2, flake8) and git."
metadata:
  source: ".github/workflows/ci.yml"
---

## CI Lint Workflow

The CI (`.github/workflows/ci.yml`) runs these steps:

### 1. Determine base SHA
```bash
if [ "$GITHUB_EVENT_NAME" = "pull_request" ]; then
  BASE_SHA="${{ github.event.pull_request.base.sha }}"
else
  BASE_SHA="${{ github.event.before }}"
fi
if ! git rev-parse --verify "$BASE_SHA" >/dev/null 2>&1 || echo "$BASE_SHA" | grep -Eq '^0+$'; then
  BASE_SHA="HEAD~1"
fi
```

### 2. Black + isort on changed files only
```bash
git diff --name-only -z --diff-filter=ACMRT "$BASE_SHA"...HEAD -- '*.py' > changed-python-files.txt
if [ -s changed-python-files.txt ]; then
  xargs -0 black --check < changed-python-files.txt
  xargs -0 isort --check < changed-python-files.txt
fi
```

### 3. Flake8 on ALL files
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

## Commands to match CI

### Check only files changed since `main`
```bash
BASE_SHA=$(git merge-base HEAD main)
git diff --name-only -z --diff-filter=ACMRT "$BASE_SHA" -- '*.py' > .changed-py-files
if [ -s .changed-py-files ]; then
  xargs -0 black --check < .changed-py-files
  xargs -0 isort --check < .changed-py-files
fi
rm -f .changed-py-files
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

### Fix formatting on all files
```bash
black src tests scripts app.py
isort src tests scripts app.py
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

### Check formatting on all files (without fixing)
```bash
black --check src tests scripts app.py
isort --check src tests scripts app.py
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

## Config

| Tool     | Source          | Key settings                                      |
|----------|-----------------|---------------------------------------------------|
| **black**  | `pyproject.toml` | line-length=88, target-version=py312              |
| **isort**  | `pyproject.toml` | profile=black, line_length=88                     |
| **flake8** | `.flake8`        | max-line-length=88, ignore=E203,E501,W503,E125    |

## Before committing

Always run all three checks. If any fail, fix and re-check.
