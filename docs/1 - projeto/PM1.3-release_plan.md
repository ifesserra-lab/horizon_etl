# Release Plan
**Projeto:** Horizon ETL
**Versão:** 1.0

---

# 1. Visão Geral de Releases
O projeto será entregue em 4 releases mensais incrementais.

| Release | Objetivo Principal | Data Estimada | Status |
|---------|--------------------|----------------|--------|
| **R1** | Integração SigPesq (IFES) | 06/02/2026 | Planejado |
| **R2** | Integração Lattes (CNPq) | 06/03/2026 | Planejado |
| **R3** | Integração SigFapes (FAPES) | 06/04/2026 | Planejado |
| **R4** | Integração Google Scholar | 06/05/2026 | Planejado |

---

# 2. Detalhamento por Release

## 2.1 Release R1 – SigPesq (Fundação)
**Objetivo:** Capturar dados institucionais de projetos de pesquisa e extensão do sistema interno (IFES).
**Funcionalidades:**
- Setup do ambiente Prefect + Supabase.
- ETL de Projetos e Pesquisadores do SigPesq.
- Tabelas Core no Banco de Dados.

## 2.2 Release R2 – Lattes
**Objetivo:** Enriquecer os perfis dos pesquisadores com dados públicos do CNPq.
**Funcionalidades:**
- ETL de Currículos Lattes (identificação por nome/CPF obtidos no R1).
- Extração de produções bibliográficas e técnicas.

## 2.3 Release R3 – SigFapes
**Objetivo:** Monitorar oportunidades de fomento, editais estaduais e a execução financeira dos projetos.
**Funcionalidades:**
- ETL de Projetos, Bolsas e Compras (Dados Abertos/API).
- ETL de Projetos aprovados, Bolsistas vinculados e Compras realizadas.
- **Integração API FAPES (Projetos, Bolsas e Pagamentos).**
- Classificação de oportunidades.

## 2.4 Release R4 – Google Scholar
**Objetivo:** Métricas acadêmicas e citações.
**Funcionalidades:**
- ETL de perfil do Google Scholar.
- Citações e índice-h.
- Consolidação final dos dados.

---

# 3. Milestones no GitHub
Cada Release acima **DEVE** ter um Milestone correspondente criado no GitHub:
- `v0.1.0 - R1 SigPesq`
- `v0.2.0 - R2 Lattes`
- `v0.3.0 - R3 SigFapes`
- `v1.0.0 - R4 Scholar`
