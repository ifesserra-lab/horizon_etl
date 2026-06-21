"""
Análise de veículos de publicação dos docentes do IFES Campus Serra.

A partir dos currículos Lattes (data/lattes_json), inventaria as REVISTAS
(artigos em periódicos) e os CONGRESSOS onde os docentes publicaram e cruza
cada revista com duas métricas de impacto:

  * SJR — SCImago Journal Rank (métrica internacional): quartil Q1–Q4,
    índice SJR e H-index do periódico. Casado por ISSN.
  * Qualis CAPES/CNPq: estrato (A1–A4, B1–B4, C). Casado por ISSN, a partir
    de uma tabela de referência local (CAPES não tem API pública estável).

Fontes de referência (opcionais, casadas por ISSN):
  - SCImago: baixa de https://www.scimagojr.com/journalrank.php?out=xls
    (cacheado em data/reference/scimago.csv). Use --download-scimago.
  - Qualis: forneça um CSV em data/reference/qualis.csv com colunas
    contendo ISSN e o estrato (ex.: "ISSN","Estrato"). Use --qualis <arquivo>.

Sem as referências, o script ainda entrega o inventário de veículos (contagens,
ISSN, anos, autores) — só não classifica impacto.

Uso:
  python -m src.scripts.analyze_venues --download-scimago
  python -m src.scripts.analyze_venues --qualis data/reference/qualis.csv
  python -m src.scripts.analyze_venues --top 30
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[2]
LATTES_DIR = BASE / "data" / "lattes_json"
REF_DIR = BASE / "data" / "reference"
OUT_DIR = BASE / "data" / "exports" / "docentes"
DEFAULT_OUT = OUT_DIR / "venues_analysis.json"
SCIMAGO_CSV = REF_DIR / "scimago.csv"
SCIMAGO_URL = "https://www.scimagojr.com/journalrank.php?out=xls"
QUALIS_CONF_FILE = REF_DIR / "qualis_conferencias.json"  # Qualis Eventos CC (UFMT, 2016)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def norm_issn(s: str) -> str:
    """Normaliza ISSN para 8 caracteres alfanuméricos (sem hífen, maiúsculo)."""
    if not s:
        return ""
    s = re.sub(r"[^0-9xX]", "", s).upper()
    return s if len(s) == 8 else ""


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def normalize_conf(name: str) -> str:
    """Normaliza nome de congresso removendo ano e número de edição.

    Funde edições do mesmo evento. Ex.:
      '2023 15th IEEE International Conference on Industry Applications' e
      '2025 16th IEEE ... Industry Applications'  ->  'IEEE ... Industry Applications'
      'XLIV Congresso Brasileiro de Educação em Engenharia' -> 'Congresso ...'
      'II Seminário de Pesquisa em Administração'           -> 'Seminário ...'
    """
    s = (name or "").strip()
    # ordinais em inglês: 15th, 1st, 2nd, 3rd (com possível ano antes)
    s = re.sub(r"\b\d{1,3}(st|nd|rd|th)\b", " ", s, flags=re.I)
    # ordinais em português: 15ª, 44º, 1o, 2a
    s = re.sub(r"\b\d{1,3}\s*[ºªoa°]\b", " ", s)
    # anos isolados (19xx/20xx) em qualquer posição
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)
    # numeral romano de edição no INÍCIO (ex.: 'XLIV ', 'VI ') seguido de palavra
    s = re.sub(r"^\s*[IVXLCDM]{1,7}\b\.?\s+(?=[A-Za-zÀ-ÿ])", " ", s)
    # 'ed.'/'edição' residual
    s = re.sub(r"\b(edi[çc][aã]o|ed\.)\b", " ", s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,.;:-–—()")
    return s


def conf_key(clean: str) -> str:
    """Chave de agrupamento de congressos: ascii minúsculo, só alfanumérico.

    Ignora o conteúdo entre parênteses (acrônimo) p/ não fragmentar o mesmo
    evento — ex.: "Congresso Brasileiro de Automática" e "… (CBA)" agrupam juntos.
    """
    s = re.sub(r"\([^)]*\)?", " ", clean or "")  # parêntese pode estar sem fechar
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


# Peso por estrato Qualis (A1 = topo) — usado no ranking de docentes por impacto.
QUALIS_WEIGHT = {
    "A1": 100, "A2": 85, "A3": 70, "A4": 55,
    "B1": 40, "B2": 30, "B3": 20, "B4": 10, "B5": 5, "C": 3,
}
_A_STRATA = ("A1", "A2", "A3", "A4")

# Mapeia áreas do SCImago (Scopus) -> grande área CNPq, p/ inferir a grande área
# de docentes que não a declararam no Lattes (substring, minúsculo).
_SCIMAGO_TO_GRANDE = [
    ("engineering", "Engenharias"), ("energy", "Engenharias"),
    ("materials", "Engenharias"), ("aerospace", "Engenharias"),
    ("computer", "Ciências Exatas e da Terra"), ("mathemat", "Ciências Exatas e da Terra"),
    ("physic", "Ciências Exatas e da Terra"), ("chemistr", "Ciências Exatas e da Terra"),
    ("statist", "Ciências Exatas e da Terra"),
    ("medicine", "Ciências da Saúde"), ("health", "Ciências da Saúde"),
    ("nursing", "Ciências da Saúde"), ("pharma", "Ciências da Saúde"),
    ("biochem", "Ciências Biológicas"), ("immunolog", "Ciências Biológicas"),
    ("neuroscience", "Ciências Biológicas"), ("agar", "Ciências Agrárias"),
    ("agricultur", "Ciências Agrárias"), ("veterinar", "Ciências Agrárias"),
    ("business", "Ciências Sociais Aplicadas"), ("management", "Ciências Sociais Aplicadas"),
    ("econom", "Ciências Sociais Aplicadas"), ("account", "Ciências Sociais Aplicadas"),
    ("decision", "Ciências Sociais Aplicadas"), ("social", "Ciências Sociais Aplicadas"),
    ("arts", "Ciências Humanas"), ("humanities", "Ciências Humanas"),
    ("psycholog", "Ciências Humanas"),
]


def _grande_from_scimago_area(area_text: str) -> str | None:
    a = (area_text or "").lower()
    for kw, grande in _SCIMAGO_TO_GRANDE:
        if kw in a:
            return grande
    return None


def _docente_area(cv: dict, field: str = "grande_area") -> str:
    """Área predominante do docente. field: 'grande_area' ou 'area' (sub-área)."""
    c = Counter()
    for a in cv.get("areas_de_atuacao") or []:
        v = (a.get(field) or "").strip()
        if v:
            c[v] += 1
    return c.most_common(1)[0][0] if c else "—"


def rank_docentes(roster: dict[str, str], qualis: dict, scimago: dict,
                  conf_acro: dict | None = None, conf_name: dict | None = None) -> list[dict]:
    """Pontua cada docente pelo Qualis dos periódicos (e, se houver, congressos CC)."""
    conf_acro = conf_acro or {}
    conf_name = conf_name or {}
    by_id = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f

    # mapa sub-área (campo 'area') -> grande área, a partir de quem declara ambos.
    # Usado p/ inferir a grande área de docentes que não a declararam no Lattes.
    sub2grande: dict[str, Counter] = defaultdict(Counter)
    for lid in roster.values():
        f = by_id.get(lid)
        if not f:
            continue
        for a in (json.loads(Path(f).read_text()).get("areas_de_atuacao") or []):
            ga = (a.get("grande_area") or "").strip()
            ar = (a.get("area") or "").strip()
            if ga and ar:
                sub2grande[ar][ga] += 1

    rows = []
    for nome, lid in roster.items():
        f = by_id.get(lid)
        if not f:
            continue
        cv = json.loads(Path(f).read_text())
        pb = cv.get("producao_bibliografica", {}) or {}
        arts = pb.get("artigos_periodicos", []) or []
        strata = Counter()
        score = q1q2 = 0
        sci_grande = Counter()  # grande área inferida dos periódicos (Scimago)
        for a in arts:
            issn = norm_issn(a.get("issn", ""))
            est = qualis.get(issn)
            if est:
                strata[est] += 1
                score += QUALIS_WEIGHT.get(est, 0)
            sm = scimago.get(issn, {})
            if sm.get("quartil", "") in ("Q1", "Q2"):
                q1q2 += 1
            g = _grande_from_scimago_area(sm.get("area", ""))
            if g:
                sci_grande[g] += 1
        # congressos: Qualis CC
        congs = pb.get("trabalhos_completos_congressos", []) or []
        conf_strata = Counter()
        score_conf = 0
        for c in congs:
            cl = normalize_conf(c.get("evento") or "")
            est = match_conf_qualis(cl, conf_acro, conf_name) if cl else None
            if est:
                conf_strata[est] += 1
                score_conf += QUALIS_WEIGHT.get(est, 0)
        conf_a = sum(conf_strata[s] for s in _A_STRATA)
        conf_q = sum(conf_strata.values())

        n_a = sum(strata[s] for s in _A_STRATA)
        n_q = sum(strata.values())  # artigos com Qualis
        subarea = _docente_area(cv, "area")
        grande = _docente_area(cv)
        if grande == "—" and subarea != "—" and sub2grande.get(subarea):
            grande = sub2grande[subarea].most_common(1)[0][0]  # inferida da sub-área
        if grande == "—" and sci_grande:
            grande = sci_grande.most_common(1)[0][0]  # inferida dos periódicos (Scimago)
        rows.append({
            "nome": nome, "area": grande,
            "subarea": subarea,
            "score": score, "estrato_A": n_a, "artigos": len(arts),
            "artigos_qualis": n_q,
            "qualidade": round(score / n_q, 1) if n_q else 0.0,
            "pct_A": round(n_a / n_q * 100) if n_q else 0,
            "A1": strata["A1"], "A2": strata["A2"], "A3": strata["A3"], "A4": strata["A4"],
            "sjr_q1q2": q1q2,
            "congressos": len(congs),
            "score_conf": score_conf, "conf_qualis": conf_q, "conf_A": conf_a,
            "score_total": score + score_conf,
        })
    rows.sort(key=lambda r: (-r["score"], -r["estrato_A"], -r["artigos"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def ascension(roster: dict[str, str], qualis: dict,
              early=(2016, 2020), recent=(2021, 2025), min_each=2) -> list[dict]:
    """Heurística de ascensão: variação da qualidade média (peso Qualis) dos
    artigos entre a janela antiga e a recente do último decênio.

    delta > 0 = pesquisador publicando em estratos mais altos com o tempo.
    Considera só quem tem >= min_each artigos com Qualis em CADA janela.
    """
    by_id = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f

    out = []
    for nome, lid in roster.items():
        f = by_id.get(lid)
        if not f:
            continue
        cv = json.loads(Path(f).read_text())
        old_w, new_w = [], []
        for a in (cv.get("producao_bibliografica", {}) or {}).get("artigos_periodicos", []) or []:
            est = qualis.get(norm_issn(a.get("issn", "")))
            if not est:
                continue
            try:
                ano = int(a.get("ano") or 0)
            except (ValueError, TypeError):
                continue
            w = QUALIS_WEIGHT.get(est, 0)
            if early[0] <= ano <= early[1]:
                old_w.append(w)
            elif recent[0] <= ano <= recent[1]:
                new_w.append(w)
        if len(old_w) < min_each or len(new_w) < min_each:
            continue
        ma = sum(old_w) / len(old_w)
        mr = sum(new_w) / len(new_w)
        out.append({
            "nome": nome,
            "media_antiga": round(ma, 1), "media_recente": round(mr, 1),
            "delta": round(mr - ma, 1),
            "n_antigo": len(old_w), "n_recente": len(new_w),
            "subarea": _docente_area(cv, "area"),
        })
    out.sort(key=lambda x: -x["delta"])
    return out


def _roster() -> dict[str, str]:
    from src.scripts.generate_docentes_executive import ROSTER_IDS
    return ROSTER_IDS


# ---------------------------------------------------------------------------
# Referências de impacto
# ---------------------------------------------------------------------------

def download_scimago() -> bool:
    REF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Baixando SCImago de {SCIMAGO_URL} ...")
    try:
        req = Request(SCIMAGO_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=120) as r:
            data = r.read()
        SCIMAGO_CSV.write_bytes(data)
        print(f"  salvo em {SCIMAGO_CSV} ({len(data)//1024} KB)")
        return True
    except Exception as exc:
        print(f"  FALHOU: {exc}", file=sys.stderr)
        return False


def load_scimago() -> dict[str, dict]:
    """ISSN -> {sjr, quartil, h_index, titulo, area}. Vazio se ausente."""
    if not SCIMAGO_CSV.exists():
        return {}
    out: dict[str, dict] = {}
    raw = SCIMAGO_CSV.read_text(encoding="utf-8", errors="ignore")
    reader = csv.DictReader(raw.splitlines(), delimiter=";")
    for row in reader:
        rec = {
            "titulo": (row.get("Title") or "").strip(),
            "sjr": (row.get("SJR") or "").replace(",", ".").strip(),
            "quartil": (row.get("SJR Best Quartile") or "").strip(),
            "h_index": (row.get("H index") or "").strip(),
            "area": (row.get("Categories") or row.get("Areas") or "").strip(),
        }
        for issn in re.split(r"[,\s]+", row.get("Issn", "") or ""):
            k = norm_issn(issn)
            if k:
                out[k] = rec
    return out


def load_qualis(path: Path | None) -> dict[str, str]:
    """ISSN -> estrato Qualis. CSV com colunas contendo ISSN e estrato."""
    if not path or not Path(path).exists():
        return {}
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    delim = ";" if raw.count(";") > raw.count(",") else ","
    reader = csv.DictReader(raw.splitlines(), delimiter=delim)
    issn_col = estr_col = None
    for c in (reader.fieldnames or []):
        cl = norm_name(c)
        if issn_col is None and "issn" in cl:
            issn_col = c
        if estr_col is None and ("estrato" in cl or "qualis" in cl or "classific" in cl):
            estr_col = c
    if not issn_col or not estr_col:
        print(f"  AVISO: não achei colunas ISSN/estrato no Qualis ({reader.fieldnames})",
              file=sys.stderr)
        return {}
    # Melhor estrato entre áreas: se o mesmo ISSN tiver vários estratos,
    # mantém o melhor (A1 é o topo).
    rank = {e: i for i, e in enumerate(
        ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "B5", "C"])}
    out: dict[str, str] = {}
    for row in reader:
        k = norm_issn(row.get(issn_col, ""))
        e = (row.get(estr_col) or "").strip().upper()
        if not k or e not in rank:
            continue
        if k not in out or rank[e] < rank[out[k]]:
            out[k] = e
    return out


def _ckey(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def load_qualis_conf(path: Path = QUALIS_CONF_FILE) -> tuple[dict, dict]:
    """Qualis de conferências CC. Retorna (acronimo->estrato, nome_norm->estrato)."""
    if not Path(path).exists():
        return {}, {}
    data = json.loads(Path(path).read_text()).get("data", [])
    acro, name = {}, {}
    for row in data:
        if len(row) < 3:
            continue
        ac, full, est = row[0].strip(), row[1].strip(), row[2].strip().upper()
        if ac:
            acro[ac.upper()] = est
        nm = re.sub(r"^\s*" + re.escape(ac) + r"\s*[-:]\s*", "", full)
        k = _ckey(nm)
        if len(k) > 6:
            name[k] = est
    return acro, name


# Siglas de organizações/editoras (não são acrônimos de evento) — evitam falso match.
_CONF_ACRO_STOP = {"IEEE", "ACM", "IFIP", "IADIS", "IARIA", "SPIE", "SBC", "IET", "AAAI"}
_CONF_FUZZY_MIN = 0.90  # similaridade mínima p/ casar por nome (determinístico)


def match_conf_qualis(evento_clean: str, acro: dict, name: dict) -> str | None:
    """Casa um congresso (nome normalizado) ao Qualis CC.

    Ordem (mais confiável → menos): acrônimo entre parênteses; nome exato;
    melhor match fuzzy de nome (≥ limiar, determinístico); acrônimo isolado
    (≥3 letras, fora da stoplist de organizações).
    """
    if not acro and not name:
        return None
    # 1) acrônimo entre parênteses — sinal explícito do autor
    for cand in re.findall(r"\(([A-Za-z][A-Za-z0-9\-]{1,})\)", evento_clean):
        cu = cand.upper()
        if cu in acro and cu not in _CONF_ACRO_STOP:
            return acro[cu]
    # 2) nome exato (sem o que está entre parênteses)
    k = _ckey(re.sub(r"\([^)]*\)", "", evento_clean))
    if not k:
        return None
    if k in name:
        return name[k]
    # 3) melhor match fuzzy de nome (determinístico: maior ratio acima do limiar)
    best_est, best_r = None, 0.0
    for nmk, est in name.items():
        if abs(len(nmk) - len(k)) > 12:
            continue
        r = SequenceMatcher(None, k, nmk).ratio()
        if r > best_r:
            best_r, best_est = r, est
    if best_r >= _CONF_FUZZY_MIN:
        return best_est
    # 4) acrônimo isolado (≥3 letras), fora da stoplist
    for cand in re.findall(r"\b([A-Z]{3,6})\b", evento_clean):
        if cand not in _CONF_ACRO_STOP and cand in acro:
            return acro[cand]
    return None


# ---------------------------------------------------------------------------
# Extração dos veículos a partir do Lattes
# ---------------------------------------------------------------------------

def collect_venues(roster: dict[str, str]) -> tuple[dict, dict]:
    by_id = {}
    for f in glob.glob(str(LATTES_DIR / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f

    journals: dict[str, dict] = {}   # chave = issn normalizado (fallback nome)
    confs: dict[str, dict] = {}      # chave = nome normalizado do evento

    for nome, lid in roster.items():
        f = by_id.get(lid)
        if not f:
            continue
        d = json.loads(Path(f).read_text())
        pb = d.get("producao_bibliografica", {}) or {}

        for a in pb.get("artigos_periodicos", []) or []:
            issn = norm_issn(a.get("issn", ""))
            rev = (a.get("revista") or "").strip()
            key = issn or ("name:" + norm_name(rev))
            if not rev and not issn:
                continue
            j = journals.setdefault(key, {
                "revista": rev, "issn": a.get("issn", "").strip(),
                "issn_norm": issn, "n": 0, "docentes": set(), "anos": [],
                "_works": set(),
            })
            # dedup co-autoria: mesma obra (título) no mesmo veículo conta 1 vez,
            # mas todos os docentes coautores são creditados em "docentes".
            wk = norm_name(a.get("titulo", ""))
            if wk and wk in j["_works"]:
                j["docentes"].add(nome)
            else:
                if wk:
                    j["_works"].add(wk)
                j["n"] += 1
                j["docentes"].add(nome)
                if a.get("ano"):
                    j["anos"].append(a["ano"])
            if not j["revista"] and rev:
                j["revista"] = rev

        for c in pb.get("trabalhos_completos_congressos", []) or []:
            ev = (c.get("evento") or "").strip()
            if not ev:
                continue
            clean = normalize_conf(ev) or ev
            key = conf_key(clean) or norm_name(ev)
            e = confs.setdefault(key, {"evento": clean, "n": 0, "docentes": set(),
                                       "anos": [], "_names": Counter(), "_works": set()})
            wk = norm_name(c.get("titulo", ""))
            if wk and wk in e["_works"]:
                e["docentes"].add(nome)
            else:
                if wk:
                    e["_works"].add(wk)
                e["n"] += 1
                e["docentes"].add(nome)
                e["_names"][clean] += 1
                if c.get("ano"):
                    e["anos"].append(c["ano"])

    # nome de exibição = variante normalizada mais frequente (desempate: mais curta)
    for e in confs.values():
        e["evento"] = max(e["_names"].items(), key=lambda kv: (kv[1], -len(kv[0])))[0]
        del e["_names"], e["_works"]
    for j in journals.values():
        del j["_works"]

    return journals, confs


def enrich_and_summarize(journals: dict, confs: dict,
                         scimago: dict, qualis: dict, top: int,
                         conf_acro: dict | None = None,
                         conf_name: dict | None = None) -> dict:
    conf_acro = conf_acro or {}
    conf_name = conf_name or {}
    # enriquece revistas
    jrows = []
    q_dist = defaultdict(int)        # quartil SJR
    qualis_dist = defaultdict(int)   # estrato Qualis
    artigos_total = 0
    for j in journals.values():
        artigos_total += j["n"]
        sm = scimago.get(j["issn_norm"], {})
        quartil = sm.get("quartil", "") or "—"
        qcap = qualis.get(j["issn_norm"], "") or "—"
        q_dist[quartil if quartil != "" else "—"] += j["n"]
        qualis_dist[qcap if qcap != "" else "—"] += j["n"]
        jrows.append({
            "revista": j["revista"],
            "issn": j["issn"],
            "publicacoes": j["n"],
            "n_docentes": len(j["docentes"]),
            "ano_min": min(j["anos"]) if j["anos"] else None,
            "ano_max": max(j["anos"]) if j["anos"] else None,
            "sjr": sm.get("sjr", ""),
            "sjr_quartil": quartil,
            "sjr_h_index": sm.get("h_index", ""),
            "sjr_titulo": sm.get("titulo", ""),
            "qualis": qcap,
        })
    jrows.sort(key=lambda r: -r["publicacoes"])

    conf_dist = defaultdict(int)   # estrato Qualis CC por trabalho
    crows = []
    for c in confs.values():
        est = match_conf_qualis(c["evento"], conf_acro, conf_name) or "—"
        conf_dist[est] += c["n"]
        crows.append({
            "evento": c["evento"], "publicacoes": c["n"],
            "n_docentes": len(c["docentes"]),
            "ano_min": min(c["anos"]) if c["anos"] else None,
            "ano_max": max(c["anos"]) if c["anos"] else None,
            "qualis": est,
        })
    crows.sort(key=lambda r: -r["publicacoes"])
    congressos_total = sum(c["publicacoes"] for c in crows)

    matched_sjr = sum(1 for r in jrows if r["sjr_quartil"] not in ("—", ""))
    matched_qualis = sum(1 for r in jrows if r["qualis"] not in ("—", ""))
    conf_matched = sum(1 for r in crows if r["qualis"] not in ("—", ""))

    return {
        "resumo": {
            "n_revistas_distintas": len(jrows),
            "n_artigos": artigos_total,
            "n_congressos_distintos": len(crows),
            "n_trabalhos_congresso": congressos_total,
            "revistas_com_sjr": matched_sjr,
            "revistas_com_qualis": matched_qualis,
            "congressos_com_qualis": conf_matched,
        },
        "distribuicao_sjr_quartil": dict(sorted(q_dist.items())),
        "distribuicao_qualis": dict(sorted(qualis_dist.items())),
        "distribuicao_qualis_conf": dict(sorted(conf_dist.items())),
        "top_revistas": jrows[:top],
        "top_congressos": crows[:top],
        "revistas": jrows,
        "congressos": crows,
    }


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_Q_COLOR = {"Q1": "var(--brand)", "Q2": "var(--blue)", "Q3": "var(--amber)",
            "Q4": "var(--rose)", "—": "var(--line2)"}
_QUALIS_COLOR = {
    "A1": "var(--brand-d)", "A2": "var(--brand)", "A3": "#3f9d63", "A4": "#6bbf86",
    "B1": "var(--blue)", "B2": "#5b8fc0", "B3": "var(--amber)", "B4": "#c9a13b",
    "B5": "#d8b56b", "C": "var(--rose)", "—": "var(--line2)",
}


def _bars(dist: dict, order: list, colors: dict, total: int) -> str:
    mx = max(list(dist.values()) + [1])
    rows = ""
    for k in order:
        v = dist.get(k, 0)
        if not v:
            continue
        w = v / mx * 100
        pct = f"{v / total * 100:.0f}%" if total else ""
        rows += (
            f'<div class="brow"><span class="bl">{k}</span>'
            f'<div class="btrack"><div class="bfill" style="width:{max(w,1.5):.1f}%;'
            f'background:{colors.get(k,"var(--line2)")};"></div></div>'
            f'<span class="bv">{v} <span style="color:var(--muted);font-weight:500;">· {pct}</span></span></div>'
        )
    return rows


def render_html(payload: dict, qualis_applied: bool, ranking: list | None = None,
                asc: list | None = None) -> str:
    from src.scripts.generate_docentes_executive import CSS
    r = payload["resumo"]
    qdist = payload["distribuicao_sjr_quartil"]
    # normaliza chave '-' para '—'
    qd = defaultdict(int)
    for k, v in qdist.items():
        qd["—" if k in ("-", "") else k] += v
    tot_art = r["n_artigos"]
    ranked = sum(qd.get(x, 0) for x in ["Q1", "Q2", "Q3", "Q4"])
    pct_scopus = round(ranked / tot_art * 100) if tot_art else 0
    q1q2 = qd.get("Q1", 0) + qd.get("Q2", 0)

    kpis = f"""
    <section class="section"><div class="kpis">
      <div class="kpi"><div class="n">{r['n_revistas_distintas']}</div>
        <div class="u">revistas distintas</div><div class="s">{r['n_artigos']} artigos em periódicos</div></div>
      <div class="kpi"><div class="n">{pct_scopus}%</div>
        <div class="u">indexado no Scopus</div><div class="s">{ranked} de {tot_art} artigos com SJR</div></div>
      <div class="kpi"><div class="n">{qd.get('Q1',0)}</div>
        <div class="u">artigos em Q1</div><div class="s">topo mundial · {round(qd.get('Q1',0)/tot_art*100) if tot_art else 0}% do total</div></div>
      <div class="kpi"><div class="n">{r['n_congressos_distintos']}</div>
        <div class="u">congressos distintos</div><div class="s">{r['n_trabalhos_congresso']} trabalhos completos</div></div>
    </div></section>"""

    sjr_legend = ('<div class="legend">'
                  '<span><i style="background:var(--brand)"></i>Q1</span>'
                  '<span><i style="background:var(--blue)"></i>Q2</span>'
                  '<span><i style="background:var(--amber)"></i>Q3</span>'
                  '<span><i style="background:var(--rose)"></i>Q4</span>'
                  '<span><i style="background:var(--line2)"></i>sem SJR</span></div>')
    sec_sjr = f"""
    <section class="section">
      <div class="eyebrow">Impacto internacional</div>
      <h2>Qualidade dos periódicos — SCImago Journal Rank (SJR)</h2>
      <p class="desc">Distribuição dos {tot_art} artigos pelo quartil do periódico no SJR
      (métrica internacional derivada do Scopus). <b>{q1q2}</b> artigos ({round(q1q2/tot_art*100) if tot_art else 0}%)
      em Q1+Q2; {tot_art-ranked} em periódicos fora do Scopus (majoritariamente nacionais).</p>
      <div class="card"><div class="card-head"><h3>Artigos por quartil SJR</h3>{sjr_legend}</div>
        {_bars(qd, ['Q1','Q2','Q3','Q4','—'], _Q_COLOR, tot_art)}</div>
    </section>"""

    # tabela top revistas
    def _qbadge(q, palette):
        c = palette.get(q, "var(--line2)")
        txt = "#fff" if q not in ("—", "") else "var(--muted)"
        return (f'<span style="display:inline-block;min-width:30px;text-align:center;'
                f'padding:2px 8px;border-radius:6px;font-size:12px;font-weight:700;'
                f'background:{c};color:{txt};">{q or "—"}</span>')

    # ordena por quartil SJR (Q1 melhor) e, dentro do quartil, pelo índice SJR desc
    _qrank = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3, "—": 9, "": 9, "-": 9}

    def _jkey(j):
        try:
            sjr = float(j["sjr"]) if j.get("sjr") else -1.0
        except ValueError:
            sjr = -1.0
        return (_qrank.get(j.get("sjr_quartil", "—"), 9), -sjr)

    jr = sorted(payload["revistas"], key=_jkey)[:20]
    qcol_head = "<th>Qualis</th>" if qualis_applied else ""
    jrows = ""
    for j in jr:
        qcell = f"<td>{_qbadge(j.get('qualis','—'), _QUALIS_COLOR)}</td>" if qualis_applied else ""
        jrows += (
            f"<tr><td>{j['revista'][:54]}</td>"
            f"<td>{j['publicacoes']}</td>"
            f"<td>{_qbadge(j['sjr_quartil'], _Q_COLOR)}</td>"
            f"<td>{j['sjr'] or '—'}</td><td>{j['sjr_h_index'] or '—'}</td>"
            f"{qcell}</tr>"
        )
    sec_top = f"""
    <section class="section">
      <div class="eyebrow">Onde publicam</div>
      <h2>Principais revistas</h2>
      <p class="desc">Top 20 periódicos ordenados por quartil SJR e, dentro do quartil,
      pelo índice SJR (do maior impacto ao menor). Coluna "Artigos" = nº de artigos dos docentes.</p>
      <table><thead><tr><th>Revista</th><th>Artigos</th><th>SJR</th><th>Índice SJR</th><th>H</th>{qcol_head}</tr></thead>
      <tbody>{jrows}</tbody></table>
    </section>"""

    # Qualis section
    sec_qualis = ""
    if qualis_applied:
        qld = defaultdict(int)
        for k, v in payload["distribuicao_qualis"].items():
            qld["—" if k in ("-", "") else k] += v
        qmatched = r.get("revistas_com_qualis", 0)
        a_strata = sum(qld.get(x, 0) for x in ["A1", "A2", "A3", "A4"])
        ql_legend = ('<div class="legend">'
                     '<span><i style="background:var(--brand-d)"></i>A1–A4</span>'
                     '<span><i style="background:var(--blue)"></i>B1–B2</span>'
                     '<span><i style="background:var(--amber)"></i>B3–B5</span>'
                     '<span><i style="background:var(--rose)"></i>C</span>'
                     '<span><i style="background:var(--line2)"></i>sem Qualis</span></div>')
        sec_qualis = f"""
    <section class="section">
      <div class="eyebrow">Classificação nacional</div>
      <h2>Qualis CAPES/CNPq (2017–2020, melhor estrato)</h2>
      <p class="desc">Estrato Qualis dos {tot_art} artigos — melhor classificação do periódico
      entre todas as áreas de avaliação. <b>{a_strata}</b> artigos em estratos A (A1–A4);
      {qmatched} das {r['n_revistas_distintas']} revistas têm Qualis.</p>
      <div class="card"><div class="card-head"><h3>Artigos por estrato Qualis</h3>{ql_legend}</div>
        {_bars(qld, ['A1','A2','A3','A4','B1','B2','B3','B4','B5','C','—'], _QUALIS_COLOR, tot_art)}</div>
    </section>"""

    # ranking de docentes por impacto (Qualis)
    sec_rank = ""
    if ranking:
        rk = ""
        for rr in ranking[:10]:
            det = (f'<span style="color:var(--muted);font-size:12px;">'
                   f'A1:{rr["A1"]} A2:{rr["A2"]} A3:{rr["A3"]} A4:{rr["A4"]}</span>')
            rk += (
                f"<tr><td>{rr['rank']}</td><td>{rr['nome']}</td><td>{rr['area']}</td>"
                f"<td>{rr['score']}</td><td>{rr['estrato_A']} {det}</td>"
                f"<td>{rr['sjr_q1q2']}</td><td>{rr['artigos']}</td></tr>"
            )
        sec_rank = f"""
    <section class="section">
      <div class="eyebrow">Quem publica com mais impacto</div>
      <h2>Top 10 docentes por impacto Qualis</h2>
      <p class="desc">Pontuação = soma dos pesos Qualis dos artigos em periódicos
      (A1=100, A2=85, A3=70, A4=55, B1=40…C=3; melhor estrato entre áreas). Congressos
      não entram (sem Qualis oficial); Q1+Q2 (SJR) ao lado como validação internacional.</p>
      <table><thead><tr><th>#</th><th>Docente</th><th>Área</th><th>Score Qualis</th>
      <th>Artigos A1–A4</th><th>Q1+Q2 SJR</th><th>Artigos</th></tr></thead>
      <tbody>{rk}</tbody></table>
    </section>"""

    # ranking por QUALIDADE (média Qualis por artigo), com piso de artigos
    sec_qual = ""
    MIN_ART = 5
    if ranking:
        elig = [x for x in ranking if x.get("artigos_qualis", 0) >= MIN_ART]
        elig.sort(key=lambda x: (-x["qualidade"], -x["pct_A"], -x["artigos_qualis"]))
        qq = ""
        for i, x in enumerate(elig[:12], 1):
            qq += (
                f"<tr><td>{i}</td><td>{x['nome']}</td><td>{x['subarea']}</td>"
                f"<td><b>{x['qualidade']:.0f}</b></td><td>{x['pct_A']}%</td>"
                f"<td>{x['estrato_A']}/{x['artigos_qualis']}</td>"
                f"<td>{x['sjr_q1q2']}</td></tr>"
            )
        sec_qual = f"""
    <section class="section">
      <div class="eyebrow">Qualidade acima de quantidade</div>
      <h2>Impacto médio por artigo (nota Qualis)</h2>
      <p class="desc">Ranking por <b>qualidade</b>, não volume: nota = média do peso Qualis
      por artigo em periódico (100 = só A1, 85 = A2, 70 = A3, 55 = A4…). Favorece quem publica
      pouco mas em estratos altos. Inclui apenas docentes com ≥{MIN_ART} artigos com Qualis
      (para a média ser confiável). "%A" = fração em A1–A4.</p>
      <table><thead><tr><th>#</th><th>Docente</th><th>Sub-área</th><th>Nota Qualis (0–100)</th>
      <th>%A</th><th>A1–A4 / c/ Qualis</th><th>Q1+Q2 SJR</th></tr></thead>
      <tbody>{qq}</tbody></table>
    </section>"""

    # ascensão: quem cresceu em qualidade no último decênio
    sec_asc = ""
    if asc:
        up = [x for x in asc if x["delta"] > 0][:12]
        ar = ""
        for i, x in enumerate(up, 1):
            seta = '▲'
            ar += (
                f"<tr><td>{i}</td><td>{x['nome']}</td><td>{x['subarea']}</td>"
                f"<td>{x['media_antiga']:.0f}</td><td>{x['media_recente']:.0f}</td>"
                f"<td style='color:var(--brand);font-weight:700;'>{seta} +{x['delta']:.0f}</td>"
                f"<td>{x['n_antigo']}→{x['n_recente']}</td></tr>"
            )
        sec_asc = f"""
    <section class="section">
      <div class="eyebrow">Trajetória de crescimento</div>
      <h2>Pesquisadores em ascensão</h2>
      <p class="desc">Variação da <b>qualidade média</b> (peso Qualis por artigo) entre a janela
      <b>2016–2020</b> e <b>2021–2025</b>. Δ positivo = passou a publicar em estratos mais altos.
      Inclui apenas quem tem ≥2 artigos com Qualis em cada janela. "Artigos" = nº antigo→recente.</p>
      <table><thead><tr><th>#</th><th>Docente</th><th>Sub-área</th>
      <th>Nota 2016–20</th><th>Nota 2021–25</th><th>Δ qualidade</th><th>Artigos</th></tr></thead>
      <tbody>{ar}</tbody></table>
    </section>"""

    # líderes por grande área
    sec_lider = ""
    if ranking:
        best: dict[str, dict] = {}
        for rr in ranking:
            ga = rr.get("area") or "—"
            if ga not in best or rr["score"] > best[ga]["score"]:
                best[ga] = rr
        lrows = "".join(
            f"<tr><td>{ga}</td><td>{b['nome']}</td><td>{b['score']}</td>"
            f"<td>{b['estrato_A']}</td></tr>"
            for ga, b in sorted(best.items(), key=lambda kv: -kv[1]["score"])
            if b["score"] > 0 and ga != "—"
        )
        # subseção: líder por QUALIDADE (nota média), piso de artigos
        bestq: dict[str, dict] = {}
        for rr in ranking:
            if rr.get("artigos_qualis", 0) < MIN_ART:
                continue
            ga = rr.get("area") or "—"
            if ga == "—":
                continue
            if ga not in bestq or rr["qualidade"] > bestq[ga]["qualidade"]:
                bestq[ga] = rr
        qrows = "".join(
            f"<tr><td>{ga}</td><td>{b['nome']}</td><td><b>{b['qualidade']:.0f}</b></td>"
            f"<td>{b['pct_A']}%</td><td>{b['estrato_A']}/{b['artigos_qualis']}</td></tr>"
            for ga, b in sorted(bestq.items(), key=lambda kv: -kv[1]["qualidade"])
        )
        sec_lider = f"""
    <section class="section">
      <div class="eyebrow">Liderança por grande área</div>
      <h2>Líderes por grande área</h2>
      <p class="desc">Docente de maior <b>score Qualis</b> (volume × qualidade) em cada grande
      área de conhecimento.</p>
      <table><thead><tr><th>Grande área</th><th>Líder</th><th>Score Qualis</th><th>A1–A4</th></tr></thead>
      <tbody>{lrows}</tbody></table>

      <h3 style="font-family:var(--serif);font-size:20px;margin:28px 0 8px;">Por qualidade (nota média), não volume</h3>
      <p class="desc">Líder por <b>nota Qualis média</b> por artigo (100 = só A1), entre quem tem
      ≥{MIN_ART} artigos com Qualis na área — destaca quem publica em estratos altos,
      independente do volume.</p>
      <table><thead><tr><th>Grande área</th><th>Líder por qualidade</th><th>Nota (0–100)</th>
      <th>%A</th><th>A1–A4 / c/ Qualis</th></tr></thead>
      <tbody>{qrows}</tbody></table>
      <div class="note-line"><b>Ressalva:</b> congressos não entram no score — a CAPES
      descontinuou o Qualis Eventos (2019) e não há ISSN para casar. O ranking é por
      periódicos; Q1+Q2 (SJR) serve como validação internacional.</div>
    </section>"""

    # ranking por sub-área
    sec_sub = ""
    if ranking:
        groups: dict[str, list] = defaultdict(list)
        for rr in ranking:
            groups[rr.get("subarea") or "—"].append(rr)
        # ordena sub-áreas pela soma de score; ignora as sem pontuação
        ordered = sorted(
            ((sa, rs) for sa, rs in groups.items()),
            key=lambda kv: -sum(x["score"] for x in kv[1]),
        )
        blocks = ""
        for sa, rs in ordered:
            if sum(x["score"] for x in rs) == 0:
                continue
            rs = sorted(rs, key=lambda x: (-x["score"], -x["estrato_A"]))[:5]
            lis = "".join(
                f'<tr><td>{x["nome"]}</td><td>{x["score"]}</td>'
                f'<td>{x["estrato_A"]}</td><td>{x["sjr_q1q2"]}</td></tr>'
                for x in rs
            )
            blocks += (
                f'<div class="card" style="margin-bottom:16px;">'
                f'<h3>{sa} <span style="color:var(--muted);font-weight:500;font-size:13px;">'
                f'· {len(groups[sa])} docentes</span></h3>'
                f'<table><thead><tr><th>Docente</th><th>Score Qualis</th>'
                f'<th>A1–A4</th><th>Q1+Q2 SJR</th></tr></thead><tbody>{lis}</tbody></table></div>'
            )
        # subseção por QUALIDADE (nota média), piso de artigos
        blocks_q = ""
        for sa, rs in ordered:
            elig = sorted(
                (x for x in rs if x.get("artigos_qualis", 0) >= MIN_ART),
                key=lambda x: (-x["qualidade"], -x["pct_A"]),
            )[:5]
            if not elig:
                continue
            lis = "".join(
                f'<tr><td>{x["nome"]}</td><td><b>{x["qualidade"]:.0f}</b></td>'
                f'<td>{x["pct_A"]}%</td><td>{x["estrato_A"]}/{x["artigos_qualis"]}</td>'
                f'<td>{x["sjr_q1q2"]}</td></tr>'
                for x in elig
            )
            blocks_q += (
                f'<div class="card" style="margin-bottom:16px;">'
                f'<h3>{sa}</h3>'
                f'<table><thead><tr><th>Docente</th><th>Nota Qualis</th><th>%A</th>'
                f'<th>A1–A4 / c/ Qualis</th><th>Q1+Q2 SJR</th></tr></thead>'
                f'<tbody>{lis}</tbody></table></div>'
            )
        sec_sub = f"""
    <section class="section">
      <div class="eyebrow">Impacto por sub-área</div>
      <h2>Top docentes em cada sub-área de conhecimento</h2>
      <p class="desc">Score Qualis (volume × qualidade) separado pela sub-área de atuação
      predominante do docente (campo "área" do Lattes — ex.: Ciência da Computação,
      Engenharia Elétrica). Top 5 por sub-área.</p>
      {blocks}

      <h3 style="font-family:var(--serif);font-size:22px;margin:34px 0 8px;">Por qualidade (nota média), não volume</h3>
      <p class="desc">Mesmas sub-áreas, agora ordenando pela <b>nota Qualis média</b> por artigo
      (100 = só A1), entre quem tem ≥{MIN_ART} artigos com Qualis — destaca consistência de
      estrato alto, não quantidade.</p>
      {blocks_q}
    </section>"""

    # congressos (com Qualis CC)
    cdist = defaultdict(int)
    for k, v in payload.get("distribuicao_qualis_conf", {}).items():
        cdist["—" if k in ("-", "") else k] += v
    ctot = sum(cdist.values())
    conf_matched = payload["resumo"].get("congressos_com_qualis", 0)
    conf_bars = _bars(cdist, ["A1", "A2", "B1", "B2", "B3", "B4", "B5", "—"],
                      _QUALIS_COLOR, ctot)
    crows = "".join(
        f"<tr><td>{c['evento'][:60]}</td><td>{_qbadge(c.get('qualis','—'), _QUALIS_COLOR)}</td>"
        f"<td>{c['publicacoes']}</td><td>{c['n_docentes']}</td></tr>"
        for c in payload["top_congressos"][:15]
    )
    sec_cong = f"""
    <section class="section">
      <div class="eyebrow">Eventos · impacto</div>
      <h2>Congressos e seu Qualis (CC)</h2>
      <p class="desc">Em Computação, conferências são canal primário de publicação. Aqui cada
      evento é casado por acrônimo/nome ao <b>Qualis de Conferências da Computação</b>
      (A1–B5). {conf_matched} dos {payload['resumo']['n_congressos_distintos']} eventos têm
      Qualis CC; o restante são congressos de Engenharia/Educação fora da lista de CC.
      Edições são fundidas (removidos ano e número).</p>
      <div class="card"><div class="card-head"><h3>Trabalhos por estrato Qualis CC</h3></div>
        {conf_bars}</div>
      <h3 style="font-family:var(--serif);font-size:20px;margin:26px 0 8px;">Principais congressos</h3>
      <table><thead><tr><th>Congresso / Evento</th><th>Qualis CC</th><th>Trabalhos</th><th>Docentes</th></tr></thead>
      <tbody>{crows}</tbody></table>
    </section>"""

    # ranking combinado: revistas + congressos
    sec_comb = ""
    if ranking:
        comb = sorted(ranking, key=lambda x: -x.get("score_total", x["score"]))[:12]
        cb = ""
        for i, x in enumerate(comb, 1):
            cb += (
                f"<tr><td>{i}</td><td>{x['nome']}</td><td>{x['subarea']}</td>"
                f"<td>{x['score']}</td><td>{x.get('score_conf',0)}</td>"
                f"<td><b>{x.get('score_total', x['score'])}</b></td>"
                f"<td>{x['artigos_qualis']} art · {x.get('conf_qualis',0)} conf</td></tr>"
            )
        # por QUALIDADE combinada: nota média = score_total / itens c/ Qualis (revista+conf)
        def _comb_items(x):
            return x.get("artigos_qualis", 0) + x.get("conf_qualis", 0)

        def _comb_qual(x):
            it = _comb_items(x)
            return (x.get("score_total", x["score"]) / it) if it else 0.0

        elig = [x for x in ranking if _comb_items(x) >= MIN_ART]
        elig.sort(key=lambda x: -_comb_qual(x))
        cq = ""
        for i, x in enumerate(elig[:12], 1):
            it = _comb_items(x)
            cq += (
                f"<tr><td>{i}</td><td>{x['nome']}</td><td>{x['subarea']}</td>"
                f"<td><b>{_comb_qual(x):.0f}</b></td>"
                f"<td>{x.get('score_total', x['score'])}</td>"
                f"<td>{x['artigos_qualis']} art · {x.get('conf_qualis',0)} conf</td></tr>"
            )
        _st = lambda x: x.get("score_total", x["score"])
        # líderes por grande área (score combinado)
        bestc: dict[str, dict] = {}
        for x in ranking:
            ga = x.get("area") or "—"
            if ga not in bestc or _st(x) > _st(bestc[ga]):
                bestc[ga] = x
        cmb_lider = "".join(
            f"<tr><td>{ga}</td><td>{b['nome']}</td><td><b>{_st(b)}</b></td>"
            f"<td>{b['score']}</td><td>{b.get('score_conf',0)}</td></tr>"
            for ga, b in sorted(bestc.items(), key=lambda kv: -_st(kv[1]))
            if _st(b) > 0 and ga != "—"
        )
        # top por sub-área (score combinado)
        gsub: dict[str, list] = defaultdict(list)
        for x in ranking:
            gsub[x.get("subarea") or "—"].append(x)
        cmb_sub = ""
        for sa, rs in sorted(gsub.items(), key=lambda kv: -sum(_st(y) for y in kv[1])):
            if sum(_st(y) for y in rs) == 0:
                continue
            top5 = sorted(rs, key=lambda y: -_st(y))[:5]
            lis = "".join(
                f"<tr><td>{y['nome']}</td><td><b>{_st(y)}</b></td>"
                f"<td>{y['score']}</td><td>{y.get('score_conf',0)}</td></tr>"
                for y in top5
            )
            cmb_sub += (
                f'<div class="card" style="margin-bottom:16px;"><h3>{sa}</h3>'
                f'<table><thead><tr><th>Docente</th><th>Score total</th>'
                f'<th>Revistas</th><th>Congressos</th></tr></thead><tbody>{lis}</tbody></table></div>'
            )
        sec_comb = f"""
    <section class="section">
      <div class="eyebrow">Visão integrada</div>
      <h2>Impacto combinado — revistas + congressos</h2>
      <p class="desc">Score total = soma dos pesos Qualis dos <b>periódicos</b> (por ISSN) e dos
      <b>congressos</b> (Qualis CC, por acrônimo/nome). Reconhece quem publica forte em
      conferências — padrão da Computação — além dos periódicos.</p>
      <table><thead><tr><th>#</th><th>Docente</th><th>Sub-área</th><th>Score revistas</th>
      <th>Score congressos</th><th>Score total</th><th>Itens c/ Qualis</th></tr></thead>
      <tbody>{cb}</tbody></table>

      <h3 style="font-family:var(--serif);font-size:22px;margin:34px 0 8px;">Por qualidade (nota média combinada), não volume</h3>
      <p class="desc">Nota = score total ÷ itens com Qualis (periódicos + congressos): a média do
      estrato considerando os dois canais (100 = só A1). Destaca consistência de alto estrato,
      não volume. Inclui quem tem ≥{MIN_ART} itens com Qualis somando revistas e congressos.</p>
      <table><thead><tr><th>#</th><th>Docente</th><th>Sub-área</th><th>Nota combinada (0–100)</th>
      <th>Score total</th><th>Itens c/ Qualis</th></tr></thead>
      <tbody>{cq}</tbody></table>

      <h3 style="font-family:var(--serif);font-size:22px;margin:34px 0 8px;">Líderes por grande área (score combinado)</h3>
      <p class="desc">Docente de maior score total (revistas + congressos) em cada grande área.</p>
      <table><thead><tr><th>Grande área</th><th>Líder</th><th>Score total</th>
      <th>Revistas</th><th>Congressos</th></tr></thead><tbody>{cmb_lider}</tbody></table>

      <h3 style="font-family:var(--serif);font-size:22px;margin:34px 0 8px;">Top docentes por sub-área (score combinado)</h3>
      <p class="desc">Top 5 por sub-área, pelo score total (revistas + congressos).</p>
      {cmb_sub}
      <div class="note-line">Congressos casados apenas na área de Computação (lista Qualis-CC 2016);
      eventos de Engenharia/Educação não pontuam — ainda subestima docentes dessas áreas.</div>
    </section>"""

    # Metodologia + fontes
    q_total = sum(payload["distribuicao_qualis"].values()) if qualis_applied else 0
    sec_metodo = f"""
    <section class="section">
      <div class="eyebrow">Metodologia e fontes</div>
      <h2>Como esta análise foi feita</h2>
      <div class="findings">
        <div class="finding"><span class="tag rs">Coleta</span>
          <h3>1. Veículos a partir do Lattes</h3>
          <p>As revistas e congressos vêm dos currículos <b>Lattes</b> dos{
          (' ' + str(len(ranking))) if ranking else ''} docentes do campus (seções
          <i>artigos em periódicos</i> e <i>trabalhos completos em congressos</i>).
          Cada artigo traz o <b>ISSN</b> do periódico —
          a chave de cruzamento com as bases de impacto. Edições de um mesmo congresso são
          unificadas removendo ano e número de edição (15th, XLIV, II…).</p>
        </div>
        <div class="finding"><span class="tag eq">Impacto internacional</span>
          <h3>2. SJR (SCImago) por ISSN</h3>
          <p>Cada revista é casada por <b>ISSN</b> com a base <b>SCImago Journal Rank (SJR)</b>,
          métrica internacional derivada do Scopus. Dela vêm o <b>quartil Q1–Q4</b> (melhor
          quartil do periódico), o índice SJR e o H-index. Revistas fora do Scopus ficam "sem SJR".</p>
        </div>
        <div class="finding"><span class="tag sp">Classificação nacional</span>
          <h3>3. Qualis CAPES por ISSN</h3>
          <p>O mesmo <b>ISSN</b> é casado com a tabela <b>Qualis Periódicos da CAPES
          (quadriênio 2017–2020)</b>. Como o Qualis varia por área de avaliação, usamos o
          <b>melhor estrato</b> do periódico entre todas as áreas (A1 é o topo). Por isso o
          Qualis cobre mais revistas que o SJR — inclui periódicos nacionais não indexados no Scopus.</p>
        </div>
        <div class="finding"><span class="tag sp">Congressos (Computação)</span>
          <h3>4. Qualis de Conferências CC</h3>
          <p>Como em Computação a conferência é canal primário, casamos cada congresso (por
          <b>acrônimo</b> ou nome) ao <b>Qualis de Conferências da Computação</b> (lista CC 2016,
          A1–B5). É o único ranking de eventos disponível — a CAPES descontinuou o Qualis
          Eventos geral em 2019. Cobre os eventos de CC; os de Engenharia/Educação ficam de fora.</p>
        </div>
        <div class="finding"><span class="tag eq">Ranking de docentes</span>
          <h3>5. Score de impacto</h3>
          <p>O score de cada docente é a <b>soma dos pesos Qualis</b> (A1=100, A2=85, A3=70,
          A4=55, B1=40, B2=30, B3=20, B4=10, C=3). O <b>score total</b> soma periódicos +
          congressos CC. A divisão por sub-área usa o campo "área" do Lattes.</p>
        </div>
      </div>
      <div class="note-line">
        <b>Limitações:</b> o Qualis de conferências cobre só Computação (lista CC 2016) — congressos
        de Engenharia/Educação não pontuam, subestimando esses docentes. Casamento de congressos é
        por nome/acrônimo (sem ISSN), sujeito a erro. Artigos em periódicos fora do Scopus não
        recebem quartil SJR. O "melhor estrato entre áreas" é leitura otimista do Qualis de periódicos.
      </div>
      <div class="card" style="margin-top:18px;">
        <h3>Fontes dos dados</h3>
        <table>
          <thead><tr><th>Dado</th><th>Fonte</th><th>Link</th></tr></thead>
          <tbody>
            <tr><td>Veículos de publicação (revistas, congressos, ISSN)</td>
              <td>Plataforma Lattes (CNPq)</td>
              <td><a href="http://lattes.cnpq.br/">lattes.cnpq.br</a></td></tr>
            <tr><td>Impacto internacional (quartil SJR, índice, H-index)</td>
              <td>SCImago Journal &amp; Country Rank</td>
              <td><a href="https://www.scimagojr.com/journalrank.php">scimagojr.com</a></td></tr>
            <tr><td>Qualis Periódicos 2017–2020 (estrato por ISSN)</td>
              <td>CAPES / Plataforma Sucupira</td>
              <td><a href="https://sucupira.capes.gov.br/">sucupira.capes.gov.br</a></td></tr>
            <tr><td>Qualis de Conferências CC (estrato por acrônimo/nome)</td>
              <td>CAPES (lista CC 2016) · portal UFMT</td>
              <td><a href="https://qualis.ic.ufmt.br/">qualis.ic.ufmt.br</a></td></tr>
          </tbody>
        </table>
      </div>
    </section>"""

    fontes = payload.get("fontes", {})
    qfonte = fontes.get("qualis", "")
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Veículos de Publicação — IFES Campus Serra</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="page">
  <div class="hero">
    <span class="kicker">IFES Campus Serra · Análise de Veículos</span>
    <h1>Onde a pesquisa do campus é publicada</h1>
    <p class="lede">Revistas e congressos dos docentes, classificados por impacto internacional
    (SJR/SCImago){' e Qualis CAPES' if qualis_applied else ''}.</p>
    <div class="meta"><span><b>{r['n_revistas_distintas']}</b> revistas</span>
      <span><b>{r['n_artigos']}</b> artigos</span>
      <span><b>{r['n_congressos_distintos']}</b> congressos</span>
      <span>Fonte: Lattes + SJR{' + Qualis' if qualis_applied else ''}</span></div>
  </div>
  {kpis}{sec_sjr}{sec_qualis}{sec_rank}{sec_qual}{sec_asc}{sec_lider}{sec_sub}{sec_top}{sec_cong}{sec_comb}{sec_metodo}
  <div class="foot"><span>Gerado em {payload.get('gerado_em','')} · veículos: Lattes ·
  impacto: {fontes.get('impacto_internacional','SJR')} · qualis: {qfonte}</span></div>
</div></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--html", default=str(OUT_DIR / "venues_analysis.html"))
    ap.add_argument("--no-qualis", action="store_true",
                    help="ignora o Qualis mesmo se o CSV existir (só SJR)")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--download-scimago", action="store_true",
                    help="baixa/atualiza a base SCImago (data/reference/scimago.csv)")
    ap.add_argument("--qualis", default=str(REF_DIR / "qualis.csv"),
                    help="CSV Qualis (ISSN -> estrato)")
    args = ap.parse_args()

    if args.download_scimago or not SCIMAGO_CSV.exists():
        download_scimago()

    scimago = load_scimago()
    qualis = {} if args.no_qualis else load_qualis(Path(args.qualis))
    conf_acro, conf_name = load_qualis_conf()
    qualis_applied = bool(qualis)
    print(f"Referências: SCImago={len(scimago)} ISSNs · Qualis={len(qualis)} ISSNs"
          f" · Qualis-Conf={len(conf_acro)} acrônimos"
          f"{' (desligado)' if args.no_qualis else ''}")

    roster = _roster()
    journals, confs = collect_venues(roster)
    print(f"Coletado: {len(journals)} revistas · {len(confs)} congressos "
          f"(de {len(roster)} docentes)")

    payload = enrich_and_summarize(journals, confs, scimago, qualis, args.top,
                                   conf_acro, conf_name)
    ranking = (rank_docentes(roster, qualis, scimago, conf_acro, conf_name)
               if qualis_applied else [])
    asc = ascension(roster, qualis) if qualis_applied else []
    payload["ranking_docentes"] = ranking
    payload["ascensao"] = asc
    payload["gerado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    payload["fontes"] = {
        "veiculos": "currículos Lattes (data/lattes_json)",
        "impacto_internacional": "SCImago Journal Rank (SJR), casado por ISSN",
        "qualis": "CAPES/CNPq, casado por ISSN" if qualis else "não fornecido",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written: {out}")

    html_path = Path(args.html)
    html_path.write_text(render_html(payload, qualis_applied, ranking, asc), encoding="utf-8")
    print(f"Written: {html_path}")

    r = payload["resumo"]
    print(f"\n  revistas={r['n_revistas_distintas']} (SJR {r['revistas_com_sjr']} · "
          f"Qualis {r['revistas_com_qualis']}) · artigos={r['n_artigos']}")
    print(f"  SJR quartil: {payload['distribuicao_sjr_quartil']}")
    print("  Top 5 revistas:")
    for j in payload["top_revistas"][:5]:
        print(f"    {j['publicacoes']:>3}x  {j['revista'][:50]:<50} "
              f"SJR={j['sjr_quartil']} Qualis={j['qualis']}")
    print("  Top 5 congressos:")
    for c in payload["top_congressos"][:5]:
        print(f"    {c['publicacoes']:>3}x  {c['evento'][:60]}")


if __name__ == "__main__":
    main()
