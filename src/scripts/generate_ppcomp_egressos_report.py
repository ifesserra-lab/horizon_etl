"""
Relatório 'Egressos PPComp × Pesquisa' — IFES Serra.

Cruza os egressos do mestrado PPComp com:
  - formandos da graduação (SI / ECA) — pipeline graduação → mestrado
  - iniciação científica / orientações registradas no SigPesq
  - bolsistas FAPES do campus
  - iniciação científica registrada no Lattes

Design claro, pronto para impressão. Reutiliza o casamento de nomes
(accent-insensitive) e os carregadores de generate_formandos_report.

Uso:
  python -m src.scripts.generate_ppcomp_egressos_report
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import openpyxl

from src.scripts.generate_formandos_report import (
    SEMESTER_FILE_MAP, DATA_FORMANDOS, BASE,
    load_formandos, load_json, load_lattes, load_bolsistas,
    _match_key, normalize_name,
)

EGRESSOS_FILE = BASE / "data" / "mestrado" / "egressos_PPComp.xlsx"
OUT_DIR = BASE / "data" / "exports" / "mestrado"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_egressos() -> list[str]:
    """Nomes dos egressos PPComp (1 coluna, sem cabeçalho)."""
    wb = openpyxl.load_workbook(EGRESSOS_FILE, read_only=True)
    out = []
    for r in wb.active.iter_rows(values_only=True):
        if r and r[0] and str(r[0]).strip():
            out.append(str(r[0]).strip())
    wb.close()
    return out


def _clean_sup(s: str | None) -> str:
    """Nome do orientador; converte stem de arquivo Lattes (NN_nome-sobrenome_id)."""
    if not s:
        return ""
    m = re.match(r"^\d+_(.+?)_\d+$", s.strip())
    if m:
        return normalize_name(m.group(1).replace("-", " "))
    return normalize_name(s)


def compute() -> dict:
    egr_raw = load_egressos()
    egr: dict[str, str] = {}            # match_key → nome (dedup)
    for e in egr_raw:
        egr.setdefault(_match_key(e), e)

    # formandos undergrad (dedup por matrícula)
    seen: dict[str, dict] = {}
    for sem in sorted(SEMESTER_FILE_MAP):
        if (DATA_FORMANDOS / SEMESTER_FILE_MAP[sem]).exists():
            for f in load_formandos(sem):
                seen.setdefault(f["matricula"] or f["nome"].strip().lower(), f)
    form_mk = {_match_key(f["nome"]): f for f in seen.values()}

    # SigPesq: separa VÍNCULO a projeto (membro) de BOLSA (fellowship registrada)
    adv = load_json("advisorships_canonical.json")
    sig_membro: set[str] = set()
    sig_bolsa: dict[str, str] = {}   # match_key → nome da bolsa IC (ex.: PIBIC)
    for p in adv:
        for a in p.get("advisorships", []):
            if not a.get("person_id"):
                continue
            k = _match_key(a.get("person_name"))
            sig_membro.add(k)
            _fn = (a.get("fellowship") or {}).get("name")
            if _fn:
                sig_bolsa[k] = _fn

    # FAPES bolsistas (todos) + valor/tipos por nome
    bd = load_bolsistas()
    bols_val: dict[str, dict] = {}
    for b in bd["bolsistas_unicos"]:
        bols_val[_match_key(b["bolsista_pesquisador_nome"])] = {
            "valor_alocado": b.get("valor_alocado_total", 0) or 0,
        }
    bols_tipos: dict[str, set] = defaultdict(set)
    for a in bd.get("alocacoes", []):
        bols_tipos[_match_key(a.get("bolsista_pesquisador_nome"))].add(a.get("bolsa_sigla") or "?")

    # Lattes dos professores: orientações de IC e TCC (orientando → orientadores)
    lat = load_lattes()
    ic_by: dict[str, set] = defaultdict(set)
    tcc_by: dict[str, set] = defaultdict(set)
    for x in lat["ic"]:
        if x.get("supervisor"):
            ic_by[_match_key(x["orientando"])].add(_clean_sup(x["supervisor"]))
    for x in lat["tcc"]:
        if x.get("supervisor"):
            tcc_by[_match_key(x["orientando"])].add(_clean_sup(x["supervisor"]))

    # tipos de bolsa por categoria (a sigla FAPES define a natureza)
    _IC_SIGLAS = {"PIBIC", "PIVIC", "PIBITI", "PIVITI", "ICT", "ICJr"}
    _MESTRADO_SIGLAS = {"ME"}

    registros = []
    for k, nome in sorted(egr.items(), key=lambda kv: kv[1]):
        f = form_mk.get(k)
        orient_ic = sorted(ic_by.get(k, set()))
        orient_tcc = sorted(tcc_by.get(k, set()))
        tipos = sorted(bols_tipos.get(k, set()))
        tset = set(tipos)
        # classifica a bolsa pela natureza
        bolsa_ic = (k in sig_bolsa) or bool(tset & _IC_SIGLAS)
        bolsa_mestrado = bool(tset & _MESTRADO_SIGLAS)
        bolsa_outra = bool(tset - _IC_SIGLAS - _MESTRADO_SIGLAS)
        registros.append({
            "nome": normalize_name(nome),
            "formando_serra": f is not None,
            "curso": f["curso"] if f else None,
            "vinculo_sigpesq": k in sig_membro,
            "bolsa_ic_grad": bolsa_ic,
            "bolsa_mestrado": bolsa_mestrado,
            "bolsa_outra": bolsa_outra,
            "bolsa_sigpesq_nome": sig_bolsa.get(k),
            "fapes_valor": bols_val.get(k, {}).get("valor_alocado", 0),
            "fapes_tipos": tipos,
            "orient_ic_prof": orient_ic,
            "orient_tcc_prof": orient_tcc,
            "orientadores": sorted(set(orient_ic) | set(orient_tcc)),
        })

    n = len(registros)
    def cnt(key) -> int:
        return sum(1 for r in registros if r[key])

    orient_prof = sum(1 for r in registros if r["orient_ic_prof"] or r["orient_tcc_prof"])
    return {
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total_linhas": len(egr_raw),
        "total_unicos": n,
        "formandos_serra": cnt("formando_serra"),
        "vinculo_sigpesq": cnt("vinculo_sigpesq"),
        "bolsa_ic_grad": cnt("bolsa_ic_grad"),
        "bolsa_mestrado": cnt("bolsa_mestrado"),
        "bolsa_outra": cnt("bolsa_outra"),
        "orient_ic_prof": cnt("orient_ic_prof"),
        "orient_tcc_prof": cnt("orient_tcc_prof"),
        "orient_prof_ifes": orient_prof,
        "registros": registros,
    }


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

CSS = """
:root{
  --ink:#16241a;--ink2:#3c4f42;--muted:#71857a;--line:#e3ece5;--line2:#cfddd3;
  --paper:#fff;--bg:#f4f8f5;--soft:#eef5f0;--brand:#0f7a40;--brand-d:#0a5c30;
  --brand-l:#e7f4ec;--blue:#2f6fb0;--blue-l:#e8f0f8;--amber:#b8860b;--amber-l:#f7f0dd;--rose:#b5455f;
  --shadow:0 1px 2px rgba(16,40,24,.04),0 6px 20px rgba(16,40,24,.06);
  --font:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;--serif:'Georgia',serif;
}
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
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;}
.kpi{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:24px 22px;
     box-shadow:var(--shadow);position:relative;overflow:hidden;}
.kpi::after{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--brand);}
.kpi .n{font-size:40px;font-weight:800;letter-spacing:-.02em;color:var(--brand-d);line-height:1;}
.kpi .u{font-size:14.5px;font-weight:600;margin-top:8px;}
.kpi .s{font-size:13px;color:var(--muted);margin-top:4px;}
.card{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:26px 28px;box-shadow:var(--shadow);}
.card h3{font-size:16px;font-weight:700;margin-bottom:16px;}
table{width:100%;border-collapse:collapse;font-size:14px;}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);}
td.c,th.c{text-align:center;}td.r,th.r{text-align:right;}
thead th{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:700;}
tbody tr:last-child td{border-bottom:none;}
.chip{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:6px;margin-right:4px;}
.chip.g{background:var(--brand-l);color:var(--brand-d);}
.chip.a{background:var(--amber-l);color:var(--amber);}
.chip.b{background:var(--blue-l);color:var(--blue);}
.ok{color:var(--brand-d);font-weight:700;}.no{color:var(--muted);}
.bars{display:flex;flex-direction:column;gap:14px;}
.brow{display:grid;grid-template-columns:210px 1fr 120px;align-items:center;gap:14px;}
.bl{font-size:14px;}.btrack{height:18px;background:var(--soft);border-radius:9px;overflow:hidden;}
.bfill{height:100%;border-radius:9px;min-width:6px;}.bv{font-size:13.5px;font-weight:700;text-align:right;white-space:nowrap;}
.callout{background:linear-gradient(135deg,var(--brand-d),var(--brand));color:#fff;border-radius:18px;
         padding:34px 38px;box-shadow:var(--shadow);}
.callout .k{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;opacity:.85;margin-bottom:12px;}
.callout h2{font-family:var(--serif);font-size:26px;color:#fff;margin-bottom:12px;}
.callout p{font-size:16px;opacity:.95;max-width:72ch;}
.note-line{font-size:12.5px;color:var(--muted);margin-top:14px;font-style:italic;}
.foot{margin-top:60px;padding-top:22px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted);
      display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;}
@media(max-width:760px){.kpis{grid-template-columns:1fr 1fr;}.brow{grid-template-columns:130px 1fr 80px;}}
@media print{body{background:#fff;font-size:12px;}.section{page-break-inside:avoid;}
  .kpi,.card,.callout{box-shadow:none;}.callout{background:var(--brand-d)!important;}}
"""


def _bar(label, value, mx, color, note):
    w = value / mx * 100 if mx else 0
    return (f'<div class="brow"><span class="bl">{label}</span>'
            f'<div class="btrack"><div class="bfill" style="width:{max(w,1.5):.1f}%;background:{color};"></div></div>'
            f'<span class="bv">{note}</span></div>')


def render(d: dict) -> str:
    n = d["total_unicos"]
    pct_orient = round(d["orient_prof_ifes"] / n * 100) if n else 0

    kpis = f"""
    <section class="section"><div class="kpis">
      <div class="kpi"><div class="n">{n}</div><div class="u">egressos PPComp</div>
        <div class="s">{d['total_linhas']} registros · sem repetição</div></div>
      <div class="kpi"><div class="n">{d['orient_prof_ifes']}</div><div class="u">orientados em IC/TCC por prof. IFES</div>
        <div class="s">{pct_orient}% · via currículos Lattes</div></div>
      <div class="kpi"><div class="n">{d['formandos_serra']}</div><div class="u">vieram da graduação Serra</div>
        <div class="s">pipeline graduação → mestrado</div></div>
      <div class="kpi"><div class="n">{d['bolsa_ic_grad']}</div><div class="u">bolsa de IC na graduação</div>
        <div class="s">mestrado {d['bolsa_mestrado']} · UnAC/EAD {d['bolsa_outra']} (à parte)</div></div>
    </div></section>"""

    # evidence bars
    mx = n
    bars = (
        _bar("Orientados em IC/TCC por prof. IFES", d["orient_prof_ifes"], mx, "var(--brand)",
             f"{d['orient_prof_ifes']} · {round(d['orient_prof_ifes']/n*100)}%")
        + _bar("Vínculo a projeto no SigPesq", d["vinculo_sigpesq"], mx, "#3a9c63",
               f"{d['vinculo_sigpesq']} · {round(d['vinculo_sigpesq']/n*100)}%")
        + _bar("Formandos da graduação Serra", d["formandos_serra"], mx, "var(--blue)",
               f"{d['formandos_serra']} · {round(d['formandos_serra']/n*100)}%")
        + _bar("Bolsa de IC na graduação", d["bolsa_ic_grad"], mx, "var(--amber)",
               f"{d['bolsa_ic_grad']} · {round(d['bolsa_ic_grad']/n*100)}%")
    )
    foot_sec = f"""
    <section class="section">
      <div class="eyebrow">Pegada de pesquisa</div>
      <h2>Por onde os egressos passaram</h2>
      <p class="desc">Fontes que evidenciam atividade de pesquisa de cada egresso. Atenção:
      vínculo a projeto no SigPesq ≠ bolsa — para mestrandos, normalmente reflete a própria
      pesquisa de mestrado.</p>
      <div class="card"><div class="bars">{bars}</div>
        <div class="note-line">Bolsas por natureza: <b>{d['bolsa_ic_grad']}</b> de IC na
        graduação, <b>{d['bolsa_mestrado']}</b> de mestrado (FAPES-ME) e <b>{d['bolsa_outra']}</b>
        da Universidade Aberta (B-UnAC/EAD) — estas duas últimas não são iniciação científica.
        O alto vínculo ao SigPesq reflete participação em projetos (em geral o próprio mestrado),
        não bolsa de IC.</div></div>
    </section>"""

    # orientação por professores IFES (Lattes) — IC / TCC
    orows = ""
    for r in sorted(d["registros"], key=lambda x: x["nome"]):
        if not (r["orient_ic_prof"] or r["orient_tcc_prof"]):
            continue
        tipo = ""
        if r["orient_ic_prof"]:
            tipo += '<span class="chip g">IC</span>'
        if r["orient_tcc_prof"]:
            tipo += '<span class="chip b">TCC</span>'
        sups = ", ".join(r["orientadores"][:3])
        orows += (f'<tr><td>{r["nome"]}</td><td>{tipo}</td>'
                  f'<td style="color:var(--ink2);">{sups}</td></tr>')
    orient_sec = f"""
    <section class="section">
      <div class="eyebrow">Orientação na graduação · Lattes dos professores</div>
      <h2>Egressos orientados por professores do IFES</h2>
      <p class="desc">Cruzando os egressos com as orientações de IC e TCC declaradas nos
      currículos Lattes dos docentes do IFES. <b>{d['orient_prof_ifes']}</b> egressos foram
      orientados por um professor da casa ({d['orient_ic_prof']} em IC, {d['orient_tcc_prof']} em TCC).</p>
      <div class="card">
        <table><thead><tr><th>Egresso</th><th>Tipo</th><th>Orientador(es) IFES</th></tr></thead>
        <tbody>{orows}</tbody></table>
        <div class="note-line">Fonte: orientações concluídas/em andamento nos CVs Lattes dos
        docentes. Pode subestimar — depende do currículo estar atualizado.</div>
      </div>
    </section>"""

    # tabela de bolsas dos egressos
    _NAT = {"PIBIC": "IC graduação", "PIVIC": "IC graduação", "ICT": "IC graduação",
            "ICJr": "IC graduação", "PIBITI": "IC graduação", "PIVITI": "IC graduação",
            "ME": "Mestrado", "B-UnAC": "Univ. Aberta (EAD)"}

    def _brl(v):
        return f'R$ {v:,.0f}'.replace(",", "X").replace(".", ",").replace("X", ".") if v else "—"

    brows = ""
    for r in sorted(d["registros"], key=lambda x: (not x["bolsa_ic_grad"], x["nome"])):
        siglas = list(r["fapes_tipos"])
        if r.get("bolsa_sigpesq_nome"):
            siglas = [r["bolsa_sigpesq_nome"]] + siglas
        if not siglas:
            continue
        nat = " · ".join(sorted({_NAT.get(s, "Outra") for s in siglas}))
        if r["bolsa_ic_grad"]:
            chip = '<span class="chip g">IC graduação</span>'
        elif r["bolsa_mestrado"]:
            chip = '<span class="chip a">Mestrado</span>'
        else:
            chip = '<span class="chip b">EAD/UnAC</span>'
        brows += (f'<tr><td>{r["nome"]}</td>'
                  f'<td>{", ".join(siglas)}</td>'
                  f'<td>{chip}</td>'
                  f'<td class="r">{_brl(r["fapes_valor"])}</td></tr>')
    bolsa_sec = f"""
    <section class="section">
      <div class="eyebrow">Bolsas dos egressos</div>
      <h2>Quem teve bolsa — e de que tipo</h2>
      <p class="desc">Bolsas registradas para os egressos, classificadas pela natureza.
      Apenas <b>{d['bolsa_ic_grad']}</b> é de iniciação científica na graduação; as demais
      são de mestrado (FAPES-ME) ou Universidade Aberta (EAD) — não são IC.</p>
      <div class="card">
        <table><thead><tr><th>Egresso</th><th>Modalidade</th><th>Natureza</th><th class="r">Valor alocado</th></tr></thead>
        <tbody>{brows}</tbody></table>
        <div class="note-line">FAPES-ME = bolsa de mestrado · B-UnAC = Universidade Aberta
        Capixaba (EAD) · PIBIC = iniciação científica (SigPesq). Valores FAPES são alocados.</div>
      </div>
    </section>"""

    # pipeline table (graduação Serra → mestrado)
    prows = ""
    for r in d["registros"]:
        if not r["formando_serra"]:
            continue
        short = "ECA" if r["curso"] and "Controle" in r["curso"] else "SI"
        chips = ""
        if r["orient_ic_prof"] or r["orient_tcc_prof"]:
            chips += '<span class="chip g">orientado IFES</span>'
        if r["bolsa_ic_grad"]:
            chips += '<span class="chip b">bolsa IC</span>'
        if r["bolsa_mestrado"]:
            chips += '<span class="chip a">bolsa mestrado</span>'
        prows += (f'<tr><td>{r["nome"]}</td><td class="c">{short}</td>'
                  f'<td>{chips or "—"}</td></tr>')
    pipeline = f"""
    <section class="section">
      <div class="eyebrow">Pipeline graduação → mestrado</div>
      <h2>Egressos que se formaram no campus</h2>
      <p class="desc">{d['formandos_serra']} dos {n} mestres do PPComp também concluíram a
      graduação no IFES Serra — formação completa dentro de casa.</p>
      <div class="card">
        <table><thead><tr><th>Egresso</th><th class="c">Graduação</th><th>Trajetória</th></tr></thead>
        <tbody>{prows}</tbody></table>
      </div>
    </section>"""

    callout = f"""
    <section class="section"><div class="callout">
      <div class="k">Mensagem central</div>
      <h2>O mestrado é alimentado pela orientação na graduação</h2>
      <p>{d['orient_prof_ifes']} egressos do PPComp foram orientados em IC ou TCC por
      professores do IFES e {d['formandos_serra']} se formaram na própria graduação do campus.
      A orientação de graduação funciona como porta de entrada para a pós.</p>
    </div></section>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Egressos PPComp × Pesquisa — IFES Serra</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="page">
<header class="hero">
  <div class="kicker">● IFES Serra · PPComp · Pesquisa</div>
  <h1>Egressos do mestrado PPComp e sua trajetória de pesquisa</h1>
  <p class="lede">Cruzamento dos egressos do PPComp com formandos da graduação, orientações
  de IC/TCC no Lattes dos professores, vínculo a projetos no SigPesq e bolsas FAPES.</p>
  <div class="meta"><span>Egressos únicos: <b>{n}</b></span>
    <span>Orientados por prof. IFES: <b>{d['orient_prof_ifes']}</b></span>
    <span>Fonte: <b>PPComp · Lattes · SigPesq · FAPES</b></span></div>
</header>
{kpis}
{orient_sec}
{foot_sec}
{bolsa_sec}
{pipeline}
{callout}
<div class="foot"><span>Egressos PPComp × Pesquisa — IFES Serra</span>
  <span>Gerado em {d['gerado_em']} · base deduplicada por nome ({n} egressos)</span></div>
</div></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    print("Calculando cruzamento dos egressos PPComp...")
    d = compute()
    print(f"  {d['total_unicos']} egressos únicos · {d['orient_prof_ifes']} orientados por prof. IFES "
          f"(IC {d['orient_ic_prof']}, TCC {d['orient_tcc_prof']}) · "
          f"{d['formandos_serra']} ex-formandos Serra · bolsa IC-grad {d['bolsa_ic_grad']}, "
          f"mestrado {d['bolsa_mestrado']}, UnAC {d['bolsa_outra']}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html_path = Path(args.out) if args.out else OUT_DIR / "ppcomp_egressos.html"
    html_path.write_text(render(d), encoding="utf-8")
    json_path = html_path.with_suffix(".json")
    json_path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written: {html_path}")
    print(f"Written: {json_path}")


if __name__ == "__main__":
    main()
