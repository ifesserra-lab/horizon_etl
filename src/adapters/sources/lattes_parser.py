import json
import re
from typing import Dict, List, Optional
from datetime import date
from dataclasses import dataclass

@dataclass
class LattesProject:
    name: str
    start_year: Optional[int]
    end_year: Optional[int]
    status: str
    description: str
    nature: str
    type_name: str  # "Research Project", "Extension Project", "Development Project"
    role: str # "Coordenador", "Integrante"

class LattesParser:
    """
    Parses Lattes JSON structure to extract projects.
    """

    def parse_research_projects(self, data: Dict) -> List[Dict]:
        return self._parse_generic_projects(
            data.get("projetos_pesquisa", []), 
            "Research Project"
        )

    def parse_extension_projects(self, data: Dict) -> List[Dict]:
        return self._parse_generic_projects(
            data.get("projetos_extensao", []), 
            "Extension Project"
        )

    def parse_development_projects(self, data: Dict) -> List[Dict]:
        return self._parse_generic_projects(
            data.get("projetos_desenvolvimento", []), 
            "Development Project"
        )

    def _parse_generic_projects(self, projects_list: List[Dict], type_name: str) -> List[Dict]:
        parsed_projects = []
        
        for p in projects_list:
            name = p.get("name") or p.get("nome")
            start_year_str = p.get("ano_inicio")
            end_year_str = p.get("ano_conclusao")
            
            start_year = int(start_year_str) if start_year_str and start_year_str.isdigit() else None
            
            end_year = None
            if end_year_str and end_year_str.isdigit():
                end_year = int(end_year_str)
            
            # Status Inference
            status = "Concluded"
            if end_year_str and end_year_str.lower() == "atual":
                status = "Active"
                end_year = None
            elif end_year and end_year >= date.today().year:
                 # If end year is defined and in future (rare in Lattes manual entry but possible)
                 pass

            # Description Cleaning
            # Description is often a list with one string containing "Descrição: ... Situação: ... Natureza: ..."
            raw_desc_list = p.get("descricao", [])
            full_desc_str = " ".join(raw_desc_list) if isinstance(raw_desc_list, list) else str(raw_desc_list)
            
            description = self._clean_description(full_desc_str)
            
            # Role extraction (self-role for the owner of the CV)
            # We don't have the Researcher ID here easily without context, 
            # but usually the first member or looking for "Coordenador" match?
            # Actually, the JSON often lists "integrantes" with names and roles.
            # For this MVP, we will extract the members list as metadata if needed, 
            # but the key is to return the Project definition.
            
            parsed_projects.append({
                "name": name,
                "start_year": start_year,
                "end_year": end_year,
                "status": status,
                "description": description,
                "initiative_type_name": type_name,
                "raw_members": p.get("integrantes", [])
            })
            
        return parsed_projects

    def _clean_description(self, text: str) -> str:
        """
        Removes metadata prefix/suffix from description.
        Input: "Descrição: O projeto... Situação: Em andamento; Natureza: Pesquisa..."
        Output: "O projeto..."
        """
        if not text:
            return ""
            
        # Remove literal "Descrição:" prefix
        clean = re.sub(r"^Descrição:\s*", "", text, flags=re.IGNORECASE)
        
        # Remove Metadata suffix starting with "Situação:" or "Natureza:"
        # We split by these keys and take the first part
        split_markers = ["Situação:", "Natureza:", "Alunos envolvidos:", "Integrantes:"]
        
        for marker in split_markers:
            if marker in clean:
                clean = clean.split(marker)[0]
        
        return clean.strip().rstrip(".")
