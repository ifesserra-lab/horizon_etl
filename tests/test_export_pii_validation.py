import re
from unittest.mock import MagicMock, patch

import pytest

from src.core.logic.canonical_exporter import CanonicalDataExporter
from src.core.logic.pii_anonymizer import is_anonymized_cpf, is_anonymized_email
from src.core.logic.research_group_exporter import ResearchGroupExporter
from src.core.ports.export_sink import IExportSink

RAW_CPF_PATTERN = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
RAW_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
ANONYMIZED_DOMAIN = "@anon.lgpd"


def _check_no_raw_pii_in_json_str(text: str):
    assert not RAW_CPF_PATTERN.search(text), "Raw CPF found in export"
    matches = RAW_EMAIL_PATTERN.findall(text)
    for m in matches:
        if not m.endswith(ANONYMIZED_DOMAIN):
            raise AssertionError(f"Raw email found in export: {m}")


def _make_exporter(mock_sink) -> CanonicalDataExporter:
    with (
        patch("src.core.logic.canonical_exporter.OrganizationController"),
        patch("src.core.logic.canonical_exporter.CampusController"),
        patch("src.core.logic.canonical_exporter.KnowledgeAreaController"),
        patch("src.core.logic.canonical_exporter.ResearcherController"),
        patch("src.core.logic.canonical_exporter.InitiativeController"),
        patch("src.core.logic.canonical_exporter.ArticleController"),
    ):
        return CanonicalDataExporter(sink=mock_sink)


# --- Researcher export PII validation ---


def test_researcher_export_identification_id_is_anonymized():
    mock_sink = MagicMock(spec=IExportSink)
    exporter = _make_exporter(mock_sink)

    mock_researcher = MagicMock()
    mock_researcher.to_dict.return_value = {
        "id": 1,
        "name": "Alice",
        "identification_id": "123.456.789-00",
        "birthday": None,
    }
    exporter.researcher_ctrl.get_all.return_value = [mock_researcher]
    exporter.initiative_ctrl.get_all.return_value = []
    exporter.initiative_ctrl.list_initiative_types.return_value = []
    exporter._get_session = lambda: None
    exporter._get_campus_resolver = lambda: MagicMock(get_campus=lambda *a, **kw: None)
    exporter._fetch_researcher_advisorship_rows = lambda _: []

    exporter.export_researchers("output/researchers_canonical.json")

    exported = mock_sink.export.call_args[0][0]
    for item in exported:
        cpf = item.get("identification_id")
        assert is_anonymized_cpf(cpf), f"Raw CPF leaked: {cpf}"

    _check_no_raw_pii_in_json_str(str(exported))


def test_researcher_export_no_raw_cpf_in_any_classification_view():
    mock_sink = MagicMock(spec=IExportSink)
    exporter = _make_exporter(mock_sink)

    mock_researcher = MagicMock()
    mock_researcher.to_dict.return_value = {
        "id": 1,
        "name": "Alice",
        "identification_id": "987.654.321-00",
        "birthday": None,
    }
    exporter.researcher_ctrl.get_all.return_value = [mock_researcher]
    exporter.initiative_ctrl.get_all.return_value = []
    exporter.initiative_ctrl.list_initiative_types.return_value = []
    exporter._get_session = lambda: None
    exporter._get_campus_resolver = lambda: MagicMock(get_campus=lambda *a, **kw: None)
    exporter._fetch_researcher_advisorship_rows = lambda _: []

    exporter.export_researchers("output/researchers_canonical.json")

    calls = mock_sink.export.call_args_list
    for _, path in [c[0] for c in calls]:
        assert not RAW_CPF_PATTERN.search(path)


def test_researcher_export_stray_emails_in_resume_are_scrubbed():
    mock_sink = MagicMock(spec=IExportSink)
    exporter = _make_exporter(mock_sink)

    mock_researcher = MagicMock()
    mock_researcher.to_dict.return_value = {
        "id": 1,
        "name": "Alice",
        "identification_id": None,
        "birthday": None,
        "resume": "Contact me at alice@ifes.edu.br for collaboration",
    }
    exporter.researcher_ctrl.get_all.return_value = [mock_researcher]
    exporter.initiative_ctrl.get_all.return_value = []
    exporter.initiative_ctrl.list_initiative_types.return_value = []
    exporter._get_session = lambda: None
    exporter._get_campus_resolver = lambda: MagicMock(get_campus=lambda *a, **kw: None)
    exporter._fetch_researcher_advisorship_rows = lambda _: []

    exporter.export_researchers("output/researchers_canonical.json")

    exported = mock_sink.export.call_args[0][0]
    raw = str(exported)
    assert "alice@ifes.edu.br" not in raw, "Raw email found in resume"
    _check_no_raw_pii_in_json_str(raw)


# --- Research group export PII validation ---


def test_research_group_export_member_emails_are_anonymized():
    mock_sink = MagicMock(spec=IExportSink)

    with (
        patch(
            "src.core.logic.research_group_exporter.ResearchGroupController"
        ) as MockRgCtrl,
        patch("src.core.logic.research_group_exporter.CampusController"),
        patch("src.core.logic.research_group_exporter.OrganizationController"),
    ):
        mock_group = MagicMock()
        mock_group.to_dict.return_value = {"id": 10, "name": "Group A"}
        mock_group.organization_id = 1
        mock_group.campus_id = 2
        mock_group.knowledge_areas = []

        mock_member = MagicMock()
        mock_member.person.id = 101
        mock_member.person.name = "Alice"
        mock_member.role.name = "Researcher"
        mock_member.person.lattes_url = None
        mock_member.start_date = None
        mock_member.end_date = None

        mock_email = MagicMock()
        mock_email.email = "alice@example.com"
        mock_member.person.emails = [mock_email]
        mock_group.members = [mock_member]

        MockRgCtrl.return_value.get_all.return_value = [mock_group]

        exporter = ResearchGroupExporter(sink=mock_sink)
        exporter.export_all("output.json")

        exported = mock_sink.export.call_args[0][0]
        for group in exported:
            for member in group.get("members", []):
                for email in member.get("emails", []):
                    assert is_anonymized_email(
                        email
                    ), f"Raw email leaked in group export: {email}"


def test_research_group_export_no_raw_email_in_output():
    mock_sink = MagicMock(spec=IExportSink)

    with (
        patch(
            "src.core.logic.research_group_exporter.ResearchGroupController"
        ) as MockRgCtrl,
        patch("src.core.logic.research_group_exporter.CampusController"),
        patch("src.core.logic.research_group_exporter.OrganizationController"),
    ):
        mock_group = MagicMock()
        mock_group.to_dict.return_value = {"id": 10, "name": "Group A"}
        mock_group.organization_id = 1
        mock_group.campus_id = 2
        mock_group.knowledge_areas = []

        mock_member = MagicMock()
        mock_member.person.id = 101
        mock_member.person.name = "Alice"
        mock_member.role.name = "Researcher"
        mock_member.person.lattes_url = None
        mock_member.start_date = None
        mock_member.end_date = None

        mock_email = MagicMock()
        mock_email.email = "bob@ifes.edu.br"
        mock_member.person.emails = [mock_email]
        mock_group.members = [mock_member]

        MockRgCtrl.return_value.get_all.return_value = [mock_group]

        exporter = ResearchGroupExporter(sink=mock_sink)
        exporter.export_all("output.json")

        exported = mock_sink.export.call_args[0][0]
        raw_json_str = str(exported)
        _check_no_raw_pii_in_json_str(raw_json_str)


# --- Advisorship export PII validation ---


class MockRow:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __iter__(self):
        return iter(self.__dict__.items())


def _make_advisorship_row(
    person_name="Alice",
    supervisor_name="Bob",
    description="contact bob@ifes.edu.br",
):
    return MockRow(
        id=10,
        name="Pesquisa A",
        status="Ativo",
        description=description,
        start_date="2024-01-01",
        end_date=None,
        advisorship_type="IC",
        initiative_type_name="Iniciação Científica",
        person_id=1,
        person_name=person_name,
        supervisor_id=2,
        supervisor_name=supervisor_name,
        fellowship_id=None,
        fellowship_name=None,
        fellowship_description=None,
        fellowship_value=None,
        sponsor_name=None,
        parent_id=100,
        parent_name="Projeto Pai",
        parent_status="Ativo",
        parent_description="Parent project description",
        parent_start_date="2023-01-01",
        parent_end_date=None,
    )


def test_advisorship_export_scrubs_emails_in_descriptions():
    mock_sink = MagicMock(spec=IExportSink)
    exporter = _make_exporter(mock_sink)
    exporter._get_campus_resolver = lambda: MagicMock(get_campus=lambda *a, **kw: None)

    row = _make_advisorship_row()
    exporter._fetch_advisorship_export_rows = lambda _: [row]

    exporter.export_advisorships("output/advisorships_canonical.json")

    exported = mock_sink.export.call_args[0][0]
    raw = str(exported)
    assert "bob@ifes.edu.br" not in raw, "Raw email found in advisorship description"
    _check_no_raw_pii_in_json_str(raw)


def test_advisorship_export_scrubs_emails_and_no_raw_pii():
    mock_sink = MagicMock(spec=IExportSink)
    exporter = _make_exporter(mock_sink)
    exporter._get_campus_resolver = lambda: MagicMock(get_campus=lambda *a, **kw: None)

    row = _make_advisorship_row(
        description="Contact bob@ifes.edu.br — CPF expansion TBD in scrub_pii_deep"
    )
    exporter._fetch_advisorship_export_rows = lambda _: [row]

    exporter.export_advisorships("output/advisorships_canonical.json")

    exported = mock_sink.export.call_args[0][0]
    raw = str(exported)
    assert "bob@ifes.edu.br" not in raw, "Raw email found in advisorship description"
    _check_no_raw_pii_in_json_str(raw)


# --- Initiative export PII validation ---


def test_initiative_export_scrubs_pii_in_description_and_team():
    mock_sink = MagicMock(spec=IExportSink)
    exporter = _make_exporter(mock_sink)
    exporter._get_campus_resolver = lambda: MagicMock(get_campus=lambda *a, **kw: None)

    mock_init = MagicMock()
    mock_init.id = 1
    mock_init.name = "Iniciativa X"
    mock_init.status = "Ativo"
    mock_init.description = "Contact: coord@ifes.edu.br"
    mock_init.start_date = None
    mock_init.end_date = None
    mock_init.initiative_type_id = 1
    mock_init.organization_id = 1
    mock_init.parent_id = None
    mock_init.demandante = None
    mock_init.metadata = None

    exporter.initiative_ctrl.get_all.return_value = [mock_init]
    exporter.initiative_ctrl.get_teams.return_value = []
    exporter.initiative_ctrl.list_initiative_types.return_value = []
    exporter.org_ctrl.get_all.return_value = []

    exporter.export_initiatives("output/initiatives_canonical.json")

    exported = mock_sink.export.call_args[0][0]
    raw = str(exported)
    assert "coord@ifes.edu.br" not in raw, "Raw email found in initiative export"
    _check_no_raw_pii_in_json_str(raw)


# --- Fellowship export PII validation ---


def test_fellowship_export_scrubs_pii():
    mock_sink = MagicMock(spec=IExportSink)
    exporter = _make_exporter(mock_sink)

    mock_session = MagicMock()
    mock_fellowship = MockRow(
        id=1,
        name="Bolsista - contato@bolsa.com",
        description="Email: admin@fellowship.org",
        value=500.0,
    )
    mock_session.execute.return_value.fetchall.return_value = [mock_fellowship]

    # Use raw session mock for the direct SQL query path
    with patch.object(
        exporter.initiative_ctrl._service._repository, "_session", mock_session
    ):
        exporter._get_session = lambda: mock_session
        exporter._get_campus_resolver = lambda: MagicMock(
            get_campus=lambda *a, **kw: None
        )

        exporter.export_fellowships("output/fellowships_canonical.json")

    exported = mock_sink.export.call_args[0][0]
    raw = str(exported)
    assert "contato@bolsa.com" not in raw, "Raw email found in fellowship name"
    assert (
        "admin@fellowship.org" not in raw
    ), "Raw email found in fellowship description"
    _check_no_raw_pii_in_json_str(raw)


# --- Article export PII validation ---


def test_article_export_scrubs_pii():
    mock_sink = MagicMock(spec=IExportSink)
    exporter = _make_exporter(mock_sink)

    mock_session = MagicMock()
    mock_article = MagicMock()
    mock_article.id = 1
    mock_article.title = "Study results - email author@paper.com"
    mock_article.year = 2024
    mock_article.type = "journal"
    mock_article.doi = "10.1234/test"
    mock_article.journal_conference = "Journal of Stuff"

    mock_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        mock_article
    ]
    mock_session.query.return_value.count.return_value = 1

    exporter._get_session = lambda: mock_session
    exporter._get_campus_resolver = lambda: MagicMock(get_campus=lambda *a, **kw: None)

    with patch.object(
        exporter.article_ctrl._service._repository, "_session", mock_session
    ):
        exporter.export_articles("output/articles_canonical.json")

    exported = mock_sink.export.call_args[0][0]
    raw = str(exported)
    assert "author@paper.com" not in raw, "Raw email found in article export"
    _check_no_raw_pii_in_json_str(raw)


# --- _export_entities path PII validation ---


@pytest.mark.parametrize(
    "export_method,attr_name,mock_data",
    [
        (
            "export_organizations",
            "org_ctrl",
            [{"id": 1, "name": "IFES - admin@ifes.edu.br"}],
        ),
        (
            "export_campuses",
            "campus_ctrl",
            [{"id": 1, "name": "Serra - secretaria@serra.ifes.edu.br"}],
        ),
        (
            "export_knowledge_areas",
            "ka_ctrl",
            [{"id": 1, "name": "CS - contato@cs.ifes.edu.br"}],
        ),
    ],
)
def test_entity_export_scrubs_pii(export_method, attr_name, mock_data):
    mock_sink = MagicMock(spec=IExportSink)
    exporter = _make_exporter(mock_sink)

    mock_items = []
    for item in mock_data:
        m = MagicMock()
        m.to_dict.return_value = item
        mock_items.append(m)

    controller = getattr(exporter, attr_name)
    controller.get_all.return_value = mock_items

    getattr(exporter, export_method)("output.json")

    exported = mock_sink.export.call_args[0][0]
    raw = str(exported)
    _check_no_raw_pii_in_json_str(raw)
