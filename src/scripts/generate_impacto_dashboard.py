#!/usr/bin/env python3
"""Dashboard de Impacto dos Docentes — IFES Campus Serra.

Unifica os indicadores de impacto (OpenAlex, citacoes casadas por DOI do Lattes)
num unico painel: ascensao/declinio, producao de elite, eficiencia, concentracao
(Lorenz/Gini), benchmark por grande area e tabela completa interativa.

Fontes:
  data/exports/docentes/openalex_citacoes.json  (impacto)
  data/exports/docentes/ranking_impacto.json    (grande area + Qualis)

Saidas:
  data/exports/docentes/impacto_dashboard.json
  data/exports/docentes/impacto_dashboard.html  (charts SVG/JS, sem libs externas)

Uso:
  python -m src.scripts.generate_impacto_dashboard
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "data" / "exports" / "docentes"
SRC_CIT = EXPORTS / "openalex_citacoes.json"
SRC_RANK = EXPORTS / "ranking_impacto.json"
SRC_FAPES = ROOT / "data" / "exports" / "projetos-fapes" / "ifes-campus-serra-projetos-concluidos-em-andamento.json"
SRC_BOLSAS = ROOT / "data" / "exports" / "bolsistas" / "ifes-campus-serra-bolsistas.json"
OUT_JSON = EXPORTS / "impacto_dashboard.json"
OUT_HTML = EXPORTS / "impacto_dashboard.html"


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def carregar_fomento() -> dict:
    """Fomento (R$) por docente coordenador: FAPES (orçamento contratado) +
    bolsas alocadas onde é coordenador. Casado por nome normalizado."""
    fomento = {}
    if SRC_FAPES.exists():
        d = json.loads(SRC_FAPES.read_text(encoding="utf-8"))
        projs = next((v for v in d.values() if isinstance(v, list)), []) if isinstance(d, dict) else d
        for p in projs:
            nm = _norm(p.get("coordenador_nome"))
            if nm:
                fomento[nm] = fomento.get(nm, 0.0) + _num(p.get("orcamento_contratado"))
    if SRC_BOLSAS.exists():
        d = json.loads(SRC_BOLSAS.read_text(encoding="utf-8"))
        for a in (d.get("alocacoes") or []):
            nm = _norm(a.get("coordenador_nome"))
            if nm:
                fomento[nm] = fomento.get(nm, 0.0) + _num(a.get("valor_alocado_total"))
    return fomento


def _faixa_fomento(v: float) -> str:
    if v <= 0:
        return "sem fomento"
    if v <= 50_000:
        return "≤ R$ 50 mil"
    if v <= 200_000:
        return "R$ 50–200 mil"
    return "> R$ 200 mil"


def _median(xs: list[float]) -> float:
    s = sorted(x for x in xs if x is not None)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2] if n % 2 else round((s[n // 2 - 1] + s[n // 2]) / 2, 2)


def gini(values: list[float]) -> float:
    """Coeficiente de Gini (0 = igualdade total, 1 = concentracao maxima)."""
    xs = sorted(v for v in values if v is not None)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * sum(xs)) - (n + 1) / n, 3)


def _qualidade_veiculo(r: dict) -> dict:
    """% de artigos em Q1/Q2 (SJR) e em A1-A2 (Qualis), a partir do ranking_impacto."""
    arts = r.get("artigos", 0) or 0
    aq = r.get("artigos_qualis", 0) or 0
    q1q2 = r.get("sjr_q1q2", 0) or 0
    a1a2 = (r.get("A1", 0) or 0) + (r.get("A2", 0) or 0)
    return {
        "q1q2_n": q1q2,
        "a1a2_n": a1a2,
        "pct_q1q2": round(q1q2 / arts * 100) if arts else 0,
        "pct_a1a2": round(a1a2 / aq * 100) if aq else 0,
        "artigos_qualis": aq,
    }


def _roi(d: dict, fomento_map: dict) -> dict:
    """ROI = impacto / fomento. Fomento exibido em FAIXA (privacidade); ROI em
    citações por R$ mil e artigos de elite por R$ 100 mil."""
    f = fomento_map.get(_norm(d["nome"]), 0.0)
    cit = d.get("citacoes_total", 0)
    top10 = d.get("artigos_top10pct", 0)
    return {
        "fomento_faixa": _faixa_fomento(f),
        "tem_fomento": f > 0,
        "fomento_x": round(f / 1000),  # eixo do scatter, em R$ mil (interno)
        "roi_cit": round(cit / (f / 1000), 1) if f > 0 else None,    # citações por R$ mil
        "roi_elite": round(top10 / (f / 100_000), 1) if f > 0 else None,  # top10 por R$ 100k
    }


def analisar() -> dict:
    cit = json.loads(SRC_CIT.read_text(encoding="utf-8"))["docentes"]
    rank = json.loads(SRC_RANK.read_text(encoding="utf-8"))["ranking"]
    area_de = {r["nome"]: r.get("area", "—") for r in rank}
    qualis_de = {r["nome"]: r.get("score_qualis", 0) for r in rank}
    rk = {r["nome"]: r for r in rank}

    docentes = []
    for d in cit:
        _area = area_de.get(d["nome"], "—")
        if _area in ("—", "", None):
            _area = "Não classificada"
        docentes.append({
            "nome": d["nome"],
            "lattes_id": d.get("lattes_id", ""),
            "area": _area,
            "artigos": d.get("encontrados_openalex", 0),
            "artigos_doi": d.get("artigos_com_doi", 0),
            "cit": d.get("citacoes_total", 0),
            "h": d.get("h_index", 0),
            "g": d.get("g_index", 0),
            "m": round(d.get("m_index", 0) or 0, 2),
            "idade": d.get("idade_academica", 0),
            "cpp": round(d.get("citacoes_por_artigo", 0) or 0, 1),
            "cit_med": d.get("citacoes_mediana", 0),
            "art_frac": round(d.get("artigos_fracionados", 0) or 0, 1),
            "cit_frac": round(d.get("citacoes_fracionadas", 0) or 0, 1),
            "i10": d.get("i10", 0),
            "mais_citado": d.get("mais_citado", 0),
            "fwci": round(d.get("fwci_medio", 0) or 0, 2),
            "fwci_delta": round(d.get("fwci_delta", 0) or 0, 2),
            "fwci_recente": round(d.get("fwci_recente", 0) or 0, 2),
            "top10": d.get("artigos_top10pct", 0),
            "top1": d.get("artigos_top1pct", 0),
            "recent2a": d.get("citacoes_recentes_2a", 0),
            "momentum": d.get("momentum_pct", 0),
            "qualis": qualis_de.get(d["nome"], 0),
            "asc": d.get("artigo_ascensao"),   # artigo em ascensão (OpenAlex counts_by_year)
            "serie": d.get("citacoes_por_ano") or {},  # sparkline citações/ano
            # artigos-fonte: principais artigos (mais citados) que sustentam as métricas
            "arts": [
                {"t": a.get("titulo", ""), "ano": a.get("ano"),
                 "cit": a.get("citacoes", 0), "fwci": round(a.get("fwci", 0) or 0, 2),
                 "pct": a.get("percentil", 0), "doi": a.get("doi", "")}
                for a in (d.get("top_artigos") or [])
            ],
            **_qualidade_veiculo(rk.get(d["nome"], {})),
        })

    com_oa = [d for d in docentes if d["artigos"] > 0]

    # benchmark por area (so quem tem OpenAlex)
    por_area = defaultdict(list)
    for d in com_oa:
        por_area[d["area"]].append(d)
    areas = []
    for area, ds in por_area.items():
        n = len(ds)
        fwcis = [x["fwci"] for x in ds if x["fwci"] > 0]
        areas.append({
            "area": area,
            "n": n,
            "cit": sum(x["cit"] for x in ds),
            "fwci_mediano": _median(fwcis),   # mediana: robusta a outlier (amostra pequena)
            "top10": sum(x["top10"] for x in ds),
            "h_medio": round(sum(x["h"] for x in ds) / n, 1) if n else 0,
        })
    areas.sort(key=lambda a: -a["cit"])

    cits = [d["cit"] for d in com_oa]
    fwcis = sorted(d["fwci"] for d in com_oa if d["fwci"] > 0)
    fwci_med = fwcis[len(fwcis) // 2] if fwcis else 0.0
    kpis = {
        "n_docentes": len(docentes),
        "com_openalex": len(com_oa),
        "citacoes_total": sum(cits),
        "fwci_medio": round(sum(fwcis) / len(fwcis), 2) if fwcis else 0.0,
        "fwci_mediano": fwci_med,
        "top10_total": sum(d["top10"] for d in com_oa),
        "top1_total": sum(d["top1"] for d in com_oa),
        "gini_citacoes": gini(cits),
        "h_mediano": sorted(d["h"] for d in com_oa)[len(com_oa) // 2] if com_oa else 0,
    }

    return {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fonte": "OpenAlex (api.openalex.org) — citacoes casadas por DOI do Lattes + Qualis (área)",
        "kpis": kpis,
        "areas": areas,
        "docentes": docentes,
    }


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
.page{max-width:1120px;margin:0 auto;padding:0 24px 80px;}
.hero{padding:54px 0 34px;border-bottom:3px solid var(--brand);margin-bottom:34px;}
.kicker{display:inline-flex;gap:8px;font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;
color:var(--brand);background:var(--brand-l);padding:6px 14px;border-radius:999px;margin-bottom:18px;}
.hero h1{font-family:var(--serif);font-size:clamp(28px,5vw,46px);line-height:1.08;font-weight:700;letter-spacing:-.01em;}
.hero .lede{font-size:18px;color:var(--ink2);margin-top:16px;max-width:70ch;}
.hero .meta{display:flex;flex-wrap:wrap;gap:8px 24px;margin-top:20px;font-size:13px;color:var(--muted);}
.hero .meta b{color:var(--ink);font-weight:600;}
.disclaimer{background:var(--rose-l);border:1px solid #eccdd5;border-left:5px solid var(--rose);border-radius:12px;
padding:16px 20px;font-size:13.5px;color:#7a2536;margin-bottom:8px;}
.disclaimer b{color:#5c1626;}.disclaimer .t{display:block;font-weight:800;font-size:12px;letter-spacing:.04em;text-transform:uppercase;margin-bottom:5px;color:var(--rose);}
.section{margin:44px 0;}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--brand);margin-bottom:8px;}
.section h2{font-family:var(--serif);font-size:24px;font-weight:700;letter-spacing:-.01em;margin-bottom:8px;}
.section .desc{font-size:14.5px;color:var(--ink2);max-width:78ch;margin-bottom:22px;}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;}
.kpi{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:20px 18px;box-shadow:var(--shadow);position:relative;overflow:hidden;}
.kpi::after{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--brand);}
.kpi.b2::after{background:var(--blue);}.kpi.b3::after{background:var(--amber);}.kpi.b4::after{background:var(--rose);}
.kpi .n{font-size:32px;font-weight:800;letter-spacing:-.02em;color:var(--brand-d);line-height:1;}
.kpi.b2 .n{color:var(--blue);}.kpi.b3 .n{color:var(--amber);}.kpi.b4 .n{color:var(--rose);}
.kpi .u{font-size:13px;font-weight:600;margin-top:7px;}.kpi .s{font-size:12px;color:var(--muted);margin-top:3px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:22px;}
.card{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:var(--shadow);}
.card h3{font-size:15px;font-weight:700;margin-bottom:4px;}
.card .h-s{font-size:12.5px;color:var(--muted);margin-bottom:16px;}
.note{background:var(--amber-l);border:1px solid #ecdfb8;border-left:3px solid var(--amber);border-radius:8px;
padding:11px 13px;font-size:11.8px;color:#5e4a12;margin-top:14px;line-height:1.45;}
.note b{color:#3f3206;}
.quads{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px;}
.quad{background:var(--paper);border:1px solid var(--line);border-left:4px solid var(--brand);border-radius:12px;padding:15px 17px;box-shadow:var(--shadow);}
.quad h4{font-size:14px;font-weight:700;margin-bottom:3px;display:flex;justify-content:space-between;align-items:baseline;}
.quad h4 .qn{font-size:12px;color:var(--muted);font-weight:600;}
.quad .qd{font-size:11.5px;color:var(--muted);margin-bottom:9px;line-height:1.35;}
.quad ul{list-style:none;font-size:12.5px;}
.quad li{padding:3px 0;border-bottom:1px dashed var(--line);}
.quad li:last-child{border-bottom:none;}
.quad li .qf{color:var(--muted);font-size:11px;}
.quad li.qe{color:var(--muted);}
.bar{display:grid;grid-template-columns:210px 1fr 56px;align-items:center;gap:10px;margin:7px 0;font-size:12.5px;}
.bar .lbl{white-space:normal;overflow-wrap:break-word;line-height:1.18;}
.bar .track{background:var(--soft);border-radius:6px;height:16px;overflow:hidden;}
.bar .fill{height:100%;border-radius:6px;background:var(--brand);}
.bar .fill.blue{background:var(--blue);}.bar .fill.amber{background:var(--amber);}.bar .fill.rose{background:var(--rose);}
.bar .val{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;}
.ascitem{padding:9px 0;border-bottom:1px solid var(--line);}
.ascitem:last-child{border-bottom:none;}
.ascitem .who{display:flex;justify-content:space-between;gap:10px;font-size:13px;font-weight:600;align-items:baseline;}
.ascitem .who .up{color:var(--brand);font-weight:800;white-space:nowrap;}
.ascitem .art{font-size:12px;color:var(--ink2);margin-top:2px;line-height:1.3;}
.ascitem .art .yr{color:var(--muted);font-weight:600;}
.ascitem .art .sh{color:var(--amber);font-weight:600;}
.ascitem .art a{color:var(--brand-d);text-decoration:underline;text-decoration-color:var(--line2);}
.ascitem .art a:hover{text-decoration-color:var(--brand);}
.bar .lbl a{color:inherit;text-decoration:underline;text-decoration-color:var(--line2);}
.bar .lbl a:hover{text-decoration-color:var(--brand);}
svg{max-width:100%;height:auto;display:block;}
.lorenz-wrap{display:grid;grid-template-columns:1fr 220px;gap:24px;align-items:center;}
.ginibox{text-align:center;}.ginibox .g{font-size:54px;font-weight:800;color:var(--rose);line-height:1;}
.ginibox .gl{font-size:13px;color:var(--muted);margin-top:6px;}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px;}
.controls input,.controls select{font:inherit;font-size:13px;padding:8px 12px;border:1px solid var(--line2);border-radius:10px;background:var(--paper);}
.controls input{flex:1;min-width:200px;}
.tbl-wrap{overflow-x:auto;}
table{width:100%;border-collapse:collapse;background:var(--paper);border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:var(--shadow);font-size:12.5px;}
thead th{background:var(--soft);text-align:right;font-weight:700;font-size:11px;letter-spacing:.03em;text-transform:uppercase;padding:10px 8px;border-bottom:1px solid var(--line2);cursor:pointer;white-space:nowrap;}
thead th:first-child,thead th:nth-child(2){text-align:left;}
thead th:hover{color:var(--brand);}
tbody td{padding:8px;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums;}
tbody td:first-child,tbody td:nth-child(2){text-align:left;}
tbody td.name{font-weight:600;}tbody tr:hover{background:var(--soft);}
.pos{color:var(--brand);font-weight:700;}.neg{color:var(--rose);font-weight:700;}
.refs{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.ref{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:18px 20px;box-shadow:var(--shadow);}
.ref h4{font-size:14.5px;font-weight:700;color:var(--brand-d);margin-bottom:7px;}
.ref p{font-size:13px;color:var(--ink2);margin-bottom:9px;}
.ref .formula{font-family:var(--serif);font-size:13px;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:5px 10px;margin-bottom:9px;display:inline-block;}
.ref .cite{font-size:11.5px;color:var(--muted);border-top:1px dashed var(--line);padding-top:8px;}
.foot{margin-top:50px;padding-top:22px;border-top:1px solid var(--line2);font-size:12px;color:var(--muted);}
@media(max-width:820px){.kpis{grid-template-columns:1fr 1fr;}.grid2{grid-template-columns:1fr;}.lorenz-wrap{grid-template-columns:1fr;}.bar{grid-template-columns:150px 1fr 44px;}.refs{grid-template-columns:1fr;}}
"""

JS = r"""
const D = DATA.docentes, A = DATA.areas, K = DATA.kpis;
const oa = D.filter(d=>d.artigos>0);
const esc = s => (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const fmt = n => (n%1===0)?n:(+n).toFixed(2);

// KPIs
function setK(id,v){const e=document.getElementById(id);if(e)e.textContent=v;}
setK('k_cit',K.citacoes_total.toLocaleString('pt-BR'));
setK('k_fwci',K.fwci_mediano);
setK('k_top10',K.top10_total);
setK('k_gini',K.gini_citacoes);
setK('k_n',K.com_openalex);
setK('k_top1',K.top1_total);
setK('k_h',K.h_mediano);

// horizontal bar list
function hbar(elId, rows, valKey, lblKey, color, fmtv){
  const el=document.getElementById(elId); if(!el) return;
  const max=Math.max(...rows.map(r=>Math.abs(r[valKey])),1);
  el.innerHTML=rows.map(r=>{
    const w=Math.max(2, Math.abs(r[valKey])/max*100);
    const v=fmtv?fmtv(r[valKey]):r[valKey];
    return `<div class="bar"><span class="lbl" title="${esc(r[lblKey])}">${esc(r[lblKey])}</span>
      <span class="track"><span class="fill ${color}" style="width:${w}%"></span></span>
      <span class="val">${v}</span></div>`;
  }).join('');
}

// ascensão — artigo que mais recebeu citações nos últimos 2 anos, por docente
(function(){
  const el=document.getElementById('c_asc'); if(!el) return;
  const rows=oa.filter(d=>d.asc && d.asc.recent_2a>0)
               .sort((a,b)=>b.asc.recent_2a-a.asc.recent_2a).slice(0,12);
  el.innerHTML=rows.map(d=>{
    const a=d.asc;
    const ttl=esc(a.titulo)+(a.titulo&&a.titulo.length>=120?'…':'');
    const titulo=a.doi ? `<a href="https://doi.org/${esc(a.doi)}" target="_blank" rel="noopener">${ttl}</a>` : ttl;
    return `<div class="ascitem">
      <div class="who"><span>${esc(d.nome)}</span><span class="up">+${a.recent_2a} cit · 2 anos</span></div>
      <div class="art"><span class="yr">[${a.ano||'?'}]</span> ${titulo}
        <span class="sh">(${a.share_recente_pct}% das citações são recentes)</span></div>
    </div>`;
  }).join('') || '<p class="h-s">Sem dados de ascensão por artigo.</p>';
})();
// declínio FWCI (fwci_delta mais negativo) — ΔFWCI é agregado (sem artigo único);
// nome linka para o Lattes do docente
(function(){
  const el=document.getElementById('c_dec'); if(!el) return;
  const rows=oa.filter(d=>d.fwci>0&&d.fwci_delta<0).sort((a,b)=>a.fwci_delta-b.fwci_delta).slice(0,10);
  const max=Math.max(...rows.map(r=>Math.abs(r.fwci_delta)),1);
  el.innerHTML=rows.map(r=>{
    const w=Math.max(2,Math.abs(r.fwci_delta)/max*100);
    const nm=r.lattes_id?`<a href="https://lattes.cnpq.br/${esc(r.lattes_id)}" target="_blank" rel="noopener">${esc(r.nome)}</a>`:esc(r.nome);
    return `<div class="bar"><span class="lbl">${nm}</span>
      <span class="track"><span class="fill rose" style="width:${w}%"></span></span>
      <span class="val">${r.fwci_delta}</span></div>`;
  }).join('') || '<p class="h-s">Sem queda de ΔFWCI.</p>';
})();
// elite top10%
hbar('c_top10', [...oa].sort((a,b)=>b.top10-a.top10||b.top1-a.top1).slice(0,12),'top10','nome','amber');
// eficiência: citações fracionadas (crédito por autoria)
hbar('c_frac', [...oa].sort((a,b)=>b.cit_frac-a.cit_frac).slice(0,12),'cit_frac','nome','blue', v=>Math.round(v));
// FWCI por área (mediana, robusta a outlier)
hbar('c_area', [...A].filter(a=>a.fwci_mediano>0).sort((a,b)=>b.fwci_mediano-a.fwci_mediano),'fwci_mediano','area','', v=>v);
// m-index (precocidade) base com idade
hbar('c_m', oa.filter(d=>d.idade>=3&&d.cit>=20).sort((a,b)=>b.m-a.m).slice(0,10),'m','nome','', v=>v);

// qualidade de veículo (% Q1/Q2 SJR e % A1-A2 Qualis) — base >=3 artigos qualis
const qual = D.filter(d=>d.artigos_qualis>=3);
hbar('c_q1q2', [...qual].sort((a,b)=>b.pct_q1q2-a.pct_q1q2).slice(0,12),'pct_q1q2','nome','blue', v=>v+'%');
hbar('c_a1a2', [...qual].sort((a,b)=>b.pct_a1a2-a.pct_a1a2).slice(0,12),'pct_a1a2','nome','amber', v=>v+'%');

// sparkline citações/ano
function spark(serie){
  const ys=Object.keys(serie||{}).map(Number).sort((a,b)=>a-b);
  if(ys.length<2) return '<span class="unk">—</span>';
  const vals=ys.map(y=>serie[y]), max=Math.max(...vals,1), n=ys.length, W=84,H=20;
  const pts=vals.map((v,i)=>`${(i/(n-1)*W).toFixed(1)},${(H-2-v/max*(H-4)).toFixed(1)}`).join(' ');
  return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="vertical-align:middle">
    <polyline points="${pts}" fill="none" stroke="var(--brand)" stroke-width="1.5"/>
    <circle cx="${(W).toFixed(1)}" cy="${(H-2-vals[n-1]/max*(H-4)).toFixed(1)}" r="1.8" fill="var(--brand-d)"/>
  </svg>`;
}

// Lorenz (concentração das citações)
(function(){
  const el=document.getElementById('lorenz'); if(!el) return;
  const xs=oa.map(d=>d.cit).sort((a,b)=>a-b);
  const n=xs.length, tot=xs.reduce((s,x)=>s+x,0)||1;
  let acc=0; const pts=[[0,0]];
  xs.forEach((x,i)=>{acc+=x; pts.push([(i+1)/n, acc/tot]);});
  const W=460,H=300,P=34;
  const X=p=>P+p*(W-2*P), Y=p=>H-P-p*(H-2*P);
  const line=pts.map(p=>`${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(' ');
  el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Curva de Lorenz">
    <rect x="${P}" y="${P}" width="${W-2*P}" height="${H-2*P}" fill="#fff" stroke="var(--line2)"/>
    <line x1="${X(0)}" y1="${Y(0)}" x2="${X(1)}" y2="${Y(1)}" stroke="var(--muted)" stroke-dasharray="4 4"/>
    <polygon points="${X(0)},${Y(0)} ${line} ${X(1)},${Y(0)}" fill="rgba(181,69,95,.10)"/>
    <polyline points="${line}" fill="none" stroke="var(--rose)" stroke-width="2.5"/>
    <text x="${W/2}" y="${H-8}" text-anchor="middle" font-size="11" fill="var(--muted)">% dos docentes (menor → maior)</text>
    <text x="12" y="${H/2}" text-anchor="middle" font-size="11" fill="var(--muted)" transform="rotate(-90 12 ${H/2})">% das citações</text>
  </svg>`;
})();

// tabela completa
const COLS=[
  ['nome','Docente',0],['area','Área',0],['serie','Trajetória cit/ano',2],['cit','Citações',1],
  ['h','h',1],['g','g',1],['m','m',1],['fwci','FWCI',1],['fwci_delta','ΔFWCI',1],['momentum','Mom%',1],
  ['top10','Top10%',1],['top1','Top1%',1],['pct_q1q2','%Q1/Q2',1],['pct_a1a2','%A1-A2',1],
  ['cpp','Cit/art',1],['cit_frac','Cit.frac',1],['recent2a','Cit.2a',1],['qualis','Qualis',1],
];
let sortKey='cit', sortDir=-1, q='', area='';
function thead(){return '<tr>'+COLS.map(c=>`<th onclick="setSort('${c[0]}')">${c[1]}</th>`).join('')+'</tr>';}
function render(){
  let list=D.filter(d=>{
    if(area && d.area!==area) return false;
    if(q && !d.nome.toLowerCase().includes(q)) return false;
    return true;
  }).sort((a,b)=>{
    if(sortKey==='serie') return 0;
    let va=a[sortKey],vb=b[sortKey];
    if(typeof va==='string') return sortDir*va.localeCompare(vb);
    return sortDir*((va||0)-(vb||0));
  });
  document.getElementById('thead').innerHTML=thead();
  document.getElementById('tbody').innerHTML=list.map(d=>'<tr>'+COLS.map(c=>{
    let v=d[c[0]];
    if(c[0]==='nome') return `<td class="name">${esc(v)}</td>`;
    if(c[0]==='area') return `<td>${esc(v)}</td>`;
    if(c[0]==='serie') return `<td style="text-align:left">${spark(v)}</td>`;
    if(c[0]==='fwci_delta'){const cl=v>0?'pos':(v<0?'neg':'');return `<td class="${cl}">${v>0?'+':''}${v}</td>`;}
    return `<td>${v}</td>`;
  }).join('')+'</tr>').join('');
  document.getElementById('tcount').textContent=list.length+' docentes';
}
function setSort(k){if(sortKey===k)sortDir*=-1;else{sortKey=k;sortDir=(k==='nome'||k==='area')?1:-1;}render();}
// area filter options
const areaSel=document.getElementById('farea');
[...new Set(D.map(d=>d.area))].filter(a=>a&&a!=='—').sort().forEach(a=>{
  const o=document.createElement('option');o.value=a;o.textContent=a;areaSel.appendChild(o);});
document.getElementById('q').addEventListener('input',e=>{q=e.target.value.toLowerCase();render();});
areaSel.addEventListener('change',e=>{area=e.target.value;render();});
render();

// Artigos-fonte das métricas (por docente) — rastreabilidade
(function(){
  const sel=document.getElementById('fdoc'); if(!sel) return;
  const box=document.getElementById('src_arts'), cnt=document.getElementById('acount');
  const docs=D.filter(d=>d.arts&&d.arts.length).sort((a,b)=>a.nome.localeCompare(b.nome));
  sel.innerHTML='<option value="">Selecione um docente…</option>'+
    docs.map((d,i)=>`<option value="${i}">${esc(d.nome)}</option>`).join('');
  function show(v){
    if(v===''){box.innerHTML='<p class="h-s">Selecione um docente para listar os artigos que sustentam suas métricas.</p>';cnt.textContent='';return;}
    const d=docs[+v], arts=[...d.arts].sort((a,b)=>b.cit-a.cit);
    cnt.textContent=`${arts.length} artigos (principais por citações) · ${d.cit.toLocaleString('pt-BR')} citações totais · h=${d.h} · g=${d.g}`;
    box.innerHTML=arts.map(a=>{
      const t=esc(a.t)||'(sem título)';
      const ttl=a.doi?`<a href="https://doi.org/${esc(a.doi)}" target="_blank" rel="noopener">${t}</a>`:t;
      const tag=a.pct>=99?'top 1%':(a.pct>=90?'top 10%':'');
      const badges=[`${a.cit} cit`, a.fwci?`FWCI ${a.fwci}`:'', tag].filter(Boolean).join(' · ');
      return `<div class="ascitem"><div class="art"><span class="yr">[${a.ano||'?'}]</span> ${ttl}
        <span class="sh">${badges}</span></div></div>`;
    }).join('') || '<p class="h-s">Sem artigos casados no OpenAlex.</p>';
  }
  sel.addEventListener('change',e=>show(e.target.value));
  show('');
})();
"""


def render_html(data: dict) -> str:
    payload = json.dumps(
        {"docentes": data["docentes"], "areas": data["areas"], "kpis": data["kpis"]},
        ensure_ascii=False, separators=(",", ":"),
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard de Impacto — Docentes IFES Campus Serra</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><div class="page">

<header class="hero">
  <span class="kicker">PRPPG / IFES · Diretoria de Pesquisa</span>
  <h1>Dashboard de Impacto dos Docentes</h1>
  <p class="lede">Indicadores de impacto científico do Campus Serra: ascensão, produção de elite,
  eficiência, concentração e benchmark por área — via <b>OpenAlex</b> (citações casadas por DOI do Lattes).</p>
  <div class="meta">
    <span><b>Docentes c/ OpenAlex:</b> {data['kpis']['com_openalex']}/{data['kpis']['n_docentes']}</span>
    <span><b>Citações totais:</b> {data['kpis']['citacoes_total']:,}</span>
    <span><b>Gerado em:</b> {data['gerado_em']}</span>
  </div>
</header>

<div class="disclaimer">
  <span class="t">⚠ Simulação — uso interno</span>
  Estimativas a partir de dados públicos do <b>OpenAlex</b>, casados por <b>DOI</b> do Lattes —
  cobertura depende de DOIs no currículo e <b>pode estar incompleta</b>. <b>OpenAlex não é o Google
  Scholar</b>: indexa menos itens (só obras com DOI/indexadas), então citações e h-index aqui tendem a
  ser <b>menores</b> que no Scholar, e artigos sem DOI <b>ficam de fora</b>. São consistentes entre
  docentes (mesma régua), mas use como panorama — não como avaliação oficial de desempenho individual.
</div>

<section class="section">
  <div class="eyebrow">Panorama</div>
  <h2>Números do impacto</h2>
  <div class="kpis">
    <div class="kpi"><div class="n" id="k_cit">·</div><div class="u">citações totais</div><div class="s">OpenAlex, por DOI</div></div>
    <div class="kpi b2"><div class="n" id="k_fwci">·</div><div class="u">FWCI mediano</div><div class="s">1.0 = média mundial da área</div></div>
    <div class="kpi b3"><div class="n" id="k_top10">·</div><div class="u">artigos top 10%</div><div class="s">percentil ≥ 90 de citações</div></div>
    <div class="kpi b4"><div class="n" id="k_gini">·</div><div class="u">Gini das citações</div><div class="s">0 = igual · 1 = concentrado</div></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Concentração</div>
  <h2>Quão concentrado é o impacto</h2>
  <p class="desc">Curva de Lorenz das citações: quanto mais a curva afunda, mais o impacto se concentra em
  poucos docentes. Gini alto sinaliza dependência de um pequeno núcleo — risco e oportunidade de difusão.</p>
  <div class="card">
    <div class="lorenz-wrap">
      <div id="lorenz"></div>
      <div class="ginibox"><div class="g" id="k_gini2">·</div><div class="gl">Gini das citações<br>(<span id="k_n2">·</span> docentes · <span id="k_top1">·</span> papers top 1%)</div></div>
    </div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Trajetória</div>
  <h2>Ascensão e declínio</h2>
  <p class="desc">Ascensão = o <b>artigo de cada docente que mais recebeu citações nos últimos 2 anos</b>
  (via <code>counts_by_year</code> do OpenAlex) — o trabalho mais "quente" no momento. Declínio = <b>ΔFWCI</b>
  (impacto recente − antigo) mais negativo. Aponta onde investir e quem apoiar.</p>
  <div class="grid2">
    <div class="card"><h3>🚀 Artigo em ascensão (por docente)</h3><div class="h-s">o paper que mais ganhou citações nos últimos 2 anos</div><div id="c_asc"></div></div>
    <div class="card"><h3>📉 Impacto relativo em queda</h3><div class="h-s">ΔFWCI = FWCI recente (2021–25) − antigo (2016–20)</div><div id="c_dec"></div>
      <div class="note"><b>Como ler — e o que NÃO concluir.</b> ΔFWCI compara o impacto <i>relativo</i> (normalizado
      por área) dos artigos recentes vs. os antigos. Negativo = os papers recentes ainda renderam menos
      citações, <b>na comparação mundial</b>, que os antigos. <b>Não</b> significa parar de produzir, nem
      trabalho ruim. Causas comuns e benignas: (1) <b>artigos novos ainda não acumularam citações</b> —
      citação leva 2–4 anos; (2) <b>regressão à média</b> depois de um paper excepcional; (3) <b>mudança de
      linha/tema</b> ou de veículo. Use como <b>sinal de atenção</b>, não de mérito; exige ≥ 2 artigos com
      FWCI em cada janela.</div>
    </div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Excelência</div>
  <h2>Produção de elite e eficiência</h2>
  <p class="desc">Elite = nº de artigos no <b>top 10%</b> de citações da área (classe mundial). Eficiência =
  <b>citações fracionadas</b> (crédito por autoria, corrige hipercoautoria) — impacto real atribuível ao docente.</p>
  <div class="grid2">
    <div class="card"><h3>🏆 Artigos de elite (top 10%)</h3><div class="h-s">nº de papers no percentil ≥ 90</div><div id="c_top10"></div></div>
    <div class="card"><h3>⚡ Impacto por crédito de autoria</h3><div class="h-s">citações fracionadas (1/nº autores)</div><div id="c_frac"></div></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Comparação</div>
  <h2>Benchmark por área e precocidade</h2>
  <p class="desc"><b>FWCI</b> é normalizado por campo → compara áreas de forma justa (1.0 = média mundial).
  <b>m-index</b> = h / idade acadêmica: quem construiu impacto mais cedo na carreira (base ≥ 3 anos, ≥ 20 citações).</p>
  <div class="grid2">
    <div class="card"><h3>🌍 FWCI mediano por grande área</h3><div class="h-s">mediana (robusta a outlier) · acima de 1.0 = acima da média mundial</div><div id="c_area"></div></div>
    <div class="card"><h3>⏱️ Precocidade (m-index)</h3><div class="h-s">h-index dividido pela idade acadêmica</div><div id="c_m"></div>
      <div class="note"><b>O que é precocidade.</b> O <b>m-index</b> = <b>h-index ÷ anos de carreira</b>
      (idade acadêmica = anos desde a 1ª publicação com DOI). Mede a <b>velocidade</b> de construção de
      impacto, corrigindo o viés do h-index (que sempre cresce com o tempo). Assim compara de forma justa
      quem começou há 5 anos com quem tem 25 de carreira. Referência: <b>m ≈ 1</b> é bom; <b>2–3</b>,
      excelente. <b>Alta precocidade</b> = construiu impacto cedo (talento emergente a apoiar).</div>
    </div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Qualidade de veículo</div>
  <h2>Onde se publica — Q1/Q2 e A1-A2</h2>
  <p class="desc">Métricas do <b>veículo</b> (não do artigo): <b>% Q1/Q2</b> = fração dos artigos em revistas no
  quartil superior do <b>SJR</b> (SCImago); <b>% A1-A2</b> = fração no estrato alto do <b>Qualis/CAPES</b>.
  Independente do OpenAlex/DOI — vem da casagem por ISSN. Base ≥ 3 artigos classificados.</p>
  <div class="grid2">
    <div class="card"><h3>📘 % artigos em Q1/Q2 (SJR)</h3><div class="h-s">quartil superior do prestígio da revista</div><div id="c_q1q2"></div></div>
    <div class="card"><h3>⭐ % artigos em A1-A2 (Qualis)</h3><div class="h-s">estrato alto da classificação CAPES</div><div id="c_a1a2"></div></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Detalhe</div>
  <h2>Tabela completa de indicadores</h2>
  <p class="desc">Clique no cabeçalho para ordenar · filtre por nome ou área. ΔFWCI verde = subindo, vermelho = caindo.</p>
  <div class="controls">
    <input id="q" placeholder="Filtrar por nome…">
    <select id="farea"><option value="">Todas as áreas</option></select>
    <span id="tcount" style="font-size:13px;color:var(--muted)"></span>
  </div>
  <div class="tbl-wrap"><table><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>
</section>

<section class="section">
  <div class="eyebrow">Rastreabilidade</div>
  <h2>Artigos-fonte das métricas</h2>
  <p class="desc">De onde vêm os números. Selecione um docente para ver os <b>principais artigos</b>
  (mais citados) que sustentam suas métricas — <b>citações</b>, <b>FWCI</b> e <b>percentil</b> vêm
  do OpenAlex, casados por <b>DOI</b> do Lattes. Cada título com DOI linka para o artigo.</p>
  <div class="controls">
    <select id="fdoc"><option value="">Selecione um docente…</option></select>
    <span id="acount" style="font-size:13px;color:var(--muted)"></span>
  </div>
  <div class="card"><div id="src_arts"></div></div>
</section>

<section class="section">
  <div class="eyebrow">Fundamentação</div>
  <h2>Base teórica das métricas</h2>
  <p class="desc">O que cada indicador mede, como é calculado e a referência seminal. Métricas baseadas em
  <b>percentil</b> e <b>normalização por campo</b> (FWCI) são preferidas às citações brutas porque
  permitem comparação justa entre áreas e idades de carreira.</p>
  <div class="refs">

    <div class="ref"><h4>h-index</h4>
      <p>Maior número <i>h</i> tal que o pesquisador tem <i>h</i> artigos com ≥ <i>h</i> citações cada.
      Combina produção e impacto num só número; robusto a outliers, mas cresce com a idade de carreira.</p>
      <span class="formula">h = max{{ i : citações(i) ≥ i }}</span>
      <div class="cite">Hirsch, J. E. (2005). <i>An index to quantify an individual's scientific research output.</i> PNAS, 102(46), 16569–16572.</div></div>

    <div class="ref"><h4>g-index</h4>
      <p>Maior <i>g</i> tal que os <i>g</i> artigos mais citados somam ≥ <i>g²</i> citações. Dá mais peso
      aos trabalhos muito citados que o h-index (que ignora o excedente de citações).</p>
      <span class="formula">g = max{{ g : Σ₁ᵍ citações ≥ g² }}</span>
      <div class="cite">Egghe, L. (2006). <i>Theory and practise of the g-index.</i> Scientometrics, 69(1), 131–152.</div></div>

    <div class="ref"><h4>m-index (m-quotient)</h4>
      <p>h-index dividido pela idade acadêmica (anos desde a 1ª publicação). Corrige o viés de antiguidade
      do h: mede a <b>velocidade</b> de construção de impacto. m ≈ 1 é considerado bom; ≈ 2–3, excelente.</p>
      <span class="formula">m = h / (ano atual − 1ª publicação)</span>
      <div class="cite">Hirsch, J. E. (2005). PNAS, 102(46). (definição do m-quotient no mesmo artigo.)</div></div>

    <div class="ref"><h4>FWCI — Field-Weighted Citation Impact</h4>
      <p>Razão entre as citações observadas e as <b>esperadas</b> para artigos do mesmo campo, ano e tipo.
      <b>1.0 = média mundial</b> da área; 2.0 = o dobro. Normaliza por campo → compara áreas com culturas
      de citação diferentes (equivalente ao MNCS / "crown indicator").</p>
      <span class="formula">FWCI = citações observadas / citações esperadas no campo·ano·tipo</span>
      <div class="cite">Waltman et al. (2011). <i>Towards a new crown indicator…</i> J. Informetrics, 5(1). · Lundberg (2007), <i>Item-oriented field normalization</i>, Scientometrics 72(3).</div></div>

    <div class="ref"><h4>Percentis de citação (top 10% / top 1%)</h4>
      <p>Posição do artigo na distribuição de citações do seu campo e ano. <b>Top 10%</b> = entre os 10%
      mais citados (classe mundial). Indicadores de percentil são mais robustos que médias, pouco
      sensíveis a um único artigo muito citado.</p>
      <span class="formula">percentil ≥ 90 → top 10% · ≥ 99 → top 1%</span>
      <div class="cite">Bornmann, L. (2013). <i>How to analyze percentile citation impact data…</i> JASIST, 64(3). · Bornmann &amp; Leydesdorff (2013).</div></div>

    <div class="ref"><h4>Crédito fracionado por autoria</h4>
      <p>Atribui a cada coautor <b>1/n</b> do artigo e <b>citações/n</b> (n = nº de autores). Corrige a
      hipercoautoria — distingue impacto real atribuível do inflado por listas longas de autores.</p>
      <span class="formula">crédito = Σ (citações_artigo / nº_autores)</span>
      <div class="cite">Waltman &amp; van Eck (2015). <i>Field-normalized citation impact indicators and the choice of an appropriate counting method.</i> J. Informetrics, 9(4).</div></div>

    <div class="ref"><h4>Índice de Gini + curva de Lorenz</h4>
      <p>Mede a <b>concentração</b> das citações entre docentes. A curva de Lorenz plota o % acumulado de
      citações vs. % acumulado de docentes; o Gini é a área entre ela e a diagonal de igualdade.
      0 = todos iguais; 1 = um docente concentra tudo.</p>
      <span class="formula">G = (2·Σ i·xᵢ)/(n·Σ xᵢ) − (n+1)/n</span>
      <div class="cite">Gini, C. (1912). <i>Variabilità e mutabilità.</i> · Lorenz, M. O. (1905). <i>Methods of measuring the concentration of wealth.</i> Publ. ASA, 9(70).</div></div>

    <div class="ref"><h4>i10-index e momentum</h4>
      <p><b>i10</b> = nº de artigos com ≥ 10 citações (popularizado pelo Google Scholar). <b>Momentum</b>
      (indicador próprio) = % das citações totais recebidas nos últimos 2 anos — proxy de aceleração /
      relevância recente da obra.</p>
      <span class="formula">momentum = citações(2 anos) / citações(total) × 100</span>
      <div class="cite">Google Scholar Metrics (2011) para i10. Momentum: indicador derivado (velocidade de citação).</div></div>

    <div class="ref"><h4>Qualis (CAPES) e SJR (SCImago)</h4>
      <p>Métricas de <b>veículo</b> (não do artigo). <b>Qualis</b> classifica periódicos por estratos
      (A1…C); <b>SJR</b> pondera as citações pelo prestígio da revista citante (análogo ao PageRank),
      em quartis Q1–Q4. Usados aqui para a grande área e contexto de qualidade.</p>
      <span class="formula">SJR ~ prestígio do citante (autovetor) · Qualis A1 &gt; A2 &gt; … &gt; C</span>
      <div class="cite">González-Pereira, Guerrero-Bote &amp; Moya-Anegón (2010). <i>A new approach to the metric of journals' scientific prestige: The SJR indicator.</i> J. Informetrics, 4(3). · Qualis/CAPES.</div></div>

    <div class="ref"><h4>Casamento por DOI (método)</h4>
      <p>As citações são obtidas no <b>OpenAlex</b> casando o <b>DOI</b> de cada artigo do Lattes (1:1, sem
      ambiguidade de homônimo). Artigos sem DOI não entram — por isso a cobertura é um <b>piso</b> e
      tende a subestimar quem publica em veículos sem DOI.</p>
      <span class="formula">Lattes (DOI) → OpenAlex (cited_by_count, FWCI, percentil)</span>
      <div class="cite">Priem, Piwowar &amp; Orr (2022). <i>OpenAlex: A fully-open index of scholarly works…</i> arXiv:2205.01833.</div></div>

    <div class="ref"><h4>Por que OpenAlex ≠ Google Scholar</h4>
      <p><b>OpenAlex</b> é uma base <b>aberta e estruturada</b>: indexa obras com metadados e DOI (periódicos
      e conferências indexados), permite cálculo de FWCI/percentil e tem API pública. Mas <b>não tem todos
      os artigos</b> — fica de fora muita produção <b>sem DOI</b>: anais e capítulos não indexados, relatórios,
      teses, alguns periódicos nacionais.</p>
      <p><b>Google Scholar</b> rastreia a web inteira (PDFs, anais, repositórios) → cobertura <b>maior</b> e
      números de citação <b>mais altos</b>, porém com duplicatas, itens não revisados por pares e <b>sem API</b>
      (acesso automatizado é bloqueado). Por isso <b>não</b> usamos o Scholar aqui.</p>
      <p><b>Consequência:</b> as citações e o h-index deste painel tendem a ser <b>menores</b> que os do
      Scholar, mas são <b>consistentes e comparáveis</b> entre docentes (mesma régua). Não compare os números
      daqui com prints do Google Scholar.</p>
      <div class="cite">Martín-Martín et al. (2021). <i>Google Scholar, Microsoft Academic, Scopus, Dimensions, Web of Science, and OpenCitations' COCI: a multidisciplinary comparison of coverage.</i> Scientometrics, 126.</div></div>

  </div>
</section>

<footer class="foot">
  Indicadores: <b>h/g/m-index</b>, <b>FWCI</b> (Field-Weighted Citation Impact), <b>percentis</b> (top 10%/1%),
  <b>momentum</b> (citações recentes), <b>crédito fracionado</b> por autoria, <b>Gini</b> (concentração).
  Fonte: OpenAlex (api.openalex.org), casado por DOI do Lattes; grande área via Qualis. Charts SVG/JS nesta página.
</footer>

<script>const DATA={payload};</script>
<script>
document.getElementById('k_gini2').textContent=DATA.kpis.gini_citacoes;
document.getElementById('k_n2').textContent=DATA.kpis.com_openalex;
{JS}
</script>
</div></body></html>"""


def main() -> None:
    data = analisar()
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_HTML.write_text(render_html(data), encoding="utf-8")
    k = data["kpis"]
    print(f"OK -> {OUT_JSON.relative_to(ROOT)}")
    print(f"OK -> {OUT_HTML.relative_to(ROOT)}")
    print(f"Docentes c/ OpenAlex: {k['com_openalex']}/{k['n_docentes']} | "
          f"citações={k['citacoes_total']} | FWCI méd={k['fwci_medio']} | "
          f"top10={k['top10_total']} | Gini={k['gini_citacoes']}")


if __name__ == "__main__":
    main()
