"""
Gera relatório HTML dos egressos do PPComp cruzando:
  - SigPesq (IC com bolsa)
  - Lattes dos professores (IC, TCC, projetos de pesquisa)
  - Bancas de mestrado nos CVs Lattes

Uso:
    python src/scripts/generate_mestrado_report.py
    python src/scripts/generate_mestrado_report.py --egressos data/mestrado/egressos_PPComp.xlsx
    python src/scripts/generate_mestrado_report.py --output data/exports/mestrado_ic_pesquisa.html
"""

import argparse
import glob
import json
import os
from collections import defaultdict
from datetime import datetime

import pandas as pd
from thefuzz import fuzz

# ── constantes ────────────────────────────────────────────────────────────────

DEFAULT_EGRESSOS = "data/mestrado/egressos_PPComp.xlsx"
DEFAULT_ADVISORSHIPS = "data/exports/advisorships_canonical.json"
DEFAULT_LATTES_DIR = "data/lattes_json"
DEFAULT_OUTPUT = "data/exports/mestrado_ic_pesquisa.html"

IC_PROGRAMS = {
    "PIBIC",
    "PIVIC",
    "PIBIT",
    "PIBITI",
    "PIBIC-AF",
    "PIBIC-EM",
    "PIBIC-JR",
    "PIVITI",
    "JTC",
}

FUZZY_THRESHOLD = 85

# ── carregamento de dados ─────────────────────────────────────────────────────


def load_egressos(path: str) -> list[str]:
    df = pd.read_excel(path, header=None)
    return list(dict.fromkeys(df[0].dropna().tolist()))


def load_sigpesq_ic(advisorships_path: str) -> defaultdict:
    with open(advisorships_path, encoding="utf-8") as f:
        data = json.load(f)
    mapping = defaultdict(list)
    for project in data:
        for adv in project.get("advisorships", []):
            fellowship = adv.get("fellowship") or {}
            if (
                adv.get("initiative_type") == "Advisorship"
                and fellowship.get("name", "") in IC_PROGRAMS
            ):
                mapping[adv.get("person_name", "").lower()].append(adv)
    return mapping


def load_sigpesq_rp(advisorships_path: str) -> defaultdict:
    with open(advisorships_path, encoding="utf-8") as f:
        data = json.load(f)
    mapping = defaultdict(list)
    for project in data:
        for adv in project.get("advisorships", []):
            if adv.get("initiative_type") == "Research Project":
                mapping[adv.get("person_name", "").lower()].append(adv)
    return mapping


def load_lattes_data(lattes_dir: str) -> tuple[list, list, list]:
    """Retorna (ic_records, tcc_records, banca_records) de todos os Lattes."""
    ic_records = []
    tcc_records = []
    banca_records = []

    for filepath in glob.glob(os.path.join(lattes_dir, "*.json")):
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        advisor = (
            data.get("nome")
            or data.get("name")
            or data.get("informacoes_pessoais", {}).get("nome_completo", "Desconhecido")
        )

        orientacoes = data.get("orientacoes", {})
        if isinstance(orientacoes, dict):
            for status_key, status_label in [
                ("concluidas", "Concluded"),
                ("em_andamento", "In Progress"),
            ]:
                section = orientacoes.get(status_key, {})
                if not isinstance(section, dict):
                    continue
                for tipo_key, items in section.items():
                    if not isinstance(items, list):
                        continue
                    for item in items:
                        orientando = (item.get("orientando") or "").strip()
                        if not orientando:
                            continue
                        rec = {
                            "orientando": orientando,
                            "advisor": advisor,
                            "status": status_label,
                            "ano_inicio": item.get("ano_inicio"),
                            "ano_conclusao": item.get("ano_conclusao"),
                            "titulo": item.get("titulo", ""),
                            "tipo_key": tipo_key,
                        }
                        if "iniciacao" in tipo_key:
                            ic_records.append(rec)
                        elif tipo_key == "tcc":
                            tcc_records.append(rec)

        bancas = data.get("bancas", {})
        if isinstance(bancas, dict):
            for banca_type, items in bancas.items():
                if banca_type not in ("mestrado", "doutorado"):
                    continue
                for item in items:
                    aluno = (item.get("aluno") or "").strip()
                    if aluno:
                        banca_records.append(
                            {
                                "aluno": aluno,
                                "advisor": advisor,
                                "tipo": banca_type,
                                "ano": item.get("ano"),
                                "titulo": str(
                                    item.get("titulo_trabalho")
                                    or item.get("descricao")
                                    or ""
                                ),
                            }
                        )

    return ic_records, tcc_records, banca_records


# ── matching ──────────────────────────────────────────────────────────────────


def fuzzy_list(name: str, records: list, key: str) -> list:
    return [
        r
        for r in records
        if fuzz.token_sort_ratio(name.lower(), r[key].lower()) >= FUZZY_THRESHOLD
    ]


def fuzzy_dict(name: str, mapping: defaultdict) -> list:
    out = []
    for k, records in mapping.items():
        if fuzz.token_sort_ratio(name.lower(), k) >= FUZZY_THRESHOLD:
            out.extend(records)
    return out


def build_results(
    egressos: list[str],
    sigpesq_ic: defaultdict,
    sigpesq_rp: defaultdict,
    lt_ic: list,
    lt_tcc: list,
    lt_bancas: list,
) -> list[dict]:
    results = []
    for name in egressos:
        sp_ic = fuzzy_dict(name, sigpesq_ic)
        lt_ic_ = fuzzy_list(name, lt_ic, "orientando")
        lt_tcc_ = fuzzy_list(name, lt_tcc, "orientando")
        lt_rp = fuzzy_dict(name, sigpesq_rp)
        bancas = fuzzy_list(name, lt_bancas, "aluno")

        results.append(
            {
                "name": name,
                "sp_ic": sp_ic,
                "lt_ic": lt_ic_,
                "lt_tcc": lt_tcc_,
                "lt_rp": lt_rp,
                "bancas": bancas,
                "has_ic": bool(sp_ic or lt_ic_),
                "has_tcc": bool(lt_tcc_),
                "has_rp": bool(lt_rp),
                "has_banca": bool(bancas),
            }
        )

    results.sort(
        key=lambda r: (
            (
                0
                if (r["has_ic"] and r["has_tcc"])
                else (
                    1
                    if r["has_ic"]
                    else (
                        2
                        if r["has_tcc"]
                        else 3 if r["has_rp"] else 4 if r["has_banca"] else 5
                    )
                )
            ),
            r["name"],
        )
    )
    return results


# ── helpers HTML ──────────────────────────────────────────────────────────────


def fmt_date(d) -> str:
    return str(d)[:10] if d else "—"


def status_chip(s: str) -> str:
    color = {"Concluded": "#22c55e", "In Progress": "#3b82f6", "Active": "#3b82f6"}.get(
        s, "#94a3b8"
    )
    return f'<span class="badge" style="background:{color}">{s or "—"}</span>'


def category_badges(r: dict) -> str:
    tags = []
    if r["sp_ic"]:
        tags.append('<span class="cat-badge cat-ic-sp">IC SigPesq</span>')
    if r["lt_ic"]:
        tags.append('<span class="cat-badge cat-ic-lt">IC Lattes</span>')
    if r["has_tcc"]:
        tags.append('<span class="cat-badge cat-tcc">TCC IFES</span>')
    if r["has_rp"]:
        tags.append('<span class="cat-badge cat-research">Pesquisa</span>')
    if r["has_banca"]:
        tags.append('<span class="cat-badge cat-banca">Defesa Mestrado</span>')
    if not tags:
        tags.append('<span class="cat-badge cat-none">Sem Registro</span>')
    return " ".join(tags)


def tbl_sp_ic(records: list) -> str:
    rows = "".join(
        f"""<tr>
      <td>{r.get('name','—')}</td>
      <td><span class="prog-badge">{(r.get('fellowship') or {}).get('name','—')}</span></td>
      <td>{r.get('supervisor_name','—')}</td>
      <td>{fmt_date(r.get('start_date'))}</td>
      <td>{fmt_date(r.get('end_date'))}</td>
      <td>{(r.get('fellowship') or {}).get('sponsor_name','—')}</td>
      <td>{status_chip(r.get('status'))}</td>
    </tr>"""
        for r in records
    )
    return f"""<div class="section-label ic-sp-label">IC — SigPesq (bolsa registrada)</div>
    <table class="detail-table"><thead><tr>
      <th>Título</th><th>Programa</th><th>Orientador</th>
      <th>Início</th><th>Fim</th><th>Patrocinador</th><th>Status</th>
    </tr></thead><tbody>{rows}</tbody></table>"""


def tbl_lt_orient(records: list, label: str, css: str) -> str:
    rows = "".join(
        f"""<tr>
      <td>{r.get('titulo','—')}</td>
      <td>{r.get('advisor','—')}</td>
      <td>{r.get('ano_inicio','—')}</td>
      <td>{r.get('ano_conclusao','—')}</td>
      <td>{status_chip(r.get('status'))}</td>
    </tr>"""
        for r in records
    )
    return f"""<div class="section-label {css}">{label}</div>
    <table class="detail-table"><thead><tr>
      <th>Título</th><th>Orientador</th><th>Início</th><th>Fim</th><th>Status</th>
    </tr></thead><tbody>{rows}</tbody></table>"""


def tbl_rp(records: list) -> str:
    rows = "".join(
        f"""<tr>
      <td>{r.get('name','—')}</td>
      <td>{r.get('supervisor_name','—')}</td>
      <td>{fmt_date(r.get('start_date'))}</td>
      <td>{fmt_date(r.get('end_date'))}</td>
      <td>{status_chip(r.get('status'))}</td>
    </tr>"""
        for r in records
    )
    return f"""<div class="section-label proj-label">Projetos de pesquisa (Lattes)</div>
    <table class="detail-table"><thead><tr>
      <th>Título</th><th>Orientador</th><th>Início</th><th>Fim</th><th>Status</th>
    </tr></thead><tbody>{rows}</tbody></table>"""


def tbl_bancas(records: list) -> str:
    by_thesis = defaultdict(lambda: {"titulo": "", "ano": None, "advisors": []})
    for b in records:
        key = (b["titulo"][:70].strip().lower(), b["ano"])
        by_thesis[key]["titulo"] = b["titulo"][:100]
        by_thesis[key]["ano"] = b["ano"]
        if b["advisor"] not in by_thesis[key]["advisors"]:
            by_thesis[key]["advisors"].append(b["advisor"])

    rows = "".join(
        f"""<tr>
      <td>{v['titulo'] or '—'}</td>
      <td>{v['ano'] or '—'}</td>
      <td style="font-size:.78rem;color:#5b21b6">{' · '.join(v['advisors'])}</td>
    </tr>"""
        for v in sorted(by_thesis.values(), key=lambda x: x["ano"] or 0, reverse=True)
    )
    return f"""<div class="section-label banca-label">Defesa de Mestrado (bancas nos CVs dos professores)</div>
    <table class="detail-table"><thead><tr>
      <th>Título da dissertação</th><th>Ano</th><th>Membros da banca</th>
    </tr></thead><tbody>{rows}</tbody></table>"""


def build_card(i: int, r: dict) -> str:
    body = ""
    if r["sp_ic"]:
        body += tbl_sp_ic(r["sp_ic"])
    if r["lt_ic"]:
        body += tbl_lt_orient(r["lt_ic"], "IC — Lattes dos professores", "ic-lt-label")
    if r["lt_tcc"]:
        body += tbl_lt_orient(r["lt_tcc"], "TCC — Lattes dos professores", "tcc-label")
    if r["lt_rp"]:
        body += tbl_rp(r["lt_rp"])
    if r["bancas"]:
        body += tbl_bancas(r["bancas"])
    if not body:
        body = '<div class="no-record">Sem registros em nenhuma fonte</div>'

    ic_n = len(r["sp_ic"]) + len(r["lt_ic"])
    tcc_n = len(r["lt_tcc"])
    banca_n = len({(b["titulo"][:50], b["ano"]) for b in r["bancas"]})
    rp_n = len(r["lt_rp"])

    return f"""<div class="person-card" id="p{i}">
  <div class="person-header">
    <div class="person-name">{r['name']}</div>
    <div class="person-meta">
      {category_badges(r)}
      <span class="cnt-pill">{ic_n} IC</span>
      <span class="cnt-pill">{tcc_n} TCC</span>
      <span class="cnt-pill">{rp_n} pesq.</span>
      <span class="cnt-pill">{banca_n} defesa(s)</span>
    </div>
  </div>
  <div class="person-body">{body}</div>
</div>"""


# ── geração HTML ──────────────────────────────────────────────────────────────

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#f8fafc;color:#1e293b}
header{background:#1e3a5f;color:#fff;padding:2rem 2.5rem}
header h1{font-size:1.55rem;font-weight:700}
header p{color:#94b4d4;font-size:.88rem;margin-top:.3rem}
.container{max-width:1200px;margin:0 auto;padding:2rem 1.5rem}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem;margin-bottom:1.75rem}
.stat-card{background:#fff;border-radius:10px;padding:1.1rem 1.4rem;box-shadow:0 1px 4px rgba(0,0,0,.07)}
.stat-card .n{font-size:2rem;font-weight:800}
.stat-card .lbl{font-size:.73rem;color:#64748b;text-transform:uppercase;letter-spacing:.04em;margin-top:.15rem}
.bl{border-left:4px solid #3b82f6}.gr{border-left:4px solid #22c55e}
.yw{border-left:4px solid #f59e0b}.pu{border-left:4px solid #8b5cf6}
.re{border-left:4px solid #ef4444}.or{border-left:4px solid #f97316}
.charts-row{display:flex;gap:1rem;margin-bottom:1.75rem;align-items:stretch;flex-wrap:wrap}
.chart-section{background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.07);padding:1.5rem 1.75rem}
.chart-title{font-size:1rem;font-weight:700;color:#1e293b;margin-bottom:1.25rem}
.chart-wrap{position:relative;height:320px}
.chart-legend{display:flex;gap:1.25rem;flex-wrap:wrap;margin-top:1rem;font-size:.78rem;color:#475569;align-items:center}
.cleg{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:middle;margin-right:3px}
.legend{font-size:.77rem;color:#64748b;background:#f1f5f9;padding:.75rem 1rem;border-radius:8px;line-height:2;margin-bottom:1.5rem}
.filters{display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:1.25rem}
.filter-btn{padding:.35rem .85rem;border-radius:20px;border:2px solid #e2e8f0;background:#fff;cursor:pointer;font-size:.8rem;font-weight:500;transition:all .15s}
.filter-btn:hover,.filter-btn.active{background:#1e3a5f;color:#fff;border-color:#1e3a5f}
.search-box{margin-bottom:1.25rem}
.search-box input{width:100%;padding:.6rem 1rem;border:2px solid #e2e8f0;border-radius:8px;font-size:.9rem;outline:none}
.search-box input:focus{border-color:#3b82f6}
.person-card{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.07);margin-bottom:.85rem;overflow:hidden}
.person-header{display:flex;align-items:center;justify-content:space-between;padding:.9rem 1.15rem;cursor:pointer;user-select:none;border-bottom:1px solid transparent;transition:background .15s;gap:.75rem;flex-wrap:wrap}
.person-header:hover{background:#f1f5f9}.person-header.open{border-bottom-color:#e2e8f0}
.person-name{font-weight:600;font-size:.97rem}
.person-meta{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap}
.person-body{padding:1.15rem;display:none}.person-body.open{display:block}
.cat-badge{padding:.22rem .6rem;border-radius:20px;font-size:.73rem;font-weight:600}
.cat-ic-sp{background:#dcfce7;color:#166534}.cat-ic-lt{background:#bbf7d0;color:#14532d}
.cat-tcc{background:#fef9c3;color:#713f12}.cat-research{background:#fef3c7;color:#92400e}
.cat-banca{background:#ede9fe;color:#5b21b6}.cat-none{background:#fee2e2;color:#991b1b}
.cnt-pill{font-size:.73rem;color:#64748b;background:#f1f5f9;padding:.18rem .48rem;border-radius:12px}
.badge{padding:.13rem .45rem;border-radius:10px;font-size:.7rem;color:#fff;font-weight:600}
.prog-badge{background:#1e3a5f;color:#fff;padding:.18rem .5rem;border-radius:10px;font-size:.73rem;font-weight:700}
.section-label{font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin:.85rem 0 .4rem;padding-bottom:.2rem;border-bottom:1px solid #f1f5f9}
.ic-sp-label{color:#166534}.ic-lt-label{color:#14532d}.tcc-label{color:#713f12}
.proj-label{color:#92400e}.banca-label{color:#5b21b6}
.detail-table{width:100%;border-collapse:collapse;font-size:.81rem;margin-bottom:.5rem}
.detail-table th{background:#f8fafc;padding:.42rem .7rem;text-align:left;font-size:.69rem;text-transform:uppercase;letter-spacing:.04em;color:#64748b;border-bottom:2px solid #e2e8f0}
.detail-table td{padding:.38rem .7rem;border-bottom:1px solid #f1f5f9;vertical-align:top}
.detail-table tr:last-child td{border-bottom:none}.detail-table tr:hover td{background:#f8fafc}
.no-record{color:#94a3b8;font-style:italic;font-size:.875rem;padding:.5rem 0}
"""

JS_FILTER = """
let cur='all';
document.querySelectorAll('.person-header').forEach(h=>{
  h.addEventListener('click',()=>{h.classList.toggle('open');h.nextElementSibling.classList.toggle('open')});
});
function sf(f,btn){cur=f;document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');fc()}
function fc(){
  const q=document.getElementById('srch').value.toLowerCase();
  document.querySelectorAll('.person-card').forEach(card=>{
    const name=card.querySelector('.person-name').textContent.toLowerCase();
    const bc=card.querySelector('.person-meta').innerHTML;
    let show=name.includes(q);
    if(show&&cur!=='all'){
      if(cur==='ic')    show=bc.includes('cat-ic');
      else if(cur==='ic-sp')  show=bc.includes('cat-ic-sp');
      else if(cur==='ic-lt')  show=bc.includes('cat-ic-lt');
      else if(cur==='tcc')    show=bc.includes('cat-tcc');
      else if(cur==='both')   show=bc.includes('cat-ic')&&bc.includes('cat-tcc');
      else if(cur==='banca')  show=bc.includes('cat-banca');
      else if(cur==='none')   show=bc.includes('cat-none');
    }
    card.style.display=show?'':'none';
  });
}
"""


def js_charts(stats: dict) -> str:
    total = stats["total"]
    n_ic = stats["n_ic"]
    n_sp = stats["n_sp"]
    n_lt_ic = stats["n_lt_ic"]
    n_tcc = stats["n_tcc"]
    n_both = stats["n_both"]
    n_banca = stats["n_banca"]
    n_none = stats["n_none"]
    n_no_ic_tcc = total - n_ic - n_tcc + n_both  # unique sem IC nem TCC

    pct_ifes = round((n_ic + n_tcc - n_both) / total * 100, 1)
    pct_nifes = round(100 - pct_ifes, 1)
    ifes_n = n_ic + n_tcc - n_both

    return f"""
Chart.register(ChartDataLabels);

// ── gráfico de barras ─────────────────────────────────────────────────────
const ctx1 = document.getElementById('barChart').getContext('2d');
new Chart(ctx1, {{
  type: 'bar',
  data: {{
    labels: [
      'IC no IFES\\n(pessoas únicas)',
      'TCC no IFES\\n(orientações dos prof.)',
      'IC + TCC',
      'Sem IC nem TCC',
      'Sem registro\\n(nenhuma fonte)',
    ],
    datasets: [{{
      data: [{n_ic}, {n_tcc}, {n_both}, {n_no_ic_tcc}, {n_none}],
      backgroundColor: ['#1e3a5f','#f59e0b','#0ea5e9','#94a3b8','#ef4444'],
      borderRadius: 6,
      borderSkipped: false,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          title: (items) => items[0].label.replace(/\\n/g,' '),
          afterBody: (items) => [
            ['SigPesq (1) + Lattes orientações (2)',
             'Lattes — orientações dos professores',
             'SigPesq + Lattes','SigPesq + Lattes','—'][items[0].dataIndex]
          ].map(s => 'Fonte: '+s),
        }}
      }},
      datalabels: {{
        anchor:'end', align:'end', offset:2,
        color:'#1e293b', font:{{ size:13, weight:'700' }},
        formatter: v => v,
      }},
    }},
    scales: {{
      x: {{
        grid: {{ display:false }},
        ticks: {{
          font:{{ size:11 }}, color:'#475569',
          callback(val) {{ return this.getLabelForValue(val).split('\\n'); }}
        }}
      }},
      y: {{
        beginAtZero:true, max:{n_no_ic_tcc + 8},
        grid:{{ color:'#f1f5f9' }},
        ticks:{{ stepSize:10, font:{{ size:11 }}, color:'#94a3b8' }},
        title:{{ display:true, text:'Nº de egressos', color:'#64748b', font:{{ size:11 }} }}
      }}
    }}
  }}
}});

// ── donut ─────────────────────────────────────────────────────────────────
const ctx2 = document.getElementById('pieChart').getContext('2d');
new Chart(ctx2, {{
  type: 'doughnut',
  data: {{
    labels: [
      'Vieram do IFES (IC ou TCC) — {pct_ifes}%',
      'Não fizeram IC nem TCC — {pct_nifes}%',
    ],
    datasets: [{{
      data: [{ifes_n}, {n_no_ic_tcc}],
      backgroundColor: ['#1e3a5f','#e2e8f0'],
      borderColor:     ['#1e3a5f','#cbd5e1'],
      borderWidth: 2,
      hoverOffset: 8,
    }}]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false, cutout:'62%',
    plugins: {{
      legend: {{
        display:true, position:'bottom',
        labels:{{ font:{{ size:11 }}, color:'#475569', padding:12, boxWidth:14 }}
      }},
      tooltip: {{
        callbacks: {{
          label: item => ` ${{item.label.split('—')[0].trim()}}: ${{item.raw}} alunos (${{item.label.split('—')[1].trim()}})`,
        }}
      }},
      datalabels: {{
        color: ctx => ctx.dataIndex===0 ? '#fff' : '#475569',
        font:{{ size:15, weight:'700' }},
        formatter: (v,ctx) => (v/ctx.chart.data.datasets[0].data.reduce((a,b)=>a+b,0)*100).toFixed(1)+'%',
      }},
    }},
  }}
}});
"""


def generate_html(results: list[dict], stats: dict, generated_at: str) -> str:
    total = stats["total"]
    n_ic = stats["n_ic"]
    n_sp = stats["n_sp"]
    n_lt_ic = stats["n_lt_ic"]
    n_tcc = stats["n_tcc"]
    n_both = stats["n_both"]
    n_banca = stats["n_banca"]
    n_none = stats["n_none"]

    cards_html = "\n".join(build_card(i, r) for i, r in enumerate(results))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Egressos PPComp — IC, TCC e Defesa</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>Egressos PPComp — IC, TCC e Defesa de Mestrado</h1>
  <p>Cruzamento: SigPesq · Lattes dos professores · Bancas · Projetos de pesquisa · Gerado em {generated_at}</p>
</header>
<div class="container">

<div class="stats-grid">
  <div class="stat-card bl"><div class="n">{total}</div><div class="lbl">Egressos únicos</div></div>
  <div class="stat-card gr"><div class="n">{n_ic}</div><div class="lbl">Fizeram IC (total)</div></div>
  <div class="stat-card gr"><div class="n">{n_sp}</div><div class="lbl">IC via SigPesq</div></div>
  <div class="stat-card gr"><div class="n">{n_lt_ic}</div><div class="lbl">IC via Lattes</div></div>
  <div class="stat-card yw"><div class="n">{n_tcc}</div><div class="lbl">TCC no IFES</div></div>
  <div class="stat-card or"><div class="n">{n_both}</div><div class="lbl">IC + TCC</div></div>
  <div class="stat-card pu"><div class="n">{n_banca}</div><div class="lbl">Defesa mestrado</div></div>
  <div class="stat-card re"><div class="n">{n_none}</div><div class="lbl">Sem registro</div></div>
</div>

<div class="charts-row">
  <div class="chart-section" style="flex:2">
    <h2 class="chart-title">Egressos por categoria e fonte dos dados</h2>
    <div class="chart-wrap"><canvas id="barChart"></canvas></div>
    <div class="chart-legend">
      <span class="cleg" style="background:#1e3a5f"></span> IC no IFES &nbsp;
      <span class="cleg" style="background:#f59e0b"></span> TCC no IFES &nbsp;
      <span class="cleg" style="background:#0ea5e9"></span> IC + TCC &nbsp;
      <span class="cleg" style="background:#94a3b8"></span> Sem IC nem TCC &nbsp;
      <span class="cleg" style="background:#ef4444"></span> Sem registro
    </div>
  </div>
  <div class="chart-section" style="flex:1">
    <h2 class="chart-title">Proporção: vieram do IFES?</h2>
    <div class="chart-wrap" style="height:260px"><canvas id="pieChart"></canvas></div>
  </div>
</div>

<div class="legend">
  <span class="cat-badge cat-ic-sp">IC SigPesq</span> Bolsa IC no SigPesq (PIBIC, PIVIC…) &nbsp;|&nbsp;
  <span class="cat-badge cat-ic-lt">IC Lattes</span> Orientação de IC nos CVs Lattes dos professores &nbsp;|&nbsp;
  <span class="cat-badge cat-tcc">TCC IFES</span> TCC orientado por professor do IFES (via Lattes) &nbsp;|&nbsp;
  <span class="cat-badge cat-research">Pesquisa</span> Projeto de pesquisa no Lattes (sem bolsa IC) &nbsp;|&nbsp;
  <span class="cat-badge cat-banca">Defesa Mestrado</span> Dissertação registrada nas bancas dos professores
</div>

<div class="search-box"><input id="srch" type="text" placeholder="Buscar egresso…" oninput="fc()"></div>
<div class="filters">
  <button class="filter-btn active" onclick="sf('all',this)">Todos ({total})</button>
  <button class="filter-btn" onclick="sf('ic',this)">IC ({n_ic})</button>
  <button class="filter-btn" onclick="sf('ic-sp',this)">IC SigPesq ({n_sp})</button>
  <button class="filter-btn" onclick="sf('ic-lt',this)">IC Lattes ({n_lt_ic})</button>
  <button class="filter-btn" onclick="sf('tcc',this)">TCC ({n_tcc})</button>
  <button class="filter-btn" onclick="sf('both',this)">IC+TCC ({n_both})</button>
  <button class="filter-btn" onclick="sf('banca',this)">Defesa ({n_banca})</button>
  <button class="filter-btn" onclick="sf('none',this)">Sem Registro ({n_none})</button>
</div>

<div id="cards">{cards_html}</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<script>
{js_charts(stats)}
{JS_FILTER}
</script>
</body>
</html>"""


# ── main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Gera relatório HTML dos egressos PPComp"
    )
    parser.add_argument("--egressos", default=DEFAULT_EGRESSOS)
    parser.add_argument("--advisorships", default=DEFAULT_ADVISORSHIPS)
    parser.add_argument("--lattes", default=DEFAULT_LATTES_DIR)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    print("Carregando dados…")
    egressos = load_egressos(args.egressos)
    sigpesq_ic = load_sigpesq_ic(args.advisorships)
    sigpesq_rp = load_sigpesq_rp(args.advisorships)
    lt_ic, lt_tcc, lt_bancas = load_lattes_data(args.lattes)

    print(
        f"  {len(egressos)} egressos · {len(lt_ic)} IC Lattes · {len(lt_tcc)} TCC Lattes · {len(lt_bancas)} bancas"
    )

    print("Cruzando nomes…")
    results = build_results(egressos, sigpesq_ic, sigpesq_rp, lt_ic, lt_tcc, lt_bancas)

    total = len(results)
    n_ic = sum(1 for r in results if r["has_ic"])
    n_sp = sum(1 for r in results if r["sp_ic"])
    n_lt_ic = sum(1 for r in results if r["lt_ic"])
    n_tcc = sum(1 for r in results if r["has_tcc"])
    n_both = sum(1 for r in results if r["has_ic"] and r["has_tcc"])
    n_banca = sum(1 for r in results if r["has_banca"])
    n_none = sum(
        1
        for r in results
        if not r["has_ic"]
        and not r["has_tcc"]
        and not r["has_rp"]
        and not r["has_banca"]
    )

    stats = dict(
        total=total,
        n_ic=n_ic,
        n_sp=n_sp,
        n_lt_ic=n_lt_ic,
        n_tcc=n_tcc,
        n_both=n_both,
        n_banca=n_banca,
        n_none=n_none,
    )

    print(
        f"  IC={n_ic} (SigPesq={n_sp}, Lattes={n_lt_ic}) · TCC={n_tcc} · IC+TCC={n_both} · sem nada={n_none}"
    )

    html = generate_html(results, stats, datetime.now().strftime("%d/%m/%Y %H:%M"))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Relatório salvo: {args.output} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
