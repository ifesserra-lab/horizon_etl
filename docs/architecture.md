# Arquitetura

## Estrutura logica

O projeto segue uma organizacao de camadas com forte separacao entre:

- **`src/core`**: regras de negocio, logica de consolidacao, linking e exportacao
- **`src/adapters`**: integracoes com fontes externas e mecanismos de saida
- **`src/flows`**: orquestracao Prefect e entrypoints executaveis
- **`src/scripts`**: utilitarios operacionais, auditorias e relatorios

## Visao de componentes

```text
Fontes externas
  |- SigPesq
  |- Lattes
  |- CNPq
        |
        v
src/adapters/sources
        |
        v
src/core/logic
  |- loaders
  |- resolucao de pesquisadores
  |- consolidacao e linking
  |- exporters
  |- auditorias
        |
        v
Persistencia local + artefatos
  |- db/horizon.db
  |- data/exports/*.json
  |- data/reports/*.md|*.json
```

## Persistencia

O ambiente local usa `db/horizon.db` como banco SQLite. Parte relevante do dominio e fornecida por bibliotecas externas, principalmente `research-domain` e `eo_lib`.

## Orquestracao

O pipeline principal e orquestrado por Prefect. O repositório tambem possui automacao local via `Makefile` e automacao remota semanal via GitHub Actions.

## Observacoes importantes

- O pipeline unificado atual e o caminho recomendado para refresh completo.
- O projeto ainda preserva entrypoints legados, como o pipeline Serra.
- Os reports sao parte da arquitetura operacional, nao apenas documentacao auxiliar.
