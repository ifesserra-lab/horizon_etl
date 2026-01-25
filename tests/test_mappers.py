from datetime import datetime

from src.core.logic.mappers import SigPesqMapper


def test_map_project_success():
    raw_data = {
        "titulo": " Projeto Horizon ",
        "situacao": "Em Andamento",
        "id_projeto": 12345,
        "data_inicio": "01/01/2026",
    }

    project = SigPesqMapper.map_project(raw_data)

    assert project.title == "Projeto Horizon"
    assert project.status == "Em Andamento"
    assert project.origin_id == "12345"
    assert project.start_date == datetime(2026, 1, 1)
    assert project.metadata["original_source"] == "sigpesq"


def test_map_project_invalid_date():
    raw_data = {"titulo": "Projeto Sem Data", "data_inicio": "invalid-date"}
    project = SigPesqMapper.map_project(raw_data)
    assert project.start_date is None


def test_map_research_group():
    raw_data = {"nome_grupo": " IA Lab ", "lider": " Dr. Silva ", "certificado": True}
    group = SigPesqMapper.map_research_group(raw_data)
    assert group.name == "IA Lab"
    # Metadata removed from mapper
    # assert group.metadata["leader"] == "Dr. Silva"
    # assert group.metadata["certified"] is True


def test_map_researcher():
    raw_data = {"nome": " Paulo Junior ", "funcao": " Bolsista "}
    researcher = SigPesqMapper.map_researcher(raw_data)
    assert researcher.name == "Paulo Junior"
    # Metadata removed from mapper
    # assert researcher.metadata["role"] == "Bolsista"
