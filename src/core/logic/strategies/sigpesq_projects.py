from typing import Any, Dict, List
import pandas as pd
from loguru import logger
from .base import ProjectMappingStrategy


class SigPesqProjectMappingStrategy(ProjectMappingStrategy):
    """Strategy for mapping SigPesq Project Excel data."""

    def map_row(self, row: dict) -> Dict[str, Any]:
        """Maps SigPesq Excel columns to standardized keys for Project."""
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
        """Parse semicolon-separated names into a list."""
        if not names_str or pd.isna(names_str):
            return []
        return [name.strip() for name in str(names_str).split(";") if name.strip()]

    def _parse_date(self, date_val: Any):
        """Helper to parse dates from various formats."""
        if pd.isna(date_val) or not date_val:
            return None
        
        from datetime import datetime
        
        # If already datetime
        if isinstance(date_val, datetime):
            return date_val
            
        str_val = str(date_val).strip()
        formats = [
            "%d/%m/%Y", 
            "%d-%m-%Y", 
            "%Y-%m-%d", 
            "%d/%m/%y", 
            "%d-%m-%y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str_val, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {str_val}")
        return None
