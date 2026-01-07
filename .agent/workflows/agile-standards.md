---
description: Enforce Agile & Project Management Standards for tasks
---

Follow this workflow ensuring all work adheres to "The Band Project" standards.

## 1. Project Governance (Senior PM Oversight)
This section enforces the **mandatory** maintenance of the Project Management (PM) documentation layer located in `docs/1 - projeto/`.
> [!IMPORTANT]
> **MANDATORY AND NON-NEGOTIABLE**: The following documents MUST be fully populated and approved by the Product Owner/Stakeholder **BEFORE** any development begins.

- **PM1.0 SOW (`PM1.0-sow.md`)**: Scope baseline and Statement of Work.
- **PM1.1 Mission (`PM1.1-mission_statement.md`)**: Strategic alignment.
- **PM1.2-1.8 Project Plan (`PM1.2-1.8-project_plan.md`)**: Master plan including WBS, Schedule, Resources, Communication, Risk, and Acceptance Criteria.
- **PM1.3 Release Plan (`PM1.3-release_plan.md`)**: High-level roadmap defining Releases.

**Ongoing Maintenance:**
- **PM1.9 Status Reports (`PM1.9-status_report_X.md`)**: Bi-weekly progress tracking mandatory for every sprint/iteration.
- **PM1.10 Closure (`PM1.10-Project_closure_report.md`)**: End-of-project formalities.

## 2. System Identification (Senior Analyst/Designer)
This section enforces the **mandatory** analysis phase before implementation, located in `docs/2 - implementacao/`.
> [!IMPORTANT]
> **MANDATORY AND NON-NEGOTIABLE**: The following documents MUST be fully populated and approved **BEFORE** any implementation.

- **SI.1 Requirements (`SI1-2 - identification/SI1-Requisitos.md`)**: Functional and Non-functional requirements, Stakeholders.
- **SI.2 Analysis (`SI1-2 - identification/SI2-Analise.md`)**: Domain understanding, User Flows, BPMN, Conceptual Model.
- **SI.3 Product Backlog (`SI3 - initiation/SI.3-product_backlog_initiation.md`)**: User Stories, Prioritization, Acceptance Criteria.
- **SI.3 Design (`SI3 - inception/diagramas/SI.3-design.md`)**: Software Architecture, Component Diagram, Data Model (Schema), API Contracts.

**Agent Responsibility (Analyst Interview):**
- The Agent **MUST** act as a **Senior Analyst**.
- If these documents are missing or incomplete, the Agent **MUST active question the User** to gather the necessary data.
- **NO Implementation** is allowed until these are populated.

## 3. Branching Strategy (GitFlow)
- **main**: Stable production branch. Restricted.
- **developing**: Integration branch for new work. Branched from `main`.
- **features**: Feature/Bugfix branches. Fork/Branch from `developing`.
    - Format: `feat/<name>`, `bugfix/issue-<id>`, `fix/<name>`.

## 4. Iteration Cadence & Reporting
- **Frequency**: 2 weeks.
- **Cadence**: 2 interactions per month.
    - **First Interaction**: Starts on the 1st day of the month.
    - **Second Interaction**: Starts on the 15th day of the month (Mean).
- **Status Reporting (MANDATORY)**:
    - **Trigger 1**: A new Status Report (`docs/1 - projeto/PM1.9-status_report_X.md`) MUST be generated at the start/end of each interaction.
    - **Trigger 2**: The Status Report MUST be updated **IMMEDIATELY** after a release is delivered, incorporating GitHub data (issues closed, PRs merged, exact version released).

## 5. Definition of Ready (DoR) Check
Before moving a task to "In Progress":
- [ ] **Project Initiation Check**:
    - [ ] Confirm `PM1.0`, `PM1.1`, `PM1.2-1.8`, and `PM1.3` in `docs/1 - projeto/` are fully populated and approved.
- [ ] **SI Artifacts Check**:
    - [ ] Confirm `SI.1`, `SI.2`, `SI.3 Backlog` and **`SI.3 Design`** in `docs/2 - implementacao/` are fully populated and approved.
- [ ] **Documentation First**:
    - [ ] Update `docs/*.md` (e.g., `requirements.md`, `sdd.md`) before creating the issue.
    - [ ] **Reference**: Description MUST link to docs (e.g., "Implement Req 1.1 as detailed in `SI1-Requisitos.md`").
- [ ] **Design Assessment (Mandatory)**:
    - [ ] **Question the User**: The Designer MUST question the user about architectural decisions if `SI.3 Design` is ambiguous.
    - [ ] **Structure Check**: Confirm implementation matches `src` folder structure defined in `SI.3 Design`.
- [ ] **Hierarchy Check**: Confirm strict hierarchy: `Epic -> User Story -> Task`.
- [ ] **Alignment Check**: ensure the Issue/User Story is aligned with **PM1.3 Release Plan**, **PM1.2 Scope** and **SI.1 Requirements**.
- [ ] **Milestone Mapping**: The Issue MUST be assigned to a GitHub Milestone that corresponds directly to a Release defined in `PM1.3 Release Plan`.
- [ ] **Governance**: Ensure work is associated with "The Band Project" ecosystem.
- [ ] **readiness**:
    - [ ] Clear Objective defined?
    - [ ] Acceptance Criteria defined?
    - [ ] Technical Plan ready?
- [ ] **GitHub Issue**:
    - [ ] **Draft**: Provide technical proposal/text to the user.
    - [ ] **Approval**: Mandatory user approval before proceeding.
    - [ ] **Create**: Create the issue on GitHub ONLY after approval.
        - [ ] **Fields Requirement (MANDATORY AND NON-NEGOTIABLE)**:
            - [ ] **Label**: Must be set (epic, us, task).
            - [ ] **Type**: Must be set (feature, bug, task).
            - [ ] **Milestone**: Must be set.
            - [ ] **Project**: Must be set to "The Band Project".
            - [ ] **Assignee**: Must be set to the logged-in user.
    - [ ] **Start**: Begin programming ONLY after issue creation. **MANDATORY AND NON-NEGOTIABLE**.

## 6. Artifact Maintenance
Maintain the following artifacts throughout the lifecycle:
- [ ] `docs/1 - projeto/*.md`: **MANDATORY**. Keep PM documents updated as described in Section 1.
- [ ] `docs/2 - implementacao/**/*.md`: **MANDATORY**. Keep SI documents (`SI.1`, `SI.2`, `SI.3 Backlog`, `SI.3 Design`) updated as described in Section 2.
- [ ] `task.md`: For detailed task tracking.
- [ ] `implementation_plan.md`: For technical planning and review.
    - [ ] **Test Plan**: MUST list all test cases based on requirements. **MANDATORY AND NON-NEGOTIABLE**.
- [ ] `docs/backlog.md`: Must include **Releases** section with:
    - PR Number & Link
    - Description
    - Commit SHA & Link
- [ ] **Synchronization (MANDATORY)**:
    - [ ] **Trigger**: Any update to `docs/2 - implementacao/SI3 - initiation/SI.3-product_backlog_initiation.md`.
    - [ ] **Action**: You MUST immediately update:
        - [ ] `task.md` (Operational tasks).
        - [ ] `docs/backlog.md` (Release status).
        - [ ] `PM1.3 Release Plan` (only if Milestones/Dates change).


## 7. Implementation Standards
- [ ] **TDD**: Implement the test cases defined in the plan BEFORE the implementation code. **MANDATORY AND NON-NEGOTIABLE**.
- [ ] **Style**: Code must pass `black`, `flake8`, `isort`.
- [ ] **Business Logic**: All business rules requirements must be satisfied and verified.
- [ ] **Observability**: **MANDATORY**. All critical actions and state changes MUST be logged (Info/Error) with context.
- [ ] **Design Patterns**: Apply the **Strategy Pattern** when multiple algorithms or behaviors are required for a specific task to ensure extensibility and reduce code duplication.

## 8. Pull Request Standards
- [ ] **Process**:
    - [ ] Create PR from feature branch targeting `developing`.
    - [ ] **Template**: Use `.github/pull_request_template.md`.
- [ ] **Content Requirements**:
    - [ ] **Related Issues**: List linked issues (e.g., `Closes #1`).
    - [ ] **Modifications**: Detailed list of technical changes.
    - [ ] **How to Test**: Clear steps for verification.


## 9. Release Strategy (CD)
- [ ] **Promotion**: `developing` -> `main`.
- [ ] **Trigger**: All tests passed on `developing`.
- [ ] **Milestone Association**: Every Release defined in `PM1.3` MUST have a corresponding GitHub Milestone.
- [ ] **Milestone Content**: The Milestone MUST contain one or more Epics, Tasks, or User Stories.
- [ ] **Process**:
    - [ ] Open Pull Request from `developing` to `main`.
    - [ ] Title Format: `release: <description>`.
    - [ ] No direct commits to `main` allowed.
        - [ ] **Versioning (MANDATORY)**:
            - [ ] **MUST** create a new version (git tag) whenever `developing` is merged to `main`.
            - [ ] **DO NOT** run `bump_version.py` locally (CI/CD handles this).
            - [ ] **Create Tag**: `git tag vX.Y.Z` (at end of each feature/fix/release).
            - [ ] **Update Latest**: `git tag -f latest` and `git push origin -f latest` (at end of each feature/fix/bug).
            - [ ] **Push Tag**: `git push origin vX.Y.Z`.
            - [ ] **CI/CD**: GitHub Action handles version bump & publish.
    - [ ] **Post-Release Reporting**: Update `PM1.9 Status Report` with release details (version, date, items delivered).

## 10. Merge Standards
- [ ] **Conflict Free**: PR can be merged if there are no conflicts.
- [ ] **Automation**: If the CI pipeline (`.github/workflows/ci.yml`) passes, the PR MUST be merged and related issues closed automatically. **MANDATORY AND NON-NEGOTIABLE**.
- [ ] **Cleanup**: 
    - [ ] **Remote**: Delete the feature/bugfix branch from GitHub immediately after the PR is merged.
    - [ ] **Local**: Delete the local branch to keep the workspace clean.
    - [ ] **Sync**: Run `git remote prune origin` to synchronize remote branch tracking.

## 11. Definition of Done (DoD)
- [ ] **Verification**:
    - [ ] Test suite passing.
    - [ ] Linting checks passing.
- [ ] **Documentation**:
    - [ ] Update Google-style docstrings.
    - [ ] Update relevant `docs/*.md` files.
    - [ ] **PM Updates**: Check if `PM1.3 Release Plan` or `PM1.9 Status Report` needs updates.
    - [ ] Update/Create `walkthrough.md`.
- [ ] **Closure**:
    - [ ] Close related GitHub Issues.
    - [ ] Update hierarchical status in `docs/backlog.md`.
    - [ ] **Cleanup**: Confirm that all related feature/fix/bug branches (remote and local) have been deleted.
    - [ ] **Versioning**: Tag the release and update `latest` tag (see Section 7) after Feature/Fix/Bug closure.

## 12. Tooling Standards
- [ ] **GitHub Interaction**:
    - [ ] **MUST USE** GitHub MCP Tools (`github-mcp-server`) for:
        - Creating/Merging Pull Requests.
        - Creating/Updating Issues.
        - Managing Branches (Remote).
        - Releases.
    - [ ] **AVOID** `git` CLI commands where MCP alternatives exist.
    - [ ] **GitHub CLI (`gh`) Usage**:
        - [ ] **Initial Setup (MANDATORY)**: Always check for and create the mandatory labels (`epic`, `us`, `task`) if they do not exist when starting a project.
        - [ ] **Release Milestones**: Always use `gh` or `gh api` to create all milestones defined in `PM1.3 Release Plan` (including titles, due dates, and descriptions) immediately after the plan is approved.
    - [ ] **Legacy Git**: Use `git` CLI only for local workspace synchronization (checkout/pull) if MCP equivalent is unavailable.
