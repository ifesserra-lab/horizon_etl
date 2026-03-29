# Visao Geral

## Objetivo

O Horizon ETL e a camada de ingestao, consolidacao e exportacao de dados de pesquisa do projeto. Ele transforma fontes heterogeneas em um conjunto padronizado de entidades e artefatos para consumo operacional e analitico.

## Fontes atendidas

- **SigPesq**: grupos, projetos e orientacoes
- **Lattes**: curriculos, projetos, artigos, formacoes e orientacoes
- **CNPq**: sincronizacao complementar de grupos de pesquisa e membros

## Principais resultados

- dados canonicos em `data/exports/`
- marts analiticos, como `knowledge_areas_mart.json`
- auditorias e reports em `data/reports/`
- rastreabilidade operacional via tracking

## Publico-alvo desta documentacao

- **Desenvolvedores**: entendimento da arquitetura e dos entrypoints
- **Operacao**: setup, automacao e troubleshooting
- **Gestao**: leitura de reports e artefatos de acompanhamento

## Principais capacidades

- ingestao multipla e incremental de fontes academicas
- consolidacao de pessoas, grupos, equipes e iniciativas
- exportacao canonica para integracoes e consumo externo
- geracao de marts e relatorios operacionais
- execucao local e execucao agendada no GitHub Actions
