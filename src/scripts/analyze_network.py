"""
Rede de coautoria dos docentes do IFES Campus Serra.

Monta a rede de colaboração interna (docente ↔ docente que coassinam trabalhos),
a partir do campo `autores` dos artigos/congressos no Lattes, e calcula métricas
de rede: grau, grau ponderado (nº de trabalhos juntos), intermediação
(betweenness), PageRank e comunidades (Louvain).

Gera um site interativo: digite o nome de um pesquisador e veja a ego-rede
(ele + colaboradores), com força das conexões e métricas.

Uso:
  python -m src.scripts.analyze_network
  python -m src.scripts.analyze_network --out data/exports/docentes/rede.html
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

import networkx as nx

from src.scripts.generate_docentes_executive import ROSTER_IDS
from src.scripts.analyze_venues import _docente_area
from src.scripts.didatica import bloco_metrica, MOBILE_CSS

BASE = Path(__file__).resolve().parents[2]
LATTES_DIR = BASE / "data" / "lattes_json"
OUT_DIR = BASE / "data" / "exports" / "docentes"
DEFAULT_OUT = OUT_DIR / "rede_colaboracao.html"

_SUFFIX = {"junior", "jr", "filho", "neto", "segundo", "sobrinho"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", s)


def _author_key(surname_part: str, given_part: str) -> tuple[str, str]:
    """(último sobrenome não-sufixo, inicial do primeiro nome)."""
    st = [t for t in _norm(surname_part).split() if t]
    gt = [t for t in _norm(given_part).split() if t]
    surname = ""
    for t in reversed(st):
        if t not in _SUFFIX:
            surname = t
            break
    ginit = gt[0][0] if gt else ""
    return surname, ginit


def build_roster_index() -> dict[tuple, str]:
    """(sobrenome, inicial) -> lattes_id do docente. Colisões: mantém 1 (raro)."""
    idx: dict[tuple, str] = {}
    for name, lid in ROSTER_IDS.items():
        toks = [t for t in _norm(name).split() if t]
        if not toks:
            continue
        ginit = toks[0][0]
        surname = ""
        for t in reversed(toks[1:] or toks):
            if t not in _SUFFIX:
                surname = t
                break
        idx[(surname, ginit)] = lid
    return idx


def map_author(author: str, idx: dict[tuple, str]) -> str | None:
    if "," in author:
        sp, gp = author.split(",", 1)
    else:
        sp, gp = author, ""
    return idx.get(_author_key(sp, gp))


def collect_coauthorship(roster_idx: dict[tuple, str]):
    by_id = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f

    pair_w: Counter = Counter()          # (id_a, id_b) -> nº trabalhos juntos
    ext_collab: dict[str, Counter] = defaultdict(Counter)  # id -> coautor externo -> n
    papers_with_coauthor: Counter = Counter()
    seen: set = set()                    # dedup global por título

    for lid, f in by_id.items():
        if lid not in ROSTER_IDS.values():
            continue
        pb = json.loads(Path(f).read_text()).get("producao_bibliografica", {}) or {}
        items = (pb.get("artigos_periodicos", []) or []) + \
                (pb.get("trabalhos_completos_congressos", []) or [])
        for it in items:
            title_k = _norm(it.get("titulo", "")).strip()
            if not title_k or title_k in seen:
                continue
            seen.add(title_k)
            authors = [a.strip() for a in (it.get("autores") or "").split(";") if a.strip()]
            roster_here = sorted({rid for a in authors if (rid := map_author(a, roster_idx))})
            ext = [a for a in authors if map_author(a, roster_idx) is None]
            for rid in roster_here:
                papers_with_coauthor[rid] += 1
                for e in ext:
                    ext_collab[rid][e[:34]] += 1
            for a, b in combinations(roster_here, 2):
                pair_w[(a, b)] += 1
    return pair_w, ext_collab, papers_with_coauthor


def build_graph(pair_w: Counter):
    G = nx.Graph()
    id2name = {v: k for k, v in ROSTER_IDS.items()}
    for lid, name in id2name.items():
        G.add_node(lid, name=name)
    for (a, b), w in pair_w.items():
        G.add_edge(a, b, weight=w)
    return G, id2name


def compute(G: nx.Graph) -> dict:
    # métricas (no maior componente p/ betweenness ser comparável; calcula em todo G)
    deg = dict(G.degree())
    wdeg = dict(G.degree(weight="weight"))
    btw = nx.betweenness_centrality(G, weight=None, normalized=True) if G.number_of_edges() else {}
    try:
        pr = nx.pagerank(G, weight="weight") if G.number_of_edges() else {}
    except Exception:
        pr = {}
    # comunidades (Louvain) só nos nós com aresta
    comm_map: dict[str, int] = {}
    sub = G.subgraph([n for n in G if deg.get(n, 0) > 0])
    if sub.number_of_edges():
        comms = nx.community.louvain_communities(sub, weight="weight", seed=42)
        for ci, nodes in enumerate(sorted(comms, key=len, reverse=True)):
            for n in nodes:
                comm_map[n] = ci
    # layout determinístico. Pesos amortecidos (log) p/ laços fortes não colapsarem
    # o núcleo; k maior espalha; isolados num anel externo p/ não amontoar.
    import math
    # Layout POR COMUNIDADE: cada comunidade ocupa um setor próprio (centro num
    # círculo grande) e é desenhada com spring local. Evita o "blob" único —
    # os grupos densos ficam separados na tela.
    groups: dict[int, list] = defaultdict(list)
    for n, ci in comm_map.items():
        groups[ci].append(n)
    pos: dict = {}
    if groups:
        ncomm = len(groups)
        maxsz = max(len(v) for v in groups.values())
        ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))
        Rcirc = 1.0 if ncomm > 1 else 0.0
        for idx, (ci, members) in enumerate(ordered):
            ang = 2 * math.pi * idx / ncomm
            ccx, ccy = Rcirc * math.cos(ang), Rcirc * math.sin(ang)
            sub = G.subgraph(members)
            if sub.number_of_edges():
                sp = nx.spring_layout(sub, seed=42,
                                      k=3.0 / math.sqrt(max(len(members), 1)),
                                      iterations=300)
            else:
                sp = {m: (0.0, 0.0) for m in members}
            r = 0.34 * math.sqrt(len(members) / maxsz)  # raio do cluster ~ tamanho
            for m in members:
                x, y = sp.get(m, (0.0, 0.0))
                pos[m] = (ccx + x * r, ccy + y * r)
    return {"deg": deg, "wdeg": wdeg, "btw": btw, "pr": pr, "comm": comm_map, "pos": pos}


def _areas(roster_ids: list[str]) -> dict:
    by_id = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f
    out = {}
    for lid in roster_ids:
        f = by_id.get(lid)
        if not f:
            out[lid] = ("—", "—")
            continue
        cv = json.loads(Path(f).read_text())
        out[lid] = (_docente_area(cv), _docente_area(cv, "area"))
    return out


def collect_projects(id2name: dict) -> tuple[Counter, Counter]:
    """Rede de co-participação em projetos de pesquisa (integrantes do Lattes)."""
    by_id = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f
    # índice de tokens dos nomes do roster
    rtok = {lid: set(_norm(name).split()) for lid, name in id2name.items()}

    def match(nome: str) -> str | None:
        nt = set(t for t in _norm(nome).split() if len(t) > 1)
        if len(nt) < 2:
            return None
        for lid, toks in rtok.items():
            if nt <= toks or toks <= nt:
                return lid
        return None

    pair: Counter = Counter()
    pcount: Counter = Counter()
    seen: set = set()
    for lid, f in by_id.items():
        if lid not in id2name:
            continue
        for p in (json.loads(Path(f).read_text()).get("projetos_pesquisa", []) or []):
            pk = _norm(p.get("nome", "")).strip()
            if not pk or pk in seen:
                continue
            seen.add(pk)
            members = sorted({mid for ig in (p.get("integrantes") or [])
                              if (mid := match(ig.get("nome", "")))})
            for mid in members:
                pcount[mid] += 1
            for a, b in combinations(members, 2):
                pair[(a, b)] += 1
    return pair, pcount


def analyze_patterns(G, m, id2name, areas, proj_pair: Counter, proj_count: Counter,
                     impact: dict | None = None) -> dict:
    impact = impact or {}     # id -> {score, qualidade, estrato_A, sjr_q1q2, artigos_qualis}

    def imp(x):
        return impact.get(x, {})
    comm = m["comm"]
    # ---- perfis de comunidade (ordenados por RELEVÂNCIA = impacto Qualis) ----
    groups: dict[int, list] = defaultdict(list)
    for lid, ci in comm.items():
        groups[ci].append(lid)
    comm_profiles = []
    for ci, members in groups.items():
        gareas = Counter(areas.get(x, ("—", "—"))[0] for x in members)
        gsub = Counter(areas.get(x, ("—", "—"))[1] for x in members)
        internal = sum(1 for a, b in G.edges(members)
                       if comm.get(a) == ci and comm.get(b) == ci)
        n = len(members)
        dens = round(2 * internal / (n * (n - 1)), 3) if n > 1 else 0
        # relevância: soma dos pesos Qualis; qualidade média; estrato A; Q1+Q2
        score_tot = sum(imp(x).get("score", 0) for x in members)
        a_tot = sum(imp(x).get("estrato_A", 0) for x in members)
        q1q2_tot = sum(imp(x).get("sjr_q1q2", 0) for x in members)
        com_pub = [x for x in members if imp(x).get("artigos_qualis", 0) > 0]
        qmean = round(sum(imp(x).get("qualidade", 0) for x in com_pub) / len(com_pub), 1) if com_pub else 0
        # top membros por IMPACTO (score Qualis), não por volume
        top = sorted(members, key=lambda x: -imp(x).get("score", 0))[:4]
        bridge = max(members, key=lambda x: m["btw"].get(x, 0))
        comm_profiles.append({
            "id": ci + 1, "n": n,
            "area": gareas.most_common(1)[0][0],
            "subareas": [f"{k} ({v})" for k, v in gsub.most_common(3)],
            "lacos_internos": internal, "densidade": dens,
            "score": score_tot, "qualidade_media": qmean,
            "estrato_A": a_tot, "q1q2": q1q2_tot,
            "membros_top": [f"{id2name[x]} ({imp(x).get('score',0)})" for x in top],
            "ponte": id2name[bridge],
        })
    comm_profiles.sort(key=lambda c: -c["score"])
    for i, c in enumerate(comm_profiles, 1):
        c["rank"] = i

    # ---- padrão por ÁREA (homofilia) ----
    area_mat: Counter = Counter()
    intra = inter = 0
    for a, b in G.edges:
        ga, gb = areas.get(a, ("—",))[0], areas.get(b, ("—",))[0]
        key = tuple(sorted((ga, gb)))
        area_mat[key] += 1
        if ga == gb:
            intra += 1
        else:
            inter += 1
    tot_e = intra + inter
    area_pairs = [{"a": k[0], "b": k[1], "n": v}
                  for k, v in sorted(area_mat.items(), key=lambda x: -x[1])][:10]

    # ---- hubs (autores) ----
    def topn(d, k=8):
        return [{"name": id2name[i], "v": round(v, 4) if isinstance(v, float) else v}
                for i, v in sorted(d.items(), key=lambda x: -x[1])[:k] if v]
    hubs = {
        "grau_ponderado": topn(m["wdeg"]),
        "intermediacao": topn(m["btw"]),
        "pagerank": topn(m["pr"]),
    }

    # ---- pares (coautoria mais forte) ----
    pares = sorted(({"a": id2name[a], "b": id2name[b], "w": G[a][b]["weight"]}
                    for a, b in G.edges), key=lambda x: -x["w"])[:12]

    # ---- projetos (co-participação) ----
    proj_pairs = sorted(({"a": id2name[a], "b": id2name[b], "n": w}
                         for (a, b), w in proj_pair.items() if a in id2name and b in id2name),
                        key=lambda x: -x["n"])[:12]
    proj_top = [{"name": id2name[i], "n": c}
                for i, c in proj_count.most_common(10) if i in id2name]
    # sobreposição coautoria × projeto
    coaut_pairs = {tuple(sorted((a, b))) for a, b in G.edges}
    projp = {tuple(sorted(k)) for k in proj_pair}
    overlap = len(coaut_pairs & projp)

    return {
        "comunidades": comm_profiles,
        "area": {"pares": area_pairs, "intra": intra, "inter": inter,
                 "pct_intra": round(100 * intra / tot_e) if tot_e else 0},
        "hubs": hubs, "pares": pares,
        "projetos": {"pares": proj_pairs, "top": proj_top,
                     "overlap_coautoria": overlap, "n_pares_proj": len(projp)},
    }


def emit(G, id2name, m, ext_collab, papers, out_path: Path, patterns: dict | None = None) -> dict:
    areas = _areas(list(id2name))
    xs = [p[0] for p in m["pos"].values()]
    ys = [p[1] for p in m["pos"].values()]
    minx, maxx = (min(xs), max(xs)) if xs else (0, 1)
    miny, maxy = (min(ys), max(ys)) if ys else (0, 1)

    def nx_(v, lo, hi):
        return (v - lo) / (hi - lo) if hi > lo else 0.5

    nodes = []
    for lid in G.nodes:
        ga, sa = areas.get(lid, ("—", "—"))
        nb = sorted(((id2name[n], G[lid][n]["weight"]) for n in G.neighbors(lid)),
                    key=lambda x: -x[1])
        if lid in m["pos"]:
            px, py = m["pos"][lid]
            x, y, iso = round(nx_(px, minx, maxx), 4), round(nx_(py, miny, maxy), 4), False
        else:
            x, y, iso = None, None, True   # isolado: sem coautoria interna
        nodes.append({
            "isolado": iso,
            "id": lid, "name": id2name[lid], "area": ga, "subarea": sa,
            "deg": m["deg"].get(lid, 0), "wdeg": m["wdeg"].get(lid, 0),
            "btw": round(m["btw"].get(lid, 0.0), 4),
            "pr": round(m["pr"].get(lid, 0.0), 4),
            "comm": m["comm"].get(lid, -1),
            "papers": papers.get(lid, 0),
            "x": x, "y": y,
            "collabs": [{"name": n, "w": w} for n, w in nb[:12]],
            "ext": [{"name": n, "n": c} for n, c in ext_collab.get(lid, Counter()).most_common(8)],
        })
    edges = [{"s": a, "t": b, "w": G[a][b]["weight"]} for a, b in G.edges]

    n_comm = len({n["comm"] for n in nodes if n["comm"] >= 0})
    stats = {
        "n_docentes": len(nodes),
        "n_conectados": sum(1 for n in nodes if n["deg"] > 0),
        "n_arestas": len(edges),
        "n_comunidades": n_comm,
        "aresta_mais_forte": max((e["w"] for e in edges), default=0),
    }
    payload = {"gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
               "stats": stats, "nodes": nodes, "edges": edges,
               "patterns": patterns or {}}
    out_path.with_suffix(".json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    out_path.write_text(_html(payload), encoding="utf-8")
    return stats


def _html(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    return r"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rede de Colaboração — IFES Campus Serra</title>
<style>
:root{--bg:#f4f8f5;--ink:#16241a;--sub:#5f7268;--line:#e2ebe4;--green:#0f7a40;--paper:#fff;
 --font:'Inter','Segoe UI',system-ui,sans-serif;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--ink);font-family:var(--font);}
.dev-banner{background:#b8860b;color:#fff;text-align:center;font-size:13px;font-weight:600;
 padding:7px 12px;letter-spacing:.02em;}
.devtag{display:inline-block;background:#f7f0dd;color:#b8860b;font-size:11px;font-weight:700;
 padding:3px 9px;border-radius:999px;vertical-align:middle;margin-left:8px;text-transform:uppercase;letter-spacing:.05em;}
header{padding:22px 28px;border-bottom:3px solid var(--green);background:var(--paper);}
header h1{font-size:22px;} header p{color:var(--sub);font-size:13px;margin-top:4px;}
.search{margin-top:14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;}
.search input{font-size:15px;padding:9px 13px;border:1px solid var(--line);border-radius:9px;width:300px;}
.search .hint{font-size:12px;color:var(--sub);}
.btn{font-size:13px;padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:#fff;
 cursor:pointer;color:var(--ink);} .btn:hover{background:#e7f4ec;border-color:var(--green);}
.wrap{display:flex;gap:0;height:calc(100vh - 116px);}
#net{flex:1;background:radial-gradient(circle at 50% 40%,#fff,#eef5f0);}
#panel{width:360px;flex-shrink:0;background:var(--paper);border-left:1px solid var(--line);
 padding:20px;overflow-y:auto;}
#panel h2{font-size:18px;color:var(--green);} #panel .area{font-size:12px;color:var(--sub);margin-bottom:14px;}
.kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;}
.kpi{background:#f4f8f5;border:1px solid var(--line);border-radius:8px;padding:10px;text-align:center;}
.kpi b{font-size:20px;color:var(--green);display:block;} .kpi span{font-size:10px;color:var(--sub);}
.sec{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--sub);
 margin:16px 0 7px;} .row{display:flex;justify-content:space-between;font-size:13px;padding:4px 8px;
 background:#f4f8f5;border-radius:5px;margin-bottom:4px;cursor:pointer;} .row:hover{background:#e7f4ec;}
.row .w{color:var(--green);font-weight:700;} .muted{color:var(--sub);font-size:12px;}
.legend{position:absolute;bottom:12px;left:12px;font-size:11px;color:var(--sub);background:rgba(255,255,255,.85);
 padding:8px 10px;border-radius:8px;border:1px solid var(--line);}
</style></head><body>
<div id="exp-banner" style="background:#b5455f;color:#fff;padding:10px 16px;font-weight:600;font-size:13.5px;text-align:center;position:sticky;top:0;z-index:9999;box-shadow:0 2px 6px rgba(0,0,0,.2);font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">⚠️ Estudo experimental em condução — os dados são preliminares e podem ser modificados. Não usar como fonte da verdade.</div>
<div class="dev-banner">🚧 Under development — versão preliminar, dados e métricas em validação</div>
<header>
 <h1>Rede de Colaboração dos Docentes — IFES Campus Serra <span class="devtag">Under development</span></h1>
 <p>Coautoria entre docentes (artigos + congressos no Lattes). Tamanho do nó = trabalhos em coautoria; cor = comunidade; espessura da aresta = nº de trabalhos juntos.</p>
 <div class="search">
   <input id="q" list="names" placeholder="Digite um pesquisador..." autocomplete="off">
   <datalist id="names"></datalist>
   <button class="btn" id="zin">+ zoom</button>
   <button class="btn" id="zout">− zoom</button>
   <button class="btn" id="spr">espalhar +</button>
   <button class="btn" id="cmp">espalhar −</button>
   <button class="btn" id="rst">resetar</button>
   <span class="hint">Roda do mouse = zoom · arraste = mover · clique num nó/colaborador = ego-rede</span>
 </div>
</header>
<div class="wrap">
 <div style="flex:1;position:relative;"><canvas id="net"></canvas>
   <div class="legend" id="legend"></div></div>
 <div id="panel"><p class="muted">Digite ou clique num pesquisador para ver a ego-rede e as métricas.</p></div>
</div>
__EXPL__
__PATTERNS__
<script>
const DATA = __DATA__;
const N = DATA.nodes, E = DATA.edges;
const byId = {}; N.forEach(n=>byId[n.id]=n);
const nameToId = {}; N.forEach(n=>nameToId[n.name.toLowerCase()]=n.id);
const adj = {}; N.forEach(n=>adj[n.id]=[]);
E.forEach(e=>{adj[e.s].push([e.t,e.w]); adj[e.t].push([e.s,e.w]);});
const PALETTE=['#0f7a40','#2f6fb0','#b8860b','#b5455f','#6a4c93','#1f9d57','#c0392b','#16a085','#8e44ad','#d35400','#2c3e50','#27ae60'];
const cv=document.getElementById('net'), ctx=cv.getContext('2d');
const dl=document.getElementById('names');
N.slice().sort((a,b)=>a.name.localeCompare(b.name)).forEach(n=>{const o=document.createElement('option');o.value=n.name;dl.appendChild(o);});
let W,H,sel=null;
const maxW=Math.max(1,...N.map(n=>n.wdeg||0));
const topHubs=new Set(N.slice().sort((a,b)=>(b.wdeg||0)-(a.wdeg||0)).slice(0,6).map(n=>n.id));
const conn=N.filter(n=>!n.isolado), iso=N.filter(n=>n.isolado);
// coords de MUNDO (independem da tela). Conectados via layout; isolados em grade ao pé.
const BASE=1300; let spread=1;
const isoCols=Math.max(1,Math.ceil(Math.sqrt(iso.length)*1.8));
function worldPos(n){
  if(!n.isolado) return {x:n.x*BASE*spread, y:n.y*BASE*0.7*spread};
  const i=iso.indexOf(n); const c=i%isoCols, r=Math.floor(i/isoCols);
  return {x:c*70, y:BASE*0.7*spread+70+r*42};
}
let view={s:1,tx:0,ty:0};
function S(p){return {x:p.x*view.s+view.tx, y:p.y*view.s+view.ty};}  // mundo→tela
function fit(){
  const ps=conn.map(worldPos); if(!ps.length){view={s:1,tx:40,ty:40};return;}
  const xs=ps.map(p=>p.x),ys=ps.map(p=>p.y);
  const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
  const m=70,s=Math.min((W-2*m)/Math.max(x1-x0,1),(H-2*m)/Math.max(y1-y0,1));
  view.s=s; view.tx=m-x0*s+((W-2*m)-(x1-x0)*s)/2; view.ty=m-y0*s;
}
function resize(){const r=cv.parentElement.getBoundingClientRect();cv.width=r.width;cv.height=r.height;W=r.width;H=r.height;if(!sel)fit();draw();}
window.addEventListener('resize',resize);
function shortName(s){const p=s.split(' ');return p[0]+(p.length>1?' '+p[p.length-1]:'');}
function rad(n){return 4+Math.sqrt((n.wdeg||0)/maxW)*15;}   // 4..19px
function col(n){return n.comm>=0?PALETTE[n.comm%PALETTE.length]:'#9bb0a4';}
// EGO: foco no centro da tela, vizinhos em círculo (laço forte = mais perto)
function egoScreen(){
  const P={},cx=W*0.5,cy=H*0.5; P[sel]={x:cx,y:cy};
  const nb=(adj[sel]||[]).slice().sort((a,b)=>b[1]-a[1]);const k=nb.length||1;
  const R=Math.min(W,H)*0.40;
  nb.forEach(([t,w],i)=>{const ang=(i/k)*2*Math.PI-Math.PI/2;
    const rr=R*(0.55+0.45*(1-Math.min(w,maxW)/maxW));
    P[t]={x:cx+rr*Math.cos(ang),y:cy+rr*Math.sin(ang)};});
  return P;
}
function draw(){
  ctx.clearRect(0,0,W,H);
  if(sel){drawEgo();return;}
  // arestas (mundo→tela)
  E.forEach(e=>{const a=S(worldPos(byId[e.s])),b=S(worldPos(byId[e.t]));
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
    ctx.strokeStyle='rgba(120,140,128,.13)';ctx.lineWidth=Math.min(.4+e.w*.25,2);ctx.stroke();});
  N.forEach(n=>{const p=S(worldPos(n));const rr=rad(n)*Math.min(view.s,1.2);
    ctx.beginPath();ctx.arc(p.x,p.y,Math.max(rr,2),0,7);
    ctx.fillStyle=n.isolado?'#c2cdc6':col(n);ctx.globalAlpha=n.isolado?.7:1;ctx.fill();ctx.globalAlpha=1;
    if(topHubs.has(n.id)){ctx.fillStyle='#16241a';ctx.font='11px Inter,sans-serif';
      ctx.fillText(shortName(n.name),p.x+rr+4,p.y+3);}});
  legend(false);
}
function drawEgo(){
  const P=egoScreen(),ego=new Set(Object.keys(P));
  E.forEach(e=>{if(e.s!==sel&&e.t!==sel)return;const a=P[e.s],b=P[e.t];if(!a||!b)return;
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
    ctx.strokeStyle='rgba(15,122,64,.45)';ctx.lineWidth=Math.min(1+e.w*0.8,10);ctx.stroke();
    const mx=(a.x+b.x)/2,my=(a.y+b.y)/2;ctx.fillStyle='#0a5c30';ctx.font='bold 11px Inter,sans-serif';ctx.fillText(e.w,mx,my-2);});
  ego.forEach(id=>{const n=byId[id],p=P[id],focus=id===sel;
    ctx.beginPath();ctx.arc(p.x,p.y,(focus?20:rad(n)+3),0,7);
    ctx.fillStyle=col(n);ctx.fill();
    if(focus){ctx.lineWidth=3;ctx.strokeStyle='#16241a';ctx.stroke();}
    ctx.fillStyle='#16241a';ctx.font=(focus?'bold 14px':'12px')+' Inter,sans-serif';
    ctx.fillText(shortName(n.name),p.x+(focus?24:rad(n)+6),p.y+4);});
  legend(true);
}
function legend(isEgo){document.getElementById('legend').innerHTML = isEgo
  ? 'Ego-rede de '+byId[sel].name+' · '+(adj[sel]||[]).length+' colaboradores · clique fora p/ voltar'
  : DATA.stats.n_docentes+' docentes · '+DATA.stats.n_conectados+' conectados · '+
    DATA.stats.n_arestas+' laços · '+DATA.stats.n_comunidades+' comunidades (cor) · '+iso.length+' sem coautoria (cinza)';}
function panel(id){
  const n=byId[id];if(!n)return;
  const collabs=n.collabs.map(c=>`<div class="row" onclick="selectName('${c.name.replace(/'/g,"\\'")}')"><span>${c.name}</span><span class="w">${c.w}</span></div>`).join('')||'<p class="muted">Sem coautoria interna registrada.</p>';
  const ext=n.ext.map(c=>`<div class="row"><span>${c.name}</span><span class="w">${c.n}</span></div>`).join('')||'<p class="muted">—</p>';
  document.getElementById('panel').innerHTML=`
   <h2>${n.name}</h2><div class="area">${n.area} · ${n.subarea}</div>
   <div class="kpis">
     <div class="kpi"><b>${n.deg}</b><span>colaboradores internos</span></div>
     <div class="kpi"><b>${n.wdeg}</b><span>trabalhos em coautoria</span></div>
     <div class="kpi"><b>${(n.btw*100).toFixed(1)}</b><span>intermediação (×100)</span></div>
     <div class="kpi"><b>${n.papers}</b><span>trabalhos c/ coautor</span></div>
   </div>
   <div class="sec">Comunidade</div><p class="muted">Grupo ${n.comm>=0?('#'+(n.comm+1)):'isolado'}</p>
   <div class="sec">Colaboradores internos (nº de trabalhos)</div>${collabs}
   <div class="sec">Coautores externos (frequentes)</div>${ext}`;
}
function clearSel(){sel=null;document.getElementById('q').value='';fit();
  document.getElementById('panel').innerHTML='<p class="muted">Digite ou clique num pesquisador para ver a ego-rede e as métricas.</p>';draw();}
function selectName(name){const id=nameToId[(name||'').toLowerCase()];if(!id){return;}sel=id;panel(id);draw();}
document.getElementById('q').addEventListener('change',e=>{if(!e.target.value)clearSel();else selectName(e.target.value);});
document.getElementById('q').addEventListener('input',e=>{if(nameToId[e.target.value.toLowerCase()])selectName(e.target.value);});
// hit-test (mundo no global, tela no ego)
function hit(mx,my){
  const P = sel?egoScreen():null;
  let best=null,bd=1e9;
  N.forEach(n=>{let p; if(sel){p=P[n.id]; if(!p)return;} else {p=S(worldPos(n));}
    const d=(p.x-mx)**2+(p.y-my)**2, rr=(sel?(n.id===sel?20:rad(n)+3):rad(n))+6;
    if(d<bd&&d<Math.max(120,rr*rr)){bd=d;best=n;}});
  return best;
}
// arraste = pan (global) ; clique = seleciona
let drag=null,moved=false;
cv.addEventListener('mousedown',e=>{drag={x:e.clientX,y:e.clientY,tx:view.tx,ty:view.ty};moved=false;});
window.addEventListener('mousemove',e=>{if(!drag||sel)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
  if(Math.abs(dx)+Math.abs(dy)>3)moved=true;view.tx=drag.tx+dx;view.ty=drag.ty+dy;draw();});
window.addEventListener('mouseup',()=>{drag=null;});
cv.addEventListener('click',ev=>{
  if(moved)return; const r=cv.getBoundingClientRect();
  const b=hit(ev.clientX-r.left,ev.clientY-r.top);
  if(b){sel=b.id;document.getElementById('q').value=b.name;panel(b.id);draw();} else clearSel();
});
// zoom na roda (em torno do cursor) — só na visão global
cv.addEventListener('wheel',ev=>{ev.preventDefault();if(sel)return;
  const r=cv.getBoundingClientRect(),mx=ev.clientX-r.left,my=ev.clientY-r.top;
  const f=ev.deltaY<0?1.15:1/1.15; const wx=(mx-view.tx)/view.s,wy=(my-view.ty)/view.s;
  view.s=Math.max(0.1,Math.min(8,view.s*f)); view.tx=mx-wx*view.s; view.ty=my-wy*view.s; draw();
},{passive:false});
document.getElementById('zin').onclick=()=>{view.s=Math.min(8,view.s*1.25);draw();};
document.getElementById('zout').onclick=()=>{view.s=Math.max(0.1,view.s/1.25);draw();};
// espalhar: aumenta o "mundo" em torno do centro da tela SEM re-encaixar (senão anula)
function applySpread(f){
  if(sel)return; const cx=W/2,cy=H/2;
  const wx=(cx-view.tx)/view.s, wy=(cy-view.ty)/view.s;  // ponto-mundo no centro
  spread*=f; view.tx=cx-wx*f*view.s; view.ty=cy-wy*f*view.s; draw();
}
document.getElementById('spr').onclick=()=>applySpread(1.3);
document.getElementById('cmp').onclick=()=>{if(spread/1.3>=0.4)applySpread(1/1.3);};
document.getElementById('rst').onclick=()=>{spread=1;clearSel();};
resize();
</script></body></html>""".replace("</style>", MOBILE_CSS+"</style>", 1).replace("__DATA__", data).replace("__EXPL__", _EXPL_REDE).replace("__PATTERNS__", _patterns_html(payload.get("patterns") or {}))


_EXPL_REDE = bloco_metrica({
    "titulo": "Rede de coautoria (como ler)",
    "o_que": "Grafo de <b>coautoria</b> entre docentes (artigos + congressos do Lattes): cada nó é "
             "um docente (tamanho = trabalhos em coautoria), a cor é a <b>comunidade</b> detectada "
             "(Louvain) e a espessura da aresta é o nº de trabalhos juntos.",
    "como_ler": "<b>Aglomerados</b> de mesma cor = grupos que publicam juntos. <b>Nós centrais</b> "
                "(grandes, muito conectados) = pontes/colaboradores frequentes que ligam grupos.",
    "nao_concluir": [
        "Coautoria é cruzada <b>por nome</b> (sujeita a homônimo) e <b>coautores externos</b> ao "
        "campus não entram no grafo.",
        "Ausência de aresta <b>≠</b> ausência de colaboração (orientação, projetos e parcerias "
        "informais não aparecem).",
        "Versão <b>preliminar</b> (under development) — métricas em validação.",
    ],
    "gestores": "Identificar <b>grupos</b> e <b>pontes</b>; estimular colaboração entre comunidades "
                "isoladas e dar visibilidade a quem conecta áreas.",
})


def _patterns_html(p: dict) -> str:
    if not p:
        return ""
    css = """<style>
.an{max-width:1100px;margin:0 auto;padding:30px 28px 70px;}
.an h2{font-size:24px;color:var(--green);margin:34px 0 6px;border-bottom:2px solid var(--line);padding-bottom:6px;}
.an .d{color:var(--sub);font-size:13px;margin-bottom:14px;}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;}
.cc{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:16px;}
.cc h3{font-size:15px;}.cc .tag{font-size:11px;color:var(--sub);}
.cc ul{margin:8px 0 0 16px;font-size:13px;} .cc .mini{font-size:11px;color:var(--sub);margin-top:8px;}
table.an-t{width:100%;border-collapse:collapse;font-size:13px;background:var(--paper);border:1px solid var(--line);border-radius:10px;overflow:hidden;}
.an-t th,.an-t td{padding:8px 12px;border-bottom:1px solid var(--line);text-align:left;}
.an-t th{font-size:11px;text-transform:uppercase;color:var(--sub);}
.an-t td.n{text-align:right;color:var(--green);font-weight:700;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px;}
@media(max-width:800px){.grid2{grid-template-columns:1fr;}}
.note{font-size:12px;color:var(--sub);font-style:italic;margin-top:8px;}
.exp{background:#eef4fb;border-left:3px solid var(--blue,#2f6fb0);border-radius:6px;
 padding:11px 13px;font-size:13px;line-height:1.6;margin:10px 0 16px;color:var(--ink);}
.exp b{color:var(--ink);}
</style>"""
    # comunidades (ordenadas por relevância / impacto Qualis)
    comm = "".join(
        f"<div class='cc'><h3>#{c['rank']} · Comunidade <span class='tag'>· {c['n']} docentes · {c['area']}</span></h3>"
        f"<div class='tag' style='color:var(--green);font-weight:700;'>Impacto Qualis {c.get('score',0)} · "
        f"nota média {c.get('qualidade_media',0)} · {c.get('estrato_A',0)} artigos A · {c.get('q1q2',0)} Q1+Q2</div>"
        f"<div class='tag'>{' · '.join(c['subareas'])}</div>"
        f"<ul>" + "".join(f"<li>{x}</li>" for x in c['membros_top']) + "</ul>"
        f"<div class='mini'>{c['lacos_internos']} laços internos · densidade {c['densidade']} · ponte: <b>{c['ponte']}</b></div></div>"
        for c in p.get("comunidades", [])
    )
    # área
    a = p.get("area", {})
    arows = "".join(f"<tr><td>{x['a']}{' ↔ '+x['b'] if x['b']!=x['a'] else ' (interno)'}</td><td class='n'>{x['n']}</td></tr>"
                    for x in a.get("pares", []))
    # hubs
    def htab(rows, lab):
        return ("<table class='an-t'><thead><tr><th>Docente</th><th>"+lab+"</th></tr></thead><tbody>"
                + "".join(f"<tr><td>{r['name']}</td><td class='n'>{r['v']}</td></tr>" for r in rows)
                + "</tbody></table>")
    hubs = p.get("hubs", {})
    # pares coautoria
    pares = "".join(f"<tr><td>{x['a']} ↔ {x['b']}</td><td class='n'>{x['w']}</td></tr>" for x in p.get("pares", []))
    # projetos
    pj = p.get("projetos", {})
    pjpairs = "".join(f"<tr><td>{x['a']} ↔ {x['b']}</td><td class='n'>{x['n']}</td></tr>" for x in pj.get("pares", []))
    pjtop = "".join(f"<tr><td>{x['name']}</td><td class='n'>{x['n']}</td></tr>" for x in pj.get("top", []))
    return css + f"""
<div class="an">
  <h2>Comunidades por relevância (impacto, não volume)</h2>
  <div class="exp"><b>O que é:</b> os grupos de colaboração (Louvain) ordenados pela <b>relevância da
  produção</b>, não pelo tamanho nem pelo volume de coautoria. <b>Impacto Qualis</b> = soma dos pesos
  Qualis (A1=100, A2=85… C=3) das publicações dos membros; <b>nota média</b> = qualidade média por
  artigo (100 = só A1); <b>Q1+Q2</b> = artigos em periódico de alto quartil SJR. Os membros listados
  são os de maior impacto do grupo (score ao lado), não os mais prolíficos.
  <b>Como ler:</b> um grupo pequeno pode liderar se publica em estratos altos; densidade alta = grupo
  coeso; a <b>ponte</b> conecta o grupo aos demais. <b>Decisão:</b> grupos de alta relevância são
  núcleos estratégicos; pontes são pessoas-chave a proteger.</div>
  <div class="cards">{comm}</div>

  <h2>Padrão por área (homofilia)</h2>
  <div class="exp"><b>O que é:</b> mede se a colaboração fica <b>dentro</b> da mesma grande área
  (homofilia) ou cruza áreas (interdisciplinaridade). <b>Como ler:</b> {a.get('pct_intra',0)}% dos
  laços são intra-área — quanto menor, mais interdisciplinar é o campus. A linha de maior valor
  mostra o eixo de colaboração mais intenso. <b>Decisão:</b> pontes inter-área fortes indicam onde
  estimular projetos conjuntos; áreas só com laço interno podem estar em silo.</div>
  <table class="an-t"><thead><tr><th>Áreas conectadas</th><th>Laços</th></tr></thead><tbody>{arows}</tbody></table>

  <h2>Autores centrais (hubs)</h2>
  <div class="exp"><b>O que é:</b> três formas de "ser central". <b>Grau ponderado</b> = volume de
  trabalhos em coautoria (quão colaborativo). <b>Intermediação (betweenness)</b> = quanto o docente
  está no caminho entre outros — é a <b>ponte</b> da rede; perdê-lo fragmenta o campus.
  <b>PageRank</b> = prestígio (conectado a quem também é bem conectado).
  <b>Como ler:</b> alto grau mas baixa intermediação = colabora muito, porém dentro do próprio grupo;
  alta intermediação = articulador entre grupos. <b>Decisão:</b> articuladores são críticos para a coesão.</div>
  <div class="grid2">
    <div>{htab(hubs.get('grau_ponderado',[]),'Trab. coautoria')}</div>
    <div>{htab(hubs.get('intermediacao',[]),'Intermediação')}</div>
  </div>
  <div style="margin-top:14px;">{htab(hubs.get('pagerank',[]),'PageRank')}</div>

  <h2>Coautores — laços mais fortes</h2>
  <div class="exp"><b>O que é:</b> os pares de docentes que mais publicam juntos (peso da aresta =
  nº de trabalhos coassinados). <b>Como ler:</b> laços muito fortes revelam duplas/parcerias estáveis
  que sustentam linhas de pesquisa. <b>Decisão:</b> risco de dependência se uma linha inteira repousa
  num único par — vale diversificar; e parcerias fortes são candidatas naturais a coordenar projetos maiores.</div>
  <table class="an-t"><thead><tr><th>Par</th><th>Trabalhos</th></tr></thead><tbody>{pares}</tbody></table>

  <h2>Padrão por projetos</h2>
  <div class="exp"><b>O que é:</b> uma segunda rede — quem participa dos mesmos <b>projetos de pesquisa</b>
  (não publicações). <b>Como ler:</b> {pj.get('overlap_coautoria',0)} pares colaboram tanto em projeto
  quanto em publicação (de {pj.get('n_pares_proj',0)} pares de projeto) — alta sobreposição = projetos
  geram publicação conjunta (saudável); baixa = projetos que não viram produção compartilhada.
  <b>Decisão:</b> pares que coordenam projetos mas não publicam juntos são oportunidade de output.</div>
  <div class="grid2">
    <div><table class="an-t"><thead><tr><th>Par (projetos juntos)</th><th>Projetos</th></tr></thead><tbody>{pjpairs}</tbody></table></div>
    <div><table class="an-t"><thead><tr><th>Docente</th><th>Projetos (c/ pares)</th></tr></thead><tbody>{pjtop}</tbody></table></div>
  </div>
  <div class="note">Comunidades por modularidade (Louvain, seed fixo). Coautoria/projetos cruzados por nome — sujeito a erro de homônimo. Coautores externos (fora do campus) não entram no grafo, mas aparecem no painel de cada docente.</div>
</div>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    idx = build_roster_index()
    pair_w, ext_collab, papers = collect_coauthorship(idx)
    G, id2name = build_graph(pair_w)
    m = compute(G)
    proj_pair, proj_count = collect_projects(id2name)
    # impacto Qualis por docente (relevância da produção), reusando analyze_venues
    impact_by_id = {}
    try:
        from src.scripts.analyze_venues import (
            load_qualis, load_scimago, load_qualis_conf, rank_docentes, REF_DIR)
        qx = load_qualis(REF_DIR / "qualis.csv")
        sx = load_scimago()
        ca, cn = load_qualis_conf()
        for r in rank_docentes(ROSTER_IDS, qx, sx, ca, cn):
            lid = ROSTER_IDS.get(r["nome"])
            if lid:
                impact_by_id[lid] = r
    except Exception as exc:
        print(f"AVISO: impacto Qualis indisponível ({exc}); comunidades por volume.")
    patterns = analyze_patterns(G, m, id2name, _areas(list(id2name)),
                                proj_pair, proj_count, impact_by_id)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stats = emit(G, id2name, m, ext_collab, papers, out, patterns)
    print(f"Rede: {stats}")
    print(f"Comunidades: {len(patterns['comunidades'])} · homofilia intra-área: {patterns['area']['pct_intra']}%"
          f" · pares projeto: {patterns['projetos']['n_pares_proj']}")
    print(f"Written: {out}")
    print(f"Written: {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
