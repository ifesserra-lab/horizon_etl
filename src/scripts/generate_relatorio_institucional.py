"""
Relatório institucional unificado — IFES Serra.

Funde, num único HTML, o relatório executivo da graduação (Formandos × Pesquisa)
com o relatório de egressos do mestrado PPComp, contando a história completa
graduação → mestrado. Reutiliza os dois geradores existentes (não duplica lógica):
extrai as seções de cada um e as compõe sob um cabeçalho institucional único.

Uso:
  python -m src.scripts.generate_relatorio_institucional
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from src.scripts import generate_formandos_executive as EX
from src.scripts import generate_ppcomp_egressos_report as PP
from src.scripts import generate_ppcomp_base_report as PPB
from src.scripts.generate_formandos_report import _match_key, normalize_name
from src.scripts.didatica import bloco_didatico, MOBILE_CSS

OUT_DIR = EX.OUT_DIR  # data/exports/formandos
DEFAULT_OUT = OUT_DIR / "relatorio_institucional.html"
PROJETOS_FILE = (EX.BASE / "data" / "exports" / "projetos-fapes"
                 / "ifes-campus-serra-projetos-concluidos-em-andamento.json")
FACTO_FILE = (EX.BASE / "data" / "exports" / "projetos-facto"
              / "facto_projects_full.json")
LATTES_DIR = EX.BASE / "data" / "lattes_json"


def _professores_campus() -> dict[str, str]:
    """{match_key → nome} dos professores do campus, a partir dos CVs Lattes."""
    profs: dict[str, str] = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        try:
            j = json.loads(Path(f).read_text())
        except Exception:
            continue
        nm = ((j.get("informacoes_pessoais") or {}).get("nome") or "").strip()
        if not nm:
            m = re.match(r"^\d+_(.+?)_\d+$", os.path.splitext(os.path.basename(f))[0])
            nm = m.group(1).replace("-", " ") if m else os.path.basename(f)
        profs[_match_key(nm)] = normalize_name(nm)
    return profs


# Coordenadores excluídos da análise de projetos (recorte da gestão).
_EXCLUDED_COORD_SUBSTR = ("elton",)


def _is_excluded_coord(name: str | None) -> bool:
    return any(sub in _match_key(name) for sub in _EXCLUDED_COORD_SUBSTR)


def _facto_info(p: dict) -> dict:
    for k, rows in (p.get("csv") or {}).items():
        if k.endswith("Informaçoes do projeto.csv") and rows:
            return rows[0]
    return {}


def _facto_brl(s) -> float:
    s = (str(s) or "").strip()
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def _facto_natureza(tipo: str | None) -> str:
    t = (tipo or "").lower()
    if not t:
        return "Sem tipo"
    if "seletivo" in t or "concurso" in t:
        return "Seleção/Concurso"
    if "pesquisa" in t or "inova" in t or "desenvolvimento" in t:
        return "Pesquisa, Desenv. e Inovação"
    if "extens" in t:
        return "Extensão"
    if "ensino" in t:
        return "Ensino"
    return "Outros"


def facto_section() -> str:
    """Parte 4 — projetos FACTO com participação de professores do campus Serra."""
    if not FACTO_FILE.exists():
        return ""
    from datetime import date as _date
    d = json.loads(FACTO_FILE.read_text())
    profs = _professores_campus()
    total_portal = len(d["projects"])

    # ---- identifica projetos Serra PELOS PROFESSORES (coord ou equipe) ----
    proj_profs: dict[str, dict[str, set]] = {}   # pid → {coord, membro} (nomes)
    prof_proj = defaultdict(lambda: {"coord": set(), "membro": set()})
    for p in d["projects"]:
        i = _facto_info(p)
        if _is_excluded_coord(i.get("Coordenador")):
            continue  # remove projetos do coordenador excluído (recorte da gestão)
        found = {"coord": set(), "membro": set()}
        c = _match_key(i.get("Coordenador"))
        if c in profs:
            found["coord"].add(profs[c])
            prof_proj[profs[c]]["coord"].add(p["id"])
        for k, rows in (p.get("csv") or {}).items():
            if k.endswith("Equipe.csv"):
                for r in rows:
                    mk = _match_key(r.get("Nome"))
                    if mk in profs:
                        func = (r.get("Função") or "").lower()
                        bucket = "coord" if "coorden" in func else "membro"
                        found[bucket].add(profs[mk])
                        prof_proj[profs[mk]][bucket].add(p["id"])
        if found["coord"] or found["membro"]:
            proj_profs[p["id"]] = found
    serra = [p for p in d["projects"] if p["id"] in proj_profs]

    # ---- indicadores (mesmo painel da FAPES), só projetos Serra ----
    fvals, fcoord, fdurs, fconc = [], defaultdict(float), [], 0
    fnat = defaultdict(lambda: [0, 0.0])
    fano_val: dict[int, float] = defaultdict(float)
    today = datetime.now().date()
    for p in serra:
        i = _facto_info(p)
        v = _facto_brl(i.get("Valor aprovado"))
        fvals.append(v)
        fcoord[(i.get("Coordenador") or "").strip()] += v
        nat = _facto_natureza(i.get("Tipo de Projeto"))
        fnat[nat][0] += 1
        fnat[nat][1] += v
        try:
            ini = _date(*map(int, i.get("Data de início", "").split("/")[::-1]))
            fano_val[ini.year] += v
            vig = _date(*map(int, i.get("Data de vigência", "").split("/")[::-1]))
            m = (vig - ini).days / 30
            if 0 < m < 200:
                fdurs.append(m)
        except Exception:
            pass
        try:
            enc = _date(*map(int, i.get("Data de encerramento", "").split("/")[::-1]))
            if enc <= today:
                fconc += 1
        except Exception:
            pass
    n_serra = len(serra)
    f_orc = sum(fvals) or 1
    f_ncoord = len([c for c in fcoord if c])
    f_maior = max(fvals) if fvals else 0
    f_dur = sum(fdurs) / len(fdurs) if fdurs else 0
    n_prof = len(prof_proj)
    n_prof_coord = sum(1 for v in prof_proj.values() if v["coord"])

    kpi_g = [
        (str(n_serra), "projetos do campus", f"de {total_portal} no portal FACTO"),
        (_brl(f_orc), "valor aprovado total", "projetos com prof. da Serra"),
        (_brl(f_orc / n_serra) if n_serra else "—", "ticket médio", f"{sum(1 for v in fvals if v>0)} c/ valor"),
        (str(n_prof), "professores do campus", f"{n_prof_coord} como coordenador"),
        (str(f_ncoord), "coordenadores distintos", f"{n_serra/f_ncoord:.1f} proj. cada" if f_ncoord else "—"),
        (f"{f_dur/12:.1f} anos", "duração média", f"{f_dur:.0f} meses"),
        (f"{round(f_maior/f_orc*100)}%", "no maior projeto", "concentração de valor"),
        (f"{round(fconc/n_serra*100)}%" if n_serra else "—", "taxa de conclusão", f"{fconc} encerrados"),
    ]
    g_cards = "".join(
        f'<div class="kpi"><div class="n" style="font-size:30px;">{nn}</div>'
        f'<div class="u">{u}</div><div class="s">{ss}</div></div>'
        for nn, u, ss in kpi_g
    )

    # natureza (campo oficial "Tipo de Projeto")
    NCOL = {"Pesquisa, Desenv. e Inovação": "var(--brand)", "Extensão": "var(--amber)",
            "Ensino": "var(--blue)", "Seleção/Concurso": "#6a4c93",
            "Sem tipo": "var(--line2)", "Outros": "var(--muted)"}
    nmax = max((v[0] for v in fnat.values()), default=1)
    nat_bars = "".join(
        f'<div class="brow"><span class="bl">{k}</span>'
        f'<div class="btrack"><div class="bfill" style="width:{max(v[0]/nmax*100,1.5):.1f}%;'
        f'background:{NCOL.get(k,"var(--muted)")};"></div></div>'
        f'<span class="bv">{v[0]} · {_brl(v[1])}</span></div>'
        for k, v in sorted(fnat.items(), key=lambda x: -x[1][1])
    )
    # valor por ano (line)
    fanos = sorted(a for a in fano_val if a)
    facto_ano_chart = _line_chart(
        fanos, [fano_val[a] for a in fanos], _brl, "var(--brand)", "gfacto",
        "Valor FACTO (campus) aprovado por ano") if fanos else ""

    # tabela: os projetos Serra (todos), com professores envolvidos
    _facto_tot = sum(_facto_brl(_facto_info(p).get("Valor aprovado")) for p in serra) or 1
    proj_rows = ""
    for p in sorted(serra, key=lambda p: -_facto_brl(_facto_info(p).get("Valor aprovado"))):
        i = _facto_info(p)
        v = _facto_brl(i.get("Valor aprovado"))
        fp = proj_profs[p["id"]]
        envolv = ", ".join(sorted(fp["coord"] | fp["membro"]))
        papel = "coord." if fp["coord"] else "equipe"
        proj_rows += (
            f'<tr><td>[{p["id"]}] {p["name"][:48]}</td>'
            f'<td style="font-size:12px;">{normalize_name((i.get("Coordenador") or "")[:22])}</td>'
            f'<td style="font-size:12px;">{_facto_natureza(i.get("Tipo de Projeto"))}</td>'
            f'<td style="font-size:12px;color:var(--ink2);">{envolv} <span style="color:var(--muted);">({papel})</span></td>'
            f'<td class="r">{v / _facto_tot * 100:.1f}%</td></tr>'
        )

    # tabela: professores do campus e seus projetos
    prof_rows = ""
    for nome, v in sorted(prof_proj.items(), key=lambda x: -(len(x[1]["coord"]) + len(x[1]["membro"]))):
        papel = ""
        if v["coord"]:
            papel += '<span class="chip g">Coordenador</span>'
        if v["membro"]:
            papel += '<span class="chip b">Equipe</span>'
        pids = sorted(v["coord"] | v["membro"], key=lambda x: int(x) if str(x).isdigit() else 0)
        prof_rows += (f'<tr><td>{nome}</td><td>{papel}</td><td>{len(pids)}</td>'
                      f'<td style="color:var(--muted);font-size:12px;">{" · ".join("["+i+"]" for i in pids)}</td></tr>')

    divider = _divider(
        "Parte 4 · FACTO",
        "Projetos FACTO do campus Serra",
        f"Projetos geridos pela fundação FACTO/Conveniar com participação de professores do "
        f"campus Serra. {n_serra} dos {total_portal} projetos do portal envolvem ao menos um "
        f"docente da Serra (coordenação ou equipe), somando {_brl(f_orc)}.",
    )
    body = f"""
    <section class="section">
      <div class="eyebrow">Indicadores de gestão</div>
      <h2>Números dos projetos do campus no FACTO</h2>
      <p class="desc">Mesmos indicadores aplicados à FAPES, restritos aos {n_serra} projetos
      FACTO com participação de professores da Serra (identificados pelos CVs Lattes).</p>
      <div class="kpis" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr));">{g_cards}</div>
    </section>
    <section class="section">
      <div class="eyebrow">Natureza dos projetos</div>
      <h2>Ensino, pesquisa ou extensão</h2>
      <p class="desc">Classificação pelo campo oficial <b>"Tipo de Projeto"</b> do FACTO — mais
      confiável que a heurística por bolsa usada na FAPES.</p>
      <div class="card"><div class="bars">{nat_bars}</div>
        <div class="note-line">Barras = nº de projetos; valor = soma do valor aprovado.</div></div>
      <div class="card" style="margin-top:20px;"><h3>Valor aprovado por ano</h3>{facto_ano_chart}
        <div class="note-line">Valor dos projetos do campus por ano de início (eixo X = ano, eixo Y = R$).</div></div>
    </section>
    <section class="section">
      <div class="eyebrow">Os projetos</div>
      <h2>Projetos FACTO do campus Serra</h2>
      <p class="desc">Todos os {n_serra} projetos com participação de docente da Serra, por
      participação no valor (<b>% do total</b>, sem expor valores individuais).</p>
      <div class="card">
        <table><thead><tr><th>Projeto</th><th>Coordenador</th><th>Natureza</th><th>Prof. do campus</th><th class="r">% do total</th></tr></thead>
        <tbody>{proj_rows}</tbody></table>
      </div>
    </section>"""
    return divider + body


def _brl(v: float) -> str:
    if not v:
        return "R$ 0"
    if v >= 1_000_000:
        return f"R$ {v/1_000_000:.1f} mi".replace(".", ",")
    return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _faixa(v: float) -> str:
    """Faixa de valor (sem cifra exata) — usada em 'Orçamento por rubrica'."""
    v = v or 0
    for lim, rot in [(1e5, "≤ R$ 100 mil"), (5e5, "R$ 100–500 mil"), (1e6, "R$ 500 mil–1 mi"),
                     (5e6, "R$ 1–5 mi"), (2e7, "R$ 5–20 mi"), (5e7, "R$ 20–50 mi")]:
        if v <= lim:
            return rot
    return "> R$ 50 mi"


def _line_chart(anos: list[int], vals: list[float], fmt, color: str,
                grad_id: str, aria: str, sublabels: list[str] | None = None) -> str:
    """Gráfico de linha SVG inline genérico: X = ano, Y = valor (fmt)."""
    if not anos:
        return ""
    W, H = 880, 320
    ml, mr, mt, mb = 64, 24, 24, 48
    iw, ih = W - ml - mr, H - mt - mb
    vmax = max(vals) or 1
    n = len(anos)
    def x(i):
        return ml + (iw * i / (n - 1) if n > 1 else iw / 2)
    def y(v):
        return mt + ih - (v / vmax * ih)

    grid = ""
    for g in range(6):
        val = vmax * g / 5
        gy = y(val)
        grid += (f'<line x1="{ml}" y1="{gy:.1f}" x2="{W-mr}" y2="{gy:.1f}" '
                 f'stroke="var(--line)" stroke-width="1"/>'
                 f'<text x="{ml-10}" y="{gy+4:.1f}" text-anchor="end" '
                 f'font-size="11" fill="var(--muted)">{fmt(val)}</text>')

    pts = [(x(i), y(vals[i])) for i in range(n)]
    poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = (f'M {pts[0][0]:.1f},{mt+ih:.1f} L '
            + " L ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
            + f' L {pts[-1][0]:.1f},{mt+ih:.1f} Z')

    dots = ""
    for i, a in enumerate(anos):
        px, py = pts[i]
        sub = (f'<text x="{px:.1f}" y="{mt+ih+32:.1f}" text-anchor="middle" font-size="9" '
               f'fill="var(--muted)">{sublabels[i]}</text>') if sublabels else ""
        dots += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{color}" '
                 f'stroke="#fff" stroke-width="1.5"/>'
                 f'<text x="{px:.1f}" y="{py-12:.1f}" text-anchor="middle" font-size="10" '
                 f'font-weight="700" fill="{color}">{fmt(vals[i])}</text>'
                 f'<text x="{px:.1f}" y="{mt+ih+18:.1f}" text-anchor="middle" font-size="11" '
                 f'fill="var(--ink2)">{a}</text>{sub}')

    return (
        f'<div style="overflow-x:auto;"><svg viewBox="0 0 {W} {H}" '
        f'style="width:100%;min-width:620px;height:auto;font-family:var(--font);" '
        f'role="img" aria-label="{aria}">'
        f'<defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{color}" stop-opacity="0.18"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
        f'{grid}<path d="{area}" fill="url(#{grad_id})"/>'
        f'<polyline points="{poly}" fill="none" stroke="{color}" '
        f'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
        f'{dots}</svg></div>'
    )


def _multiline_chart(anos: list[int], series: list[dict], fmt, aria: str,
                     uid: str = "ml") -> str:
    """Multi-linha SVG inline com legenda clicável (toggle por série).

    series: [{"name": str, "color": str, "values": [..], "width": float?}]
    """
    if not anos or not series:
        return ""
    W, H = 880, 360
    ml, mr, mt, mb = 56, 24, 16, 44
    iw, ih = W - ml - mr, H - mt - mb
    vmax = max((v for s in series for v in s["values"]), default=1) or 1
    n = len(anos)
    def x(i):
        return ml + (iw * i / (n - 1) if n > 1 else iw / 2)
    def y(v):
        return mt + ih - (v / vmax * ih)

    grid = ""
    for g in range(6):
        val = vmax * g / 5
        gy = y(val)
        grid += (f'<line x1="{ml}" y1="{gy:.1f}" x2="{W-mr}" y2="{gy:.1f}" '
                 f'stroke="var(--line)" stroke-width="1"/>'
                 f'<text x="{ml-8}" y="{gy+4:.1f}" text-anchor="end" font-size="11" '
                 f'fill="var(--muted)">{fmt(val)}</text>')
    xlabels = "".join(
        f'<text x="{x(i):.1f}" y="{mt+ih+18:.1f}" text-anchor="middle" font-size="11" '
        f'fill="var(--ink2)">{a}</text>' for i, a in enumerate(anos))

    lines = ""
    for si, s in enumerate(series):
        pts = [(x(i), y(s["values"][i])) for i in range(n)]
        poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        w = s.get("width", 2)
        dots = "".join(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{s["color"]}" '
            f'stroke="#fff" stroke-width="1"/>' for px, py in pts)
        lines += (f'<g class="ser" data-i="{si}">'
                  f'<polyline points="{poly}" fill="none" stroke="{s["color"]}" '
                  f'stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round" '
                  f'opacity="0.92"/>{dots}</g>')

    legend = (f'<div class="ml-legend" style="display:flex;flex-wrap:wrap;gap:8px 12px;'
              f'margin-top:14px;">') + "".join(
        f'<button type="button" class="leg-item" data-i="{si}" '
        f'style="display:inline-flex;align-items:center;gap:6px;font-size:12px;'
        f'color:var(--ink2);background:var(--soft);border:1px solid var(--line);'
        f'border-radius:999px;padding:4px 11px;cursor:pointer;font-family:inherit;">'
        f'<span style="width:14px;height:3px;border-radius:2px;background:{s["color"]};'
        f'display:inline-block;"></span>{s["name"]}</button>'
        for si, s in enumerate(series)
    ) + '</div>'

    svg = (
        f'<div style="overflow-x:auto;"><svg viewBox="0 0 {W} {H}" '
        f'style="width:100%;min-width:640px;height:auto;font-family:var(--font);" '
        f'role="img" aria-label="{aria}">{grid}{xlabels}{lines}</svg></div>'
    )
    script = (
        f"<script>(function(){{var box=document.getElementById('{uid}');"
        f"box.querySelectorAll('.leg-item').forEach(function(b){{"
        f"b.addEventListener('click',function(){{var i=b.dataset.i,"
        f"g=box.querySelector('g.ser[data-i=\"'+i+'\"]');"
        f"var off=g.style.display==='none';g.style.display=off?'':'none';"
        f"b.style.opacity=off?'1':'0.4';"
        f"b.style.textDecoration=off?'none':'line-through';}});}});}})();</script>"
    )
    return f'<div id="{uid}" class="ml-chart">{svg}{legend}</div>{script}'


def _bolsa_familia(tipo: str | None) -> str:
    """Família da bolsa (BPIG, B-UnAC, ICT...) a partir do tipo_bolsa completo."""
    t = (tipo or "").upper()
    fams = [("B-UNAC", "B-UnAC"), ("BPIG", "BPIG"), ("ICJR", "ICJr"), ("ICT", "ICT"),
            ("ME", "ME"), ("EXT", "EXT"), ("DTI", "DTI"), ("AT-N", "AT"), ("BCO", "BCO"),
            ("BTU", "BTU"), ("BMO", "BMO"), ("TPQ", "TPq"), ("BPC", "BPC")]
    for pref, disp in fams:
        if t.startswith(pref):
            return disp
    return "Outros"


def _categoria_bolsa(tipo: str | None) -> str:
    """Classifica a natureza do projeto pela bolsa: ensino/pesquisa/extensão/etc."""
    t = (tipo or "").upper()
    if "UNAC" in t or t.startswith(("BTU", "BMO")):
        return "Ensino"
    if t.startswith("EXT"):
        return "Extensão"
    if t.startswith(("ICT", "ICJR", "ME", "DTI", "TPQ", "BPC", "PV")):
        return "Pesquisa"
    if t.startswith("BPIG"):
        return "Institucional/Governo"
    if t.startswith(("BCO", "AT-", "ORG", "AP-", "ETC")):
        return "Apoio/Gestão"
    return "Outros"


def projetos_section(with_research: int | None = None) -> str:
    """Seção executiva dos projetos FAPES do campus (ou '' se arquivo ausente)."""
    if not PROJETOS_FILE.exists():
        return ""
    from datetime import date as _date
    d = json.loads(PROJETOS_FILE.read_text())
    r = d["resumo"]
    tot = r["total_status_ou_prazo"]
    conc = r["concluidos"]
    and_ = r["em_andamento_por_status_e_prazo"]
    venc = r["status_em_andamento_prazo_encerrado"]
    allp = [p for lst in d["projetos"].values() for p in lst]

    # ---- indicadores de gestão ----
    npj = tot["quantidade_projetos"]
    orc = tot["orcamento_contratado_total"] or 1
    nb = tot["quantidade_bolsas_total"] or 1
    vb = tot["valor_bolsas_total"]
    _coord_orc = defaultdict(float)
    for p in allp:
        _coord_orc[p["coordenador_nome"]] += p.get("orcamento_contratado", 0) or 0
    n_coord = len(_coord_orc)
    top5 = sum(sorted(_coord_orc.values(), reverse=True)[:5])
    _durs = []
    for p in allp:
        try:
            _a = _date.fromisoformat(p["projeto_data_inicio_previsto"])
            _b = _date.fromisoformat(p["projeto_data_fim_previsto"])
            _m = (_b - _a).days / 30.0
            if 0 < _m < 120:
                _durs.append(_m)
        except Exception:
            pass
    dur_med = sum(_durs) / len(_durs) if _durs else 0
    kpi_gestao = [
        (f"R$ {orc/npj/1000:.0f} mil", "ticket médio por projeto", f"{npj} projetos"),
        (f"R$ {vb/nb/1000:.0f} mil", "valor médio por bolsa", f"{nb} bolsas"),
        (f"{nb/npj:.1f}", "bolsas por projeto", "média"),
        (str(n_coord), "coordenadores captando", f"{npj/n_coord:.1f} projetos cada"),
        (f"{round(vb/orc*100)}%", "do orçamento em bolsas", _brl(vb)),
        (f"{dur_med/12:.1f} anos", "duração média", f"{dur_med:.0f} meses"),
        (f"{round(top5/orc*100)}%", "nos top-5 coordenadores", "concentração de fomento"),
        (f"{venc['quantidade_projetos']}", "projetos com prazo vencido",
         f"{round(venc['quantidade_projetos']/npj*100)}% do total"),
        (f"{round(conc['quantidade_projetos']/npj*100)}%", "taxa de conclusão",
         f"{conc['quantidade_projetos']} concluídos"),
    ]
    if with_research:
        kpi_gestao.append(
            (_brl(vb / with_research), "em bolsas por aluno-pesquisa",
             f"{_brl(vb)} ÷ {with_research}"))
    gestao_cards = "".join(
        f'<div class="kpi"><div class="n" style="font-size:30px;">{n}</div>'
        f'<div class="u">{u}</div><div class="s">{s}</div></div>'
        for n, u, s in kpi_gestao
    )
    _aluno_txt = (f'<li><b>Bolsas por aluno-pesquisa</b> — total investido em bolsas dividido '
                  f'pelos {with_research} egressos com participação em pesquisa; aproxima o '
                  f'custo de formar um aluno pesquisador. <i>Cruza fomento com a graduação.</i></li>'
                  if with_research else "")
    explic = f"""
      <div class="card" style="margin-top:20px;">
        <h3>O que cada indicador significa</h3>
        <ul style="margin:0;padding-left:20px;font-size:14px;color:var(--ink2);line-height:1.7;">
          <li><b>Ticket médio por projeto</b> — orçamento total contratado ÷ nº de projetos.
          Mede o porte típico de um projeto FAPES no campus.</li>
          <li><b>Valor médio por bolsa</b> — valor total em bolsas ÷ nº de bolsas. É o aporte
          médio acumulado por bolsa (não o valor mensal).</li>
          <li><b>Bolsas por projeto</b> — nº de bolsas ÷ nº de projetos. Indica quantas pessoas,
          em média, cada projeto coloca para trabalhar.</li>
          <li><b>Coordenadores captando</b> — docentes distintos que coordenam ao menos um
          projeto FAPES. Mede a <i>capilaridade</i> do fomento no corpo docente.</li>
          <li><b>% do orçamento em bolsas</b> — fatia do recurso destinada a pessoas (bolsas)
          versus custeio/capital. Quanto maior, mais o dinheiro vira mão de obra.</li>
          <li><b>Duração média</b> — tempo médio entre início e fim previstos dos projetos.
          Mostra o horizonte típico de execução.</li>
          <li><b>Concentração top-5</b> — % do orçamento sob os 5 maiores coordenadores. Alto =
          fomento concentrado em poucos grupos (risco de dependência).</li>
          <li><b>Projetos com prazo vencido</b> — em situação "Em Andamento" mas com data-fim já
          passada. Sinaliza atraso ou pendência de encerramento — atenção da gestão.</li>
          <li><b>Taxa de conclusão</b> — % de projetos já concluídos/encerrados sobre o total.
          Indicador de execução e entrega.</li>
          {_aluno_txt}
        </ul>
      </div>"""
    gestao_strip = f"""
    <section class="section">
      <div class="eyebrow">Indicadores de gestão</div>
      <h2>Números do fomento</h2>
      <p class="desc">Indicadores derivados dos {npj} projetos FAPES — porte, capilaridade,
      concentração e execução.</p>
      <div class="kpis" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr));">{gestao_cards}</div>
      {explic}
    </section>"""

    # KPIs
    kpis = f"""
    <section class="section"><div class="kpis">
      <div class="kpi"><div class="n">{tot['quantidade_projetos']}</div>
        <div class="u">projetos FAPES</div><div class="s">no campus Serra</div></div>
      <div class="kpi"><div class="n">{_brl(tot['orcamento_contratado_total'])}</div>
        <div class="u">orçamento contratado</div><div class="s">total captado</div></div>
      <div class="kpi"><div class="n">{_brl(tot['valor_bolsas_total'])}</div>
        <div class="u">em bolsas</div><div class="s">{round(tot['valor_bolsas_total']/tot['orcamento_contratado_total']*100)}% do orçamento</div></div>
      <div class="kpi"><div class="n">{tot['quantidade_bolsas_total']}</div>
        <div class="u">bolsas contratadas</div><div class="s">nos projetos</div></div>
    </div></section>"""

    # status bars
    smax = max(conc['quantidade_projetos'], and_['quantidade_projetos'], venc['quantidade_projetos'], 1)
    def _bar(lbl, v, color, sub):
        w = v / smax * 100
        return (f'<div class="brow"><span class="bl">{lbl}</span>'
                f'<div class="btrack"><div class="bfill" style="width:{max(w,2):.1f}%;background:{color};"></div></div>'
                f'<span class="bv">{v} · {sub}</span></div>')
    status = (
        _bar("Concluídos", conc['quantidade_projetos'], "var(--brand)", _brl(conc['orcamento_contratado_total']))
        + _bar("Em andamento (no prazo)", and_['quantidade_projetos'], "var(--blue)", _brl(and_['orcamento_contratado_total']))
        + _bar("Em andamento (prazo vencido)", venc['quantidade_projetos'], "var(--amber)", _brl(venc['orcamento_contratado_total']))
    )

    # top coordenadores
    coord = defaultdict(lambda: [0, 0.0, 0])
    for p in allp:
        c = coord[p["coordenador_nome"]]
        c[0] += 1
        c[1] += p.get("orcamento_contratado", 0) or 0
        c[2] += p.get("quantidade_bolsas", 0) or 0
    _coord_tot = sum(c[1] for c in coord.values()) or 1
    top = sorted(coord.items(), key=lambda x: -x[1][1])[:8]
    crows = "".join(
        f'<tr><td>{nome}</td><td>{n}</td><td class="r">{orc / _coord_tot * 100:.1f}%</td><td>{b}</td></tr>'
        for nome, (n, orc, b) in top
    )

    # por ano: orçamento + bolsas alocadas — gráficos de linha SVG inline
    ano = defaultdict(lambda: [0, 0.0, 0])  # ano → [n_proj, orcamento, bolsas]
    for p in allp:
        a = ano[p.get("ano")]
        a[0] += 1
        a[1] += p.get("orcamento_contratado", 0) or 0
        a[2] += p.get("quantidade_bolsas", 0) or 0
    anos = sorted(a for a in ano if a)
    ano_chart = _line_chart(
        anos, [ano[a][1] for a in anos], _brl, "var(--brand)", "gano",
        "Orçamento FAPES contratado por ano",
        sublabels=[f"{ano[a][0]}p" for a in anos])
    bolsa_chart = _line_chart(
        anos, [ano[a][2] for a in anos], lambda v: f"{v:.0f}", "var(--blue)", "gbol",
        "Bolsas alocadas por ano",
        sublabels=[f"{ano[a][0]}p" for a in anos])

    # bolsas por família × ano (multi-linha)
    fam_ano: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    fam_total: dict[str, float] = defaultdict(float)
    for p in allp:
        a = p.get("ano")
        if not a:
            continue
        for b in (p.get("bolsas") or []):
            fam = _bolsa_familia(b.get("tipo_bolsa"))
            q = b.get("quantidade", 0) or 0
            fam_ano[fam][a] += q
            fam_total[fam] += q
    _PAL = ["var(--brand)", "var(--blue)", "var(--amber)", "var(--rose)",
            "#6a4c93", "#1f9d57", "var(--muted)"]
    top_fams = [f for f, _ in sorted(fam_total.items(), key=lambda x: -x[1])[:6]]
    fam_series = [
        {"name": f, "color": _PAL[i % len(_PAL)],
         "values": [fam_ano[f].get(a, 0) for a in anos]}
        for i, f in enumerate(top_fams)
    ]
    bolsa_tipo_chart = _multiline_chart(
        anos, fam_series, lambda v: f"{v:.0f}",
        "Bolsas alocadas por tipo ao longo dos anos", uid="chart-bolsa-tipo")

    # projetos por ano × status (multi-linha)
    _ST = [("concluidos", "Concluídos", "var(--brand)"),
           ("em_andamento", "Em andamento (no prazo)", "var(--blue)"),
           ("status_em_andamento_prazo_encerrado", "Prazo vencido", "var(--amber)")]
    st_ano: dict[str, dict[int, int]] = {k: defaultdict(int) for k, _, _ in _ST}
    for key, _, _ in _ST:
        for p in d["projetos"].get(key, []):
            if p.get("ano"):
                st_ano[key][p["ano"]] += 1
    status_series = [
        {"name": lbl, "color": col, "values": [st_ano[key].get(a, 0) for a in anos]}
        for key, lbl, col in _ST
    ]
    status_chart = _multiline_chart(
        anos, status_series, lambda v: f"{v:.0f}",
        "Projetos por ano e status", uid="chart-status-ano")

    # categorização por natureza (ensino/pesquisa/extensão) via tipo de bolsa
    cat = defaultdict(lambda: [0, 0.0, 0])  # categoria → [n_proj, orcamento, bolsas]
    cat_ano: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for p in allp:
        val_by = defaultdict(float)
        for b in (p.get("bolsas") or []):
            val_by[_categoria_bolsa(b.get("tipo_bolsa"))] += b.get("valor_total", 0) or 0
        c = max(val_by, key=val_by.get) if val_by else "Sem bolsa (custeio/equipamento)"
        cat[c][0] += 1
        cat[c][1] += p.get("orcamento_contratado", 0) or 0
        cat[c][2] += p.get("quantidade_bolsas", 0) or 0
        if p.get("ano"):
            cat_ano[c][p["ano"]] += 1
    CATCOL = {"Ensino": "var(--blue)", "Pesquisa": "var(--brand)", "Extensão": "var(--amber)",
              "Institucional/Governo": "#6a4c93", "Apoio/Gestão": "var(--muted)",
              "Outros": "var(--line2)", "Sem bolsa (custeio/equipamento)": "#b5455f"}
    cat_series = [
        {"name": k if "Sem bolsa" not in k else "Sem bolsa", "color": CATCOL.get(k, "var(--muted)"),
         "values": [cat_ano[k].get(a, 0) for a in anos]}
        for k, _ in sorted(cat.items(), key=lambda x: -x[1][0])
    ]
    cat_chart = _multiline_chart(
        anos, cat_series, lambda v: f"{v:.0f}",
        "Projetos por ano e natureza", uid="chart-cat-ano")
    cat_total_orc = sum(v[1] for v in cat.values()) or 1
    cat_rows = "".join(
        f'<tr><td><span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
        f'background:{CATCOL.get(k,"var(--muted)")};margin-right:7px;"></span>{k}</td>'
        f'<td>{v[0]}</td><td class="r">{_brl(v[1])}</td>'
        f'<td class="r">{round(v[1]/cat_total_orc*100)}%</td><td>{v[2]}</td></tr>'
        for k, v in sorted(cat.items(), key=lambda x: -x[1][1])
    )
    inst_pct = round(cat.get("Institucional/Governo", [0, 0, 0])[1] / cat_total_orc * 100)
    pesquisa_n = cat.get("Pesquisa", [0, 0, 0])[0]

    # orçamento por rubrica (descricao_categoria) — decompõe todo o orçamento
    rub = defaultdict(float)
    rub_ano: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for p in allp:
        a = p.get("ano")
        for r in (p.get("rubricas") or []):
            k = r.get("descricao_categoria") or "Outros"
            v = r.get("valor", 0) or 0
            rub[k] += v
            if a:
                rub_ano[k][a] += v
    rub_tot = sum(rub.values()) or 1
    rmax = max(rub.values()) if rub else 1
    RCOL = {"Bolsas": "var(--brand)", "Equipamentos e Material Permanente": "var(--blue)",
            "Outros Serviços de Terceiros": "#6a4c93", "Material de Consumo": "var(--amber)",
            "Diárias": "var(--rose)", "Passagens": "#1f9d57",
            "Hospedagem e Alimentação": "var(--muted)"}
    rub_bars = "".join(
        f'<div class="brow"><span class="bl">{k}</span>'
        f'<div class="btrack"><div class="bfill" style="width:{max(v/rmax*100,1.5):.1f}%;'
        f'background:{RCOL.get(k,"var(--muted)")};"></div></div>'
        f'<span class="bv">{_faixa(v)} · {round(v/rub_tot*100,1)}%</span></div>'
        for k, v in sorted(rub.items(), key=lambda x: -x[1])
    )
    rub_series = [
        {"name": k if len(k) < 22 else k[:20] + "…", "color": RCOL.get(k, "var(--muted)"),
         "values": [rub_ano[k].get(a, 0) for a in anos]}
        for k, _ in sorted(rub.items(), key=lambda x: -x[1])
    ]
    rub_chart = _multiline_chart(
        anos, rub_series, _faixa, "Valor por rubrica ao longo dos anos (faixas)", uid="chart-rubrica-ano")

    divider = _divider(
        "Parte 3 · Projetos",
        "Projetos de pesquisa FAPES",
        f"O fomento que sustenta a pesquisa do campus: {tot['quantidade_projetos']} projetos "
        f"FAPES, {_brl(tot['orcamento_contratado_total'])} contratados e "
        f"{tot['quantidade_bolsas_total']} bolsas.",
    )
    body = f"""
    {kpis}
    {gestao_strip}
    <section class="section">
      <div class="eyebrow">Situação dos projetos</div>
      <h2>Concluídos e em andamento</h2>
      <p class="desc">Distribuição dos {tot['quantidade_projetos']} projetos por situação e
      prazo. Atenção aos <b>{venc['quantidade_projetos']}</b> em andamento com prazo já vencido
      ({_brl(venc['orcamento_contratado_total'])}).</p>
      <div class="card"><div class="bars">{status}</div>
        <div class="note-line">Valores = orçamento contratado por grupo. Prazo vencido: situação
        "Em Andamento" com data-fim anterior a {d['metadata'].get('data_referencia','hoje')}.</div></div>
      <div class="card" style="margin-top:20px;">
        <h3>Projetos por ano e status</h3>
        {status_chart}
        <div class="note-line">Quantidade de projetos por ano de início, separados por situação
        (eixo X = ano, eixo Y = projetos). <b>Clique na legenda</b> para filtrar.</div>
      </div>
    </section>
    <section class="section">
      <div class="eyebrow">Liderança de captação</div>
      <h2>Coordenadores por orçamento captado</h2>
      <p class="desc">Top 8 coordenadores por participação no orçamento FAPES do campus — em
      <b>% do total contratado</b>, sem expor valores individuais.</p>
      <div class="card">
        <table><thead><tr><th>Coordenador</th><th>Projetos</th><th class="r">% do total</th><th>Bolsas</th></tr></thead>
        <tbody>{crows}</tbody></table>
      </div>
    </section>
    <section class="section">
      <div class="eyebrow">Natureza dos projetos</div>
      <h2>Ensino, pesquisa ou extensão</h2>
      <p class="desc">Categorização por tipo de bolsa do projeto (ex.: B-UnAC = ensino,
      ICT/ME/DTI = pesquisa, EXT = extensão, BPIG = projeto institucional de governo).
      Cada projeto entra na categoria que concentra o maior valor em bolsas.</p>
      <div class="card">
        <table><thead><tr><th>Natureza</th><th>Projetos</th><th class="r">Orçamento</th><th class="r">% orç.</th><th>Bolsas</th></tr></thead>
        <tbody>{cat_rows}</tbody></table>
        <p style="font-size:14px;color:var(--ink2);margin-top:18px;">
          <b>Leitura.</b> Em valor, o fomento concentra-se em <b>projetos institucionais de
          governo</b> (BPIG, ~{inst_pct}% do orçamento) e em <b>ensino</b> (Universidade Aberta
          Capixaba — B-UnAC), que juntos respondem pela maior parte dos recursos. A <b>pesquisa</b>,
          porém, é a natureza com <b>mais projetos</b> ({pesquisa_n}), ainda que com orçamento médio menor — o
          padrão típico da iniciação científica e tecnológica (ICT, ME, DTI). A <b>extensão</b>
          (EXT) tem presença pequena tanto em número quanto em valor.
        </p>
        <p style="font-size:13px;color:var(--muted);margin-top:12px;">
          <b>Como foi classificado.</b> A natureza de cada projeto é inferida pelo <b>tipo de
          bolsa</b> que ele contrata — não pela classificação oficial do edital. Exemplos:
          <b>B-UnAC → Ensino</b>; <b>ICT, ME, DTI, TPq → Pesquisa</b>; <b>EXT → Extensão</b>;
          <b>BPIG → Institucional/Governo</b> (não é o tripé clássico ensino-pesquisa-extensão).
          Quando um projeto mistura bolsas de naturezas diferentes, ele entra na categoria que
          concentra o <b>maior valor</b> em bolsas. <b>"Sem bolsa (custeio/equipamento)"</b> são
          projetos que não contratam bolsista nenhum — o recurso vai para material, equipamento,
          diárias e serviços (ex.: "Robótica para todos", "CurSol PRO 4.0"). Por ser uma
          heurística, os números servem de panorama, não de classificação formal.
        </p>
      </div>
      <div class="card" style="margin-top:20px;">
        <h3>Projetos por ano e natureza</h3>
        {cat_chart}
        <div class="note-line">Quantidade de projetos por ano de início, separados por natureza
        (eixo X = ano, eixo Y = projetos). <b>Clique na legenda</b> para filtrar.</div>
      </div>
    </section>
    <section class="section">
      <div class="eyebrow">Evolução</div>
      <h2>Captação por ano</h2>
      <p class="desc">Orçamento FAPES contratado por ano de início do projeto (eixo X = ano,
      eixo Y = valor). Rótulo "Np" = número de projetos no ano.</p>
      <div class="card">{ano_chart}</div>
    </section>
    <section class="section">
      <div class="eyebrow">Bolsistas</div>
      <h2>Bolsas alocadas ao longo dos anos</h2>
      <p class="desc">Número de bolsas contratadas nos projetos por ano de início
      (eixo X = ano, eixo Y = bolsas).</p>
      <div class="card">{bolsa_chart}</div>
      <div class="card" style="margin-top:20px;">
        <h3>Por tipo de bolsa (BPIG, B-UnAC, ICT…)</h3>
        {bolsa_tipo_chart}
        <div class="note-line">Uma linha por família de bolsa (top 6 por volume). Famílias
        agrupam os níveis (ex.: "B-UnAC-VI - Antigo" → B-UnAC).
        <b>Clique nos rótulos da legenda</b> para mostrar/ocultar cada tipo no gráfico.</div>
      </div>
    </section>
    <section class="section">
      <div class="eyebrow">Composição do orçamento</div>
      <h2>Orçamento por rubrica</h2>
      <p class="desc">Em que o recurso FAPES é aplicado. As <b>bolsas</b> concentram a maior
      fatia; o restante vai para equipamento, serviços, material, diárias e passagens.</p>
      <div class="card"><div class="bars">{rub_bars}</div>
        <div class="note-line">Soma de todas as rubricas dos {tot['quantidade_projetos']} projetos.
        Percentual sobre o total executado em rubricas.</div></div>
      <div class="card" style="margin-top:20px;">
        <h3>Valor por rubrica ao longo dos anos</h3>
        {rub_chart}
        <div class="note-line">Valor de cada rubrica por ano de início do projeto
        (eixo X = ano, eixo Y = R$). <b>Clique na legenda</b> para filtrar.</div>
      </div>
    </section>
    <section class="section"><div class="callout">
      <div class="k">Mensagem central</div>
      <h2>A pesquisa do campus move dezenas de milhões</h2>
      <p>{tot['quantidade_projetos']} projetos FAPES somam {_brl(tot['orcamento_contratado_total'])}
      contratados e {tot['quantidade_bolsas_total']} bolsas — a infraestrutura de fomento que
      sustenta a iniciação científica da graduação e a pós-graduação.</p>
    </div></section>"""
    return divider + body


def _body(html: str) -> str:
    """Extrai as seções (entre o fim do <header> e o rodapé) de um relatório."""
    a = html.index("</header>") + len("</header>")
    b = html.index('<div class="foot">')
    return html[a:b]


def _divider(eyebrow: str, title: str, lead: str) -> str:
    return f"""
    <section class="section" style="margin-top:64px;">
      <div style="border-top:3px solid var(--brand);padding-top:28px;">
        <div class="eyebrow">{eyebrow}</div>
        <h2 style="font-size:32px;">{title}</h2>
        <p class="desc" style="font-size:16px;max-width:70ch;">{lead}</p>
      </div>
    </section>"""


def build(grad_payload: dict, ppbase: dict, generated_at: str) -> str:
    grad_html = EX.build(grad_payload, generated_at)
    ppcomp_html = PPB.render(ppbase)          # Parte 2 = base completa (269 discentes)

    grad_body = _body(grad_html)
    ppcomp_body = _body(ppcomp_html)

    s = grad_payload["stats"]
    sems = grad_payload.get("semesters") or []
    period = (f"{sems[0].replace('_', '.')} – {sems[-1].replace('_', '.')}"
              if sems else "")
    total = s["total"]
    pct = s["pct_research"]
    n_egr = ppbase["total"]                   # discentes do mestrado (base completa)
    defendidos = ppbase["defendidos"]
    pipeline = ppbase.get("pipeline", {}).get("total", 0)  # vindos da graduação Serra

    # resumo de projetos FAPES (para o cabeçalho)
    proj_meta = ""
    if PROJETOS_FILE.exists():
        _pr = json.loads(PROJETOS_FILE.read_text())["resumo"]["total_status_ou_prazo"]
        proj_meta = (f'<span>Projetos FAPES: <b>{_pr["quantidade_projetos"]}</b> · '
                     f'<b>{_brl(_pr["orcamento_contratado_total"])}</b></span>')

    css = EX.CSS + "\n/* ---- ppcomp base ---- */\n" + PPB.CSS

    hero = f"""
    <header class="hero">
      <div class="kicker">● IFES Serra · Pesquisa na Formação</div>
      <h1>Da iniciação científica ao mestrado: a trajetória de pesquisa no IFES Serra</h1>
      <p class="lede">Relatório institucional — a participação em pesquisa dos
      <b>{total} egressos</b> da graduação e a trajetória dos <b>{n_egr} discentes</b>
      do mestrado PPComp.</p>
      <div class="meta">
        <span>Graduação: <b>{pct}%</b> com pesquisa</span>
        <span>Período: <b>{period}</b></span>
        <span>Mestrado PPComp: <b>{n_egr}</b> discentes · <b>{defendidos}</b> defenderam</span>
        <span>Pipeline interno: <b>{pipeline}</b> egressos ingressaram no mestrado</span>
        {proj_meta}
      </div>
    </header>"""

    div1 = _divider(
        "Parte 1 · Graduação",
        "Pesquisa na graduação",
        f"Sistemas de Informação e Engenharia de Controle e Automação: {total} egressos, "
        f"participação em iniciação científica, cotas e tempo de formação.",
    )
    div2 = _divider(
        "Parte 2 · Mestrado",
        "O mestrado PPComp",
        f"Base completa de {n_egr} discentes do PPComp: situação acadêmica, coortes, tempo até a "
        f"defesa, evasão, carga de orientação e o pipeline da própria graduação do campus.",
    )
    projetos_body = projetos_section(with_research=s.get("with_research"))
    facto_body = facto_section()
    analises_body = analises_section(s, ppbase)

    foot = f"""
    <div class="foot">
      <span>Relatório institucional · Pesquisa na Formação — IFES Serra</span>
      <span>Gerado em {generated_at} · graduação {total} egressos · mestrado {n_egr} egressos</span>
    </div>"""

    # --- tempo médio de formação por curso (semestres do ingresso à formatura) ---
    gt = s["graduation_time"]
    _by_curso = gt.get("by_curso", {})
    _CURSOS_TEMPO = [
        ("Sistemas de Informação", "BSI", 8, "4 anos"),
        ("Engenharia de Controle e Automação", "ECA", 12, "6 anos"),
    ]
    _tempo_cards = ""
    for _cnome, _sigla, _prev, _anos in _CURSOS_TEMPO:
        _st = _by_curso.get(_cnome, {})
        _m = _st.get("mean")
        if _m is None:
            continue
        _atraso = round(_m - _prev, 1)
        _atr_txt = (f"atraso médio +{_atraso} sem" if _atraso > 0
                    else (f"{_atraso} sem" if _atraso < 0 else "no prazo previsto"))
        _tempo_cards += (
            f'<div class="kpi"><div class="n">{_m:.1f}</div>'
            f'<div class="u">semestres em média · {_sigla}</div>'
            f'<div class="s">previsto {_prev} sem ({_anos}) · {_atr_txt} · n={_st.get("n", 0)}</div></div>'
        )
    _ov_mean = gt.get("overall", {}).get("mean")
    _n_tempo = gt.get("overall", {}).get("n", 0)
    _n_excl = total - _n_tempo
    _ov_txt = (f'Média geral dos dois cursos: <b>{_ov_mean:.1f} semestres</b> '
               f'({_ov_mean / 2:.1f} anos). ' if _ov_mean else "")
    _cov_note = (
        f'<div class="note-line">{_ov_txt}Base do cálculo: <b>{_n_tempo} de {total}</b> egressos '
        f'com duração calculável. <b>{_n_excl}</b> ficam de fora porque a matrícula indica ingresso '
        f'no <b>mesmo semestre</b> da formatura (duração não mensurável — provável reingresso ou '
        f'matrícula nova). Esses {_n_excl} seguem contando no total e na divisão por forma de ingresso, '
        f'só não entram na média de tempo.</div>'
    )
    tempo_formacao = (f"""
    <section class="section">
      <div class="eyebrow">Tempo de formação</div>
      <h2>Quantos semestres até a formatura</h2>
      <p class="desc">Média de semestres do ingresso à formatura, por curso, ante a duração
      prevista no currículo — BSI: 8 semestres (4 anos) · ECA: 12 semestres (6 anos).</p>
      <div class="kpis" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr));">{_tempo_cards}</div>
      {_cov_note}
    </section>""" if _tempo_cards else "")

    # ---------- blocos didáticos das Partes 1 e 2 ----------
    _si_m = _by_curso.get("Sistemas de Informação", {}).get("mean")
    _eca_m = _by_curso.get("Engenharia de Controle e Automação", {}).get("mean")
    _si_txt = f"SI ~{_si_m:.0f} sem (previsto 8)" if _si_m else "SI"
    _eca_txt = f"ECA ~{_eca_m:.0f} sem (previsto 12)" if _eca_m else "ECA"
    _ger_txt = f"média geral ~{_ov_mean:.0f} semestres" if _ov_mean else "média geral"
    bloco_tempo = bloco_didatico({
        "titulo": "Tempo de formação",
        "analisa": "Quanto tempo o estudante leva do <b>ingresso à formatura</b>, em cada curso, "
                   "comparado à <b>duração prevista</b> no currículo.",
        "importa": "O tempo de formação conversa com <b>permanência, evasão, custo e eficiência</b> "
                   "do curso — e é insumo direto para a gestão acadêmica planejar apoio ao estudante.",
        "mostram": f"{_si_txt}; {_eca_txt}; {_ger_txt}. Cada curso é lido na <b>própria régua</b>: "
                   "comparar SI e ECA diretamente não faz sentido (durações diferentes).",
        "interpretar": "Algum atraso em relação ao previsto é <b>comum e multifatorial</b> "
                       "(trabalho, reprovações, estágio, TCC). É um retrato de percurso, não de mérito.",
        "atencao": "os dados <b>não dizem</b> se a participação em pesquisa acelera ou atrasa a "
                   "formatura — isso exigiria comparar quem fez e quem não fez IC, o que esta seção "
                   "não faz. Não inferir causa.",
        "cuidados": [
            "<b>SI ≠ ECA</b> (diurno 4 anos × noturno 6 anos) — réguas distintas, nunca comparar.",
            "Ingresso é <b>inferido da matrícula</b>; alguns egressos ficam fora da média (reingresso).",
            "Atraso levemente negativo é <b>plausível</b> (aproveitamento/reingresso), não erro.",
        ],
        "pesquisadores": "Saber o tempo típico do orientando ajuda a <b>dimensionar projetos</b> e "
                         "prazos de IC compatíveis com a jornada do curso.",
        "professores": "Tempo longo concentrado em certas fases pode sinalizar <b>gargalos "
                       "curriculares</b> que valem investigação — não culpa do estudante.",
        "estudantes": "Planeje sua jornada: a IC <b>não precisa atrasar</b> a formatura se bem "
                      "encaixada no semestre — e agrega bolsa e currículo no caminho.",
        "central": "Cada curso tem sua <b>régua própria</b> de tempo; o dado serve para gerir "
                   "permanência e apoio, não para ranquear estudantes ou cursos.",
        "acoes": [
            "<b>Gestão:</b> investigar gargalos por fase do curso; apoio a quem atrasa.",
            "<b>Cursos:</b> integrar a IC ao fluxo curricular para não competir com disciplinas.",
            "<b>Estudantes:</b> conversar com a coordenação sobre encaixar IC sem estender o curso.",
        ],
    })
    bloco_cotas = bloco_didatico({
        "titulo": "Cotas e inclusão na pesquisa",
        "analisa": "Se estudantes <b>cotistas</b> chegam à pesquisa e às <b>bolsas</b> na mesma "
                   "medida — ou seja, se a pesquisa também é via de inclusão.",
        "importa": "Pesquisa e bolsa são poderosos vetores de <b>permanência e equidade</b> para "
                   "grupos historicamente sub-representados; a cota no ingresso só se completa se "
                   "alcançar também a formação científica.",
        "mostram": "Os dados indicam que a <b>FAPES destina a maior parte de suas bolsas a "
                   "cotistas</b>, enquanto a Ifes distribui de forma mais equilibrada — sinal de que "
                   "a pesquisa <b>está</b> alcançando os cotistas, não só o ingresso.",
        "evidencia": "presença expressiva de cotistas entre os bolsistas de pesquisa (ver seção de financiamento).",
        "interpretar": "É um indício de que a política de cotas <b>transborda do acesso para a "
                       "formação em pesquisa</b> — um dos melhores caminhos de inclusão real.",
        "atencao": "<b>presença não é igualdade plena</b>: para afirmar equidade, é preciso comparar "
                   "a proporção de cotistas na pesquisa com a proporção no corpo discente — não feito aqui.",
        "cuidados": [
            "Critérios de reserva de vaga <b>se sobrepõem</b> (um aluno pode atender a vários).",
            "Participação por <b>autodeclaração</b> e casamento por nome — subestima.",
            "Recortes por grupo têm <b>amostra menor</b> — ler com cautela.",
        ],
        "pesquisadores": "Acolher cotistas em projetos <b>amplia o repertório de talentos</b> e "
                         "cumpre a missão social da instituição.",
        "professores": "A IC pode ser uma <b>ferramenta de permanência</b> para o estudante "
                       "cotista — vínculo, renda e propósito.",
        "estudantes": "Se você entrou por cota: <b>pesquisa e bolsa são para você também</b> — e os "
                      "dados mostram colegas cotistas já nesse caminho.",
        "central": "A pesquisa do campus está funcionando como <b>via de inclusão</b>: cotistas "
                   "chegam à iniciação científica e às bolsas, não só à matrícula.",
        "acoes": [
            "<b>Gestão:</b> monitorar a participação de cotistas na IC vs sua presença no corpo discente.",
            "<b>Editais:</b> reservar/priorizar bolsas de IC com recorte social.",
            "<b>Cursos:</b> divulgar ativamente a IC entre estudantes cotistas.",
        ],
    })
    bloco_mestrado = bloco_didatico({
        "titulo": "Mestrado PPComp — permanência, tempo e desfecho",
        "analisa": f"A trajetória dos <b>{n_egr} discentes</b> do mestrado PPComp: quantos defendem, "
                   "em quanto tempo, quantos evadem e quantos vieram da própria graduação do campus.",
        "importa": "O mestrado é o <b>topo da formação em pesquisa</b> do campus e o destino natural "
                   "de parte dos egressos da graduação — fecha o ciclo IC → pós-graduação.",
        "mostram": f"<b>{defendidos}</b> defesas entre os {n_egr} discentes; <b>{pipeline}</b> "
                   "vieram da própria graduação do campus (pipeline interno); a maioria defende em "
                   "torno de <b>2 anos</b> (prazo regulamentar de 24 meses). A evasão (cancelamentos "
                   "e trancamentos) existe e merece atenção.",
        "evidencia": f"{defendidos}/{n_egr} defenderam; {pipeline} via pipeline interno; mediana ~2 anos.",
        "interpretar": "Defesa em ~2 anos indica <b>aderência ao prazo</b>; o pipeline interno mostra "
                       "que a graduação <b>alimenta</b> o mestrado. A evasão é o ponto a vigiar.",
        "atencao": "a evasão tem <b>causas múltiplas</b> (trabalho, orientação, vida pessoal, "
                   "mercado) — não atribuível a um único fator nem ao programa isoladamente.",
        "cuidados": [
            "<b>Datas mistas</b> na base (sentinela 1905 inválida foi descartada do tempo).",
            "Coortes <b>recentes</b> têm muitos ativos (ainda sem desfecho) — não comparar com antigas.",
            "Orientador registrado em <b>nome curto</b>; pipeline casado por nome (sem acento).",
        ],
        "pesquisadores": "Acompanhar <b>evasão e tempo até a defesa</b> ajuda a calibrar seleção, "
                         "orientação e oferta de bolsas.",
        "professores": "Integrar graduação e mestrado (projetos conjuntos, convites a egressos) "
                       "<b>fortalece o pipeline interno</b>.",
        "estudantes": f"O mestrado da casa é uma <b>continuidade natural</b> da IC: {pipeline} "
                      "colegas da graduação do campus já fizeram essa transição.",
        "central": "O PPComp converte a formação em pesquisa da graduação em <b>titulação de "
                   "mestrado</b>, com prazo aderente — a <b>evasão</b> é o principal ponto a monitorar.",
        "acoes": [
            "<b>Gestão/Programa:</b> monitorar evasão por coorte e criar apoio a discente em risco.",
            "<b>Cursos:</b> fortalecer a ponte graduação → mestrado (divulgação, projetos conjuntos).",
            "<b>Orientadores:</b> acompanhamento próximo nos primeiros 12 meses (fase de maior evasão).",
        ],
    })

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pesquisa na Formação — Relatório Institucional — IFES Serra {period}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{css}{MOBILE_CSS}</style>
</head><body>
<div id="exp-banner" style="background:#b5455f;color:#fff;padding:10px 16px;font-weight:600;font-size:13.5px;text-align:center;position:sticky;top:0;z-index:9999;box-shadow:0 2px 6px rgba(0,0,0,.2);font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">⚠️ Estudo experimental em condução — os dados são preliminares e podem ser modificados. Não usar como fonte da verdade.</div>
<div class="page">
{hero}
{div1}
{tempo_formacao}
{bloco_tempo}
{grad_body}
{bloco_cotas}
{div2}
{ppcomp_body}
{bloco_mestrado}
{projetos_body}
{facto_body}
{analises_body}
{foot}
</div></body></html>"""




def _funnel_svg(estagios: list[tuple], total: int) -> str:
    """Desenho de funil em SVG: trapézios à esquerda, rótulos à direita."""
    if not estagios or not total:
        return ""
    n = len(estagios)
    W, H = 820, 104 * n + 16
    mt, gap = 12, 28
    bh = (H - mt - gap * (n - 1) - 8) / n
    funnel_w = 440          # área do funil
    label_x = funnel_w + 36  # início dos rótulos
    cx = funnel_w / 2
    vals = [v for _, v, _ in estagios]

    def hw(v):
        return max(funnel_w * v / total / 2, 10)

    out = ""
    y = mt
    for idx, (lbl, v, col) in enumerate(estagios):
        top = hw(v)
        bot = hw(vals[idx + 1]) if idx + 1 < n else max(top * 0.5, 10)
        pct = v / total * 100
        cy = y + bh / 2
        # trapézio
        out += (f'<path d="M {cx-top:.1f},{y:.1f} L {cx+top:.1f},{y:.1f} '
                f'L {cx+bot:.1f},{y+bh:.1f} L {cx-bot:.1f},{y+bh:.1f} Z" '
                f'fill="{col}" opacity="0.92"/>')
        # valor + % dentro da banda quando há largura
        if top > 60:
            out += (f'<text x="{cx:.1f}" y="{cy-2:.1f}" text-anchor="middle" '
                    f'fill="#fff" font-size="16" font-weight="800">{v}</text>'
                    f'<text x="{cx:.1f}" y="{cy+16:.1f}" text-anchor="middle" '
                    f'fill="#fff" font-size="12" font-weight="600" opacity="0.95">{pct:.0f}%</text>')
        elif top > 24:
            out += (f'<text x="{cx:.1f}" y="{cy+5:.1f}" text-anchor="middle" '
                    f'fill="#fff" font-size="13" font-weight="800">{pct:.0f}%</text>')
        # conector + rótulo à direita (sempre visível)
        out += (f'<line x1="{cx+top:.1f}" y1="{cy:.1f}" x2="{label_x-10:.1f}" y2="{cy:.1f}" '
                f'stroke="{col}" stroke-width="1.5" opacity="0.5"/>'
                f'<rect x="{label_x:.1f}" y="{cy-9:.1f}" width="13" height="13" rx="3" fill="{col}"/>'
                f'<text x="{label_x+20:.1f}" y="{cy-2:.1f}" font-size="14" font-weight="700" '
                f'fill="var(--ink)">{lbl}</text>'
                f'<text x="{label_x+20:.1f}" y="{cy+15:.1f}" font-size="12.5" '
                f'fill="var(--muted)">{v} egressos · {pct:.0f}% do total</text>')
        # queda entre etapas — explicada na própria figura
        if idx + 1 < n:
            nxt = vals[idx + 1]
            drop = round((1 - nxt / v) * 100) if v else 0
            keep = 100 - drop
            lost = v - nxt
            ty = y + bh + gap / 2 + 3
            out += (
                f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle" '
                f'font-size="12" font-weight="700" fill="var(--rose)">↓ −{drop}%</text>'
                f'<text x="{cx+top+14:.1f}" y="{ty-1:.1f}" font-size="10.5" '
                f'fill="var(--muted)">{lost} não avançam · {nxt} seguem ({keep}%)</text>'
            )
        y += bh + gap

    return (f'<div style="overflow-x:auto;"><svg viewBox="0 0 {W} {H}" '
            f'style="width:100%;min-width:580px;height:auto;font-family:var(--font);" '
            f'role="img" aria-label="Funil de pesquisa">{out}</svg></div>')


def analises_section(s: dict, ppbase: dict) -> str:
    """Parte 5 — funil, produtividade docente, coortes e eficiência de fomento."""
    total = s["total"]
    with_research = s["with_research"]
    # bolsa paga = SigPesq pago ∪ bolsistas FAPES (consistente com 'research')
    com_bolsa = s.get("with_paid_bolsa",
                      sum(v.get("paid", 0) for v in s.get("admission", {}).get("group_fellowship", {}).values()))
    # ingressaram no mestrado = formandos que entraram no PPComp (base completa)
    mestrado = ppbase.get("pipeline", {}).get("total", 0)

    # ---- 1. FUNIL ----
    estagios = [
        ("Egressos", total, "var(--ink2)"),
        ("Participaram de pesquisa", with_research, "var(--brand)"),
        ("Tiveram bolsa paga", com_bolsa, "var(--amber)"),
        ("Ingressaram no mestrado PPComp", mestrado, "#6a4c93"),
    ]
    funil = _funnel_svg(estagios, total)

    # ---- 2. PRODUTIVIDADE DOCENTE (IC no Lattes, casando orientando ↔ egresso da base) ----
    from src.scripts.generate_formandos_report import (
        load_lattes, load_formandos, SEMESTER_FILE_MAP, DATA_FORMANDOS)
    _seen_f: dict[str, dict] = {}
    for _sem in sorted(SEMESTER_FILE_MAP):
        if (DATA_FORMANDOS / SEMESTER_FILE_MAP[_sem]).exists():
            for _f in load_formandos(_sem):
                _seen_f.setdefault(_f["matricula"] or _f["nome"].strip().lower(), _f)
    _form_keys = {_match_key(_f["nome"]) for _f in _seen_f.values()}
    _lat = load_lattes()
    _ic_egr: dict[str, set] = defaultdict(set)   # orientador → {egressos distintos}
    for r in _lat.get("ic", []):
        if r.get("supervisor") and _match_key(r.get("orientando")) in _form_keys:
            _ic_egr[normalize_name(r["supervisor"])].add(_match_key(r["orientando"]))
    _n_orient = len(_ic_egr)
    _top_orient = sorted(_ic_egr.items(), key=lambda x: -len(x[1]))[:10]
    prod_rows = "".join(
        f'<tr><td>{nome}</td><td>{len(al)}</td></tr>' for nome, al in _top_orient
    )

    # ---- 3. COORTES POR ANO DE INGRESSO ----
    co = {int(y): dd for y, dd in s.get("cohort_analysis", {}).items()}
    anos = sorted(y for y, dd in co.items() if dd.get("total", 0) >= 3)
    co_series = [
        {"name": "% com pesquisa", "color": "var(--brand)",
         "values": [co[a]["ic_pct"] for a in anos]},
    ]
    cohort_chart = _multiline_chart(
        anos, co_series, lambda v: f"{v:.0f}%",
        "Percentual com pesquisa por ano de ingresso", uid="chart-cohort") if anos else ""
    co_size = [co[a]["total"] for a in anos]

    # ---- 4. EFICIÊNCIA DE FOMENTO ----
    fapes_bolsas = fapes_orc = fapes_conc_n = fapes_conc_orc = 0
    if PROJETOS_FILE.exists():
        pr = json.loads(PROJETOS_FILE.read_text())["resumo"]
        fapes_bolsas = pr["total_status_ou_prazo"]["valor_bolsas_total"]
        fapes_orc = pr["total_status_ou_prazo"]["orcamento_contratado_total"]
        fapes_conc_n = pr["concluidos"]["quantidade_projetos"]
        fapes_conc_orc = pr["concluidos"]["orcamento_contratado_total"]
    ef = [
        (_brl(fapes_bolsas / with_research) if with_research else "—",
         "bolsas FAPES por aluno-pesquisa", f"{_brl(fapes_bolsas)} ÷ {with_research}"),
        (_brl(fapes_conc_orc / fapes_conc_n) if fapes_conc_n else "—",
         "custo por projeto concluído", f"{fapes_conc_n} concluídos"),
        (_brl(fapes_orc / total) if total else "—",
         "orçamento FAPES por egresso", "fomento ÷ egressos"),
        (f"{round(fapes_bolsas/fapes_orc*100)}%" if fapes_orc else "—",
         "do orçamento vira bolsa", "pessoas vs custeio"),
    ]
    ef_cards = "".join(
        f'<div class="kpi"><div class="n" style="font-size:26px;">{nn}</div>'
        f'<div class="u">{u}</div><div class="s">{ss}</div></div>'
        for nn, u, ss in ef
    )

    divider = _divider(
        "Parte 5 · Análises",
        "Análises aprofundadas",
        "Quatro recortes que conectam graduação, fomento e pós-graduação: o funil de pesquisa, "
        "a produtividade docente, a evolução das turmas e a eficiência do investimento.",
    )

    # --- Leitura institucional/didática do funil (significado, não só números) ---
    _pp = round(with_research / total * 100) if total else 0   # % pesquisa
    _pb = round(com_bolsa / total * 100) if total else 0       # % bolsa paga
    _pm = round(mestrado / total * 100) if total else 0        # % mestrado
    _tag = ('display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;'
            'letter-spacing:.03em;text-transform:uppercase;padding:2px 8px;border-radius:5px;')
    _box = 'border-radius:10px;padding:11px 14px;margin:12px 0;font-size:14px;border-left:4px solid;line-height:1.5;'
    _ev = f'{_box}background:var(--brand-l);border-color:var(--brand);color:#14361f;'
    _hip = f'{_box}background:#fbf4df;border-color:var(--amber);color:#5e4a12;'
    _rec = f'{_box}background:#eaf1f9;border-color:var(--blue);color:#1f4d7a;'

    def _el(num, titulo, corpo):
        return (f'<div style="margin-top:22px;">'
                f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:6px;">'
                f'<span style="width:28px;height:28px;flex:0 0 28px;border-radius:8px;'
                f'background:var(--brand-l);color:var(--brand-d);display:grid;place-items:center;'
                f'font-size:14px;font-weight:800;">{num}</span>'
                f'<span style="font-size:17px;font-weight:700;color:var(--ink,#16241a);">{titulo}</span>'
                f'</div><div style="padding-left:38px;">{corpo}</div></div>')

    def _frow(lbl, val, p, color):
        w = max(p, 6)
        return (f'<div style="display:grid;grid-template-columns:200px 1fr 60px;align-items:center;'
                f'gap:12px;margin:8px 0;font-size:13.5px;">'
                f'<span style="color:var(--ink2,#3c4f42);line-height:1.2;">{lbl}</span>'
                f'<span style="background:var(--bg,#f4f8f5);border-radius:7px;height:28px;overflow:hidden;">'
                f'<span style="display:flex;align-items:center;height:100%;width:{w}%;background:{color};'
                f'color:#fff;font-weight:700;font-size:12.5px;padding-left:10px;border-radius:7px;">{p}%</span></span>'
                f'<span style="text-align:right;font-weight:800;color:var(--brand-d);'
                f'font-variant-numeric:tabular-nums;">{val}</span></div>')

    _funil_bars = (
        _frow("Egressos (SI + ECA)", total, 100, "#0a5c30")
        + _frow("Passaram por <b>iniciação científica</b>", with_research, _pp, "#0f7a40")
        + _frow("Tiveram <b>bolsa paga</b>", com_bolsa, _pb, "#2f6fb0")
        + _frow("Seguiram para o <b>mestrado</b>", mestrado, _pm, "#b8860b"))

    didatica = f"""
    <section class="section">
      <div class="eyebrow">Leitura institucional</div>
      <h2>O que o funil significa</h2>
      <p class="desc">Além dos números: o que a trajetória diz sobre a relação entre <b>pesquisa e
      formação</b>, e o que cada público faz com isso.</p>
      <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--muted,#71857a);margin:0 0 14px;">
        <span style="{_tag}background:var(--brand-l);color:var(--brand-d);">Evidência</span> medido nos dados
        <span style="{_tag}background:#fbf4df;color:#7a5b06;">Hipótese</span> plausível, não comprovado
        <span style="{_tag}background:#eaf1f9;color:#1f4d7a;">Recomendação</span> ação sugerida
      </div>

      <div class="card">
        <h3 style="margin:0 0 12px;">Funil da trajetória de pesquisa</h3>
        {_funil_bars}
        <div class="note-line" style="margin-top:10px;">Evidência observada. Cruzamento por nome
        (sem acento) — tende a <b>subestimar</b>. {_n_orient} orientadores têm ≥1 egresso.</div>

        {_el(1, "O que esta seção analisa",
             f"<p>Quantos dos <b>{total} egressos</b> (Sistemas de Informação e Engenharia de "
             f"Controle e Automação) passaram por pesquisa no curso — e até onde foram: ingresso → "
             f"iniciação científica → bolsa paga → mestrado.</p>")}

        {_el(2, "Por que é importante",
             "<p>A iniciação científica é um dos caminhos mais consistentes de <b>aprendizagem ativa, "
             "amadurecimento profissional e aproximação com a pós-graduação</b>. O funil mostra qual "
             "fração da formação do campus foi <b>tocada pela pesquisa</b>.</p>")}

        {_el(3, "O que os dados mostram",
             f"<p><b>{with_research} dos {total} egressos ({_pp}%)</b> participaram de pesquisa — "
             f"maioria, não minoria. O funil se estreita: <b>{com_bolsa} ({_pb}%)</b> tiveram bolsa "
             f"paga e <b>{mestrado} ({_pm}%)</b> seguiram ao mestrado PPComp.</p>"
             f'<div style="{_ev}"><b>Evidência:</b> {total} → {with_research} (pesquisa, {_pp}%) → '
             f"{com_bolsa} (bolsa, {_pb}%) → {mestrado} (mestrado, {_pm}%). Cada degrau = mais "
             f"envolvimento com pesquisa.</div>")}

        {_el(4, "Como interpretar",
             f"<p>O topo largo ({_pp}%) sugere que a pesquisa é uma <b>porta larga</b> na graduação. "
             f"O estreitamento é <b>esperado</b>: nem todo aluno de IC quer carreira acadêmica — "
             f"mercado, concursos e empreendedorismo são desfechos legítimos. Cair de {_pp}% para "
             f"{_pm}% <b>não é \"perda\"</b>; é o formato normal de um funil.</p>"
             f'<div style="{_hip}"><b>Atenção — associação, não causa:</b> os dados ligam fazer IC a '
             f"avançar, mas <b>não provam causa</b> (quem faz IC pode já ser mais inclinado à pesquisa).</div>")}

        {_el(5, "Cuidados de interpretação",
             '<ul style="margin:4px 0 0 4px;padding-left:18px;">'
             "<li>Cruzamento <b>por nome (sem acento), match exato</b> → <b>subestima</b> "
             "(homônimos, grafias); os reais tendem a ser maiores.</li>"
             "<li><b>Autodeclaração no Lattes</b>: ausência de registro ≠ ausência de pesquisa.</li>"
             "<li><b>SI ≠ ECA</b> (diurno 4 anos × noturno 6 anos) — não comparar diretamente.</li>"
             "<li><b>Amostra pequena por turma</b> nos anos iniciais → ler tendência, não o ponto.</li></ul>")}

        {_el(6, "Para pesquisadores",
             f"<p>O funil é a evidência de que <b>projetos formam pessoas, não só publicações</b>: "
             f"mostra quantos orientandos avançaram, ajuda a justificar <b>captação de bolsas</b> "
             f"(IC é a porta de entrada) e a planejar a <b>renovação do grupo</b> ({_pm}% vão ao "
             f"mestrado).</p>"
             f'<div style="{_rec}"><b>Recomendação:</b> registrar IC e produtos no Lattes/SigPesq — '
             f"é o que torna o impacto <b>visível e defensável</b>.</div>")}

        {_el(7, "Para professores",
             "<p>A pesquisa é <b>aliada do ensino</b>: aproxima teoria e prática e tende a "
             "<b>engajar</b>. Convidar alunos para projetos amplia a porta que já é larga.</p>"
             f'<div style="{_hip}"><b>Hipótese a confirmar:</b> o engajamento pode favorecer '
             "<b>permanência e conclusão</b> — a seção <b>ainda não mede</b> isso; é plausível, "
             "não comprovado.</div>")}

        {_el(8, "Para estudantes",
             f"<p>Em linguagem direta: você <b>aprende fazendo</b>, ganha <b>bolsa</b> (renda + "
             f"experiência), constrói <b>currículo</b>, desenvolve <b>autonomia</b> e cria "
             f"<b>vínculo</b> com o curso. Não é para poucos — a maioria dos formandos passou por IC. "
             f"E para quem pensa em <b>mestrado</b>, a IC é o caminho mais batido: {mestrado} colegas "
             f"fizeram essa transição no campus.</p>")}

        {_el(9, "Mensagem central",
             '<div style="background:linear-gradient(180deg,#0f7a40,#0a5c30);color:#fff;'
             'border-radius:12px;padding:18px 20px;font-size:16px;line-height:1.5;">'
             f"A pesquisa já é parte <b>estruturante</b> da graduação: <b>{_pp}% dos egressos passaram "
             f"por iniciação científica</b>, e essa trajetória alimenta o próprio mestrado. O desafio "
             f"não é criar cultura de pesquisa — ela existe e é ampla —, mas <b>sustentá-la, "
             f"registrá-la e reduzir o afunilamento</b> entre entrada e continuidade.</div>")}

        {_el(10, "Possíveis ações",
             '<ul style="margin:4px 0 0 4px;padding-left:18px;">'
             "<li><b>Gestão:</b> ampliar bolsas de IC; painel anual de participação por turma; "
             "integrar bases (nome → ORCID/matrícula) para parar de subestimar.</li>"
             "<li><b>Cursos:</b> divulgar a IC a todos os ingressantes; mapear evasão da pesquisa.</li>"
             f"<li><b>Grupos:</b> registrar orientações/produtos; acolher mais ingressantes (há "
             f"{_n_orient} orientadores — capilaridade para crescer).</li>"
             "<li><b>Professores:</b> convidar alunos de sala; ligar disciplina a pesquisa real.</li>"
             "<li><b>Estudantes:</b> procurar orientador cedo; tratar IC como porta para bolsa, "
             "currículo e mestrado.</li></ul>")}
      </div>
    </section>"""

    # --- blocos didáticos das demais seções da Parte 5 ---
    _o_nome = _top_orient[0][0] if _top_orient else "—"
    _o_n = len(_top_orient[0][1]) if _top_orient else 0
    _anos_v = [a for a, n in zip(anos, co_size) if n >= 3]
    _faixa_turmas = f"{_anos_v[0]}–{_anos_v[-1]}" if _anos_v else "—"
    bloco_prod = bloco_didatico({
        "titulo": "Produtividade docente",
        "analisa": "Quais docentes orientaram em iniciação científica os egressos da base — a "
                   "<b>face humana</b> da formação em pesquisa.",
        "importa": "A orientação é o motor da IC: sem orientador, não há projeto. Ver a "
                   "<b>distribuição</b> entre docentes mostra se a formação depende de poucos ou "
                   "está espalhada pelo corpo docente.",
        "mostram": f"<b>{_n_orient} docentes</b> têm ao menos um egresso orientado em IC. O mais "
                   f"ativo (<b>{_o_nome}</b>) orientou <b>{_o_n}</b> egressos da base. A orientação "
                   f"é, portanto, <b>distribuída</b> — não concentrada em uma ou duas pessoas.",
        "evidencia": f"{_n_orient} orientadores com ≥1 egresso; topo em {_o_n} egressos.",
        "interpretar": "Orientação distribuída é um <b>sinal de saúde</b>: a formação em pesquisa "
                       "não fica refém de poucos docentes e resiste a saídas/aposentadorias. O "
                       "topo da lista é natural (quem tem mais tempo de casa orienta mais).",
        "cuidados": [
            "Casamento <b>por nome (sem acento)</b> orientando↔egresso → <b>subestima</b>.",
            "Conta só a <b>IC declarada no Lattes</b> do docente; coorientação informal escapa.",
            "Quem chegou há pouco ao campus aparece com menos egressos (viés de tempo).",
        ],
        "pesquisadores": "Orientar é <b>impacto formativo</b> tão real quanto publicar — e alimenta "
                         "o próprio grupo. Vale registrar todas as orientações no Lattes.",
        "recomendacao": "reconhecer a orientação de IC na avaliação docente e na distribuição de bolsas.",
        "professores": "Assumir um orientando de IC é uma das formas mais diretas de <b>engajar</b> "
                       "e formar — e há espaço para novos orientadores entrarem.",
        "estudantes": "Há <b>muitos</b> docentes que acolhem iniciação científica — procurar um "
                      "orientador alinhado ao seu interesse é mais fácil do que parece.",
        "central": "A formação em pesquisa do campus se apoia em uma <b>base ampla de "
                   "orientadores</b>, não em poucos nomes — o que a torna resiliente e expansível.",
        "acoes": [
            "<b>Gestão:</b> reconhecer orientação de IC na carreira e nos editais de bolsa.",
            "<b>Cursos:</b> apresentar os grupos/orientadores aos ingressantes.",
            "<b>Grupos:</b> criar mentoria para novos docentes assumirem orientandos.",
            "<b>Estudantes:</b> mapear orientadores por linha de pesquisa e procurar cedo.",
        ],
    })
    bloco_ano = bloco_didatico({
        "titulo": "Pesquisa por ano de ingresso",
        "analisa": "A <b>tendência ao longo do tempo</b>: que fração de cada turma (por ano de "
                   "ingresso) participou de pesquisa.",
        "importa": "Diz se a cultura de pesquisa do campus está <b>crescendo, estável ou "
                   "recuando</b> — algo que o número total (78%) sozinho esconde.",
        "mostram": f"A série cobre as turmas de <b>{_faixa_turmas}</b> (só anos com 3+ egressos). "
                   "A participação é <b>consistentemente alta</b> na maior parte do período.",
        "interpretar": "As turmas <b>mais recentes</b> tiveram menos tempo para registrar IC, "
                       "concluir TCC ou ingressar no mestrado — então uma participação menor nos "
                       "anos finais <b>pode ser maturação</b>, não recuo real da cultura de pesquisa.",
        "atencao": "uma eventual queda nas turmas recentes provavelmente reflete o <b>tempo de "
                   "maturação</b> da trajetória, não uma perda de interesse — comparar turmas "
                   "antigas com recentes mistura coisas diferentes.",
        "cuidados": [
            "<b>Amostra pequena</b> por ano nos primeiros anos → série ruidosa.",
            "<b>Viés de maturação</b>: turmas novas ainda não completaram a trajetória.",
            "Participação por <b>autodeclaração</b> (Lattes/SigPesq) — subestima.",
        ],
        "pesquisadores": "Acompanhar a participação por coorte ajuda a <b>planejar captação</b> e a "
                         "perceber cedo quedas reais de engajamento.",
        "professores": "Engajar as turmas <b>logo no início</b> do curso antecipa a entrada na "
                       "pesquisa e melhora a série das próximas coortes.",
        "estudantes": "Quanto <b>mais cedo</b> você entra na IC, mais tempo tem para bolsa, "
                      "currículo e a transição para o mestrado.",
        "central": "A participação em pesquisa é <b>consistente entre as turmas</b>; quedas nos anos "
                   "recentes pedem leitura cuidadosa (maturação), não alarme.",
        "acoes": [
            "<b>Gestão:</b> publicar a série por coorte todo ano e ler a tendência (não o ponto).",
            "<b>Cursos:</b> ação de <b>entrada precoce</b> na IC já no 1º/2º período.",
            "<b>Grupos:</b> reservar vagas de IC para calouros.",
        ],
    })
    bloco_efic = bloco_didatico({
        "titulo": "Eficiência do fomento",
        "analisa": "Quanto de <b>recurso FAPES</b> sustenta a formação em pesquisa — uma noção de "
                   "custo por <b>aluno-pesquisador</b> formado.",
        "importa": "Conecta diretamente <b>investimento</b> e <b>formação de pessoas</b>: bolsa não "
                   "é gasto, é o que viabiliza o estudante dedicar-se à pesquisa.",
        "mostram": f"Dividindo as bolsas FAPES pelos <b>{with_research} egressos com pesquisa</b>, "
                   "chega-se a um <b>custo médio por aluno-pesquisador</b> (alguns milhares de "
                   "reais) — uma ordem de grandeza, não um preço exato.",
        "interpretar": "Esse valor é <b>custo de formar gente</b>, não desperdício: é investimento "
                       "em <b>capital humano</b> que retorna como produção, mestrandos e captação futura.",
        "cuidados": [
            "Numerador (bolsas) e denominador (egressos com pesquisa) vêm de <b>janelas e fontes "
            "diferentes</b> — é aproximação, não atribuição 1:1.",
            "O <b>valor pago</b> consta <b>zerado</b> na fonte (só o alocado) — subestima a execução.",
            "Nem toda bolsa do período foi para esses egressos específicos.",
        ],
        "pesquisadores": "Bolsas <b>formam pessoas</b> e renovam o grupo — argumento direto para "
                         "justificar e renovar captação.",
        "recomendacao": "acompanhar o custo por aluno-pesquisador ao longo dos anos, não num ponto isolado.",
        "professores": "Bolsas viabilizam a <b>orientação</b>: sem fomento, o aluno precisa trabalhar "
                       "e abandona a IC.",
        "estudantes": "A bolsa é muitas vezes a <b>condição de permanência</b> que permite você se "
                      "dedicar à pesquisa em vez de só ao emprego.",
        "central": "Investir em bolsas de IC é investir na <b>formação</b>: o custo por "
                   "aluno-pesquisador é métrica de <b>capital humano</b>, não de despesa.",
        "acoes": [
            "<b>Gestão:</b> proteger o orçamento de bolsas de IC; cobrar o registro do valor pago.",
            "<b>Cursos:</b> divulgar editais de bolsa amplamente, não só aos melhores alunos.",
            "<b>Estudantes:</b> candidatar-se a bolsas cedo — é o que sustenta a dedicação.",
        ],
    })

    body = f"""
    <section class="section">
      <div class="eyebrow">Do ingresso à pós</div>
      <h2>Funil de pesquisa</h2>
      <p class="desc">Quantos egressos avançam em cada etapa da trajetória de pesquisa.</p>
      <div class="card">{funil}
        <div class="note-line">À direita, o <b>% sobre o total</b> de egressos. As setas
        <b>↓ −X%</b> entre as bandas são a <b>queda em relação à etapa anterior</b> (e o texto ao
        lado mostra quantos não avançam e quantos seguem). "Bolsa paga" = fomento financiado
        registrado (bolsa paga no SigPesq <b>ou</b> bolsista FAPES); última etapa = egressos da
        graduação que <b>ingressaram no mestrado PPComp</b> (base completa de discentes).</div>
      </div>
    </section>
    {didatica}
    <section class="section">
      <div class="eyebrow">Quem sustenta a pesquisa</div>
      <h2>Produtividade docente</h2>
      <p class="desc">Orientadores com mais <b>egressos da base</b> orientados em iniciação
      científica, segundo o currículo Lattes.</p>
      <div class="card">
        <table><thead><tr><th>Orientador</th><th>Egressos orientados em IC (Lattes)</th></tr></thead>
        <tbody>{prod_rows}</tbody></table>
        <div class="note-line">Orientações de IC declaradas no Lattes do docente, cruzadas com a
        base de egressos (orientando = formando SI/ECA). {_n_orient} orientadores têm ao menos um
        egresso. Casamento por nome, sem acento.</div>
      </div>
    </section>
    {bloco_prod}
    <section class="section">
      <div class="eyebrow">Evolução das turmas</div>
      <h2>Pesquisa por ano de ingresso</h2>
      <p class="desc">% de cada turma (por ano de ingresso) que participou de pesquisa — só anos
      com 3+ egressos. Mostra a tendência ao longo do tempo.</p>
      <div class="card">{cohort_chart}
        <div class="note-line">Turmas (nº de egressos por ano de ingresso): {", ".join(f"{a}:{n}" for a,n in zip(anos, co_size))}.</div>
      </div>
    </section>
    {bloco_ano}
    <section class="section">
      <div class="eyebrow">Retorno do investimento</div>
      <h2>Eficiência do fomento</h2>
      <p class="desc">Quanto custa, em recurso FAPES, sustentar a formação em pesquisa.</p>
      <div class="kpis" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr));">{ef_cards}</div>
    </section>
    {bloco_efic}"""
    return divider + body


def _find_chrome() -> str | None:
    """Localiza um navegador Chromium para renderizar o PDF."""
    import shutil
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "google-chrome", "chromium", "chromium-browser", "chrome",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
        w = shutil.which(c)
        if w:
            return w
    return None


def html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    """Gera PDF a partir do HTML via headless Chrome (SVG + CSS de impressão)."""
    import subprocess
    chrome = _find_chrome()
    if not chrome:
        print("PDF: navegador Chromium não encontrado — pulei a geração.")
        return False
    cmd = [
        chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        "--virtual-time-budget=8000", "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri(),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except Exception as e:
        print(f"PDF: falha ao gerar ({e}).")
        return False
    return pdf_path.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None)
    parser.add_argument("--pdf", action="store_true", help="Gera também um PDF")
    args = parser.parse_args()

    print("Calculando dados da graduação...")
    grad_payload = EX.compute_payload()
    print(f"  {grad_payload['stats']['total']} formandos · "
          f"{grad_payload['stats']['pct_research']}% com pesquisa")

    print("Calculando base PPComp (mestrado)...")
    ppbase = PPB.compute()
    print(f"  {ppbase['total']} discentes · {ppbase['defendidos']} defenderam · "
          f"{ppbase['pipeline']['total']} vindos da graduação Serra")

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = build(grad_payload, ppbase, now)

    out = Path(args.out) if args.out else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Written: {out}")

    if args.pdf:
        pdf = out.with_suffix(".pdf")
        if html_to_pdf(out, pdf):
            print(f"Written: {pdf}")


if __name__ == "__main__":
    main()
