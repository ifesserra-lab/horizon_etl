# Lacunas de Dados e Recomendações

Lista de dados ausentes ou de baixa qualidade que **limitam** a avaliação de ROI, com
prioridade e o impacto de cada lacuna sobre as dimensões do retorno.

> Prioridade: 🔴 alta · 🟡 média · 🟢 baixa.
> Compromete: F = financeiro · C = científico · S = social · T = tecnológico · Fo = formação.

---

## 1. Lacunas críticas (impedem dimensões inteiras)

| # | Lacuna | O que falta | Como coletar | Prio. | Compromete |
|---|---|---|---|---|---|
| 1 | **Benefício monetizado** | royalties, licenças, contratos, receita, economia | NIT, contratos, convênios | 🔴 | **F** (ROI% impossível) |
| 2 | **Vínculo produção↔projeto** | qual produto saiu de qual projeto financiado | cadastro único + ID de projeto | 🔴 | C, T, Fo (atribuição) |
| 3 | **Impacto social/político** | políticas, normas, beneficiários, território | formulário de impacto + Overton | 🔴 | **S** (dimensão inteira) |
| 4 | **Valor executado de bolsas** | `valor_pago_total = 0` em toda a base | execução financeira SigPesq | 🔴 | F (só "alocado" hoje) |
| 5 | **Identificador único** | só nome (homônimos, abreviações) | ORCID + ID Lattes em todas as bases | 🔴 | todas (join frágil) |

## 2. Lacunas que reduzem confiança (corrigíveis com enriquecimento)

| # | Lacuna | O que falta | Como coletar | Prio. | Compromete |
|---|---|---|---|---|---|
| 6 | **Cobertura de citações** | 29/93 docentes sem casamento OpenAlex | DOIs no Lattes; Scopus/WoS/Dimensions | 🔴 | C |
| 7 | **Patentes (status)** | Lattes mostra 0 patentes (subnotif.) | INPI, Lens.org, Espacenet | 🔴 | T |
| 8 | **Egressos no mercado** | inexistente | Lattes egressos, RAIS, LinkedIn | 🔴 | Fo, S |
| 9 | **Contrapartida institucional** | valor próprio aportado por projeto | cadastro de projetos | 🟡 | F (alavancagem) |
| 10 | ~~Valor FACTO~~ **RESOLVIDO** | — (era erro de parsing) | parser FACTO incluído (`02_metricas_roi.py`) | ✅ | F (centenas de mi aprovado / dezenas de mi executado, pesquisa) |
| 11 | **Segregação ensino × pesquisa** | B-UnAC (860 bolsas) mistura EAD e pesquisa | flag de natureza no cadastro | 🟡 | F (denominador) |
| 12 | **Janela temporal padronizada** | produção sem recorte único vs fomento 2015–26 | regra de janela no pipeline | 🟡 | C, T (comparabilidade) |
| 13 | **Altmetrics** | atenção social/midiática | Altmetric, PlumX | 🟢 | S |

## 3. Problemas de qualidade observados

- **Duplicidade** de produções por co-autoria (mitigado por dedup de título por docente).
- **Variações de nome** entre Lattes / FAPES / Bolsas (join por nome normalizado, médio).
- **`instituicao_sigla` = "IFES - SERRA"** em todas as bolsas — não identifica a **agência**
  real (FAPES/CAPES/CNPq); o tipo da bolsa (B-UnAC, BPIG…) é o melhor proxy hoje.
- **Datas mistas** na base PPComp (sentinela 1905 inválida descartada).
- **Concentração distorcida**: projetos institucionais/programáticos (ConectaFapes + UnAC,
  37,8% do orçamento) inflam o Gini "por coordenador" — já segregados (0,771 → 0,748).

---

## 4. Recomendações por prioridade

**🔴 Curto prazo (0–3 meses) — destrava o painel v1**
1. Rodar pipeline **OpenAlex/Crossref** para os 93 (subir cobertura de citações).
2. **Recalcular concentração** segregando o projeto UnAC.
3. **Verificar patentes** no INPI/Lens para os 93.
4. Padronizar **janela temporal** (ex.: produção e fomento por ano-calendário).

**🟡 Médio prazo (3–12 meses) — destrava atribuição e formação**
5. Implantar **cadastro único de projetos** com ID propagado a bolsas e produtos.
6. Criar **formulário anual de impacto** (modelo REF) por projeto/grupo.
7. Integrar **ORCID + ID Lattes**.
8. Coletar **dados de egressos**.

**🟢 Longo prazo (12–24 meses) — destrava social e econômico**
9. **Overton** (citações em políticas), **RAIS/IBGE** (impacto econômico regional).
10. **Auditoria metodológica** externa do painel.
11. Registrar **benefícios monetizados** (NIT/contratos) — só então calcular ROI%.

---

## 5. Efeito das lacunas sobre o ROI (resumo)

| Dimensão de ROI | Estado atual | Principal bloqueio |
|---|---|---|
| Científico | **calculável** (parcial) | cobertura de citações (#6) |
| Formação | **calculável** | vínculo com projeto (#2), egressos (#8) |
| Inovação/Tecnológico | **parcial** | patentes/status (#7), vínculo (#2) |
| Financeiro | **bloqueado** | benefício monetizado (#1), executado (#4) |
| Social/Político | **bloqueado** | dado inexistente (#3) |
| Institucional | **calculável** | segregação ensino×pesquisa (#11) |
