import json
import re
import unicodedata

import pandas as pd
from loguru import logger


def normalize_name(name: str) -> str:
    if not name:
        return ""
    name_str = "".join(
        c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn"
    )
    name_str = re.sub(r"[^A-Z\s]", " ", name_str.upper())
    return " ".join(name_str.split())


def verify():
    excel_path = "/home/paulossjunior/projects/horizon_project/horizon_etl/data/raw/sigpesq/research_projects/Relatorio_15_01_2026.xlsx"
    json_path = "/home/paulossjunior/projects/horizon_project/horizon_etl/data/exports/initiatives_canonical.json"

    logger.info(f"Loading Excel: {excel_path}")
    df = pd.read_excel(excel_path).fillna("")

    logger.info(f"Loading JSON: {json_path}")
    with open(json_path, "r") as f:
        initiatives = json.load(f)

    json_by_name = {init["name"]: init for init in initiatives}

    errors = []
    total_projects = 0
    clean_projects = 0

    for _, row in df.iterrows():
        title = row["Titulo"]
        total_projects += 1

        if title not in json_by_name:
            logger.warning(f"Project not found in JSON: {title[:50]}...")
            continue

        # Extract members from Excel
        excel_members = set()
        coord = row["Coordenador"]
        if coord:
            excel_members.add(normalize_name(coord))

        researchers = row["Pesquisadores"]
        if researchers:
            for n in str(researchers).split(";"):
                if n.strip():
                    excel_members.add(normalize_name(n.strip()))

        students = row["Estudantes"]
        if students:
            for n in str(students).split(";"):
                if n.strip():
                    excel_members.add(normalize_name(n.strip()))

        # Extract members from JSON
        json_members = set()
        for member in json_by_name[title].get("team", []):
            json_members.add(normalize_name(member["person_name"]))

        # Compare
        extra_in_json = json_members - excel_members
        real_extras = []
        for jm in extra_in_json:
            found = False
            for em in excel_members:
                if jm == em:
                    found = True
                    break
            if not found:
                real_extras.append(jm)

        if real_extras:
            errors.append(
                {
                    "title": title,
                    "extra_members": real_extras,
                    "excel_count": len(excel_members),
                    "json_count": len(json_members),
                }
            )
        else:
            clean_projects += 1

    if errors:
        logger.error(f"Found {len(errors)} projects with extra members in JSON!")
        for err in errors:
            print(f"\nProject: {err['title']}")
            print(f"Extra members found: {err['extra_members']}")
            print(f"Counts: Excel={err['excel_count']}, JSON={err['json_count']}")
    else:
        logger.success(
            f"All {clean_projects}/{total_projects} projects verified as clean!"
        )


if __name__ == "__main__":
    verify()
