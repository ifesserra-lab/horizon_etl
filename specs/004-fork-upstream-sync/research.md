# Research: Fork Upstream Synchronization

**Feature**: 004-fork-upstream-sync
**Date**: 2026-07-12
**Status**: Complete

## Research Tasks

### 1. Upstream Remote Configuration

**Question**: Is the upstream remote properly configured and accessible?

**Findings**:
- Upstream remote configured: `https://github.com/ifesserra-lab/horizon_etl.git`
- Origin remote: `https://github.com/henriqk0/horizon_etl.git`
- Current branch: `fix/merge-original` (planning branch)

**Decision**: Proceed with synchronization using configured upstream remote.

**Rationale**: Both remotes are properly configured and accessible.

### 2. Current Branch State Analysis

**Question**: What planning work exists on the current branch?

**Findings**:
- Branch contains planning commits for fork synchronization
- download.py exists at `src/flows/lattes/download.py`
- Planning artifacts in `specs/` directory

**Decision**: Current branch is the authoritative source for planning work.

**Rationale**: Per clarification Q1, the currently checked-out branch is authoritative.

### 3. download.py Protection Strategy

**Question**: How should download.py be protected during synchronization?

**Findings**:
- File location: `src/flows/lattes/download.py`
- Must never be overwritten with upstream version
- Local version takes absolute precedence

**Decision**: Use `git checkout --ours` for download.py conflicts.

**Rationale**: Per clarification Q4, download.py is a protected file with unconditional precedence.

### 4. Synchronization Strategy Selection

**Question**: Should merge or rebase be used?

**Findings**:
- Either strategy is acceptable (clarification Q2)
- Strategy should minimize conflicts
- Planning commits must remain logically intact

**Decision**: Evaluate both strategies and choose based on conflict analysis.

**Rationale**: The cleanest integration strategy will be selected during execution.

### 5. Conflict Resolution Priority

**Question**: What is the priority order for resolving conflicts?

**Findings**:
- Priority 1: Preserve intentional local work
- Priority 2: Incorporate compatible upstream improvements
- Priority 3: Avoid losing upstream fixes unless conflicting with deliberate decisions

**Decision**: Follow three-tier priority resolution.

**Rationale**: Per clarification Q3, conflicts must be resolved manually following this priority order.

### 6. Automatic vs Manual Resolution

**Question**: When can automatic resolution be used?

**Findings**:
- Automatic resolution allowed only when outcome is guaranteed
- Otherwise, manual resolution required

**Decision**: Default to manual resolution; use automatic only for non-conflicting changes.

**Rationale**: Per clarification Q9, automatic resolution is only allowed when guaranteed to satisfy rules.

### 7. Success Criteria Verification

**Question**: How will successful synchronization be verified?

**Findings**:
- Branch contains latest upstream history
- All planning work intact
- download.py identical to pre-sync state
- Repository ready for future implementation

**Decision**: Multi-point verification checklist.

**Rationale**: Per clarification Q7, these are the four criteria for success.

## Best Practices Identified

### Git Synchronization Best Practices

1. **Backup Before Sync**: Create a backup branch before starting synchronization
2. **Fetch First**: Always fetch upstream before attempting merge/rebase
3. **Clean Working Tree**: Ensure no uncommitted changes before synchronization
4. **Incremental Resolution**: Handle conflicts one at a time
5. **Verification**: Run tests after synchronization to catch issues early

### Conflict Resolution Best Practices

1. **Understand Intent**: Read commit messages to understand why changes were made
2. **Preserve History**: Keep meaningful commit history when possible
3. **Test After Resolution**: Verify changes don't break functionality
4. **Document Decisions**: Record why specific resolution choices were made

## Alternatives Considered

### Alternative 1: Rebase Only

**Description**: Always use rebase to maintain linear history.

**Pros**: Cleaner history, easier to understand.

**Cons**: Rewrites history, may complicate conflict resolution.

**Decision**: Not mandatory - evaluate based on situation.

### Alternative 2: Merge Only

**Description**: Always use merge to preserve complete history.

**Pros**: Preserves all history, safer for shared branches.

**Cons**: Creates merge commits, more complex history.

**Decision**: Not mandatory - evaluate based on situation.

### Alternative 3: Manual Cherry-Pick

**Description**: Manually select upstream commits to apply.

**Pros**: Maximum control over what gets integrated.

**Cons**: Time-consuming, may miss important changes.

**Decision**: Not recommended - too labor-intensive for full synchronization.

## Resolution Notes

All research questions have been resolved. The synchronization strategy will be determined during execution based on conflict analysis. The three-tier priority resolution approach will be followed for all conflicts. download.py protection is clearly defined with absolute precedence.
