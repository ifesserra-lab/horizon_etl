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

---

## 1. Sumário executivo

A pesquisa do Campus Serra movimenta um volume de fomento **expressivo e crescente**:
**R$ 48,5 milhões** em orçamento FAPES contratado em **99 projetos** (2015–2026), com
pico em **2023 (R$ 18,5 mi)**. A produção do quadro de **93 docentes** (unidade de análise)
soma **2.346 itens científicos** (549 artigos, 96 livros, 182 capítulos, 1.519 trabalhos
em congressos), **315 titulados** de mestrado/doutorado e **93 ativos tecnológicos**
(majoritariamente softwares; **patentes registradas = 0** no Lattes).

**Principais achados (confiança alta, salvo indicação):**

1. **Há base sólida para um painel de inputs e de produção** — fomento, bolsas, produção
   bibliográfica, orientação e produção técnica são todos **observáveis [O]**.
2. **O fomento é altamente concentrado**: **Gini = 0,771** entre coordenadores; os **5
   maiores concentram 70,1%** do orçamento FAPES. Ressalva crítica (corrigida nesta
   versão): **37,8% do orçamento (R$ 18,3 mi) são projetos institucionais/programáticos**,
   não captação individual de pesquisa — **ConectaFapes** (plataforma de PD&I, R$ 11,6 mi)
   e **UnAC** (gestão da Universidade Aberta, R$ 6,7 mi em 4 projetos). **Segregando-os, o
   Gini cai para 0,748** (0,742 considerando só quem mantém fomento de pesquisa). A
   concentração "por coordenador" superestima a "por pesquisador" e deve ser lida com cuidado.
3. **O ROI financeiro clássico NÃO é calculável com defensabilidade** — não há
   benefícios monetizados (royalties, licenças, contratos, receita incremental) nem
   valor de contrapartida institucional. Reportar um "%" de ROI aqui seria **indefensável**.
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
| 1 | Currículos Lattes | JSON (154 arq.; **93 = roster**) | 549 artigos, 1.519 congressos, 2.345 orient. | livre | nome / lattes_id | autodeclarado; sem citações; sem DOI em parte |
| 2 | Projetos FAPES | JSON | **99 projetos · R$ 48,5 mi** | 2015–2026 | coordenador_nome | "contratado" ≠ executado |
| 3 | Bolsas (SigPesq) | JSON | 1.407 aloc. · 749 bolsistas · R$ 17,0 mi | 2015–2026 | coordenador_nome | **valor_pago = 0** (só alocado) |
| 4 | Projetos FACTO | JSON | 111 projetos | — | name (texto) | **sem valor** confiável |
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

| Indicador | Valor | Fonte | Confiança |
|---|---:|---|---|
| Projetos FAPES (concluídos + andamento) | **99** (37 + 62) | FAPES | alto |
| Orçamento FAPES contratado | **R$ 48.547.974** | FAPES | alto |
| Valor de bolsas dentro dos projetos FAPES | R$ 26.379.575 | FAPES | alto |
| Bolsas FAPES (quantidade) | 729 | FAPES | alto |
| Alocações de bolsa (SigPesq) | 1.407 (749 bolsistas) | Bolsas | médio |
| Valor **alocado** em bolsas (SigPesq) | R$ 16.991.685 | Bolsas | médio (pago=0) |
| Projetos FACTO | 111 | FACTO | baixo (sem valor) |
| Projetos de pesquisa declarados (Lattes) | 493 | Lattes | médio |

**Fomento FAPES por ano (R$):** 2018 ≈ 3,28 mi · 2021 ≈ 5,78 mi · 2022 ≈ 6,34 mi ·
**2023 ≈ 18,52 mi** · 2024 ≈ 2,96 mi · 2025 ≈ 3,95 mi · 2026 ≈ 6,09 mi. Tendência de
**crescimento e volatilidade** (um ou poucos grandes projetos movem o total do ano).

**Bolsas por tipo (top):** B-UnAC 860 · BPIG 253 · AT-NM 71 · DTI-A 44 · ICJr 42 · EXT 28.
⚠️ **B-UnAC** (Universidade Aberta Capixaba) é majoritariamente **ensino/EAD**, não pesquisa —
não deve entrar no denominador de "investimento em pesquisa" sem segregação.

### 6.2 Produção científica (roster, 93 docentes)

| Indicador | Valor | Confiança |
|---|---:|---|
| Artigos em periódicos (dedup) | **549** | alto |
| Livros publicados | 96 | alto |
| Capítulos de livros | 182 | alto |
| Trabalhos completos em congressos | 1.519 | alto |
| **Total de itens científicos** | **2.346** | alto |
| Citações (OpenAlex, por DOI) | 5.793 | médio (64/93) |
| FWCI mediano | **1,4** (acima da média mundial) | médio |
| Artigos no top 10% mundial | 226 | médio |

> **Fórmula (baixa confiança):** produção científica por R$ 1 mi = 2.346 / 48,55 = **48,3
> itens/R$ mi**. Ordem de grandeza institucional; não atribuir a projetos específicos.

### 6.3 Formação e capacidade

Orientações concluídas **por nível** (chaves reais do Lattes, sem misturar níveis —
*stricto sensu* ≠ graduação):

| Nível (tipo de trabalho no Lattes) | Concluídas | Confiança |
|---|---:|---|
| **Mestrado** (Dissertação) | **308** | alto |
| **Doutorado / pós-doc** (Tese) | 7 | alto |
| Especialização — *lato sensu* (Monografia) | 381 | alto |
| **Graduação** — TCC + Iniciação Científica | **1.369** | alto |
| Outros (residual) | 194 | médio |
| Mestrado **em andamento** | 136 | alto |
| Doutorado **em andamento** | 4 | alto |

> **Correção metodológica:** uma versão anterior somava TCC + IC + especialização sob o
> rótulo "IC/outras", **misturando graduação com pós-graduação**. Agora cada nível é
> contado pela chave correta do Lattes (verificado pelo campo `tipo_trabalho`:
> mestrado = *Dissertação*; TCC/IC = *Trabalho de Conclusão de Curso*). **Mestrado e
> graduação são linhas distintas.**

Capacidade institucional de pós-graduação (programa PPComp):

| Indicador | Valor | Confiança |
|---|---:|---|
| Discentes PPComp (mestrado) | 269 | alto |
| Defesas PPComp | 83 (97 ativos; evasão 89) | alto |

> **Titulados *stricto sensu*** (mestrado + doutorado) = 308 + 7 = **315**. Fórmula
> (baixa confiança): 315 / 48,55 = **6,5 titulados/R$ mi**. **A graduação (1.369 TCC/IC)
> não entra** nesse indicador de titulação *stricto sensu*.

### 6.4 Inovação e produção técnica

| Indicador | Valor | Confiança |
|---|---:|---|
| **Patentes (Lattes)** | **0** | médio (provável subnotificação) |
| Softwares | 77 | médio |
| Produtos tecnológicos | 16 | médio |
| Registros (programas/desenhos) | 0 | médio |
| **Ativos tecnológicos (soma)** | **93** | médio |
| Prêmios e títulos | 49 | médio |

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

⚠️ **Atribuição (recalculado nesta versão):** **37,8% do orçamento (R$ 18,3 mi)** são
**projetos institucionais/programáticos**, não captação individual de pesquisa:
**ConectaFapes** (R$ 11,6 mi, plataforma de PD&I — coord. Paulo Sérgio dos Santos Júnior) e
**UnAC** (R$ 6,7 mi em 4 projetos de gestão da Universidade Aberta — coord. José Geraldo das
Neves Orlandi). Segregando-os, o **Gini cai de 0,771 → 0,742**: a concentração é real, mas
parte expressiva é **infraestrutura/programa**, não desempenho individual. (Detalhe em
`gini_segregado.csv`.)

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

| Item | Valor | Base |
|---|---:|---|
| Valor de bolsas em projetos FAPES | R$ 26.379.575 | FAPES |
| Orçamento FAPES contratado | R$ 48.547.974 | FAPES |
| Valor alocado em bolsas (SigPesq) | R$ 16.991.685 | Bolsas (só alocado) |

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

| Coordenador (norm.) | Orçamento FAPES | Projetos | Citações | FWCI | Top 10% |
|---|---:|---:|---:|---:|---:|
| paulo sergio dos santos junior | R$ 11,6 mi¹ | 1 | 107 | 4,75 | 4 |
| jose geraldo das neves orlandi | R$ 6,9 mi | 6 | — | — | — |
| mateus conrad barcellos da costa | R$ 5,8 mi | 3 | 3 | 0,13 | 1 |
| karin satie komati | R$ 5,6 mi | 6 | 74 | 0,86 | 8 |
| maxwell eduardo monteiro | R$ 4,1 mi | 6 | 83 | 3,40 | 9 |

¹ Projeto **ConectaFapes** (plataforma de PD&I) — alto orçamento, natureza de
**infraestrutura institucional**; bom candidato a caso de **impacto institucional/de
capacidade**, não de impacto científico individual. (Os projetos **UnAC**, de gestão da
Universidade Aberta, R$ 6,7 mi, são do coord. *jose geraldo das neves orlandi* — candidatos
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
| Artigos (total, todas as datas) | 549 |
| Artigos **na janela 2015–2026** | **427** |
| Artigos fora da janela (pré-2015) | 122 |
| Artigos na janela recente 2021–2025 | 230 |
| Fomento FAPES na janela 2015–2026 | R$ 48,5 mi (todo) |

→ Recomenda-se reportar os indicadores de produção **dentro da janela** para comparabilidade
com o fomento. Série completa em `janelas_temporais.csv`. **Confiança alta** (datas do Lattes).

### 15.2 Gini recalculado segregando UnAC + ConectaFapes
| Cenário | Gini |
|---|---:|
| Base (todos) | 0,771 |
| **Sem institucionais (UnAC + ConectaFapes)** | **0,748** |
| Só pesquisa stricto sensu (>0) | 0,742 |

Institucional = **R$ 18,3 mi (37,8%)** do orçamento. Conclusão: a concentração é **real e
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
