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
               + "cited_by_percentile_year,counts_by_year&filter=" + quote(flt, safe="|:/."))
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
                recent = sum(c.get("cited_by_count", 0) for c in (w.get("counts_by_year") or [])
                             if c.get("year", 0) >= 2024)
                out[wdoi] = {"cit": w.get("cited_by_count", 0),
                             "title": w.get("title", ""),
                             "year": w.get("publication_year"),
                             "fwci": w.get("fwci"),
                             "pct": pct, "recent": recent}
        print(f"  lote {i//BATCH+1}/{(len(uniq)+BATCH-1)//BATCH}: {len(chunk)} DOIs → {len(data.get('results',[]))} achados")
        time.sleep(sleep)
    return out


def h_index(cits: list[int]) -> int:
    h = 0
    for i, c in enumerate(sorted(cits, reverse=True), 1):
        if c >= i:
            h = i
        else:
            break
    return h


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
        rows.append({
            "nome": nome, "lattes_id": lid,
            "artigos_com_doi": len(set(dois)),
            "encontrados_openalex": len(found),
            "citacoes_total": total,
            "h_index": h_index(cits),
            "i10": sum(1 for c in cits if c >= 10),
            "mais_citado": max(cits) if cits else 0,
            "fwci_medio": fwci_mean,
            "fwci_mediana": fwci_med,
            "fwci_antigo": fwci_antigo, "fwci_recente": fwci_recente, "fwci_delta": fwci_delta,
            "artigos_top10pct": top10,
            "artigos_top1pct": top1,
            "citacoes_recentes_2a": recent_cit,
            "momentum_pct": round(recent_cit / total * 100) if total else 0,
            "top_artigos": [{"titulo": (c["title"] or "")[:90], "ano": c["year"],
                             "citacoes": c["cit"], "fwci": c.get("fwci"),
                             "percentil": c.get("pct"), "doi": d} for d, c in top],
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
              f"i10={r['i10']:<3} ({r['encontrados_openalex']}/{r['artigos_com_doi']} DOIs)")


if __name__ == "__main__":
    main()
