# Statement of Work (SOW)
**Projeto:** Horizon ETL
**Data:** 06/01/2026
**Autor:** Antigravity (Senior PM)
**Versão:** 1.0

---

# 1. Introdução
## 1.1 Propósito
Este documento define o escopo, objetivos e entregáveis do projeto **Horizon ETL**. O projeto visa criar uma infraestrutura de dados robusta para capturar, transformar e centralizar informações de diversas fontes relacionadas à pesquisa e extensão.

## 1.2 Justificativa
A gestão eficiente de Pesquisa, Extensão e Pós-Graduação requer dados consolidados para definir políticas de apoio assertivas. Atualmente, a dispersão dessas informações dificulta a transparência e a conectividade entre atores acadêmicos e o mercado.
Este projeto é necessário para:
- **Gestão Baseada em Dados**: Permitir que a gestão do campus defina políticas de apoio baseadas em evidências.
- **Transparência**: Promover o acesso público às informações de pesquisa e extensão.
- **Conectividade**: Facilitar a busca de alunos por projetos, professores por parcerias e empresas por pesquisadores.

---

# 2. Escopo do Projeto

## 2.1 O que ESTÁ no Escopo (In-Scope)
O foco exclusivo é o processo de **ETL (Extract, Transform, Load)**.
- **Extração de Dados**:
    - Sistemas de gestão de projetos da instituição de ensino.
    - Google Scholar (metadados acadêmicos).
    - FAPES (editais, fomento, **projetos, bolsistas e compras**).
    - Plataforma Lattes (currículos e produções).
- **Processamento**:
    - Orquestração de fluxos de dados.
    - Limpeza e normalização das informações.
- **Armazenamento**:
    - Carga em banco de dados centralizado.

## 2.2 O que NÃO ESTÁ no Escopo (Out-Scope)
- Desenvolvimento de front-ends ou dashboards para visualização final (apenas a disponibilaização dos dados).
- Análises de dados complexas ou Machine Learning (nesta fase).
- Alterações nos sistemas fonte.
- Qualquer atividade que não seja estritamente relacionada ao pipeline de ETL.

---

# 3. Objetivos de Negócio
1.  **Centralização**: Unificar dados dispersos em uma única fonte da verdade.
2.  **Transparência Ativa**: Disponibilizar dados para consulta da sociedade.
3.  **Fomento à Inovação**: Reduzir a fricção na conexão entre academia e mercado.

---

# 4. Stakeholders
- **Alunos**: Em busca de oportunidades e orientadores.
- **Professores**: Em busca de parcerias e visibilidade.
- **Empresários / Empresas Públicas**: Em busca de expertise e inovação.
- **Gestão do Campus**: Para tomada de decisão estratégica.

---

# 5. Premissas e Restrições
## 5.1 Premissas Técnicas
- **Linguagem**: [Python](https://www.python.org/).
- **Orquestração**: [Prefect](https://www.prefect.io/) (Gestor de Fluxo).
- **Infraestrutura de Banco de Dados**: [Supabase](https://supabase.com/).
- **Idempotência**: O sistema deve ser idempotente, permitindo rodar diversas vezes as fontes de dados e obtendo o mesmo resultado final (sem duplicatas).

## 5.2 Restrições
- O projeto deve respeitar as limitações de acesso e _rate limits_ das fontes de dados externas.
