# Quickstart: Fork Upstream Synchronization

**Feature**: 004-fork-upstream-sync
**Date**: 2026-07-12

## Prerequisites

- Git installed and configured
- Upstream remote accessible (`https://github.com/ifesserra-lab/horizon_etl.git`)
- Current branch clean (no uncommitted changes)
- Make and build tools available for validation

## Pre-Synchronization Validation

### 1. Verify Current State

```bash
# Check current branch
git branch --show-current

# Verify upstream remote
git remote -v

# Ensure clean working tree
git status

# Record pre-sync download.py hash
sha256sum src/flows/lattes/download.py
```

### 2. Backup Current State

```bash
# Create backup branch
git branch backup-pre-sync-$(date +%Y%m%d)

# Record planning commit count
git rev-list --count HEAD
```

## Synchronization Execution

### Option A: Merge Strategy

```bash
# Fetch upstream changes
git fetch upstream

# Merge upstream default branch
git merge upstream/main --no-edit

# Resolve any conflicts (if they occur)
# For download.py conflicts:
git checkout --ours src/flows/lattes/download.py
git add src/flows/lattes/download.py

# For other files:
# Manual resolution following priority rules
# Then add resolved files
git add <resolved-files>

# Complete merge
git commit
```

### Option B: Rebase Strategy

```bash
# Fetch upstream changes
git fetch upstream

# Rebase current branch onto upstream
git rebase upstream/main

# Resolve any conflicts (if they occur)
# For download.py conflicts:
git checkout --ours src/flows/lattes/download.py
git add src/flows/lattes/download.py

# For other files:
# Manual resolution following priority rules
# Then add resolved files
git add <resolved-files>

# Continue rebase
git rebase --continue
```

## Post-Synchronization Validation

### 1. Verify Integrity

```bash
# Verify planning commits preserved
git rev-list --count HEAD

# Verify download.py unchanged
sha256sum src/flows/lattes/download.py

# Compare with pre-sync hash
# Should match exactly
```

### 2. Run Build & Tests

```bash
# Run CI checks (includes linting, formatting, type checking, tests)
make ci-check
```

### 3. Verify Repository State

```bash
# Check git status
git status

# Verify upstream history integrated
git log --oneline -10
```

## Expected Outcomes

- **Planning commits**: All preserved (count should match or exceed pre-sync count)
- **download.py**: Byte-identical to pre-sync version
- **Upstream changes**: Integrated where compatible
- **Build status**: make ci-check passes
- **Repository**: Ready for implementation work

## Troubleshooting

### download.py Modified

If download.py was accidentally modified during sync:

```bash
# Restore from backup
git checkout backup-pre-sync-YYYYMMDD -- src/flows/lattes/download.py

# Verify restoration
sha256sum src/flows/lattes/download.py
```

### Planning Commits Lost

If planning commits appear missing:

```bash
# Check reflog for lost commits
git reflog

# Recover if needed
git cherry-pick <commit-hash>
```

### Build Fails After Sync

If make ci-check fails:

```bash
# Identify failing checks
make ci-check 2>&1 | head -50

# Fix issues per error messages
# Re-run validation
make ci-check
```

## Validation Checklist

- [ ] Pre-sync backup created
- [ ] download.py hash recorded before sync
- [ ] Upstream fetched successfully
- [ ] Synchronization completed (merge or rebase)
- [ ] download.py hash verified unchanged
- [ ] Planning commit count verified
- [ ] make ci-check passes
- [ ] Repository ready for next phase
