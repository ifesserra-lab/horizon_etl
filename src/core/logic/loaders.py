import json
import os
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from loguru import logger


class SigPesqFileLoader:
    """
    Loads and parses files downloaded by sigpesq_agent.
    Expects files to be in a 'report' subdirectory or the root of the download dir.
    """

    def __init__(self, directory: str):
        self.directory = directory

    def load_files(self) -> List[Dict[str, Any]]:
        """
        Scans the directory for HTML/JSON files and loads them.
        Prioritizes 'report' subdirectory if it exists.
        """
        target_dir = os.path.join(self.directory, "report")
        if not os.path.exists(target_dir):
            logger.warning(
                f"'report' directory not found in {self.directory}. Scanning root."
            )
            target_dir = self.directory

        if not os.path.exists(target_dir):
            logger.error(f"Target directory {target_dir} does not exist.")
            return []

        results = []
        logger.info(f"Scanning files in {target_dir}...")

        for filename in os.listdir(target_dir):
            file_path = os.path.join(target_dir, filename)
            if not os.path.isfile(file_path):
                continue

            try:
                content = self._read_file(file_path)
                if content:
                    results.append(content)
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")

        return results

    def _read_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        filename = os.path.basename(file_path)

        # Simple extraction strategy
        data = {
            "filename": filename,
            "path": file_path,
            "raw_content": None,
            "parsed_content": {},
        }

        if filename.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data["parsed_content"] = json.load(f)

        elif filename.endswith(".html"):
            with open(file_path, "r", encoding="utf-8") as f:
                raw_html = f.read()
                data["raw_content"] = raw_html
                # Basic parsing or just passing raw
                # For SigPesq, usually we extract tables.
                # Let's try to extract something minimal if possible, else leave to mapper
                soup = BeautifulSoup(raw_html, "html.parser")
                data["parsed_content"] = {
                    "title": soup.title.string if soup.title else ""
                }
        else:
            return None

        return data
