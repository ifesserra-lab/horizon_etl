import json
import re
import unicodedata
from typing import Any, Dict, List, Optional
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
    Parses Lattes JSON structure to extract projects and articles.
    """

    def normalize_title(self, title: Optional[str]) -> str:
        """
        Normalizes a title for comparison (lowercase, no accents, no special chars).
        """
        if not title:
            return ""
        # Accents and case
        nfkd_form = unicodedata.normalize("NFKD", title)
        only_ascii = nfkd_form.encode("ASCII", "ignore").decode("ASCII")
        # Remove special characters and multiple spaces
        clean = re.sub(r"[^a-zA-Z0-9\s]", " ", only_ascii).lower()
        return " ".join(clean.split())

    def parse_research_projects(self, data: Dict) -> List[Dict]:
        return self._parse_generic_projects(
            data, "projetos_pesquisa", "Research Project"
        )

    def parse_extension_projects(self, data: Dict) -> List[Dict]:
        return self._parse_generic_projects(
            data, "projetos_extensao", "Extension Project"
        )

    def parse_development_projects(self, json_data: dict) -> List[Dict[str, Any]]:
        """Parses 'projetos_desenvolvimento' from JSON."""
        return self._parse_generic_projects(
            json_data, "projetos_desenvolvimento", "Development Project"
        )
    
    def parse_articles(self, data: Dict) -> List[Dict[str, Any]]:
        """Parses 'artigos_periodicos' from JSON."""
        biblio = data.get("producao_bibliografica", {})
        items = biblio.get("artigos_periodicos", [])
        parsed = []
        for item in items:
            title = item.get("titulo")
            parsed.append({
                "title": title,
                "normalized_title": self.normalize_title(title),
                "year": int(item["ano"]) if str(item.get("ano", "")).isdigit() else None,
                "journal_conference": item.get("revista"),
                "volume": item.get("volume"),
                "pages": item.get("paginas"),
                "doi": item.get("doi"),
                "authors_str": item.get("autores"),
                "type": "Journal"  # lib expectation
            })
        return parsed

    def parse_conference_papers(self, data: Dict) -> List[Dict[str, Any]]:
        """Parses 'trabalhos_completos_congressos' from JSON."""
        biblio = data.get("producao_bibliografica", {})
        items = biblio.get("trabalhos_completos_congressos", [])
        parsed = []
        for item in items:
            title = item.get("titulo")
            parsed.append({
                "title": title,
                "normalized_title": self.normalize_title(title),
                "year": int(item["ano"]) if str(item.get("ano", "")).isdigit() else None,
                "journal_conference": item.get("evento"),
                "pages": item.get("paginas"),
                "authors_str": item.get("autores"),
                "type": "Conference Event"  # lib expectation
            })
        return parsed
    
    def parse_personal_info(self, data: Dict) -> Dict[str, Any]:
        """
        Extracts personal info (name, resume, etc) from JSON.
        """
        info = data.get("informacoes_pessoais", {})
        return {
            "name": info.get("nome_completo") or data.get("nome") or data.get("name"),
            "resume": info.get("texto_resumo"),
            "lattes_id": info.get("id_lattes"),
            "citation_names": info.get("nome_citacoes"),
            "cnpq_url": info.get("url")
        }

    def parse_academic_education(self, json_data: dict) -> List[Dict[str, Any]]:
        """Parses 'formacao_academica' from JSON."""
        items = json_data.get("formacao_academica", [])
        if not items:
            return []

        parsed_items = []
        for item in items:
            try:
                # Extract degree code/name
                # Some JSONs have 'tipo': 'Doutorado em Informática'
                # Others might have 'nome_pt' or 'degree'
                degree = item.get("nome_pt") or item.get("degree")
                course_name = item.get("nome_curso_ingles")

                if not degree:
                     tipo = item.get("tipo", "")
                     if " em " in tipo:
                         parts = tipo.split(" em ", 1)
                         degree = parts[0]
                         course_name = parts[1] if not course_name else course_name
                     else:
                         degree = tipo or "Unknown"

                # Extract years
                start_year = None
                if item.get("ano_inicio"):
                     try:
                         start_year = int(item["ano_inicio"])
                     except ValueError:
                         pass

                end_year = None
                if item.get("ano_conclusao") or item.get("ano_fim"):
                     val = item.get("ano_conclusao") or item.get("ano_fim")
                     try:
                         end_year = int(val)
                     except ValueError:
                         pass
                
                # Extract institution
                institution = item.get("nome_instituicao") or item.get("institution")

                # Fallback course name
                if not course_name:
                    course_name = degree

                # Extract Description and Thesis Title
                description = item.get("descricao")
                thesis_title = None
                
                if description:
                    # Description is sometimes a list in legacy formats, but usually a string in JSON
                    # If it's a list, join it? The sample shows it as string inside list in other fields, 
                    # but for `formacao_academica` strict schema isn't fully clear. 
                    # Assuming string as per recent observation 
                    # "descricao": "Título: From Continuous ... , Ano..."
                    
                    # Regex to find title
                    # Pattern: Título: (.*?)(,|Ano de|$)
                    # Adjust regex to capture until comma or known delimeters
                    match = re.search(r"Título:\s*(.+?)(?:, Ano|,\s*Orientador|\.|$)", description, re.IGNORECASE)
                    if match:
                        thesis_title = match.group(1).strip()

                parsed_items.append({
                    "degree": degree,
                    "institution": institution,
                    "course_name": course_name,
                    "start_year": start_year,
                    "end_year": end_year,
                    "description": description,
                    "thesis_title": thesis_title
                })
            except Exception as e:
                logger.warning(f"Error parsing education item: {e}")
                continue
        
        return parsed_items

    def _parse_generic_projects(self, data: Dict, projects_key: str, type_name: str) -> List[Dict]:
        parsed_projects = []
        projects_list = data.get(projects_key, [])
        
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
