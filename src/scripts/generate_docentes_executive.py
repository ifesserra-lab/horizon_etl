"""
Relatório Executivo de Docentes — IFES Campus Serra.

Indicadores de produtividade e formação de pessoas a partir dos currículos
Lattes (data/lattes_json) dos professores do campus. Centrado no DOCENTE
(diferente do executivo de formandos, centrado no aluno).

Uso:
  python -m src.scripts.generate_docentes_executive
  python -m src.scripts.generate_docentes_executive --out caminho.html
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
LATTES_DIR = BASE / "data" / "lattes_json"
OUT_DIR = BASE / "data" / "exports" / "formandos"
DEFAULT_OUT = OUT_DIR / "docentes_executivo.html"

# Professores do IFES Campus Serra: nome de exibição -> Lattes ID (16 díg).
# Match por ID (não por nome) — robusto a CVs com nome não parseado pelo scriptLattes.
ROSTER_IDS: dict[str, str] = {
    "Adelson Pereira do Nascimento": "1472669413938036",
    "Adilson Ribeiro Prado": "3085491325255749",
    "Adriana Padua Lovatte": "7017732650864488",
    "Adrianna Machado Meneguelli": "5918972460759215",
    "Adriano Márcio Sgrancio": "6083976036911793",
    "Alessandra Aguiar Vilarinho": "7835886986453798",
    "Alessandro Bermudes Gomes": "4784366298051203",
    "Alexander Jeferson Nassau Borges": "5991774940350065",
    "Amarildo Mendes Lemos": "9267167998031136",
    "Augusto Cesar Machado Ramos": "5802598567613054",
    "Bruno Cardoso Coutinho": "8843799612871667",
    "Bruno Ramos Gonzaga": "2837721944606164",
    "Cassius Zanetti Resende": "4261626566157032",
    "Celio Proliciano Maioli": "9321190078824486",
    "Cristina Klippel Dominicini": "7853087416950443",
    "Daniel Cruz Cavalieri": "9583314331960942",
    "Danilo de Paula e Silva": "9470331518728833",
    "Dirceu Soares Junior": "5471356042256233",
    "Edilson Luiz do Nascimento": "7888526444943028",
    "Elinario Santos Costa": "2048000343117704",
    "Emmanuel Marques Silva": "8050663713027392",
    "Ernani Leite Ribeiro Filho": "8533403769344054",
    "Fabiano Borges Ruy": "2532510759040199",
    "Fabio de Oliveira Lima": "1245001920023849",
    "Fidelis Zanetti de Castro": "2373180848461397",
    "Flávio Barcelos Braz da Silva": "0082588377275398",
    "Flávio Garcia Pereira": "3794041743196202",
    "Flavio Giraldeli Bianca": "2045931062434335",
    "Flávio Lopes da Silva": "9857186681773709",
    "Francisco de Assis Boldt": "0385991152092556",
    "Francisco José Casarim Rapchan": "1844100532565640",
    "Gabriel Tozatto Zago": "8771088249434104",
    "Geovane de Araújo Ceolin": "2097843909201655",
    "Geraldo Andrade de Oliveira": "1902497507486240",
    "Geraldo Simonetti Bello": "2171535044272850",
    "Gilberto Neves Sudré Filho": "7036261180355869",
    "Gilmar Luiz Vassoler": "4324881751736449",
    "Giordana dos Santos Sperandio": "6550053640492591",
    "Giovani Freire Azeredo": "0401735286340193",
    "Graziela Barboza Guaitolini Ramos": "8149991878329604",
    "Gustavo Maia de Almeida": "2650921349694794",
    "Hilário Seibel Júnior": "8155773475663050",
    "Hilário Tomaz Alves de Oliveira": "8980213630090119",
    "Jefferson Oliveira Andrade": "7138275599443632",
    "Jefferson Ribeiro de Lima": "8645994745413313",
    "João Vitor Ferreira Duque": "4157383685655204",
    "Jonathan Toczek Souza": "3258707743087263",
    "Karin Satie Komati": "9860697624155451",
    "Kelly Assis de Souza Gazolli": "0343732414150447",
    "Leandro Colombi Resendo": "8108487234297364",
    "Leonardo Aguiar do Amaral": "3747190706760201",
    "Leonardo Matiazzi Corrêa": "1879691887687737",
    "Leonardo Azevedo Scardua": "3651077981942079",
    "Luciano de Oliveira Toledo": "5592754862270484",
    "Luiz Alberto Pinto": "3550111932609658",
    "Maikon Chaider Silva Scaldaferro": "5909044646841082",
    "Marco Antonio de Souza Leite Cuadros": "8629256330944049",
    "Marcos Simão Guimarães": "1309219372857869",
    "Marcos Paulo Kohler Caldas": "6499650719150590",
    "Marta Talitha Carvalho Freire Mendes": "3770740577508464",
    "Mateus Conrad Barcellos da Costa": "9244741653857997",
    "Maxwell Eduardo Monteiro": "8831352516689445",
    "Milainy Ludmila Santos Goulart": "4538755343018125",
    "Moises Savedra Omena": "0059221043399777",
    "Nauvia Maria Cancelieri": "7515984919866826",
    "Paulo Cezar Camargo Guedes": "5710836199570315",
    "Paulo Sergio dos Santos Junior": "8400407353673370",
    "Rafael Emerick Zape de Oliveira": "8365543719828195",
    "Rafael Peixoto Derenzi Vivacqua": "9741308000396752",
    "Raquel da Silva Xavier Guizia Matos": "7815658457566599",
    "Reginaldo Corteletti": "3373905719716652",
    "Renata Gomes de Jesus": "1386809028095357",
    "Renato Tannure Rotta de Almeida": "6927212610032092",
    "Renner Sartório Camargo": "3539297708118726",
    "Ricardo Ramos Costa": "3570729284909193",
    "Richard Junior Manuel Godinez Tello": "3966230569744918",
    "Rodrigo Fernandes Calhau": "5553396597490044",
    "Rogério Passos do Amaral Pereira": "2592658166362342",
    "Ronaldo Aparecida Marques": "2269276436108008",
    "Rosiane Ribeiro Rocha": "7769380471199102",
    "Saul da Silva Munareto": "1484609457358730",
    "Sérgio Nery Simões": "0723238551725187",
    "Thiago Meireles Paixão": "2961730349897943",
    "Valeria Vieira de Lima Feu": "5251921528349204",
    "Vantuil Manoel Thebas": "4206334178739043",
    "Victorio Albani de Carvalho": "6035323365313300",
    "Vinicius Secchin de Melo": "0449903748898289",
    "Vitor Faiçal Campana": "4448287274372321",
    "Wagner Kirmse Caldas": "1629043689973681",
    "Wallas Gusmão Thomas": "7656611629494754",
    "Rosilene de Sá Ribeiro": "1985806708983534",
    "Reginaldo Barbosa Nunes": "0301147577506989",
    "Pablo Rodrigues Muniz": "4404912914498937",
}

# IDs ainda não confirmados (CV baixado é de outra pessoa) — fora dos indicadores.
ROSTER_SUSPECT: dict[str, str] = {
    "Tatiane Policário Chagas": "4370865107182288",  # baixou "Tatiane Leal Bastos"
    "Weverthon Lobo de Oliveira": "6404017817382636",  # baixou "Marcia de Oliveira Gomes"
}


# ---------------------------------------------------------------------------
# Data loading + indicators
# ---------------------------------------------------------------------------


def _stat(d: dict, key: str) -> int:
    return int((d.get("estatisticas") or {}).get(key, 0) or 0)


def _orient_by_level(d: dict, bucket: str) -> dict[str, int]:
    o = (d.get("orientacoes") or {}).get(bucket) or {}
    return {k: len(v) if isinstance(v, list) else 0 for k, v in o.items()}


def _bancas_total(d: dict) -> int:
    b = d.get("bancas") or {}
    return sum(len(v) for v in b.values() if isinstance(v, list))


def _producao_tecnica_total(d: dict) -> int:
    t = d.get("producao_tecnica") or {}
    return sum(len(v) for v in t.values() if isinstance(v, list))


def _patentes_total(d: dict) -> int:
    p = d.get("patentes_registros") or {}
    return sum(len(v) for v in p.values() if isinstance(v, list))


def load_docentes(roster: dict[str, str]) -> tuple[list[dict], list[str]]:
    """Carrega o CV de cada docente por Lattes ID. Retorna (matched, faltam)."""
    # indexa CVs por id (do filename: NN_Nome_ID.json)
    by_id: dict[str, str] = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f

    matched, faltam = [], []
    for nome, lid in roster.items():
        f = by_id.get(lid)
        if not f:
            faltam.append(nome)
            continue
        try:
            d = json.loads(Path(f).read_text())
        except Exception:
            faltam.append(nome)
            continue
        matched.append({"roster": nome, "nome": nome, "file": f, "cv": d})
    return matched, faltam


def compute(matched: list[dict]) -> dict:
    n = len(matched)
    agg = Counter()
    orient_c = Counter()
    orient_a = Counter()
    areas = Counter()
    per_doc = []
    bolsistas_pq = []

    LEVELS = [
        "doutorado",
        "mestrado",
        "especializacao",
        "tcc",
        "iniciacao_cientifica",
        "pos_doutorado",
        "outros",
    ]

    for m in matched:
        d = m["cv"]
        art = _stat(d, "total_artigos_periodicos")
        cong = _stat(d, "total_trabalhos_congressos")
        liv = _stat(d, "total_livros")
        cap = _stat(d, "total_capitulos")
        pp = _stat(d, "total_projetos_pesquisa")
        pe = _stat(d, "total_projetos_extensao")
        pd = _stat(d, "total_projetos_desenvolvimento")
        oc = _stat(d, "total_orientacoes_concluidas")
        oa = _stat(d, "total_orientacoes_andamento")
        tec = _producao_tecnica_total(d)
        pat = _patentes_total(d)
        banc = _bancas_total(d)

        agg["artigos"] += art
        agg["congressos"] += cong
        agg["livros"] += liv
        agg["capitulos"] += cap
        agg["proj_pesq"] += pp
        agg["proj_ext"] += pe
        agg["proj_dev"] += pd
        agg["orient_conc"] += oc
        agg["orient_and"] += oa
        agg["tecnica"] += tec
        agg["patentes"] += pat
        agg["bancas"] += banc

        for lvl, c in _orient_by_level(d, "concluidas").items():
            orient_c[lvl] += c
        for lvl, c in _orient_by_level(d, "em_andamento").items():
            orient_a[lvl] += c

        for a in d.get("areas_de_atuacao") or []:
            ga = (a.get("grande_area") or a.get("area") or "").strip()
            if ga:
                areas[ga] += 1

        bp = (
            (d.get("informacoes_pessoais") or {}).get("bolsa_produtividade") or ""
        ).strip()
        if bp:
            bolsistas_pq.append({"nome": m["nome"], "bolsa": bp})

        per_doc.append(
            {
                "nome": m["nome"],
                "orient_conc": oc,
                "orient_and": oa,
                "producao": art + cong + liv + cap,
                "artigos": art,
                "congressos": cong,
                "projetos": pp + pe + pd,
                "tecnica": tec,
                "patentes": pat,
            }
        )

    prod_total = agg["artigos"] + agg["congressos"] + agg["livros"] + agg["capitulos"]
    proj_total = agg["proj_pesq"] + agg["proj_ext"] + agg["proj_dev"]

    return {
        "n_docentes": n,
        "agg": dict(agg),
        "prod_total": prod_total,
        "proj_total": proj_total,
        "orient_conc_total": agg["orient_conc"],
        "orient_and_total": agg["orient_and"],
        "orient_c_by_level": {k: orient_c.get(k, 0) for k in LEVELS},
        "orient_a_by_level": {k: orient_a.get(k, 0) for k in LEVELS},
        "areas": areas.most_common(8),
        "bolsistas_pq": bolsistas_pq,
        "top_orient": sorted(per_doc, key=lambda x: -x["orient_conc"])[:10],
        "top_prod": sorted(per_doc, key=lambda x: -x["producao"])[:10],
        "top_proj": sorted(per_doc, key=lambda x: -x["projetos"])[:10],
        "media_prod": round(prod_total / n, 1) if n else 0,
        "media_orient": round(agg["orient_conc"] / n, 1) if n else 0,
    }


# ---------------------------------------------------------------------------
# Styling (idêntico ao executivo de formandos)
# ---------------------------------------------------------------------------

CSS = """
:root{
  --ink:#16241a; --ink2:#3c4f42; --muted:#71857a;
  --line:#e3ece5; --line2:#cfddd3;
  --paper:#ffffff; --bg:#f4f8f5; --soft:#eef5f0;
  --brand:#0f7a40; --brand-d:#0a5c30; --brand-l:#e7f4ec;
  --blue:#2f6fb0; --blue-l:#e8f0f8;
  --amber:#b8860b; --amber-l:#f7f0dd;
  --rose:#b5455f;
  --shadow:0 1px 2px rgba(16,40,24,.04),0 6px 20px rgba(16,40,24,.06);
  --font:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
  --serif:'Georgia','Times New Roman',serif;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
body{background:var(--bg);color:var(--ink);font-family:var(--font);
     line-height:1.55;font-size:15px;}
.page{max-width:980px;margin:0 auto;padding:0 28px 80px;}

/* hero */
.hero{padding:64px 0 44px;border-bottom:3px solid var(--brand);margin-bottom:48px;}
.kicker{display:inline-flex;align-items:center;gap:8px;font-size:12px;font-weight:600;
        letter-spacing:.14em;text-transform:uppercase;color:var(--brand);
        background:var(--brand-l);padding:6px 14px;border-radius:999px;margin-bottom:22px;}
.hero h1{font-family:var(--serif);font-size:clamp(30px,5.2vw,50px);line-height:1.08;
         font-weight:700;letter-spacing:-.01em;color:var(--ink);max-width:18ch;}
.hero .lede{font-size:19px;color:var(--ink2);margin-top:20px;max-width:62ch;}
.hero .meta{display:flex;flex-wrap:wrap;gap:10px 26px;margin-top:28px;font-size:13px;color:var(--muted);}
.hero .meta b{color:var(--ink);font-weight:600;}

/* section scaffolding */
.section{margin:56px 0;}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
         color:var(--brand);margin-bottom:10px;}
.section h2{font-family:var(--serif);font-size:27px;font-weight:700;color:var(--ink);
            letter-spacing:-.01em;margin-bottom:8px;}
.section .desc{font-size:15px;color:var(--ink2);max-width:64ch;margin-bottom:26px;}

/* KPI strip */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;}
.kpi{background:var(--paper);border:1px solid var(--line);border-radius:16px;
     padding:24px 22px;box-shadow:var(--shadow);position:relative;overflow:hidden;}
.kpi::after{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--brand);}
.kpi .n{font-size:42px;font-weight:800;letter-spacing:-.02em;color:var(--brand-d);line-height:1;}
.kpi .u{font-size:15px;font-weight:600;color:var(--ink);margin-top:8px;}
.kpi .s{font-size:13px;color:var(--muted);margin-top:4px;}

/* findings */
.findings{display:grid;grid-template-columns:1fr 1fr;gap:20px;}
.finding{background:var(--paper);border:1px solid var(--line);border-radius:16px;
         padding:26px 26px 24px;box-shadow:var(--shadow);}
.finding .tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.08em;
              text-transform:uppercase;padding:4px 10px;border-radius:6px;margin-bottom:14px;}
.tag.eq{background:var(--brand-l);color:var(--brand-d);}
.tag.sp{background:var(--amber-l);color:var(--amber);}
.tag.rs{background:var(--blue-l);color:var(--blue);}
.finding h3{font-size:18px;font-weight:700;color:var(--ink);margin-bottom:8px;line-height:1.3;}
.finding p{font-size:14.5px;color:var(--ink2);}
.finding .big{display:flex;align-items:baseline;gap:10px;margin:4px 0 14px;}
.finding .big .v{font-size:34px;font-weight:800;color:var(--brand-d);letter-spacing:-.02em;}
.finding .big .vs{font-size:15px;color:var(--muted);}

/* bars */
.card{background:var(--paper);border:1px solid var(--line);border-radius:16px;
      padding:26px 28px;box-shadow:var(--shadow);}
.card h3{font-size:16px;font-weight:700;margin-bottom:18px;color:var(--ink);}
.brow{display:grid;grid-template-columns:160px 1fr 118px;align-items:center;gap:14px;margin-bottom:15px;}
.brow .bl{font-size:13.5px;color:var(--ink);font-weight:500;line-height:1.25;}
.btrack{height:18px;background:var(--soft);border-radius:9px;overflow:hidden;position:relative;}
.bfill{height:100%;border-radius:9px;min-width:6px;}
.brow .bv{font-size:13.5px;color:var(--ink);font-weight:700;text-align:right;white-space:nowrap;}
.brow .bv .bv-sub{color:var(--muted);font-weight:500;}
/* stacked bars (concluídas + em andamento) */
.btrack.stack{display:flex;}
.btrack.stack .seg{height:100%;min-width:3px;transition:none;}
.card-head{display:flex;align-items:center;justify-content:space-between;
           gap:16px;margin-bottom:18px;flex-wrap:wrap;}
.card-head h3{margin-bottom:0;}
.legend{display:flex;gap:18px;font-size:12.5px;color:var(--ink2);}
.legend span{display:inline-flex;align-items:center;gap:7px;}
.legend i{width:12px;height:12px;border-radius:3px;display:inline-block;}

.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px;}

/* comparison stat row */
.cmp{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}
.cmp .c{background:var(--paper);border:1px solid var(--line);border-radius:14px;
        padding:22px 20px;text-align:center;box-shadow:var(--shadow);border-top:4px solid var(--line2);}
.cmp .c.win{border-top-color:var(--brand);background:linear-gradient(180deg,var(--brand-l),#fff 60%);}
.cmp .c .lab{font-size:13px;font-weight:700;color:var(--ink);margin-bottom:10px;}
.cmp .c .v{font-size:38px;font-weight:800;letter-spacing:-.02em;line-height:1;}
.cmp .c .v.g{color:var(--brand-d);} .cmp .c .v.b{color:var(--blue);} .cmp .c .v.a{color:var(--amber);}
.cmp .c .sub{font-size:12.5px;color:var(--muted);margin-top:7px;}

/* callout */
.callout{background:linear-gradient(135deg,var(--brand-d),var(--brand));color:#fff;
         border-radius:18px;padding:38px 40px;box-shadow:var(--shadow);}
.callout .k{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
            opacity:.85;margin-bottom:14px;}
.callout h2{font-family:var(--serif);font-size:28px;color:#fff;margin-bottom:14px;line-height:1.2;}
.callout p{font-size:16px;opacity:.95;max-width:70ch;}
.callout .row{display:flex;flex-wrap:wrap;gap:34px;margin-top:26px;}
.callout .row .it .n{font-size:34px;font-weight:800;}
.callout .row .it .l{font-size:13px;opacity:.9;}

/* table */
table{width:100%;border-collapse:collapse;font-size:14px;}
th,td{padding:11px 14px;text-align:right;border-bottom:1px solid var(--line);}
th:first-child,td:first-child{text-align:left;}
thead th{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:700;}
tbody tr:last-child td{border-bottom:none;}
.tot td{font-weight:700;background:var(--soft);}

/* recommendations */
.recs{display:grid;grid-template-columns:1fr 1fr;gap:18px;}
.rec{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:22px 24px;
     box-shadow:var(--shadow);display:flex;gap:16px;}
.rec .num{flex-shrink:0;width:34px;height:34px;border-radius:10px;background:var(--brand-l);
          color:var(--brand-d);font-weight:800;display:flex;align-items:center;justify-content:center;font-size:16px;}
.rec h4{font-size:15.5px;font-weight:700;margin-bottom:5px;color:var(--ink);}
.rec p{font-size:13.5px;color:var(--ink2);}

.foot{margin-top:64px;padding-top:24px;border-top:1px solid var(--line);
      font-size:12.5px;color:var(--muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;}
.note-line{font-size:12.5px;color:var(--muted);margin-top:14px;font-style:italic;}

@media (max-width:760px){
  .kpis,.findings,.grid2,.cmp,.recs{grid-template-columns:1fr;}
  .brow{grid-template-columns:110px 1fr 70px;}
}
@media print{
  body{background:#fff;font-size:12px;}
  .page{max-width:none;padding:0 8mm;}
  .section{margin:26px 0;page-break-inside:avoid;}
  .kpi,.finding,.card,.cmp .c,.callout,.rec{box-shadow:none;}
  .hero{padding:14px 0 24px;}
  .callout{background:var(--brand-d) !important;}
}
"""


def _pct(part, whole):
    return round(part / whole * 100, 1) if whole else 0.0


def bar(label, value, max_val, color, suffix="", note=None):
    w = (value / max_val * 100) if max_val else 0
    val_txt = note if note is not None else f"{value}{suffix}"
    return (
        f'<div class="brow"><span class="bl">{label}</span>'
        f'<div class="btrack"><div class="bfill" '
        f'style="width:{max(w, 1.5):.1f}%;background:{color};"></div></div>'
        f'<span class="bv">{val_txt}</span></div>'
    )


def stacked_bar(label, concl, andamento, max_total):
    """Barra empilhada: concluídas (verde) + em andamento (âmbar) no mesmo trilho.

    Largura proporcional ao TOTAL relativo ao maior total da série.
    """
    tot = concl + andamento
    wc = (concl / max_total * 100) if max_total else 0
    wa = (andamento / max_total * 100) if max_total else 0
    seg_c = (
        (
            f'<div class="seg" style="width:{wc:.1f}%;background:var(--brand);" '
            f'title="{concl} concluídas"></div>'
        )
        if concl
        else ""
    )
    seg_a = (
        (
            f'<div class="seg" style="width:{wa:.1f}%;background:var(--amber);" '
            f'title="{andamento} em andamento"></div>'
        )
        if andamento
        else ""
    )
    return (
        f'<div class="brow"><span class="bl">{label}</span>'
        f'<div class="btrack stack">{seg_c}{seg_a}</div>'
        f'<span class="bv">{concl}'
        f'<span class="bv-sub"> · {andamento} em and.</span></span></div>'
    )


_LVL_LABEL = {
    "doutorado": "Doutorado",
    "mestrado": "Mestrado",
    "especializacao": "Especialização",
    "tcc": "TCC / Graduação",
    "iniciacao_cientifica": "Iniciação científica",
    "pos_doutorado": "Pós-doutorado",
    "outros": "Outros",
}


def build(s: dict, generated_at: str, faltam: list) -> str:
    n = s["n_docentes"]
    agg = s["agg"]
    # KPI strip
    kpis = f"""
    <section class="section">
      <div class="kpis">
        <div class="kpi"><div class="n">{n}</div>
          <div class="u">docentes analisados</div><div class="s">currículos Lattes do Campus Serra</div></div>
        <div class="kpi"><div class="n">{s['orient_conc_total']}</div>
          <div class="u">orientações concluídas</div><div class="s">+{s['orient_and_total']} em andamento</div></div>
        <div class="kpi"><div class="n">{s['prod_total']}</div>
          <div class="u">produções bibliográficas</div><div class="s">artigos, congressos, livros, capítulos</div></div>
        <div class="kpi"><div class="n">{s['proj_total']}</div>
          <div class="u">projetos</div><div class="s">pesquisa, extensão e desenvolvimento</div></div>
      </div>
    </section>"""

    # Formação de pessoas (orientações por nível)
    oc = s["orient_c_by_level"]
    oa = s["orient_a_by_level"]
    levels = [k for k in oc if oc[k] or oa[k]]
    maxtot = max([oc[k] + oa[k] for k in levels] + [1])
    tot_c = s["orient_conc_total"]
    tot_a = s["orient_and_total"]
    orient_bars = "".join(
        stacked_bar(_LVL_LABEL.get(k, k), oc[k], oa[k], maxtot)
        for k in sorted(levels, key=lambda k: -(oc[k] + oa[k]))
    )
    legend = (
        '<div class="legend">'
        '<span><i style="background:var(--brand)"></i>Concluídas</span>'
        '<span><i style="background:var(--amber)"></i>Em andamento (pipeline)</span>'
        "</div>"
    )
    sec_orient = f"""
    <section class="section">
      <div class="eyebrow">Formação de pessoas</div>
      <h2>Capacidade de formar pesquisadores</h2>
      <p class="desc">Orientações por nível acadêmico — <b>concluídas</b> (entregue) e
      <b>em andamento</b> (pipeline em formação). Média de <b>{s['media_orient']}</b>
      orientações concluídas por docente; <b>{tot_a}</b> orientandos ainda em curso.</p>
      <div class="card">
        <div class="card-head"><h3>Orientações por nível</h3>{legend}</div>
        {orient_bars}
      </div>
    </section>"""

    # Produção científica
    maxp = max(agg.get("congressos", 0), agg.get("artigos", 0), 1)
    prod_bars = (
        bar("Trabalhos em congressos", agg.get("congressos", 0), maxp, "var(--blue)")
        + bar("Artigos em periódicos", agg.get("artigos", 0), maxp, "var(--brand)")
        + bar("Capítulos de livro", agg.get("capitulos", 0), maxp, "var(--amber)")
        + bar("Livros publicados", agg.get("livros", 0), maxp, "var(--rose)")
    )
    sec_prod = f"""
    <section class="section">
      <div class="eyebrow">Produção científica</div>
      <h2>Produção bibliográfica do corpo docente</h2>
      <p class="desc">Volume agregado de produção registrada no Lattes — média de
      <b>{s['media_prod']}</b> produções por docente.</p>
      <div class="card"><h3>Por tipo de produção</h3>{prod_bars}</div>
    </section>"""

    # Projetos
    pj = [
        ("Pesquisa", agg.get("proj_pesq", 0), "g"),
        ("Extensão", agg.get("proj_ext", 0), "b"),
        ("Desenvolvimento", agg.get("proj_dev", 0), "a"),
    ]
    cmp_proj = "".join(
        f'<div class="c"><div class="lab">{lab}</div>'
        f'<div class="v {cls}">{val}</div><div class="sub">projetos</div></div>'
        for lab, val, cls in pj
    )
    sec_proj = f"""
    <section class="section">
      <div class="eyebrow">Projetos</div>
      <h2>Projetos de pesquisa, extensão e desenvolvimento</h2>
      <p class="desc">Distribuição dos {s['proj_total']} projetos registrados pelos docentes.</p>
      <div class="cmp">{cmp_proj}</div>
    </section>"""

    # Áreas de conhecimento
    maxa = s["areas"][0][1] if s["areas"] else 1
    area_bars = "".join(
        bar(a, c, maxa, "var(--brand)", note=f"{c} docentes") for a, c in s["areas"]
    )
    sec_areas = f"""
    <section class="section">
      <div class="eyebrow">Áreas de conhecimento</div>
      <h2>Onde está concentrada a competência do campus</h2>
      <p class="desc">Grandes áreas de atuação declaradas pelos docentes (um docente pode atuar em mais de uma).</p>
      <div class="card"><h3>Docentes por grande área</h3>{area_bars}</div>
    </section>"""

    # Top docentes (tabela)
    def _rows(items, key, suf=""):
        return "".join(
            f'<tr><td>{d["nome"]}</td><td>{d["orient_conc"]}</td>'
            f'<td>{d["producao"]}</td><td>{d["projetos"]}</td></tr>'
            for d in items
        )

    top_table = f"""
    <section class="section">
      <div class="eyebrow">Destaques</div>
      <h2>Docentes com maior volume</h2>
      <p class="desc">Top 10 por orientações concluídas. Produção e projetos exibidos para contexto —
      não é ranking de mérito (perfis e tempos de carreira diferem).</p>
      <table>
        <thead><tr><th>Docente</th><th>Orient. concl.</th><th>Produção</th><th>Projetos</th></tr></thead>
        <tbody>{_rows(s['top_orient'], 'orient_conc')}</tbody>
      </table>
      <p class="note-line">Ordenado por orientações concluídas.</p>
    </section>"""

    # Inovação + bolsistas produtividade
    n_bp = len(s["bolsistas_pq"])
    bp_list = (
        "".join(
            f"<li>{b['nome']} — <span style='color:var(--muted)'>{b['bolsa']}</span></li>"
            for b in s["bolsistas_pq"]
        )
        or "<li>Nenhum bolsista de produtividade identificado.</li>"
    )
    sec_inov = f"""
    <section class="section">
      <div class="eyebrow">Inovação e reconhecimento</div>
      <h2>Produção técnica e bolsas de produtividade</h2>
      <div class="findings">
        <div class="finding"><span class="tag rs">Inovação</span>
          <h3>Produção técnica e propriedade intelectual</h3>
          <div class="big"><span class="v">{agg.get('tecnica',0)}</span><span class="vs">produções técnicas (software, produtos, processos)</span></div>
          <p>{agg.get('patentes',0)} registros de patentes / programas de computador / desenhos industriais.</p>
        </div>
        <div class="finding"><span class="tag eq">Reconhecimento</span>
          <h3>Bolsistas de produtividade</h3>
          <div class="big"><span class="v">{n_bp}</span><span class="vs">docentes com bolsa PQ (CNPq/FAPES)</span></div>
          <ul style="font-size:13.5px;color:var(--ink2);margin-left:18px;">{bp_list}</ul>
        </div>
      </div>
    </section>"""

    # Callout
    callout = f"""
    <section class="section">
      <div class="callout">
        <div class="k">Síntese</div>
        <h2>{n} docentes que sustentam a pesquisa do Campus Serra</h2>
        <p>O corpo docente analisado concluiu <b>{s['orient_conc_total']}</b> orientações,
        registrou <b>{s['prod_total']}</b> produções bibliográficas e conduz <b>{s['proj_total']}</b>
        projetos. Esses números são a base de capacidade para a graduação, o mestrado PPComp e a
        captação de fomento.</p>
        <div class="row">
          <div class="it"><div class="n">{s['media_orient']}</div><div class="l">orientações concl. / docente</div></div>
          <div class="it"><div class="n">{s['media_prod']}</div><div class="l">produções / docente</div></div>
          <div class="it"><div class="n">{s['orient_and_total']}</div><div class="l">orientações em andamento</div></div>
          <div class="it"><div class="n">{n_bp}</div><div class="l">bolsistas produtividade</div></div>
        </div>
      </div>
    </section>"""

    falta_note = f' · {len(faltam)} sem CV: {", ".join(faltam)}' if faltam else ""
    if ROSTER_SUSPECT:
        falta_note += (
            f" · {len(ROSTER_SUSPECT)} com Lattes ID a confirmar "
            f'(fora dos indicadores): {", ".join(ROSTER_SUSPECT)}'
        )

    return (
        f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Executivo de Docentes — IFES Campus Serra</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{{CSS}}</style></head>
<body><div class="page">
  <div class="hero">
    <span class="kicker">IFES Campus Serra · Relatório Executivo</span>
    <h1>O corpo docente em números</h1>
    <p class="lede">Indicadores de formação de pessoas, produção científica e projetos
    a partir dos currículos Lattes dos professores do campus.</p>
    <div class="meta"><span><b>{n}</b> docentes</span>
      <span><b>{s['orient_conc_total']}</b> orientações concluídas</span>
      <span><b>{s['prod_total']}</b> produções</span>
      <span>Fonte: Plataforma Lattes</span></div>
  </div>
  {{KPIS}}{{ORIENT}}{{PROD}}{{PROJ}}{{AREAS}}{{TOP}}{{INOV}}{{CALLOUT}}
  <div class="foot"><span>Gerado em {generated_at} · fonte: currículos Lattes (data/lattes_json)</span>
  <span>{n} docentes{falta_note}</span></div>
</div></body></html>""".replace(
            "{CSS}", CSS
        )
        .replace("{KPIS}", kpis)
        .replace("{ORIENT}", sec_orient)
        .replace("{PROD}", sec_prod)
        .replace("{PROJ}", sec_proj)
        .replace("{AREAS}", sec_areas)
        .replace("{TOP}", top_table)
        .replace("{INOV}", sec_inov)
        .replace("{CALLOUT}", callout)
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    print(
        f"Roster: {len(ROSTER_IDS)} docentes (+{len(ROSTER_SUSPECT)} com ID a confirmar)"
    )
    matched, faltam = load_docentes(ROSTER_IDS)
    print(f"  casados com CV: {len(matched)}")
    if faltam:
        print(f"  SEM CV: {faltam}")
    print(f"  ID a confirmar (fora dos indicadores): {list(ROSTER_SUSPECT)}")

    s = compute(matched)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = build(s, now, faltam)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
