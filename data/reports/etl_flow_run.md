# Relatorio de Execucao do ETL

Inicio: **2026-03-30T14:15:36.527541**
Fim: **2026-03-30T15:14:00.450633**

## Etapas

### sigpesq_research_groups

- Status: **success**
- Origem: **sigpesq_research_group**
- Duracao: **27.33s**
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
- Duracao: **17.29s**
- Tracking run id: **2**
- Arquivos de origem: **1**

#### Quantidade Extraida

- `research_projects_rows`: **66**

#### Entidades Salvas

| Entidade | Antes | Depois | Delta |
| --- | --- | --- | --- |
| persons | 449 | 681 | 232 |
| researchers | 449 | 502 | 53 |
| initiative_types | 0 | 1 | 1 |
| initiatives | 0 | 62 | 62 |
| teams | 338 | 401 | 63 |
| team_members | 507 | 997 | 490 |
| research_groups | 338 | 339 | 1 |
| knowledge_areas | 51 | 287 | 236 |
| researcher_knowledge_areas | 0 | 953 | 953 |
| initiative_teams | 0 | 112 | 112 |

### sigpesq_advisorships

- Status: **success**
- Origem: **sigpesq_advisorships**
- Duracao: **381.17s**
- Tracking run id: **3**
- Arquivos de origem: **22**

#### Quantidade Extraida

- `advisorship_files`: **22**
- `advisorship_rows_total`: **2226**
- `Relatorio_29_03_2026.xlsx`: **114**
- `Relatorio_30_03_2026.xlsx`: **114**

#### Entidades Salvas

| Entidade | Antes | Depois | Delta |
| --- | --- | --- | --- |
| persons | 681 | 947 | 266 |
| person_emails | 449 | 715 | 266 |
| organizations | 1 | 5 | 4 |
| initiative_types | 1 | 2 | 1 |
| initiatives | 62 | 711 | 649 |
| advisorships | 0 | 519 | 519 |
| fellowships | 0 | 9 | 9 |
| teams | 401 | 1045 | 644 |
| team_members | 997 | 2965 | 1968 |
| initiative_teams | 112 | 761 | 649 |

### lattes_projects

- Status: **success**
- Origem: **lattes_projects**
- Duracao: **80.49s**
- Tracking run id: **4**
- Arquivos de origem: **15**

#### Quantidade Extraida

- `lattes_files`: **15**
- `projects_total`: **204**
- `articles_total`: **791**
- `educations_total`: **58**

#### Entidades Salvas

| Entidade | Antes | Depois | Delta |
| --- | --- | --- | --- |
| persons | 947 | 1251 | 304 |
| researchers | 502 | 544 | 42 |
| organizations | 5 | 27 | 22 |
| initiatives | 711 | 885 | 174 |
| articles | 0 | 660 | 660 |
| article_authors | 0 | 782 | 782 |
| academic_educations | 0 | 58 | 58 |
| teams | 1045 | 1206 | 161 |
| team_members | 2965 | 3513 | 548 |
| initiative_teams | 761 | 935 | 174 |

### lattes_advisorships

- Status: **success**
- Origem: **lattes_advisorships**
- Duracao: **134.44s**
- Tracking run id: **5**
- Arquivos de origem: **15**

#### Quantidade Extraida

- `lattes_files`: **15**
- `advisorships_total`: **647**

#### Entidades Salvas

| Entidade | Antes | Depois | Delta |
| --- | --- | --- | --- |
| persons | 1251 | 1631 | 380 |
| initiatives | 885 | 1410 | 525 |
| advisorships | 519 | 1044 | 525 |
| teams | 1206 | 1703 | 497 |
| team_members | 3513 | 4736 | 1223 |
| initiative_teams | 935 | 1460 | 525 |

### cnpq_sync

- Status: **success**
- Origem: **cnpq_sync**
- Duracao: **2831.86s**
- Tracking run id: **6**

#### Quantidade Extraida

- `groups_to_sync`: **337**
- `campus_name`: **all**

#### Entidades Salvas

| Entidade | Antes | Depois | Delta |
| --- | --- | --- | --- |
| persons | 1631 | 7460 | 5829 |
| researchers | 544 | 6373 | 5829 |
| team_members | 4736 | 12420 | 7684 |
| knowledge_areas | 287 | 1464 | 1177 |

## Estado Final

| Check | Quantidade |
| --- | --- |
| persons_by_canonical_name | 258 |
| teams_by_canonical_name | 0 |
| knowledge_areas_by_canonical_name | 8 |
| person_emails_by_lower_email | 0 |
| organizations_by_name | 0 |
| organizational_units_by_name_org | 0 |
| roles_by_name | 0 |
| initiative_types_by_name | 0 |

## Tracking Summary

| Tabela | Quantidade |
| --- | --- |
| ingestion_runs | 6 |
| source_records | 13556 |
| entity_matches | 13415 |
| attribute_assertions | 58947 |
| entity_change_logs | 15625 |

### Ultimos Tracking Runs

| id | source_system | flow_name | status | started_at | finished_at |
| --- | --- | --- | --- | --- | --- |
| 6 | cnpq_sync | cnpq_sync | success | 2026-03-30 17:26:17 | 2026-03-30 18:13:29.640468 |
| 5 | lattes_advisorships | lattes_advisorships | success | 2026-03-30 17:24:03 | 2026-03-30 17:26:17.789404 |
| 4 | lattes_projects | lattes_projects | success | 2026-03-30 17:22:42 | 2026-03-30 17:24:03.325938 |
| 3 | sigpesq_advisorships | sigpesq_advisorships | success | 2026-03-30 17:16:21 | 2026-03-30 17:22:42.784496 |
| 2 | sigpesq_research_projects | sigpesq_projects | success | 2026-03-30 17:16:03 | 2026-03-30 17:16:21.228063 |
| 1 | sigpesq_research_group | sigpesq_research_groups | success | 2026-03-30 17:15:36 | 2026-03-30 17:16:03.920000 |
