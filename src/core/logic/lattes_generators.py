import os
from typing import List, Dict

class LattesConfigGenerator:
    """
    Generates the configuration file for scriptLattes.
    """
    def generate(self, config_path: str, output_dir: str) -> None:
        """
        Generates the configuration file.

        Args:
            config_path: Absolute path where the .config file will be saved.
            output_dir: Directory where scriptLattes should save its output (JSONs).
        """
        config_content = f"""
# Arquivo de configuracao gerado automaticamente
global-diretorio_de_saida_json = {output_dir}
"""
        with open(config_path, 'w') as f:
            f.write(config_content.strip())

class LattesListGenerator:
    """
    Generates the list file for scriptLattes containing researchers' Lattes IDs.
    """
    def generate_from_db(self, list_path: str, researchers: List[Dict]) -> None:
        """
        Generates the list file from a list of researcher dictionaries.
        
        Args:
            list_path: Absolute path where the .list file will be saved.
            researchers: List of dicts, each must have 'name' and 'lattes_id'.
        """
        lines = []
        for r in researchers:
            lattes_id = r.get('lattes_id')
            name = r.get('name')
            if lattes_id and name:
                 lines.append(f"{lattes_id},{name}")
        
        with open(list_path, 'w') as f:
            f.write("\n".join(lines))
