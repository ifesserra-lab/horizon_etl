import os

from typing import Any, Dict, List

from loguru import logger

from src.core.logic.loaders import SigPesqFileLoader
from src.core.ports.source import ISource


class SigPesqAdapter(ISource):
    def __init__(self, download_dir: str = "data/raw/sigpesq"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def extract(self) -> List[Dict[str, Any]]:
        """
        Orchestrates the extraction:
        1. Validate environment (credentials).
        2. Trigger sigpesq_agent to download files.
        3. Read downloaded files from 'report' folder.
        """
        logger.info("Starting SigPesq extraction adapter...")

        self._validate_environment()

        # Step 1: Download
        self._trigger_download()

        # Step 2: Read
        loader = SigPesqFileLoader(self.download_dir)
        raw_data = loader.load_files()

        logger.info(f"Extraction finished. {len(raw_data)} items loaded.")
        return raw_data

    def _validate_environment(self):
        """
        Ensures necessary environment variables are set for sigpesq_agent.
        """
        required_vars = ["SIGPESQ_USERNAME", "SIGPESQ_PASSWORD"]
        missing = [v for v in required_vars if not os.getenv(v)]

        if missing:
            logger.error(
                f"Missing environment variables for SigPesq: {', '.join(missing)}"
            )
            raise EnvironmentError(f"SigPesq Agent requires: {', '.join(missing)}")

        logger.debug("Environment variables for SigPesq verified.")

    def _trigger_download(self):
        """
        Calls the external lib to download files.
        """
        logger.info(f"Triggering sigpesq_agent in {self.download_dir}...")

        try:
            # Attempt to import and run the agent
            import sigpesq_agent

            # Check for common entry points (heuristic)
            if hasattr(sigpesq_agent, "main"):
                sigpesq_agent.main()
            elif hasattr(sigpesq_agent, "run"):
                sigpesq_agent.run()
            else:
                logger.warning("sigpesq_agent imported but no run/main found.")

        except ImportError:
            logger.warning(
                "sigpesq_agent library not found. Running in Mock/Offline mode."
            )
            # Create dummy report for testing
            report_dir = os.path.join(self.download_dir, "report")
            os.makedirs(report_dir, exist_ok=True)
            with open(os.path.join(report_dir, "mock_project_001.json"), "w") as f:
                f.write(
                    '{"titulo": "Projeto Mock SigPesq", "situacao": "Em Andamento", "id_projeto": "12345"}'
                )
        except Exception as e:
            logger.error(f"Error running sigpesq_agent: {e}")
