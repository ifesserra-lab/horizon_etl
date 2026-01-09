from typing import Any, Dict, List, Optional

from dgp_cnpq_lib import CnpqCrawler
from loguru import logger


class CnpqCrawlerAdapter:
    """
    Adapter for dgp_cnpq_lib to extract research group data from CNPq DGP.
    """

    def __init__(self):
        self._crawler = CnpqCrawler()

    def get_group_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extracts data for a single research group from its mirror URL.
        """
        try:
            logger.info(f"Extracting data from CNPq Mirror: {url}")
            data = self._crawler.get_data(url)
            return data
        except Exception as e:
            logger.error(f"Failed to extract data from {url}: {e}")
            return None

    def extract_members(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses member data from the raw extracted dictionary.
        Members are usually found under 'recursos_humanos' fieldset.
        """
        members = []
        logger.info(f"Available keys in raw data: {list(data.keys())}")

        rh_content = data.get("recursos_humanos") or data.get("recursos_humanos_do_grupo") or {}
        logger.info(f"RH content keys: {list(rh_content.keys())}")

        # Researchers table
        if "pesquisadores" in rh_content:
            for item in rh_content["pesquisadores"]:
                # The key can be 'nome', 'nome_do_pesquisador' or even 'pesquisadores'
                name = (
                    item.get("nome") or 
                    item.get("nome_do_pesquisador") or 
                    item.get("pesquisadores")
                )
                if name:
                    members.append(
                        {
                            "name": name,
                            "role": "Pesquisador",
                            "data_inicio": item.get("data_inclusao") or item.get("data_inicio"),
                            "data_fim": item.get("data_egresso") or item.get("data_fim"),
                            "bolsa": item.get("bolsa"),
                        }
                    )

        # Students table
        if "estudantes" in rh_content:
            for item in rh_content["estudantes"]:
                name = (
                    item.get("nome") or 
                    item.get("nome_do_estudante") or 
                    item.get("estudantes")
                )
                if name:
                    members.append(
                        {
                            "name": name,
                            "role": "Estudante",
                            "data_inicio": item.get("data_inclusao") or item.get("data_inicio"),
                            "data_fim": item.get("data_egresso") or item.get("data_fim"),
                            "nivel": item.get("nivel"),
                        }
                    )

        # Technicians
        if "tecnicos" in rh_content:
            for item in rh_content["tecnicos"]:
                name = (
                    item.get("nome") or 
                    item.get("nome_do_tecnico") or 
                    item.get("tecnicos")
                )
                if name:
                    members.append(
                        {
                            "name": name,
                            "role": "Técnico",
                            "data_inicio": item.get("data_inclusao") or item.get("data_inicio"),
                            "data_fim": item.get("data_egresso") or item.get("data_fim"),
                        }
                    )

        # Egressos
        if "egressos" in rh_content:
            for item in rh_content["egressos"]:
                name = (
                    item.get("nome") or 
                    item.get("nome_do_egresso") or
                    item.get("egressos")
                )
                if name:
                    # Determine role based on available info or default to generic Egresso
                    role_suffix = " (Egresso)"
                    base_role = "Pesquisador" # Default
                    
                    # Try to infer original role if possible (some structures might have it)
                    if item.get("nivel") or "estudante" in str(item).lower():
                        base_role = "Estudante"
                    
                    final_role = f"{base_role}{role_suffix}"

                    members.append(
                        {
                            "name": name,
                            "role": final_role,
                            "data_inicio": item.get("data_inclusao") or item.get("data_inicio"),
                            "data_fim": item.get("data_egresso") or item.get("data_fim"),
                            "nivel": item.get("nivel"),
                        }
                    )

        return members

    def extract_leaders(self, data: Dict[str, Any]) -> List[str]:
        """
        Extracts leader names.
        Usually found in 'identificacao' under 'lideres_do_grupo'.
        """
        ident_content = data.get("identificacao", {})
        return ident_content.get("lideres_do_grupo", [])

    def extract_research_lines(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts research lines from 'linhas_de_pesquisa' fieldset.
        Returns a list of dictionaries, usually containing 'nome_da_linha_de_pesquisa'.
        """
        # Based on debug output: {'linhas': [{'nome_da_linha_de_pesquisa': '...', ...}]}
        lp_content = data.get("linhas_de_pesquisa", {})
        return lp_content.get("linhas", [])
