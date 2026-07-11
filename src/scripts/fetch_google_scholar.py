"""
Coleta métricas do Google Scholar para os docentes do IFES Campus Serra.

Para cada professor do roster, busca o perfil no Google Scholar e extrai:
  - h-index, i10-index, total de citações (e janela de 5 anos)
  - artigos mais citados (título, ano, veículo, nº de citações)

IMPORTANTE — limitações do Google Scholar:
  * NÃO há API oficial. Este script usa a lib `scholarly`, que faz scraping.
  * O Scholar bloqueia agressivamente (CAPTCHA / 429 / ban de IP). Para 90+
    nomes em sequência o bloqueio é quase certo sem proxy. Use --sleep alto e,
    se preciso, um ProxyGenerator (Tor/free proxies) — ver --use-proxy.
  * Nem todo docente tem perfil no Scholar; e nomes comuns geram ambiguidade.
    O script só aceita um perfil se a afiliação casar com IFES/Espírito Santo
    (a menos que --no-affiliation-check).
  * Salva incrementalmente e é resumível: reexecutar pula quem já foi coletado.

Instalação:
  pip install scholarly

Uso:
  python -m src.scripts.fetch_google_scholar                 # todos do roster
  python -m src.scripts.fetch_google_scholar --limit 5       # teste com 5
  python -m src.scripts.fetch_google_scholar --sleep 8 --use-proxy
  python -m src.scripts.fetch_google_scholar --names "Karin Satie Komati"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "data" / "exports" / "docentes"
DEFAULT_OUT = OUT_DIR / "google_scholar.json"

# Afiliação esperada (para desambiguar nomes comuns).
AFFIL_HINTS = ("ifes", "instituto federal", "espirito santo", "espírito santo")
DEFAULT_QUERY_SUFFIX = "Instituto Federal Espírito Santo"
TOP_ARTICLES = 10


def _roster_names() -> list[str]:
    """Nomes dos docentes — reaproveita o roster do executivo de docentes."""
    try:
        from src.scripts.generate_docentes_executive import ROSTER_IDS, ROSTER_SUSPECT

        return list(ROSTER_IDS.keys()) + list(ROSTER_SUSPECT.keys())
    except Exception:
        return []


def _norm(s: str) -> str:
    return (
        unicodedata.normalize("NFKD", s or "")
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )


def _affiliation_ok(affiliation: str) -> bool:
    a = _norm(affiliation)
    return any(h in a for h in AFFIL_HINTS)


def _load_existing(out_path: Path) -> dict:
    if out_path.exists():
        try:
            data = json.loads(out_path.read_text())
            return {r["nome"]: r for r in data.get("docentes", [])}
        except Exception:
            return {}
    return {}


def _save(out_path: Path, results: dict, generated_at: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fonte": "Google Scholar (via scholarly)",
        "gerado_em": generated_at,
        "total": len(results),
        "com_perfil": sum(1 for r in results.values() if r.get("encontrado")),
        "docentes": sorted(
            results.values(),
            key=lambda r: -(r.get("h_index") or 0),
        ),
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fetch_one(scholarly, name: str, query_suffix: str, check_affiliation: bool) -> dict:
    """Busca um docente no Scholar e extrai métricas. Nunca levanta exceção."""
    rec: dict = {"nome": name, "encontrado": False, "erro": None}
    try:
        query = f"{name} {query_suffix}".strip()
        author = next(scholarly.search_author(query), None)

        # fallback: busca só pelo nome se a query com afiliação não achou
        if author is None:
            author = next(scholarly.search_author(name), None)
        if author is None:
            rec["erro"] = "perfil não encontrado"
            return rec

        affiliation = author.get("affiliation", "") or ""
        if check_affiliation and not _affiliation_ok(affiliation):
            rec["erro"] = f"afiliação não confere: {affiliation!r}"
            rec["afiliacao_encontrada"] = affiliation
            return rec

        full = scholarly.fill(
            author, sections=["basics", "indices", "counts", "publications"]
        )

        pubs = full.get("publications", []) or []

        def _cit(p):
            return p.get("num_citations", 0) or 0

        top = sorted(pubs, key=_cit, reverse=True)[:TOP_ARTICLES]
        top_articles = []
        for p in top:
            bib = p.get("bib", {}) or {}
            top_articles.append(
                {
                    "titulo": bib.get("title", ""),
                    "ano": bib.get("pub_year", ""),
                    "veiculo": bib.get("venue", "") or bib.get("citation", ""),
                    "citacoes": _cit(p),
                }
            )

        rec.update(
            {
                "encontrado": True,
                "scholar_id": full.get("scholar_id", ""),
                "nome_scholar": full.get("name", ""),
                "afiliacao": affiliation,
                "areas": full.get("interests", []),
                "h_index": full.get("hindex"),
                "h_index_5y": full.get("hindex5y"),
                "i10_index": full.get("i10index"),
                "i10_index_5y": full.get("i10index5y"),
                "citacoes_total": full.get("citedby"),
                "citacoes_5y": full.get("citedby5y"),
                "n_publicacoes": len(pubs),
                "url": f"https://scholar.google.com/citations?user={full.get('scholar_id','')}",
                "artigos_mais_citados": top_articles,
            }
        )
    except StopIteration:
        rec["erro"] = "perfil não encontrado"
    except Exception as exc:  # bloqueio, parsing, rede
        rec["erro"] = f"{type(exc).__name__}: {exc}"
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Coleta métricas do Google Scholar dos docentes."
    )
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--limit", type=int, default=0, help="limita nº de docentes (0 = todos)"
    )
    ap.add_argument("--sleep", type=float, default=6.0, help="pausa entre buscas (s)")
    ap.add_argument("--names", nargs="*", help="processa apenas estes nomes")
    ap.add_argument(
        "--query-suffix",
        default=DEFAULT_QUERY_SUFFIX,
        help="sufixo de afiliação adicionado à busca",
    )
    ap.add_argument(
        "--no-affiliation-check",
        action="store_true",
        help="aceita o 1º perfil mesmo sem casar afiliação (arriscado)",
    )
    ap.add_argument(
        "--use-proxy",
        action="store_true",
        help="usa ProxyGenerator (free proxies) para reduzir bloqueio",
    )
    ap.add_argument(
        "--no-resume",
        action="store_true",
        help="ignora resultados já salvos e refaz tudo",
    )
    args = ap.parse_args()

    try:
        from scholarly import ProxyGenerator, scholarly
    except ImportError:
        print(
            "ERRO: lib 'scholarly' não instalada. Rode: pip install scholarly",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.use_proxy:
        print("Configurando proxy (free proxies)... pode demorar.")
        pg = ProxyGenerator()
        if pg.FreeProxies():
            scholarly.use_proxy(pg)
            print("Proxy ativo.")
        else:
            print("AVISO: não consegui configurar proxy; seguindo sem.")

    names = args.names or _roster_names()
    if not names:
        print("ERRO: roster vazio (não consegui importar ROSTER_IDS).", file=sys.stderr)
        sys.exit(1)
    if args.limit:
        names = names[: args.limit]

    out_path = Path(args.out)
    results = {} if args.no_resume else _load_existing(out_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    pend = [n for n in names if n not in results or results[n].get("erro")]
    print(
        f"Docentes: {len(names)} · já coletados: {len(names) - len(pend)} · "
        f"a processar: {len(pend)} · sleep={args.sleep}s"
    )

    for i, name in enumerate(pend, 1):
        print(f"[{i}/{len(pend)}] {name} ... ", end="", flush=True)
        rec = fetch_one(
            scholarly,
            name,
            args.query_suffix,
            check_affiliation=not args.no_affiliation_check,
        )
        results[name] = rec
        if rec["encontrado"]:
            print(
                f"h={rec.get('h_index')} cit={rec.get('citacoes_total')} "
                f"({len(rec.get('artigos_mais_citados', []))} artigos top)"
            )
        else:
            print(f"— {rec.get('erro')}")
        _save(out_path, results, now)  # salva incremental
        if i < len(pend):
            time.sleep(args.sleep)

    found = sum(1 for r in results.values() if r.get("encontrado"))
    print(f"\nConcluído. {found}/{len(results)} com perfil. Saída: {out_path}")


if __name__ == "__main__":
    main()
