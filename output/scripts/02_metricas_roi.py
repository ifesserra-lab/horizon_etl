#!/usr/bin/env python3
"""ROI da Pesquisa — IFES Campus Serra : integração + métricas auditáveis.

Lê as fontes locais (Lattes, bolsas SigPesq, projetos FAPES/FACTO, SigPesq
projetos/grupos, OpenAlex) e produz tabelas consolidadas e um JSON intermediário
que alimenta o relatório. NÃO inventa dados: cada métrica registra fonte,
disponibilidade e nível de confiança.

Unidade institucional = roster oficial de 93 docentes (generate_docentes_executive.ROSTER_IDS).
Integração docente↔projeto↔bolsa por NOME normalizado (não há ID comum entre as bases).

Saídas (output/):
  metricas_roi_pesquisa.csv     — indicadores institucionais (valor, fonte, confiança)
  roi_intermediate.json         — payload completo p/ o relatório
  por_coordenador.csv           — fomento × produção por coordenador (auditoria)

Uso:  python -m output.scripts.02_metricas_roi   (ou: python output/scripts/02_metricas_roi.py)
"""
from __future__ import annotations

import csv
import glob
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.scripts.generate_docentes_executive import ROSTER_IDS  # noqa: E402

LATTES = ROOT / "data" / "lattes_json"
FAPES = (
    ROOT
    / "data"
    / "exports"
    / "projetos-fapes"
    / "ifes-campus-serra-projetos-concluidos-em-andamento.json"
)
FACTO = ROOT / "data" / "exports" / "projetos-facto" / "facto_projects_full.json"
BOLSAS = ROOT / "data" / "exports" / "bolsistas" / "ifes-campus-serra-bolsistas.json"
OPENALEX = ROOT / "data" / "exports" / "docentes" / "openalex_citacoes.json"
PPCOMP = ROOT / "data" / "mestrado" / "base_de_dados_ppcomp.json"
OUT = ROOT / "output"


# ---------------------------------------------------------------------------
def norm(s: str) -> str:
    s = (
        unicodedata.normalize("NFKD", s or "")
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )
    return " ".join(s.split())


def num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def gini(values: list[float]) -> float:
    xs = sorted(v for v in values if v is not None)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * sum(xs)) - (n + 1) / n, 3)


# --- Sanitização financeira (privacidade/segurança): nunca expor R$ concreto ---
# Granular (coordenador/projeto/financiadora) -> FAIXA + %. Totais -> ORDEM de grandeza.
_FAIXAS = [
    (1e5, "≤ R$ 100 mil"),
    (5e5, "R$ 100–500 mil"),
    (1e6, "R$ 500 mil–1 mi"),
    (5e6, "R$ 1–5 mi"),
    (2e7, "R$ 5–20 mi"),
    (5e7, "R$ 20–50 mi"),
]


def faixa(v) -> str:
    v = num(v)
    if v <= 0:
        return "sem valor"
    for lim, rot in _FAIXAS:
        if v <= lim:
            return rot
    return "> R$ 50 mi"


def pct(v, total) -> float | None:
    v, total = num(v), num(total)
    return round(v / total * 100, 1) if total else None


def ordem(v) -> str:
    """Ordem de grandeza (1 algarismo significativo), sem cifra exata."""
    v = num(v)
    if v <= 0:
        return "—"
    mi = v / 1e6
    if mi < 1:
        return "menos de R$ 1 mi"
    e = 10 ** (len(str(int(mi))) - 1)
    r = int(round(mi / e) * e)
    qual = (
        "centenas de milhões"
        if mi >= 100
        else ("dezenas de milhões" if mi >= 10 else "milhões")
    )
    return f"ordem de ~R$ {r} mi ({qual})"


def lattes_index() -> dict[str, str]:
    by_id = {}
    for f in glob.glob(str(LATTES / "*.json")):
        m = re.search(r"_(\d{16})\.json$", f)
        if m:
            by_id[m.group(1)] = f
    return by_id


# ---------------------------------------------------------------------------
def carregar_fapes() -> dict:
    d = json.loads(FAPES.read_text(encoding="utf-8"))
    pj = d["projetos"]
    grupos = [
        "concluidos",
        "em_andamento",
        "status_em_andamento_prazo_encerrado",
        "status_em_andamento_prazo_futuro",
        "status_em_andamento_sem_prazo_valido",
    ]
    # dedup por projeto_id (as listas são disjuntas, mas garantimos)
    proj = {}
    status_de = {}
    for g in grupos:
        cat = "concluido" if g == "concluidos" else "em_andamento"
        for x in pj.get(g, []):
            pid = x["projeto_id"]
            proj[pid] = x
            status_de[pid] = cat
    por_ano = defaultdict(float)
    por_coord = defaultdict(
        lambda: {
            "orcamento": 0.0,
            "valor_bolsas": 0.0,
            "n_proj": 0,
            "n_bolsas": 0,
            "anos": set(),
        }
    )
    orc_total = bolsa_total = nb_total = 0.0
    n_conc = n_and = 0
    for pid, x in proj.items():
        orc = num(x.get("orcamento_contratado"))
        vb = num(x.get("valor_bolsas"))
        qb = num(x.get("quantidade_bolsas"))
        ano = x.get("ano")
        orc_total += orc
        bolsa_total += vb
        nb_total += qb
        if status_de[pid] == "concluido":
            n_conc += 1
        else:
            n_and += 1
        if ano:
            por_ano[int(ano)] += orc
        c = norm(x.get("coordenador_nome"))
        if c:
            pc = por_coord[c]
            pc["orcamento"] += orc
            pc["valor_bolsas"] += vb
            pc["n_proj"] += 1
            pc["n_bolsas"] += qb
            if ano:
                pc["anos"].add(int(ano))
    return {
        "n_proj": len(proj),
        "n_concluidos": n_conc,
        "n_andamento": n_and,
        "orcamento_total": round(orc_total, 2),
        "valor_bolsas_total": round(bolsa_total, 2),
        "quantidade_bolsas_total": int(nb_total),
        "por_ano": {k: round(v, 2) for k, v in sorted(por_ano.items())},
        "por_coord": {
            k: {**v, "anos": sorted(v["anos"])} for k, v in por_coord.items()
        },
    }


def _br(v) -> float:
    """Converte número no formato brasileiro ('1.256.355,65') para float."""
    v = (str(v or "")).strip().replace(".", "").replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return 0.0


# Tipos de projeto FACTO considerados PESQUISA (stricto + PD&I + inovação)
FACTO_TIPOS_PESQUISA = {
    "Pesquisa, Desenvolvimento e Inovação",
    "Pesquisa",
    "Inovação",
    "Pesquisa e Extensão",
    "Pesquisa e Ensino",
    "Pesquisa, Ensino e Extensão",
}


def carregar_facto(roster_norm: set[str]) -> dict:
    """FACTO (fundação de apoio à rede IFES). Cada projeto traz 7 CSVs aninhados; usamos
    'Informações do projeto' (valor aprovado, financiadora, tipo, coordenador) e
    'Recursos por rubrica' (Executado por despesa).

    REGRA DE SALDO (campus Serra): só entra no fomento do campus o projeto cujo
    **coordenador é docente do roster** (campus Serra). Participação apenas como EQUIPE
    NÃO soma ao saldo. A FACTO gere projetos de toda a rede; a maioria é de outros
    campi/coordenadores e fica fora do saldo do campus (reportada só como contexto)."""
    if not FACTO.exists():
        return {"n_proj": 0, "aprovado_pesquisa": None}
    projs = json.loads(FACTO.read_text(encoding="utf-8")).get("projects", [])
    n_err = sum(1 for p in projs if p.get("_error"))
    por_fin = defaultdict(lambda: {"n": 0, "aprovado": 0.0})  # só roster-coord
    por_coord = defaultdict(lambda: {"aprovado": 0.0, "executado": 0.0, "n": 0})
    por_ano = defaultdict(float)
    rows = []
    n_info = 0
    ap_total = 0.0
    n_pesq_total = 0
    ap_pesq_total = 0.0  # todo FACTO pesquisa (contexto)
    n_pesq_r = 0
    ap_pesq_r = ex_pesq_r = 0.0  # pesquisa COORD=roster (saldo campus)
    for p in projs:
        csv = p.get("csv") or {}
        info = next((v for k, v in csv.items() if "Informa" in k), None)
        if not (isinstance(info, list) and info):
            continue
        r = info[0]
        n_info += 1
        tipo = r.get("Tipo de Projeto") or "?"
        ap = _br(r.get("Valor aprovado"))
        fin = (r.get("Financiadora") or "").strip()
        coord = (r.get("Coordenador") or "").strip()
        is_roster = norm(coord) in roster_norm
        ini = r.get("Data de início") or ""
        m = re.search(r"(\d{4})", ini[-4:] if len(ini) >= 4 else ini)
        ano = int(m.group(1)) if m else None
        is_pesq = tipo in FACTO_TIPOS_PESQUISA
        ex = 0.0
        if is_pesq:
            rec = next((v for k, v in csv.items() if "rubrica" in k.lower()), None)
            if isinstance(rec, list):
                for row in rec:
                    if "despesa" in (row.get("Tipo da Rubrica") or "").lower():
                        ex += abs(_br(row.get("Executado")))
        ap_total += ap
        if is_pesq:
            n_pesq_total += 1
            ap_pesq_total += ap
            if is_roster:  # <-- só coordenador do campus entra no saldo
                n_pesq_r += 1
                ap_pesq_r += ap
                ex_pesq_r += ex
                if fin:
                    por_fin[fin[:45]]["n"] += 1
                    por_fin[fin[:45]]["aprovado"] += ap
                if coord:
                    pc = por_coord[norm(coord)]
                    pc["aprovado"] += ap
                    pc["executado"] += ex
                    pc["n"] += 1
                if ano:
                    por_ano[ano] += ap
        rows.append(
            {
                "referencia": (r.get("Referência do projeto") or "")[:60],
                "coordenador": coord,
                "coord_roster": is_roster,
                "financiadora": fin,
                "tipo": tipo,
                "ano": ano,
                "aprovado": round(ap, 2),
                "executado": round(ex, 2),
                "pesquisa": is_pesq,
                "conta_saldo": bool(is_pesq and is_roster),
            }
        )
    return {
        "n_proj": len(projs),
        "n_com_info": n_info,
        "n_erros_scrape": n_err,
        # contexto (toda a rede): NÃO é saldo do campus
        "n_pesquisa_total_rede": n_pesq_total,
        "aprovado_pesquisa_total_rede": round(ap_pesq_total, 2),
        # SALDO do campus Serra = só projetos coordenados por docente do roster
        "n_pesquisa": n_pesq_r,
        "aprovado_pesquisa": round(ap_pesq_r, 2),
        "executado_pesquisa": round(ex_pesq_r, 2),
        "por_financiadora": {
            k: {"n": v["n"], "aprovado": round(v["aprovado"], 2)}
            for k, v in sorted(por_fin.items(), key=lambda kv: -kv[1]["aprovado"])
        },
        "por_ano": {k: round(v, 2) for k, v in sorted(por_ano.items())},
        "por_coord": {
            k: {
                "aprovado": round(v["aprovado"], 2),
                "executado": round(v["executado"], 2),
                "n": v["n"],
            }
            for k, v in por_coord.items()
        },
        "_rows": rows,
    }


def carregar_bolsas() -> dict:
    d = json.loads(BOLSAS.read_text(encoding="utf-8"))
    al = d.get("alocacoes", [])
    por_tipo = Counter()
    por_ano = defaultdict(float)
    por_coord = defaultdict(lambda: {"valor": 0.0, "n": 0})
    v_alocado = v_pago = 0.0
    for x in al:
        sig = x.get("bolsa_sigla") or "—"
        va = num(x.get("valor_alocado_total"))
        vp = num(x.get("valor_pago_total"))
        por_tipo[sig] += 1
        v_alocado += va
        v_pago += vp
        ini = (x.get("formulario_bolsa_inicio") or "")[:4]
        if ini.isdigit():
            por_ano[int(ini)] += va
        c = norm(x.get("coordenador_nome"))
        if c:
            por_coord[c]["valor"] += va
            por_coord[c]["n"] += 1
    return {
        "n_alocacoes": len(al),
        "n_bolsistas_unicos": len(d.get("bolsistas_unicos", [])),
        "valor_alocado_total": round(v_alocado, 2),
        "valor_pago_total": round(v_pago, 2),
        "por_tipo": dict(por_tipo.most_common()),
        "por_ano": {k: round(v, 2) for k, v in sorted(por_ano.items())},
        "por_coord": {
            k: {"valor": round(v["valor"], 2), "n": v["n"]}
            for k, v in por_coord.items()
        },
        "n_coordenadores": len(por_coord),
    }


# ---------------------------------------------------------------------------
def _ntitulo(s: str) -> str:
    """Título normalizado p/ deduplicação (NFKD, ascii, minúsculo, espaços colapsados)."""
    return norm(s)


def carregar_producao_roster() -> dict:
    """Agrega produção/orientação dos 93 docentes. TODOS os totais institucionais são
    DISTINTOS (deduplicados por título GLOBALMENTE entre docentes) — uma obra co-autorada
    ou uma dissertação co-orientada conta UMA vez, não uma por coautor/co-orientador.
    `por_doc` mantém a contagem própria de cada docente (não somável institucionalmente).
    """
    by_id = lattes_index()
    # conjuntos globais de títulos já vistos, por categoria (dedup entre docentes)
    seen = defaultdict(set)

    def _distinct(cat: str, items, lid: str) -> int:
        """Conta itens novos (título inédito na categoria). Sem título → único."""
        n = 0
        for i, it in enumerate(items or []):
            t = _ntitulo(it.get("titulo", "")) if isinstance(it, dict) else ""
            key = t if t else f"__{cat}|{lid}|{i}"
            if key in seen[cat]:
                continue
            seen[cat].add(key)
            n += 1
        return n

    def _own(items) -> int:
        """Contagem própria do docente (dedup só intra-docente), p/ por_doc."""
        s, n = set(), 0
        for it in items or []:
            t = _ntitulo(it.get("titulo", "")) if isinstance(it, dict) else ""
            if t and t in s:
                continue
            if t:
                s.add(t)
            n += 1
        return n

    art = liv = cap = cong = 0
    orient_m = orient_d = orient_espec = orient_grad = orient_outros = 0
    orient_m_and = orient_d_and = 0
    pat = soft = prod_tec = registros = premios = proj_pesq = 0
    por_doc = {}
    n_match = 0
    for nome, lid in ROSTER_IDS.items():
        f = by_id.get(lid)
        if not f:
            por_doc[nome] = None
            continue
        n_match += 1
        cv = json.loads(Path(f).read_text(encoding="utf-8"))
        pb = cv.get("producao_bibliografica", {}) or {}
        art += _distinct("artigos", pb.get("artigos_periodicos"), lid)
        liv += _distinct("livros", pb.get("livros_publicados"), lid)
        cap += _distinct("capitulos", pb.get("capitulos_livros"), lid)
        cong += _distinct("congressos", pb.get("trabalhos_completos_congressos"), lid)
        o = cv.get("orientacoes", {}) or {}
        conc = o.get("concluidas", {}) or {}
        anda = o.get("em_andamento", {}) or {}
        orient_m += _distinct("o_mest", conc.get("mestrado"), lid)  # Dissertação
        orient_d += _distinct(
            "o_dout",
            (conc.get("doutorado") or []) + (conc.get("pos_doutorado") or []),
            lid,
        )  # Tese/pós
        orient_espec += _distinct(
            "o_esp", conc.get("especializacao"), lid
        )  # lato sensu
        orient_grad += _distinct(
            "o_grad",
            (conc.get("tcc") or []) + (conc.get("iniciacao_cientifica") or []),
            lid,
        )  # graduação
        orient_outros += _distinct("o_out", conc.get("outros"), lid)
        orient_m_and += _distinct("o_mest_and", anda.get("mestrado"), lid)
        orient_d_and += _distinct(
            "o_dout_and",
            (anda.get("doutorado") or []) + (anda.get("pos_doutorado") or []),
            lid,
        )
        pr = cv.get("patentes_registros", {}) or {}
        pt = cv.get("producao_tecnica", {}) or {}
        pat += _distinct("pat", pr.get("patentes"), lid)
        registros += _distinct(
            "reg",
            (pr.get("programas_computador") or [])
            + (pr.get("desenhos_industriais") or []),
            lid,
        )
        soft += _distinct(
            "soft",
            (pt.get("softwares_com_patente") or [])
            + (pt.get("softwares_sem_patente") or []),
            lid,
        )
        prod_tec += _distinct("prodtec", pt.get("produtos_tecnologicos"), lid)
        premios += _distinct("premios", cv.get("premios_titulos"), lid)
        proj_pesq += _distinct("projpesq", cv.get("projetos_pesquisa"), lid)
        por_doc[nome] = {
            "artigos": _own(pb.get("artigos_periodicos")),
            "livros": _own(pb.get("livros_publicados")),
            "capitulos": _own(pb.get("capitulos_livros")),
            "congressos": _own(pb.get("trabalhos_completos_congressos")),
            "orient_mestrado": _own(conc.get("mestrado")),
            "orient_doutorado": _own(
                (conc.get("doutorado") or []) + (conc.get("pos_doutorado") or [])
            ),
            "orient_especializacao": _own(conc.get("especializacao")),
            "orient_graduacao": _own(
                (conc.get("tcc") or []) + (conc.get("iniciacao_cientifica") or [])
            ),
            "orient_outros": _own(conc.get("outros")),
            "patentes": _own(pr.get("patentes")),
            "softwares": _own(
                (pt.get("softwares_com_patente") or [])
                + (pt.get("softwares_sem_patente") or [])
            ),
            "produtos_tec": _own(pt.get("produtos_tecnologicos")),
            "premios": _own(cv.get("premios_titulos")),
            "projetos_pesquisa": _own(cv.get("projetos_pesquisa")),
        }
    return {
        "n_roster": len(ROSTER_IDS),
        "n_lattes_encontrados": n_match,
        "dedup": "global por título (obra co-autorada/co-orientada conta 1x)",
        "artigos": art,
        "livros": liv,
        "capitulos": cap,
        "congressos": cong,
        "orient_mestrado_conc": orient_m,
        "orient_doutorado_conc": orient_d,
        "orient_especializacao_conc": orient_espec,
        "orient_graduacao_conc": orient_grad,
        "orient_outros_conc": orient_outros,
        "orient_mestrado_and": orient_m_and,
        "orient_doutorado_and": orient_d_and,
        "patentes": pat,
        "softwares": soft,
        "produtos_tec": prod_tec,
        "registros": registros,
        "premios": premios,
        "projetos_pesquisa_lattes": proj_pesq,
        "por_doc": por_doc,
    }


def carregar_openalex() -> dict:
    if not OPENALEX.exists():
        return {}
    d = json.loads(OPENALEX.read_text(encoding="utf-8"))["docentes"]
    com = [x for x in d if x.get("encontrados_openalex", 0) > 0]
    cits = sum(x.get("citacoes_total", 0) for x in com)
    fwcis = sorted(
        x.get("fwci_medio", 0) or 0 for x in com if (x.get("fwci_medio") or 0) > 0
    )
    top10 = sum(x.get("artigos_top10pct", 0) for x in com)
    por_doc = {
        x["nome"]: {
            "cit": x.get("citacoes_total", 0),
            "h": x.get("h_index", 0),
            "fwci": round(x.get("fwci_medio", 0) or 0, 2),
            "top10": x.get("artigos_top10pct", 0),
            "artigos_oa": x.get("encontrados_openalex", 0),
        }
        for x in com
    }
    return {
        "n_com_openalex": len(com),
        "citacoes_total": cits,
        "top10_total": top10,
        "fwci_mediano": fwcis[len(fwcis) // 2] if fwcis else 0,
        "por_doc": por_doc,
    }


def carregar_ppcomp() -> dict:
    if not PPCOMP.exists():
        return {}
    d = json.loads(PPCOMP.read_text(encoding="utf-8"))
    recs = (
        d
        if isinstance(d, list)
        else next((v for v in d.values() if isinstance(v, list)), [])
    )
    sit = Counter((x.get("situacao") or "—") for x in recs)
    defend = sum(
        1
        for x in recs
        if "defend" in (x.get("situacao") or "").lower()
        or (x.get("data_defesa") and "1905" not in str(x.get("data_defesa")))
    )
    return {
        "n_discentes": len(recs),
        "defendidos": sit.get("Defendido", defend),
        "situacao": dict(sit.most_common()),
    }


# ---------------------------------------------------------------------------
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    roster_norm = {norm(n) for n in ROSTER_IDS}
    fapes = carregar_fapes()
    facto = carregar_facto(roster_norm)
    bolsas = carregar_bolsas()
    prod = carregar_producao_roster()
    oa = carregar_openalex()
    ppcomp = carregar_ppcomp()

    inv_fapes = fapes["orcamento_total"]  # FAPES contratado
    # fomento de pesquisa CONSOLIDADO (FAPES contratado + FACTO pesquisa aprovado) =
    # denominador das razões de produtividade (mais completo que só FAPES)
    fomento_pesquisa = round(inv_fapes + (facto.get("aprovado_pesquisa") or 0), 2)
    # produção científica total (peer-review: artigos + livros + capítulos + congressos)
    prod_cient = (
        prod["artigos"] + prod["livros"] + prod["capitulos"] + prod["congressos"]
    )
    titulados = prod["orient_mestrado_conc"] + prod["orient_doutorado_conc"]
    ativos_tec = (
        prod["patentes"] + prod["softwares"] + prod["produtos_tec"] + prod["registros"]
    )

    # razões institucionais (com forte ressalva de atribuição — ver relatório)
    def per_milhao(n):
        return (
            round(n / (fomento_pesquisa / 1_000_000), 2) if fomento_pesquisa else None
        )

    # concentração do fomento (Gini) entre coordenadores FAPES
    coord_vals = [v["orcamento"] for v in fapes["por_coord"].values()]
    gini_fapes = gini(coord_vals)
    top5_coord = sorted(fapes["por_coord"].items(), key=lambda kv: -kv[1]["orcamento"])[
        :5
    ]
    top5_share = (
        round(sum(v["orcamento"] for _, v in top5_coord) / inv_fapes * 100, 1)
        if inv_fapes
        else None
    )

    # candidatos a estudo de caso REF: projetos FAPES de maior orçamento + coordenadores
    # de alto impacto (FWCI/citações) — interseção fomento × impacto
    cand = []
    oa_doc = {norm(k): v for k, v in (oa.get("por_doc") or {}).items()}
    for c, v in sorted(fapes["por_coord"].items(), key=lambda kv: -kv[1]["orcamento"])[
        :12
    ]:
        impacto = oa_doc.get(c, {})
        cand.append(
            {
                "coordenador_norm": c,
                "orcamento": round(v["orcamento"], 2),
                "n_proj": v["n_proj"],
                "anos": v["anos"],
                "citacoes": impacto.get("cit"),
                "fwci": impacto.get("fwci"),
                "top10": impacto.get("top10"),
                "h": impacto.get("h"),
            }
        )

    metricas = [
        # (dimensao, indicador, valor, unidade, fonte, disponib, confianca, obs)
        (
            "Input",
            "Projetos FAPES (concluídos + andamento)",
            fapes["n_proj"],
            "projetos",
            "FAPES",
            "disponível",
            "alto",
            "Universo dedup por projeto_id; 3 listas disjuntas.",
        ),
        (
            "Input",
            "Orçamento FAPES contratado (total)",
            inv_fapes,
            "R$",
            "FAPES",
            "disponível",
            "alto",
            "Contratado, não necessariamente executado.",
        ),
        (
            "Input",
            "Valor de bolsas em projetos FAPES",
            fapes["valor_bolsas_total"],
            "R$",
            "FAPES",
            "disponível",
            "alto",
            "Subconjunto do orçamento; não somar com base de bolsas.",
        ),
        (
            "Input",
            "Bolsas FAPES (quantidade)",
            fapes["quantidade_bolsas_total"],
            "bolsas",
            "FAPES",
            "disponível",
            "alto",
            "",
        ),
        (
            "Input",
            "Alocações de bolsas (SigPesq)",
            bolsas["n_alocacoes"],
            "alocações",
            "SigPesq",
            "disponível",
            "médio",
            "Inclui B-UnAC (ensino), não só pesquisa.",
        ),
        (
            "Input",
            "Valor alocado em bolsas (SigPesq)",
            bolsas["valor_alocado_total"],
            "R$",
            "SigPesq",
            "parcial",
            "médio",
            "valor_pago_total=0 em toda a base (só alocado).",
        ),
        (
            "Input",
            "Projetos FACTO geridos pela fundação (toda a rede)",
            facto["n_proj"],
            "projetos",
            "FACTO",
            "contexto",
            "alto",
            f"{facto.get('n_com_info')} com ficha; maioria de outros campi/coordenadores.",
        ),
        (
            "Input",
            "FACTO pesquisa coordenada por docente do CAMPUS (saldo)",
            facto.get("n_pesquisa"),
            "projetos",
            "FACTO",
            "disponível",
            "alto",
            f"Só coord∈roster; {facto.get('n_pesquisa_total_rede')} na rede toda (contexto).",
        ),
        (
            "Input",
            "FACTO — valor aprovado (saldo do campus)",
            facto.get("aprovado_pesquisa"),
            "R$",
            "FACTO",
            "disponível",
            "alto",
            "Só projetos coordenados por docente do campus; equipe não soma.",
        ),
        (
            "Econômico",
            "FACTO — valor EXECUTADO (saldo do campus)",
            facto.get("executado_pesquisa"),
            "R$",
            "FACTO",
            "disponível",
            "médio",
            "Execução real por rubrica; só coord∈roster.",
        ),
        (
            "Input",
            "Projetos de pesquisa declarados (Lattes)",
            prod["projetos_pesquisa_lattes"],
            "projetos",
            "Lattes",
            "disponível",
            "médio",
            "Autodeclarado; sem valor financeiro.",
        ),
        (
            "Científico",
            "Artigos em periódicos (roster, dedup)",
            prod["artigos"],
            "artigos",
            "Lattes",
            "disponível",
            "alto",
            "Dedup por título dentro do docente.",
        ),
        (
            "Científico",
            "Livros publicados",
            prod["livros"],
            "livros",
            "Lattes",
            "disponível",
            "alto",
            "",
        ),
        (
            "Científico",
            "Capítulos de livros",
            prod["capitulos"],
            "capítulos",
            "Lattes",
            "disponível",
            "alto",
            "",
        ),
        (
            "Científico",
            "Trabalhos completos em congressos",
            prod["congressos"],
            "trabalhos",
            "Lattes",
            "disponível",
            "alto",
            "",
        ),
        (
            "Científico",
            "Citações (OpenAlex, por DOI)",
            oa.get("citacoes_total"),
            "citações",
            "OpenAlex",
            "parcial",
            "médio",
            f"Só {oa.get('n_com_openalex')}/93 docentes casados por DOI.",
        ),
        (
            "Científico",
            "FWCI mediano",
            oa.get("fwci_mediano"),
            "índice",
            "OpenAlex",
            "parcial",
            "médio",
            "Normalizado por área/ano; cobertura parcial.",
        ),
        (
            "Científico",
            "Artigos no top 10% mundial",
            oa.get("top10_total"),
            "artigos",
            "OpenAlex",
            "parcial",
            "médio",
            "",
        ),
        (
            "Científico",
            "Produção científica por R$ 1 mi (fomento pesquisa consolidado)",
            per_milhao(prod_cient),
            "produtos/R$mi",
            "Lattes+FAPES",
            "parcial",
            "baixo",
            "Atribuição institucional bruta; produção NÃO ligada a projeto específico.",
        ),
        (
            "Formação",
            "Orientações de mestrado concluídas",
            prod["orient_mestrado_conc"],
            "orientações",
            "Lattes",
            "disponível",
            "alto",
            "",
        ),
        (
            "Formação",
            "Orientações de doutorado/pós-doc concluídas",
            prod["orient_doutorado_conc"],
            "orientações",
            "Lattes",
            "disponível",
            "alto",
            "Tipo: Tese.",
        ),
        (
            "Formação",
            "Orientações de especialização (lato sensu)",
            prod["orient_especializacao_conc"],
            "orientações",
            "Lattes",
            "disponível",
            "alto",
            "Tipo: Monografia.",
        ),
        (
            "Formação",
            "Orientações de GRADUAÇÃO (TCC + IC) concluídas",
            prod["orient_graduacao_conc"],
            "orientações",
            "Lattes",
            "disponível",
            "alto",
            "TCC + iniciação científica; NÃO confundir com mestrado.",
        ),
        (
            "Formação",
            "Orientações 'outros' concluídas",
            prod["orient_outros_conc"],
            "orientações",
            "Lattes",
            "disponível",
            "médio",
            "Categoria residual do Lattes.",
        ),
        (
            "Formação",
            "Discentes PPComp (mestrado)",
            ppcomp.get("n_discentes"),
            "discentes",
            "Base PPComp",
            "disponível",
            "alto",
            "",
        ),
        (
            "Formação",
            "Defesas PPComp",
            ppcomp.get("defendidos"),
            "defesas",
            "Base PPComp",
            "disponível",
            "alto",
            "",
        ),
        (
            "Formação",
            "Titulados (M+D) por R$ 1 mi (fomento pesquisa consolidado)",
            per_milhao(titulados),
            "titulados/R$mi",
            "Lattes+FAPES",
            "parcial",
            "baixo",
            "Atribuição bruta.",
        ),
        (
            "Inovação",
            "Patentes (Lattes)",
            prod["patentes"],
            "patentes",
            "Lattes",
            "disponível",
            "médio",
            "Autodeclarado; sem status INPI.",
        ),
        (
            "Inovação",
            "Softwares",
            prod["softwares"],
            "softwares",
            "Lattes",
            "disponível",
            "médio",
            "",
        ),
        (
            "Inovação",
            "Produtos tecnológicos",
            prod["produtos_tec"],
            "produtos",
            "Lattes",
            "disponível",
            "médio",
            "",
        ),
        (
            "Inovação",
            "Registros (programas/desenhos)",
            prod["registros"],
            "registros",
            "Lattes",
            "disponível",
            "médio",
            "",
        ),
        (
            "Inovação",
            "Ativos tecnológicos por R$ 1 mi (fomento pesquisa consolidado)",
            per_milhao(ativos_tec),
            "ativos/R$mi",
            "Lattes+FAPES",
            "parcial",
            "baixo",
            "Atribuição bruta.",
        ),
        (
            "Institucional",
            "Prêmios e títulos",
            prod["premios"],
            "prêmios",
            "Lattes",
            "disponível",
            "médio",
            "",
        ),
        (
            "Institucional",
            "Gini do orçamento FAPES (coordenadores)",
            gini_fapes,
            "0–1",
            "FAPES",
            "disponível",
            "alto",
            "Concentração de fomento entre coordenadores.",
        ),
        (
            "Institucional",
            "Concentração top-5 coordenadores (% do orçamento)",
            top5_share,
            "%",
            "FAPES",
            "disponível",
            "alto",
            "",
        ),
        (
            "Econômico",
            "Alavancagem (externo/institucional)",
            None,
            "razão",
            "—",
            "ausente",
            "baixo",
            "Sem valor de contrapartida institucional registrado.",
        ),
        (
            "Econômico",
            "ROI financeiro (%)",
            None,
            "%",
            "—",
            "ausente",
            "baixo",
            "Sem benefícios monetizados (royalties/licenças/contratos).",
        ),
        (
            "Social",
            "Impacto em políticas/sociedade",
            None,
            "—",
            "—",
            "ausente",
            "baixo",
            "Não há dado estruturado; exige narrativa/estudo de caso.",
        ),
    ]

    # valor sanitizado p/ exibição: R$ -> ordem de grandeza; demais unidades inalteradas
    def _val_pub(v, unidade):
        if v is None:
            return ""
        return ordem(v) if unidade == "R$" else v

    # ---- CSV principal (R$ vira ordem de grandeza) ----
    with (OUT / "metricas_roi_pesquisa.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "dimensao",
                "indicador",
                "valor",
                "unidade",
                "fonte",
                "disponibilidade",
                "nivel_confianca",
                "observacao",
            ]
        )
        for row in metricas:
            w.writerow(
                [
                    row[0],
                    row[1],
                    _val_pub(row[2], row[3]),
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                ]
            )

    # ---- CSV por coordenador (fomento em FAIXA + %; sem R$ concreto) ----
    prod_doc = {norm(k): v for k, v in prod["por_doc"].items() if v}
    coords = set(fapes["por_coord"]) | set(bolsas["por_coord"])
    with (OUT / "por_coordenador.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "coordenador_norm",
                "fapes_faixa",
                "fapes_pct",
                "fapes_n_proj",
                "bolsas_faixa",
                "bolsas_n",
                "artigos",
                "orient_m",
                "orient_d",
                "citacoes_oa",
                "fwci",
                "top10",
            ]
        )
        for c in sorted(coords):
            fp = fapes["por_coord"].get(c, {})
            bo = bolsas["por_coord"].get(c, {})
            pd = prod_doc.get(c, {})
            od = oa_doc.get(c, {})
            w.writerow(
                [
                    c,
                    faixa(fp.get("orcamento", 0)),
                    pct(fp.get("orcamento", 0), inv_fapes),
                    fp.get("n_proj", 0),
                    faixa(bo.get("valor", 0)),
                    bo.get("n", 0),
                    pd.get("artigos", ""),
                    pd.get("orient_mestrado", ""),
                    pd.get("orient_doutorado", ""),
                    od.get("cit", ""),
                    od.get("fwci", ""),
                    od.get("top10", ""),
                ]
            )

    # FACTO: CSV por projeto. conta_saldo = pesquisa E coordenador∈roster (campus Serra).
    # % é sobre o SALDO do campus (só projetos que contam).
    facto_rows = facto.pop("_rows", [])
    ap_saldo = facto.get("aprovado_pesquisa") or 0
    with (OUT / "facto_projetos.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "referencia",
                "coordenador",
                "coord_roster",
                "financiadora",
                "tipo",
                "ano",
                "aprovado_faixa",
                "executado_faixa",
                "conta_saldo_campus",
                "saldo_pct",
            ],
        )
        w.writeheader()
        for r in facto_rows:
            w.writerow(
                {
                    "referencia": r["referencia"],
                    "coordenador": r["coordenador"],
                    "coord_roster": r["coord_roster"],
                    "financiadora": r["financiadora"],
                    "tipo": r["tipo"],
                    "ano": r["ano"],
                    "aprovado_faixa": faixa(r["aprovado"]),
                    "executado_faixa": faixa(r["executado"]),
                    "conta_saldo_campus": r["conta_saldo"],
                    "saldo_pct": (
                        pct(r["aprovado"], ap_saldo) if r["conta_saldo"] else ""
                    ),
                }
            )

    # ---- payload sanitizado (totais em ordem; granular em faixa + %) ----
    fapes_pub = {k: v for k, v in fapes.items() if k not in ("por_coord", "por_ano")}
    fapes_pub["orcamento_total"] = ordem(fapes["orcamento_total"])
    fapes_pub["valor_bolsas_total"] = ordem(fapes["valor_bolsas_total"])
    fapes_pub["por_ano_faixa"] = {str(k): faixa(v) for k, v in fapes["por_ano"].items()}

    facto_pub = {
        k: v
        for k, v in facto.items()
        if k not in ("por_coord", "por_ano", "por_financiadora")
    }
    for k in (
        "aprovado_pesquisa",
        "executado_pesquisa",
        "aprovado_pesquisa_total_rede",
    ):
        if facto_pub.get(k) is not None:
            facto_pub[k] = ordem(facto[k])
    facto_pub["por_financiadora_faixa"] = {
        fin: {
            "n": d["n"],
            "faixa": faixa(d["aprovado"]),
            "pct": pct(d["aprovado"], ap_saldo),
        }
        for fin, d in facto.get("por_financiadora", {}).items()
    }

    bolsas_pub = {k: v for k, v in bolsas.items() if k != "por_coord"}
    bolsas_pub["valor_alocado_total"] = ordem(bolsas["valor_alocado_total"])
    bolsas_pub["valor_pago_total"] = ordem(bolsas["valor_pago_total"])

    top_coord_pub = [
        {
            "coord": k,
            "faixa": faixa(v["orcamento"]),
            "pct": pct(v["orcamento"], inv_fapes),
            "n_proj": v["n_proj"],
            "anos": sorted(v["anos"]),
        }
        for k, v in top5_coord
    ]
    cand_pub = [
        {
            **c,
            "orcamento": None,
            "faixa": faixa(c["orcamento"]),
            "pct": pct(c["orcamento"], inv_fapes),
        }
        for c in cand
    ]

    payload = {
        "_nota_seguranca": "Valores financeiros não são expostos em cifra exata: totais em "
        "ordem de grandeza; granular em faixa + % do total.",
        "fapes": fapes_pub,
        "fapes_top_coord": top_coord_pub,
        "facto": facto_pub,
        "bolsas": bolsas_pub,
        "producao": {k: v for k, v in prod.items() if k != "por_doc"},
        "openalex": {k: v for k, v in oa.items() if k != "por_doc"},
        "ppcomp": ppcomp,
        "derivados": {
            "fomento_pesquisa_consolidado_ordem": ordem(fomento_pesquisa),
            "fapes_contratado_ordem": ordem(inv_fapes),
            "facto_pesquisa_aprovado_ordem": ordem(facto.get("aprovado_pesquisa")),
            "facto_pesquisa_executado_ordem": ordem(facto.get("executado_pesquisa")),
            "producao_cientifica_total": prod_cient,
            "titulados_md": titulados,
            "ativos_tecnologicos": ativos_tec,
            "prod_cient_por_milhao": per_milhao(prod_cient),
            "titulados_por_milhao": per_milhao(titulados),
            "ativos_tec_por_milhao": per_milhao(ativos_tec),
            "gini_fapes": gini_fapes,
            "top5_coord_share_pct": top5_share,
        },
        "candidatos_caso": cand_pub,
        "metricas": [
            {
                "dimensao": r[0],
                "indicador": r[1],
                "valor": _val_pub(r[2], r[3]),
                "unidade": r[3],
                "fonte": r[4],
                "disponibilidade": r[5],
                "confianca": r[6],
                "obs": r[7],
            }
            for r in metricas
        ],
    }
    (OUT / "roi_intermediate.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        "OK — output/metricas_roi_pesquisa.csv, por_coordenador.csv, facto_projetos.csv, roi_intermediate.json"
    )
    print(
        f"FAPES: {fapes['n_proj']} proj · {ordem(inv_fapes)} · Gini={gini_fapes} · top5={top5_share}%"
    )
    print(
        f"FACTO pesquisa: {facto.get('n_pesquisa')} proj · aprovado {ordem(facto.get('aprovado_pesquisa'))} "
        f"· executado {ordem(facto.get('executado_pesquisa'))}"
    )
    print(f"Fomento pesquisa consolidado: {ordem(fomento_pesquisa)}")
    print(
        f"Produção: {prod_cient} itens científicos · {titulados} titulados M+D · {ativos_tec} ativos tec"
    )
    print(
        f"OpenAlex: {oa.get('citacoes_total')} citações ({oa.get('n_com_openalex')}/93)"
    )


if __name__ == "__main__":
    main()
