# Horizon ETL

Esta documentacao organiza a solucao **Horizon ETL** em torno de quatro perguntas:

- O que a solucao faz
- Como ela esta estruturada
- Como executar e operar o pipeline
- Como interpretar os reports gerados

## Visao rapida

O Horizon ETL consolida dados academicos e de pesquisa a partir de fontes como:

- SigPesq
- Lattes
- CNPq

E entrega artefatos operacionais e analiticos como:

- base canônica exportada em JSON
- marts analiticos
- reports de execucao do ETL
- reports de conciliacao e auditoria

## Estrutura proposta do site

O MkDocs foi organizado nestas secoes:

- **Solucao**
  Conteudo de alto nivel sobre objetivo, arquitetura, fluxos e artefatos.
- **Operacao**
  Setup local, comandos principais, automacao semanal e troubleshooting.
- **Reports**
  Catalogo dos reports e snapshots dos relatorios mais relevantes.
- **Governanca**
  Documentos ja existentes no repositorio que ajudam a manter contexto de backlog, planejamento e historico.

## Ponto de partida recomendado

Se voce esta chegando agora no projeto, a leitura sugerida e:

1. `Visao Geral`
2. `Arquitetura`
3. `Fluxos e Entrypoints`
4. `Automacao Semanal`
5. `Reports`

## Localizacao dos artefatos

- Codigo: `src/`
- Scripts operacionais: `src/scripts/`
- Fluxos: `src/flows/`
- Exports: `data/exports/`
- Reports: `data/reports/`
- Banco local: `db/horizon.db`

---

# 8. Governança do SDLC

A governança é conduzida pela equipe **DevOps + PMO do ConectaFapes**, usando indicadores:

| Métrica | Objetivo |
|--------|----------|
| Lead Time | Velocidade de entrega |
| Change Failure Rate | Estabilidade |
| MTTR | Recuperação |
| Cobertura de Testes | Qualidade |
| Aderência SDLC | Auditoria |

Toda melhoria é registrada via **Pull Request** neste repositório, assegurando evolução controlada e institucional.

---

# 9. Referências Técnicas

- ISO/IEC 29110 – Processos de Ciclo de Vida para VSEs  
- ISO/IEC 12207 – Processos de Ciclo de Vida de Software  
- ISO/IEC 25010 – Qualidade de Produto  
- DORA Metrics – Google Research  
