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
FAPES = ROOT / "data" / "exports" / "projetos-fapes" / "ifes-campus-serra-projetos-concluidos-em-andamento.json"
FACTO = ROOT / "data" / "exports" / "projetos-facto" / "facto_projects_full.json"
BOLSAS = ROOT / "data" / "exports" / "bolsistas" / "ifes-campus-serra-bolsistas.json"
OPENALEX = ROOT / "data" / "exports" / "docentes" / "openalex_citacoes.json"
PPCOMP = ROOT / "data" / "mestrado" / "base_de_dados_ppcomp.json"
OUT = ROOT / "output"


# ---------------------------------------------------------------------------
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
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
    qual = "centenas de milhões" if mi >= 100 else ("dezenas de milhões" if mi >= 10 else "milhões")
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
    grupos = ["concluidos", "em_andamento", "status_em_andamento_prazo_encerrado",
              "status_em_andamento_prazo_futuro", "status_em_andamento_sem_prazo_valido"]
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
    por_coord = defaultdict(lambda: {"orcamento": 0.0, "valor_bolsas": 0.0, "n_proj": 0,
                                     "n_bolsas": 0, "anos": set()})
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
        "n_proj": len(proj), "n_concluidos": n_conc, "n_andamento": n_and,
        "orcamento_total": round(orc_total, 2), "valor_bolsas_total": round(bolsa_total, 2),
        "quantidade_bolsas_total": int(nb_total),
        "por_ano": {k: round(v, 2) for k, v in sorted(por_ano.items())},
        "por_coord": {k: {**v, "anos": sorted(v["anos"])} for k, v in por_coord.items()},
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
    "Pesquisa, Desenvolvimento e Inovação", "Pesquisa", "Inovação",
    "Pesquisa e Extensão", "Pesquisa e Ensino", "Pesquisa, Ensino e Extensão",
}


def carregar_facto() -> dict:
    """FACTO (fundação de apoio). Cada projeto traz 7 CSVs aninhados; usamos
    'Informações do projeto' (valor aprovado, financiadora, tipo, coordenador) e
    'Recursos por rubrica' (Executado por despesa). Separa PESQUISA de não-pesquisa."""
    if not FACTO.exists():
        return {"n_proj": 0, "valor_aprovado_total": None}
    projs = json.loads(FACTO.read_text(encoding="utf-8")).get("projects", [])
    n_err = sum(1 for p in projs if p.get("_error"))
    por_fin = defaultdict(lambda: {"n": 0, "aprovado": 0.0})
    por_coord = defaultdict(lambda: {"aprovado": 0.0, "executado": 0.0, "n": 0})
    por_ano = defaultdict(float)
    rows = []
    n_info = 0
    ap_total = ap_pesq = ex_pesq = ap_outros = 0.0
    n_pesq = n_outros = 0
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
        ini = (r.get("Data de início") or "")
        ano = None
        m = re.search(r"(\d{4})", ini[-4:] if len(ini) >= 4 else ini)
        if m:
            ano = int(m.group(1))
        is_pesq = tipo in FACTO_TIPOS_PESQUISA
        # executado (despesas, valor absoluto) — só p/ subset pesquisa (custo de parsing)
        ex = 0.0
        if is_pesq:
            rec = next((v for k, v in csv.items() if "rubrica" in k.lower()), None)
            if isinstance(rec, list):
                for row in rec:
                    if "despesa" in (row.get("Tipo da Rubrica") or "").lower():
                        ex += abs(_br(row.get("Executado")))
        ap_total += ap
        if is_pesq:
            n_pesq += 1; ap_pesq += ap; ex_pesq += ex
            if fin:
                por_fin[fin[:45]]["n"] += 1
                por_fin[fin[:45]]["aprovado"] += ap
            if coord:
                pc = por_coord[norm(coord)]
                pc["aprovado"] += ap; pc["executado"] += ex; pc["n"] += 1
            if ano:
                por_ano[ano] += ap
        else:
            n_outros += 1; ap_outros += ap
        rows.append({"referencia": (r.get("Referência do projeto") or "")[:60],
                     "coordenador": coord, "financiadora": fin, "tipo": tipo,
                     "ano": ano, "aprovado": round(ap, 2), "executado": round(ex, 2),
                     "pesquisa": is_pesq})
    return {
        "n_proj": len(projs), "n_com_info": n_info, "n_erros_scrape": n_err,
        "valor_aprovado_total": round(ap_total, 2),
        "n_pesquisa": n_pesq, "aprovado_pesquisa": round(ap_pesq, 2),
        "executado_pesquisa": round(ex_pesq, 2),
        "n_outros": n_outros, "aprovado_outros": round(ap_outros, 2),
        "por_financiadora": {k: {"n": v["n"], "aprovado": round(v["aprovado"], 2)}
                             for k, v in sorted(por_fin.items(), key=lambda kv: -kv[1]["aprovado"])},
        "por_ano": {k: round(v, 2) for k, v in sorted(por_ano.items())},
        "por_coord": {k: {"aprovado": round(v["aprovado"], 2),
                          "executado": round(v["executado"], 2), "n": v["n"]}
                      for k, v in por_coord.items()},
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
        "n_alocacoes": len(al), "n_bolsistas_unicos": len(d.get("bolsistas_unicos", [])),
        "valor_alocado_total": round(v_alocado, 2), "valor_pago_total": round(v_pago, 2),
        "por_tipo": dict(por_tipo.most_common()),
        "por_ano": {k: round(v, 2) for k, v in sorted(por_ano.items())},
        "por_coord": {k: {"valor": round(v["valor"], 2), "n": v["n"]} for k, v in por_coord.items()},
        "n_coordenadores": len(por_coord),
    }


# ---------------------------------------------------------------------------
def _dedup_titulos(items, key="titulo"):
    seen, n = set(), 0
    for a in items or []:
        t = norm(a.get(key, "")) if isinstance(a, dict) else ""
        if t and t in seen:
            continue
        if t:
            seen.add(t)
        n += 1
    return n


def carregar_producao_roster() -> dict:
    by_id = lattes_index()
    art = liv = cap = cong = 0
    # orientações CONCLUÍDAS por nível (chaves reais do Lattes: mestrado, doutorado,
    # pos_doutorado, especializacao, tcc, iniciacao_cientifica, outros)
    orient_m = orient_d = orient_espec = orient_grad = orient_outros = 0
    orient_m_and = orient_d_and = 0      # em andamento
    pat = soft = prod_tec = registros = 0
    premios = 0
    proj_pesq = 0
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
        a = _dedup_titulos(pb.get("artigos_periodicos"))
        l = _dedup_titulos(pb.get("livros_publicados"))
        c = _dedup_titulos(pb.get("capitulos_livros"))
        cg = _dedup_titulos(pb.get("trabalhos_completos_congressos"))
        art += a; liv += l; cap += c; cong += cg
        # orientações
        o = cv.get("orientacoes", {}) or {}
        conc = o.get("concluidas", {}) or {}
        anda = o.get("em_andamento", {}) or {}
        om = len(conc.get("mestrado") or [])            # tipo: Dissertação
        od = len(conc.get("doutorado") or []) + len(conc.get("pos_doutorado") or [])  # Tese
        oesp = len(conc.get("especializacao") or [])    # lato sensu (Monografia)
        # GRADUAÇÃO = TCC + iniciação científica (ambos tipo "Trab. de Conclusão de Curso")
        ograd = len(conc.get("tcc") or []) + len(conc.get("iniciacao_cientifica") or [])
        ooutros = len(conc.get("outros") or [])
        orient_m += om; orient_d += od
        orient_espec += oesp; orient_grad += ograd; orient_outros += ooutros
        orient_m_and += len(anda.get("mestrado") or [])
        orient_d_and += len(anda.get("doutorado") or []) + len(anda.get("pos_doutorado") or [])
        # técnica / PI
        pr = cv.get("patentes_registros", {}) or {}
        npat = len(pr.get("patentes") or [])
        nreg = len(pr.get("programas_computador") or []) + len(pr.get("desenhos_industriais") or [])
        pt = cv.get("producao_tecnica", {}) or {}
        nsoft = len(pt.get("softwares_com_patente") or []) + len(pt.get("softwares_sem_patente") or [])
        nprodt = len(pt.get("produtos_tecnologicos") or [])
        pat += npat; soft += nsoft; prod_tec += nprodt; registros += nreg
        premios += len(cv.get("premios_titulos") or [])
        proj_pesq += len(cv.get("projetos_pesquisa") or [])
        por_doc[nome] = {
            "artigos": a, "livros": l, "capitulos": c, "congressos": cg,
            "orient_mestrado": om, "orient_doutorado": od,
            "orient_especializacao": oesp, "orient_graduacao": ograd, "orient_outros": ooutros,
            "patentes": npat, "softwares": nsoft, "produtos_tec": nprodt, "registros": nreg,
            "premios": len(cv.get("premios_titulos") or []),
            "projetos_pesquisa": len(cv.get("projetos_pesquisa") or []),
        }
    return {
        "n_roster": len(ROSTER_IDS), "n_lattes_encontrados": n_match,
        "artigos": art, "livros": liv, "capitulos": cap, "congressos": cong,
        "orient_mestrado_conc": orient_m, "orient_doutorado_conc": orient_d,
        "orient_especializacao_conc": orient_espec,
        "orient_graduacao_conc": orient_grad, "orient_outros_conc": orient_outros,
        "orient_mestrado_and": orient_m_and, "orient_doutorado_and": orient_d_and,
        "patentes": pat, "softwares": soft, "produtos_tec": prod_tec, "registros": registros,
        "premios": premios, "projetos_pesquisa_lattes": proj_pesq,
        "por_doc": por_doc,
    }


def carregar_openalex() -> dict:
    if not OPENALEX.exists():
        return {}
    d = json.loads(OPENALEX.read_text(encoding="utf-8"))["docentes"]
    com = [x for x in d if x.get("encontrados_openalex", 0) > 0]
    cits = sum(x.get("citacoes_total", 0) for x in com)
    fwcis = sorted(x.get("fwci_medio", 0) or 0 for x in com if (x.get("fwci_medio") or 0) > 0)
    top10 = sum(x.get("artigos_top10pct", 0) for x in com)
    por_doc = {x["nome"]: {"cit": x.get("citacoes_total", 0), "h": x.get("h_index", 0),
                           "fwci": round(x.get("fwci_medio", 0) or 0, 2),
                           "top10": x.get("artigos_top10pct", 0),
                           "artigos_oa": x.get("encontrados_openalex", 0)}
               for x in com}
    return {
        "n_com_openalex": len(com), "citacoes_total": cits, "top10_total": top10,
        "fwci_mediano": fwcis[len(fwcis) // 2] if fwcis else 0,
        "por_doc": por_doc,
    }


def carregar_ppcomp() -> dict:
    if not PPCOMP.exists():
        return {}
    d = json.loads(PPCOMP.read_text(encoding="utf-8"))
    recs = d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])
    sit = Counter((x.get("situacao") or "—") for x in recs)
    defend = sum(1 for x in recs if "defend" in (x.get("situacao") or "").lower()
                 or (x.get("data_defesa") and "1905" not in str(x.get("data_defesa"))))
    return {"n_discentes": len(recs), "defendidos": sit.get("Defendido", defend),
            "situacao": dict(sit.most_common())}


# ---------------------------------------------------------------------------
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fapes = carregar_fapes()
    facto = carregar_facto()
    bolsas = carregar_bolsas()
    prod = carregar_producao_roster()
    oa = carregar_openalex()
    ppcomp = carregar_ppcomp()

    inv_fapes = fapes["orcamento_total"]  # FAPES contratado
    # fomento de pesquisa CONSOLIDADO (FAPES contratado + FACTO pesquisa aprovado) =
    # denominador das razões de produtividade (mais completo que só FAPES)
    fomento_pesquisa = round(inv_fapes + (facto.get("aprovado_pesquisa") or 0), 2)
    # produção científica total (peer-review: artigos + livros + capítulos + congressos)
    prod_cient = prod["artigos"] + prod["livros"] + prod["capitulos"] + prod["congressos"]
    titulados = prod["orient_mestrado_conc"] + prod["orient_doutorado_conc"]
    ativos_tec = prod["patentes"] + prod["softwares"] + prod["produtos_tec"] + prod["registros"]

    # razões institucionais (com forte ressalva de atribuição — ver relatório)
    def per_milhao(n):
        return round(n / (fomento_pesquisa / 1_000_000), 2) if fomento_pesquisa else None

    # concentração do fomento (Gini) entre coordenadores FAPES
    coord_vals = [v["orcamento"] for v in fapes["por_coord"].values()]
    gini_fapes = gini(coord_vals)
    top5_coord = sorted(fapes["por_coord"].items(), key=lambda kv: -kv[1]["orcamento"])[:5]
    top5_share = (round(sum(v["orcamento"] for _, v in top5_coord) / inv_fapes * 100, 1)
                  if inv_fapes else None)

    # candidatos a estudo de caso REF: projetos FAPES de maior orçamento + coordenadores
    # de alto impacto (FWCI/citações) — interseção fomento × impacto
    cand = []
    oa_doc = {norm(k): v for k, v in (oa.get("por_doc") or {}).items()}
    for c, v in sorted(fapes["por_coord"].items(), key=lambda kv: -kv[1]["orcamento"])[:12]:
        impacto = oa_doc.get(c, {})
        cand.append({
            "coordenador_norm": c,
            "orcamento": round(v["orcamento"], 2), "n_proj": v["n_proj"],
            "anos": v["anos"],
            "citacoes": impacto.get("cit"), "fwci": impacto.get("fwci"),
            "top10": impacto.get("top10"), "h": impacto.get("h"),
        })

    metricas = [
        # (dimensao, indicador, valor, unidade, fonte, disponib, confianca, obs)
        ("Input", "Projetos FAPES (concluídos + andamento)", fapes["n_proj"], "projetos",
         "FAPES", "disponível", "alto", "Universo dedup por projeto_id; 3 listas disjuntas."),
        ("Input", "Orçamento FAPES contratado (total)", inv_fapes, "R$",
         "FAPES", "disponível", "alto", "Contratado, não necessariamente executado."),
        ("Input", "Valor de bolsas em projetos FAPES", fapes["valor_bolsas_total"], "R$",
         "FAPES", "disponível", "alto", "Subconjunto do orçamento; não somar com base de bolsas."),
        ("Input", "Bolsas FAPES (quantidade)", fapes["quantidade_bolsas_total"], "bolsas",
         "FAPES", "disponível", "alto", ""),
        ("Input", "Alocações de bolsas (SigPesq)", bolsas["n_alocacoes"], "alocações",
         "Bolsas/SigPesq", "disponível", "médio", "Inclui B-UnAC (ensino), não só pesquisa."),
        ("Input", "Valor alocado em bolsas (SigPesq)", bolsas["valor_alocado_total"], "R$",
         "Bolsas/SigPesq", "parcial", "médio", "valor_pago_total=0 em toda a base (só alocado)."),
        ("Input", "Projetos FACTO (total geridos pela fundação)", facto["n_proj"], "projetos",
         "FACTO", "disponível", "alto", f"{facto.get('n_com_info')} com ficha; inclui ensino/extensão/seletivo."),
        ("Input", "Projetos FACTO de PESQUISA/PD&I/Inovação", facto.get("n_pesquisa"), "projetos",
         "FACTO", "disponível", "alto", "Filtrado por Tipo de Projeto."),
        ("Input", "FACTO — valor aprovado (pesquisa)", facto.get("aprovado_pesquisa"), "R$",
         "FACTO", "disponível", "alto", "Só subset pesquisa; exclui ensino/extensão/seletivo."),
        ("Econômico", "FACTO — valor EXECUTADO (pesquisa)", facto.get("executado_pesquisa"), "R$",
         "FACTO", "disponível", "médio", "Soma de despesas executadas por rubrica; raro dado de execução real."),
        ("Input", "FACTO — valor aprovado (não-pesquisa)", facto.get("aprovado_outros"), "R$",
         "FACTO", "disponível", "alto", "Ensino/extensão/processo seletivo/concurso — fora do ROI de pesquisa."),
        ("Input", "Projetos de pesquisa declarados (Lattes)", prod["projetos_pesquisa_lattes"],
         "projetos", "Lattes", "disponível", "médio", "Autodeclarado; sem valor financeiro."),
        ("Científico", "Artigos em periódicos (roster, dedup)", prod["artigos"], "artigos",
         "Lattes", "disponível", "alto", "Dedup por título dentro do docente."),
        ("Científico", "Livros publicados", prod["livros"], "livros",
         "Lattes", "disponível", "alto", ""),
        ("Científico", "Capítulos de livros", prod["capitulos"], "capítulos",
         "Lattes", "disponível", "alto", ""),
        ("Científico", "Trabalhos completos em congressos", prod["congressos"], "trabalhos",
         "Lattes", "disponível", "alto", ""),
        ("Científico", "Citações (OpenAlex, por DOI)", oa.get("citacoes_total"), "citações",
         "OpenAlex", "parcial", "médio", f"Só {oa.get('n_com_openalex')}/93 docentes casados por DOI."),
        ("Científico", "FWCI mediano", oa.get("fwci_mediano"), "índice",
         "OpenAlex", "parcial", "médio", "Normalizado por área/ano; cobertura parcial."),
        ("Científico", "Artigos no top 10% mundial", oa.get("top10_total"), "artigos",
         "OpenAlex", "parcial", "médio", ""),
        ("Científico", "Produção científica por R$ 1 mi (fomento pesquisa consolidado)", per_milhao(prod_cient),
         "produtos/R$mi", "Lattes+FAPES", "parcial", "baixo",
         "Atribuição institucional bruta; produção NÃO ligada a projeto específico."),
        ("Formação", "Orientações de mestrado concluídas", prod["orient_mestrado_conc"],
         "orientações", "Lattes", "disponível", "alto", ""),
        ("Formação", "Orientações de doutorado/pós-doc concluídas", prod["orient_doutorado_conc"],
         "orientações", "Lattes", "disponível", "alto", "Tipo: Tese."),
        ("Formação", "Orientações de especialização (lato sensu)", prod["orient_especializacao_conc"],
         "orientações", "Lattes", "disponível", "alto", "Tipo: Monografia."),
        ("Formação", "Orientações de GRADUAÇÃO (TCC + IC) concluídas", prod["orient_graduacao_conc"],
         "orientações", "Lattes", "disponível", "alto", "TCC + iniciação científica; NÃO confundir com mestrado."),
        ("Formação", "Orientações 'outros' concluídas", prod["orient_outros_conc"],
         "orientações", "Lattes", "disponível", "médio", "Categoria residual do Lattes."),
        ("Formação", "Discentes PPComp (mestrado)", ppcomp.get("n_discentes"), "discentes",
         "Base PPComp", "disponível", "alto", ""),
        ("Formação", "Defesas PPComp", ppcomp.get("defendidos"), "defesas",
         "Base PPComp", "disponível", "alto", ""),
        ("Formação", "Titulados (M+D) por R$ 1 mi (fomento pesquisa consolidado)", per_milhao(titulados),
         "titulados/R$mi", "Lattes+FAPES", "parcial", "baixo", "Atribuição bruta."),
        ("Inovação", "Patentes (Lattes)", prod["patentes"], "patentes",
         "Lattes", "disponível", "médio", "Autodeclarado; sem status INPI."),
        ("Inovação", "Softwares", prod["softwares"], "softwares",
         "Lattes", "disponível", "médio", ""),
        ("Inovação", "Produtos tecnológicos", prod["produtos_tec"], "produtos",
         "Lattes", "disponível", "médio", ""),
        ("Inovação", "Registros (programas/desenhos)", prod["registros"], "registros",
         "Lattes", "disponível", "médio", ""),
        ("Inovação", "Ativos tecnológicos por R$ 1 mi (fomento pesquisa consolidado)", per_milhao(ativos_tec),
         "ativos/R$mi", "Lattes+FAPES", "parcial", "baixo", "Atribuição bruta."),
        ("Institucional", "Prêmios e títulos", prod["premios"], "prêmios",
         "Lattes", "disponível", "médio", ""),
        ("Institucional", "Gini do orçamento FAPES (coordenadores)", gini_fapes, "0–1",
         "FAPES", "disponível", "alto", "Concentração de fomento entre coordenadores."),
        ("Institucional", "Concentração top-5 coordenadores (% do orçamento)", top5_share, "%",
         "FAPES", "disponível", "alto", ""),
        ("Econômico", "Alavancagem (externo/institucional)", None, "razão",
         "—", "ausente", "baixo", "Sem valor de contrapartida institucional registrado."),
        ("Econômico", "ROI financeiro (%)", None, "%",
         "—", "ausente", "baixo", "Sem benefícios monetizados (royalties/licenças/contratos)."),
        ("Social", "Impacto em políticas/sociedade", None, "—",
         "—", "ausente", "baixo", "Não há dado estruturado; exige narrativa/estudo de caso."),
    ]

    # valor sanitizado p/ exibição: R$ -> ordem de grandeza; demais unidades inalteradas
    def _val_pub(v, unidade):
        if v is None:
            return ""
        return ordem(v) if unidade == "R$" else v

    # ---- CSV principal (R$ vira ordem de grandeza) ----
    with (OUT / "metricas_roi_pesquisa.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["dimensao", "indicador", "valor", "unidade", "fonte",
                    "disponibilidade", "nivel_confianca", "observacao"])
        for row in metricas:
            w.writerow([row[0], row[1], _val_pub(row[2], row[3]), row[3], row[4], row[5], row[6], row[7]])

    # ---- CSV por coordenador (fomento em FAIXA + %; sem R$ concreto) ----
    prod_doc = {norm(k): v for k, v in prod["por_doc"].items() if v}
    coords = set(fapes["por_coord"]) | set(bolsas["por_coord"])
    with (OUT / "por_coordenador.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["coordenador_norm", "fapes_faixa", "fapes_pct", "fapes_n_proj",
                    "bolsas_faixa", "bolsas_n", "artigos", "orient_m", "orient_d",
                    "citacoes_oa", "fwci", "top10"])
        for c in sorted(coords):
            fp = fapes["por_coord"].get(c, {})
            bo = bolsas["por_coord"].get(c, {})
            pd = prod_doc.get(c, {})
            od = oa_doc.get(c, {})
            w.writerow([c, faixa(fp.get("orcamento", 0)), pct(fp.get("orcamento", 0), inv_fapes),
                        fp.get("n_proj", 0), faixa(bo.get("valor", 0)), bo.get("n", 0),
                        pd.get("artigos", ""), pd.get("orient_mestrado", ""),
                        pd.get("orient_doutorado", ""), od.get("cit", ""),
                        od.get("fwci", ""), od.get("top10", "")])

    # FACTO: CSV por projeto (valores em FAIXA + % do total aprovado de pesquisa)
    facto_rows = facto.pop("_rows", [])
    ap_pesq_tot = facto.get("aprovado_pesquisa") or 0
    with (OUT / "facto_projetos.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["referencia", "coordenador", "financiadora",
                                           "tipo", "ano", "aprovado_faixa", "aprovado_pct",
                                           "executado_faixa", "pesquisa"])
        w.writeheader()
        for r in facto_rows:
            w.writerow({"referencia": r["referencia"], "coordenador": r["coordenador"],
                        "financiadora": r["financiadora"], "tipo": r["tipo"], "ano": r["ano"],
                        "aprovado_faixa": faixa(r["aprovado"]),
                        "aprovado_pct": (pct(r["aprovado"], ap_pesq_tot) if r["pesquisa"] else ""),
                        "executado_faixa": faixa(r["executado"]), "pesquisa": r["pesquisa"]})

    # ---- payload sanitizado (totais em ordem; granular em faixa + %) ----
    fapes_pub = {k: v for k, v in fapes.items() if k not in ("por_coord", "por_ano")}
    fapes_pub["orcamento_total"] = ordem(fapes["orcamento_total"])
    fapes_pub["valor_bolsas_total"] = ordem(fapes["valor_bolsas_total"])
    fapes_pub["por_ano_faixa"] = {str(k): faixa(v) for k, v in fapes["por_ano"].items()}

    facto_pub = {k: v for k, v in facto.items() if k not in ("por_coord", "por_ano", "por_financiadora")}
    for k in ("valor_aprovado_total", "aprovado_pesquisa", "executado_pesquisa", "aprovado_outros"):
        if facto_pub.get(k) is not None:
            facto_pub[k] = ordem(facto[k])
    facto_pub["por_financiadora_faixa"] = {
        fin: {"n": d["n"], "faixa": faixa(d["aprovado"]), "pct": pct(d["aprovado"], ap_pesq_tot)}
        for fin, d in facto.get("por_financiadora", {}).items()}

    bolsas_pub = {k: v for k, v in bolsas.items() if k != "por_coord"}
    bolsas_pub["valor_alocado_total"] = ordem(bolsas["valor_alocado_total"])
    bolsas_pub["valor_pago_total"] = ordem(bolsas["valor_pago_total"])

    top_coord_pub = [{"coord": k, "faixa": faixa(v["orcamento"]),
                      "pct": pct(v["orcamento"], inv_fapes), "n_proj": v["n_proj"],
                      "anos": sorted(v["anos"])} for k, v in top5_coord]
    cand_pub = [{**c, "orcamento": None, "faixa": faixa(c["orcamento"]),
                 "pct": pct(c["orcamento"], inv_fapes)} for c in cand]

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
            "producao_cientifica_total": prod_cient, "titulados_md": titulados,
            "ativos_tecnologicos": ativos_tec,
            "prod_cient_por_milhao": per_milhao(prod_cient),
            "titulados_por_milhao": per_milhao(titulados),
            "ativos_tec_por_milhao": per_milhao(ativos_tec),
            "gini_fapes": gini_fapes, "top5_coord_share_pct": top5_share,
        },
        "candidatos_caso": cand_pub,
        "metricas": [{"dimensao": r[0], "indicador": r[1], "valor": _val_pub(r[2], r[3]),
                      "unidade": r[3], "fonte": r[4], "disponibilidade": r[5],
                      "confianca": r[6], "obs": r[7]} for r in metricas],
    }
    (OUT / "roi_intermediate.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("OK — output/metricas_roi_pesquisa.csv, por_coordenador.csv, facto_projetos.csv, roi_intermediate.json")
    print(f"FAPES: {fapes['n_proj']} proj · {ordem(inv_fapes)} · Gini={gini_fapes} · top5={top5_share}%")
    print(f"FACTO pesquisa: {facto.get('n_pesquisa')} proj · aprovado {ordem(facto.get('aprovado_pesquisa'))} "
          f"· executado {ordem(facto.get('executado_pesquisa'))}")
    print(f"Fomento pesquisa consolidado: {ordem(fomento_pesquisa)}")
    print(f"Produção: {prod_cient} itens científicos · {titulados} titulados M+D · {ativos_tec} ativos tec")
    print(f"OpenAlex: {oa.get('citacoes_total')} citações ({oa.get('n_com_openalex')}/93)")


if __name__ == "__main__":
    main()
