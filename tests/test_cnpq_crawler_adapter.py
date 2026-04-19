from src.adapters.sources.cnpq_crawler import CnpqCrawlerAdapter, normalize_cnpq_url


def make_adapter():
    return CnpqCrawlerAdapter.__new__(CnpqCrawlerAdapter)


def test_normalize_cnpq_url_trims_and_collapses_mirror_path_slashes():
    assert (
        normalize_cnpq_url(" http://dgp.cnpq.br/dgp/espelhogrupo//0343404635555454 ")
        == "http://dgp.cnpq.br/dgp/espelhogrupo/0343404635555454"
    )


def test_extract_leaders_ignores_ui_placeholder_names():
    adapter = make_adapter()

    leaders = adapter.extract_leaders(
        {
            "identificacao": {
                "lideres_do_grupo": [
                    "Maria Silva",
                    "ui-button",
                    "  ",
                    None,
                    "Joao Souza",
                ]
            }
        }
    )

    assert leaders == ["Maria Silva", "Joao Souza"]


def test_extract_members_ignores_ui_placeholder_names_across_member_tables():
    adapter = make_adapter()

    members = adapter.extract_members(
        {
            "recursos_humanos": {
                "pesquisadores": [
                    {"nome": "Ana Pesquisadora", "data_inicio": "01/01/2020"},
                    {"nome": "ui-button"},
                ],
                "estudantes": [
                    {"nome": "ui-button"},
                    {"nome": "Bruno Estudante", "nivel": "Graduacao"},
                ],
                "tecnicos": [
                    {"nome": "ui-button"},
                    {"nome": "Carla Tecnica"},
                ],
                "egressos": [
                    {"nome": "ui-button"},
                    {"nome": "Diego Egresso"},
                ],
            }
        }
    )

    assert [member["name"] for member in members] == [
        "Ana Pesquisadora",
        "Bruno Estudante",
        "Carla Tecnica",
        "Diego Egresso",
    ]
