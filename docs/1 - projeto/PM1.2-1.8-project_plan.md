# Project Plan
**Projeto:** Horizon ETL
**Data:** 06/01/2026
**Autor:** Antigravity (Senior PM)
**Versão:** 1.0

---

# 1. Escopo e WBS (PM1.2)
A estrutura analítica do projeto (EAP/WBS) é dividida por fontes de dados (Releases):

1.  **Fundação e SigPesq** (Mês 1)
    1.1. Setup de Infraestrutura (Prefect + Supabase).
    1.2. Mapeamento de dados do SigPesq (IFES).
    1.3. Extrator SigPesq.
    1.4. Carga SigPesq no Supabase.
2.  **Lattes** (Mês 2)
    2.1. Investigação de APIs/Scrapers do Lattes.
    2.2. Extrator de Currículos e Produções.
    2.3. Normalização de autores.
    2.4. Carga Lattes.
3.  **SigFapes** (Mês 3)
    3.1. Extrator de Dados de Execução (Projetos/Bolsas).
    3.2. Extrator de **Projetos, Bolsistas e Compras/Prestação de Contas**.
    3.3. Carga SigFapes.
4.  **Google Scholar** (Mês 4)
    4.1. Extrator de Metadados Acadêmicos.
    4.2. Carga Google Scholar.
    4.3. Relatório Final e Documentação de Encerramento.

---

# 2. Cronograma Macro (PM1.3)
| Marco | Descrição | Data Estimada |
|-------|-----------|---------------|
| **Start** | Início do Projeto | 06/01/2026 |
| **R1** | Entrega Release 1 (SigPesq) | 06/02/2026 |
| **R2** | Entrega Release 2 (Lattes) | 06/03/2026 |
| **R3** | Entrega Release 3 (SigFapes) | 06/04/2026 |
| **R4** | Entrega Final (Google Scholar + Encerramento) | 06/05/2026 |

**Ritmo de Trabalho**:
- Sprints quinzenais (2 s/mês).
- Checagem de status no dia 1 e 15 de cada mês.

---

# 3. Recursos (PM1.4)
- **Equipe Técnica**: 1 Desenvolvedor Fullstack (User).
- **Stakeholders**: Gestão do Campus, Alunos, Pesquisadores.
- **Tecnologia**: [Python](https://www.python.org/), [Prefect Cloud/Self-hosted](https://www.prefect.io/), [Supabase](https://supabase.com/) (PostgreSQL).

---

# 4. Plano de Gerenciamento de Riscos (PM1.7)
| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Mudanças no Layout dos Sites (Scraping) | Alto | Utilizar libs resilientes e monitoramento de falhas no Prefect. |
| Bloqueio de IP (Rate Limiting) | Alto | Implementar backoff exponencial e rotação de user-agents. |
| Complexidade dos Dados Lattes | Médio | Focar apenas nos campos essenciais para o MVP. |

---

# 5. Critérios de Aceite (PM1.8)
- Os pipelines no Prefect devem rodar com sucesso (Status: Success).
- Os dados devem estar persistidos no Supabase conforme esquema definido.
- **Idempotência**: Múltiplas execuções do pipeline não devem gerar dados duplicados ou inconsistentes.
- O código deve passar nos checks de qualidade (`black`, `isort`, `flake8`).
- Testes unitários cobrindo a lógica de extração.
