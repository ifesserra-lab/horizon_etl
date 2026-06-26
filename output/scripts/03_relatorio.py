#!/usr/bin/env python3
"""Gera o relatório de ROI em HTML (a partir do Markdown) + um JSON do relatório.

- Lê output/relatorio_roi_pesquisa.md e converte para HTML standalone (sem libs externas
  no HTML; CSS embutido), com sumário navegável.
- Acrescenta uma seção "Artigos-fonte das métricas" (rastreabilidade): por docente, os
  principais artigos (OpenAlex, casados por DOI do Lattes) que sustentam as métricas
  científicas — cada título com DOI linka para o artigo.
- Escreve output/relatorio_roi_pesquisa.json: representação estruturada do relatório
  (metadados, métricas, candidatos a caso, referências e artigos-fonte).

Uso: python output/scripts/03_relatorio.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import sys
import markdown  # 3.x, com extensão 'tables'

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.scripts.didatica import bloco_metrica  # noqa: E402
OUT = ROOT / "output"
MD = OUT / "relatorio_roi_pesquisa.md"
INTER = OUT / "roi_intermediate.json"
PLANO = OUT / "plano_curto_prazo.json"
OPENALEX = ROOT / "data" / "exports" / "docentes" / "openalex_citacoes.json"
HTML = OUT / "relatorio_roi_pesquisa.html"
JSON_OUT = OUT / "relatorio_roi_pesquisa.json"

# Referências (estruturadas → entram no JSON; o MD já as traz em texto).
# "citações não verificadas nesta execução" (sem checagem automática de contagem).
REFERENCIAS = [
    {"autor": "Buxton, M.; Hanney, S.", "ano": 1996,
     "titulo": "How can payback from health services research be assessed?",
     "fonte": "J. Health Services Research & Policy 1(1):35-43",
     "doi": "10.1177/135581969600100107", "citacoes": "não verificadas nesta execução"},
    {"autor": "Canadian Academy of Health Sciences", "ano": 2009,
     "titulo": "Making an Impact: A Preferred Framework and Indicators to Measure Returns on Investment in Health Research (CAHS)",
     "fonte": "CAHS", "doi": None, "citacoes": "não verificadas nesta execução"},
    {"autor": "Hicks, D.; Wouters, P.; Waltman, L.; de Rijcke, S.; Rafols, I.", "ano": 2015,
     "titulo": "The Leiden Manifesto for research metrics",
     "fonte": "Nature 520:429-431", "doi": "10.1038/520429a",
     "citacoes": "não verificadas nesta execução"},
    {"autor": "DORA", "ano": 2012,
     "titulo": "San Francisco Declaration on Research Assessment",
     "fonte": "DORA", "doi": None, "citacoes": "não verificadas nesta execução"},
    {"autor": "CoARA", "ano": 2022,
     "titulo": "Agreement on Reforming Research Assessment",
     "fonte": "CoARA", "doi": None, "citacoes": "não verificadas nesta execução"},
    {"autor": "REF", "ano": 2021,
     "titulo": "Research Excellence Framework — guidance on submissions (impact case studies)",
     "fonte": "Research England", "doi": None, "citacoes": "não verificadas nesta execução"},
    {"autor": "Penfield, T.; Baker, M. J.; Scoble, R.; Wykes, M. C.", "ano": 2014,
     "titulo": "Assessment, evaluations, and definitions of research impact: A review",
     "fonte": "Research Evaluation 23(1):21-32", "doi": "10.1093/reseval/rvt021",
     "citacoes": "não verificadas nesta execução"},
    {"autor": "Greenhalgh, T. et al.", "ano": 2016,
     "titulo": "Research impact: a narrative review",
     "fonte": "BMC Medicine 14:78", "doi": "10.1186/s12916-016-0620-8",
     "citacoes": "não verificadas nesta execução"},
    {"autor": "Waltman, L.", "ano": 2016,
     "titulo": "A review of the literature on citation impact indicators",
     "fonte": "J. Informetrics 10(2):365-391", "doi": "10.1016/j.joi.2016.02.007",
     "citacoes": "não verificadas nesta execução"},
    {"autor": "Priem, J.; Piwowar, H.; Orr, R.", "ano": 2022,
     "titulo": "OpenAlex: A fully-open index of scholarly works",
     "fonte": "arXiv:2205.01833", "doi": "10.48550/arXiv.2205.01833",
     "citacoes": "não verificadas nesta execução"},
]


def _clean_doi(raw: str) -> str:
    m = re.search(r"10\.\d{4,9}/[^\s\"'<>&?]+", raw or "")
    return m.group(0) if m else ""


def artigos_fonte() -> list[dict]:
    """Por docente, os principais artigos (top_artigos do OpenAlex) que sustentam as
    métricas científicas. Fonte auditável das citações/FWCI/top 10%."""
    if not OPENALEX.exists():
        return []
    docs = json.loads(OPENALEX.read_text(encoding="utf-8"))["docentes"]
    out = []
    for d in docs:
        arts = d.get("top_artigos") or []
        if not arts:
            continue
        out.append({
            "docente": d["nome"], "lattes_id": d.get("lattes_id", ""),
            "citacoes_total": d.get("citacoes_total", 0), "h_index": d.get("h_index", 0),
            "artigos": [
                {"titulo": a.get("titulo", ""), "ano": a.get("ano"),
                 "citacoes": a.get("citacoes") or 0, "fwci": round(a.get("fwci", 0) or 0, 2),
                 "percentil": a.get("percentil") or 0, "doi": _clean_doi(a.get("doi", ""))}
                for a in arts
            ],
        })
    out.sort(key=lambda x: x["docente"].lower())
    return out


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def secao_artigos_html(fonte: list[dict]) -> str:
    n_doc = len(fonte)
    n_art = sum(len(d["artigos"]) for d in fonte)
    rows = ""
    for d in fonte:
        arts = sorted(d["artigos"], key=lambda a: -a["citacoes"])
        lis = ""
        for a in arts:
            t = _esc(a["titulo"]) or "(sem título)"
            ttl = (f'<a href="https://doi.org/{_esc(a["doi"])}" target="_blank" rel="noopener">{t}</a>'
                   if a["doi"] else t)
            tag = "top 1%" if a["percentil"] >= 99 else ("top 10%" if a["percentil"] >= 90 else "")
            badges = " · ".join(x for x in [f'{a["citacoes"]} cit',
                                            (f'FWCI {a["fwci"]}' if a["fwci"] else ""), tag] if x)
            lis += (f'<li><span class="yr">[{a["ano"] or "?"}]</span> {ttl} '
                    f'<span class="bdg">{badges}</span></li>')
        rows += (f'<details class="doc"><summary><b>{_esc(d["docente"])}</b> '
                 f'<span class="meta">{d["citacoes_total"]} citações · h={d["h_index"]} · '
                 f'{len(arts)} artigos-fonte</span></summary><ul>{lis}</ul></details>')
    return (f'<h2 id="artigos-fonte">Anexo — Artigos-fonte das métricas científicas</h2>'
            f'<p class="desc">Rastreabilidade: de quais artigos vêm as métricas científicas '
            f'(citações, FWCI, top 10%). Fonte: <b>OpenAlex</b>, casado por <b>DOI</b> do '
            f'Lattes — <b>{n_doc} docentes</b>, <b>{n_art} artigos</b>. Clique para expandir; '
            f'títulos com DOI linkam para o artigo.</p>'
            f'<div class="arts">{rows}</div>')


def referencias_html() -> str:
    items = ""
    for r in REFERENCIAS:
        doi = (f' · DOI: <a href="https://doi.org/{r["doi"]}" target="_blank" '
               f'rel="noopener">{r["doi"]}</a>' if r["doi"] else "")
        items += (f'<li><b>{_esc(r["autor"])}</b> ({r["ano"]}). <i>{_esc(r["titulo"])}</i>. '
                  f'{_esc(r["fonte"])}.{doi} '
                  f'<span class="cit">[citações: {r["citacoes"]}]</span></li>')
    return (f'<h2 id="referencias-estruturadas">Referências (estruturadas)</h2>'
            f'<ol class="refs">{items}</ol>')


CSS = """
:root{--ink:#16241a;--ink2:#3c4f42;--muted:#71857a;--line:#e3ece5;--line2:#cfddd3;
--bg:#f4f8f5;--paper:#fff;--brand:#0f7a40;--brand-d:#0a5c30;--brand-l:#e7f4ec;
--blue:#2f6fb0;--amber:#b8860b;--rose:#b5455f;
--font:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;--serif:'Georgia',serif;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);
line-height:1.6;font-size:15px;}
.page{max-width:980px;margin:0 auto;padding:0 22px 90px;}
.hero{padding:46px 0 24px;border-bottom:3px solid var(--brand);margin-bottom:8px;}
.hero .kick{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
color:var(--brand);background:var(--brand-l);padding:6px 13px;border-radius:999px;display:inline-block;}
h1{font-family:var(--serif);font-size:clamp(26px,4vw,40px);line-height:1.1;margin:16px 0 0;}
h2{font-family:var(--serif);font-size:23px;margin:38px 0 10px;padding-top:10px;
border-top:1px solid var(--line2);color:var(--brand-d);}
h3{font-size:17px;margin:24px 0 8px;color:var(--ink);}
h4{font-size:15px;margin:16px 0 6px;}
p,li{color:var(--ink2);} .desc{color:var(--muted);font-size:14px;}
a{color:var(--brand-d);} a:hover{color:var(--brand);}
blockquote{margin:16px 0;padding:12px 18px;background:#fffdf5;border-left:4px solid var(--amber);
border-radius:8px;font-size:14px;color:#5e4a12;}
blockquote p{color:#5e4a12;margin:6px 0;}
code{background:var(--brand-l);padding:1px 6px;border-radius:5px;font-size:13px;color:var(--brand-d);}
pre{background:#0f1a13;color:#d6ecdd;padding:14px 16px;border-radius:10px;overflow:auto;font-size:13px;}
pre code{background:none;color:inherit;padding:0;}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:13.5px;background:var(--paper);
border:1px solid var(--line);border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(16,40,24,.05);}
th{background:var(--brand-l);text-align:left;padding:9px 11px;font-size:12px;text-transform:uppercase;
letter-spacing:.03em;color:var(--brand-d);border-bottom:1px solid var(--line2);}
td{padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top;}
tr:last-child td{border-bottom:none;} tbody tr:hover{background:var(--bg);}
hr{border:none;border-top:1px solid var(--line2);margin:30px 0;}
.toc{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:16px 20px;
margin:22px 0;font-size:14px;} .toc ul{margin:6px 0;padding-left:20px;} .toc a{text-decoration:none;}
.tabbar{position:sticky;top:42px;z-index:50;display:flex;gap:8px;flex-wrap:wrap;
background:var(--bg);padding:14px 0 10px;margin:6px 0 4px;border-bottom:1px solid var(--line2);}
.tabbtn{font:inherit;font-size:14px;font-weight:600;padding:9px 18px;border:1px solid var(--line2);
background:var(--paper);color:var(--ink2);border-radius:999px;cursor:pointer;transition:all .12s;}
.tabbtn:hover{border-color:var(--brand);color:var(--brand-d);}
.tabbtn.active{background:var(--brand);color:#fff;border-color:var(--brand);box-shadow:0 2px 8px rgba(15,122,64,.25);}
.tabpanel[hidden]{display:none;}
.tabpanel>h2:first-child{border-top:none;padding-top:0;margin-top:18px;}
@media(max-width:680px){.tabbar{top:54px;gap:6px;}.tabbtn{padding:7px 13px;font-size:13px;}}
.arts .doc{background:var(--paper);border:1px solid var(--line);border-radius:10px;
margin:8px 0;padding:4px 14px;} .arts summary{cursor:pointer;padding:8px 0;font-size:14px;}
.arts summary .meta{color:var(--muted);font-size:12.5px;font-weight:400;}
.arts ul{margin:6px 0 12px;padding-left:18px;} .arts li{font-size:13px;padding:3px 0;line-height:1.4;}
.arts .yr{color:var(--muted);font-variant-numeric:tabular-nums;} .arts .bdg{color:var(--amber);font-size:11.5px;}
ol.refs li,.refs li{font-size:13.5px;margin:7px 0;} .cit{color:var(--muted);font-size:11.5px;}
@media print{body{background:#fff;}.page{max-width:none;}a{color:var(--ink);}}
@media(max-width:680px){table{display:block;overflow-x:auto;white-space:nowrap;}}
"""


_TABS = [("geral", "Visão geral"), ("metodo", "Metodologia"), ("analise", "Análise"),
         ("recom", "Recomendações"), ("anexos", "Anexos")]
_TABMAP_NUM = {1: "geral", 5: "geral", 6: "geral",
               2: "metodo", 3: "metodo", 4: "metodo",
               7: "analise", 8: "analise", 9: "analise", 10: "analise",
               11: "recom", 12: "recom", 13: "recom", 15: "recom", 14: "anexos"}
_TABMAP_ID = {"explicadores": "anexos", "artigos-fonte": "anexos",
              "referencias-estruturadas": "anexos"}


def build_tabs(body: str):
    """Divide o corpo (seções <h2>) em abas tipo dashboard. Retorna (preâmbulo, barra, painéis)."""
    parts = re.split(r"(?=<h2\b)", body)
    preamble = parts[0]
    panels = {t: "" for t, _ in _TABS}
    for sec in parts[1:]:
        m = re.match(r'<h2 id="([^"]*)">(.*?)</h2>', sec, re.S)
        hid = m.group(1) if m else ""
        txt = re.sub(r"<[^>]+>", "", m.group(2)) if m else ""
        num = re.match(r"\s*(\d+)", txt)
        tab = (_TABMAP_NUM.get(int(num.group(1))) if num else None) or _TABMAP_ID.get(hid) or "anexos"
        panels[tab] += sec
    btns = "".join(
        f'<button class="tabbtn{" active" if i == 0 else ""}" data-t="{t}">{label}</button>'
        for i, (t, label) in enumerate(_TABS))
    pans = "".join(
        f'<div class="tabpanel" id="tab-{t}"{"" if i == 0 else " hidden"}>{panels[t]}</div>'
        for i, (t, label) in enumerate(_TABS))
    return preamble, f'<nav class="tabbar">{btns}</nav>', pans


def main() -> None:
    md_text = MD.read_text(encoding="utf-8")
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"])
    body = md.convert(md_text)
    # remove o H1 duplicado (o cabeçalho/hero já traz o título)
    body = re.sub(r"^\s*<h1[^>]*>.*?</h1>", "", body, count=1, flags=re.S)

    body += '<h2 id="explicadores">Como ler as métricas (interpretação)</h2>'
    body += bloco_metrica({
        "titulo": "Razões de produtividade (produção por R$)",
        "o_que": "Indicadores que dividem a produção (itens científicos, titulados, ativos "
                 "tecnológicos) pelo <b>fomento de pesquisa consolidado</b> (ordem de grandeza).",
        "como_ler": "Dão uma <b>ordem de grandeza</b> institucional de 'quanto se produz por real "
                    "investido' — útil para comparar anos ou planejar, não para precisão contábil.",
        "nao_concluir": [
            "<b>Não é causalidade</b>: a produção do Lattes <b>não está ligada</b> a um projeto "
            "financiado específico — é uma proporção institucional bruta.",
            "Numerador (produção, carreira inteira) e denominador (fomento de um período) têm "
            "<b>janelas diferentes</b> — confiança baixa.",
        ],
        "gestores": "Usar como <b>ordem de grandeza</b> e tendência ao longo do tempo; nunca atribuir "
                    "a produtividade de um real a um docente ou projeto isolado.",
    })
    body += bloco_metrica({
        "titulo": "Concentração do fomento (Gini)",
        "o_que": "O quanto o orçamento de pesquisa se concentra em poucos coordenadores (Gini "
                 "0–1) — e o efeito de segregar projetos institucionais (UnAC/ConectaFapes).",
        "formula": "Gini: 0 = igual entre coordenadores · 1 = um concentra tudo",
        "como_ler": "Gini alto = captação concentrada num núcleo. Parte da concentração é "
                    "<b>infraestrutura/programa</b> (não captação individual) — por isso reportamos "
                    "também o Gini <b>sem os institucionais</b>.",
        "nao_concluir": [
            "Concentração de captação <b>não</b> mede esforço nem mérito individual.",
            "Projetos <b>institucionais/programáticos</b> (UnAC, ConectaFapes) inflam o Gini 'por "
            "coordenador' — separá-los é essencial.",
        ],
        "gestores": "Diversificar a base de captação; apoiar novos coordenadores; separar sempre "
                    "fomento <b>institucional</b> de <b>pesquisa individual</b>.",
    })

    fonte = artigos_fonte()
    body += secao_artigos_html(fonte)
    body += referencias_html()
    preamble, tabbar, panels = build_tabs(body)

    page = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatório de ROI e Impacto da Pesquisa — IFES Campus Serra</title>
<style>{CSS}</style></head><body>
<div id="exp-banner" style="background:#b5455f;color:#fff;padding:10px 16px;font:600 14px/1.45 var(--font);text-align:center;position:sticky;top:0;z-index:9999;box-shadow:0 2px 6px rgba(0,0,0,.2);">⚠️ Estudo experimental em condução — os dados são preliminares e podem ser modificados. Não usar como fonte da verdade.</div>
<div class="page">
<header class="hero"><span class="kick">IFES Campus Serra · Diretoria de Pesquisa</span>
<h1>Relatório de ROI e Impacto da Pesquisa</h1></header>
{preamble}
{tabbar}
{panels}
</div>
<script>
(function(){{
  var btns=[].slice.call(document.querySelectorAll('.tabbtn'));
  btns.forEach(function(b){{
    b.addEventListener('click',function(){{
      btns.forEach(function(x){{x.classList.toggle('active',x===b);}});
      document.querySelectorAll('.tabpanel').forEach(function(p){{p.hidden=(p.id!=='tab-'+b.dataset.t);}});
      var bar=document.querySelector('.tabbar');
      window.scrollTo({{top:(bar?bar.offsetTop-70:0),behavior:'smooth'}});
    }});
  }});
}})();
</script>
</body></html>"""
    HTML.write_text(page, encoding="utf-8")

    # ---- JSON do relatório ----
    inter = json.loads(INTER.read_text(encoding="utf-8")) if INTER.exists() else {}
    relatorio_json = {
        "meta": {
            "titulo": "Relatório de ROI e Impacto da Pesquisa",
            "instituicao": "IFES — Campus Serra",
            "unidade_analise": "93 docentes (roster oficial)",
            "frameworks": ["Payback", "CAHS", "Bibliometria responsável",
                           "Monetização seletiva", "Estudos de caso REF"],
            "convencao_evidencia": {"O": "Observado", "I": "Inferido", "A": "Ausente"},
            "aviso": "ROI financeiro (%) não calculável: sem benefícios monetizados. "
                     "Citações cobrem 64/93 (OpenAlex por DOI). Impacto social ausente.",
        },
        "secoes": [
            "1. Sumário executivo", "2. Objetivo e escopo", "3. Dados utilizados",
            "4. Metodologia", "5. Painel de métricas", "6. Indicadores calculados",
            "7. Enriquecimento externo", "8. Matriz Payback/CAHS",
            "9. Monetização seletiva", "10. Estudos de caso REF",
            "11. Recomendações", "12. Limitações e riscos", "13. Plano de implementação",
            "14. Referências",
        ],
        "inputs": inter.get("fapes", {}),
        "fapes_top_coordenadores": inter.get("fapes_top_coord", []),
        "bolsas": inter.get("bolsas", {}),
        "facto": inter.get("facto", {}),
        "producao": inter.get("producao", {}),
        "openalex": inter.get("openalex", {}),
        "ppcomp": inter.get("ppcomp", {}),
        "derivados": inter.get("derivados", {}),
        "metricas": inter.get("metricas", []),
        "candidatos_estudo_caso": inter.get("candidatos_caso", []),
        "plano_curto_prazo": (json.loads(PLANO.read_text(encoding="utf-8"))
                              if PLANO.exists() else {}),
        "referencias": REFERENCIAS,
        "artigos_fonte": fonte,
        "arquivos": [
            "relatorio_roi_pesquisa.md", "relatorio_roi_pesquisa.html",
            "relatorio_roi_pesquisa.json", "metricas_roi_pesquisa.csv",
            "matriz_payback_cahs.csv", "por_coordenador.csv", "dicionario_dados.md",
            "estudos_de_caso_ref.md", "lacunas_e_recomendacoes.md", "roi_intermediate.json",
        ],
    }
    JSON_OUT.write_text(json.dumps(relatorio_json, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK -> {HTML.relative_to(ROOT)} ({len(page):,} bytes)")
    print(f"OK -> {JSON_OUT.relative_to(ROOT)}")
    print(f"Artigos-fonte: {len(fonte)} docentes · "
          f"{sum(len(d['artigos']) for d in fonte)} artigos · {len(REFERENCIAS)} referências")


if __name__ == "__main__":
    main()
