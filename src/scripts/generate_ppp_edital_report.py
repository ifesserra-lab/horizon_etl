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
OUT_JSON = EXPORTS / "ppp_edital_13_2026.json"
OUT_HTML = EXPORTS / "ppp_edital_13_2026.html"

ANO_INI = 2021  # Secao 6.4


def _lattes_id(r: dict) -> str | None:
    m = re.search(r"(\d{16})", r.get("cnpq_url") or "")
    return m.group(1) if m else None


def carregar_orientacoes() -> dict[str, dict]:
    """Mapa lattes_id/nome -> orientacoes concluidas (initiative_type 'Advisorship')."""
    R = json.loads(SRC_RESEARCHERS.read_text(encoding="utf-8"))
    R = R if isinstance(R, list) else R.get("data") or list(R.values())[0]
    by_lid: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for r in R:
        lid = _lattes_id(r)
        if lid and lid not in by_lid:
            by_lid[lid] = r
        by_name.setdefault(r["name"], r)
    return {"by_lid": by_lid, "by_name": by_name}


def contar_orientacoes(r: dict | None) -> int:
    if not r:
        return -1  # sem registro -> desconhecido
    return sum(
        1 for a in (r.get("advisorships") or [])
        if a.get("initiative_type") == "Advisorship" and a.get("status") == "Concluded"
    )


def analisar() -> dict:
    docentes = json.loads(SRC_CITACOES.read_text(encoding="utf-8"))["docentes"]
    ranking = json.loads(SRC_RANKING.read_text(encoding="utf-8"))["ranking"]
    qmap = {r["nome"]: r for r in ranking}
    idx = carregar_orientacoes()

    rows = []
    for d in docentes:
        artigos = [
            {"ano": a["ano"], "percentil": round(a["percentil"], 1)}
            for a in d.get("top_artigos", [])
            if (a.get("ano") or 0) >= ANO_INI and a.get("percentil") is not None
        ]
        r = idx["by_lid"].get(d["lattes_id"]) or idx["by_name"].get(d["nome"])
        q = qmap.get(d["nome"], {})
        rows.append({
            "nome": d["nome"],
            "area": q.get("area", "—"),
            "lattes_id": d["lattes_id"],
            "artigos_2021_2026": artigos,          # BRUTO: HTML calcula os pontos
            "orientacoes_concluidas": contar_orientacoes(r),  # -1 = sem registro
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
  return {bib, e, det, hasAB, hasAD, bibTier, oc, orientStatus};
}
const TORDER={'PQ-1':1,'PQ-2':2,'PQ-3':3,'—':9};

let ROWS = DATA.docentes.map(d=>({...d, c:calcular(d)}));

// --- categorias para as shortlists ---
function categoria(r){
  const c=r.c;
  if(c.bibTier==='—') return 'improvavel';
  if(c.oc>=0 && c.oc>=ORMIN[c.bibTier]) return 'confirmado';
  return 'chance';
}
function motivo(r){
  const c=r.c;
  if(c.oc<0) return 's/ registro orient.';
  return `orient. ${c.oc} &lt; ${ORMIN[c.bibTier]}`;
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
    <td class="num"><span class="ok">${r.c.oc} ✓</span></td><td class="num">${r.h_index}</td>
    <td class="unk" style="font-size:11px">conferir PPG${r.c.bibTier==='PQ-1'?' + colab. intl':''}</td></tr>`).join('');
  const th=document.getElementById('tChance');
  th.innerHTML=chance.map((r,i)=>`<tr><td class="num">${i+1}</td>
    <td class="name">${r.nome}<small>${r.area}</small></td>
    <td>${pill(r.c.bibTier)}</td><td class="num">${r.c.bib}</td>
    <td class="num">${r.c.oc<0?'<span class="unk">s/ reg.</span>':r.c.oc}</td><td class="num">${r.h_index}</td>
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
      <td class="num">${r.h_index}</td>
      <td class="num">${r.fwci_medio}</td>
      <td class="num">${r.qualis_score_all_time}</td>`;
    tb.appendChild(tr);
    // detail row
    const dr=document.createElement('tr'); dr.className='detail'; dr.style.display='none';
    const arts=c.det.map(a=>`<span class="art">${a.ano} · p${a.perc} → ${a.pts}pt (${a.estrato})</span>`).join(' ')||'sem artigo DOI 2021–2026 no OpenAlex';
    dr.innerHTML=`<td></td><td colspan="9"><b>Cálculo bibliográfico:</b> ${arts}<br>
      Soma = <b>${c.bib} pts</b> · estratos A/B/C/D/E = ${est} ·
      orientações concluídas = ${c.oc<0?'s/ registro':c.oc} ·
      <i>falta verificar manual: vínculo PPG stricto sensu${c.bibTier==='PQ-1'?' + colaboração internacional':''}</i></td>`;
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
  let nextMarked=false;
  tb.innerHTML=DATA.prazos.map(p=>{
    const fim=new Date(p.fim+'T00:00:00');
    let cls='fut', label='futuro', rcls='';
    if(fim < hoje){ cls='done'; label='concluído'; rcls='done'; }
    else if(!nextMarked){ cls='next'; label='próximo'; rcls='next'; nextMarked=true; }
    return `<tr class="${rcls}"><td><b>${p.etapa}</b></td><td>${p.quando}</td>
      <td><span class="st ${cls}">${label}</span></td></tr>`;
  }).join('');
}
kpis(); renderPrazos(); renderShortlist(); render();
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
  <p class="lede">Quem dos {data['total_docentes']} docentes consegue, pelo Lattes, atingir o piso
  de pontuação bibliográfica e de orientações de cada modalidade.</p>
  <div class="meta">
    <span><b>Vagas:</b> 25</span>
    <span><b>Produção contada:</b> {data['periodo_producao']}</span>
    <span><b>Nota final:</b> 80% currículo + 20% projeto</span>
    <span><b>Gerado em:</b> {data['gerado_em']}</span>
  </div>
</header>

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
  <div class="eyebrow">Cronograma</div>
  <h2>Prazos do edital</h2>
  <p class="desc">Etapas conforme a Seção 11 do Edital PRPPG 13/2026. Status calculado em relação à data de hoje.</p>
  <table><thead><tr><th>Etapa</th><th>Quando</th><th>Status</th></tr></thead>
  <tbody id="tPrazos"></tbody></table>
</section>

<section class="section">
  <div class="callout">
    <b>Como ler.</b> Pontuação = <b>piso</b>: 50 × (artigos top-citados com DOI de 2021–2026), via percentil
    OpenAlex (proxy do percentil WoS/Scopus da Tabela 1). Subestima quem publica muito ou teve pico antes de
    2021, e ignora produção sem DOI (livros, capítulos, eventos, periódicos nacionais), que também pontua.
    Orientações = total concluído (nível IC/stricto sensu não consta nos dados). <b>Vínculo a PPG stricto
    sensu</b> e <b>colaboração internacional</b> (exigências PQ-1/PQ-2) <b>não estão nos dados</b> → conferir Lattes.
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
    <div class="rule"><h3>Exigências fora destes dados</h3><ul>
      <li>Vínculo a PPG stricto sensu (PQ-2/PQ-1)</li>
      <li>Colaboração internacional (PQ-1)</li>
      <li>Proposta a edital CNPq/FAPES + captação de recursos</li>
    </ul></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Shortlist</div>
  <h2>Confirmados <span style="font-weight:400;color:var(--muted);font-size:18px">(<span id="cConf">·</span>) — passam pontuação <b>e</b> orientações</span></h2>
  <p class="desc">Atingem o piso bibliográfico <b>e</b> a quantidade mínima de orientações concluídas
  da modalidade. Risco baixo — falta só confirmar vínculo a PPG (e colaboração internacional no PQ-1).</p>
  <table><thead><tr><th class="num">#</th><th>Docente / Área</th><th>Modalidade</th>
    <th class="num">Piso pts</th><th class="num">Orient.</th><th class="num">h</th><th>Falta conferir</th>
  </tr></thead><tbody id="tConf"></tbody></table>
</section>

<section class="section">
  <div class="eyebrow">Shortlist</div>
  <h2>Com chance <span style="font-weight:400;color:var(--muted);font-size:18px">(<span id="cChance">·</span>) — pontuação ok, falta confirmar</span></h2>
  <p class="desc">Têm a produção científica para a modalidade, mas as orientações registradas estão
  abaixo do mínimo <b>ou ausentes nos dados</b>. Muitos provavelmente qualificam após conferência do
  Lattes (orientações sem registro, projetos, produção sem DOI). Esta é a lista a investigar primeiro.</p>
  <table><thead><tr><th class="num">#</th><th>Docente / Área</th><th>Modalidade</th>
    <th class="num">Piso pts</th><th class="num">Orient.</th><th class="num">h</th><th>Pendência</th>
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
    <th class="num" onclick="setSort('h_index')">h</th>
    <th class="num" onclick="setSort('fwci_medio')">FWCI</th>
    <th class="num" onclick="setSort('qualis_score_all_time')">Qualis*</th>
  </tr></thead><tbody id="tbody"></tbody></table>
</section>

<footer class="foot">
  * Qualis = score bibliográfico all-time (contexto de capacidade, fora da janela 2021-2026).
  Fontes: Edital PRPPG 13/2026 · OpenAlex (citações casadas por DOI do Lattes) · ranking_impacto.json ·
  researchers_canonical.json (orientações). Cálculo executado em JavaScript nesta página.
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
