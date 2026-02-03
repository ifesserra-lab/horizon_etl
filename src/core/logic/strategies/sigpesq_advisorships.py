from datetime import datetime
from typing import Any, Dict

from research_domain.domain.entities import Advisorship

from .base import ProjectMappingStrategy


class SigPesqAdvisorshipMappingStrategy(ProjectMappingStrategy):
    """
    Strategy for mapping SigPesq Advisorship (Bolsistas) Excel data to canonical domain models.
    """

    def map_row(self, row: dict) -> Dict[str, Any]:
        """
        Maps a Single SigPesq Advisorship Excel row to a standardized dictionary.
        Returns data compatible with ProjectLoader.
        """
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

        # Determine status based on end_date
        status = "Active"
        if end_date and end_date < datetime.now():
            status = "Concluded"

        # Fellowship data
        programa = row.get("Programa")
        fellowship_data = None
        if programa:
            fellowship_data = {
                "name": str(programa).strip().upper(),
                "value": self.parse_currency(row.get("Valor")),
                "description": f"Programa: {programa}",
                "sigpesq_id": row_id,
                "sponsor_name": str(
                    row.get("AgFinanciadora", row.get("agFinanciadora", ""))
                ).strip(),
            }

        return {
            "title": project_title,
            "parent_title": str(row.get("TituloPJ", "")).strip(),
            "status": status,
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
                "sigpesq_id": row_id,
                "original_program": programa,
                "parent_project_title": str(row.get("TituloPJ", "")).strip(),
            },
            "campus_name": row.get("CampusExecucao", row.get("Campus")),
        }
