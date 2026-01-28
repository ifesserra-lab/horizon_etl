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
| **RF-12** | O sistema deve criar equipes automaticamente durante a ingestão de projetos SigPesq, extraindo coordenadores, pesquisadores e estudantes das colunas do Excel. | Equipes criadas com membros associados aos respectivos roles (Coordinator, Researcher, Student). Persons criadas ou reutilizadas (idempotente com Fuzzy Matching). | User Req. |
| **RF-13** | O sistema deve gerar um "Mart JSON" de estatísticas de iniciativa, consolidando totais, evolução anual e composição de equipes. | Arquivo `initiatives_analytics_mart.json` gerado com dados de resumo, evolução e composição. | User Req. |
| **RF-14** | O sistema deve associar palavras-chave de projetos como Áreas de Conhecimento ao Grupo de Pesquisa e Pesquisadores vinculados. | Palavras-chave extraídas e persistidas como `KnowledgeArea`. Vínculos criados nas tabelas `group_knowledge_areas` e `researcher_knowledge_areas`. | User Req. |
| **RF-15** | O sistema deve popular automaticamente Grupos de Pesquisa recém-criados (via ingestão de projetos) com os membros do projeto (Pesquisadores e Estudantes). | Ao criar um Grupo de Pesquisa inexistente, Coordenador/Pesquisadores do projeto são adicionados como "Pesquisador" do grupo, e Alunos como "Estudante". | User Req. |
| **RF-16** | O sistema deve extrair dados de bolsistas (orientações/bolsas) do SigPesq mapeando: TituloPT (Name), Inicio (StartDate), Fim (EndDate), Orientado (Student) e Orientador (Supervisor). A identificação de pessoas deve usar Nome e E-mail (OrientadoEmail/OrientadorEmail) para evitar duplicatas. | Bolsistas persistidos no Supabase e vinculados aos seus projetos/orientadores com campos corretos. | User Req. |
| **RF-17** | O sistema deve extrair dados de bolsas (Fellowships) mapeando: Programa (Name) e Valor (Value). | Fellowships persistidAs com nome do programa e valor financeiro. | User Req. |
| **RF-18** | O sistema deve criar uma Iniciativa do tipo "Projeto de Pesquisa" vinculada à "Advisorship" (Bolsista) usando o campo TituloPJ como nome. | Advisorships vinculadas a um projeto pai único por título. A unicidade do projeto de pesquisa é garantida pelo nome (TituloPJ). | User Req. |
| **RF-19** | O arquivo `advisorships_canonical.json` deve exportar os dados agrupados por Projeto de Pesquisa (Parent Project), incluindo detalhes do projeto e a lista de bolsistas vinculados. | Exportação hierárquica (Projeto -> Bolsistas). Projetos sem bolsistas não precisam ser listados, e bolsistas sem projeto devem ser agrupados sob uma entrada "Sem Projeto" ou similar. | User Req. |
| **RF-20** | O sistema deve garantir que o orientador (Supervisor) e o bolsista (Student) de uma Advisorship sejam adicionados como membros da equipe do Projeto de Pesquisa pai correspondente. | A identificação de pessoas deve ser idempotente (usando `PersonMatcher`). O orientador deve ser adicionado ao projeto pai com o papel de "Coordinator" (ou membro da equipe) e o estudante com o papel de "Student". | User Req. |
| **RF-21** | O arquivo `advisorships_canonical.json` deve incluir a lista de membros da equipe (Team) de cada Projeto de Pesquisa (Parent Project), detalhando nome e papel (Role). | Para cada projeto no JSON, deve haver um campo `team` contendo a lista de membros e seus respectivos papéis no projeto pai. | User Req. |
| **RF-22** | O arquivo `advisorships_canonical.json` deve expandir o campo `fellowship_id` para um objeto `fellowship` contendo todos os detalhes da bolsa (ID, Nome, Descrição, Valor). | Em vez de exportar apenas o ID da bolsa, o sistema deve realizar um join com a tabela de bolsas e exportar o objeto completo. | User Req. |
| **RF-23** | O sistema deve gerar um Data Mart de indicadores (`advisorship_analytics.json`) a partir do canônico agrupado. | O mart deve consolidar métricas por projeto (investimento total, contagem de alunos) e globais (distribuição por modalidade de bolsa). | User Req. |
| **RF-24** | O Data Mart deve incluir resumos estatísticos e rankings de orientadores e programas de fomento. | Automatizar a geração de indicadores de performance e rankings para dashboards. | User Req. |
| **RF-25** | O status de uma Advisorship deve ser determinado automaticamente com base na data de término (`Fim`). Se a data de término for maior que a data atual, o status é "Active"; caso contrário, é "Concluded". | Implementar lógica de validação temporal durante a ingestão de dados do SigPesq. | User Req. |
| **RF-26** | O sistema deve calcular automaticamente as datas de início e término dos Projetos de Pesquisa (TituloPJ) com base nas datas das orientações filhas associadas. O `start_date` do projeto deve ser a data mais antiga entre todas as orientações. O `end_date` deve ser a data mais recente. O `status` é calculado automaticamente: "Concluded" se `end_date` < hoje, caso contrário "Active". | Projetos de Pesquisa criados devem ter: (1) `start_date` = MIN(orientações.start_date), (2) `end_date` = MAX(orientações.end_date), (3) `status` calculado conforme regra. Nenhum projeto deve ter status "Unknown" quando possui orientações. | User Req. |
| **RF-27** | O sistema deve capturar a agência financiadora (Sponsor) da bolsa SigPesq a partir da coluna `agFinanciadora`. | Campo `sponsor` populado na entidade Fellowship. | User Req. |

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
