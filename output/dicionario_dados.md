# Dicionário de Dados — ROI da Pesquisa (IFES Campus Serra)

Inventário das fontes locais usadas no relatório, com campos, volume, chaves de
integração e problemas de qualidade observados. **Não há campos inventados** — apenas o
que existe nos arquivos.

> Legenda de qualidade: ✅ confiável · ⚠️ usar com ressalva · ❌ ausente/inutilizável.

---

## 1. Currículos Lattes — `data/lattes_json/*.json`

- **Formato:** JSON, 1 arquivo por currículo. **154 arquivos**; o roster institucional
  oficial são **93 docentes** (`generate_docentes_executive.ROSTER_IDS`). Os 61 restantes
  são coautores/externos e **não** entram na unidade de análise.
- **Chave:** `lattes_id` (16 dígitos no nome do arquivo) · nome (para join com fomento).

| Seção (top-level) | Conteúdo | Uso no ROI | Qualidade |
|---|---|---|---|
| `informacoes_pessoais` | nome, IDs | identificação | ✅ |
| `producao_bibliografica.artigos_periodicos` | título, ano, autores, revista, issn, doi, qualis | produção científica, citações (DOI) | ⚠️ DOI parcial; dups por título |
| `producao_bibliografica.livros_publicados` / `capitulos_livros` | título, ano | produção científica | ✅ |
| `producao_bibliografica.trabalhos_completos_congressos` | título, ano, evento | produção científica | ⚠️ muitos itens; dups |
| `orientacoes.concluidas.{mestrado,doutorado,pos_doutorado,especializacao,tcc,iniciacao_cientifica,outros}` | título, orientando, `tipo_trabalho` | formação por nível | ✅ chaves separadas por nível — **mestrado (Dissertação) ≠ graduação (TCC/IC)** |
| `orientacoes.em_andamento.{...}` | idem | formação em curso | ✅ |
| `patentes_registros.{patentes,programas_computador,desenhos_industriais}` | listas | inovação/PI | ⚠️ vazias no roster (subnotif.) |
| `producao_tecnica.{softwares_*,produtos_tecnologicos,...}` | título, ano, tipo | inovação | ⚠️ autodeclarado |
| `premios_titulos` | descrição, ano | reconhecimento | ⚠️ |
| `projetos_pesquisa` | nome, anos, integrantes, **financiadores (texto)** | inputs (declarado) | ⚠️ sem valor R$ |
| `areas_de_atuacao` | grande_area, area | normalização por área | ✅ |
| `linhas_de_pesquisa`, `bancas`, `eventos`, `atuacao_profissional` | — | contexto | ⚠️ |

**Problemas:** variações de nome (homônimos, abreviações); produções sem DOI; dups por
co-autoria; áreas heterogêneas; ausência de citações; PI subnotificada; autodeclaração.

---

## 2. Projetos FAPES — `data/exports/projetos-fapes/ifes-campus-serra-projetos-concluidos-em-andamento.json`

- **Formato:** JSON `{metadata, resumo, projetos}`. `projetos` é um **dict** com 5 listas
  **disjuntas** (verificado por `projeto_id`): `concluidos` (37), `em_andamento` (27),
  `status_em_andamento_prazo_encerrado` (35), `..._prazo_futuro` (0), `..._sem_prazo_valido` (0).
  **Universo = 99 projetos.**
- **Chave:** `coordenador_nome` (join com Lattes/bolsas por nome normalizado).

| Campo | Tipo | Uso | Qualidade |
|---|---|---|---|
| `projeto_id` | int | dedup | ✅ |
| `projeto_titulo` | str | caso REF | ✅ |
| `coordenador_nome` | str | join | ⚠️ nome (sem ID) |
| `ano` | int | série temporal | ✅ |
| `orcamento_contratado` | float (R$) | **input principal** | ✅ contratado (≠ executado) |
| `valor_bolsas`, `quantidade_bolsas` | float/int | bolsas no projeto | ✅ |
| `rubricas`, `bolsas` | listas aninhadas | detalhe | ⚠️ |
| `projeto_data_inicio/fim_previsto` | data | duração/janela | ✅ |

**Totais (resumo, ordem de grandeza):** dezenas de milhões contratado · dezenas de milhões
em bolsas · 729 bolsas. *(Cifras exatas omitidas por segurança; ver convenção no relatório.)*

---

## 3. Bolsas (SigPesq) — `data/exports/bolsistas/ifes-campus-serra-bolsistas.json`

- **Formato:** JSON `{metadata, bolsistas_unicos (749), alocacoes (1407)}`.
- **Chave:** `coordenador_nome`; `bolsista_pesquisador_id/nome`.

| Campo | Tipo | Uso | Qualidade |
|---|---|---|---|
| `bolsa_sigla` / `bolsa_nome` | str | tipo (B-UnAC, BPIG…) | ✅ |
| `bolsa_nivel_nome` / `bolsa_nivel_valor` | str/num | nível | ⚠️ rótulos mistos |
| `valor_alocado_total` | float | input bolsas | ⚠️ só alocado |
| `valor_pago_total` | float | execução | ❌ **= 0 em toda a base** |
| `formulario_bolsa_inicio/termino` | data | janela | ✅ |
| `instituicao_sigla` | str | "agência" | ❌ só "IFES - SERRA" (não é a agência real) |
| `coordenador_nome`, `projeto_id/titulo` | str | join | ⚠️ |

**Ressalva:** **B-UnAC** (860 de 1.407) é Universidade Aberta Capixaba (ensino), não
pesquisa — segregar antes de usar como "investimento em pesquisa".

---

## 4. Projetos FACTO — `data/exports/projetos-facto/facto_projects_full.json`

- **Formato:** JSON `{projects: [111]}`; cada item `{id, name, csv, ...}`. O campo **`csv` é um
  dict de 7 sub-CSVs já parseados** (lista de dicts): `Informações do projeto`,
  **`Recursos por rubrica`** (Aprovado/Liberado/**Executado**), `Pagamento PF`, `Pagamento PJ`,
  `Equipe`, `Plano de trabalho`, `Documentos`.
- **Campos-chave (Informações):** `Coordenador`, `Financiadora`, `Data de início/vigência/
  encerramento`, `Tipo de Projeto`, **`Valor aprovado`**. Rubrica traz **`Executado`** (R$).
- **Volume:** 111 projetos (87 com ficha). **Pesquisa/PD&I/Inovação = 43 proj · centenas de
  milhões aprovado · dezenas de milhões executado** (ordem de grandeza). Não-pesquisa
  (ensino/extensão/seletivo/concurso) = 44 proj · centenas de milhões (fora do ROI de pesquisa).
- **Qualidade:** ✅ valor aprovado e executado por projeto; ✅ financiadora real (MEC, FINEP,
  INCRA, Petrobras…). ⚠️ 24 projetos sem ficha; classificação por `Tipo de Projeto`.
- **Chave:** `Coordenador` (nome). **Nota:** versão anterior deste relatório **descartou a
  FACTO por engano** (erro de parsing do campo `csv`); corrigido — é a fonte mais rica de
  valor financeiro **executado**.

---

## 5. SigPesq projetos/grupos — `data/raw/sigpesq/research_projects|research_group/*.xlsx`

- **Formato:** XLSX. `research_projects`: **98 linhas × 22 colunas** — `Inicio, Fim, Titulo,
  Coordenador, EmailCoordenador, Pesquisadores, Estudantes, QtdOutros, GrupoPesquisa…`
- **Uso:** equipes, grupos, datas (capacidade institucional). ❌ **sem valor financeiro**.
- **Chave:** `Coordenador`/`EmailCoordenador` (e-mail é a melhor chave disponível).
- `advisorships/` por ano (2016–2026): orientações por ano (não consolidado neste relatório).

---

## 6. OpenAlex (citações) — `data/exports/docentes/openalex_citacoes.json`

- **Formato:** JSON `{docentes:[…]}`, casado por **DOI** do Lattes.
- **Cobertura:** **64 de 93** docentes têm ao menos 1 obra indexada.
- **Campos:** `citacoes_total, h_index, g_index, m_index, fwci_medio, artigos_top10pct,
  artigos_top1pct, top_artigos[]`.
- **Qualidade:** ⚠️ cobertura parcial (só com DOI); menor que Google Scholar; consistente
  entre docentes (mesma régua). **Não** usar como avaliação individual.

---

## 7. Base PPComp — `data/mestrado/base_de_dados_ppcomp.json`

- **Formato:** lista de 269 discentes: `coorte, matricula, nome_completo, orientador1/2,
  coorientador, bolsista, data_defesa, situacao, observacoes`.
- **Uso:** formação (mestrado). 83 defesas, 97 ativos, evasão 89.
- **Qualidade:** ⚠️ orientador em nome curto; datas mistas (sentinela 1905 inválida).

---

## 8. Referências SJR/Qualis — `data/reference/{scimago.csv, qualis.csv, qualis_conferencias.json}`

- **Uso:** classificar **veículo** (não o artigo) por ISSN — quartil SJR, estrato Qualis.
- **Qualidade:** ✅ para o veículo; ⚠️ não mede impacto do artigo individual.

---

## Chaves de integração (resumo)

| Entre | Chave usada | Robustez |
|---|---|---|
| Lattes ↔ FAPES ↔ Bolsas | **nome normalizado** do coordenador/docente | ⚠️ média (homônimos) |
| Lattes ↔ OpenAlex | **DOI** do artigo | ✅ alta (1:1) quando há DOI |
| Lattes ↔ SigPesq | nome / e-mail | ⚠️ média |
| Projeto ↔ Produção | **inexistente** | ❌ exige cadastro único |

> **Recomendação central:** adotar **ORCID + ID Lattes** em todas as bases e um
> **identificador de projeto** propagado para bolsas e produtos — elimina o join frágil
> por nome e habilita a atribuição produção→projeto (hoje impossível).
