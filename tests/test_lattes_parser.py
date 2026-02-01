import pytest
from src.adapters.sources.lattes_parser import LattesParser

@pytest.fixture
def parser():
    return LattesParser()

@pytest.fixture
def sample_data():
    return {
        "projetos_pesquisa": [
            {
                "nome": "Projeto Pesquisa 1",
                "ano_inicio": "2020",
                "ano_conclusao": "Atual",
                "descricao": ["Descrição: Descricao do projeto. Situação: Em andamento; Natureza: Pesquisa."],
                "integrantes": [{"nome": "Pesquisador A", "papel": "Coordenador"}]
            }
        ],
        "projetos_extensao": [
            {
                "nome": "Projeto Extensao 1",
                "ano_inicio": "2021",
                "ano_conclusao": "2022",
                "descricao": ["Descrição: Descricao extensao. Situação: Concluído; Natureza: Extensão."],
                "integrantes": []
            }
        ],
        "projetos_desenvolvimento": [
             {
                "nome": "Projeto Dev 1",
                "ano_inicio": "2019",
                "ano_conclusao": "2019",
                "descricao": ["Descrição: Descricao dev. Situação: Concluído; Natureza: Desenvolvimento."],
                "integrantes": []
            }
        ]
    }

def test_parse_research_projects(parser, sample_data):
    projects = parser.parse_research_projects(sample_data)
    assert len(projects) == 1
    p = projects[0]
    assert p["name"] == "Projeto Pesquisa 1"
    assert p["start_year"] == 2020
    assert p["end_year"] is None
    assert p["status"] == "Active"
    assert p["initiative_type_name"] == "Research Project"
    assert "Descricao do projeto" in p["description"]

def test_parse_extension_projects(parser, sample_data):
    projects = parser.parse_extension_projects(sample_data)
    assert len(projects) == 1
    p = projects[0]
    assert p["name"] == "Projeto Extensao 1"
    assert p["start_year"] == 2021
    assert p["end_year"] == 2022
    assert p["status"] == "Concluded"
    assert p["initiative_type_name"] == "Extension Project"

def test_parse_development_projects(parser, sample_data):
    projects = parser.parse_development_projects(sample_data)
    assert len(projects) == 1
    p = projects[0]
    assert p["name"] == "Projeto Dev 1"
    assert p["initiative_type_name"] == "Development Project"

def test_clean_description(parser):
    raw = "Descrição: Minha descrição aqui. Situação: Em andamento; Natureza: Pesquisa."
    clean = parser._clean_description(raw)
    assert clean == "Minha descrição aqui"
    
    raw2 = "Descrição: Apenas descrição."
    clean2 = parser._clean_description(raw2)
    assert clean2 == "Apenas descrição"

