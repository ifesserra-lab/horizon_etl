# Reports

## Objetivo da secao

Esta secao centraliza os reports mais importantes da solucao, com foco em:

- acompanhamento de execucao
- conciliacao entre extraido e persistido
- auditoria do dominio de tracking

## Fonte canonica

Os arquivos gerados em runtime ficam em:

```text
data/reports/
```

A secao do MkDocs funciona como uma vitrine documentada desses artefatos e pode ser atualizada sempre que o pipeline gerar novos snapshots relevantes.

## Reports incluidos

- **ETL Flow Run**
  Resumo por etapa da execucao do pipeline, com duracao, origem e deltas por entidade.
- **ETL Load Report**
  Relatorio de conciliacao entre o que foi extraido e o que foi persistido.
- **Tracking Audit Report**
  Visao de auditoria do dominio de tracking e de suas tabelas.
