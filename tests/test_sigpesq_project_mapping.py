from src.core.logic.initiative_identity import build_identity_key
from src.core.logic.strategies.sigpesq_projects import SigPesqProjectMappingStrategy


def test_sigpesq_project_mapping_uses_project_id_as_sigpesq_identity_code():
    strategy = SigPesqProjectMappingStrategy()

    mapped = strategy.map_row(
        {
            "Id": "PJ      8748",
            "Titulo": "Desenvolvimento de um Modulo de Hidroponia Autonomo",
            "ParecerDiretoria": "Aprovado",
            "Inicio": "01-08-26",
            "Coordenador": "Docente Coordenador",
        }
    )

    assert mapped["identity_key"] == build_identity_key(["sigpesq_project", "8748"])
    assert mapped["metadata"]["sigpesq_project_code"] == "8748"
