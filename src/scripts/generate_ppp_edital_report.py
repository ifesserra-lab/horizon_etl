#!/usr/bin/env python3
"""Analise de elegibilidade ao Edital PRPPG 13/2026 (PPP - Pesquisador de Produtividade).

Cruza a producao cientifica dos docentes (percentil de citacao OpenAlex, casado por
DOI do Lattes) e as orientacoes concluidas com os criterios do edital, e classifica
cada docente na modalidade PQ que ele alcanca.

O calculo de pontos NAO e feito aqui: o script exporta os DADOS BRUTOS (percentil de
cada artigo 2021-2026 + orientacoes) embutidos no HTML, e o proprio HTML calcula a
pontuacao em JavaScript, de forma transparente. O JSON de saida tambem traz os brutos.

Regras do edital aplicadas no HTML:
  - Periodo de producao: 2021-2026 (Secao 6.4).
  - Pontos por artigo (Tabela 1, percentil WoS/Scopus, maior valor):
      A >=87,5% = 50 | B 75-87,5% = 40 | C 62,5-75% = 30 | D 50-62,5% = 20 | E 37,5-50% = 10 | <37,5% = 0
  - Piso bibliografico (Quadro 3): PQ-3=30 | PQ-2=50 (>=1 A-D) | PQ-1=100 (>=1 A-B)
  - Orientacoes concluidas, rota iniciacao (Quadro 3): PQ-3>=3 | PQ-2>=6 | PQ-1>=9

LIMITACOES (declaradas no HTML):
  - Cache OpenAlex guarda so os ~8 artigos mais citados (todos banda A); pontuacao = PISO.
  - Ignora producao sem DOI (livros, capitulos, eventos, periodicos nacionais).
  - Nivel da orientacao (IC vs stricto sensu) nao consta nos dados -> usa total concluido.
  - Vinculo a PPG stricto sensu e colaboracao internacional (PQ-1) nao constam -> manual.

Saidas:
  data/exports/docentes/ppp_edital_13_2026.json
  data/exports/docentes/ppp_edital_13_2026.html
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "data" / "exports" / "docentes"
SRC_CITACOES = EXPORTS / "openalex_citacoes.json"
SRC_RANKING = EXPORTS / "ranking_impacto.json"
SRC_RESEARCHERS = ROOT / "data" / "exports" / "researchers_canonical.json"
SRC_MESTRADOS = ROOT / "data" / "exports" / "professores-mestrado" / "corpo_docente_mestrados.json"
OUT_JSON = EXPORTS / "ppp_edital_13_2026.json"
OUT_HTML = EXPORTS / "ppp_edital_13_2026.html"

ANO_INI = 2021  # Secao 6.4


def _lattes_id(r: dict) -> str | None:
    m = re.search(r"(\d{16})", r.get("cnpq_url") or "")
    return m.group(1) if m else None


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def carregar_researchers() -> dict:
    """Indice de researchers_canonical por lattes_id e nome normalizado.

    researchers_canonical agrega Lattes + SigPesq (grupos de pesquisa, projetos,
    orientacoes). Por nome, mantem o registro mais rico (mais initiatives)."""
    R = json.loads(SRC_RESEARCHERS.read_text(encoding="utf-8"))
    R = R if isinstance(R, list) else R.get("data") or list(R.values())[0]
    by_lid: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for r in R:
        lid = _lattes_id(r)
        if lid:
            by_lid.setdefault(lid, r)
        nm = _norm(r["name"])
        prev = by_name.get(nm)
        if prev is None or len(r.get("initiatives") or []) > len(prev.get("initiatives") or []):
            by_name[nm] = r
    return {"by_lid": by_lid, "by_name": by_name}


def _itype(i: dict):
    t = i.get("initiative_type")
    return t.get("name") if isinstance(t, dict) else t


def extrai_sigpesq(r: dict | None) -> dict:
    """Orientacoes concluidas + grupos + projetos (SigPesq), DEDUPLICADOS por nome.

    O mesmo projeto/orientacao/grupo aparece repetido (Lattes + SigPesq, ou varias
    linhas). Conta nomes distintos (normalizados)."""
    if not r:
        return {"orientacoes_concluidas": -1, "grupos_pesquisa": [],
                "projetos_coordenados": 0, "projetos_total": 0}

    # orientacoes concluidas: nomes distintos
    orient_nomes = {
        _norm(a.get("name") or "")
        for a in (r.get("advisorships") or [])
        if a.get("initiative_type") == "Advisorship" and a.get("status") == "Concluded" and a.get("name")
    }

    # grupos de pesquisa: nomes distintos
    grupos = sorted({
        g.get("name") for g in (r.get("research_groups") or [])
        if isinstance(g, dict) and g.get("name")
    })

    # projetos: agrupa por nome; coordenado se algum registro tem role Coordinator
    coord_por_nome: dict[str, bool] = {}
    for i in (r.get("initiatives") or []):
        if _itype(i) != "Research Project":
            continue
        nm = _norm(i.get("name") or "")
        if not nm:
            continue
        coord_por_nome[nm] = coord_por_nome.get(nm, False) or (i.get("role") == "Coordinator")

    return {
        "orientacoes_concluidas": len(orient_nomes),
        "grupos_pesquisa": grupos,
        "projetos_coordenados": sum(1 for v in coord_por_nome.values() if v),
        "projetos_total": len(coord_por_nome),
    }


def carregar_ppg() -> dict:
    """Vinculo a PPG stricto sensu por lattes_id e por nome normalizado.

    Retorna lista de vinculos ATIVOS {programa, categoria} de cada docente —
    base para checar a exigencia de docente de PPG (PQ-1 obrigatorio; PQ-2 ou pleitear).
    """
    if not SRC_MESTRADOS.exists():
        return {"by_lid": {}, "by_name": {}}
    profs = json.loads(SRC_MESTRADOS.read_text(encoding="utf-8"))["professores"]
    by_lid: dict[str, list] = {}
    by_name: dict[str, list] = {}
    for p in profs:
        ativos = [
            {"programa": v["programa"], "categoria": v["categoria"]}
            for v in p.get("programas", []) if v.get("ativo")
        ]
        if not ativos:
            continue
        by_lid[p["lattes_id"]] = ativos
        by_name[_norm(p["nome"])] = ativos
    return {"by_lid": by_lid, "by_name": by_name}


def analisar() -> dict:
    docentes = json.loads(SRC_CITACOES.read_text(encoding="utf-8"))["docentes"]
    ranking = json.loads(SRC_RANKING.read_text(encoding="utf-8"))["ranking"]
    qmap = {r["nome"]: r for r in ranking}
    idx = carregar_researchers()
    ppg = carregar_ppg()

    rows = []
    for d in docentes:
        artigos = [
            {"ano": a["ano"], "percentil": round(a["percentil"], 1)}
            for a in d.get("top_artigos", [])
            if (a.get("ano") or 0) >= ANO_INI and a.get("percentil") is not None
        ]
        r = idx["by_lid"].get(d["lattes_id"]) or idx["by_name"].get(_norm(d["nome"]))
        sig = extrai_sigpesq(r)
        ppg_vinculos = ppg["by_lid"].get(d["lattes_id"]) or ppg["by_name"].get(_norm(d["nome"])) or []
        q = qmap.get(d["nome"], {})
        rows.append({
            "nome": d["nome"],
            "area": q.get("area", "—"),
            "lattes_id": d["lattes_id"],
            "artigos_2021_2026": artigos,          # BRUTO: HTML calcula os pontos
            "orientacoes_concluidas": sig["orientacoes_concluidas"],  # -1 = sem registro
            "grupos_pesquisa": sig["grupos_pesquisa"],      # SigPesq — elegibilidade
            "projetos_coordenados": sig["projetos_coordenados"],  # SigPesq
            "projetos_total": sig["projetos_total"],        # SigPesq
            "ppg_stricto_sensu": ppg_vinculos,     # vinculos ATIVOS [{programa,categoria}]
            "h_index": d.get("h_index", 0),
            "fwci_medio": round(d.get("fwci_medio", 0) or 0, 2),
            "citacoes_total": d.get("citacoes_total", 0),
            "qualis_score_all_time": q.get("score_qualis", 0),
            "qualis_A1": q.get("A1", 0),
            "qualis_A2": q.get("A2", 0),
        })

    return {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "edital": "PRPPG 13/2026 - Programa Pesquisador de Produtividade (PPP) - IFES",
        "periodo_producao": f"{ANO_INI}-2026",
        "config_calculo": {
            "faixas_tabela1": [
                {"min_percentil": 87.5, "pontos": 50, "estrato": "A"},
                {"min_percentil": 75.0, "pontos": 40, "estrato": "B"},
                {"min_percentil": 62.5, "pontos": 30, "estrato": "C"},
                {"min_percentil": 50.0, "pontos": 20, "estrato": "D"},
                {"min_percentil": 37.5, "pontos": 10, "estrato": "E"},
            ],
            "piso_bibliografico": {"PQ-1": 100, "PQ-2": 50, "PQ-3": 30},
            "orientacoes_min_rota_ic": {"PQ-1": 9, "PQ-2": 6, "PQ-3": 3},
        },
        "prazos": [
            {"etapa": "Lançamento do edital", "quando": "01/06/2026", "fim": "2026-06-01"},
            {"etapa": "Submissão das propostas", "quando": "01–14/06/2026", "fim": "2026-06-14"},
            {"etapa": "Avaliação das propostas", "quando": "15–26/06/2026", "fim": "2026-06-26"},
            {"etapa": "Resultado preliminar", "quando": "29/06/2026", "fim": "2026-06-29"},
            {"etapa": "Pedido de recurso", "quando": "30/06/2026", "fim": "2026-06-30"},
            {"etapa": "Avaliação dos recursos", "quando": "01–03/07/2026", "fim": "2026-07-03"},
            {"etapa": "Resultado final", "quando": "a partir de 06/07/2026", "fim": "2026-07-06"},
            {"etapa": "Designação · início das atividades", "quando": "até 31/07 · início 01/08/2026", "fim": "2026-08-01"},
            {"etapa": "Relatório parcial #1", "quando": "até 31/08/2027", "fim": "2027-08-31"},
            {"etapa": "Relatório parcial #2", "quando": "até 31/08/2028", "fim": "2028-08-31"},
            {"etapa": "Relatório final", "quando": "até 31/08/2029", "fim": "2029-08-31"},
        ],
        "total_docentes": len(rows),
        "docentes": rows,
    }


# ---------------------------------------------------------------------------
# HTML  (calculo roda em JavaScript, dentro da pagina)
# ---------------------------------------------------------------------------
CSS = """
:root{--ink:#16241a;--ink2:#3c4f42;--muted:#71857a;--line:#e3ece5;--line2:#cfddd3;
--paper:#fff;--bg:#f4f8f5;--soft:#eef5f0;--brand:#0f7a40;--brand-d:#0a5c30;--brand-l:#e7f4ec;
--blue:#2f6fb0;--blue-l:#e8f0f8;--amber:#b8860b;--amber-l:#f7f0dd;--rose:#b5455f;--rose-l:#f8e7ec;
--shadow:0 1px 2px rgba(16,40,24,.04),0 6px 20px rgba(16,40,24,.06);
--font:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;--serif:'Georgia','Times New Roman',serif;}
*{margin:0;padding:0;box-sizing:border-box;}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
body{background:var(--bg);color:var(--ink);font-family:var(--font);line-height:1.55;font-size:15px;}
.page{max-width:1080px;margin:0 auto;padding:0 24px 80px;}
.hero{padding:56px 0 38px;border-bottom:3px solid var(--brand);margin-bottom:40px;}
.kicker{display:inline-flex;gap:8px;font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;
color:var(--brand);background:var(--brand-l);padding:6px 14px;border-radius:999px;margin-bottom:20px;}
.hero h1{font-family:var(--serif);font-size:clamp(28px,5vw,46px);line-height:1.08;font-weight:700;letter-spacing:-.01em;max-width:20ch;}
.hero .lede{font-size:18px;color:var(--ink2);margin-top:18px;max-width:66ch;}
.hero .meta{display:flex;flex-wrap:wrap;gap:8px 24px;margin-top:24px;font-size:13px;color:var(--muted);}
.hero .meta b{color:var(--ink);font-weight:600;}
.section{margin:48px 0;}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--brand);margin-bottom:8px;}
.section h2{font-family:var(--serif);font-size:25px;font-weight:700;letter-spacing:-.01em;margin-bottom:8px;}
.section .desc{font-size:15px;color:var(--ink2);max-width:74ch;margin-bottom:22px;}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;}
.kpi{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:22px 20px;box-shadow:var(--shadow);position:relative;overflow:hidden;}
.kpi::after{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--brand);}
.kpi.b2::after{background:var(--blue);}.kpi.b3::after{background:var(--amber);}.kpi.b4::after{background:var(--rose);}
.kpi .n{font-size:38px;font-weight:800;letter-spacing:-.02em;color:var(--brand-d);line-height:1;}
.kpi.b2 .n{color:var(--blue);}.kpi.b3 .n{color:var(--amber);}.kpi.b4 .n{color:var(--rose);}
.kpi .u{font-size:14px;font-weight:600;margin-top:8px;}.kpi .s{font-size:12px;color:var(--muted);margin-top:4px;}
.callout{background:var(--amber-l);border:1px solid #ecdfb8;border-left:4px solid var(--amber);border-radius:12px;
padding:18px 20px;font-size:14px;color:#5e4a12;margin-bottom:22px;}.callout b{color:#3f3206;}
.disclaimer{background:var(--rose-l);border:1px solid #eccdd5;border-left:5px solid var(--rose);border-radius:12px;
padding:18px 22px;font-size:14px;color:#7a2536;margin:0 0 8px;}
.disclaimer b{color:#5c1626;}
.disclaimer .t{display:block;font-weight:800;font-size:13px;letter-spacing:.04em;text-transform:uppercase;margin-bottom:6px;color:var(--rose);}
.rules{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.rule{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:20px 22px;box-shadow:var(--shadow);}
.rule h3{font-size:15px;font-weight:700;margin-bottom:10px;color:var(--brand-d);}
.rule ul{list-style:none;font-size:13.5px;color:var(--ink2);}
.rule li{padding:5px 0 5px 18px;position:relative;border-bottom:1px dashed var(--line);}
.rule li:last-child{border-bottom:none;}
.rule li::before{content:'';position:absolute;left:0;top:12px;width:6px;height:6px;border-radius:50%;background:var(--brand);}
.rule li b{color:var(--ink);}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px;}
.controls input,.controls select{font:inherit;font-size:13px;padding:8px 12px;border:1px solid var(--line2);border-radius:10px;background:var(--paper);color:var(--ink);}
.controls input{flex:1;min-width:200px;}
table{width:100%;border-collapse:collapse;background:var(--paper);border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:var(--shadow);font-size:13px;}
thead th{background:var(--soft);text-align:left;font-weight:700;font-size:11px;letter-spacing:.04em;text-transform:uppercase;padding:11px 10px;border-bottom:1px solid var(--line2);cursor:pointer;white-space:nowrap;}
thead th:hover{color:var(--brand);}
tbody td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top;}
tbody tr:last-child td{border-bottom:none;}tbody tr:hover{background:var(--soft);}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;}
td.name{font-weight:600;cursor:pointer;}
td.name small{display:block;font-weight:400;color:var(--muted);font-size:11px;}
.pill{display:inline-block;font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px;letter-spacing:.03em;}
.pq1{background:var(--brand-l);color:var(--brand-d);}.pq2{background:var(--blue-l);color:var(--blue);}
.pq3{background:var(--amber-l);color:var(--amber);}.pqx{background:#eef0ef;color:var(--muted);}
.ok{color:var(--brand);font-weight:700;}.warn{color:var(--rose);font-weight:700;}.unk{color:var(--muted);}
.calc{font-size:11px;color:var(--muted);font-family:var(--serif);}
.detail td{background:#fbfdfb;font-size:12px;color:var(--ink2);}
.detail .art{display:inline-block;margin:2px 6px 2px 0;padding:2px 8px;border-radius:8px;background:var(--brand-l);color:var(--brand-d);font-size:11px;}
.steps{display:flex;flex-direction:column;gap:12px;counter-reset:st;}
.step{display:flex;gap:16px;background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:18px 20px;box-shadow:var(--shadow);position:relative;}
.step::before{counter-increment:st;content:counter(st);flex:0 0 36px;height:36px;border-radius:50%;background:var(--brand);color:#fff;font-weight:800;font-size:16px;display:flex;align-items:center;justify-content:center;}
.step .b{flex:1;}
.step .b h3{font-size:15.5px;font-weight:700;margin-bottom:5px;color:var(--ink);}
.step .b p{font-size:13.5px;color:var(--ink2);}
.tagx{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:2px 8px;border-radius:6px;margin-left:8px;vertical-align:middle;}
.tagx.elim{background:var(--rose-l);color:var(--rose);}
.tagx.clas{background:var(--blue-l);color:var(--blue);}
.tagx.auto{background:var(--brand-l);color:var(--brand-d);}
.st{display:inline-block;font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:999px;letter-spacing:.04em;text-transform:uppercase;}
.st.done{background:#eef0ef;color:var(--muted);}.st.next{background:var(--brand);color:#fff;}.st.fut{background:var(--blue-l);color:var(--blue);}
tr.done td{color:var(--muted);}tr.next td{background:var(--brand-l);}
.foot{margin-top:56px;padding-top:24px;border-top:1px solid var(--line2);font-size:12px;color:var(--muted);}
@media(max-width:760px){.kpis{grid-template-columns:1fr 1fr;}.rules{grid-template-columns:1fr;}
table{font-size:11.5px;}thead th,tbody td{padding:7px 6px;}}
"""

JS = r"""
const FAIXAS = CFG.faixas_tabela1;            // [{min_percentil,pontos,estrato}]
const PISO   = CFG.piso_bibliografico;        // {PQ-1:100,...}
const ORMIN  = CFG.orientacoes_min_rota_ic;   // {PQ-1:9,...}

function pontosArtigo(p){
  for(const f of FAIXAS){ if(p >= f.min_percentil) return {pts:f.pontos, estrato:f.estrato}; }
  return {pts:0, estrato:'-'};
}
function calcular(d){
  let bib=0; const e={A:0,B:0,C:0,D:0,E:0}; const det=[];
  for(const a of d.artigos_2021_2026){
    const r=pontosArtigo(a.percentil); bib+=r.pts; if(e[r.estrato]!==undefined) e[r.estrato]++;
    det.push({ano:a.ano, perc:a.percentil, pts:r.pts, estrato:r.estrato});
  }
  const hasAD = (e.A+e.B+e.C+e.D)>0, hasAB=(e.A+e.B)>0;
  let bibTier='—';
  if(bib>=PISO['PQ-1'] && hasAB) bibTier='PQ-1';
  else if(bib>=PISO['PQ-2'] && hasAD) bibTier='PQ-2';
  else if(bib>=PISO['PQ-3']) bibTier='PQ-3';
  const oc=d.orientacoes_concluidas;
  // orientacao satisfaz a bar da modalidade alcancada pelo biblio?
  let orientStatus='unk';
  if(oc>=0 && bibTier!=='—'){ orientStatus = (oc>=ORMIN[bibTier]) ? 'ok' : 'warn'; }
  const ppg = d.ppg_stricto_sensu || [];
  const ppgOk = ppg.length>0;
  const grupos = d.grupos_pesquisa || [];
  const temGrupo = grupos.length>0;
  const projCoord = d.projetos_coordenados||0;
  const projTotal = d.projetos_total||0;
  return {bib, e, det, hasAB, hasAD, bibTier, oc, orientStatus, ppg, ppgOk, grupos, temGrupo, projCoord, projTotal};
}
const TORDER={'PQ-1':1,'PQ-2':2,'PQ-3':3,'—':9};

let ROWS = DATA.docentes.map(d=>({...d, c:calcular(d)}));

// --- categorias para as shortlists ---
// PQ-1 exige vínculo a PPG stricto sensu (obrigatório); PQ-2 pode pleitear; PQ-3 não exige.
function categoria(r){
  const c=r.c;
  if(c.bibTier==='—') return 'improvavel';
  const orientOk = c.oc>=0 && c.oc>=ORMIN[c.bibTier];
  const ppgOk = (c.bibTier!=='PQ-1') || c.ppgOk;
  if(orientOk && ppgOk && c.temGrupo) return 'confirmado';
  return 'chance';
}
function motivo(r){
  const c=r.c; const m=[];
  if(!c.temGrupo) m.push('sem grupo de pesquisa');
  if(c.oc<0) m.push('s/ registro orient.');
  else if(c.oc<ORMIN[c.bibTier]) m.push(`orient. ${c.oc} &lt; ${ORMIN[c.bibTier]}`);
  if(c.bibTier==='PQ-1' && !c.ppgOk) m.push('sem vínculo PPG');
  return m.join(' · ') || '—';
}
function ppgCell(c){
  if(!c.ppg || !c.ppg.length) return '<span class="unk">—</span>';
  return c.ppg.map(v=>`<span class="st ok" title="${v.categoria}">${v.programa}</span>`).join(' ');
}
function grupoCell(c){
  return c.temGrupo ? '<span class="ok" title="'+c.grupos.join(' · ')+'">✓</span>'
                    : '<span class="warn">⚠</span>';
}
function projCell(c){
  return c.projCoord>0 ? '<span class="ok" title="'+c.projCoord+' registros de projeto coordenado">✓</span>'
                       : '<span class="unk">—</span>';
}
function cmpShort(a,b){
  const t=TORDER[a.c.bibTier]-TORDER[b.c.bibTier]; if(t) return t;
  const p=b.c.bib-a.c.bib; if(p) return p; return b.h_index-a.h_index;
}
function renderShortlist(){
  const conf=ROWS.filter(r=>categoria(r)==='confirmado').sort(cmpShort);
  const chance=ROWS.filter(r=>categoria(r)==='chance').sort(cmpShort);
  const tc=document.getElementById('tConf');
  tc.innerHTML=conf.map((r,i)=>`<tr><td class="num">${i+1}</td>
    <td class="name">${r.nome}<small>${r.area}</small></td>
    <td>${pill(r.c.bibTier)}</td><td class="num">${r.c.bib}</td>
    <td class="num"><span class="ok">${r.c.oc} ✓</span></td><td>${ppgCell(r.c)}</td><td class="num">${r.h_index}</td>
    <td class="unk" style="font-size:11px">${r.c.bibTier==='PQ-1'?'colab. internacional':'—'}</td></tr>`).join('');
  const th=document.getElementById('tChance');
  th.innerHTML=chance.map((r,i)=>`<tr><td class="num">${i+1}</td>
    <td class="name">${r.nome}<small>${r.area}</small></td>
    <td>${pill(r.c.bibTier)}</td><td class="num">${r.c.bib}</td>
    <td class="num">${r.c.oc<0?'<span class="unk">s/ reg.</span>':r.c.oc}</td><td>${ppgCell(r.c)}</td><td class="num">${r.h_index}</td>
    <td class="warn" style="font-size:11px">${motivo(r)}</td></tr>`).join('');
  document.getElementById('cConf').textContent=conf.length;
  document.getElementById('cChance').textContent=chance.length;
}
let sortKey='bib', sortDir=-1, filterTier='', q='';

function pill(t){const m={'PQ-1':'pq1','PQ-2':'pq2','PQ-3':'pq3'};return `<span class="pill ${m[t]||'pqx'}">${t}</span>`;}
function orientCell(c){
  if(c.oc<0) return '<span class="unk">s/ registro</span>';
  if(c.bibTier==='—') return `<span class="unk">${c.oc}</span>`;
  const need=ORMIN[c.bibTier];
  return c.oc>=need ? `<span class="ok">${c.oc} ✓</span>` : `<span class="warn">${c.oc} ⚠ (precisa ${need})</span>`;
}

function render(){
  const tb=document.getElementById('tbody'); tb.innerHTML='';
  let list=ROWS.filter(r=>{
    if(filterTier && r.c.bibTier!==filterTier) return false;
    if(q && !r.nome.toLowerCase().includes(q) && !(r.area||'').toLowerCase().includes(q)) return false;
    return true;
  });
  list.sort((a,b)=>{
    let va,vb;
    if(sortKey==='nome'){va=a.nome;vb=b.nome;return sortDir*va.localeCompare(vb);}
    if(sortKey==='tier'){va=TORDER[a.c.bibTier];vb=TORDER[b.c.bibTier];}
    else if(sortKey==='bib'){va=a.c.bib;vb=b.c.bib;}
    else if(sortKey==='oc'){va=a.c.oc;vb=b.c.oc;}
    else {va=a[sortKey]||0;vb=b[sortKey]||0;}
    return sortDir*(va-vb);
  });
  // tie-break by bib desc
  list.forEach((r,i)=>{
    const c=r.c; const est=`${c.e.A}/${c.e.B}/${c.e.C}/${c.e.D}/${c.e.E}`;
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="num">${i+1}</td>
      <td class="name" data-id="${r.lattes_id}">${r.nome}<small>${r.area}</small></td>
      <td class="num">${c.bib}<div class="calc">${c.det.length?c.det.length+'×art':'—'}</div></td>
      <td>${pill(c.bibTier)}</td>
      <td class="num">${est}</td>
      <td class="num">${c.det.length}</td>
      <td class="num">${orientCell(c)}</td>
      <td class="num">${grupoCell(c)}</td>
      <td class="num">${projCell(c)}</td>
      <td>${ppgCell(c)}</td>
      <td class="num">${r.h_index}</td>
      <td class="num">${r.fwci_medio}</td>
      <td class="num">${r.qualis_score_all_time}</td>`;
    tb.appendChild(tr);
    // detail row
    const dr=document.createElement('tr'); dr.className='detail'; dr.style.display='none';
    const arts=c.det.map(a=>`<span class="art">${a.ano} · p${a.perc} → ${a.pts}pt (${a.estrato})</span>`).join(' ')||'sem artigo DOI 2021–2026 no OpenAlex';
    const ppgTxt = (c.ppg && c.ppg.length) ? c.ppg.map(v=>`${v.programa} (${v.categoria})`).join(', ') : 'sem vínculo identificado';
    const grpTxt = c.temGrupo ? c.grupos.join(', ') : 'nenhum identificado (elegibilidade!)';
    dr.innerHTML=`<td></td><td colspan="12"><b>Cálculo bibliográfico:</b> ${arts}<br>
      Soma = <b>${c.bib} pts</b> · estratos A/B/C/D/E = ${est} ·
      orientações concluídas = ${c.oc<0?'s/ registro':c.oc} ·
      grupo(s) de pesquisa (SigPesq) = <b>${grpTxt}</b> ·
      projeto coordenado = <b>${c.projCoord>0?'sim':'não'}</b> (${c.projCoord} registros Lattes+SigPesq, pode haver duplicação) ·
      PPG stricto sensu = <b>${ppgTxt}</b> ·
      <i>falta verificar manual: captação/recursos do projeto${c.bibTier==='PQ-1'?' + colaboração internacional':''}</i></td>`;
    tb.appendChild(dr);
    tr.querySelector('.name').onclick=()=>{dr.style.display = dr.style.display==='none'?'table-row':'none';};
  });
  document.getElementById('count').textContent=list.length+' docentes';
}
function setSort(k){ if(sortKey===k) sortDir*=-1; else {sortKey=k; sortDir=(k==='nome')?1:-1;} render(); }

// KPIs
function kpis(){
  const c=t=>ROWS.filter(r=>r.c.bibTier===t).length;
  document.getElementById('k1').textContent=c('PQ-1');
  document.getElementById('k2').textContent=c('PQ-2');
  document.getElementById('k3').textContent=c('PQ-3');
  document.getElementById('k4').textContent=ROWS.filter(r=>r.c.bibTier==='—').length;
}
document.getElementById('q').addEventListener('input',e=>{q=e.target.value.toLowerCase();render();});
document.getElementById('ftier').addEventListener('change',e=>{filterTier=e.target.value;render();});
function renderPrazos(){
  const tb=document.getElementById('tPrazos'); if(!tb||!DATA.prazos) return;
  const hoje=new Date(); hoje.setHours(0,0,0,0);
  const DIA=86400000;
  let nextMarked=false, nextEtapa=null, nextDias=null;
  tb.innerHTML=DATA.prazos.map(p=>{
    const fim=new Date(p.fim+'T00:00:00');
    let cls='fut', label='futuro', rcls='';
    if(fim < hoje){ cls='done'; label='concluído'; rcls='done'; }
    else if(!nextMarked){
      cls='next'; label='em andamento'; rcls='next'; nextMarked=true;
      nextEtapa=p.etapa; nextDias=Math.round((fim-hoje)/DIA);
    }
    return `<tr class="${rcls}"><td><b>${p.etapa}</b></td><td>${p.quando}</td>
      <td><span class="st ${cls}">${label}</span></td></tr>`;
  }).join('');
  const info=document.getElementById('prazoHoje');
  if(info){
    const hojeBR=hoje.toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric'});
    if(nextEtapa){
      const txt = nextDias<=0 ? 'encerra hoje' : `encerra em ${nextDias} dia${nextDias!==1?'s':''}`;
      info.innerHTML=`📅 <b>Hoje: ${hojeBR}</b> &middot; etapa atual: <b>${nextEtapa}</b> (${txt})`;
    } else {
      info.innerHTML=`📅 <b>Hoje: ${hojeBR}</b> &middot; todas as etapas do cronograma foram concluídas`;
    }
  }
}
kpis(); renderPrazos(); renderShortlist(); render();
setInterval(renderPrazos, 3600000); // re-checa a cada hora: vira o dia, status atualiza sozinho
"""


def render_html(data: dict) -> str:
    payload = json.dumps(
        {"docentes": data["docentes"], "prazos": data["prazos"]},
        ensure_ascii=False, separators=(",", ":"),
    )
    cfg = json.dumps(data["config_calculo"], ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Edital PRPPG 13/2026 (PPP) — Análise de Elegibilidade</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><div class="page">

<header class="hero">
  <span class="kicker">PRPPG / IFES · Diretoria de Pesquisa</span>
  <h1>Edital 13/2026 — Pesquisador de Produtividade</h1>
  <p class="lede"><b>Simulação</b> de quais dos {data['total_docentes']} docentes conseguiriam, pelo Lattes,
  atingir o piso de pontuação bibliográfica e de orientações de cada modalidade. Estimativa com base em
  dados públicos (OpenAlex) — sujeita a erros.</p>
  <div class="meta">
    <span><b>Vagas:</b> 25</span>
    <span><b>Produção contada:</b> {data['periodo_producao']}</span>
    <span><b>Nota final:</b> 80% currículo + 20% projeto</span>
    <span><b>Gerado em:</b> {data['gerado_em']}</span>
  </div>
</header>

<div class="disclaimer">
  <span class="t">⚠ Simulação — uso interno · não é resultado oficial</span>
  Esta análise é uma <b>simulação</b> e <b>pode conter erros e imprecisões</b>. Os números são
  <b>estimativas</b> (piso) calculadas a partir de dados do <b>OpenAlex</b> (citações casadas por DOI do
  currículo Lattes), do <b>Qualis</b>, do <b>SigPesq</b> (grupos de pesquisa e projetos) e do corpo
  docente do PPComp/PROPECAUT — não substitui a avaliação oficial da comissão. <b>Não</b> é o resultado
  do edital, <b>não</b> reflete a decisão da PRPPG e <b>não deve ser usada para classificar, comparar ou
  tomar decisões sobre docentes</b>. Cobertura depende de DOIs no Lattes e da atualização do SigPesq, e
  pode estar incompleta. Em caso de divergência, vale o currículo Lattes e o edital oficial.
</div>

<section class="section">
  <div class="eyebrow">Panorama</div>
  <h2>Quantos alcançam cada modalidade</h2>
  <p class="desc">Classificação pelo <b>piso bibliográfico</b> (lower bound). O número real é maior — ver limitação.</p>
  <div class="kpis">
    <div class="kpi"><div class="n" id="k1">·</div><div class="u">alcançam PQ-1</div><div class="s">≥100 pts · ≥1 A-B</div></div>
    <div class="kpi b2"><div class="n" id="k2">·</div><div class="u">alcançam PQ-2</div><div class="s">≥50 pts · ≥1 A-D</div></div>
    <div class="kpi b3"><div class="n" id="k3">·</div><div class="u">alcançam PQ-3</div><div class="s">≥30 pts</div></div>
    <div class="kpi b4"><div class="n" id="k4">·</div><div class="u">sem evidência</div><div class="s">sem artigo DOI 21-26</div></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Benefício</div>
  <h2>O que ganha quem for contemplado</h2>
  <p class="desc">O PPP concede <b>carga horária semanal protegida para pesquisa</b> — liberação de parte
  da carga de ensino, por 36 meses — conforme a modalidade. <b>Não é bolsa financeira</b> neste edital;
  o ganho é tempo dedicado, designado por portaria do Reitor.</p>
  <div class="kpis">
    <div class="kpi"><div class="n">16–20h</div><div class="u">PQ-1 · por semana</div><div class="s">dedicadas à pesquisa</div></div>
    <div class="kpi b2"><div class="n">12–15h</div><div class="u">PQ-2 · por semana</div><div class="s">dedicadas à pesquisa</div></div>
    <div class="kpi b3"><div class="n">8–11h</div><div class="u">PQ-3 · por semana</div><div class="s">dedicadas à pesquisa</div></div>
    <div class="kpi b4"><div class="n">36</div><div class="u">meses de vigência</div><div class="s">+6 meses extra p/ metas</div></div>
  </div>
  <div class="rules" style="margin-top:18px">
    <div class="rule"><h3>Vantagens diretas</h3><ul>
      <li><b>Tempo de pesquisa</b> garantido na carga horária (Quadro 2), liberado do ensino</li>
      <li><b>Portaria</b> de designação do Reitor — vínculo formal como Pesquisador de Produtividade do IFES</li>
      <li><b>Concentração de aulas</b> possível p/ viabilizar a pesquisa (Seção 9.1.2)</li>
      <li>Equipamentos comprados com fomento externo patrimoniados no campus</li>
    </ul></div>
    <div class="rule"><h3>Ganhos estratégicos</h3><ul>
      <li>Trampolim para <b>bolsa PQ do CNPq/FAPES</b> (exigência de submissão vira vantagem)</li>
      <li>Base para <b>criar / credenciar-se</b> em programas de pós-graduação stricto sensu</li>
      <li>Prioridade institucional e visibilidade na produção do campus</li>
      <li>Colaboração formal com outros campi e parceiros internacionais (PQ-1)</li>
    </ul></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Como ser contemplado</div>
  <h2>Regras para ser contemplado</h2>
  <p class="desc">Etapas em ordem. As <span class="tagx elim">eliminatória</span> reprovam quem não cumpre;
  a <span class="tagx clas">classificatória</span> ordena os aprovados pelas 25 vagas. Há ainda um caminho
  <span class="tagx auto">automático</span>.</p>
  <div class="steps">
    <div class="step"><div class="b"><h3>Elegibilidade <span class="tagx elim">eliminatória</span></h3>
      <p>Servidor <b>permanente</b> do IFES, em <b>grupo de pesquisa ativo, atualizado e certificado</b> no
      Diretório CNPq. Sem pendência com a PRPPG, sem punição disciplinar/ética nos últimos 5 anos, sem
      afastamento &gt; 90 dias previsto.</p></div></div>
    <div class="step"><div class="b"><h3>Inscrição completa no prazo <span class="tagx elim">eliminatória</span></h3>
      <p>Via <b>SIGPesq</b>, anexar: <b>projeto de pesquisa (PDF)</b>, <b>currículo Lattes (PDF)</b>,
      Termo de Anuência (Anexo I, assinado pela chefia) e Termo de Compromisso (Anexo II). Documentação
      incompleta ou fora do prazo (01–14/06/2026) = desclassificado. Sem Lattes = nota zero no currículo.</p></div></div>
    <div class="step"><div class="b"><h3>Projeto com mérito ≥ 60% <span class="tagx elim">eliminatória</span></h3>
      <p>O projeto é avaliado em 9 critérios (título, resumo, relevância, resultados, revisão, objetivos,
      metodologia, referências, cronograma). Média &lt; 60% <b>elimina</b> a proposta. Deve ser pesquisa
      aplicada ao arranjo produtivo regional, com colaboração de pesquisador de outro campus.</p></div></div>
    <div class="step"><div class="b"><h3>Classificação por pontuação <span class="tagx clas">classificatória</span></h3>
      <p>Nota final = <b>80% currículo Lattes + 20% projeto</b>. Currículo pontua por artigos (percentil
      WoS/Scopus), livros, eventos, patentes, orientações, captação de recursos etc. (Quadro 4). A comissão
      publica a lista <b>decrescente por modalidade</b> (PQ-1/2/3).</p></div></div>
    <div class="step"><div class="b"><h3>Caber nas 25 vagas <span class="tagx clas">classificatória</span></h3>
      <p>Vagas distribuídas por demanda entre modalidades e grandes áreas (mín. 1/área), <b>teto de 2
      pesquisadores por grande área por campus</b>. Prioridade de vaga: <b>1º</b> bolsista PQ CNPq, <b>2º</b>
      bolsista FAPES, <b>3º</b> projeto aprovado em agência de fomento, <b>4º</b> demais inscritos.</p></div></div>
    <div class="step"><div class="b"><h3>Atalho: entrada automática <span class="tagx auto">automática</span></h3>
      <p>Bolsista de produtividade <b>PQ do CNPq ou da FAPES</b>, ou quem tem <b>projeto aprovado em agência
      oficial de fomento com captação de recursos</b>, é contemplado <b>sem avaliação de currículo/projeto</b> —
      basta comprovar, escolher a modalidade e cumprir os requisitos mínimos do Quadro 3.</p></div></div>
    <div class="step"><div class="b"><h3>Compromisso após aprovação (Quadro 3)</h3>
      <p>Pontuação bibliográfica mínima — <b>PQ-3: 30 · PQ-2: 50 · PQ-1: 100 pts</b> — mais orientações
      concluídas, submissão a edital CNPq/FAPES, vínculo a PPG stricto sensu (PQ-2/PQ-1) e colaboração
      internacional (PQ-1), a entregar nos 36 meses. Não cumprir = impedido de editais da PRPPG por até 60 meses.</p></div></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Cronograma</div>
  <h2>Prazos do edital</h2>
  <p class="desc">Etapas conforme a Seção 11 do Edital PRPPG 13/2026. Status atualizado automaticamente pela data de acesso.</p>
  <div id="prazoHoje" class="callout" style="background:var(--brand-l);border-color:#bfe0cc;border-left-color:var(--brand);color:var(--brand-d);margin-bottom:16px;"></div>
  <table><thead><tr><th>Etapa</th><th>Quando</th><th>Status</th></tr></thead>
  <tbody id="tPrazos"></tbody></table>
</section>

<section class="section">
  <div class="callout">
    <b>Como ler.</b> Pontuação = <b>piso</b>: 50 × (artigos top-citados com DOI de 2021–2026), via percentil
    OpenAlex (proxy do percentil WoS/Scopus da Tabela 1). Subestima quem publica muito ou teve pico antes de
    2021, e ignora produção sem DOI (livros, capítulos, eventos, periódicos nacionais), que também pontua.
    Orientações = total concluído (nível IC/stricto sensu não consta nos dados). <b>Grupo de pesquisa</b> e
    <b>projetos coordenados</b> vêm do <b>SigPesq</b> — grupo ativo é exigência de elegibilidade (⚠ = sem grupo
    identificado). <b>Vínculo a PPG stricto sensu</b> é verificado pelo corpo docente do <b>PPComp</b>/<b>PROPECAUT</b>
    (obrigatório no PQ-1; no PQ-2 pode-se pleitear). Restam manuais: <b>captação de recursos</b> do projeto e
    <b>colaboração internacional</b> (PQ-1).
  </div>
  <div class="eyebrow">Regras aplicadas no cálculo</div>
  <h2>Critérios do edital usados pela página</h2>
  <div class="rules">
    <div class="rule"><h3>Piso bibliográfico (Quadro 3)</h3><ul>
      <li><b>PQ-3</b> — 30 pts</li>
      <li><b>PQ-2</b> — 50 pts + ≥1 estrato A-D</li>
      <li><b>PQ-1</b> — 100 pts + ≥1 estrato A-B</li>
    </ul></div>
    <div class="rule"><h3>Pontos por artigo (Tabela 1 · percentil)</h3><ul>
      <li><b>A</b> ≥87,5% → 50 · <b>B</b> 75-87,5% → 40</li>
      <li><b>C</b> 62,5-75% → 30 · <b>D</b> 50-62,5% → 20</li>
      <li><b>E</b> 37,5-50% → 10 · &lt;37,5% → 0</li>
    </ul></div>
    <div class="rule"><h3>Orientações concluídas — rota iniciação (Quadro 3)</h3><ul>
      <li><b>PQ-3</b> ≥ 3 · <b>PQ-2</b> ≥ 6 · <b>PQ-1</b> ≥ 9</li>
      <li>(ou rota stricto sensu: 1 / 2 / 3)</li>
    </ul></div>
    <div class="rule"><h3>Vínculo a PPG stricto sensu (verificado)</h3><ul>
      <li><b>PQ-1</b>: docente de PPG é <b>obrigatório</b></li>
      <li><b>PQ-2</b>: participar <b>ou pleitear</b> credenciamento</li>
      <li>Fonte: corpo docente <b>PPComp</b> + <b>PROPECAUT</b></li>
      <li>Ainda manual: colaboração internacional · proposta CNPq/FAPES</li>
    </ul></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Shortlist</div>
  <h2>Confirmados <span style="font-weight:400;color:var(--muted);font-size:18px">(<span id="cConf">·</span>) — passam pontuação <b>e</b> orientações</span></h2>
  <p class="desc">Atingem o piso bibliográfico <b>e</b> a quantidade mínima de orientações concluídas
  da modalidade. Risco baixo — falta só confirmar vínculo a PPG (e colaboração internacional no PQ-1).</p>
  <table><thead><tr><th class="num">#</th><th>Docente / Área</th><th>Modalidade</th>
    <th class="num">Piso pts</th><th class="num">Orient.</th><th>PPG stricto sensu</th><th class="num">h</th><th>Falta conferir</th>
  </tr></thead><tbody id="tConf"></tbody></table>
</section>

<section class="section">
  <div class="eyebrow">Shortlist</div>
  <h2>Com chance <span style="font-weight:400;color:var(--muted);font-size:18px">(<span id="cChance">·</span>) — pontuação ok, falta confirmar</span></h2>
  <p class="desc">Têm a produção científica para a modalidade, mas as orientações registradas estão
  abaixo do mínimo <b>ou ausentes nos dados</b>. Muitos provavelmente qualificam após conferência do
  Lattes (orientações sem registro, projetos, produção sem DOI). Esta é a lista a investigar primeiro.</p>
  <table><thead><tr><th class="num">#</th><th>Docente / Área</th><th>Modalidade</th>
    <th class="num">Piso pts</th><th class="num">Orient.</th><th>PPG stricto sensu</th><th class="num">h</th><th>Pendência</th>
  </tr></thead><tbody id="tChance"></tbody></table>
</section>

<section class="section">
  <div class="eyebrow">Ranking interativo</div>
  <h2>Docentes por capacidade</h2>
  <p class="desc">Clique no cabeçalho para ordenar · clique no nome para ver o cálculo artigo a artigo.</p>
  <div class="controls">
    <input id="q" placeholder="Filtrar por nome ou área…">
    <select id="ftier"><option value="">Todas modalidades</option>
      <option value="PQ-1">PQ-1</option><option value="PQ-2">PQ-2</option>
      <option value="PQ-3">PQ-3</option><option value="—">Sem evidência</option></select>
    <span id="count" style="font-size:13px;color:var(--muted)"></span>
  </div>
  <table><thead><tr>
    <th class="num">#</th>
    <th onclick="setSort('nome')">Docente / Área</th>
    <th class="num" onclick="setSort('bib')">Piso pts</th>
    <th onclick="setSort('tier')">Modalidade</th>
    <th class="num">A/B/C/D/E</th>
    <th class="num">Art 21-26</th>
    <th class="num" onclick="setSort('oc')">Orient.</th>
    <th class="num">Grupo</th>
    <th class="num">Proj.</th>
    <th>PPG</th>
    <th class="num" onclick="setSort('h_index')">h</th>
    <th class="num" onclick="setSort('fwci_medio')">FWCI</th>
    <th class="num" onclick="setSort('qualis_score_all_time')">Qualis*</th>
  </tr></thead><tbody id="tbody"></tbody></table>
</section>

<footer class="foot">
  * Qualis = score bibliográfico all-time (contexto de capacidade, fora da janela 2021-2026).
  Fontes: Edital PRPPG 13/2026 · OpenAlex (citações casadas por DOI do Lattes) · ranking_impacto.json ·
  researchers_canonical.json + SigPesq (orientações, grupos de pesquisa, projetos) · corpo docente PPComp e
  PROPECAUT (vínculo a PPG stricto sensu). Cálculo executado em JavaScript nesta página.
</footer>

<script>const CFG={cfg};const DATA={payload};</script>
<script>{JS}</script>
</div></body></html>"""


def main() -> None:
    data = analisar()
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_HTML.write_text(render_html(data), encoding="utf-8")
    # resumo no terminal (mesma logica do JS)
    faixas = data["config_calculo"]["faixas_tabela1"]
    piso = data["config_calculo"]["piso_bibliografico"]
    ormin = data["config_calculo"]["orientacoes_min_rota_ic"]

    def pts(p):
        for f in faixas:
            if p >= f["min_percentil"]:
                return f["pontos"], f["estrato"]
        return 0, "-"

    from collections import Counter
    tiers = Counter()
    orient_ok = 0
    for d in data["docentes"]:
        bib = 0
        e = Counter()
        for a in d["artigos_2021_2026"]:
            pt, es = pts(a["percentil"])
            bib += pt
            e[es] += 1
        hasAB = e["A"] + e["B"] > 0
        hasAD = hasAB or e["C"] + e["D"] > 0
        t = "PQ-1" if (bib >= piso["PQ-1"] and hasAB) else "PQ-2" if (bib >= piso["PQ-2"] and hasAD) else "PQ-3" if bib >= piso["PQ-3"] else "—"
        tiers[t] += 1
        oc = d["orientacoes_concluidas"]
        if t != "—" and oc >= ormin[t]:
            orient_ok += 1
    print(f"OK -> {OUT_JSON.relative_to(ROOT)}")
    print(f"OK -> {OUT_HTML.relative_to(ROOT)}")
    print(f"Docentes: {data['total_docentes']} | PQ-1={tiers['PQ-1']} PQ-2={tiers['PQ-2']} "
          f"PQ-3={tiers['PQ-3']} sem_dados={tiers['—']} | biblio+orient OK={orient_ok}")


if __name__ == "__main__":
    main()
