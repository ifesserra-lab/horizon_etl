"""
Ranking de docentes por impacto de publicação — IFES Campus Serra.

Pontua cada docente pelo estrato Qualis (CAPES, melhor estrato entre áreas) dos
periódicos onde publicou, casado por ISSN, e mostra a grande área de atuação.
Também reporta o quartil SJR e o volume em congressos como contexto.

Nota: o Qualis classifica PERIÓDICOS por ISSN. Congressos NÃO têm Qualis oficial
(CAPES descontinuou o Qualis Eventos em 2019) — entram como volume, sem peso.

Uso:
  python -m src.scripts.rank_docentes_impact
  python -m src.scripts.rank_docentes_impact --top 10 --by-area
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from src.scripts.analyze_venues import (
    LATTES_DIR,
    REF_DIR,
    load_qualis,
    load_scimago,
    norm_issn,
)
from src.scripts.generate_docentes_executive import ROSTER_IDS

OUT = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "exports"
    / "docentes"
    / "ranking_impacto.json"
)

# Peso por estrato Qualis (A1 = topo).
QUALIS_WEIGHT = {
    "A1": 100,
    "A2": 85,
    "A3": 70,
    "A4": 55,
    "B1": 40,
    "B2": 30,
    "B3": 20,
    "B4": 10,
    "B5": 5,
    "C": 3,
}
A_STRATA = {"A1", "A2", "A3", "A4"}


def _area(cv: dict) -> str:
    c = Counter()
    for a in cv.get("areas_de_atuacao") or []:
        ga = (a.get("grande_area") or a.get("area") or "").strip()
        if ga:
            c[ga] += 1
    return c.most_common(1)[0][0] if c else "—"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument(
        "--by-area", action="store_true", help="também mostra o top 1 por área"
    )
    ap.add_argument("--qualis", default=str(REF_DIR / "qualis.csv"))
    args = ap.parse_args()

    qualis = load_qualis(Path(args.qualis))
    scimago = load_scimago()
    print(f"Qualis={len(qualis)} ISSNs · SJR={len(scimago)} ISSNs")

    by_id = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f

    rows = []
    for nome, lid in ROSTER_IDS.items():
        f = by_id.get(lid)
        if not f:
            continue
        cv = json.loads(Path(f).read_text())
        pb = cv.get("producao_bibliografica", {}) or {}
        arts = pb.get("artigos_periodicos", []) or []
        congs = pb.get("trabalhos_completos_congressos", []) or []

        strata = Counter()
        q1q2 = 0
        score = 0
        n_qualis = 0
        for a in arts:
            issn = norm_issn(a.get("issn", ""))
            est = qualis.get(issn)
            if est:
                strata[est] += 1
                score += QUALIS_WEIGHT.get(est, 0)
                n_qualis += 1
            quart = scimago.get(issn, {}).get("quartil", "")
            if quart in ("Q1", "Q2"):
                q1q2 += 1

        n_a = sum(strata[s] for s in A_STRATA)
        rows.append(
            {
                "nome": nome,
                "area": _area(cv),
                "score_qualis": score,
                "artigos": len(arts),
                "artigos_qualis": n_qualis,
                "estrato_A": n_a,
                "A1": strata["A1"],
                "A2": strata["A2"],
                "A3": strata["A3"],
                "A4": strata["A4"],
                "B": sum(strata[s] for s in ("B1", "B2", "B3", "B4", "B5")),
                "C": strata["C"],
                "sjr_q1q2": q1q2,
                "congressos": len(congs),
                "pct_A": round(n_a / len(arts) * 100) if arts else 0,
            }
        )

    rows.sort(key=lambda r: (-r["score_qualis"], -r["estrato_A"], -r["artigos"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "metodo": "score = soma dos pesos Qualis (A1=100..C=3) dos artigos em periódicos, "
                "melhor estrato entre áreas; congressos sem Qualis (contexto).",
                "ranking": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    top = rows[: args.top]
    print(f"\nTOP {args.top} — impacto por Qualis (periódicos):")
    print(
        f"  {'#':>2} {'score':>5} {'A1-A4':>5} {'art':>4} {'Q1Q2':>4}  {'docente':<34} {'área'}"
    )
    for r in top:
        det = f"A1:{r['A1']} A2:{r['A2']} A3:{r['A3']} A4:{r['A4']}"
        print(
            f"  {r['rank']:>2} {r['score_qualis']:>5} {r['estrato_A']:>5} {r['artigos']:>4} "
            f"{r['sjr_q1q2']:>4}  {r['nome'][:34]:<34} {r['area'][:24]}  [{det}]"
        )

    if args.by_area:
        print("\nTop 1 por grande área:")
        best = {}
        for r in rows:
            if r["area"] not in best:
                best[r["area"]] = r
        for area, r in sorted(best.items(), key=lambda x: -x[1]["score_qualis"]):
            print(
                f"  {area[:34]:<34} {r['nome'][:30]:<30} score={r['score_qualis']} A={r['estrato_A']}"
            )


if __name__ == "__main__":
    main()
