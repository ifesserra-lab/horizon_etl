"""Maturidade dos docentes por grande área — radar interativo (SVG + JS vanilla).

Para cada (entidade, grande área) calcula 4 sinais de maturidade a partir da
produção em periódicos (Lattes), casada com SCImago (SJR) e Qualis (estrato):

  * Volume        — nº de artigos na área (normalizado pela área mais forte da entidade)
  * Qualidade     — média do peso Qualis (A1=100 … C=3) dos artigos com estrato
  * Impacto       — média do quartil SJR do veículo (Q1=1.0 … Q4=0.25)
  * Consistência  — atividade (anos distintos) + recência (publicou nos últimos anos)

"score" da área = média dos 4 sinais → rótulo (Madura / Em desenvolvimento /
Esporádica / Incipiente; Declinante se forte no passado e parada).

Entidades: "Programa (todos)" (agregado) + cada docente (seletor no HTML).
Atribuição de área por artigo: área SCImago do veículo (evidência); se ausente,
a grande área declarada do docente no Lattes (fallback, menor evidência).

Uso:
  python -m src.scripts.analyze_maturity
  python -m src.scripts.analyze_maturity --min-artigos 2
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from src.scripts.analyze_venues import (
    LATTES_DIR, OUT_DIR, REF_DIR, SCIMAGO_CSV,
    QUALIS_WEIGHT, _A_STRATA,
    _docente_area, _grande_from_scimago_area,
    download_scimago, load_qualis, load_scimago, load_openalex,
    norm_issn, norm_name, _roster,
)

SExports = OUT_DIR
DEFAULT_JSON = OUT_DIR / "maturidade_areas.json"
DEFAULT_HTML = OUT_DIR / "maturidade_areas.html"

PROGRAMA = "__programa__"

# quartil SJR -> escore de impacto (proxy de alcance do veículo)
_Q_SCORE = {"Q1": 1.0, "Q2": 0.66, "Q3": 0.40, "Q4": 0.20}


# ---------------------------------------------------------------------------
# Coleta de artigos por (docente, área)
# ---------------------------------------------------------------------------

def _article_records(roster: dict[str, str], scimago: dict, qualis: dict):
    """Gera (lattes_id, nome, grande_area, titulo, doi, quartil, estrato|None,
    q_score|None, ano|None) por artigo de periódico, deduplicando obras
    repetidas do mesmo docente. Os 3 últimos campos (estrato, q_score, ano) são
    consumidos posicionalmente por _signals — novos campos vão ANTES deles."""
    by_id = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f

    recs = []
    for nome, lid in roster.items():
        f = by_id.get(lid)
        if not f:
            continue
        cv = json.loads(Path(f).read_text())
        decl = _docente_area(cv)  # grande área declarada (fallback)
        pb = cv.get("producao_bibliografica", {}) or {}
        seen_works = set()
        for a in pb.get("artigos_periodicos", []) or []:
            wk = norm_name(a.get("titulo", ""))
            if wk and wk in seen_works:
                continue
            if wk:
                seen_works.add(wk)
            issn = norm_issn(a.get("issn", ""))
            sm = scimago.get(issn) if issn else None
            grande = _grande_from_scimago_area(sm.get("area", "")) if sm else None
            if not grande:
                grande = decl if decl != "—" else "Não classificada"
            estrato = qualis.get(issn) if issn else None
            q = sm.get("quartil", "") if sm else ""
            q_score = _Q_SCORE.get(q)
            ano = None
            try:
                ano = int(str(a.get("ano", "")).strip()[:4])
            except (ValueError, TypeError):
                ano = None
            titulo = (a.get("titulo") or "").strip()
            doi = (a.get("doi") or "").strip()
            recs.append((lid, nome, grande, titulo, doi, q or "",
                         estrato, q_score, ano))
    return recs


def _signals(records: list[tuple], now_year: int) -> dict:
    """Calcula sinais brutos para um conjunto de artigos de UMA área/entidade."""
    n = len(records)
    estratos = [QUALIS_WEIGHT[e] / 100 for *_, e, _q, _a in records if e in QUALIS_WEIGHT]
    qs = [q for *_, _e, q, _a in records if q is not None]
    anos = sorted({a for *_, _e, _q, a in records if a})
    n_qualis = len(estratos)
    n_sjr = len(qs)
    qualidade = sum(estratos) / n_qualis if estratos else 0.0
    impacto = sum(qs) / n_sjr if qs else 0.0
    if anos:
        span = anos[-1] - anos[0] + 1
        distinct = len(anos)
        ultimo = anos[-1]
        atividade = min(1.0, distinct / 5)
        gap = now_year - ultimo
        recencia = 1.0 if gap <= 2 else (0.6 if gap <= 4 else (0.3 if gap <= 6 else 0.0))
        consistencia = 0.5 * atividade + 0.5 * recencia
    else:
        span = distinct = 0
        ultimo = None
        consistencia = 0.0
    return {
        "n": n, "n_qualis": n_qualis, "n_sjr": n_sjr,
        "qualidade": round(qualidade, 3),
        "impacto": round(impacto, 3),
        "consistencia": round(consistencia, 3),
        "ultimo_ano": ultimo, "anos_distintos": distinct, "span": span,
    }


def _label(score: float, sig: dict, now_year: int) -> str:
    ultimo = sig.get("ultimo_ano")
    parada = ultimo is not None and (now_year - ultimo) > 6
    if parada and sig["n"] >= 4:
        return "Declinante"
    if score >= 0.66:
        return "Madura"
    if score >= 0.40:
        return "Em desenvolvimento"
    if score >= 0.20:
        return "Esporádica"
    return "Incipiente"


def _entity_areas(records: list[tuple], now_year: int, min_artigos: int) -> dict:
    """Agrega sinais por grande área para uma entidade (lista de artigos)."""
    by_area = defaultdict(list)
    for r in records:
        by_area[r[2]].append(r)  # r[2] = grande_area
    out = {}
    max_vol = max((len(v) for v in by_area.values()), default=1)
    for area, recs in by_area.items():
        if len(recs) < min_artigos:
            continue
        sig = _signals(recs, now_year)
        volume = round(min(1.0, len(recs) / max_vol), 3)
        score = round((volume + sig["qualidade"] + sig["impacto"]
                       + sig["consistencia"]) / 4, 3)
        # artigos-fonte da área (titulo, doi, ano, estrato, quartil)
        arts = [{"t": r[3], "doi": r[4], "ano": r[8],
                 "estrato": r[6] or "", "quartil": r[5] or ""}
                for r in recs]
        arts.sort(key=lambda x: (-(x["ano"] or 0), x["t"].lower()))
        out[area] = {
            "n": sig["n"], "volume": volume,
            "qualidade": sig["qualidade"], "impacto": sig["impacto"],
            "consistencia": sig["consistencia"], "score": score,
            "label": _label(score, sig, now_year),
            "ultimo_ano": sig["ultimo_ano"], "anos_distintos": sig["anos_distintos"],
            "cobertura_qualis": sig["n_qualis"], "cobertura_sjr": sig["n_sjr"],
            "artigos": arts,
        }
    return out


def build_payload(roster: dict[str, str], scimago: dict, qualis: dict,
                  min_artigos: int) -> dict:
    now_year = datetime.now().year
    recs = _article_records(roster, scimago, qualis)

    entities = {}
    # Programa = todos os artigos juntos (min_artigos=1 p/ não perder área de programa)
    entities[PROGRAMA] = {
        "nome": "Programa (todos)",
        "areas": _entity_areas(recs, now_year, max(1, min_artigos)),
    }
    by_doc = defaultdict(list)
    nome_de = {}
    for r in recs:
        by_doc[r[0]].append(r)
        nome_de[r[0]] = r[1]
    for lid, drecs in by_doc.items():
        entities[lid] = {
            "nome": nome_de[lid],
            "areas": _entity_areas(drecs, now_year, min_artigos),
        }

    # eixos = união de áreas presentes em qualquer entidade, ordem estável por
    # volume agregado no programa
    prog_areas = entities[PROGRAMA]["areas"]
    all_areas = set(prog_areas)
    for e in entities.values():
        all_areas |= set(e["areas"])
    areas_order = sorted(all_areas,
                         key=lambda a: (-prog_areas.get(a, {}).get("n", 0), a))

    ordem_docentes = sorted(
        ((lid, e["nome"]) for lid, e in entities.items() if lid != PROGRAMA),
        key=lambda kv: kv[1].lower())

    return {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ano_referencia": now_year,
        "areas_order": areas_order,
        "ordem_docentes": ordem_docentes,
        "entities": entities,
        "sinais": ["Volume", "Qualidade", "Impacto", "Consistência"],
        "legenda_sinais": {
            "Volume": "nº de artigos na área (relativo à área mais forte da entidade)",
            "Qualidade": "média do peso Qualis (A1=100 … C=3) dos artigos com estrato",
            "Impacto": "média do quartil SJR do veículo (Q1=1.0 … Q4=0.25)",
            "Consistência": "atividade (anos distintos) + recência da última publicação",
        },
    }


# ---------------------------------------------------------------------------
# HTML (SVG + JS vanilla, sem CDN)
# ---------------------------------------------------------------------------

def render_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    return _HTML_TEMPLATE.replace("/*__DATA__*/", data_json)


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Maturidade por Área — Docentes</title>
<style>
  :root { --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          --bg:#0f1419; --card:#1a2129; --ink:#e6edf3; --mut:#8b98a5;
          --line:#2a3540; --accent:#4c9eff; --accent2:#ffb84c; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font-family:var(--font);
         line-height:1.5; padding:24px; }
  .wrap { max-width:1100px; margin:0 auto; }
  h1 { font-size:22px; margin:0 0 4px; }
  .sub { color:var(--mut); font-size:13px; margin:0 0 20px; }
  .bar { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:18px; }
  select { background:var(--card); color:var(--ink); border:1px solid var(--line);
           border-radius:8px; padding:8px 12px; font-size:14px; font-family:var(--font); }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
  @media (max-width:760px){ .grid{ grid-template-columns:1fr; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px;
          padding:18px; }
  .card h2 { font-size:15px; margin:0 0 2px; }
  .card .hint { color:var(--mut); font-size:12px; margin:0 0 10px; }
  svg { width:100%; height:auto; display:block; }
  .axis-label { fill:var(--ink); font-size:11px; cursor:pointer; }
  .axis-label:hover { fill:var(--accent); text-decoration:underline; }
  .ring { fill:none; stroke:var(--line); }
  .spoke { stroke:var(--line); }
  .poly { fill:rgba(76,158,255,.18); stroke:var(--accent); stroke-width:2; }
  .poly2 { fill:rgba(255,184,76,.18); stroke:var(--accent2); stroke-width:2; }
  .dot { fill:var(--accent); }
  table { width:100%; border-collapse:collapse; font-size:12.5px; margin-top:6px; }
  th,td { text-align:left; padding:5px 8px; border-bottom:1px solid var(--line); }
  th { color:var(--mut); font-weight:600; }
  td.num { text-align:right; font-variant-numeric:tabular-nums; }
  .tag { font-size:11px; padding:1px 7px; border-radius:10px; white-space:nowrap; }
  .Madura{ background:#143d28; color:#5fd99a; }
  .Em.desenvolvimento,.tag.dev{ background:#143a4d; color:#67c5ff; }
  .Esporádica{ background:#3d3414; color:#e6c14c; }
  .Incipiente{ background:#3a2030; color:#e08bb0; }
  .Declinante{ background:#3d1f1f; color:#ff8b8b; }
  .legend { color:var(--mut); font-size:11.5px; margin-top:10px; }
  .legend code { color:var(--ink); }
  .back { color:var(--accent); cursor:pointer; font-size:12px; user-select:none; }
  .src-arts { max-height:320px; overflow:auto; margin-top:12px;
              border-top:1px solid var(--line); padding-top:10px; }
  .src-h { font-size:12px; color:var(--mut); margin:0 0 6px; font-weight:600; }
  .src-item { font-size:12.5px; padding:5px 0; border-bottom:1px solid var(--line);
              line-height:1.4; }
  .src-item:last-child { border-bottom:none; }
  .src-y { color:var(--mut); font-variant-numeric:tabular-nums; }
  .src-item a { color:var(--accent); text-decoration:none; }
  .src-item a:hover { text-decoration:underline; }
  .src-t { color:var(--accent2); font-size:11px; white-space:nowrap; }
</style></head>
<body><div class="wrap">
  <h1>Maturidade por Área de Atuação</h1>
  <p class="sub" id="sub"></p>
  <div class="bar">
    <label for="ent" style="color:var(--mut);font-size:13px;">Entidade:</label>
    <select id="ent"></select>
  </div>
  <div class="grid">
    <div class="card">
      <h2>Maturidade por área</h2>
      <p class="hint">Cada eixo é uma grande área · valor = score (0–100). Clique numa área para o detalhe.</p>
      <svg id="radarAreas" viewBox="0 0 360 360"></svg>
    </div>
    <div class="card">
      <h2 id="sigTitle">Perfil de sinais</h2>
      <p class="hint" id="sigHint">Selecione uma área no radar ao lado.</p>
      <svg id="radarSig" viewBox="0 0 360 360"></svg>
      <div id="sigArts" class="src-arts"></div>
    </div>
  </div>
  <div class="card" style="margin-top:18px;">
    <h2>Detalhamento</h2>
    <div id="tableWrap"></div>
    <div class="legend" id="legend"></div>
  </div>
</div>
<script>
const DATA = /*__DATA__*/;
const SVGNS = "http://www.w3.org/2000/svg";
const SIG_KEYS = ["volume","qualidade","impacto","consistencia"];
let curArea = null;
const esc = s => (s||"").replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const cleanDoi = s => { const m=(s||"").match(/10\.\d{4,9}\/[^\s"'<>&?]+/); return m?m[0]:""; };

function el(tag, attrs, parent){
  const e = document.createElementNS(SVGNS, tag);
  for(const k in attrs) e.setAttribute(k, attrs[k]);
  if(parent) parent.appendChild(e);
  return e;
}
function polar(cx, cy, r, i, n){
  const ang = -Math.PI/2 + i*2*Math.PI/n;
  return [cx + r*Math.cos(ang), cy + r*Math.sin(ang)];
}
function drawRadar(svg, axes, values, opts){
  opts = opts || {};
  svg.innerHTML = "";
  const W=360, cx=180, cy=180, R=120;
  const n = axes.length;
  if(n < 3){
    const t = el("text",{x:cx,y:cy,"text-anchor":"middle",fill:"#8b98a5","font-size":13},svg);
    t.textContent = n===0 ? "Sem dados" : "Áreas insuficientes p/ radar (mín. 3)";
    return;
  }
  for(let g=1; g<=4; g++){
    const pts=[];
    for(let i=0;i<n;i++){ const p=polar(cx,cy,R*g/4,i,n); pts.push(p.join(",")); }
    el("polygon",{class:"ring",points:pts.join(" ")},svg);
  }
  for(let i=0;i<n;i++){
    const p=polar(cx,cy,R,i,n);
    el("line",{class:"spoke",x1:cx,y1:cy,x2:p[0],y2:p[1]},svg);
    const lp=polar(cx,cy,R+18,i,n);
    const t=el("text",{class:"axis-label",x:lp[0],y:lp[1],
      "text-anchor": Math.abs(lp[0]-cx)<8?"middle":(lp[0]<cx?"end":"start"),
      "dominant-baseline":"middle"},svg);
    let lab = axes[i];
    if(lab.length>16) lab = lab.slice(0,15)+"…";
    t.textContent = lab;
    if(opts.onAxis){ t.style.cursor="pointer"; t.addEventListener("click",()=>opts.onAxis(axes[i])); }
  }
  const pts=[];
  for(let i=0;i<n;i++){ const p=polar(cx,cy,R*Math.max(0,Math.min(1,values[i])),i,n); pts.push(p); }
  el("polygon",{class:opts.cls||"poly",points:pts.map(p=>p.join(",")).join(" ")},svg);
  for(const p of pts) el("circle",{class:"dot",cx:p[0],cy:p[1],r:3},svg);
}

function entAreas(entId){ return DATA.entities[entId].areas; }

function renderAreas(entId){
  const areas = entAreas(entId);
  const axes = DATA.areas_order.filter(a => areas[a]);
  const vals = axes.map(a => areas[a].score);
  drawRadar(document.getElementById("radarAreas"), axes, vals, {
    onAxis: (a)=>{ curArea=a; renderSig(entId); renderTable(entId); }
  });
  if(curArea && !areas[curArea]) curArea = null;
  if(!curArea && axes.length) curArea = axes.slice().sort((x,y)=>areas[y].score-areas[x].score)[0];
  renderSig(entId);
}

function renderSig(entId){
  const areas = entAreas(entId);
  const svg = document.getElementById("radarSig");
  const title = document.getElementById("sigTitle");
  const hint = document.getElementById("sigHint");
  if(!curArea || !areas[curArea]){
    svg.innerHTML=""; title.textContent="Perfil de sinais";
    hint.textContent="Selecione uma área no radar ao lado.";
    const b=document.getElementById("sigArts"); if(b) b.innerHTML=""; return;
  }
  const a = areas[curArea];
  title.textContent = "Perfil — " + curArea;
  hint.textContent = `${a.n} artigos · Qualis em ${a.cobertura_qualis} · SJR em ${a.cobertura_sjr} · último ${a.ultimo_ano||"—"}`;
  drawRadar(svg, ["Volume","Qualidade","Impacto","Consistência"],
            SIG_KEYS.map(k=>a[k]), {cls:"poly2"});
  renderArts(a.artigos || []);
}

function renderArts(arts){
  const box = document.getElementById("sigArts");
  if(!box) return;
  if(!arts.length){ box.innerHTML = '<div class="src-h" style="color:var(--mut)">Sem artigos-fonte nesta área.</div>'; return; }
  box.innerHTML = `<div class="src-h">Artigos-fonte das métricas (${arts.length})</div>` +
    arts.map(x=>{
      const t = esc(x.t) || "(sem título)";
      const doi = cleanDoi(x.doi);
      const ttl = doi ? `<a href="https://doi.org/${esc(doi)}" target="_blank" rel="noopener">${t}</a>` : t;
      const tags = [x.estrato, x.quartil].filter(Boolean).join(" · ");
      return `<div class="src-item"><span class="src-y">${x.ano||"?"}</span> ${ttl}` +
             (tags ? ` <span class="src-t">${esc(tags)}</span>` : "") + `</div>`;
    }).join("");
}

function renderTable(entId){
  const areas = entAreas(entId);
  const rows = DATA.areas_order.filter(a=>areas[a]).map(a=>({a, ...areas[a]}))
                 .sort((x,y)=>y.score-x.score);
  let h = `<table><thead><tr><th>Área</th><th class="num">Artigos</th>
    <th class="num">Volume</th><th class="num">Qualidade</th><th class="num">Impacto</th>
    <th class="num">Consist.</th><th class="num">Score</th><th>Maturidade</th>
    <th class="num">Último</th></tr></thead><tbody>`;
  for(const r of rows){
    const cls = r.label.replace(/ /g,".");
    const pct = x => Math.round(x*100);
    h += `<tr><td>${r.a}</td><td class="num">${r.n}</td>
      <td class="num">${pct(r.volume)}</td><td class="num">${pct(r.qualidade)}</td>
      <td class="num">${pct(r.impacto)}</td><td class="num">${pct(r.consistencia)}</td>
      <td class="num"><b>${pct(r.score)}</b></td>
      <td><span class="tag ${cls}">${r.label}</span></td>
      <td class="num">${r.ultimo_ano||"—"}</td></tr>`;
  }
  h += `</tbody></table>`;
  if(!rows.length) h = `<p style="color:var(--mut)">Sem áreas acima do mínimo de artigos.</p>`;
  document.getElementById("tableWrap").innerHTML = h;
}

function renderAll(entId){
  document.getElementById("sub").textContent =
    `Gerado em ${DATA.gerado_em} · ref ${DATA.ano_referencia} · ${DATA.ordem_docentes.length} docentes`;
  renderAreas(entId);
  renderTable(entId);
}

function init(){
  const sel = document.getElementById("ent");
  const opt0 = document.createElement("option");
  opt0.value = "__programa__"; opt0.textContent = "Programa (todos)";
  sel.appendChild(opt0);
  for(const [lid,nome] of DATA.ordem_docentes){
    const o = document.createElement("option"); o.value=lid; o.textContent=nome;
    sel.appendChild(o);
  }
  sel.addEventListener("change", ()=>{ curArea=null; renderAll(sel.value); });
  const L = DATA.legenda_sinais;
  document.getElementById("legend").innerHTML =
    "Sinais — " + Object.keys(L).map(k=>`<code>${k}</code>: ${L[k]}`).join(" · ");
  renderAll("__programa__");
}
init();
</script>
</body></html>"""


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    ap.add_argument("--qualis", default=str(REF_DIR / "qualis.csv"),
                    help="CSV Qualis (melhor estrato entre áreas)")
    ap.add_argument("--min-artigos", type=int, default=2,
                    help="mín. de artigos p/ uma área aparecer no radar do docente")
    args = ap.parse_args()

    if not SCIMAGO_CSV.exists():
        download_scimago()
    scimago = load_scimago()
    qualis = load_qualis(Path(args.qualis))
    print(f"Referências: SCImago={len(scimago)} · Qualis={len(qualis)}")

    roster = _roster()
    payload = build_payload(roster, scimago, qualis, args.min_artigos)

    n_areas = len(payload["areas_order"])
    prog = payload["entities"][PROGRAMA]["areas"]
    print(f"Docentes={len(payload['ordem_docentes'])} · áreas-eixo={n_areas}")
    print("Programa — maturidade por área:")
    for a in sorted(prog, key=lambda x: -prog[x]["score"]):
        d = prog[a]
        print(f"  {d['score']*100:5.1f}  {a:<34} n={d['n']:<3} {d['label']}")

    out_json = Path(args.json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written: {out_json}")

    out_html = Path(args.html)
    out_html.write_text(render_html(payload), encoding="utf-8")
    print(f"Written: {out_html}")


if __name__ == "__main__":
    main()
