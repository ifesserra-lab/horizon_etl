# Tasks: Fork Upstream Synchronization

**Input**: Design documents from `/specs/004-fork-upstream-sync/`

**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: No automated tests - this is a git synchronization operation with manual validation

**Organization**: Tasks are grouped by user story to enable independent verification of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different operations, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths or git commands in descriptions

## Phase 1: Setup (Pre-Synchronization Preparation)

**Purpose**: Verify environment and create safety checkpoints before synchronization

- [ ] T001 Verify current branch is clean with no uncommitted changes using `git status`
- [ ] T002 Verify upstream remote is configured and accessible using `git remote -v`
- [ ] T003 Record pre-sync download.py hash using `sha256sum src/flows/lattes/download.py`
- [ ] T004 Record pre-sync planning commit count using `git rev-list --count HEAD`
- [ ] T005 Create backup branch using `git branch backup-pre-sync-$(date +%Y%m%d)`

**Checkpoint**: Environment verified and backup created - synchronization can proceed

---

## Phase 2: Foundational (Fetch Upstream References)

**Purpose**: Fetch latest upstream changes - blocking prerequisite for all user stories

**⚠️ CRITICAL**: No synchronization work can begin until upstream is fetched

- [ ] T006 Fetch all upstream changes using `git fetch upstream`

**Checkpoint**: Upstream fetched - synchronization can now proceed

---

## Phase 3: User Story 1 - Fetch and Update Upstream References (Priority: P1) 🎯 MVP

**Goal**: Ensure fork has the most recent upstream code available for synchronization

**Independent Test**: Verify upstream remote references are updated to latest commits

### Implementation for User Story 1

- [ ] T007 [US1] Verify upstream default branch reference updated using `git log --oneline upstream/main -1`
- [ ] T008 [US1] Confirm no local changes were made during fetch using `git status`

**Checkpoint**: Upstream references updated - fork knows about latest upstream state

---

## Phase 4: User Story 2 - Synchronize History While Preserving Planning Work (Priority: P1)

**Goal**: Integrate upstream changes without losing planning commits

**Independent Test**: Compare planning commit count before and after synchronization

### Implementation for User Story 2

- [ ] T009 [US2] Analyze potential conflicts using `git merge-tree` or `git rebase` dry-run
- [ ] T010 [US2] Choose synchronization strategy (merge or rebase) based on conflict analysis
- [ ] T011 [US2] Execute synchronization strategy (merge: `git merge upstream/main` OR rebase: `git rebase upstream/main`)
- [ ] T012 [US2] If conflicts occur, resolve manually following three-tier priority: (1) preserve local work, (2) incorporate compatible upstream, (3) avoid losing upstream fixes
- [ ] T013 [US2] Complete synchronization (merge commit or rebase continue)
- [ ] T014 [US2] Verify all planning commits preserved using `git rev-list --count HEAD`

**Checkpoint**: Upstream changes integrated - planning work intact

---

## Phase 5: User Story 3 - Protect download.py from Upstream Overwrites (Priority: P1)

**Goal**: Ensure download.py always takes precedence in conflicts

**Independent Test**: Verify download.py is byte-identical before and after synchronization

### Implementation for User Story 3

- [ ] T015 [US3] Check if download.py had conflicts during synchronization
- [ ] T016 [US3] If download.py conflicted, restore local version using `git checkout --ours src/flows/lattes/download.py`
- [ ] T017 [US3] If download.py conflicted, stage restored file using `git add src/flows/lattes/download.py`
- [ ] T018 [US3] Verify download.py hash matches pre-sync hash using `sha256sum src/flows/lattes/download.py`
- [ ] T019 [US3] If hash doesn't match, restore from backup using `git checkout backup-pre-sync-YYYYMMDD -- src/flows/lattes/download.py`

**Checkpoint**: download.py protected - local version preserved exactly

---

## Phase 6: User Story 4 - Incorporate Compatible Upstream Improvements (Priority: P2)

**Goal**: Integrate upstream enhancements that don't conflict with planning work

**Independent Test**: Verify compatible upstream changes are present in working branch

### Implementation for User Story 4

- [ ] T020 [US4] Review non-download.py file changes from upstream
- [ ] T021 [US4] For each conflicting non-download.py file, apply priority rules manually
- [ ] T022 [US4] Verify compatible upstream improvements are incorporated using `git diff HEAD~1 --stat`

**Checkpoint**: Upstream improvements integrated - fork stays current

---

## Phase 7: User Story 5 - Validate Repository Integrity After Sync (Priority: P2)

**Goal**: Verify repository is in valid state for continued implementation work

**Independent Test**: Run build and test commands to confirm repository integrity

### Implementation for User Story 5

- [ ] T023 [US5] Run CI checks using `make ci-check`
- [ ] T024 [US5] If CI fails, analyze and fix issues
- [ ] T025 [US5] Verify no planning artifacts were lost or modified using `git diff backup-pre-sync-YYYYMMDD -- specs/`
- [ ] T026 [US5] Verify upstream history is integrated using `git log --oneline -10`
- [ ] T027 [US5] Verify repository status is clean using `git status`

**Checkpoint**: Repository validated - ready for implementation work

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and cleanup

- [ ] T028 Delete backup branch if synchronization successful using `git branch -d backup-pre-sync-YYYYMMDD`
- [ ] T029 Document synchronization completion in commit message
- [ ] T030 Verify all success criteria from spec.md are met:
  - Zero planning commits lost
  - download.py byte-identical before/after
  - All compatible upstream improvements integrated
  - make ci-check passes
  - Repository ready for next implementation phase

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can proceed sequentially (recommended for git operations)
  - Some tasks within stories can run in parallel
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - Should run immediately after US2 to verify download.py protection
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Integrates with US2 but should be independently verifiable
- **User Story 5 (P2)**: Can start after Foundational (Phase 2) - Should run after US2-US4 to validate overall synchronization

### Within Each User Story

- Verify conditions before executing operations
- Execute git commands in correct sequence
- Validate results before proceeding to next task
- Document any issues encountered

### Parallel Opportunities

- Tasks within Setup phase (T001-T005) can run in parallel
- Tasks T007-T008 within US1 can run in parallel
- Tasks T015-T017 within US3 can run in parallel if download.py conflicted
- Tasks T023-T027 within US5 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Verify upstream references and local state simultaneously:
Task: "Verify upstream default branch reference updated using git log --oneline upstream/main -1"
Task: "Confirm no local changes were made during fetch using git status"
```

---

## Parallel Example: User Story 5

```bash
# Run validation checks simultaneously:
Task: "Run CI checks using make ci-check"
Task: "Verify no planning artifacts were lost or modified using git diff backup-pre-sync-YYYYMMDD -- specs/"
Task: "Verify upstream history is integrated using git log --oneline -10"
Task: "Verify repository status is clean using git status"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006)
3. Complete Phase 3: User Story 1 (T007-T008)
4. Complete Phase 4: User Story 2 (T009-T014)
5. Complete Phase 5: User Story 3 (T015-T019)
6. **STOP and VALIDATE**: Verify download.py protected and planning work intact
7. Proceed only if MVP validation passes

### Incremental Delivery

1. Complete Setup + Foundational → Environment ready
2. Add User Story 1 → Verify upstream fetched → Continue
3. Add User Story 2 → Verify synchronization complete → Continue
4. Add User Story 3 → Verify download.py protected → Continue (MVP!)
5. Add User Story 4 → Verify upstream improvements integrated → Continue
6. Add User Story 5 → Verify repository integrity → Complete

### Sequential Strategy (Recommended for Git Operations)

Git synchronization is inherently sequential - each operation builds on the previous state. The recommended approach is:

1. Complete all Setup tasks (T001-T005)
2. Complete Foundational task (T006)
3. Complete User Story 1 tasks (T007-T008)
4. Complete User Story 2 tasks (T009-T014)
5. Complete User Story 3 tasks (T015-T019)
6. Complete User Story 4 tasks (T020-T022)
7. Complete User Story 5 tasks (T023-T027)
8. Complete Polish tasks (T028-T030)

---

## Notes

- [P] tasks = different operations, no dependencies
- [Story] label maps task to specific user story for traceability
- Git operations should be executed sequentially for safety
- Always verify conditions before executing git commands
- Document any issues encountered during synchronization
- Stop at any checkpoint to validate progress
- Backup branch provides safety net for recovery if needed
- Total tasks: 30
- Parallel opportunities: Limited (git operations are sequential by nature)
- Recommended approach: Sequential execution with validation at each checkpoint
