"""
Citações e h-index dos docentes via OpenAlex — casadas por DOI (Lattes).

Para cada docente do roster, coleta os DOIs dos artigos no Lattes, consulta o
OpenAlex em lote (cited_by_count por obra) e agrega por docente:
  - citações totais, h-index, i10-index (calculados das citações por artigo)
  - nº de artigos com DOI, quantos foram encontrados no OpenAlex
  - artigos mais citados

DOI é casamento 1:1 (sem ambiguidade de homônimo). OpenAlex é aberto, sem chave.

Uso:
  python -m src.scripts.fetch_openalex_citations
  python -m src.scripts.fetch_openalex_citations --out data/exports/docentes/openalex_citacoes.json
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.scripts.generate_docentes_executive import ROSTER_IDS

BASE = Path(__file__).resolve().parents[2]
LATTES_DIR = BASE / "data" / "lattes_json"
OUT_DIR = BASE / "data" / "exports" / "docentes"
DEFAULT_OUT = OUT_DIR / "openalex_citacoes.json"
MAILTO = "paulo.junior@conecta.academy"   # polite pool do OpenAlex
BATCH = 40


def clean_doi(raw: str) -> str | None:
    if not raw:
        return None
    m = re.search(r"10\.\d{4,9}/\S+", raw.strip())
    if not m:
        return None
    return m.group(0).rstrip(" .,;)").lower()


def _get(url: str) -> dict:
    req = Request(url, headers={"User-Agent": f"ifes-serra-research/1.0 (mailto:{MAILTO})"})
    with urlopen(req, timeout=60) as r:
        return json.load(r)


def collect_dois() -> tuple[dict, dict]:
    """Retorna (docente_id -> [dois], doi -> set(docente_ids))."""
    by_id = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f
    doc_dois: dict[str, list] = defaultdict(list)
    doi_docs: dict[str, set] = defaultdict(set)
    for nome, lid in ROSTER_IDS.items():
        f = by_id.get(lid)
        if not f:
            continue
        for a in (json.loads(Path(f).read_text()).get("producao_bibliografica", {}) or {}) \
                .get("artigos_periodicos", []) or []:
            cd = clean_doi(a.get("doi", ""))
            if cd:
                doc_dois[lid].append(cd)
                doi_docs[cd].add(lid)
    return doc_dois, doi_docs


def fetch_citations(dois: list[str], sleep: float = 0.4) -> dict:
    """doi -> {cit, title, year}. Lote via filtro OR do OpenAlex."""
    out: dict[str, dict] = {}
    uniq = sorted(set(dois))
    for i in range(0, len(uniq), BATCH):
        chunk = uniq[i:i + BATCH]
        flt = "doi:" + "|".join(chunk)
        url = ("https://api.openalex.org/works?per-page=200&mailto=" + MAILTO
               + "&select=doi,cited_by_count,title,publication_year,fwci,"
               + "cited_by_percentile_year,counts_by_year,authorships&filter="
               + quote(flt, safe="|:/."))
        try:
            data = _get(url)
        except Exception as exc:
            print(f"  lote {i//BATCH+1}: ERRO {exc}")
            time.sleep(sleep)
            continue
        for w in data.get("results", []):
            wdoi = clean_doi(w.get("doi", "") or "")
            if wdoi:
                pct = (w.get("cited_by_percentile_year") or {}).get("min")
                by_year = {c.get("year"): c.get("cited_by_count", 0)
                           for c in (w.get("counts_by_year") or []) if c.get("year")}
                recent = sum(v for y, v in by_year.items() if y >= 2024)
                out[wdoi] = {"cit": w.get("cited_by_count", 0),
                             "title": w.get("title", ""),
                             "year": w.get("publication_year"),
                             "fwci": w.get("fwci"),
                             "pct": pct, "recent": recent, "by_year": by_year,
                             "n_authors": len(w.get("authorships") or []) or 1}
        print(f"  lote {i//BATCH+1}/{(len(uniq)+BATCH-1)//BATCH}: {len(chunk)} DOIs → {len(data.get('results',[]))} achados")
        time.sleep(sleep)
    return out


def h_index(cits: list[int]) -> int:
    """Hirsch (2005): maior h com h artigos de >= h citações cada."""
    h = 0
    for i, c in enumerate(sorted(cits, reverse=True), 1):
        if c >= i:
            h = i
        else:
            break
    return h


def _artigo_ascensao(found: list) -> dict | None:
    """Artigo em ascensao do docente = o que mais recebeu citacoes nos ultimos 2
    anos (counts_by_year). Sinaliza o trabalho mais 'quente' no momento."""
    if not found:
        return None
    d, c = max(found, key=lambda x: x[1].get("recent", 0))
    if c.get("recent", 0) <= 0:
        return None
    cit = c.get("cit", 0) or 0
    return {
        "titulo": (c.get("title") or "")[:120],
        "ano": c.get("year"),
        "recent_2a": c.get("recent", 0),
        "citacoes": cit,
        "share_recente_pct": round(c.get("recent", 0) / cit * 100) if cit else 0,
        "fwci": c.get("fwci"),
        "doi": d,
    }


def g_index(cits: list[int]) -> int:
    """Egghe (2006): maior g tal que os g artigos mais citados somem >= g²
    citações. Dá mais peso aos trabalhos muito citados que o h-index."""
    s = sorted(cits, reverse=True)
    acc = best = 0
    for g, c in enumerate(s, 1):
        acc += c
        if acc >= g * g:
            best = g
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()

    doc_dois, doi_docs = collect_dois()
    all_dois = sorted(doi_docs)
    print(f"Docentes com DOI: {len(doc_dois)} · DOIs únicos: {len(all_dois)}")
    cit_map = fetch_citations(all_dois, args.sleep)
    print(f"Citações obtidas p/ {len(cit_map)}/{len(all_dois)} DOIs")

    rows = []
    for lid, nome in ((v, k) for k, v in ROSTER_IDS.items()):
        dois = doc_dois.get(lid, [])
        found = [(d, cit_map[d]) for d in dict.fromkeys(dois) if d in cit_map]  # dedup, achados
        cits = [c["cit"] for _, c in found]
        total = sum(cits)
        top = sorted(found, key=lambda x: -x[1]["cit"])[:8]
        # qualidade de citação
        def _median(vals):
            s = sorted(vals); n = len(s)
            if not s:
                return 0.0
            return round(s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2, 2)
        fwcis = [c["fwci"] for _, c in found if c.get("fwci") is not None]
        fwci_mean = round(sum(fwcis) / len(fwcis), 2) if fwcis else 0.0
        fwci_med = _median(fwcis)
        # FWCI por janela (ascensão de impacto): 2016-2020 vs 2021-2025
        old_fw = [c["fwci"] for _, c in found if c.get("fwci") is not None
                  and 2016 <= (c.get("year") or 0) <= 2020]
        new_fw = [c["fwci"] for _, c in found if c.get("fwci") is not None
                  and 2021 <= (c.get("year") or 0) <= 2025]
        fwci_antigo = _median(old_fw) if len(old_fw) >= 2 else None
        fwci_recente = _median(new_fw) if len(new_fw) >= 2 else None
        fwci_delta = (round(fwci_recente - fwci_antigo, 2)
                      if fwci_antigo is not None and fwci_recente is not None else None)
        pcts = [c["pct"] for _, c in found if c.get("pct") is not None]
        top10 = sum(1 for p in pcts if p >= 90)
        top1 = sum(1 for p in pcts if p >= 99)
        recent_cit = sum(c.get("recent", 0) for _, c in found)
        # série de citações por ano (agregada de todos os artigos) → sparkline
        por_ano: dict[int, int] = {}
        for _, c in found:
            for y, v in (c.get("by_year") or {}).items():
                por_ano[y] = por_ano.get(y, 0) + v
        citacoes_por_ano = {str(y): por_ano[y] for y in sorted(por_ano)}
        # h, g (núcleo citado e concentração de impacto)
        h = h_index(cits)
        g = g_index(cits)
        # m-index = h / idade acadêmica (anos desde a 1ª publicação com DOI no OpenAlex).
        # Proxy: usa só artigos com DOI — pode subestimar a idade de quem publicou antes
        # de adotar DOI. Corrige o viés de antiguidade do h (Hirsch, 2005).
        anos_found = [c.get("year") for _, c in found if c.get("year")]
        idade = (datetime.now().year - min(anos_found)) if anos_found else 0
        m_idx = round(h / idade, 2) if idade else 0.0
        # citações por artigo (intensidade média) + mediana (robusta a 1 artigo viral)
        cpp = round(total / len(found), 1) if found else 0.0
        cit_med = _median(cits)
        # crédito fracionado por autoria (corrige hipercoautoria): 1/n_autores por
        # artigo e citações/n_autores por artigo (Waltman & van Eck, 2015).
        n_auts = [max(int(c.get("n_authors") or 1), 1) for _, c in found]
        art_frac = round(sum(1.0 / n for n in n_auts), 2) if n_auts else 0.0
        cit_frac = round(sum(c["cit"] / max(int(c.get("n_authors") or 1), 1)
                             for _, c in found), 1) if found else 0.0
        rows.append({
            "nome": nome, "lattes_id": lid,
            "artigos_com_doi": len(set(dois)),
            "encontrados_openalex": len(found),
            "citacoes_total": total,
            "h_index": h,
            "g_index": g,
            "m_index": m_idx,
            "idade_academica": idade,
            "citacoes_por_artigo": cpp,
            "citacoes_mediana": cit_med,
            "artigos_fracionados": art_frac,
            "citacoes_fracionadas": cit_frac,
            "i10": sum(1 for c in cits if c >= 10),
            "mais_citado": max(cits) if cits else 0,
            "fwci_medio": fwci_mean,
            "fwci_mediana": fwci_med,
            "fwci_antigo": fwci_antigo, "fwci_recente": fwci_recente, "fwci_delta": fwci_delta,
            "artigos_top10pct": top10,
            "artigos_top1pct": top1,
            "citacoes_recentes_2a": recent_cit,
            "momentum_pct": round(recent_cit / total * 100) if total else 0,
            "citacoes_por_ano": citacoes_por_ano,
            "artigo_ascensao": _artigo_ascensao(found),
            "top_artigos": [{"titulo": (c["title"] or "")[:90], "ano": c["year"],
                             "citacoes": c["cit"], "fwci": c.get("fwci"),
                             "percentil": c.get("pct"), "recent_2a": c.get("recent", 0),
                             "doi": d} for d, c in top],
        })
    rows.sort(key=lambda r: -r["citacoes_total"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    payload = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fonte": "OpenAlex (api.openalex.org), citações casadas por DOI do Lattes",
        "resumo": {
            "n_docentes": len(rows),
            "com_doi": sum(1 for r in rows if r["artigos_com_doi"]),
            "dois_unicos": len(all_dois),
            "dois_encontrados": len(cit_map),
            "citacoes_totais": sum(r["citacoes_total"] for r in rows),
        },
        "docentes": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written: {out}")

    # um JSON por docente
    per_dir = out.parent / "openalex"
    per_dir.mkdir(parents=True, exist_ok=True)
    for r in rows:
        slug = re.sub(r"[^a-z0-9]+", "-",
                      r["nome"].lower().encode("ascii", "ignore").decode()).strip("-")
        fp = per_dir / f"{r['lattes_id']}_{slug}.json"
        fp.write_text(json.dumps(
            {"gerado_em": payload["gerado_em"], "fonte": payload["fonte"], **r},
            ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written: {len(rows)} arquivos por docente em {per_dir}/")
    print("Top 8 por citações (OpenAlex):")
    for r in rows[:8]:
        print(f"  {r['rank']:>2} {r['nome'][:34]:<34} cit={r['citacoes_total']:<5} h={r['h_index']:<3} "
              f"g={r['g_index']:<3} m={r['m_index']:<5} i10={r['i10']:<3} "
              f"cit/art={r['citacoes_por_artigo']:<5} fr={r['citacoes_fracionadas']:<6} "
              f"({r['encontrados_openalex']}/{r['artigos_com_doi']} DOIs)")


if __name__ == "__main__":
    main()
