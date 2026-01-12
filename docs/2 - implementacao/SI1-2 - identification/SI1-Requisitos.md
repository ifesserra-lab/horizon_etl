# SI.1 – Especificação dos Requisitos do Software
**Projeto:** Horizon ETL
**Versão:** 1.0
**Data:** 06/01/2026
**Responsável:** Antigravity (Senior Analyst)

---

## 1. Objetivo do Documento
Registrar os requisitos funcionais e não funcionais do sistema Horizon ETL, focando na extração, transformação e carga de dados de múltiplas fontes acadêmicas.

---

## 2. Escopo do Sistema
O **Horizon ETL** é uma infraestrutura de dados que automatiza a coleta de informações de pesquisa e extensão.
- **Entradas**: SigPesq, Lattes, FAPES, Google Scholar.
- **Saída**: Banco de Dados Unificado (Supabase) para consumo por outros sistemas.

---

## 3. Stakeholders
| Nome / Papel | Interesse | Responsabilidade |
|---------------|-----------|------------------|
| **Product Owner** | Priorização das fontes | Validar dados extraídos |
| **Gestores (Campus)** | Relatórios gerenciais | Definir métricas de sucesso |
| **Pesquisadores** | Visibilidade do perfil | Validar precisão dos dados |

---

## 4. Requisitos Funcionais (RF)

| ID | Requisito | Critério de Aceitação | Origem |
|----|-----------|------------------------|--------|
| **RF-01** | O sistema deve extrair dados de projetos do SigPesq. | Projetos persistidos no Supabase com metadados completos. | PM1.3 (R1) |
| **RF-02** | O sistema deve extrair dados curriculares da Plataforma Lattes. | Perfil, formação e produções carregadas para pesquisadores listados. | PM1.3 (R2) |
| **RF-04** | O sistema deve extrair dados de execução (Projetos/Bolsas/Compras) da FAPES. | Dados financeiros e de bolsistas vinculados persistidos. | PM1.3 (R3) |
| **RF-05** | O sistema deve coletar metadados do Google Scholar. | Citações e índice-h atualizados. | PM1.3 (R4) |
| **RF-06** | O sistema deve normalizar nomes de autores e instituições. | Entidades duplicadas fundidas (Merge) em ID único. | Arq. |
| **RF-07** | O sistema deve exportar dados de grupos de pesquisa de uma Unidade Organizacional para JSON. | Arquivo JSON gerado seguindo schema do ResearchGroup. | User Req. |
| **RF-08** | O sistema deve exportar dados canônicos (Organização, Campus, Áreas) para arquivos JSON separados, permitindo filtragem por Campus. | Arquivos `organizations.json`, `campuses.json`, `knowledge_areas.json` gerados. Filtro de Campus suportado. | User Req. |
| **RF-09** | O sistema deve extrair e atualizar dados de grupos de pesquisa do CNPq DGP (identificação, linhas de pesquisa, membros). | Dados do grupo (espelho), membros e **linhas de pesquisa (mapeadas para Áreas do Conhecimento)** atualizados no banco de dados via `dgp_cnpq_lib`. | User Req. |
| **RF-10** | O sistema deve identificar e sincronizar membros egressos do CNPq, registrando corretamente as datas de início e fim de participação. | Membros egressos identificados e datas de participação (início/fim) persistidas no Supabase. | User Req. |
| **RF-11** | O sistema deve gerar um "Mart JSON" que consolida as Áreas de Pesquisa com seus Grupos e Campi vinculados, permitindo filtragem por campus. | Arquivo `knowledge_areas_mart.json` gerado com estatísticas por área. Filtro de campus suportado. | User Req. |

---

## 5. Requisitos Não Funcionais (RNF)

| ID | Categoria | Descrição | Restrição Técnica |
|----|------------|-----------|-------------------|
| **RNF-01** | Idempotência | Re-execução de pipelines não deve duplicar dados. | `UPSERT` obrigatório. |
| **RNF-02** | Resiliência | Pipelines devem suportar falhas de rede (retries). | Prefect Retries. |
| **RNF-03** | Arquitetura | Código desacoplado seguindo Clean/Hexagonal Arch. | Modules `etl`, `core`. |
| **RNF-04** | Stack | Python 3.10+, Prefect, Supabase. | PM1.0 |
| **RNF-05** | Qualidade | Cobertura de testes em lógicas de transformação. | Pytest, TDD. |
| **RNF-06** | Observabilidade | Todas as ações do sistema devem gerar logs estruturados. | Loguru/Prefect Logger. |

---

## 6. Restrições
- Rate Limits do Google Scholar e Lattes (cnpq).
- Acesso à VPN institucional pode ser necessário para SigPesq (a confirmar).
