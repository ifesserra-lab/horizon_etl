# Relatório de ROI e Impacto da Pesquisa
### IFES — Campus Serra · Diretoria de Pesquisa e Pós-Graduação

> **Natureza do documento.** Relatório técnico-metodológico para a Pró-Reitoria de
> Pesquisa, Planejamento Institucional e comissões de avaliação. Combina quatro
> abordagens internacionais — **Payback Framework**, **CAHS Framework**, **bibliometria
> responsável** e **estudos de caso no modelo REF** — com **monetização seletiva**.
> Todos os números vêm de fontes locais auditáveis (Lattes, bolsas/SigPesq, projetos
> FAPES/FACTO, OpenAlex). Onde o dado não existe, o relatório diz explicitamente
> *"dado ausente"* em vez de estimar.
>
> **Convenção de evidência (usada em todo o documento):**
> **[O] Observado** = lido diretamente dos dados · **[I] Inferido** = derivado por regra
> declarada · **[A] Ausente** = não há dado, exige coleta. Cada métrica recebe ainda um
> **nível de confiança** (alto / médio / baixo) e um **risco de viés**.
>
> **Convenção de contagem (dados distintos):** todos os totais institucionais são
> **distintos** — cada obra é contada **uma única vez**, mesmo quando co-autorada ou
> co-orientada por vários docentes do quadro (deduplicação **global por título**). Isso evita
> inflar a produção/orientação por dupla contagem. A contagem **por docente** (em anexos) é a
> produção própria de cada um e **não deve ser somada** entre docentes.
>
> **Convenção de valores financeiros (segurança/privacidade):** este relatório **não expõe
> cifras exatas**. **Totais** aparecem em **ordem de grandeza** ("dezenas/centenas de milhões");
> valores **por coordenador, projeto ou financiadora** aparecem em **faixa + % do total**.
> Faixas: ≤ R$ 100 mil · 100–500 mil · 500 mil–1 mi · 1–5 mi · 5–20 mi · 20–50 mi · > 50 mi.
> A reprodução com cifras exatas exige acesso aos dados-fonte (controlado), via os scripts.

---

## 1. Sumário executivo

A pesquisa do Campus Serra movimenta um fomento **muito superior ao inicialmente
mapeado**: o **fomento de pesquisa consolidado (valor aprovado/contratado) é da ordem de
dezenas de milhões de reais** — quase todo da **FAPES** (99 projetos, 2015–2026), mais uma
parcela da **FACTO** restrita aos **projetos coordenados por docentes do campus** (3 projetos,
poucos milhões — principalmente 1 projeto **FINEP** e contratos com a empresa **Intelliway**).
⚠️ A FACTO **gere centenas de milhões na rede IFES**, mas a **maioria é de outros
campi/coordenadores** e **não entra no saldo do campus Serra** (só conta o projeto cujo
**coordenador** é docente do quadro; participação como equipe não soma).
A produção do quadro de **93 docentes** (unidade de análise)
soma **1.959 itens científicos distintos** (473 artigos, 90 livros, 162 capítulos, 1.234
trabalhos em congressos), **261 titulados distintos** de mestrado/doutorado e **91 ativos
tecnológicos** (majoritariamente softwares; **patentes registradas = 0** no Lattes). *Todos os
totais são distintos: obra co-autorada/dissertação co-orientada conta uma vez.*

**Principais achados (confiança alta, salvo indicação):**

1. **Há base sólida para um painel de inputs e de produção** — fomento, bolsas, produção
   bibliográfica, orientação e produção técnica são todos **observáveis [O]**.
2. **O fomento é altamente concentrado**: **Gini = 0,771** entre coordenadores; os **5
   maiores concentram 70,1%** do orçamento FAPES. Ressalva crítica (corrigida nesta
   versão): **37,8% do orçamento são projetos institucionais/programáticos**,
   não captação individual de pesquisa — **ConectaFapes** (plataforma de PD&I, faixa > R$ 5 mi)
   e **UnAC** (gestão da Universidade Aberta, 4 projetos). **Segregando-os, o Gini cai para
   0,748** (0,742 considerando só quem mantém fomento de pesquisa). A concentração "por
   coordenador" superestima a "por pesquisador" e deve ser lida com cuidado.
3. **O ROI financeiro clássico (%) ainda NÃO é calculável** — não há benefícios
   monetizados (royalties, licenças, receita incremental). **Mas a FACTO destrava parte da
   dimensão econômica** no recorte do campus: **execução real** e **captação externa** dos
   projetos coordenados por docentes (1 **FINEP** + contratos da empresa **Intelliway**) —
   permite **taxa de execução** e **captação externa/privada**, não o ROI% (que segue exigindo
   o lado "benefício"). Valores granulares só em **faixa + % do total**.
4. **Citações existem, mas só parcialmente** (5.793 citações, **FWCI mediano 1,4**,
   226 artigos no top 10% mundial) e cobrem **apenas 64 dos 93 docentes** (casamento por
   DOI via OpenAlex). Servem como panorama, **não** como avaliação individual.
5. **Impacto social/político é hoje uma lacuna total [A]** — não há dado estruturado;
   só pode ser capturado por **narrativa + estudo de caso REF**.

**Indicadores NÃO calculáveis por falta de dados:** ROI financeiro (%), razão
benefício-custo monetizada, alavancagem (externo/institucional), royalties/licenças,
impacto econômico regional, citações em políticas públicas, dados de egressos no mercado.

**Recomendação geral.** Adotar um **painel multidimensional de 7 dimensões** (não um número
único), com **monetização restrita** ao que tem evidência documental (valor de bolsas e de
projetos) e **estudos de caso REF** para o impacto não-monetizável. Em paralelo, fechar as
lacunas de governança de dados (cadastro único de projetos, valor executado, ORCID,
formulário anual de impacto) que hoje impedem o ROI financeiro e o impacto social.

---

## 2. Objetivo e escopo

**O que este relatório mede.** A relação entre **investimento** em pesquisa (projetos e
bolsas) e seus **retornos** científico, de formação, tecnológico e — onde houver evidência —
econômico, em um **painel multidimensional auditável**.

**O que este relatório NÃO mede.** (a) ROI financeiro em %, por ausência de benefícios
monetizados; (b) impacto social/político/territorial quantitativo, por ausência de dado;
(c) atribuição causal produção→projeto específico (a produção do Lattes **não** está
ligada a um projeto financiado); (d) desempenho individual comparável entre áreas.

**Unidades de análise** (o painel deve operar em todos os níveis, nunca colapsando-os):

| Nível | Definição operacional | Fontes |
|---|---|---|
| Instituição | Campus Serra (agregado) | todas |
| Unidade/Área | grande área CNPq / programa (PPComp) | Lattes, PPComp |
| Pesquisador | docente do roster (93) | Lattes, OpenAlex |
| Projeto | projeto FAPES/FACTO/SigPesq | FAPES, FACTO, SigPesq |
| Bolsa | alocação de bolsa | Bolsas/SigPesq |

---

## 3. Dados utilizados

| # | Fonte | Formato | Volume | Período | Chave de integração | Limitação principal |
|---|---|---|---|---|---|---|
| 1 | Currículos Lattes | JSON (154 arq.; **93 = roster**) | 473 artigos, 1.234 congressos, ~2.016 orient. (distintos) | livre | nome / lattes_id | autodeclarado; sem citações; sem DOI em parte |
| 2 | Projetos FAPES | JSON | **99 projetos · dezenas de milhões** | 2015–2026 | coordenador_nome | "contratado" ≠ executado |
| 3 | Bolsas (SigPesq) | JSON | 1.407 aloc. · 749 bolsistas · dezenas de milhões | 2015–2026 | coordenador_nome | **valor_pago = 0** (só alocado) |
| 4 | Projetos FACTO (fundação, rede IFES) | JSON (7 CSVs/projeto) | 111 proj rede; **só 3 de pesquisa coord. pelo campus → poucos milhões** | 2016–2026 | coordenador (∈roster) | maioria de outros campi (fora do saldo) |
| 5 | SigPesq projetos/grupos | XLSX | 98 projetos · grupos | até 2026 | Coordenador/email | sem valor financeiro |
| 6 | OpenAlex (citações) | JSON | 5.793 cit · 64/93 docentes | — | DOI do Lattes | cobertura parcial (só com DOI) |
| 7 | Base PPComp | JSON | 269 discentes | 2015–2026 | nome | orientador em nome curto |
| 8 | Referências SJR/Qualis | CSV/JSON | SCImago + Qualis | — | ISSN | classifica veículo, não artigo |

> **Período coberto:** fomento e bolsas **2015–2026**; produção bibliográfica conforme o
> Lattes de cada docente (sem recorte único). **Recomenda-se padronizar janelas** (ver §12).

---

## 4. Metodologia recomendada

Quatro lentes complementares, deliberadamente **não reduzidas a um número único**:

- **Payback Framework** (Buxton & Hanney, 1996) — classifica o retorno em 5 categorias,
  da produção de conhecimento aos benefícios econômicos amplos. Bom para **mapear** onde
  há retorno e onde não há.
- **CAHS Framework** (Canadian Academy of Health Sciences, 2009) — adiciona a **cadeia de
  impacto** (avanço do conhecimento → capacitação → decisão → impacto → benefício amplo)
  e a noção de **indicadores por estágio**.
- **Bibliometria responsável** (Manifesto de Leiden, 2015; DORA; CoARA) — métricas
  **normalizadas por área/ano/tipo**, sempre acompanhadas de juízo qualitativo; proíbe
  ranking simplista e comparação entre áreas por volume bruto.
- **Estudos de caso REF** (Research Excellence Framework, UK) — para o impacto **além da
  academia**, que não cabe em indicador: narrativa estruturada (problema → pesquisa →
  evidência → trajetória → alcance × significância) com **evidências documentais**.
- **Monetização seletiva** — transversal: só converte em R$ o que tem evidência
  documental; o resto vira narrativa/alcance/significância.

---

## 5. Painel de métricas recomendado

| Dimensão | Indicadores-núcleo | Framework | Como reportar |
|---|---|---|---|
| **A. Inputs** | orçamento (contratado/executado), bolsas, nº projetos, nº pesquisadores, duração | Payback | valor absoluto + por ano/área |
| **B. Científico** | artigos/livros/capítulos/congressos, FWCI, top 10%, colaboração | Bibliometria | normalizado; nunca volume bruto entre áreas |
| **C. Formação** | titulados M/D, IC, orientações concluídas, egressos | CAHS | absoluto + por projeto/área |
| **D. Inovação** | patentes, softwares, registros, produtos, contratos | Payback | absoluto + status (INPI/TRL) |
| **E. Econômico** | captação, alavancagem, B/C, ROI% | Monetização | **só com evidência**; senão omitir |
| **F. Social/político** | políticas, normas, beneficiários, território | REF | narrativa + alcance × significância |
| **G. Estudos de caso** | fichas REF | REF | 1–2 páginas por caso |

A **Tabela 2** (anexo CSV `metricas_roi_pesquisa.csv`) traz todos os indicadores com
dimensão, fonte, disponibilidade e confiança.

---

## 6. Indicadores calculados com os dados disponíveis

> Todos os valores abaixo são **observados [O]** salvo indicação. As **razões por R$
> investido** são marcadas **confiança baixa**: a produção do Lattes **não** está vinculada
> a projeto financiado, então a divisão é uma **proporção institucional bruta**, não uma
> causalidade. Use-as como ordem de grandeza, jamais como "produtividade do real".

### 6.1 Inputs (fomento)

> **Valores em ordem de grandeza (totais) e faixa + % (granular)** — por segurança, sem
> cifra exata. Faixas: ≤100 mil · 100–500 mil · 500 mil–1 mi · 1–5 mi · 5–20 mi · 20–50 mi · >50 mi.

| Indicador | Valor (ordem) | Fonte | Confiança |
|---|---:|---|---|
| Projetos FAPES (concluídos + andamento) | **99** (37 + 62) | FAPES | alto |
| Orçamento FAPES contratado | **dezenas de milhões** | FAPES | alto |
| Valor de bolsas dentro dos projetos FAPES | dezenas de milhões | FAPES | alto |
| Bolsas FAPES (quantidade) | 729 | FAPES | alto |
| Alocações de bolsa (SigPesq) | 1.407 (749 bolsistas) | Bolsas | médio |
| Valor **alocado** em bolsas (SigPesq) | dezenas de milhões | Bolsas | médio (pago=0) |
| **FACTO pesquisa coord. pelo campus (saldo)** | **3 projetos** | FACTO | alto |
| **FACTO — valor aprovado (saldo do campus)** | **poucos milhões** | FACTO | alto |
| **FACTO — valor executado (saldo do campus)** | **poucos milhões** | FACTO | médio |
| FACTO pesquisa na rede IFES (contexto, fora do saldo) | 43 proj · centenas de milhões | FACTO | contexto |
| **Fomento de pesquisa consolidado (FAPES + FACTO-campus)** | **dezenas de milhões** | FAPES+FACTO | médio |
| Projetos de pesquisa declarados (Lattes) | 493 | Lattes | médio |

**FACTO — financiadoras dos projetos coord. pelo campus (faixa + % do saldo):** **FINEP**
(R$ 5–20 mi · ~97%) · **Intelliway Tecnologia** (R$ 100–500 mil · ~3%, 2 contratos de empresa).
→ captação externa competitiva (FINEP) + **contrato privado** (Intelliway). ⚠️ Grandes
financiadoras como INCRA, MEC, Petrobras aparecem na FACTO **mas em projetos de outros
campi/coordenadores** — **não** são captação do campus Serra. Detalhe em `facto_projetos.csv`
(coluna `conta_saldo_campus`).

**Fomento FAPES por ano (faixa):** 2018 (R$ 1–5 mi) · 2021–2022 (R$ 5–20 mi/ano) · **2023
(R$ 5–20 mi, pico)** · 2024–2026 (R$ 1–5 mi a 5–20 mi). Tendência de **crescimento e
volatilidade** (um ou poucos grandes projetos movem o total do ano). Série (faixas) em
`janelas_temporais.csv`.

**Bolsas por tipo (top):** B-UnAC 860 · BPIG 253 · AT-NM 71 · DTI-A 44 · ICJr 42 · EXT 28.
⚠️ **B-UnAC** (Universidade Aberta Capixaba) é majoritariamente **ensino/EAD**, não pesquisa —
não deve entrar no denominador de "investimento em pesquisa" sem segregação.

### 6.2 Produção científica (roster, 93 docentes)

> Todos os números abaixo são **distintos** (obra co-autorada conta 1×, dedup global por título).

| Indicador | Valor (distinto) | Confiança |
|---|---:|---|
| Artigos em periódicos | **473** | alto |
| Livros publicados | 90 | alto |
| Capítulos de livros | 162 | alto |
| Trabalhos completos em congressos | 1.234 | alto |
| **Total de itens científicos** | **1.959** | alto |
| Citações (OpenAlex, por DOI) | 5.794 | médio (64/93; ver ⚠️) |
| FWCI mediano | **1,4** (acima da média mundial) | médio |
| Artigos no top 10% mundial | 226 | médio |

> ⚠️ **Citações (OpenAlex)** ainda podem contar uma obra co-autorada por docentes do quadro
> mais de uma vez (o total vem da soma por docente; o detalhe por DOI único não está no
> resumo). Tratar como **panorama**, não total exato. Demais contagens são distintas.
>
> **Fórmula (baixa confiança):** produção científica por R$ 1 mi ≈ **35 itens/R$ mi**
> (1.959 itens distintos ÷ fomento consolidado, dezenas de milhões). Ordem de grandeza
> institucional; não atribuir a projetos específicos.

### 6.3 Formação e capacidade

Orientações concluídas **por nível** (chaves reais do Lattes, sem misturar níveis —
*stricto sensu* ≠ graduação):

| Nível (tipo de trabalho no Lattes) | Concluídas (distintas) | Confiança |
|---|---:|---|
| **Mestrado** (Dissertação) | **254** | alto |
| **Doutorado / pós-doc** (Tese) | 7 | alto |
| Especialização — *lato sensu* (Monografia) | 372 | alto |
| **Graduação** — TCC + Iniciação Científica | **1.267** | alto |
| Outros (residual) | 116 | médio |
| Mestrado **em andamento** | 124 | alto |
| Doutorado **em andamento** | 4 | alto |

> **Correções metodológicas (acumuladas):** (1) cada nível é contado pela chave correta do
> Lattes (`tipo_trabalho`: mestrado = *Dissertação*; TCC/IC = *Trab. de Conclusão de Curso*) —
> **mestrado ≠ graduação**; (2) **deduplicação global**: dissertação co-orientada por 2+
> docentes conta **uma vez** (o bruto somava 308 mestrado; os **distintos** são **254**).

Capacidade institucional de pós-graduação (programa PPComp):

| Indicador | Valor | Confiança |
|---|---:|---|
| Discentes PPComp (mestrado) | 269 | alto |
| Defesas PPComp | 83 (97 ativos; evasão 89) | alto |

> **Titulados *stricto sensu*** (mestrado + doutorado, distintos) = 254 + 7 = **261**. Fórmula
> (baixa confiança): ≈ **4,7 titulados/R$ mi** (fomento consolidado, dezenas de milhões). **A
> graduação (1.267 TCC/IC) não entra** nesse indicador de titulação *stricto sensu*.

### 6.4 Inovação e produção técnica

| Indicador | Valor | Confiança |
|---|---:|---|
| **Patentes (Lattes)** | **0** | médio (provável subnotificação) |
| Softwares (distintos) | 75 | médio |
| Produtos tecnológicos | 16 | médio |
| Registros (programas/desenhos) | 0 | médio |
| **Ativos tecnológicos (soma, distintos)** | **91** | médio |
| Prêmios e títulos (distintos) | 49 | médio |

> Patentes = 0 é um **alerta de qualidade de dado**, não necessariamente ausência real:
> patentes podem estar em `producao_tecnica` sob outra rubrica ou fora do Lattes (INPI).
> Exige verificação manual / base INPI (§7).

### 6.5 Concentração e equidade do fomento

| Cenário (Gini do orçamento FAPES) | Valor | Leitura |
|---|---:|---|
| **Base — todos os coordenadores** | **0,771** | concentração alta |
| **Sem institucionais (UnAC + ConectaFapes)** | **0,748** | ainda alta, mas menor |
| Só coordenadores com fomento de pesquisa > 0 | 0,742 | pesquisa stricto sensu |
| Top-5 coordenadores (% do orçamento, base) | 70,1% | núcleo pequeno capta a maioria |

⚠️ **Atribuição (recalculado nesta versão):** **37,8% do orçamento** são **projetos
institucionais/programáticos**, não captação individual de pesquisa: **ConectaFapes**
(plataforma de PD&I — coord. Paulo Sérgio dos Santos Júnior) e **UnAC** (4 projetos de gestão
da Universidade Aberta — coord. José Geraldo das Neves Orlandi). Segregando-os, o **Gini cai
de 0,771 → 0,748** (0,742 só pesquisa): a concentração é real, mas parte expressiva é
**infraestrutura/programa**, não desempenho individual. (Faixas em `gini_segregado.csv`.)

---

## 7. Indicadores que exigem enriquecimento externo

| Indicador | Por que falta | Fonte de enriquecimento | Prioridade |
|---|---|---|---|
| Citações completas e normalizadas | Lattes não tem citação; OpenAlex só cobre DOIs (64/93) | OpenAlex, Scopus, WoS, Dimensions, Crossref | **alta** |
| Patentes com status | Lattes vazio/subnotificado | INPI, Espacenet, Lens.org | **alta** |
| Altmetrics (atenção social) | inexistente | Altmetric, PlumX, Dimensions | média |
| Citações em políticas públicas | inexistente | Overton, Policy Commons | **alta** (impacto social) |
| Impacto econômico regional | inexistente | RAIS, IBGE, dados de empresas | média |
| Dados de egressos (mercado) | inexistente | Lattes egressos, LinkedIn, RAIS | **alta** |
| Adoção por empresa/governo | inexistente | contratos, convênios, relatórios | **alta** |
| Identidade unívoca do pesquisador | só nome (ambíguo) | **ORCID**, ID Lattes em todas as bases | **alta** |

---

## 8. Matriz Payback / CAHS aplicada à instituição

Resumo (matriz completa em `matriz_payback_cahs.csv`):

| Framework · Categoria | Indicador possível | Fonte | Calcula agora? | Confiança |
|---|---|---|---|---|
| Payback · Produção de conhecimento | artigos, livros, congressos, FWCI | Lattes, OpenAlex | **Sim** | alto/médio |
| Payback · Benefício p/ pesquisa futura | orientações, projetos, redes, captação recorrente | Lattes, FAPES | **Parcial** | médio |
| Payback · Políticas e práticas | citações em políticas, normas, diretrizes | externo | Não | baixo |
| Payback · Setor/sociedade/educação | egressos, adoção, extensão | externo | Não | baixo |
| Payback · Econômico amplo | royalties, licenças, empregos, receita | ausente | Não | baixo |
| CAHS · Avanço do conhecimento | produção + FWCI + top 10% | Lattes, OpenAlex | **Sim** | médio |
| CAHS · Capacitação | titulados, IC, bolsistas, novas competências | Lattes, PPComp, Bolsas | **Sim** | alto |
| CAHS · Informação p/ decisão | participação em normas/pareceres | ausente | Não | baixo |
| CAHS · Impacto setorial | saúde/educação/território | ausente (narrativa) | Não | baixo |
| CAHS · Benefício econômico/social | monetização seletiva + casos REF | parcial | Parcial | baixo |

---

## 9. Monetização seletiva do ROI

**Princípio:** monetizar **apenas com evidência documental**. O que não tem evidência vira
narrativa de impacto, indicadores de alcance e estudo de caso.

**Pode ser monetizado agora (evidência local):**

> Valores em **ordem de grandeza** (totais); granular em **faixa + %** (`facto_projetos.csv`).

| Item | Valor (ordem) | Base |
|---|---:|---|
| Orçamento FAPES contratado | dezenas de milhões | FAPES |
| Valor de bolsas em projetos FAPES | dezenas de milhões | FAPES |
| Valor alocado em bolsas (SigPesq) | dezenas de milhões | Bolsas (só alocado) |
| **FACTO — aprovado (saldo do campus, coord∈roster)** | **poucos milhões** | FACTO |
| **FACTO — EXECUTADO (saldo do campus)** | **poucos milhões** | FACTO (despesas por rubrica) |
| Captação dos projetos coord. pelo campus: **FINEP** + **Intelliway** (empresa) | faixa + % (`facto_projetos.csv`) | FACTO |

> **Avanço (FACTO, recorte do campus):** a execução financeira real e a **captação externa**
> dos projetos **coordenados por docentes** (1 **FINEP** + contratos da empresa **Intelliway**)
> são monetizáveis com evidência — permitem **taxa de execução** e **captação externa/privada**,
> sem inventar benefício. Os contratos **Intelliway** são caso de **receita de pesquisa
> contratada por empresa**. ⚠️ Os grandes aportes (INCRA, MEC, Petrobras) vistos na FACTO são
> de **outros campi** e **não** contam como captação do campus Serra.

**NÃO deve ser monetizado sem dado adicional:** royalties, licenciamento, receita
incremental, economia gerada, empregos criados, empresas/spin-offs, beneficiários com valor
econômico — **nenhum** tem registro local; monetizá-los seria invenção.

**Fórmulas (a usar SÓ quando houver benefício monetizado real):**
```
ROI financeiro (%)    = ((benefícios monetizados − investimento) / investimento) × 100
Razão benefício-custo = benefícios monetizados / investimento
Alavancagem           = recursos externos captados / investimento institucional
```

**Cenários (estrutura; não preenchível hoje por falta de benefícios monetizados):**
- *Conservador:* só captação documentada (sem projeção de benefício) → **ROI% indefinido**.
- *Intermediário:* + economia/receita com contrato assinado → exige coleta.
- *Ampliado:* + impacto econômico regional modelado → exige base externa (RAIS/IBGE).

> **Veredito:** hoje o numerador de "benefício monetizado" é **vazio**. Reportar ROI% seria
> indefensável. Reportar **captação, alavancagem (quando houver contrapartida) e B/C** é o
> caminho correto assim que o lado "benefício" for coletado.

---

## 10. Estudos de caso de impacto no modelo REF

**Critério de seleção:** interseção de **fomento alto** (FAPES) × **impacto científico**
(FWCI/citações/top 10%) × **potencial de impacto além da academia**. Modelo de ficha em
`estudos_de_caso_ref.md`.

**Candidatos identificados nos dados** (fomento × impacto; nomes de coordenadores são de
domínio público em Lattes/FAPES):

| Coordenador (norm.) | Fomento FAPES (faixa · %) | Projetos | Citações | FWCI | Top 10% |
|---|---|---:|---:|---:|---:|
| paulo sergio dos santos junior | R$ 5–20 mi · ~24%¹ | 1 | 107 | 4,75 | 4 |
| jose geraldo das neves orlandi | R$ 5–20 mi · ~14% | 6 | — | — | — |
| mateus conrad barcellos da costa | R$ 5–20 mi · ~12% | 3 | 3 | 0,13 | 1 |
| karin satie komati | R$ 5–20 mi · ~12% | 6 | 74 | 0,86 | 8 |
| maxwell eduardo monteiro | R$ 1–5 mi · ~9% | 6 | 83 | 3,40 | 9 |

¹ Projeto **ConectaFapes** (plataforma de PD&I) — alto orçamento, natureza de
**infraestrutura institucional**; bom candidato a caso de **impacto institucional/de
capacidade**, não de impacto científico individual. (Os projetos **UnAC**, de gestão da
Universidade Aberta, são do coord. *jose geraldo das neves orlandi* — candidatos
a impacto **educacional/territorial**.) "—" = coordenador sem casamento no OpenAlex (sem
DOIs indexados); exige enriquecimento.

> Os melhores casos REF combinam **fomento + FWCI alto + trajetória de uso externo**.
> Maxwell Monteiro (FWCI 3,40; 9 artigos top 10%; 6 projetos) e o programa UnAC são os
> dois perfis mais promissores — um pelo **impacto científico**, outro pelo **alcance
> educacional**. As **evidências de impacto além da academia ainda precisam ser coletadas**
> (formulário de impacto, §11/§15).

---

## 11. Recomendações institucionais

**Governança**
- Criar um **Comitê de Avaliação de Impacto da Pesquisa** com mandato metodológico
  (define indicadores, audita, publica o painel anual).
- Separar formalmente **projetos institucionais/programáticos** (ex.: UnAC) de
  **pesquisa stricto sensu** nos indicadores de concentração e produtividade.

**Coleta de dados**
- **Cadastro único de projetos** com: valor contratado **e executado**, equipe, produtos
  esperados × entregues, parceiros, contrapartida institucional.
- **Formulário anual de impacto** (modelo REF-light) por projeto/grupo.
- Registrar **valor pago** de bolsas (hoje = 0) e **agência/fonte** real (hoje só "IFES-SERRA").

**Sistemas**
- Integração **Lattes ↔ ORCID ↔ SigPesq** com identificador único (acaba a ambiguidade de nome).
- Pipeline anual **OpenAlex/Crossref** para citações e FWCI; **INPI/Lens** para PI;
  **Overton** para citações em políticas.

**Indicadores anuais (mínimo viável):** inputs (fomento, bolsas), produção normalizada
(FWCI, top 10%), formação (titulados, IC), inovação (PI com status), concentração (Gini),
+ **2 estudos de caso REF/ano**.

**Prestação de contas (agências e sociedade):** painel público com inputs × produção ×
formação + casos de impacto narrados — **sem** ROI% até haver benefício monetizado.

---

## 12. Limitações e riscos

| Risco | Descrição | Mitigação |
|---|---|---|
| **Viés de cobertura** | OpenAlex só cobre 64/93 (DOIs); Lattes subnotifica PI | enriquecer; declarar cobertura sempre |
| **Atribuição indevida** | produção do Lattes não está ligada a projeto financiado | não dividir produção por fomento como causalidade; usar janelas temporais |
| **Comparação entre áreas** | volume bruto favorece áreas de alta publicação | usar **só** indicadores normalizados (FWCI, percentil) |
| **Supermonetização** | tentar pôr R$ em impacto sem evidência | monetização seletiva; narrativa para o resto |
| **Concentração mal lida** | projeto institucional infla Gini "por pesquisador" | segregar institucional × pesquisa |
| **Lacunas de dado** | social/político/econômico ausentes | coleta dirigida (§7, §15) |
| **valor_pago = 0** | bolsas só têm "alocado" | exigir execução financeira |

---

## 13. Plano de implementação

| Prazo | Ações | Entregável |
|---|---|---|
| **Curto (0–3 m)** | padronizar janelas temporais; recalcular Gini segregando UnAC; pipeline OpenAlex p/ os 93; revisar patentes no INPI | painel v1 (inputs + científico + formação) |
| **Médio (3–12 m)** | cadastro único de projetos; formulário anual de impacto; integração ORCID; 2 estudos de caso REF; enriquecer egressos | painel v2 + 2 casos REF |
| **Longo (12–24 m)** | Overton (políticas); INPI/Lens (PI); modelagem de impacto econômico regional; auditoria metodológica externa | painel v3 com dimensão social/econômica |

---

## 14. Referências

> *Citações não verificadas nesta execução* (sem checagem automática de DOI/contagem nesta
> rodada). DOIs informados quando conhecidos; números de citação **não** foram inventados.

1. **Buxton, M.; Hanney, S. (1996).** *How can payback from health services research be
   assessed?* Journal of Health Services Research & Policy, 1(1), 35–43.
   DOI: 10.1177/135581969600100107.
2. **Canadian Academy of Health Sciences (2009).** *Making an Impact: A Preferred Framework
   and Indicators to Measure Returns on Investment in Health Research* (CAHS Framework).
3. **Hicks, D.; Wouters, P.; Waltman, L.; de Rijcke, S.; Rafols, I. (2015).** *The Leiden
   Manifesto for research metrics.* Nature, 520, 429–431. DOI: 10.1038/520429a.
4. **DORA (2012).** *San Francisco Declaration on Research Assessment.*
5. **CoARA (2022).** *Agreement on Reforming Research Assessment.*
6. **REF (2014; 2021).** *Research Excellence Framework — Assessment framework and guidance
   on submissions* (impact case studies). Research England / HEFCE.
7. **Penfield, T.; Baker, M. J.; Scoble, R.; Wykes, M. C. (2014).** *Assessment, evaluations,
   and definitions of research impact: A review.* Research Evaluation, 23(1), 21–32.
   DOI: 10.1093/reseval/rvt021.
8. **Greenhalgh, T. et al. (2016).** *Research impact: a narrative review.* BMC Medicine,
   14:78. DOI: 10.1186/s12916-016-0620-8 (Research Impact Framework / comparativo).
9. **Waltman, L. (2016).** *A review of the literature on citation impact indicators.*
   Journal of Informetrics, 10(2), 365–391. DOI: 10.1016/j.joi.2016.02.007.
10. **Priem, J.; Piwowar, H.; Orr, R. (2022).** *OpenAlex: A fully-open index of scholarly
    works…* arXiv:2205.01833.

---

## 15. Execução do plano de curto prazo (0–3 meses)

As quatro ações de curto prazo (§13) foram **executadas** nesta rodada. Resultados:

### 15.1 Padronização de janelas temporais
Janela-padrão **2015–2026** (alinhada ao fomento FAPES) + janela recente **2021–2025**.
Aplicada à produção de artigos (dedup por título):

| Métrica | Valor |
|---|---:|
| Artigos distintos (total, todas as datas) | 473 |
| Artigos **na janela 2015–2026** | **356** |
| Artigos fora da janela (pré-2015) | 117 |
| Artigos na janela recente 2021–2025 | 183 |
| Fomento FAPES na janela 2015–2026 | dezenas de milhões (todo) |

→ Recomenda-se reportar os indicadores de produção **dentro da janela** para comparabilidade
com o fomento. Série completa em `janelas_temporais.csv`. **Confiança alta** (datas do Lattes).

### 15.2 Gini recalculado segregando UnAC + ConectaFapes
| Cenário | Gini |
|---|---:|
| Base (todos) | 0,771 |
| **Sem institucionais (UnAC + ConectaFapes)** | **0,748** |
| Só pesquisa stricto sensu (>0) | 0,742 |

Institucional = **37,8%** do orçamento FAPES. Conclusão: a concentração é **real e
alta** mesmo após segregar, mas **mais de 1/3 do "fomento à pesquisa" é, na verdade,
infraestrutura/programa institucional** — fato que deve constar em qualquer leitura de ROI.

### 15.3 Pipeline OpenAlex para os 93
Pipeline re-executado sobre **todo o roster (93)**. Cobertura: **64/93 (68,8%)** casados por
**DOI**; **29 sem casamento** — porque **não têm DOIs indexados no Lattes**, não por falha do
pipeline. Busca exploratória **por nome** (não confirmada por ORCID) encontrou perfil OpenAlex
para **21 dos 29** — mas com **forte risco de homônimo** (ex.: um perfil com 138 trabalhos e 0
citações é claramente outra pessoa). **Confiança baixa**; não incorporado às métricas. Ação
correta: **DOIs/ORCID no Lattes** (lista em `cobertura_openalex.csv`, candidatos por nome em
`openalex_busca_nome_29.json`).

### 15.4 Revisão de patentes (INPI)
O Lattes do roster traz **0 patentes** e **0 softwares com patente** (apenas softwares
sem patente). Logo, **não há o que validar a partir do Lattes** — a checagem no **INPI** deve
ser feita **por nome do inventor**. Gerada worklist dos 93 docentes priorizando os **com
produção técnica** (software/produto) — mais propensos a depósito. **INPI não tem API
pública estável** (busca com sessão/captcha): a verificação é **manual/RPA**. Lista em
`patentes_worklist_inpi.csv`. **Conclusão:** patente é uma **lacuna de dado**, não
necessariamente ausência real de PI.

> **Efeito no ROI:** §15.1 e §15.2 **melhoram a defensabilidade** (comparabilidade temporal e
> leitura correta da concentração); §15.3 e §15.4 confirmam que **citações completas e
> patentes seguem dependendo de enriquecimento externo** (ORCID/DOI e INPI).

---

### Anexos (em `output/`)
`metricas_roi_pesquisa.csv` · `matriz_payback_cahs.csv` · `por_coordenador.csv` ·
`dicionario_dados.md` · `estudos_de_caso_ref.md` · `lacunas_e_recomendacoes.md` ·
`roi_intermediate.json` · `relatorio_roi_pesquisa.json` · **(plano curto prazo)**
`janelas_temporais.csv` · `gini_segregado.csv` · `cobertura_openalex.csv` ·
`patentes_worklist_inpi.csv` · `openalex_busca_nome_29.json` · `plano_curto_prazo.json` ·
`scripts/` (`02_metricas_roi.py`, `03_relatorio.py`, `04_plano_curto_prazo.py`)

*Gerado a partir de dados locais do repositório horizon_etl. Reprodutível via
`output/scripts/02_metricas_roi.py`.*
