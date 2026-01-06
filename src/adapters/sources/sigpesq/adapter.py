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
        # Support SIGPESQ_USER as alias for SIGPESQ_USERNAME
        if os.getenv("SIGPESQ_USER") and not os.getenv("SIGPESQ_USERNAME"):
            os.environ["SIGPESQ_USERNAME"] = os.getenv("SIGPESQ_USER")

        required_vars = ["SIGPESQ_USERNAME", "SIGPESQ_PASSWORD"]
        missing = [v for v in required_vars if not os.getenv(v)]

        if missing:
            logger.error(
                f"Missing environment variables for SigPesq: {', '.join(missing)}"
            )
            # Try to be helpful if they used the wrong one
            if "SIGPESQ_USERNAME" in missing and os.getenv("SIGPESQ_USER"):
                logger.info("Found SIGPESQ_USER, mapped to SIGPESQ_USERNAME.")
            else:
                raise EnvironmentError(f"SigPesq Agent requires: {', '.join(missing)}")

        logger.debug("Environment variables for SigPesq verified.")

    def _trigger_download(self):
        """
        Calls the external lib to download files.
        """
        logger.info(f"Triggering sigpesq_agent in {self.download_dir}...")

        # Attempt to import and run the agent
        import asyncio
        from agent_sigpesq.services.reports_service import SigpesqReportService

        async def run_agent():
            service = SigpesqReportService(headless=True, download_dir=self.download_dir)
            return await service.run()

        success = asyncio.run(run_agent())
        
        if not success:
             raise RuntimeError("SigpesqReportService failed to download reports.")

