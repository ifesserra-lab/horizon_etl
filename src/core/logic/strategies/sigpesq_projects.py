from typing import Any, Dict, List

import pandas as pd
from loguru import logger

from .base import ProjectMappingStrategy


class SigPesqProjectMappingStrategy(ProjectMappingStrategy):
    """
    Strategy for mapping SigPesq Project Excel data to canonical domain models.

    This strategy handles the specific column names and formats found in the SigPesq
    research project exports, including multi-value name parsing and date handling.
    """

    def map_row(self, row: dict) -> Dict[str, Any]:
        """
        Maps a Single SigPesq Excel row to a standardized dictionary of initiative attributes.

        Args:
            row (dict): A dictionary representing a row from the Excel file.

        Returns:
            Dict[str, Any]: Standardized project data with keys like 'title', 'coordinator_name', etc.
        """
        return {
            "title": row.get("Titulo", row.get("Título")),
            "status": row.get("Situacao", row.get("Situação")),
            "start_date": self._parse_date(row.get("Inicio")),
            "end_date": self._parse_date(row.get("Fim")),
            "description": row.get("Resumo"),
            "value": row.get("Valor Aprovado"),
            "coordinator_name": row.get("Coordenador"),
            "researcher_names": self._parse_names(row.get("Pesquisadores")),
            "student_names": self._parse_names(row.get("Estudantes")),
        }

    def _parse_names(self, names_str: Any) -> List[str]:
        """
        Parses a semicolon-separated string of names into a trimmed list.

        Args:
            names_str (Any): The input string or NaN value.

        Returns:
            List[str]: A list of non-empty name strings.
        """
        if not names_str or pd.isna(names_str):
            return []
        return [name.strip() for name in str(names_str).split(";") if name.strip()]

    def _parse_date(self, date_val: Any):
        """
        Attempts to parse a date from various types and string formats.

        Args:
            date_val (Any): Input date value (datetime, string, or NaN).

        Returns:
            Optional[datetime]: The parsed datetime object, or None if parsing fails.
        """
        if pd.isna(date_val) or not date_val:
            return None

        from datetime import datetime

        # If already datetime
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
