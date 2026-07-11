#!/usr/bin/env python3
"""Plano de curto prazo do relatório de ROI — execução das 4 ações:

  1. Padronizar janelas temporais  -> produção (Lattes) e fomento (FAPES) por ano,
     com janela-padrão 2015–2026 e janela recente 2021–2025.
  2. Recalcular Gini segregando UnAC (e ConectaFapes) — projetos institucionais/
     programáticos que distorcem a concentração "por pesquisador".
  3. (OpenAlex p/ 93 — feito por src.scripts.fetch_openalex_citations; aqui só medimos
     a cobertura final e listamos os docentes sem casamento por DOI.)
  4. Revisar patentes — re-extrai sinais de PI do Lattes e gera worklist p/ checagem INPI.

Saídas (output/):
  janelas_temporais.csv · gini_segregado.csv · cobertura_openalex.csv ·
  patentes_worklist_inpi.csv · plano_curto_prazo.json
"""
from __future__ import annotations

import csv
import glob
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.scripts.generate_docentes_executive import ROSTER_IDS  # noqa: E402

LATTES = ROOT / "data" / "lattes_json"
FAPES = ROOT / "data" / "exports" / "projetos-fapes" / "ifes-campus-serra-projetos-concluidos-em-andamento.json"
OPENALEX = ROOT / "data" / "exports" / "docentes" / "openalex_citacoes.json"
OUT = ROOT / "output"

JANELA_INI, JANELA_FIM = 2015, 2026          # janela-padrão (alinhada ao fomento FAPES)
RECENTE_INI, RECENTE_FIM = 2021, 2025        # janela recente (5 anos fechados)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


_FAIXAS = [(1e5, "≤ R$ 100 mil"), (5e5, "R$ 100–500 mil"), (1e6, "R$ 500 mil–1 mi"),
           (5e6, "R$ 1–5 mi"), (2e7, "R$ 5–20 mi"), (5e7, "R$ 20–50 mi")]


def faixa(v) -> str:
    v = num(v)
    if v <= 0:
        return "sem valor"
    for lim, rot in _FAIXAS:
        if v <= lim:
            return rot
    return "> R$ 50 mi"


def ordem(v) -> str:
    v = num(v)
    if v <= 0:
        return "—"
    mi = v / 1e6
    if mi < 1:
        return "menos de R$ 1 mi"
    e = 10 ** (len(str(int(mi))) - 1)
    r = int(round(mi / e) * e)
    qual = "centenas de milhões" if mi >= 100 else ("dezenas de milhões" if mi >= 10 else "milhões")
    return f"ordem de ~R$ {r} mi ({qual})"


def gini(values: list[float]) -> float:
    xs = sorted(v for v in values if v is not None)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * sum(xs)) - (n + 1) / n, 3)


def lattes_index():
    by_id = {}
    for f in glob.glob(str(LATTES / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f
    return by_id


def _ano(v):
    try:
        return int(str(v).strip()[:4])
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# 1. Janelas temporais
# ---------------------------------------------------------------------------
def janelas_temporais():
    by_id = lattes_index()
    art_ano = defaultdict(int)
    seen = set()  # dedup GLOBAL por título (artigo co-autorado conta 1x no total do campus)
    for nome, lid in ROSTER_IDS.items():
        f = by_id.get(lid)
        if not f:
            continue
        pb = (json.loads(Path(f).read_text(encoding="utf-8"))
              .get("producao_bibliografica", {}) or {})
        for i, a in enumerate(pb.get("artigos_periodicos", []) or []):
            t = norm(a.get("titulo", ""))
            key = t if t else f"__{lid}_{i}"
            if key in seen:
                continue
            seen.add(key)
            y = _ano(a.get("ano"))
            if y:
                art_ano[y] += 1
    # fomento FAPES por ano
    d = json.loads(FAPES.read_text(encoding="utf-8"))["projetos"]
    fap_ano = defaultdict(float)
    for grp in d:
        for x in d[grp]:
            y = _ano(x.get("ano"))
            if y:
                fap_ano[y] += num(x.get("orcamento_contratado"))
    anos = sorted(set(list(art_ano) + list(fap_ano)))
    # fomento por ano em FAIXA (sem R$ concreto)
    linhas = [{"ano": y, "artigos": art_ano.get(y, 0),
               "fapes_orcamento_faixa": faixa(fap_ano.get(y, 0)),
               "na_janela_padrao": JANELA_INI <= y <= JANELA_FIM} for y in anos]

    def soma(d, a, b):
        return sum(v for k, v in d.items() if a <= k <= b)
    resumo = {
        "janela_padrao": [JANELA_INI, JANELA_FIM], "janela_recente": [RECENTE_INI, RECENTE_FIM],
        "artigos_total": sum(art_ano.values()),
        "artigos_na_janela_padrao": soma(art_ano, JANELA_INI, JANELA_FIM),
        "artigos_fora_janela": sum(art_ano.values()) - soma(art_ano, JANELA_INI, JANELA_FIM),
        "artigos_recente": soma(art_ano, RECENTE_INI, RECENTE_FIM),
        "fapes_na_janela_padrao_ordem": ordem(soma(fap_ano, JANELA_INI, JANELA_FIM)),
        "fapes_recente_ordem": ordem(soma(fap_ano, RECENTE_INI, RECENTE_FIM)),
    }
    return linhas, resumo


# ---------------------------------------------------------------------------
# 2. Gini segregando UnAC / ConectaFapes
# ---------------------------------------------------------------------------
def _classifica_projeto(titulo: str) -> str | None:
    t = norm(titulo)
    if "unac" in t or "universidade aberta" in t:
        return "UnAC"
    if "conectafapes" in t or "conecta fapes" in t:
        return "ConectaFapes"
    return None


def gini_segregado():
    d = json.loads(FAPES.read_text(encoding="utf-8"))["projetos"]
    # por coordenador: orçamento total, e parcela institucional (UnAC/ConectaFapes)
    por_coord = defaultdict(lambda: {"orc_total": 0.0, "orc_inst": 0.0})
    inst_detalhe = []
    for grp in d:
        for x in d[grp]:
            c = norm(x.get("coordenador_nome"))
            orc = num(x.get("orcamento_contratado"))
            cls = _classifica_projeto(x.get("projeto_titulo") or "")
            por_coord[c]["orc_total"] += orc
            if cls:
                por_coord[c]["orc_inst"] += orc
                inst_detalhe.append({"classe": cls, "coordenador": x.get("coordenador_nome"),
                                     "faixa": faixa(orc),
                                     "titulo": (x.get("projeto_titulo") or "")[:80]})
    base = [v["orc_total"] for v in por_coord.values()]
    # cenário A: remove só UnAC; B: remove UnAC + ConectaFapes (institucionais)
    sem_inst = [max(0.0, v["orc_total"] - v["orc_inst"]) for v in por_coord.values()]
    # também: Gini sobre PESQUISA stricto sensu (coordenadores que sobram com >0)
    sem_inst_pos = [v for v in sem_inst if v > 0]
    total = sum(base)
    inst_total = sum(v["orc_inst"] for v in por_coord.values())
    # ordena institucionais por classe+título (sem expor R$)
    cenarios = {
        "gini_base_todos": gini(base),
        "gini_sem_institucionais": gini(sem_inst),
        "gini_sem_institucionais_pos": gini(sem_inst_pos),
        "orcamento_total_ordem": ordem(total),
        "orcamento_institucional_ordem": ordem(inst_total),
        "pct_institucional": round(inst_total / total * 100, 1) if total else 0,
        "projetos_institucionais": sorted(inst_detalhe, key=lambda r: (r["classe"], r["titulo"])),
    }
    return cenarios


# ---------------------------------------------------------------------------
# 3. Cobertura OpenAlex (mede após o pipeline; lista sem casamento)
# ---------------------------------------------------------------------------
def cobertura_openalex():
    if not OPENALEX.exists():
        return {"erro": "openalex_citacoes.json ausente"}, []
    docs = json.loads(OPENALEX.read_text(encoding="utf-8"))["docentes"]
    com = [d for d in docs if d.get("encontrados_openalex", 0) > 0]
    sem = [d for d in docs if d.get("encontrados_openalex", 0) == 0]
    linhas = [{"docente": d["nome"], "lattes_id": d.get("lattes_id", ""),
               "artigos_com_doi": d.get("artigos_com_doi", 0),
               "encontrados_openalex": d.get("encontrados_openalex", 0)} for d in docs]
    resumo = {"n_total": len(docs), "n_com_openalex": len(com), "n_sem": len(sem),
              "cobertura_pct": round(len(com) / len(docs) * 100, 1) if docs else 0,
              "sem_match": [d["nome"] for d in sem]}
    return resumo, linhas


# ---------------------------------------------------------------------------
# 4. Patentes — re-extração Lattes + worklist INPI
# ---------------------------------------------------------------------------
def patentes_worklist():
    """Lattes não traz patentes (0 no roster). Logo, a checagem INPI tem de ser por
    NOME do inventor. Gera worklist dos 93 docentes, priorizando quem tem produção
    técnica (software/produto) — mais propensos a ter depósito de patente."""
    by_id = lattes_index()
    rows = []
    tot_pat = tot_soft_pat = tot_soft = tot_prod = 0
    for nome, lid in ROSTER_IDS.items():
        f = by_id.get(lid)
        if not f:
            continue
        cv = json.loads(Path(f).read_text(encoding="utf-8"))
        pr = cv.get("patentes_registros", {}) or {}
        pt = cv.get("producao_tecnica", {}) or {}
        n_pat = len(pr.get("patentes") or [])
        n_soft_pat = len(pt.get("softwares_com_patente") or [])
        n_soft = len(pt.get("softwares_sem_patente") or []) + n_soft_pat
        n_prod = len(pt.get("produtos_tecnologicos") or [])
        tot_pat += n_pat; tot_soft_pat += n_soft_pat; tot_soft += n_soft; tot_prod += n_prod
        prioridade = "alta" if (n_soft + n_prod) >= 1 else "baixa"
        rows.append({
            "docente": nome,
            "patentes_lattes": n_pat, "softwares_lattes": n_soft, "produtos_tec_lattes": n_prod,
            "prioridade_inpi": prioridade,
            "verificar_inpi": "SIM (busca por inventor)",
        })
    rows.sort(key=lambda r: (r["prioridade_inpi"] != "alta",
                             -(r["softwares_lattes"] + r["produtos_tec_lattes"]), r["docente"]))
    n_alta = sum(1 for r in rows if r["prioridade_inpi"] == "alta")
    return rows, {"patentes_lattes": tot_pat, "softwares_com_patente": tot_soft_pat,
                  "softwares_total": tot_soft, "produtos_tec": tot_prod,
                  "docentes_prioridade_alta": n_alta, "docentes_total": len(rows),
                  "metodo": "Lattes=0 patentes; checar INPI por nome do inventor (sem API; manual/RPA)"}


# ---------------------------------------------------------------------------
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jl, jres = janelas_temporais()
    gseg = gini_segregado()
    ocov, olin = cobertura_openalex()
    pwork, pres = patentes_worklist()

    with (OUT / "janelas_temporais.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ano", "artigos", "fapes_orcamento_faixa", "na_janela_padrao"])
        w.writeheader(); w.writerows(jl)
    with (OUT / "gini_segregado.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cenario", "gini", "descricao"])
        w.writerow(["base_todos", gseg["gini_base_todos"], "todos os coordenadores (inclui institucionais)"])
        w.writerow(["sem_institucionais", gseg["gini_sem_institucionais"], "remove UnAC + ConectaFapes (mantém coords com 0)"])
        w.writerow(["sem_institucionais_pos", gseg["gini_sem_institucionais_pos"], "só coords com fomento de pesquisa > 0"])
    with (OUT / "cobertura_openalex.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["docente", "lattes_id", "artigos_com_doi", "encontrados_openalex"])
        w.writeheader(); w.writerows(olin)
    with (OUT / "patentes_worklist_inpi.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["docente", "patentes_lattes", "softwares_lattes",
                                           "produtos_tec_lattes", "prioridade_inpi", "verificar_inpi"])
        w.writeheader(); w.writerows(pwork)

    payload = {"janelas": {"resumo": jres, "por_ano": jl},
               "gini_segregado": gseg, "cobertura_openalex": ocov,
               "patentes": pres}
    (OUT / "plano_curto_prazo.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("== 1. Janelas ==")
    print(f"  artigos total={jres['artigos_total']} · na janela {JANELA_INI}-{JANELA_FIM}="
          f"{jres['artigos_na_janela_padrao']} · fora={jres['artigos_fora_janela']} · "
          f"recente {RECENTE_INI}-{RECENTE_FIM}={jres['artigos_recente']}")
    print("== 2. Gini segregado ==")
    print(f"  base={gseg['gini_base_todos']} · sem institucionais={gseg['gini_sem_institucionais']} "
          f"· só pesquisa(>0)={gseg['gini_sem_institucionais_pos']} · "
          f"institucional={gseg['pct_institucional']}% do orçamento")
    print("== 3. Cobertura OpenAlex ==")
    print(f"  {ocov.get('n_com_openalex')}/{ocov.get('n_total')} = {ocov.get('cobertura_pct')}% "
          f"· sem match={ocov.get('n_sem')}")
    print("== 4. Patentes ==")
    print(f"  patentes Lattes={pres['patentes_lattes']} (zero) · softwares Lattes={pres['softwares_total']} "
          f"· prioridade alta INPI={pres['docentes_prioridade_alta']}/{pres['docentes_total']} docentes")


if __name__ == "__main__":
    main()
