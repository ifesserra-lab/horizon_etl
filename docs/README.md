# Horizon ETL - Map of Documentation

This directory contains all the governance, analysis, and design artifacts for the **Horizon ETL** project. The structure follows the project's **Agile Standards** for software development.

## 📂 Directory Structure

### 1. Project Governance (`/docs/1 - projeto/`)
Managed by the **Senior Project Manager**, this layer ensures strategic alignment and planning.
- **[PM1.0 SOW](1 - projeto/PM1.0-sow.md)**: Statement of Work and initial scope baseline.
- **[PM1.1 Mission](1 - projeto/PM1.1-mission_statement.md)**: Project mission and strategic objectives.
- **[PM1.2-1.8 Project Plan](1 - projeto/PM1.2-1.8-project_plan.md)**: Comprehensive master plan (Schedule, Risk, Quality).
- **[PM1.3 Release Plan](1 - projeto/PM1.3-release_plan.md)**: High-level roadmap and milestones.
- **[PM1.9 Status Reports](1 - projeto/)**: Iterative progress reports (Status Report 0, 1, etc.).
- **[PM1.10 Closure](1 - projeto/PM1.10-Project_closure_report.md)**: Formalities for project completion.

### 2. System Identification & Implementation (`/docs/2 - implementacao/`)
Technical analysis and design phase artifacts.
- **[SI.1 Requirements](2 - implementacao/SI1-2 - identification/SI1-Requisitos.md)**: Functional and non-functional requirements.
- **[SI.2 Analysis](2 - implementacao/SI1-2 - identification/SI2-Analise.md)**: Domain model, user flows, and business logic analysis.
- **[SI.3 Product Backlog](2 - implementacao/SI3 - initiation/SI.3-product_backlog_initiation.md)**: Centralized list of User Stories and Epics.
- **[SI.3 Design](2 - implementacao/SI3 - inception/diagramas/SI.3-design.md)**: Software architecture, component diagrams, and data model.
- **Construction Sprints**: Specific sprint backlogs and tracking located in `SI4-6 - construction-sprints/`.

### 3. General Tracking
- **[backlog.md](backlog.md)**: High-level dashboard for production releases and hierarchical item status.

### 4. Local Infrastructure
- **[docker-compose.yml](../docker-compose.yml)**: Orchestration for local Prefect Server and PostgreSQL.

---
> [!NOTE]
> All changes to these documents must be approved and reflected in the `task.md` of active features.
