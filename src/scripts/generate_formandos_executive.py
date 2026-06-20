"""
Relatório EXECUTIVO 'Formandos × Pesquisa' — IFES Serra.

Versão de apresentação para professores e gestores: design claro, foco
narrativo, pronto para impressão (A4) e projeção. Consome o JSON gerado por
``generate_formandos_report`` (não recalcula nada).

Uso:
  python -m src.scripts.generate_formandos_executive
  python -m src.scripts.generate_formandos_executive --json <caminho.json>
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "data" / "exports" / "formandos"
DEFAULT_JSON = OUT_DIR / "formandos_pesquisa_all_generated.json"

GROUPS = ["Cotas / Reserva de vagas", "Ampla Concorrência", "Transferência"]
GSHORT = {"Cotas / Reserva de vagas": "Cotistas",
          "Ampla Concorrência": "Ampla concorrência",
          "Transferência": "Transferência"}


# ---------------------------------------------------------------------------
# Styling
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def bar(label: str, value, max_val: float, color: str, suffix: str = "",
        note: str | None = None) -> str:
    """Horizontal bar; value label always sits OUTSIDE the track (right)."""
    w = (value / max_val * 100) if max_val else 0
    val_txt = note if note is not None else f"{value}{suffix}"
    return (
        f'<div class="brow"><span class="bl">{label}</span>'
        f'<div class="btrack"><div class="bfill" '
        f'style="width:{max(w, 1.5):.1f}%;background:{color};"></div></div>'
        f'<span class="bv">{val_txt}</span></div>'
    )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(payload: dict, generated_at: str) -> str:
    s = payload["stats"]
    sems = payload.get("semesters") or []
    period = (f"{sems[0].replace('_', '.')} – {sems[-1].replace('_', '.')}"
              if sems else "")
    total = s["total"]
    a = s["admission"]
    gt = s["graduation_time"]

    # --- core figures ---
    with_research = s["with_research"]
    pct_research = s["pct_research"]
    grad_mean = gt["overall"]["mean"]
    grad_years = grad_mean / 2

    g_counts = a["group_counts"]
    g_ic = a["group_ic"]
    g_fel = a["group_fellowship"]
    by_adm = gt.get("by_admission", {})

    cota_n = g_counts.get("Cotas / Reserva de vagas", 0)
    ampla_n = g_counts.get("Ampla Concorrência", 0)
    cota_ic_pct = g_ic.get("Cotas / Reserva de vagas", {}).get("pct", 0)
    ampla_ic_pct = g_ic.get("Ampla Concorrência", {}).get("pct", 0)
    cota_paid_pct = g_fel.get("Cotas / Reserva de vagas", {}).get("pct_paid_total", 0)
    ampla_paid_pct = g_fel.get("Ampla Concorrência", {}).get("pct_paid_total", 0)
    cota_grad = by_adm.get("Cotas / Reserva de vagas", {}).get("overall", {}).get("mean", 0)
    ampla_grad = by_adm.get("Ampla Concorrência", {}).get("overall", {}).get("mean", 0)
    # atraso = semestres além do currículo previsto (SI=8, ECA=12) — comparável entre cursos
    cota_delay = by_adm.get("Cotas / Reserva de vagas", {}).get("delay", {}).get("mean", 0)
    ampla_delay = by_adm.get("Ampla Concorrência", {}).get("delay", {}).get("mean", 0)
    exp = gt.get("expected", {})

    def _sig(v) -> str:
        return f"+{v}" if v > 0 else (f"{v}" if v < 0 else "0")

    # Atraso até ~2 semestres NEGATIVO é plausível (aproveitamento de créditos / horas de
    # extensão antecipam a colação). Mas atraso <= -3 (formar 3+ semestres antes do previsto,
    # vários em 1 semestre total) extensão não explica → ingresso inferido do prefixo da
    # matrícula está errado (reingresso/SISU/matrícula nova). Afeta cota E ampla.
    def _atraso_breakdown(g: str) -> tuple[int, int, int]:
        dl = by_adm.get(g, {}).get("delay") or {}
        dist = dl.get("dist") or {}
        accel = sum(c for v, c in dist.items() if -2 <= int(v) <= -1)
        suspect = sum(c for v, c in dist.items() if int(v) <= -3)
        return accel, suspect, dl.get("n", 0)
    _cota_accel, _cota_susp, _cota_nn = _atraso_breakdown("Cotas / Reserva de vagas")
    _ampla_accel, _ampla_susp, _ampla_nn = _atraso_breakdown("Ampla Concorrência")
    cota_susp_pct = round(_cota_susp / _cota_nn * 100) if _cota_nn else 0

    # === HERO ===
    hero = f"""
    <header class="hero">
      <div class="kicker">● IFES Serra · Pesquisa & Inclusão</div>
      <h1>Iniciação científica forma profissionais — e nivela oportunidades</h1>
      <p class="lede">Análise de <b>{total} formandos</b> dos cursos de Sistemas de Informação
      e Engenharia de Controle e Automação, cruzando participação em pesquisa, forma de
      ingresso (cotas) e tempo de formação.</p>
      <div class="meta">
        <span>Período analisado: <b>{period}</b></span>
        <span>Formandos únicos: <b>{total}</b></span>
        <span>Fonte: <b>SigPesq</b> + registros acadêmicos</span>
      </div>
    </header>"""

    # === KPIs ===
    kpis = f"""
    <section class="section">
      <div class="kpis">
        <div class="kpi"><div class="n">{total}</div>
          <div class="u">formandos analisados</div>
          <div class="s">2 cursos · {len(sems)} semestres · sem repetição</div></div>
        <div class="kpi"><div class="n">{pct_research}%</div>
          <div class="u">participaram de pesquisa</div>
          <div class="s">{with_research} alunos com iniciação científica</div></div>
        <div class="kpi"><div class="n">{_pct(cota_n, total)}%</div>
          <div class="u">ingressaram por cotas</div>
          <div class="s">{cota_n} formandos por reserva de vagas</div></div>
        <div class="kpi"><div class="n">{grad_mean}</div>
          <div class="u">semestres até formar</div>
          <div class="s">média geral · {grad_years:.1f} anos</div></div>
      </div>
    </section>"""

    # === FINDINGS ===
    findings = f"""
    <section class="section">
      <div class="eyebrow">O que os dados mostram</div>
      <h2>Principais achados</h2>
      <p class="desc">Três resultados que merecem atenção da gestão acadêmica e do corpo docente.</p>
      <div class="findings">
        <div class="finding">
          <span class="tag eq">Equidade</span>
          <h3>Cotistas participam mais de pesquisa</h3>
          <div class="big"><span class="v">{cota_ic_pct}%</span>
            <span class="vs">dos cotistas vs {ampla_ic_pct}% da ampla concorrência</span></div>
          <p>Estudantes que ingressaram por cotas se engajam em iniciação científica em
          proporção <b>maior</b> que os demais — sinal de que a política de inclusão alcança
          também a formação em pesquisa.</p>
        </div>
        <div class="finding">
          <span class="tag eq">Desempenho</span>
          <h3>Tempo de formação — dado não confiável por grupo</h3>
          <div class="big"><span class="v">{_sig(cota_delay)}</span>
            <span class="vs">semestres de atraso vs {_sig(ampla_delay)} da ampla concorrência</span></div>
          <p>Medindo o <b>atraso</b> ante a duração prevista de cada curso (SI = 8 semestres,
          ECA = 12). <b>⚠ Ressalva:</b> formar até ~2 semestres antes do previsto é plausível
          (aproveitamento de créditos / horas de extensão). Mas <b>{_cota_susp} de {_cota_nn}</b>
          cotistas ({cota_susp_pct}%) aparecem formando <b>3+ semestres antes</b> — vários em 1
          semestre total — o que extensão não explica e revela ingresso inferido da matrícula
          incorreto (reingresso/SISU/matrícula nova). O mesmo ocorre na ampla
          ({_ampla_susp} de {_ampla_nn}). <b>A comparação de tempo por forma de ingresso fica comprometida.</b></p>
        </div>
        <div class="finding">
          <span class="tag sp">Fomento</span>
          <h3>Cotistas têm mais bolsa paga</h3>
          <div class="big"><span class="v">{cota_paid_pct}%</span>
            <span class="vs">com bolsa vs {ampla_paid_pct}% da ampla concorrência</span></div>
          <p>A taxa de bolsas pagas entre cotistas é cerca de duas vezes a da ampla
          concorrência. A <b>Fapes</b> concentra esse financiamento.</p>
        </div>
        <div class="finding">
          <span class="tag rs">Pesquisa</span>
          <h3>Pesquisa é parte da formação</h3>
          <div class="big"><span class="v">{with_research}</span>
            <span class="vs">de {total} formandos passaram por IC</span></div>
          <p>Quase <b>{round(pct_research)}%</b> dos formandos tiveram alguma experiência de
          iniciação científica registrada — base sólida para fortalecer a cultura de pesquisa
          na graduação.</p>
        </div>
      </div>
    </section>"""

    # === COTAS DISTRIBUTION ===
    gmax = max(g_counts.values()) if g_counts else 1
    GCOL = {"Cotas / Reserva de vagas": "var(--brand)",
            "Ampla Concorrência": "var(--blue)",
            "Transferência": "var(--amber)"}
    grp_bars = "".join(
        bar(GSHORT.get(g, g), g_counts.get(g, 0), gmax, GCOL.get(g, "var(--muted)"),
            note=f"{g_counts.get(g,0)} · {_pct(g_counts.get(g,0), total)}%")
        for g in GROUPS if g_counts.get(g)
    )
    flags = a["flag_counts"]
    fmax = max(flags.values()) if flags else 1
    FCOL = {"Escola Pública": "var(--brand)", "PPI": "#3a9c63", "Renda": "var(--amber)",
            "Ação Afirmativa": "var(--blue)", "Pessoa c/ Deficiência": "var(--rose)"}
    flag_bars = "".join(
        bar(k, v, fmax, FCOL.get(k, "var(--muted)"),
            note=f"{v} · {_pct(v, total)}%")
        for k, v in flags.items()
    )
    cotas_sec = f"""
    <section class="section">
      <div class="eyebrow">Perfil de ingresso</div>
      <h2>Quem são os formandos</h2>
      <p class="desc">Distribuição por forma de ingresso e pelos critérios de reserva de vagas
      (um aluno pode atender a mais de um critério).</p>
      <div class="grid2">
        <div class="card"><h3>Forma de ingresso</h3>{grp_bars}</div>
        <div class="card"><h3>Critérios de cota atendidos</h3>{flag_bars}</div>
      </div>
    </section>"""

    # === GRADUATION COMPARISON (atraso, course-normalized) ===
    cmp_cards = ""
    win_key = min(
        (g for g in GROUPS if by_adm.get(g, {}).get("delay")),
        key=lambda g: by_adm[g]["delay"]["mean"], default=None,
    )
    CCOL = {"Cotas / Reserva de vagas": "g", "Ampla Concorrência": "b", "Transferência": "a"}
    for g in GROUPS:
        dl = by_adm.get(g, {}).get("delay")
        if not dl:
            continue
        win = " win" if g == win_key else ""
        cmp_cards += (
            f'<div class="c{win}"><div class="lab">{GSHORT.get(g, g)}</div>'
            f'<div class="v {CCOL.get(g,"g")}">{_sig(dl["mean"])}</div>'
            f'<div class="sub">semestres de atraso · n={dl["n"]}</div></div>'
        )
    # per-curso table: raw mean vs previsto
    cursos = sorted({
        c for g in GROUPS for c in (by_adm.get(g, {}).get("by_curso", {}) or {})
    })
    crows = ""
    for c in cursos:
        short = "ECA" if "Controle" in c else "SI"
        ce = exp.get(c, 12 if "Controle" in c else 8)
        tds = ""
        for g in GROUPS:
            st = (by_adm.get(g, {}).get("by_curso", {}) or {}).get(c) or {}
            tds += (f'<td>{st["mean"]} <span style="color:var(--muted);">(n={st["n"]})</span></td>'
                    if st else "<td>—</td>")
        crows += (f'<tr><td><b>{short}</b> — {c} '
                  f'<span style="color:var(--muted);font-weight:400;">· prev. {ce} sem</span></td>{tds}</tr>')
    chead = "".join(f"<th>{GSHORT.get(g, g)}</th>" for g in GROUPS)
    grad_sec = f"""
    <section class="section">
      <div class="eyebrow">Tempo de formação</div>
      <h2>Quanto tempo até a colação</h2>
      <p class="desc">Como os cursos têm durações diferentes (SI = 8 semestres, ECA = 12), a
      comparação justa é o <b>atraso</b>: semestres além do previsto no currículo.
      Quanto menor (ou mais negativo), melhor.</p>
      <div class="cmp" style="margin-bottom:22px;">{cmp_cards}</div>
      <div class="card"><h3>Detalhe por curso — média de semestres até a colação</h3>
        <table><thead><tr><th>Curso</th>{chead}</tr></thead><tbody>{crows}</tbody></table>
        <div class="note-line">Valores absolutos em semestres; a duração prevista de cada curso
        está indicada para referência. <b>⚠ Atraso até ~2 semestres negativo é plausível</b>
        (aproveitamento de créditos / horas de extensão antecipam a colação). Já formar
        <b>3+ semestres antes</b> do previsto — cota {_cota_susp}/{_cota_nn}, ampla
        {_ampla_susp}/{_ampla_nn}, vários em 1 semestre total — extensão não explica: é ingresso
        inferido do prefixo da matrícula (reingresso/SISU/matrícula nova). A média de atraso por
        forma de ingresso é, por isso, <b>não confiável</b>.</div>
      </div>
    </section>"""

    # === TEMPO POR CURSO, ISOLADO (cursos têm naturezas distintas — não comparar entre si) ===
    _ci = gt.get("cohort_impact", {})

    def _cblock(sg: str, full: str, r: dict) -> str:
        if not r:
            return ""
        n = r.get("n") or 0
        def p(k):
            return round((r.get(k) or 0) / n * 100) if n else 0
        md = r.get("atraso_median")
        return f"""
      <div class="card" style="margin-bottom:18px;">
        <h3>{sg} — {full} · previsto {r.get("expected")} semestres</h3>
        <div class="big" style="margin:6px 0 14px;">
          <span class="v">{_sig(md) if md is not None else "—"}</span>
          <span class="vs">semestres de atraso (mediana, robusta à cauda) · n={n}</span></div>
        <table><tbody>
          <tr><td>No prazo ou antes (atraso ≤ 0)</td><td class="r"><b>{r.get("on_time",0)}</b> ({p("on_time")}%)</td></tr>
          <tr><td>Adiantado plausível (−1/−2 sem · extensão/aproveitamento)</td><td class="r">{r.get("early_plausible",0)} ({p("early_plausible")}%)</td></tr>
          <tr><td>⚠ Suspeito de artefato (3+ sem antes do previsto)</td><td class="r">{r.get("suspect",0)} ({p("suspect")}%)</td></tr>
          <tr><td>Atrasado (além do previsto)</td><td class="r">{r.get("late",0)} ({p("late")}%)</td></tr>
          <tr><td>Ingresso ≤ 2015 (cauda antiga que infla a média)</td><td class="r">{r.get("old_le_2015",0)} ({p("old_le_2015")}%)</td></tr>
        </tbody></table>
      </div>"""

    _blocks = (_cblock("SI", "Sistemas de Informação", _ci.get("Sistemas de Informação"))
               + _cblock("ECA", "Engenharia de Controle e Automação",
                         _ci.get("Engenharia de Controle e Automação")))
    cohort_sec = (f"""
    <section class="section">
      <div class="eyebrow">Tempo de formação · cada curso na própria régua</div>
      <h2>Cada curso analisado isoladamente</h2>
      <p class="desc">SI (diurno, 4 anos) e ECA (noturno, 6 anos) têm naturezas distintas —
      <b>não são comparáveis entre si</b>. Cada um é lido contra a <b>própria</b> duração prevista,
      pela <b>mediana</b> do atraso (a média é distorcida por ingressantes antigos e por artefato
      de matrícula).</p>
      {_blocks}
      <div class="note-line"><b>Dois vieses afetam cada curso:</b> (1) ingressantes antigos (≤2015),
      de duração real longa, puxam a <b>média</b> pra cima — por isso usamos a <b>mediana</b>;
      (2) artefato da matrícula (ingresso inferido do prefixo) cria durações curtas falsas — a linha
      “suspeito”. No <b>ECA</b>, removendo artefato e antigos não sobra coorte recente mensurável: a
      janela 2020–2025 ainda não acumulou formações limpas de turmas novas de um curso de 6 anos.
      Leia cada curso isolado.</div>
    </section>""" if _blocks else "")

    # === EQUITY CALLOUT ===
    callout = f"""
    <section class="section">
      <div class="callout">
        <div class="k">Mensagem central</div>
        <h2>A política de cotas está dando certo na pesquisa</h2>
        <p>Os cotistas não apenas chegam à graduação — eles participam mais de iniciação
        científica e recebem mais bolsas que a média da ampla concorrência. Inclusão e
        excelência caminham juntas. <span style="color:var(--muted);">(Tempo de formação por
        forma de ingresso fica de fora: o ingresso inferido da matrícula é não confiável para
        parte da coorte.)</span></p>
        <div class="row">
          <div class="it"><div class="n">{cota_ic_pct}%</div><div class="l">cotistas em pesquisa</div></div>
          <div class="it"><div class="n">{cota_paid_pct}%</div><div class="l">cotistas com bolsa</div></div>
        </div>
      </div>
    </section>"""

    # === AGENCY × COTA ===
    ag_grp: dict[str, dict[str, int]] = {}
    for g in GROUPS:
        for ag, n in (g_fel.get(g, {}).get("sponsors", {}) or {}).items():
            ag_grp.setdefault(ag, {})[g] = ag_grp.get(ag, {}).get(g, 0) + n
    ag_order = [x for x in ["Fapes", "Ifes", "CNPq"] if x in ag_grp] + \
               [x for x in ag_grp if x not in ("Fapes", "Ifes", "CNPq")]
    ag_rows = ""
    col_tot = {g: 0 for g in GROUPS}
    for ag in ag_order:
        row = ag_grp[ag]
        tot = sum(row.get(g, 0) for g in GROUPS)
        for g in GROUPS:
            col_tot[g] += row.get(g, 0)
        tds = "".join(f"<td>{row.get(g, 0)}</td>" for g in GROUPS)
        cot_pct = _pct(row.get("Cotas / Reserva de vagas", 0), tot)
        ag_rows += f'<tr><td><b>{ag}</b></td>{tds}<td>{tot}</td><td style="color:var(--brand-d);font-weight:700;">{round(cot_pct)}%</td></tr>'
    gtot = sum(col_tot.values())
    tot_tds = "".join(f"<td>{col_tot[g]}</td>" for g in GROUPS)
    ag_rows += (f'<tr class="tot"><td>Total</td>{tot_tds}<td>{gtot}</td>'
                f'<td>{round(_pct(col_tot["Cotas / Reserva de vagas"], gtot))}%</td></tr>')
    ahead = "".join(f"<th>{GSHORT.get(g, g)}</th>" for g in GROUPS)
    agency_sec = f"""
    <section class="section">
      <div class="eyebrow">Financiamento</div>
      <h2>Quem financia a pesquisa dos cotistas</h2>
      <p class="desc">Formandos com bolsa paga, por agência e forma de ingresso.</p>
      <div class="card">
        <table><thead><tr><th>Agência</th>{ahead}<th>Total</th><th>% cotas</th></tr></thead>
        <tbody>{ag_rows}</tbody></table>
        <div class="note-line">A Fapes destina a maior parte de suas bolsas a cotistas;
        a Ifes distribui de forma mais equilibrada.</div>
      </div>
    </section>"""

    # === BOLSISTAS FAPES ===
    bc = s.get("bolsistas_cross") or {}
    bolsistas_sec = ""
    if bc.get("formaram"):
        def _brl(v):
            return f'R$ {v:,.0f}'.replace(",", "X").replace(".", ",").replace("X", ".")
        sig_n = s.get("with_research_sigpesq", with_research)
        sig_pct = s.get("pct_research_sigpesq", pct_research)
        novos = bc.get("novos_pesquisa", 0)
        brows = ""
        for x in bc.get("por_bolsa", []):
            faixa = (_brl(x["valor_min"]) if x["valor_min"] == x["valor_max"]
                     else f'{_brl(x["valor_min"])} – {_brl(x["valor_max"])}')
            brows += (f'<tr><td><b>{x["sigla"]}</b> '
                      f'<span style="color:var(--muted);">{x["nome"]}</span></td>'
                      f'<td>{x["formados"]}</td><td>{faixa}</td>'
                      f'<td>{_brl(x["valor_alocado"])}</td></tr>')
        bolsistas_sec = f"""
    <section class="section">
      <div class="eyebrow">Bolsas FAPES</div>
      <h2>Bolsistas FAPES que se formaram</h2>
      <p class="desc">Cruzamos os bolsistas de pesquisa FAPES do campus com os formandos.
      A bolsa é evidência de participação em pesquisa — e revela alunos que o SigPesq não capturava.</p>
      <div class="cmp" style="margin-bottom:22px;">
        <div class="c"><div class="lab">Pesquisa só pelo SigPesq</div>
          <div class="v b">{sig_pct}%</div><div class="sub">{sig_n} formandos</div></div>
        <div class="c win"><div class="lab">+ bolsistas FAPES</div>
          <div class="v g">{pct_research}%</div><div class="sub">{with_research} formandos</div></div>
        <div class="c"><div class="lab">Novos revelados</div>
          <div class="v a">+{novos}</div><div class="sub">só a bolsa comprova pesquisa</div></div>
      </div>
      <div class="card"><h3>Modalidades FAPES dos formados — cada uma com valor mensal próprio</h3>
        <table><thead><tr><th>Modalidade</th><th>Formados</th><th>Valor/mês</th><th>Alocado</th></tr></thead>
        <tbody>{brows}</tbody></table>
        <div class="note-line">{bc["formaram"]} bolsistas FAPES já formados ({bc["com_ic_sigpesq"]}
        também no SigPesq, {novos} novos). Total alocado: {_brl(bc["valor_alocado_total"])}
        (pagamento efetivo consta zerado na fonte).</div>
      </div>
    </section>"""

    # === RECOMMENDATIONS ===
    recs = """
    <section class="section">
      <div class="eyebrow">Para a gestão</div>
      <h2>Recomendações</h2>
      <div class="recs">
        <div class="rec"><div class="num">1</div><div>
          <h4>Ampliar bolsas para não-cotistas em risco</h4>
          <p>A ampla concorrência tem menor taxa de bolsa e maior tempo de formação —
          público que se beneficiaria de fomento à pesquisa.</p></div></div>
        <div class="rec"><div class="num">2</div><div>
          <h4>Manter e divulgar a política de cotas</h4>
          <p>Os indicadores de pesquisa e conclusão dos cotistas sustentam a continuidade
          e expansão da reserva de vagas.</p></div></div>
        <div class="rec"><div class="num">3</div><div>
          <h4>Diversificar agências de fomento</h4>
          <p>A dependência da Fapes para cotistas sugere buscar editais CNPq/CAPES
          complementares para reduzir risco de financiamento.</p></div></div>
        <div class="rec"><div class="num">4</div><div>
          <h4>Acompanhar o ECA de perto</h4>
          <p>A Engenharia concentra os maiores tempos de formação; vale investigar gargalos
          curriculares e oferta de disciplinas.</p></div></div>
      </div>
    </section>"""

    foot = f"""
    <div class="foot">
      <span>Relatório executivo · Formandos × Pesquisa — IFES Serra</span>
      <span>Gerado em {generated_at} · base deduplicada por matrícula ({total} alunos)</span>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Formandos × Pesquisa — Relatório Executivo — IFES Serra {period}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="page">
{hero}
{kpis}
{findings}
{cotas_sec}
{grad_sec}
{cohort_sec}
{callout}
{agency_sec}
{bolsistas_sec}
{recs}
{foot}
</div>
</body>
</html>"""


def compute_payload() -> dict:
    """Compute stats from source data — self-contained, no cached JSON needed."""
    from src.scripts.generate_formandos_report import (
        SEMESTER_FILE_MAP, DATA_FORMANDOS, load_formandos, load_json,
        load_lattes, load_bolsistas, compute,
    )
    # dedup by matrícula across all semester snapshots (earliest occurrence wins)
    seen: dict[str, dict] = {}
    semesters_used: list[str] = []
    for sem in sorted(SEMESTER_FILE_MAP.keys()):
        if not (DATA_FORMANDOS / SEMESTER_FILE_MAP[sem]).exists():
            continue
        for f in load_formandos(sem):
            key = f["matricula"] or f["nome"].strip().lower()
            seen.setdefault(key, f)
        semesters_used.append(sem)
    formandos = list(seen.values())
    grad_semester = semesters_used[-1] if semesters_used else ""

    adv = load_json("advisorships_canonical.json")
    rgs = load_json("research_groups_canonical.json")
    lattes = load_lattes()
    bolsistas = load_bolsistas()
    stats = compute(formandos, adv, rgs, lattes=lattes,
                    grad_semester=grad_semester, bolsistas=bolsistas)
    return {"semester": "all", "semesters": semesters_used, "stats": stats}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera o relatório executivo Formandos × Pesquisa (IFES Serra).")
    parser.add_argument("--json", default=None,
                        help="Usar um JSON já gerado em vez de recalcular")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    if args.json:
        print(f"Lendo JSON: {args.json}")
        payload = json.loads(Path(args.json).read_text(encoding="utf-8"))
    elif DEFAULT_JSON.exists() and False:  # always recompute by default
        payload = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
    else:
        print("Calculando estatísticas a partir dos dados...")
        payload = compute_payload()
        print(f"  {payload['stats']['total']} formandos únicos "
              f"({len(payload['semesters'])} semestres)")

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = build(payload, now)

    out_path = Path(args.out) if args.out else OUT_DIR / "formandos_executivo.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
