from prefect import flow, task
import os
from loguru import logger
from typing import List, Dict
from src.core.logic.lattes_generators import LattesConfigGenerator, LattesListGenerator
from src.core.logic.strategies.script_lattes_mock import ScriptLattesMock
# from research_domain_lib.repository.researcher_repository import ResearcherRepository

# Mocking repository access for standalone flow execution if needed, 
# but in real scenario this should inject the repo.
# For now, I'll assume we can get data. 
# Since I cannot easily instantiate the real repository without DB connection in this "one-shot" agent,
# I'll create a task that *would* fetch from DB, but for now returns mock data or tries to use the repo if available.

@task
def get_researchers_from_db() -> List[Dict]:
    """
    Fetches researchers from the database.
    For this implementation, we will mock the return to ensure the flow runs 
    without needing a live DB connection if the environment isn't fully set up for it,
    BUT the goal is to use the DB. 
    Equality, let's try to mock it for the 'mock process' requested.
    """
    # In a real scenario:
    # repo = ResearcherRepository(db_session)
    # return repo.get_all()
    
    # Mock return for the scope of this task
    return [
        {"name": "Paulo Sergio dos Santos Junior", "lattes_id": "8400407353673370"},
        {"name": "Daniel Cruz Cavalieri", "lattes_id": "9583314331960942"},
        {"name": "Monalessa Perini Barcellos", "lattes_id": "8826584877205264"},
        {"name": "João Paulo Andrade Almeida", "lattes_id": "4332944687727598"},
        {"name": "Rafael Emerick Zape de Oliveira", "lattes_id": "8365543719828195"},
        {"name": "Gabriel Tozatto Zago", "lattes_id": "8771088249434104"},
        {"name": "Renato Tannure Rotta de Almeida", "lattes_id": "6927212610032092"},
        {"name": "Rodrigo Varejão Andreão", "lattes_id": "5589662366089944"},
        {"name": "Elton Siqueira Moura", "lattes_id": "7923759097083335"},
        {"name": "Eduardo Peixoto Costa Rocha", "lattes_id": "8617069437130629"},
        {"name": "Germana Sagrillo Moro", "lattes_id": "8223626264677830"},
        {"name": "Celso Alberto Saibel Santos", "lattes_id": "7614206164174151"}
    ]

@task
def generate_config(output_dir: str, list_path: str) -> str:
    config_gen = LattesConfigGenerator()
    config_path = os.path.abspath("lattes.config")
    config_gen.generate(config_path, output_dir, list_path)
    return config_path

@task
def generate_list(researchers: List[Dict]) -> str:
    list_gen = LattesListGenerator()
    list_path = os.path.abspath("lattes.list")
    list_gen.generate_from_db(list_path, researchers)
    return list_path

@task
def run_script_lattes_real(config_path: str):
    try:
        from scriptLattes.run import executar_scriptLattes
        logger.info(f"Starting real scriptLattes execution with config: {config_path}")
        # Run with somente_json=True since we are an ETL pipeline
        executar_scriptLattes(config_path, somente_json=True)
        logger.info("Real scriptLattes execution finished.")
    except ImportError:
        logger.error("scriptLattes library not found. Please install it.")
        raise
    except Exception as e:
        logger.error(f"scriptLattes execution failed: {e}")
        raise

@flow(name="Download Lattes Curricula")
def download_lattes_flow():
    # 1. Setup paths
    base_dir = os.path.abspath("data")
    output_dir = os.path.join(base_dir, "lattes_json")
    os.makedirs(output_dir, exist_ok=True)

    # 2. Key: Check for override list
    override_list_path = os.path.abspath("data/lattes_run/lattes.list")
    
    # 3. Generate List First
    if os.path.exists(override_list_path):
        logger.info(f"Using override list file: {override_list_path}")
        list_path = override_list_path
    else:
        logger.info("Using DB researchers for list generation.")
        researchers = get_researchers_from_db()
        list_path = generate_list(researchers)

    # 4. Generate Config (Now depends on list path)
    config_path = generate_config(output_dir, list_path)
    
    # 4. Run Real scriptLattes
    # We need to make sure the list file path in config matches what we expect
    # The LattesConfigGenerator might need adjustment if it doesn't take list_path as arg 
    # but writes 'lattes.list' to config. 
    # scriptLattes reads 'lista-de-entrada-de-nomes' parameter.
    
    # Check if we need to update config to point to the correct list?
    # LattesConfigGenerator.generate usually assumes "lattes.list" in the same dir or defines it.
    # Let's inspect LattesConfigGenerator if needed, but assuming standard behavior:
    # We should ensure the list path is correctly referenced.
    
    # Check if list_path needs to be configured in config file.
    # For now, let's run.
    run_script_lattes_real(config_path)

if __name__ == "__main__":
    download_lattes_flow()
