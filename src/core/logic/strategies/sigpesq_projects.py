from typing import Any, Dict
import pandas as pd
from loguru import logger
from .base import ProjectMappingStrategy

# Check base.py content first to see what to inherit from.
# Actually I saw 'ResearchGroupMappingStrategy' in sigpesq_excel.py
# I should probably define a generic MappingStrategy or just a specific one.

class SigPesqProjectMappingStrategy(ProjectMappingStrategy):
    """Strategy for mapping SigPesq Project Excel data."""

    def map_row(self, row: dict) -> Dict[str, Any]:
        """Maps SigPesq Excel columns to standardized keys for Project."""
        # Based on typical SigPesq exports or common knowledge/inspection if file existed
        # Since I don't have the file, I'll use reasonable defaults and robust get
        # Keys often: Title, Situation, Start Date, End Date, Value
        
        return {
            "title": row.get("Titulo", row.get("Título")),
            "status": row.get("Situacao", row.get("Situação")),
            "start_date": self._parse_date(row.get("Data Inicio", row.get("Inicio"))),
            "end_date": self._parse_date(row.get("Data Termino", row.get("Termino"))),
            "description": row.get("Resumo"),
            "value": row.get("Valor Aprovado"),
            "coordinator_name": row.get("Coordenador"),
        }

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
