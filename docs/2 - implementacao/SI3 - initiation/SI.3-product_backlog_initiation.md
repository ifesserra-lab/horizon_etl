# Product Backlog – Horizon ETL
**Última atualização:** 06/01/2026
**Responsável (PO):** Antigravity (Senior Lead)
**Versão do Documento:** 1.0

---

# 1. Visão Geral
Este Backlog traduz os Requisitos (SI.1) e Análise (SI.2) em itens de trabalho entregáveis (US).
**Estratégia**: Todo item deve ser testável e deployável independentemente.

---

# 2. Epics & User Stories

## Epic 1: Extração SigPesq (Release 1)
**Objetivo**: Coletar dados de projetos da base SigPesq.

### US-001 – Extração de Projetos SigPesq
```yaml
id: US-001
milestone: R1
prioridade: Alta
tamanho: 8
origem: [RF-01, RNF-01, RNF-04, RNF-06]
tags: [type:feature, area:backend, source:sigpesq]
dependencias: []
modulos_afetados: [src/adapters/sources/sigpesq, src/flows]
```

#### Descrição
Desenvolver o pipeline de extração para o SigPesq. O sistema deve conectar e extrair dados de **Projetos**, **Grupos de Pesquisa** e **Bolsistas**, persistindo-os no Supabase.

#### Critérios de Aceitação (Definition of Done)
- **Funcional**:
    - [ ] Dados de **Projetos** extraídos (Título, Data, Status).
    - [ ] Dados de **Grupos de Pesquisa** extraídos (Líder, Área, certificado).
    - [ ] Dados de **Bolsistas** extraídos (Nome, Modalidade de bolsa, Vigência).
    - [ ] Mapeamento correto utilizando entidades da lib **`research_domain_lib`** (`Project`, `ResearchGroup`, `Researcher`).
- **Teste (TDD)**:
    - [ ] Teste Unitário: Parser de HTML/JSON do SigPesq com mocks.
    - [ ] Teste Integração: Gravação via `ResearchDomainLib` (ou suas abstrações).
    - [ ] Cobertura > 80% no módulo `adapters/sources/sigpesq`.
- **Deploy**:
    - [ ] Flow `ingest_sigpesq` registrado no Prefect.
    - [ ] Execução bem-sucedida em ambiente de Staging.
- **Observabilidade**:
    - [ ] Logs de "Início", "Extração (Qtd)", "Carga" e "Fim".

#### Tasks Sugeridas
1.  **T-001 [Dev]**: Implementar `SigPesqClient` (Source Adapter).
    - *Critério*: Passar testes unitários com HTML mockado.
2.  **T-002 [Dev]**: Implementar `SigPesqMapper` (Raw -> Domain).
    - *Critério*: Transformação valida tipos Pydantic.
3.  **T-003 [Ops]**: Criar Flow Prefect e Dockerfile.
    - *Critério*: Container sobe e flow registra no server.

---

## Epic 2: Extração Lattes (Release 2)
**Objetivo**: Enriquecer dados de pesquisadores (Currículo, Produção).

### US-002 – Extração de Currículo Lattes (XML/Zip)
```yaml
id: US-002
milestone: R2
prioridade: Alta
tamanho: 13
origem: [RF-02, RF-06, RNF-01]
tags: [type:feature, area:backend, source:lattes]
dependencias: [US-001]
modulos_afetados: [src/adapters/sources/lattes, src/core/logic]
```

#### Descrição
Processar arquivos XML de currículos Lattes para extrair dados pessoais e produções bibliográficas. Deve lidar com desduplicação de autores (`RF-06`).

#### Critérios de Aceitação (Definition of Done)
- **Funcional**:
    - [ ] XML parseado corretamente para Objetos de Domínio (`Researcher`, `Publication`).
    - [ ] Identificação única por ID Lattes (16 dígitos).
- **Teste (TDD)**:
    - [ ] Teste Unitário: Parser XML com massa de dados de exemplo.
    - [ ] Teste de Lógica: Algoritmo de normalização de nomes.
- **Deploy**:
    - [ ] Flow `ingest_lattes` capaz de processar lote de zips.
    - [ ] Infraestrutura de disco/volume montada para leitura de arquivos.

#### Tasks Sugeridas
1.  **T-004 [Dev]**: Criar `LattesXMLParser`.
    - *Critério*: Extrair nome, resumo e lista de artigos.
2.  **T-005 [Dev]**: Implementar Lógica de `Merge/Deduplication`.
    - *Critério*: Teste com 2 XMLs do mesmo autor (versões diferentes) resulta em 1 registro atualizado.

---

## Epic 3: Dados de Execução FAPES (Release 3)
**Objetivo**: Monitorar execução financeira e bolsas.

### US-003 – Dados Financeiros e Bolsas
```yaml
id: US-003
milestone: R3
prioridade: Média
tamanho: 8
origem: [RF-04]
tags: [type:feature, area:backend, source:fapes]
dependencias: []
```

#### Descrição
Extrair dados do Portal da Transparência/Dados Abertos sobre repasses da FAPES.

#### Critérios de Aceitação
- **Funcional**:
    - [ ] Extração de valores (R$) e beneficiários.
    - [ ] Vínculo com Projetos existentes (se houver chave comum).
- **Teste**:
    - [ ] Teste de parsing de CSV/API Fapes.
- **Deploy**:
    - [ ] Flow agendado (Cron) para rodar mensalmente.

---

### US-006 – Integração API FAPES (Projetos e Bolsas)
```yaml
id: US-006
milestone: R3
prioridade: Alta
tamanho: 8
origem: [RF-04]
tags: [type:feature, area:backend, source:fapes]
dependencias: []
modulos_afetados: [src/adapters/sources/fapes, src/flows]
```

#### Descrição
Desenvolver a integração com a **API da FAPES** para extrair dados estruturados de:
1.  **Projetos** (Títulos, vigência, valores).
2.  **Bolsistas** (Beneficiários de bolsas).
3.  **Pagamentos** (Execução financeira).

#### Critérios de Aceitação (Definition of Done)
- **Funcional**:
    - [ ] Conexão autenticada/segura com API FAPES.
    - [ ] Extração de dados de **Projetos** mapeados para o Domínio.
    - [ ] Extração de dados de **Bolsistas** mapeados para o Domínio.
    - [ ] Extração de dados de **Pagamentos** financeiros.
- **Teste (TDD)**:
    - [ ] Teste Unitário: Client HTTP com Mock da API FAPES.
    - [ ] Teste de Contrato: Validação do Schema JSON retornado.
- **Deploy**:  
---

## Epic 7: Orquestração e Pipelines (Release 1)
**Objetivo**: Unificar fluxos de dados para facilitar a execução completa.

### US-011 – Pipeline Unificado de Ingestão e Exportação
```yaml
id: US-011
milestone: R1
prioridade: Alta
tamanho: 3
origem: [RNF-01]
tags: [type:feature, area:core, area:flows]
dependencias: [US-001, US-009, US-007]
modulos_afetados: [src/flows, app.py]
```

#### Descrição
Criar um flow mestre que orquestra a execução sequencial dos fluxos de SigPesq, CNPq e Exportação Canônica.

#### Critérios de Aceitação
- **Funcional**:
    - [x] Execução sequencial: SigPesq -> CNPq -> Export.
    - [x] Parametrização de filtro de campus e diretório de saída.
- **Deploy**:
    - [ ] Comando `full_pipeline` disponível no `app.py`.
- **Observabilidade**:
    - [ ] Logs do flow pai indicando o status de cada subflow.
    - [ ] Flow `ingest_fapes_api` agendado.
- **Observabilidade**:
    - [ ] Logs detalhando: "Projetos Encontrados"  , "Novos Baixados", "Falha na Extração".

#### Tasks Sugeridas
1.  **T-006 [Dev]**: Criar `FapesSiteScraper` para listar e baixar PDFs.
    - *Critério*: Salvar arquivos com nomenclatura padronizada.
2.  **T-007 [Dev]**: Implementar `EditalPDFParser` com Docling.
    - *Critério*: Converter PDF para Markdown com layout preservado.
3.  **T-008 [Dev]**: Implementar `EditalMatcher` (Regex/NLP).
    - *Critério*: Extrair Tabela de Cronograma e Parágrafo de Objetivo.
4.  **T-009 [Ops]**: Criar Flow Prefect com Persistência.

---

### US-012 – Geração de Data Mart de Áreas de Pesquisa
```yaml
id: US-012
milestone: R2
prioridade: Alta
tamanho: 3
origem: [User Req.]
tags: [type:feature, area:core, area:mart]
dependencias: [US-007, US-009]
modulos_afetados: [src/core/logic/mart_generator.py, src/flows]
```

#### Descrição
Gerar um arquivo JSON consolidado que vincula Áreas de Conhecimento aos Grupos de Pesquisa e Campi correspondentes, incluindo contagens agregadas.

#### Critérios de Aceitação
- **Funcional**:
    - [x] Leitura direta do Banco de Dados via Controllers.
    - [x] Agregação de contagem de grupos por área.
    - [x] Listagem de nomes de campi únicos por área.
- **Deploy**:
    - [x] Comando `ka_mart` integrado ao `app.py`.
    - [x] Passo final do `full_pipeline`.

---

## Epic 4: Metadados Google Scholar (Release 4)
**Objetivo**: Métricas de impacto.

### US-004 – Metadados e Citações
```yaml
id: US-004
milestone: R4
prioridade: Baixa
tamanho: 5
origem: [RF-05]
tags: [type:feature, source:scholar]
```

#### Descrição
Busca de perfil e métricas (H-Index) via Scraper.

#### Critérios de Aceitação
- **Funcional**:
    - [ ] H-Index atualizado para pesquisador.
- **Teste**:
    - [ ] Mock severo do Scholar para evitar banimento em CI.
- **Deploy**:
    - [ ] Uso de Proxies configurados no Deploy (Env Vars).

---

## Cross-Cutting (Arquitetura)

### US-005 – Observabilidade e Idempotência
```yaml
id: US-005
milestone: R1
prioridade: Crítica
tamanho: 5
origem: [RNF-01, RNF-06]
tags: [type:arch, area:core]

## Epic 5: Ingestão de Grupos de Pesquisa (Excel) (Release 1)
**Objetivo**: Processar planilhas extraídas do SigPesq e popular o domínio de Grupos de Pesquisa.

### US-007 – Carga de Grupos de Pesquisa (Excel -> DB)
```yaml
id: US-007
milestone: R1
prioridade: Alta
tamanho: 5
origem: [RF-01]
tags: [type:feature, area:backend, source:sigpesq]
dependencias: [US-001]
modulos_afetados: [src/flows, src/core/logic]
```

#### Descrição
Ler o arquivo Excel de Grupos de Pesquisa (processado na US-001/Extração) e persistir utilizando os Controllers da `research_domain_lib`. Deve garantir a criação da hierarquia (Universidade -> Campus -> Grupo).

#### Critérios de Aceitação
- **Funcional**:
    - [ ] Leitura do Excel `data/raw/sigpesq/research_group/*.xlsx`.
    - [ ] **Universidade** "UFSC" criada (se não existir) via `UniversityController`.
    - [ ] **Campus** "Florianópolis" criado (se não existir) via `CampusController`.
    - [ ] **Grupo de Pesquisa** criado com nome, sigla e vínculos via `ResearchGroupController`.
- **Teste**:
    - [ ] Teste de Integração com banco (Mock ou Local) validando a criação dos registros.
- **Deploy**:
    - [ ] Flow `ingest_sigpesq_groups` executável via `app.py`.

#### Tasks Sugeridas
1.  **T-010 [Dev]**: Implementar `ResearchGroupExcelLoader`.
    - *Critério*: Ler Excel com Pandas e iterar linhas.
2.  **T-011 [Dev]**: Implementar Lógica de Carga (Service).
    - *Critério*: Usar `UniversityController`, `CampusController`, `ResearchGroupController` para idempotência.


#### Descrição
Implementar Base Repository com Loguru e lógica de `ON CONFLICT DO UPDATE`.

#### Critérios de Aceitação
- **Funcional**:
    - [ ] Logs aparecem no Stdout e UI do Prefect.
    - [ ] Inserir registro X duas vezes não cria duplicata.
- **Teste**:
    - [ ] Teste de Repositório (Integration) provando idempotência.
    - [ ] Teste validando formato JSON dos logs.
- **Deploy**:
    - [ ] Variáveis de ambiente de LOG_LEVEL configuráveis.

---

## Epic 6: Atualização de Grupos de Pesquisa CNPq (Release 2)
**Objetivo**: Enriquecer dados dos grupos de pesquisa com informações oficiais do CNPq (DGP).

### US-009 – Atualização de Dados de Grupos via DGP/CNPq
```yaml
id: US-009
milestone: R2
prioridade: Média
tamanho: 8
origem: [RF-09, RNF-01, RNF-02, RNF-06]
tags: [type:feature, area:backend, source:cnpq]
dependencias: [US-007]
modulos_afetados: [src/flows, src/core/logic/strategies]
```

#### Descrição
Desenvolver um novo pipeline que extrai URLs de espelho de grupos do banco de dados, utiliza a lib `dgp_cnpq_lib` para coletar dados atualizados (nome, líderes, linhas de pesquisa) e atualiza os membros do grupo.

#### Critérios de Aceitação (Definition of Done)
- **Funcional**:
    - [ ] Extração de URLs de grupos existentes no DB via `ResearchGroupRepository`.
    - [ ] Uso da `dgp_cnpq_lib` para extrair dados do espelho.
    - [ ] Atualização dos dados do grupo (Líderes, Linhas de Pesquisa) no DB.
    - [ ] Sincronização de membros do grupo (inserção de novos, atualização de participações).
- **Teste (TDD)**:
    - [ ] Teste Unitário: Estratégia de mapeamento dos dados da lib para o domínio `ResearchGroup`.
    - **Tasks**:
        - Create `CnpqCrawlerAdapter` to connect with `dgp_cnpq_lib`.
        - Implement `CnpqSyncLogic` for orchestration.
        - Create Sync Flow.

### US-010: Sincronização de Egressos CNPq
- **Description**: Como gestor, quero que os ex-membros (egressos) dos grupos de pesquisa sejam sincronizados com suas respectivas datas de saída, para manter o histórico fiel da participação.
- **Acceptance Criteria**:
    - Extrair lista de egressos do CNPq.
    - Identificar pesquisadores/estudantes já existentes ou criar novos.
    - Atualizar a associação no grupo (TeamMember) preservando a `start_date` e preenchendo a `end_date`.
    - Garantir que egressos não sejam reativados como membros ativos incorretamente.
- **Priority**: High
- **Tasks**:
    - Atualizar `CnpqCrawlerAdapter` para extrair egressos.
    - Atualizar `CnpqSyncLogic` para processar egressos.
- **Deploy**:
    - [ ] Flow `sync_cnpq_groups` registrado e explorável no `app.py`.
- **Observabilidade**:
    - [ ] Log de "Qtd de Grupos Processados", "Sucesso/Erro por URL".

#### Tasks Sugeridas
1.  **T-012 [Dev]**: Implementar `CnpqCrawlerStrategy`.
    - *Critério*: Mapear `dict` retornado pela lib para as entidades do domínio.
2.  **T-013 [Ops]**: Criar Flow Prefect `sync_cnpq_groups`.
    - *Critério*: Flow orquestra: Seleção -> Crawler -> Persistência.

---

# 4. Backlog Refinado (Release 1)

| **US-005** | Observabilidade e Idempotência (Base) | R1 | **Concluído** |
| **US-001** | Extração Projetos SigPesq | R1 | **Concluído** |
| **US-007** | Ingestão Grupos Pesquisa (Excel) | R1 | **Concluído** |
| **US-009** | Sincronização CNPq DGP | R2 | **Concluído** |
| **US-010** | Sincronização Egressos CNPq | R2 | **Concluído** |
| **US-011** | Pipeline Unificado | R1 | **Concluído** |
| **US-012** | Research Area Mart | R2 | **Concluído** |
| **US-006** | Extração Editais FAPES (PDF) | R3 | **Ready** |


---

# 5. Definition of Ready (DoR) Check for R1
- [x] US-005 e US-001 possuem arquitetura definida em `SI.3-design.md`.
- [x] Critérios de Teste e Deploy explícitos.
- [x] Origem rastreada para `SI.1`.
