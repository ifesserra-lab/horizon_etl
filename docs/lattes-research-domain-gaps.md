# Lattes x ResearchDomain Gaps

This note records the Lattes entities already present in `data/lattes_json`
that the current ETL still does not import, even though `research-domain`
already has a matching model or a close target.

## Covered today

- `informacoes_pessoais`
- `formacao_academica`
- `projetos_pesquisa`
- `projetos_extensao`
- `projetos_desenvolvimento`
- `orientacoes`
- `producao_bibliografica.artigos_periodicos`
- `producao_bibliografica.trabalhos_completos_congressos`

## Present in Lattes and already representable in ResearchDomain

These blocks are still not imported by the ETL today. The point here is only
that the current domain already has a compatible model or a close target.

- `idiomas` -> `Language` and `Proficiency`
- `premios_titulos` -> `Award`
- `areas_de_atuacao` -> `KnowledgeArea`
- `linhas_de_pesquisa` -> `KnowledgeArea`
- `bancas` -> implicit `Advisorship` board members via `AdvisorshipMember`
  with role `BOARD_MEMBER`, but still not ingested from Lattes today
- `producao_bibliografica.livros_publicados` -> `ResearchProduction` + `ProductionType`
- `producao_bibliografica.capitulos_livros` -> `ResearchProduction` + `ProductionType`
- `producao_tecnica` -> `ResearchProduction` + `ProductionType`

## Present in Lattes without a first-class target in the current ETL round

- `eventos`
- `atuacao_profissional`
- `estatisticas`

## Important modeling notes

- `banca` is not a standalone entity in the current domain. It is modeled as
  a set of people attached to an `Advisorship` with the board-member role.
  This is a domain capability, not current ETL coverage.
- `linha de pesquisa` can be normalized to `KnowledgeArea` in the current
  domain model. This is still not imported from the Lattes block today.
- `evento` is also not a standalone entity today. It appears only indirectly
  in `Article`, through the conference-related article type and the
  `journal_conference` field. This does not cover the top-level `eventos`
  block from the Lattes JSON.

## Explicitly out of scope for this round

- No new Lattes ingestion flow is added for the entities above.
- `ExternalResearchGroup` remains outside this round because no clear and
  recurring mapping was identified in the current `lattes_json` set.
