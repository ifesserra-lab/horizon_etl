# ETL Flow Run

Fonte canonica: `data/reports/etl_flow_run.md`

Este arquivo abaixo representa um snapshot versionado do report de execucao do ETL.

---

# Relatorio de Execucao do ETL

Inicio: **2026-03-29T11:31:26.271857**
Fim: **2026-03-29T11:36:55.106711**

## Etapas

### sigpesq_research_groups

- Status: **success**
- Origem: **sigpesq_research_group**
- Duracao: **25.22s**
- Tracking run id: **1**
- Arquivos de origem: **1**

#### Quantidade Extraida

- `research_groups_rows`: **339**

#### Entidades Salvas

| Entidade | Antes | Depois | Delta |
| --- | --- | --- | --- |
| persons | 0 | 449 | 449 |
| researchers | 0 | 449 | 449 |
| person_emails | 0 | 449 | 449 |
| organizational_units | 0 | 23 | 23 |
| teams | 0 | 338 | 338 |
| team_members | 0 | 507 | 507 |
| research_groups | 0 | 338 | 338 |
| knowledge_areas | 0 | 51 | 51 |

### sigpesq_projects

- Status: **success**
- Origem: **sigpesq_research_projects**
- Duracao: **16.15s**
- Tracking run id: **2**
- Arquivos de origem: **1**

#### Quantidade Extraida

- `research_projects_rows`: **66**

#### Entidades Salvas

| Entidade | Antes | Depois | Delta |
| --- | --- | --- | --- |
| persons | 449 | 680 | 231 |
| researchers | 449 | 502 | 53 |
| initiative_types | 0 | 1 | 1 |
| initiatives | 0 | 62 | 62 |
| teams | 338 | 401 | 63 |
| team_members | 507 | 996 | 489 |
| research_groups | 338 | 339 | 1 |
| knowledge_areas | 51 | 287 | 236 |
| researcher_knowledge_areas | 0 | 953 | 953 |
| initiative_teams | 0 | 112 | 112 |

### sigpesq_advisorships

- Status: **success**
- Origem: **sigpesq_advisorships**
- Duracao: **286.66s**
- Tracking run id: **3**
- Arquivos de origem: **22**

#### Quantidade Extraida

- `advisorship_files`: **22**
- `advisorship_rows_total`: **2223**
- `Relatorio_23_03_2026.xlsx`: **113**
- `Relatorio_24_03_2026.xlsx`: **113**

#### Entidades Salvas

| Entidade | Antes | Depois | Delta |
| --- | --- | --- | --- |
| persons | 680 | 946 | 266 |
| person_emails | 449 | 715 | 266 |
| organizations | 1 | 5 | 4 |
| initiative_types | 1 | 2 | 1 |
| initiatives | 62 | 694 | 632 |
| advisorships | 0 | 502 | 502 |
| fellowships | 0 | 9 | 9 |
| teams | 401 | 1028 | 627 |
| team_members | 996 | 2916 | 1920 |
| initiative_teams | 112 | 744 | 632 |

## Estado Final

| Check | Quantidade |
| --- | --- |
| persons_by_canonical_name | 0 |
| teams_by_canonical_name | 0 |
| knowledge_areas_by_canonical_name | 0 |
| person_emails_by_lower_email | 0 |
| organizations_by_name | 0 |
| organizational_units_by_name_org | 0 |
| roles_by_name | 0 |
| initiative_types_by_name | 0 |

## Tracking Summary

| Tabela | Quantidade |
| --- | --- |
| ingestion_runs | 3 |
| source_records | 1040 |
| entity_matches | 1039 |
| attribute_assertions | 7298 |
| entity_change_logs | 1721 |

### Ultimos Tracking Runs

| id | source_system | flow_name | status | started_at | finished_at |
| --- | --- | --- | --- | --- | --- |
| 3 | sigpesq_advisorships | sigpesq_advisorships | running | 2026-03-29 14:32:08 | None |
| 2 | sigpesq_research_projects | sigpesq_projects | success | 2026-03-29 14:31:51 | 2026-03-29 14:32:07.757167 |
| 1 | sigpesq_research_group | sigpesq_research_groups | success | 2026-03-29 14:31:26 | 2026-03-29 14:31:51.605842 |
