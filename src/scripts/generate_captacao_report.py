#!/usr/bin/env python3
"""Evolução e volume da captação de projetos — IFES Campus Serra (FAPES + FACTO).

Mostra a EVOLUÇÃO temporal (volume de projetos e captação por ano) e o VOLUME por
fonte/coordenador, a partir de:
  - FAPES: data/exports/projetos-fapes/...json  (orçamento contratado; campo numérico)
  - FACTO: data/exports/projetos-facto/facto_projects_full.json (valor aprovado; string BR)

REGRA DE CAPTAÇÃO DO CAMPUS: FAPES = todos os 99 projetos do campus. FACTO entra no
"captado pelo campus" só quando o COORDENADOR é docente do roster (equipe não soma); a
participação (coord OU equipe) é reportada à parte, como contexto.

SEGURANÇA: não expõe cifras exatas — totais em ORDEM de grandeza; por coordenador/
financiadora em FAIXA + %; captação por ano como ÍNDICE (base 100 no ano de pico).

Saída: data/exports/docentes/captacao_projetos.html
Uso:   python -m src.scripts.generate_captacao_report
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.scripts.generate_docentes_executive import ROSTER_IDS  # noqa: E402
from src.scripts.didatica import bloco_metrica  # noqa: E402

FAPES = ROOT / "data" / "exports" / "projetos-fapes" / "ifes-campus-serra-projetos-concluidos-em-andamento.json"
FACTO = ROOT / "data" / "exports" / "projetos-facto" / "facto_projects_full.json"
BOLSAS = ROOT / "data" / "exports" / "bolsistas" / "ifes-campus-serra-bolsistas.json"
OUT = ROOT / "data" / "exports" / "docentes" / "captacao_projetos.html"

FACTO_TIPOS_PESQUISA = {"Pesquisa, Desenvolvimento e Inovação", "Pesquisa", "Inovação",
                        "Pesquisa e Extensão", "Pesquisa e Ensino", "Pesquisa, Ensino e Extensão"}


def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().split())


def _num(v) -> float:          # FAPES: campo numérico (float)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _br(v) -> float:           # FACTO: número no formato BR ("1.256.355,65")
    v = str(v or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return 0.0


_FAIXAS = [(1e5, "≤ R$ 100 mil"), (5e5, "R$ 100–500 mil"), (1e6, "R$ 500 mil–1 mi"),
           (5e6, "R$ 1–5 mi"), (2e7, "R$ 5–20 mi"), (5e7, "R$ 20–50 mi")]


def faixa(v) -> str:
    v = _num(v)
    if v <= 0:
        return "sem valor"
    for lim, rot in _FAIXAS:
        if v <= lim:
            return rot
    return "> R$ 50 mi"


def pct(v, total):
    return round(_num(v) / total * 100, 1) if total else 0.0


def ordem(v) -> str:
    v = _num(v)
    if v <= 0:
        return "—"
    mi = v / 1e6
    if mi < 1:
        return "menos de R$ 1 mi"
    e = 10 ** (len(str(int(mi))) - 1)
    r = int(round(mi / e) * e)
    q = "centenas de milhões" if mi >= 100 else ("dezenas de milhões" if mi >= 10 else "milhões")
    return f"~R$ {r} mi ({q})"


# ---------------------------------------------------------------------------
def carregar() -> dict:
    roster = {norm(n) for n in ROSTER_IDS}
    # --- FAPES ---
    dj = json.loads(FAPES.read_text(encoding="utf-8"))["projetos"]
    fap_ano = defaultdict(lambda: {"n": 0, "v": 0.0})
    fap_coord = defaultdict(lambda: {"n": 0, "v": 0.0})
    fap_rub = defaultdict(float)
    seen = set()
    fap_n = 0
    fap_v = 0.0
    for g in dj:
        for x in dj[g]:
            pid = x["projeto_id"]
            if pid in seen:
                continue
            seen.add(pid)
            v = _num(x.get("orcamento_contratado"))
            fap_n += 1
            fap_v += v
            a = x.get("ano")
            if a:
                fap_ano[int(a)]["n"] += 1
                fap_ano[int(a)]["v"] += v
            c = norm(x.get("coordenador_nome"))
            if c:
                fap_coord[c]["n"] += 1
                fap_coord[c]["v"] += v
            for rb in (x.get("rubricas") or []):
                nm = (rb.get("rubrica") or rb.get("descricao_categoria") or "—").strip()
                fap_rub[nm] += _num(rb.get("valor"))
    # --- BOLSAS (SigPesq) por ano de início ---
    bol_ano = defaultdict(int)
    bol_total = 0
    bol_tipo = Counter()
    if BOLSAS.exists():
        b = json.loads(BOLSAS.read_text(encoding="utf-8")).get("alocacoes", [])
        bol_total = len(b)
        for a in b:
            y = (a.get("formulario_bolsa_inicio") or "")[:4]
            if y.isdigit():
                bol_ano[int(y)] += 1
            bol_tipo[(a.get("bolsa_sigla") or "—")] += 1
    # --- FACTO ---
    P = json.loads(FACTO.read_text(encoding="utf-8")).get("projects", [])

    def equipe_roster(csv):
        eq = next((v for k, v in csv.items() if "Equipe" in k), None)
        if isinstance(eq, list):
            for membro in eq:
                if isinstance(membro, dict):
                    for val in membro.values():
                        if norm(val) in roster:
                            return True
        return False

    fct_ano = defaultdict(lambda: {"n": 0, "v": 0.0})
    fct_fin = defaultdict(lambda: {"n": 0, "v": 0.0})
    fct_coord = defaultdict(lambda: {"n": 0, "v": 0.0})
    fct_tipo = Counter()
    fct_coord_n = 0
    fct_coord_v = 0.0
    fct_part_n = 0
    for p in P:
        csv = p.get("csv") or {}
        info = next((v for k, v in csv.items() if "Informa" in k), None)
        if not (isinstance(info, list) and info):
            continue
        r = info[0]
        v = _br(r.get("Valor aprovado"))
        is_coord = norm(r.get("Coordenador")) in roster
        if is_coord or equipe_roster(csv):
            fct_part_n += 1
        if not is_coord:
            continue
        fct_coord_n += 1
        fct_coord_v += v
        _cn = (r.get("Coordenador") or "—").strip().title()
        fct_coord[_cn]["n"] += 1
        fct_coord[_cn]["v"] += v
        fct_tipo[r.get("Tipo de Projeto") or "—"] += 1
        fin = (r.get("Financiadora") or "—").strip()[:40]
        fct_fin[fin]["n"] += 1
        fct_fin[fin]["v"] += v
        m = re.search(r"(\d{4})", (r.get("Data de início") or "")[-4:])
        if m:
            a = int(m.group(1))
            fct_ano[a]["n"] += 1
            fct_ano[a]["v"] += v
    return {
        "roster": roster,
        "fap_n": fap_n, "fap_v": fap_v, "fap_ano": dict(fap_ano), "fap_coord": dict(fap_coord),
        "fap_rub": dict(fap_rub),
        "bol_ano": dict(bol_ano), "bol_total": bol_total, "bol_tipo": dict(bol_tipo),
        "fct_coord_n": fct_coord_n, "fct_coord_v": fct_coord_v, "fct_part_n": fct_part_n,
        "fct_ano": dict(fct_ano), "fct_fin": dict(fct_fin), "fct_tipo": dict(fct_tipo),
        "fct_coord": dict(fct_coord),
    }


# ---------------------------------------------------------------------------
def _bars_vol(anos, fap, fct):
    """Barras verticais empilhadas: projetos/ano (FAPES + FACTO), eixo = contagem."""
    W, H, P = 760, 300, 36
    mx = max([fap.get(a, {}).get("n", 0) + fct.get(a, {}).get("n", 0) for a in anos] + [1])
    bw = (W - 2 * P) / len(anos) * 0.62
    gap = (W - 2 * P) / len(anos)
    bars = ""
    for i, a in enumerate(anos):
        x = P + i * gap + (gap - bw) / 2
        nf = fap.get(a, {}).get("n", 0)
        nc = fct.get(a, {}).get("n", 0)
        hf = (nf / mx) * (H - 2 * P)
        hc = (nc / mx) * (H - 2 * P)
        yf = H - P - hf
        yc = yf - hc
        bars += f'<rect x="{x:.1f}" y="{yf:.1f}" width="{bw:.1f}" height="{hf:.1f}" fill="#0f7a40"/>'
        if nc:
            bars += f'<rect x="{x:.1f}" y="{yc:.1f}" width="{bw:.1f}" height="{hc:.1f}" fill="#2f6fb0"/>'
        tot = nf + nc
        if tot:
            bars += (f'<text x="{x + bw/2:.1f}" y="{yc - 4:.1f}" text-anchor="middle" '
                     f'font-size="11" font-weight="700" fill="#16241a">{tot}</text>')
        bars += (f'<text x="{x + bw/2:.1f}" y="{H - P + 16:.1f}" text-anchor="middle" '
                 f'font-size="10.5" fill="#71857a">{a}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">'
            f'<line x1="{P}" y1="{H-P}" x2="{W-P}" y2="{H-P}" stroke="#cfddd3"/>{bars}</svg>')


def _line_vol(anos, fap, fct):
    """Gráfico de LINHA: volume de projetos/ano (eixo Y) × ano (eixo X).
    Duas séries: FAPES (verde) e FACTO-campus (azul)."""
    W, H, P = 760, 300, 40
    mx = max([fap.get(a, {}).get("n", 0) for a in anos]
             + [fct.get(a, {}).get("n", 0) for a in anos] + [1])
    n = len(anos)

    def X(i):
        return P + i * (W - 2 * P) / (n - 1)

    def Y(v):
        return H - P - (v / mx) * (H - 2 * P)

    # grades horizontais + rótulos do eixo Y
    grid = ""
    steps = 4
    for s in range(steps + 1):
        v = mx * s / steps
        y = Y(v)
        grid += (f'<line x1="{P}" y1="{y:.1f}" x2="{W-P}" y2="{y:.1f}" stroke="#eef5f0"/>'
                 f'<text x="{P-8:.0f}" y="{y+4:.0f}" text-anchor="end" font-size="10" '
                 f'fill="#71857a">{round(v)}</text>')

    def serie(get, color, dots=True):
        pts = " ".join(f"{X(i):.1f},{Y(get(a)):.1f}" for i, a in enumerate(anos))
        out = f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>'
        if dots:
            for i, a in enumerate(anos):
                v = get(a)
                out += f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.2" fill="{color}"/>'
                if color == "#0f7a40" and v:
                    out += (f'<text x="{X(i):.1f}" y="{Y(v)-8:.1f}" text-anchor="middle" '
                            f'font-size="10.5" font-weight="700" fill="#0a5c30">{v}</text>')
        return out

    fap_line = serie(lambda a: fap.get(a, {}).get("n", 0), "#0f7a40")
    fct_line = serie(lambda a: fct.get(a, {}).get("n", 0), "#2f6fb0", dots=True)
    xlabels = "".join(f'<text x="{X(i):.1f}" y="{H-P+18:.0f}" text-anchor="middle" '
                      f'font-size="10.5" fill="#71857a">{a}</text>' for i, a in enumerate(anos))
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">{grid}'
            f'<line x1="{P}" y1="{H-P}" x2="{W-P}" y2="{H-P}" stroke="#cfddd3"/>'
            f'<line x1="{P}" y1="{P}" x2="{P}" y2="{H-P}" stroke="#cfddd3"/>'
            f'{fct_line}{fap_line}{xlabels}'
            f'<text x="14" y="{H/2:.0f}" transform="rotate(-90 14 {H/2:.0f})" text-anchor="middle" '
            f'font-size="11" fill="#71857a">projetos / ano</text></svg>')


def _line1(anos, get, color, ylabel):
    """Linha de série única: valor (Y) × ano (X), com grade, pontos e rótulos."""
    W, H, P = 760, 300, 44
    mx = max([get(a) for a in anos] + [1])
    n = len(anos)

    def X(i):
        return P + i * (W - 2 * P) / (n - 1)

    def Y(v):
        return H - P - (v / mx) * (H - 2 * P)

    grid = ""
    for s in range(5):
        v = mx * s / 4
        y = Y(v)
        grid += (f'<line x1="{P}" y1="{y:.1f}" x2="{W-P}" y2="{y:.1f}" stroke="#eef5f0"/>'
                 f'<text x="{P-8:.0f}" y="{y+4:.0f}" text-anchor="end" font-size="10" fill="#71857a">{round(v)}</text>')
    pts = " ".join(f"{X(i):.1f},{Y(get(a)):.1f}" for i, a in enumerate(anos))
    dots = ""
    for i, a in enumerate(anos):
        v = get(a)
        dots += f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.2" fill="{color}"/>'
        if v:
            dots += (f'<text x="{X(i):.1f}" y="{Y(v)-8:.1f}" text-anchor="middle" font-size="10.5" '
                     f'font-weight="700" fill="{color}">{v}</text>')
    xlabels = "".join(f'<text x="{X(i):.1f}" y="{H-P+18:.0f}" text-anchor="middle" font-size="10.5" '
                      f'fill="#71857a">{a}</text>' for i, a in enumerate(anos))
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">{grid}'
            f'<line x1="{P}" y1="{H-P}" x2="{W-P}" y2="{H-P}" stroke="#cfddd3"/>'
            f'<line x1="{P}" y1="{P}" x2="{P}" y2="{H-P}" stroke="#cfddd3"/>'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>{dots}{xlabels}'
            f'<text x="14" y="{H/2:.0f}" transform="rotate(-90 14 {H/2:.0f})" text-anchor="middle" '
            f'font-size="11" fill="#71857a">{ylabel}</text></svg>')


def _bars_idx(anos, serie):
    """Barras de ÍNDICE (base 100 no ano de pico) — evolução da captação sem expor R$."""
    W, H, P = 760, 260, 36
    mx = max([serie.get(a, {}).get("v", 0.0) for a in anos] + [1e-9])
    bw = (W - 2 * P) / len(anos) * 0.62
    gap = (W - 2 * P) / len(anos)
    bars = ""
    for i, a in enumerate(anos):
        x = P + i * gap + (gap - bw) / 2
        v = serie.get(a, {}).get("v", 0.0)
        idx = round(v / mx * 100)
        h = (idx / 100) * (H - 2 * P)
        y = H - P - h
        bars += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="#b8860b"/>'
        if idx:
            bars += (f'<text x="{x + bw/2:.1f}" y="{y - 4:.1f}" text-anchor="middle" font-size="10.5" '
                     f'font-weight="700" fill="#5e4a12">{idx}</text>')
        bars += (f'<text x="{x + bw/2:.1f}" y="{H - P + 16:.1f}" text-anchor="middle" '
                 f'font-size="10.5" fill="#71857a">{a}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">'
            f'<line x1="{P}" y1="{H-P}" x2="{W-P}" y2="{H-P}" stroke="#cfddd3"/>{bars}</svg>')


def _hbars(rows, total):
    """Barras horizontais por coordenador/financiadora: faixa + % (sem R$ exato)."""
    if not rows:
        return '<p class="muted">Sem dados.</p>'
    mx = max(r[1] for r in rows) or 1
    out = ""
    for nome, v, n in rows:
        w = max(v / mx * 100, 2)
        out += (f'<div class="bar"><span class="bl">{nome}</span>'
                f'<span class="bt"><span class="bf" style="width:{w:.0f}%"></span></span>'
                f'<span class="bv">{faixa(v)} · {pct(v, total):.0f}% · {n} proj</span></div>')
    return out


# ---------------------------------------------------------------------------
EXPL = bloco_metrica({
    "titulo": "Captação de projetos (FAPES + FACTO)",
    "o_que": "A <b>evolução</b> (volume de projetos e captação por ano) e o <b>volume</b> da "
             "captação dos professores do campus na <b>FAPES</b> (fomento estadual) e na "
             "<b>FACTO</b> (fundação de apoio).",
    "como_ler": "<b>Volume</b> = nº de projetos por ano (barras). <b>Captação</b> = mostrada como "
                "<b>índice</b> (100 = ano de maior captação) para revelar a <b>tendência</b> sem "
                "expor cifras. Por coordenador/financiadora: <b>faixa + %</b> do total.",
    "nao_concluir": [
        "FAPES e FACTO são <b>fontes distintas</b> — não somar como se fossem o mesmo fluxo.",
        "FACTO entra no captado do campus só quando o <b>coordenador é docente</b> do campus "
        "(equipe não soma); a maioria dos projetos FACTO é de <b>outros campi</b>.",
        "Captação não é execução: valores são <b>aprovado/contratado</b>, não necessariamente gasto.",
        "Um ano de pico costuma refletir <b>1–2 projetos grandes</b>, não um salto geral.",
    ],
    "gestores": "Acompanhar a <b>tendência de volume</b> (capilaridade) e a <b>concentração</b> da "
                "captação; diversificar fontes e apoiar novos coordenadores a captar.",
})

CSS = """
:root{--ink:#16241a;--ink2:#3c4f42;--muted:#71857a;--line:#e3ece5;--line2:#cfddd3;--bg:#f4f8f5;
--paper:#fff;--brand:#0f7a40;--brand-d:#0a5c30;--brand-l:#e7f4ec;--blue:#2f6fb0;--amber:#b8860b;
--font:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;--serif:'Georgia',serif;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--ink);font-family:var(--font);line-height:1.6;font-size:15px;}
.page{max-width:980px;margin:0 auto;padding:0 22px 90px;}
.hero{padding:46px 0 24px;border-bottom:3px solid var(--brand);margin-bottom:10px;}
.kick{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--brand);background:var(--brand-l);padding:5px 12px;border-radius:999px;}
h1{font-family:var(--serif);font-size:clamp(25px,4vw,38px);line-height:1.12;margin:14px 0 8px;}
.lede{color:var(--ink2);font-size:17px;max-width:75ch;}
.meta{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:16px;font-size:13px;color:var(--muted);}
.meta b{color:var(--ink);}
.section{margin:38px 0;}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--brand);margin-bottom:6px;}
h2{font-family:var(--serif);font-size:23px;margin-bottom:8px;color:var(--brand-d);}
.desc{color:var(--muted);font-size:14px;max-width:78ch;margin-bottom:16px;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;}
.kpi{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 1px 3px rgba(16,40,24,.05);border-left:4px solid var(--brand);}
.kpi.b2{border-left-color:var(--blue);}.kpi.b3{border-left-color:var(--amber);}
.kpi .n{font-size:26px;font-weight:800;color:var(--brand-d);line-height:1.1;}
.kpi.b2 .n{color:var(--blue);}.kpi.b3 .n{color:var(--amber);}
.kpi .u{font-size:13px;font-weight:600;margin-top:5px;}.kpi .s{font-size:12px;color:var(--muted);margin-top:2px;}
.card{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 1px 3px rgba(16,40,24,.05);}
.legend{display:flex;gap:16px;font-size:12.5px;color:var(--muted);margin-top:10px;}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:middle;margin-right:5px;}
.note{background:#fbf4df;border:1px solid #ecdfb8;border-left:4px solid var(--amber);border-radius:8px;padding:11px 14px;font-size:12.5px;color:#5e4a12;margin-top:14px;}
.bar{display:grid;grid-template-columns:230px 1fr 220px;align-items:center;gap:10px;margin:7px 0;font-size:13px;}
.bar .bl{overflow-wrap:break-word;line-height:1.2;}
.bar .bt{background:var(--bg);border-radius:6px;height:16px;overflow:hidden;}
.bar .bf{display:block;height:100%;background:var(--brand);border-radius:6px;}
.bar .bv{text-align:right;color:var(--ink2);font-variant-numeric:tabular-nums;}
.muted{color:var(--muted);}
table{width:100%;border-collapse:collapse;font-size:13.5px;}
th{background:var(--brand-l);text-align:left;padding:8px 11px;font-size:12px;text-transform:uppercase;color:var(--brand-d);}
td{padding:7px 11px;border-bottom:1px solid var(--line);}
.foot{margin-top:46px;padding-top:18px;border-top:1px solid var(--line2);font-size:12px;color:var(--muted);}
@media(max-width:620px){.bar{grid-template-columns:1fr;}.bar .bv{text-align:left;}}
"""


def render(d: dict) -> str:
    anos = list(range(2015, 2027))
    fap_ano, fct_ano = d["fap_ano"], d["fct_ano"]
    total_capt = d["fap_v"] + d["fct_coord_v"]
    pico = max(fap_ano.items(), key=lambda kv: kv[1]["v"])[0] if fap_ano else "—"
    n_coord = len({c for c in d["fap_coord"]})
    top_coord = sorted(d["fap_coord"].items(), key=lambda kv: -kv[1]["v"])[:8]
    top_coord_rows = [(c.title(), v["v"], v["n"]) for c, v in top_coord]
    fct_coord_rows = [(c, v["v"], v["n"]) for c, v in
                      sorted(d["fct_coord"].items(), key=lambda kv: -kv[1]["v"])]
    fin_rows = [(k, v["v"], v["n"]) for k, v in sorted(d["fct_fin"].items(), key=lambda kv: -kv[1]["v"])]
    rub = d["fap_rub"]
    rub_tot = sum(rub.values()) or 1
    rub_rows = "".join(
        f'<tr><td>{k}</td><td>{pct(v, rub_tot):.0f}%</td><td>{faixa(v)}</td></tr>'
        for k, v in sorted(rub.items(), key=lambda x: -x[1])) or '<tr><td class="muted">—</td><td></td><td></td></tr>'
    bol_ano = d["bol_ano"]
    bol_total = d["bol_total"]
    bunac = d["bol_tipo"].get("B-UnAC", 0)
    vol_rows = (f'<tr><td>FAPES (fomento estadual)</td><td>{d["fap_n"]}</td>'
                f'<td>{ordem(d["fap_v"])}</td></tr>'
                f'<tr><td>FACTO — coordenados pelo campus</td><td>{d["fct_coord_n"]}</td>'
                f'<td>{ordem(d["fct_coord_v"])}</td></tr>'
                f'<tr><td>FACTO — com participação (coord. ou equipe)</td><td>{d["fct_part_n"]}</td>'
                f'<td>contexto (rede)</td></tr>')
    tipo_rows = "".join(f'<tr><td>{t}</td><td>{n}</td></tr>'
                        for t, n in sorted(d["fct_tipo"].items(), key=lambda kv: -kv[1])) or \
        '<tr><td class="muted">—</td><td>0</td></tr>'
    banner = ('<div id="exp-banner" style="background:#b5455f;color:#fff;padding:10px 16px;'
              'font-weight:600;font-size:13.5px;text-align:center;position:sticky;top:0;z-index:9999;'
              "box-shadow:0 2px 6px rgba(0,0,0,.2);font-family:system-ui,sans-serif;\">⚠️ Estudo "
              'experimental em condução — os dados são preliminares e podem ser modificados. '
              'Não usar como fonte da verdade.</div>')
    gerado = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Captação de Projetos (FAPES + FACTO) — IFES Campus Serra</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
{banner}
<div class="page">
<header class="hero">
  <span class="kick">IFES Campus Serra · Captação de Projetos</span>
  <h1>Evolução e volume da captação de projetos</h1>
  <p class="lede">Quantos projetos os professores do campus captaram, em que ritmo e por qual
  fonte — <b>FAPES</b> (fomento estadual) e <b>FACTO</b> (fundação de apoio).</p>
  <div class="meta">
    <span><b>FAPES:</b> {d['fap_n']} projetos</span>
    <span><b>FACTO (campus):</b> {d['fct_coord_n']} coordenados · {d['fct_part_n']} com participação</span>
    <span><b>Captação total (ordem):</b> {ordem(total_capt)}</span>
    <span><b>Pico de captação:</b> {pico}</span>
    <span><b>Gerado em:</b> {gerado}</span>
  </div>
</header>

<section class="section">
  <div class="eyebrow">Panorama</div>
  <h2>Números da captação</h2>
  <div class="kpis">
    <div class="kpi"><div class="n">{d['fap_n']}</div><div class="u">projetos FAPES</div><div class="s">fomento estadual, campus Serra</div></div>
    <div class="kpi b2"><div class="n">{d['fct_coord_n']}</div><div class="u">projetos FACTO coordenados</div><div class="s">por docente do campus · +{d['fct_part_n']} com participação</div></div>
    <div class="kpi b3"><div class="n">{n_coord}</div><div class="u">coordenadores FAPES</div><div class="s">captadores distintos</div></div>
    <div class="kpi"><div class="n" style="font-size:19px;">{ordem(total_capt)}</div><div class="u">captação total</div><div class="s">ordem de grandeza (FAPES + FACTO-campus)</div></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Evolução</div>
  <h2>Projetos por ano</h2>
  <p class="desc">Volume de projetos iniciados por ano (linha) — <b>eixo Y</b> = nº de projetos,
  <b>eixo X</b> = ano. <b>Verde</b> = FAPES · <b>azul</b> = FACTO coordenado pelo campus. Mostra a
  <b>capilaridade</b> crescente da captação.</p>
  <div class="card">{_line_vol(anos, fap_ano, fct_ano)}
    <div class="legend"><span><i style="background:#0f7a40"></i>FAPES</span><span><i style="background:#2f6fb0"></i>FACTO (campus)</span></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Evolução</div>
  <h2>Captação por ano (índice)</h2>
  <p class="desc">Tendência da <b>captação FAPES</b> por ano, em <b>índice</b> (100 = ano de maior
  captação, {pico}). Mostra a forma da curva <b>sem expor valores</b>.</p>
  <div class="card">{_bars_idx(anos, fap_ano)}
    <div class="note"><b>Como ler:</b> 100 = pico; os demais anos são proporcionais a ele. Picos
    refletem <b>1–2 projetos grandes</b>, não um salto geral — leia junto com o volume acima.</div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Bolsas</div>
  <h2>Bolsistas ao longo dos anos</h2>
  <p class="desc">Nº de bolsas alocadas por ano de início (SigPesq) — <b>eixo Y</b> = bolsas,
  <b>eixo X</b> = ano. Mostra a expansão do fomento a bolsistas no campus.</p>
  <div class="card">{_line1(anos, lambda a: bol_ano.get(a, 0), "#6a4c93", "bolsas / ano")}
    <div class="note"><b>Atenção:</b> inclui <b>B-UnAC</b> (Universidade Aberta Capixaba, ensino/EAD):
    {bunac} de {bol_total} alocações — portanto <b>não é só pesquisa</b>. A curva reflete o conjunto
    das bolsas geridas, não apenas iniciação científica.</div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Composição</div>
  <h2>Em que o recurso FAPES é aplicado (rubricas)</h2>
  <p class="desc">Distribuição do orçamento contratado FAPES por <b>rubrica</b>, em <b>% do total</b>
  e faixa (sem cifra exata). As <b>bolsas</b> concentram a maior parte.</p>
  <div class="card"><table><thead><tr><th>Rubrica</th><th>% do total</th><th>Faixa</th></tr></thead>
    <tbody>{rub_rows}</tbody></table></div>
</section>

<section class="section">
  <div class="eyebrow">Volume por fonte</div>
  <h2>FAPES e FACTO</h2>
  <p class="desc">Projetos e captação por fonte. FACTO entra no <b>captado do campus</b> só quando o
  <b>coordenador</b> é docente do campus; "com participação" (coord. ou equipe) é contexto.</p>
  <div class="card"><table><thead><tr><th>Fonte</th><th>Projetos</th><th>Captação (ordem)</th></tr></thead>
    <tbody>{vol_rows}</tbody></table></div>
</section>

<section class="section">
  <div class="eyebrow">Liderança</div>
  <h2>Coordenadores por captação (FAPES)</h2>
  <p class="desc">Top coordenadores por participação no orçamento FAPES — em <b>faixa + %</b> do
  total (sem cifra individual).</p>
  <div class="card">{_hbars(top_coord_rows, d['fap_v'])}</div>
</section>

<section class="section">
  <div class="eyebrow">Liderança</div>
  <h2>Coordenadores por captação (FACTO — campus)</h2>
  <p class="desc">Coordenadores de projetos FACTO com coordenação de docente do campus — faixa + %
  do total FACTO-campus. Universo pequeno (poucos projetos coordenados pelo campus).</p>
  <div class="card">{_hbars(fct_coord_rows, d['fct_coord_v'])}</div>
</section>

<section class="section">
  <div class="eyebrow">Financiadoras</div>
  <h2>Financiadoras (FACTO, projetos do campus)</h2>
  <p class="desc">Origem do recurso dos projetos FACTO coordenados pelo campus — faixa + %.</p>
  <div class="card">{_hbars(fin_rows, d['fct_coord_v'])}</div>
</section>

<section class="section">
  <div class="eyebrow">Natureza</div>
  <h2>Tipo dos projetos FACTO (campus)</h2>
  <div class="card"><table><thead><tr><th>Tipo de projeto</th><th>Projetos</th></tr></thead>
    <tbody>{tipo_rows}</tbody></table></div>
</section>

{EXPL}

<div class="foot">Fontes: FAPES (orçamento contratado) e FACTO (valor aprovado), campus Serra.
FACTO restrito a projetos coordenados por docente do campus (regra de captação). Valores em
ordem de grandeza/faixa por segurança. Gerado em {gerado}.</div>
</div></body></html>"""


def main() -> None:
    d = carregar()
    OUT.write_text(render(d), encoding="utf-8")
    print(f"OK -> {OUT.relative_to(ROOT)}")
    print(f"FAPES: {d['fap_n']} proj · {ordem(d['fap_v'])} | "
          f"FACTO campus: {d['fct_coord_n']} coord ({ordem(d['fct_coord_v'])}) · "
          f"{d['fct_part_n']} c/ participação")


if __name__ == "__main__":
    main()
