"""
Relatório analítico do PPComp — base completa de discentes.

Fonte: data/mestrado/base_de_dados_ppcomp.json (269 discentes: coorte, orientador,
bolsa, situação, data de defesa). Gera HTML claro (+ PDF opcional) com situação,
coortes, desfecho, tempo até defesa, carga de orientação e trilhas especiais.

Uso:
  python -m src.scripts.generate_ppcomp_base_report          # HTML
  python -m src.scripts.generate_ppcomp_base_report --pdf    # HTML + PDF
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC = BASE / "data" / "mestrado" / "base_de_dados_ppcomp.json"
OUT_DIR = BASE / "data" / "exports" / "mestrado"

# orientador1 (nome curto na base) → nome completo do docente (roster IFES Serra).
# Curtos não mapeados (ex.: externos) ficam como estão.
ORIENTADOR_FULL = {
    "Boldt": "Francisco de Assis Boldt",
    "Cristina": "Cristina Klippel Dominicini",
    "Danilo": "Danilo de Paula e Silva",
    "Fabiano": "Fabiano Borges Ruy",
    "Gilmar": "Gilmar Luiz Vassoler",
    "Hilário Seibel": "Hilário Seibel Júnior",
    "Hilário T.": "Hilário Tomaz Alves de Oliveira",
    "Jefferson": "Jefferson Oliveira Andrade",
    "Karin": "Karin Satie Komati",
    "Kelly": "Kelly Assis de Souza Gazolli",
    "Leandro": "Leandro Colombi Resendo",
    "Mateus": "Mateus Conrad Barcellos da Costa",
    "Maxwell": "Maxwell Eduardo Monteiro",
    "Paulo": "Paulo Sergio dos Santos Junior",
    "Sergio": "Sérgio Nery Simões",
    "Thiago": "Thiago Meireles Paixão",
}


def _orient_full(nome: str) -> str:
    """Resolve o nome curto do orientador para o nome completo (ou mantém o curto)."""
    return ORIENTADOR_FULL.get((nome or "").strip(), (nome or "").strip())


# situação → cor
SIT_COL = {
    "Defendido": "var(--brand)", "Ativo": "var(--blue)", "Cancelado": "var(--rose)",
    "Trancado": "var(--amber)", "Desistência (indicada)": "#6a4c93",
}
EVASAO = {"Cancelado", "Trancado", "Desistência (indicada)"}


def _ano(coorte) -> int | None:
    m = re.match(r"(\d{4})", str(coorte or ""))
    y = int(m.group(1)) if m else None
    return y if y and 2015 <= y <= 2030 else None


def _ano_defesa(s) -> int | None:
    """Extrai ano da data de defesa em formatos variados; ignora sentinela 1905."""
    if not s:
        return None
    for m in re.finditer(r"(\d{4})", str(s)):
        y = int(m.group(1))
        if 2018 <= y <= 2030:
            return y
    return None


# ---------------------------------------------------------------------------
# Compute
# ---------------------------------------------------------------------------

def compute() -> dict:
    d = json.loads(SRC.read_text())
    n = len(d)
    sit = Counter(x.get("situacao") or "—" for x in d)
    defendidos = sit.get("Defendido", 0)
    ativos = sit.get("Ativo", 0)
    evasao = sum(v for k, v in sit.items() if k in EVASAO)

    # por ano de ingresso
    sit_ano: dict[int, Counter] = defaultdict(Counter)
    ingresso_ano: Counter = Counter()
    for x in d:
        a = _ano(x.get("coorte"))
        if a:
            ingresso_ano[a] += 1
            sit_ano[a][x.get("situacao")] += 1

    # tempo até defesa (anos)
    tempos = []
    for x in d:
        ai = _ano(x.get("coorte"))
        ad = _ano_defesa(x.get("data_defesa"))
        if ai and ad and 0 <= ad - ai <= 8:
            tempos.append(ad - ai)
    tempo_dist = Counter(tempos)
    tempo_med = round(sum(tempos) / len(tempos), 1) if tempos else 0

    # carga de orientação (orientador1 preenchido) — nome curto → nome completo
    orient = Counter(_orient_full(x["orientador1"]) for x in d if x.get("orientador1"))
    sem_orient = sum(1 for x in d if not x.get("orientador1"))
    co_orient = sum(1 for x in d if x.get("coorientador"))

    # trilhas especiais
    unac = sum(1 for x in d if "unac" in str(x.get("coorte")).lower())
    mulheres = sum(1 for x in d if "mulher" in str(x.get("coorte")).lower())

    # bolsa (raramente preenchida)
    com_bolsa = sum(1 for x in d if x.get("bolsista"))

    # pipeline: quantos discentes vieram da graduação Serra (formandos)
    pipeline = {"total": 0, "por_situacao": {}, "por_curso": {}}
    try:
        from src.scripts.generate_formandos_report import (
            SEMESTER_FILE_MAP, DATA_FORMANDOS, load_formandos, _match_key)
        seen = {}
        for sem in sorted(SEMESTER_FILE_MAP):
            if (DATA_FORMANDOS / SEMESTER_FILE_MAP[sem]).exists():
                for f in load_formandos(sem):
                    seen.setdefault(f["matricula"] or f["nome"].strip().lower(), f)
        form = {_match_key(f["nome"]): f for f in seen.values()}
        de_form = [x for x in d if _match_key(x.get("nome_completo")) in form]
        pipeline = {
            "total": len(de_form),
            "pct": round(len(de_form) / n * 100, 1) if n else 0,
            "defendidos": sum(1 for x in de_form if x.get("situacao") == "Defendido"),
            "ativos": sum(1 for x in de_form if x.get("situacao") == "Ativo"),
            "por_situacao": dict(Counter(x.get("situacao") for x in de_form)),
            "por_curso": dict(Counter(form[_match_key(x["nome_completo"])]["curso"] for x in de_form)),
        }
    except Exception:
        pass

    # taxa de conclusão entre os de desfecho definido (defendido + evasão)
    desfecho = defendidos + evasao
    taxa_defesa = round(defendidos / desfecho * 100, 1) if desfecho else 0

    # cruzamento com bolsas pagas FAPES + FACTO
    bolsas = {"fapes": 0, "facto": 0, "uniao": 0, "ambos": 0, "valor_fapes": 0,
              "por_situacao": {}, "registros": []}
    try:
        from src.scripts.generate_formandos_report import _match_key as _mk
        mk_mest = {_mk(x["nome_completo"]): x for x in d if x.get("nome_completo")}
        bdir = BASE / "data" / "exports"
        fp = json.loads((bdir / "bolsistas" / "ifes-campus-serra-bolsistas.json").read_text())
        fapes_val = {_mk(b["bolsista_pesquisador_nome"]): b.get("valor_alocado_total", 0) or 0
                     for b in fp.get("bolsistas_unicos", [])}
        ftipos = defaultdict(set)
        for a in fp.get("alocacoes", []):
            ftipos[_mk(a["bolsista_pesquisador_nome"])].add(a.get("bolsa_sigla"))
        fa = json.loads((bdir / "projetos-facto" / "facto_projects_full.json").read_text())
        facto_p = set()
        for p in fa.get("projects", []):
            for k, rows in (p.get("csv") or {}).items():
                if k.endswith("Equipe.csv"):
                    for r in rows:
                        if r.get("Nome") and "bolsista" in (r.get("Função") or "").lower():
                            facto_p.add(_mk(r["Nome"]))
        m_fapes = {mk for mk in mk_mest if mk in fapes_val}
        m_facto = {mk for mk in mk_mest if mk in facto_p}
        uniao = m_fapes | m_facto
        regs = []
        for mk in uniao:
            x = mk_mest[mk]
            fontes = ([("FAPES")] if mk in m_fapes else []) + (["FACTO"] if mk in m_facto else [])
            regs.append({
                "nome": x["nome_completo"], "situacao": x.get("situacao"),
                "fontes": fontes, "valor_fapes": fapes_val.get(mk, 0),
                "tipos": sorted(t for t in ftipos.get(mk, set()) if t),
            })
        regs.sort(key=lambda r: -r["valor_fapes"])
        bolsas = {
            "fapes": len(m_fapes), "facto": len(m_facto), "uniao": len(uniao),
            "ambos": len(m_fapes & m_facto),
            "valor_fapes": sum(fapes_val[mk] for mk in m_fapes),
            "por_situacao": dict(Counter(mk_mest[mk].get("situacao") for mk in uniao)),
            "registros": regs,
        }
    except Exception:
        pass

    return {
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "bolsas": bolsas,
        "total": n,
        "defendidos": defendidos,
        "ativos": ativos,
        "evasao": evasao,
        "taxa_defesa_desfecho": taxa_defesa,
        "tempo_medio_anos": tempo_med,
        "tempo_dist": dict(sorted(tempo_dist.items())),
        "situacao": dict(sit.most_common()),
        "ingresso_ano": dict(sorted(ingresso_ano.items())),
        "sit_ano": {a: dict(c) for a, c in sorted(sit_ano.items())},
        "orientadores": orient.most_common(),
        "sem_orientador": sem_orient,
        "co_orientacoes": co_orient,
        "orientadores_distintos": len(orient),
        "unac": unac,
        "mulheres": mulheres,
        "com_bolsa": com_bolsa,
        "pipeline": pipeline,
    }


# ---------------------------------------------------------------------------
# Render (light theme, self-contained)
# ---------------------------------------------------------------------------

CSS = """
:root{--ink:#16241a;--ink2:#3c4f42;--muted:#71857a;--line:#e3ece5;--line2:#cfddd3;
--paper:#fff;--bg:#f4f8f5;--soft:#eef5f0;--brand:#0f7a40;--brand-d:#0a5c30;--brand-l:#e7f4ec;
--blue:#2f6fb0;--blue-l:#e8f0f8;--amber:#b8860b;--amber-l:#f7f0dd;--rose:#b5455f;
--shadow:0 1px 2px rgba(16,40,24,.04),0 6px 20px rgba(16,40,24,.06);
--font:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;--serif:'Georgia',serif;}
*{margin:0;padding:0;box-sizing:border-box;}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
body{background:var(--bg);color:var(--ink);font-family:var(--font);line-height:1.55;font-size:15px;}
.page{max-width:980px;margin:0 auto;padding:0 28px 80px;}
.hero{padding:60px 0 40px;border-bottom:3px solid var(--brand);margin-bottom:44px;}
.kicker{display:inline-flex;gap:8px;font-size:12px;font-weight:600;letter-spacing:.14em;
text-transform:uppercase;color:var(--brand);background:var(--brand-l);padding:6px 14px;border-radius:999px;margin-bottom:20px;}
.hero h1{font-family:var(--serif);font-size:clamp(28px,5vw,46px);line-height:1.1;font-weight:700;max-width:20ch;}
.hero .lede{font-size:18px;color:var(--ink2);margin-top:18px;max-width:64ch;}
.hero .meta{display:flex;flex-wrap:wrap;gap:8px 24px;margin-top:24px;font-size:13px;color:var(--muted);}
.hero .meta b{color:var(--ink);}
.section{margin:50px 0;}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--brand);margin-bottom:10px;}
.section h2{font-family:var(--serif);font-size:26px;font-weight:700;margin-bottom:8px;}
.section .desc{font-size:15px;color:var(--ink2);max-width:66ch;margin-bottom:24px;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;}
.kpi{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:22px 20px;
box-shadow:var(--shadow);position:relative;overflow:hidden;}
.kpi::after{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--brand);}
.kpi .n{font-size:34px;font-weight:800;letter-spacing:-.02em;color:var(--brand-d);line-height:1;}
.kpi .u{font-size:14px;font-weight:600;margin-top:8px;}
.kpi .s{font-size:12.5px;color:var(--muted);margin-top:4px;}
.card{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:26px 28px;box-shadow:var(--shadow);}
.card h3{font-size:16px;font-weight:700;margin-bottom:16px;}
.brow{display:grid;grid-template-columns:200px 1fr 132px;align-items:center;gap:14px;margin-bottom:13px;}
.bl{font-size:13.5px;}.btrack{height:18px;background:var(--soft);border-radius:9px;overflow:hidden;}
.bfill{height:100%;border-radius:9px;min-width:6px;}.bv{font-size:13px;font-weight:700;text-align:right;white-space:nowrap;}
table{width:100%;border-collapse:collapse;font-size:14px;}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);}
td.r,th.r{text-align:right;}
thead th{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:700;}
tbody tr:last-child td{border-bottom:none;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px;}
.note-line{font-size:12.5px;color:var(--muted);margin-top:14px;font-style:italic;}
.foot{margin-top:60px;padding-top:22px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted);
display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;}
@media(max-width:760px){.grid2{grid-template-columns:1fr;}.brow{grid-template-columns:130px 1fr 90px;}}
@media print{body{background:#fff;font-size:12px;}.section{page-break-inside:avoid;}.kpi,.card{box-shadow:none;}}
"""


def _bar(label, value, mx, color, note):
    w = value / mx * 100 if mx else 0
    return (f'<div class="brow"><span class="bl">{label}</span>'
            f'<div class="btrack"><div class="bfill" style="width:{max(w,1.5):.1f}%;background:{color};"></div></div>'
            f'<span class="bv">{note}</span></div>')


def _stacked_bar_year(sit_ano: dict, anos: list) -> str:
    """Barra empilhada por ano: situação proporcional."""
    order = ["Defendido", "Ativo", "Trancado", "Cancelado", "Desistência (indicada)"]
    rows = ""
    mx = max((sum(sit_ano[a].values()) for a in anos), default=1)
    for a in anos:
        c = sit_ano[a]
        tot = sum(c.values())
        segs = ""
        for s in order:
            v = c.get(s, 0)
            if not v:
                continue
            pctw = v / tot * 100
            lbl = str(v) if pctw >= 7 else ""   # mostra nº se o segmento couber
            segs += (f'<div style="width:{pctw:.1f}%;background:{SIT_COL.get(s,"var(--muted)")};'
                     f'display:flex;align-items:center;justify-content:center;color:#fff;'
                     f'font-size:11px;font-weight:700;" title="{s}: {v}">{lbl}</div>')
        rows += (
            f'<div style="display:grid;grid-template-columns:56px 1fr 40px;align-items:center;gap:12px;margin-bottom:7px;">'
            f'<span style="font-size:12.5px;color:var(--ink2);">{a}</span>'
            f'<div style="display:flex;height:24px;border-radius:5px;overflow:hidden;width:{tot/mx*100:.0f}%;">{segs}</div>'
            f'<span style="font-size:12px;color:var(--muted);text-align:right;font-weight:600;">{tot}</span></div>'
        )
    legend = '<div style="display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:12px;">' + "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--ink2);">'
        f'<span style="width:12px;height:12px;border-radius:3px;background:{SIT_COL.get(s)};"></span>{s}</span>'
        for s in order) + '</div>'
    return rows + legend


def _line_chart(anos, vals, color, fmt, aria):
    if not anos:
        return ""
    W, H = 820, 300
    ml, mr, mt, mb = 48, 20, 18, 42
    iw, ih = W - ml - mr, H - mt - mb
    vmax = max(vals) or 1
    nn = len(anos)
    def x(i): return ml + (iw * i / (nn - 1) if nn > 1 else iw / 2)
    def y(v): return mt + ih - (v / vmax * ih)
    grid = ""
    for g in range(6):
        gy = y(vmax * g / 5)
        grid += (f'<line x1="{ml}" y1="{gy:.0f}" x2="{W-mr}" y2="{gy:.0f}" stroke="var(--line)"/>'
                 f'<text x="{ml-8}" y="{gy+4:.0f}" text-anchor="end" font-size="11" fill="var(--muted)">{fmt(vmax*g/5)}</text>')
    pts = [(x(i), y(vals[i])) for i in range(nn)]
    poly = " ".join(f"{a:.0f},{b:.0f}" for a, b in pts)
    dots = ""
    for i, a in enumerate(anos):
        px, py = pts[i]
        dots += (f'<circle cx="{px:.0f}" cy="{py:.0f}" r="4" fill="{color}" stroke="#fff" stroke-width="1.5"/>'
                 f'<text x="{px:.0f}" y="{py-11:.0f}" text-anchor="middle" font-size="11" font-weight="700" fill="{color}">{fmt(vals[i])}</text>'
                 f'<text x="{px:.0f}" y="{mt+ih+18:.0f}" text-anchor="middle" font-size="11" fill="var(--ink2)">{a}</text>')
    return (f'<div style="overflow-x:auto;"><svg viewBox="0 0 {W} {H}" style="width:100%;min-width:560px;height:auto;'
            f'font-family:var(--font);" role="img" aria-label="{aria}">{grid}'
            f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"/>{dots}</svg></div>')


def render(s: dict) -> str:
    n = s["total"]
    sit = s["situacao"]
    smax = max(sit.values()) if sit else 1
    sit_bars = "".join(
        _bar(k, v, smax, SIT_COL.get(k, "var(--muted)"), f"{v} · {round(v/n*100)}%")
        for k, v in sit.items()
    )
    anos = [a for a in s["ingresso_ano"]]
    ing_chart = _line_chart(anos, [s["ingresso_ano"][a] for a in anos], "var(--brand)",
                            lambda v: f"{v:.0f}", "Ingressantes por ano")
    sit_ano = {int(a): Counter(c) for a, c in s["sit_ano"].items()}
    stacked = _stacked_bar_year(sit_ano, sorted(sit_ano))

    # tempo até defesa
    td = s["tempo_dist"]
    tmax = max(td.values()) if td else 1
    tempo_bars = "".join(
        _bar(f"{k} ano{'s' if k != 1 else ''}", v, tmax, "var(--blue)", f"{v}")
        for k, v in sorted(td.items())
    )
    # orientadores
    omax = s["orientadores"][0][1] if s["orientadores"] else 1
    orient_rows = "".join(
        f'<tr><td>{nome}</td><td class="r">{v}</td></tr>' for nome, v in s["orientadores"]
    )

    # pipeline graduação → mestrado
    _pp = s.get("pipeline", {})
    _ppmax = max(_pp.get("por_situacao", {}).values()) if _pp.get("por_situacao") else 1
    pp_bars = "".join(
        _bar(k, v, _ppmax, SIT_COL.get(k, "var(--muted)"), str(v))
        for k, v in sorted(_pp.get("por_situacao", {}).items(), key=lambda x: -x[1])
    )
    pp_curso = " · ".join(f"{c}: {v}" for c, v in _pp.get("por_curso", {}).items())

    # bolsas FAPES/FACTO
    _bo = s.get("bolsas", {})
    def _brl(v):
        return f'R$ {v:,.0f}'.replace(",", "X").replace(".", ",").replace("X", ".") if v else "—"
    bo_rows = "".join(
        f'<tr><td>{r["nome"]}</td><td>{r.get("situacao")}</td>'
        f'<td>{" + ".join(r["fontes"])}{(" · "+", ".join(r["tipos"])) if r["tipos"] else ""}</td></tr>'
        for r in _bo.get("registros", [])
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PPComp — Relatório analítico de discentes — IFES</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="page">
<header class="hero">
  <div class="kicker">● PPComp · Mestrado · Análise de discentes</div>
  <h1>O mestrado PPComp em números: ingresso, defesa e evasão</h1>
  <p class="lede">Base completa de <b>{n} discentes</b> do PPComp — situação acadêmica, coortes,
  tempo até a defesa, carga de orientação e trilhas de inclusão.</p>
  <div class="meta">
    <span>Discentes: <b>{n}</b></span>
    <span>Defendidos: <b>{s['defendidos']}</b></span>
    <span>Ativos: <b>{s['ativos']}</b></span>
    <span>Tempo médio até defesa: <b>{s['tempo_medio_anos']} anos</b></span>
  </div>
</header>

<section class="section"><div class="kpis">
  <div class="kpi"><div class="n">{n}</div><div class="u">discentes no total</div><div class="s">todas as coortes</div></div>
  <div class="kpi"><div class="n">{s['defendidos']}</div><div class="u">defenderam</div><div class="s">{round(s['defendidos']/n*100)}% do total</div></div>
  <div class="kpi"><div class="n">{s['ativos']}</div><div class="u">ativos</div><div class="s">em curso</div></div>
  <div class="kpi"><div class="n">{s['evasao']}</div><div class="u">evasão</div><div class="s">cancelado/trancado/desistência · {round(s['evasao']/n*100)}%</div></div>
  <div class="kpi"><div class="n">{s['taxa_defesa_desfecho']}%</div><div class="u">taxa de defesa</div><div class="s">entre os com desfecho</div></div>
  <div class="kpi"><div class="n">{_pp.get('total',0)}</div><div class="u">vindos da graduação Serra</div><div class="s">{_pp.get('pct',0)}% · pipeline interno</div></div>
</div></section>

<section class="section">
  <div class="eyebrow">Pipeline graduação → mestrado</div>
  <h2>Quantos vieram da própria graduação</h2>
  <p class="desc"><b>{_pp.get('total',0)}</b> dos {n} discentes ({_pp.get('pct',0)}%) concluíram a
  graduação no IFES Serra antes de ingressar no mestrado — a "prata da casa". Destes,
  <b>{_pp.get('defendidos',0)}</b> já defenderam e <b>{_pp.get('ativos',0)}</b> seguem ativos.</p>
  <div class="card">{pp_bars}
    <div class="note-line">Por curso de origem: {pp_curso}. Casamento por nome (sem acento) com
    a base de 306 formandos da graduação (SI + ECA). Match exato — subestima.</div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Fomento aos discentes</div>
  <h2>Mestrandos com bolsa paga (FAPES / FACTO)</h2>
  <p class="desc">Discentes do PPComp que aparecem como bolsistas pagos da <b>FAPES</b> ou em
  projetos do <b>FACTO</b>. {_bo.get('uniao',0)} discentes ({_bo.get('fapes',0)} FAPES ·
  {_bo.get('facto',0)} FACTO), somando <b>{_brl(_bo.get('valor_fapes',0))}</b> alocados pela FAPES.</p>
  <div class="card">
    <table><thead><tr><th>Discente</th><th>Situação</th><th>Fonte / bolsa</th></tr></thead>
    <tbody>{bo_rows}</tbody></table>
    <div class="note-line">Casamento por nome (sem acento). FAPES: bolsistas únicos do campus
    (ME = mestrado, B-UnAC, BPIG, ICT…). FACTO: equipe com função "Bolsista". Valor FACTO não
    detalhado por pessoa na fonte. {_bo.get('ambos',0)} discentes em ambas as fontes.</div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Situação acadêmica</div>
  <h2>Onde estão os discentes</h2>
  <p class="desc">Distribuição por situação atual.</p>
  <div class="card">{sit_bars}</div>
</section>

<section class="section">
  <div class="eyebrow">Entrada</div>
  <h2>Ingressantes por ano</h2>
  <p class="desc">Volume de discentes por ano de ingresso (coorte).</p>
  <div class="card">{ing_chart}</div>
</section>

<section class="section">
  <div class="eyebrow">Desfecho por turma</div>
  <h2>Situação por ano de ingresso</h2>
  <p class="desc">Como cada turma se distribuiu entre defesa, curso, trancamento e evasão.
  Turmas recentes têm muitos ativos; turmas antigas, mais defesas e cancelamentos.</p>
  <div class="card">{stacked}</div>
</section>

<section class="section">
  <div class="grid2">
    <div>
      <div class="eyebrow">Tempo de conclusão</div>
      <h2>Tempo até a defesa</h2>
      <p class="desc">Anos entre o ingresso e a defesa (entre os {sum(s['tempo_dist'].values())} com data válida).</p>
      <div class="card">{tempo_bars}
        <div class="note-line">Mestrado: 24 meses regulamentar. Maioria defende em 2 anos.</div></div>
    </div>
    <div>
      <div class="eyebrow">Orientação</div>
      <h2>Carga por orientador</h2>
      <p class="desc">Discentes por orientador principal ({s['orientadores_distintos']} orientadores;
      {s['co_orientacoes']} com coorientação).</p>
      <div class="card"><div style="max-height:340px;overflow-y:auto;">
        <table><thead><tr><th>Orientador</th><th class="r">Discentes</th></tr></thead>
        <tbody>{orient_rows}</tbody></table></div></div>
    </div>
  </div>
</section>

<section class="section">
  <div class="eyebrow">Inclusão</div>
  <h2>Trilhas especiais</h2>
  <p class="desc">Coortes específicas de ações afirmativas e parcerias.</p>
  <div class="kpis">
    <div class="kpi"><div class="n">{s['unac']}</div><div class="u">vagas UnAC</div><div class="s">Universidade Aberta Capixaba</div></div>
    <div class="kpi"><div class="n">{s['mulheres']}</div><div class="u">trilha de mulheres</div><div class="s">coorte afirmativa de gênero</div></div>
    <div class="kpi"><div class="n">{s['com_bolsa']}</div><div class="u">com bolsa registrada</div><div class="s">FAPES/CAPES/CNPq/PROCAP</div></div>
  </div>
  <div class="card" style="margin-top:18px;">
    <div class="note-line"><b>Limitações da base:</b> orientador principal vazio em
    {s['sem_orientador']} registros e bolsa preenchida em apenas {s['com_bolsa']} — os números
    de orientação e bolsa subestimam o real. Datas de defesa têm formatos mistos; registros com
    sentinela inválida (1905) foram descartados no cálculo de tempo.</div>
  </div>
</section>

<div class="foot"><span>PPComp · Relatório analítico de discentes — IFES</span>
  <span>Gerado em {s['gerado_em']} · {n} discentes</span></div>
</div></body></html>"""


def _find_chrome():
    import shutil
    for c in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "google-chrome", "chromium", "chrome"]:
        if os.path.isfile(c):
            return c
        w = shutil.which(c)
        if w:
            return w
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None)
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()

    print("Analisando base PPComp...")
    s = compute()
    print(f"  {s['total']} discentes · {s['defendidos']} defendidos · "
          f"{s['ativos']} ativos · evasão {s['evasao']} · tempo médio {s['tempo_medio_anos']} anos")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else OUT_DIR / "ppcomp_base_analitico.html"
    out.write_text(render(s), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written: {out}")
    print(f"Written: {out.with_suffix('.json')}")

    if args.pdf:
        chrome = _find_chrome()
        if chrome:
            pdf = out.with_suffix(".pdf")
            subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                            "--virtual-time-budget=8000", "--run-all-compositor-stages-before-draw",
                            f"--print-to-pdf={pdf}", out.resolve().as_uri()],
                           capture_output=True, timeout=120)
            if pdf.exists():
                print(f"Written: {pdf}")
        else:
            print("PDF: Chrome não encontrado.")


if __name__ == "__main__":
    main()
