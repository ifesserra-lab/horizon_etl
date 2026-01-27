from typing import Any, Dict, List

import pandas as pd
from loguru import logger

from .base import ProjectMappingStrategy


class SigPesqAdvisorshipMappingStrategy(ProjectMappingStrategy):
    """
    Strategy for mapping SigPesq Advisorship (Bolsistas) Excel data to canonical domain models.
    """

    def map_row(self, row: dict) -> Dict[str, Any]:
        """
        Maps a Single SigPesq Advisorship Excel row to a standardized dictionary.
        Returns data compatible with ProjectLoader, using research_domain entities.
        """
        from research_domain.domain.entities import Advisorship

        # Student Mapping
        bolsista = str(row.get("Orientado", "")).strip()
        bolsista_email = str(row.get("OrientadoEmail", "")).strip()

        # Supervisor Mapping
        orientador = str(row.get("Orientador", "")).strip()
        orientador_email = str(row.get("OrientadorEmail", "")).strip()

        # Project Mapping
        project_title = str(row.get("TituloPT", "N/A")).strip()
        row_id = row.get("Id", "")

        if not bolsista and not bolsista_email:
            return {}

        start_date = self._parse_date(row.get("Inicio"))
        end_date = self._parse_date(row.get("Fim"))

        # Fellowship/Flowship data
        programa = row.get("Programa")
        valor = row.get("Valor", 0.0)

        fellowship_data = None
        if programa:
            # Handle Portuguese decimal separator (comma)
            processed_valor = 0.0
            if valor:
                try:
                    if isinstance(valor, str):
                        processed_valor = float(valor.replace(".", "").replace(",", "."))
                    else:
                        processed_valor = float(valor)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert value '{valor}' to float. Using 0.0")
                    processed_valor = 0.0

            fellowship_data = {
                "name": str(programa).strip(),
                "value": processed_valor,
                "description": f"Programa: {programa}",
                "sigpesq_id": row_id,
            }

        return {
            "title": project_title,
            "status": row.get("Situacao", row.get("Situação", "Active")),
            "start_date": start_date,
            "end_date": end_date,
            "description": f"Programa: {programa or 'N/A'}",
            "coordinator_name": orientador,
            "coordinator_email": orientador_email,
            "student_names": [bolsista] if bolsista else [],
            "student_emails": [bolsista_email] if bolsista_email else [],
            "researcher_names": [],
            "model_class": Advisorship,
            "fellowship_data": fellowship_data,
            "metadata": {
                "bolsista_name": bolsista,
                "bolsista_email": bolsista_email,
                "orientador_name": orientador,
                "orientador_email": orientador_email,
                "project_title": project_title,
                "programa": programa,
                "valor": valor,
                "sigpesq_id": row_id,
            },
            "campus_name": row.get("CampusExecucao", row.get("Campus")),
        }

    def _parse_names(self, names_str: Any) -> List[str]:
        if not names_str or pd.isna(names_str):
            return []
        return [name.strip() for name in str(names_str).split(";") if name.strip()]

    def _parse_date(self, date_val: Any):
        if pd.isna(date_val) or not date_val:
            return None

        from datetime import datetime

        if isinstance(date_val, datetime):
            return date_val

        str_val = str(date_val).strip()
        formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"]

        for fmt in formats:
            try:
                return datetime.strptime(str_val, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {str_val}")
        return None
