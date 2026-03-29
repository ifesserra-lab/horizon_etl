# ETL Load Report

Fonte canonica: `data/reports/etl_load_report.md`

Este arquivo abaixo representa um snapshot versionado do report de reconciliacao do ETL.

---

# Relatorio ETL

Gerado em: **2026-03-23T23:05:26.925209**

## Resumo Executivo

- Duplicados estruturais auditados: **0**
- Artigos faltando na reconciliacao Lattes: **47**
- Formacoes faltando na reconciliacao Lattes: **7**
- Orientacoes faltando na reconciliacao Lattes: **150**
- Projetos faltando na reconciliacao Lattes: **7**
- Pesquisadores sem resume: **6.343**
- Pesquisadores sem CNPq URL: **6.343**

## Inventario

- Arquivos Lattes: **15**
- Arquivos fonte SigPesq: **13**

| Entidade | Quantidade |
| --- | --- |
| persons | 7.189 |
| researchers | 6.356 |
| person_emails | 715 |
| organizations | 24 |
| organizational_units | 23 |
| roles | 10 |
| initiative_types | 2 |
| initiatives | 1.351 |
| advisorships | 991 |
| fellowships | 9 |
| articles | 624 |
| article_authors | 736 |
| academic_educations | 54 |
| teams | 1.644 |
| team_members | 13.335 |
| research_groups | 339 |
| knowledge_areas | 1.450 |
| researcher_knowledge_areas | 917 |
| initiative_teams | 1.401 |

## Duplicados

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

## Saude do Banco

| Check | Quantidade |
| --- | --- |
| articles_duplicate_doi | 0 |
| articles_duplicate_title_year | 0 |
| advisorships_without_supervisor | 0 |
| advisorships_without_student | 0 |
| initiatives_without_team | 0 |
| research_groups_without_cnpq_url | 2 |
| researchers_without_resume | 6.343 |
| researchers_without_cnpq_url | 6.343 |

## Reconciliacao Lattes

- Curriculos Lattes: **15**
- Curriculos resolvidos no banco: **15**
- Curriculos nao resolvidos: **0**

| Entidade | Extraido | Persistido | Casado | Faltando no banco | Extras no banco |
| --- | --- | --- | --- | --- | --- |
| projects | 202 | 918 | 195 | 7 | 723 |
| articles | 782 | 736 | 735 | 47 | 1 |
| educations | 58 | 51 | 51 | 7 | 0 |
| advisorships | 639 | 677 | 489 | 150 | 188 |

### Limitacoes

- Projects and advisorships are reconciled by normalized names/keys and researcher ownership because the current SQLite initiatives table does not persist source_identity metadata.
- extra_in_db can include records from SigPesq/CNPq or older loads that belong to the same researcher.

## Principais Deltas por Curriculo

### projects

| Arquivo | Faltando | Extra | Casado | Extraido | Persistido |
| --- | --- | --- | --- | --- | --- |
| 13_Renner-Sartório-Camargo_3539297708118726.json | 5 | 8 | 1 | 6 | 9 |
| 05_Gustavo-Maia-de-Almeida_2650921349694794.json | 1 | 101 | 18 | 19 | 119 |
| 03_Gabriel-Tozatto-Zago_8771088249434104.json | 1 | 24 | 18 | 19 | 42 |
| 08_Pablo-Rodrigues-Muniz_4404912914498937.json | 0 | 123 | 20 | 20 | 143 |
| 11_Marco-Antonio-de-Souza-Leite-Cuadros_8629256330944049.json | 0 | 108 | 26 | 26 | 134 |

### articles

| Arquivo | Faltando | Extra | Casado | Extraido | Persistido |
| --- | --- | --- | --- | --- | --- |
| 13_Renner-Sartório-Camargo_3539297708118726.json | 32 | 0 | 0 | 32 | 0 |
| 10_Leonardo-Azevedo-Scardua_3651077981942079.json | 14 | 0 | 0 | 14 | 0 |
| 01_Daniel-Cruz-Cavalieri_9583314331960942.json | 1 | 1 | 79 | 80 | 80 |
| 00_Paulo-Sergio-dos-Santos-Junior_8400407353673370.json | 0 | 0 | 27 | 27 | 27 |
| 02_Rafael-Emerick-Zape-de-Oliveira_8365543719828195.json | 0 | 0 | 6 | 6 | 6 |

### educations

| Arquivo | Faltando | Extra | Casado | Extraido | Persistido |
| --- | --- | --- | --- | --- | --- |
| 13_Renner-Sartório-Camargo_3539297708118726.json | 4 | 0 | 0 | 4 | 0 |
| 10_Leonardo-Azevedo-Scardua_3651077981942079.json | 3 | 0 | 0 | 3 | 0 |
| 00_Paulo-Sergio-dos-Santos-Junior_8400407353673370.json | 0 | 0 | 3 | 3 | 3 |
| 01_Daniel-Cruz-Cavalieri_9583314331960942.json | 0 | 0 | 4 | 4 | 4 |
| 02_Rafael-Emerick-Zape-de-Oliveira_8365543719828195.json | 0 | 0 | 2 | 2 | 2 |

### advisorships

| Arquivo | Faltando | Extra | Casado | Extraido | Persistido |
| --- | --- | --- | --- | --- | --- |
| 11_Marco-Antonio-de-Souza-Leite-Cuadros_8629256330944049.json | 46 | 79 | 56 | 102 | 135 |
| 05_Gustavo-Maia-de-Almeida_2650921349694794.json | 39 | 52 | 55 | 94 | 107 |
| 08_Pablo-Rodrigues-Muniz_4404912914498937.json | 24 | 0 | 123 | 147 | 123 |
| 06_Cassius-Zanetti-Resende_4261626566157032.json | 12 | 9 | 12 | 24 | 21 |
| 09_Luiz-Alberto-Pinto_3550111932609658.json | 10 | 13 | 32 | 42 | 45 |
