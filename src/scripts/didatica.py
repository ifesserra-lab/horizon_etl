"""Componentes didáticos reutilizáveis para os relatórios institucionais.

Dois formatos (ambos colapsáveis, estilo inline com fallback de cores):

  bloco_didatico(d)  — 10 elementos, para relatórios de FORMAÇÃO (tem "para
                       estudantes / professores"). Diferencia evidência,
                       hipótese e recomendação; não afirma causalidade.

  bloco_metrica(d)   — "explicador de métrica", para relatórios BIBLIOMÉTRICOS
                       /de gestão: o que mostra · como ler · o que NÃO concluir ·
                       para gestores. Mais enxuto, sem "para estudantes".

As cores usam var(--brand)…; se a página não definir as variáveis, há fallback.
"""
from __future__ import annotations

# paleta com fallback (caso a página não tenha as variáveis CSS)
_BRAND = "var(--brand,#0f7a40)"
_BRAND_D = "var(--brand-d,#0a5c30)"
_BRAND_L = "var(--brand-l,#e7f4ec)"
_INK = "var(--ink,#16241a)"
_MUT = "var(--muted,#71857a)"
_LINE = "var(--line,#e3ece5)"
_PAPER = "var(--paper,#fff)"

_IC = (f"width:28px;height:28px;flex:0 0 28px;border-radius:8px;background:{_BRAND_L};"
       f"color:{_BRAND_D};display:grid;place-items:center;font-size:14px;font-weight:800;")
_BOXBASE = ("border-radius:10px;padding:11px 14px;margin:10px 0;font-size:13.5px;"
            "border-left:4px solid;line-height:1.5;")
_EV = f"{_BOXBASE}background:{_BRAND_L};border-color:{_BRAND};color:#14361f;"
_HIP = f"{_BOXBASE}background:#fbf4df;border-color:#b8860b;color:#5e4a12;"
_REC = f"{_BOXBASE}background:#eaf1f9;border-color:#2f6fb0;color:#1f4d7a;"
_WARN = f"{_BOXBASE}background:#f8e9ed;border-color:#b5455f;color:#7a2536;"
_TAG = ("display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;"
        "letter-spacing:.03em;text-transform:uppercase;padding:2px 8px;border-radius:5px;")
_CENTRAL = ("background:linear-gradient(180deg,#0f7a40,#0a5c30);color:#fff;border-radius:12px;"
            "padding:16px 18px;font-size:15.5px;line-height:1.5;")


# CSS responsivo compartilhado (mobile-first): empilha grids/barras, contém tabelas,
# escala SVG/imagens, reduz padding e tipografia em telas pequenas. Anexar ao <style> de
# cada relatório: f"<style>{CSS}{MOBILE_CSS}</style>".
MOBILE_CSS = """
/* ---- mobile-first (responsivo, sem rolagem horizontal de página) ---- */
*{max-width:100%;}
img,svg{max-width:100%;height:auto;}
.tbl-wrap,.table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;}
@media (max-width:720px){
  html,body{overflow-x:hidden;}
  .page,.wrap{padding-left:14px!important;padding-right:14px!important;}
  /* grids comuns -> 1 coluna */
  .kpis,.grid2,.grid,.grid3,.refs,.lorenz-wrap,.quads,.compare,.af-chips,
  .rz-stats,.rz-cards,.cards,.two-col{grid-template-columns:1fr!important;}
  /* barras com grid fixo (label|trilho|valor) -> empilha */
  .bar,.brow,.frow{grid-template-columns:1fr!important;gap:3px 0!important;}
  .bar .val,.bar .bv,.brow .bv,.frow .fv{text-align:left!important;}
  /* tabelas largas: rolam dentro do próprio bloco, não na página */
  .section table,.card table,table{display:block;width:100%;overflow-x:auto;
    -webkit-overflow-scrolling:touch;white-space:normal;}
  .af-tbl{display:table!important;}              /* exceção: quadro de artigos já é fixo */
  th,td{font-size:12.5px;padding:7px 8px;}
  h1{font-size:24px!important;line-height:1.15;}
  h2{font-size:20px!important;}
  .hero{padding:34px 0 20px!important;}
  .lede{font-size:15px!important;}
  /* abas (ROI) */
  .tabbar{gap:6px;} .tabbtn{padding:7px 12px;font-size:13px;}
  /* blocos didáticos: recuo menor */
  details [style*="padding-left:38px"]{padding-left:0!important;}
}
"""


def _el(num, titulo, corpo, extra=""):
    return (f'<div style="margin-top:18px;"><div style="display:flex;gap:10px;align-items:center;'
            f'margin-bottom:5px;"><span style="{_IC}">{num}</span>'
            f'<span style="font-size:16px;font-weight:700;color:{_INK};">{titulo}</span>'
            f'</div><div style="padding-left:38px;">{corpo}{extra}</div></div>')


def _ul(items):
    return ('<ul style="margin:4px 0 0 4px;padding-left:18px;">'
            + "".join(f"<li>{x}</li>" for x in items) + "</ul>")


def _details(summary, legenda_html, inner):
    return f"""
      <details style="background:{_PAPER};border:1px solid {_LINE};border-radius:12px;
        padding:4px 18px;margin:14px 0;box-shadow:0 1px 3px rgba(16,40,24,.05);">
        <summary style="cursor:pointer;padding:12px 0;font-weight:700;font-size:15px;color:{_BRAND_D};">
          {summary}</summary>
        {legenda_html}
        {inner}
      </details>"""


def _legenda_full():
    return (f'<div style="display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:{_MUT};margin:2px 0 8px;">'
            f'<span style="{_TAG}background:{_BRAND_L};color:{_BRAND_D};">Evidência</span> medido nos dados'
            f'<span style="{_TAG}background:#fbf4df;color:#7a5b06;">Hipótese</span> plausível'
            f'<span style="{_TAG}background:#eaf1f9;color:#1f4d7a;">Recomendação</span> ação sugerida</div>')


def bloco_didatico(d: dict) -> str:
    """10 elementos (formação). Chaves: titulo, analisa, importa, mostram, evidencia?,
    interpretar, atencao?, cuidados(list), pesquisadores, recomendacao?, professores,
    hipotese?, estudantes, central, acoes(list)."""
    ev = f'<div style="{_EV}"><b>Evidência:</b> {d["evidencia"]}</div>' if d.get("evidencia") else ""
    at = f'<div style="{_HIP}"><b>Atenção — associação, não causa:</b> {d["atencao"]}</div>' if d.get("atencao") else ""
    rec = f'<div style="{_REC}"><b>Recomendação:</b> {d["recomendacao"]}</div>' if d.get("recomendacao") else ""
    hip = f'<div style="{_HIP}"><b>Hipótese a confirmar:</b> {d["hipotese"]}</div>' if d.get("hipotese") else ""
    central = f'<div style="{_CENTRAL}">{d["central"]}</div>'
    inner = (
        _el(1, "O que esta seção analisa", d["analisa"])
        + _el(2, "Por que é importante", d["importa"])
        + _el(3, "O que os dados mostram", d["mostram"], ev)
        + _el(4, "Como interpretar", d["interpretar"], at)
        + _el(5, "Cuidados de interpretação", _ul(d["cuidados"]))
        + _el(6, "Para pesquisadores", d["pesquisadores"], rec)
        + _el(7, "Para professores", d["professores"], hip)
        + _el(8, "Para estudantes", d["estudantes"])
        + _el(9, "Mensagem central", central)
        + _el(10, "Possíveis ações", _ul(d["acoes"]))
    )
    return _details(f'📖 Entenda esta seção — {d["titulo"]}', _legenda_full(), inner)


def bloco_metrica(d: dict) -> str:
    """Explicador de métrica (bibliométrico/gestão). Chaves: titulo, o_que, como_ler,
    nao_concluir(list), gestores, evidencia?, formula?(str)."""
    n = 0
    partes = []

    def _add(titulo, corpo, extra=""):
        nonlocal n
        n += 1
        partes.append(_el(n, titulo, corpo, extra))

    ev = f'<div style="{_EV}"><b>Evidência:</b> {d["evidencia"]}</div>' if d.get("evidencia") else ""
    _add("O que esta seção mostra", d["o_que"], ev)
    if d.get("formula"):
        _add("Como é calculada",
             f'<span style="font-family:Georgia,serif;background:{_BRAND_L};border-radius:6px;'
             f'padding:3px 9px;display:inline-block;">{d["formula"]}</span>')
    _add("Como ler", d["como_ler"])
    _add("O que NÃO concluir",
         _ul(d["nao_concluir"]) + f'<div style="{_WARN}">Métricas isoladas enganam: '
         "leia em conjunto e com juízo qualitativo (Manifesto de Leiden).</div>")
    _add("Para gestores", d["gestores"])
    legenda = (f'<div style="display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:{_MUT};margin:2px 0 8px;">'
               f'<span style="{_TAG}background:{_BRAND_L};color:{_BRAND_D};">Evidência</span> medido'
               f'<span style="{_TAG}background:#f8e9ed;color:#7a2536;">Cuidado</span> o que evitar</div>')
    return _details(f'📊 Como ler esta seção — {d["titulo"]}', legenda, "".join(partes))
