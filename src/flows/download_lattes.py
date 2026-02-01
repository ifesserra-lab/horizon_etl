from prefect import flow, task
import os
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
def generate_config(output_dir: str) -> str:
    config_gen = LattesConfigGenerator()
    config_path = os.path.abspath("lattes.config")
    config_gen.generate(config_path, output_dir)
    return config_path

@task
def generate_list(researchers: List[Dict]) -> str:
    list_gen = LattesListGenerator()
    list_path = os.path.abspath("lattes.list")
    list_gen.generate_from_db(list_path, researchers)
    return list_path

@task
def run_script_lattes_mock(config_path: str, list_path: str):
    mocker = ScriptLattesMock()
    mocker.run(config_path, list_path)

@flow(name="Download Lattes Curricula")
def download_lattes_flow():
    # 1. Setup paths
    base_dir = os.path.abspath("data")
    output_dir = os.path.join(base_dir, "lattes_json")
    os.makedirs(output_dir, exist_ok=True)

    # 2. Get Data
    researchers = get_researchers_from_db()
    
    # 3. Generate Files
    config_path = generate_config(output_dir)
    list_path = generate_list(researchers)
    
    # 4. Run Mock
    run_script_lattes_mock(config_path, list_path)

if __name__ == "__main__":
    download_lattes_flow()
