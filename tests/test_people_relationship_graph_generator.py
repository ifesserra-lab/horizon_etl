import json

from src.core.logic.people_relationship_graph_generator import (
    PeopleRelationshipGraphGenerator,
)


def _write_sample_inputs(tmp_path, include_null_person: bool = False):
    researchers = [
        {
            "id": 1,
            "name": "Ana",
            "classification": "researcher",
            "classification_confidence": "high",
            "was_student": False,
            "was_staff": True,
            "campus": {"id": 10, "name": "Serra"},
            "articles": [
                {
                    "id": 501,
                    "title": "Article Shared",
                    "year": 2022,
                    "type": "JOURNAL",
                }
            ],
        },
        {
            "id": 2,
            "name": "Bruno",
            "classification": "student",
            "classification_confidence": "high",
            "was_student": True,
            "was_staff": False,
            "campus": {"id": 10, "name": "Serra"},
            "articles": [
                {
                    "id": 501,
                    "title": "Article Shared",
                    "year": 2022,
                    "type": "JOURNAL",
                }
            ],
        },
        {
            "id": 3,
            "name": "Carla",
            "classification": "student",
            "classification_confidence": "medium",
            "was_student": True,
            "was_staff": False,
            "campus": None,
            "articles": [],
        },
    ]

    if include_null_person:
        researchers.append(
            {
                "id": 4,
                "name": "Dora",
                "classification": None,
                "classification_confidence": "low",
                "was_student": False,
                "was_staff": False,
                "campus": None,
            }
        )

    fixtures = {
        "researchers.json": researchers,
        "initiatives.json": [
            {
                "id": 100,
                "name": "Projeto 1",
                "initiative_type": {"name": "Research Project"},
                "team": [
                    {"person_id": 1, "person_name": "Ana"},
                    {"person_id": 2, "person_name": "Bruno"},
                    {"person_id": 3, "person_name": "Carla"},
                ],
            }
        ],
        "research_groups.json": [
            {
                "id": 200,
                "name": "Grupo 1",
                "short_name": "G1",
                "campus": {"id": 10, "name": "Serra"},
                "members": [
                    {
                        "id": 1,
                        "name": "Ana",
                        "start_date": "2020-01-01",
                        "end_date": "2022-12-31",
                    },
                    {
                        "id": 2,
                        "name": "Bruno",
                        "start_date": "2021-01-01",
                        "end_date": "2022-12-31",
                    },
                    *(
                        [
                            {
                                "id": 4,
                                "name": "Dora",
                                "start_date": "2025-01-01",
                                "end_date": None,
                            }
                        ]
                        if include_null_person
                        else []
                    ),
                ],
            }
        ],
        "advisorships.json": [
            {
                "id": 300,
                "name": "Projeto com bolsa",
                "advisorships": [
                    {
                        "id": 400,
                        "person_id": 3,
                        "person_name": "Carla",
                        "supervisor_id": 1,
                        "supervisor_name": "Ana",
                    }
                ],
            }
        ],
    }

    paths = {}
    for filename, payload in fixtures.items():
        path = tmp_path / filename
        path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        paths[filename] = path

    return paths


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_people_relationship_graph_generator_aggregates_relationships(tmp_path):
    paths = _write_sample_inputs(tmp_path)
    output_path = tmp_path / "people_relationship_graph.json"

    generator = PeopleRelationshipGraphGenerator()
    result = generator.generate(
        researchers_path=str(paths["researchers.json"]),
        initiatives_path=str(paths["initiatives.json"]),
        research_groups_path=str(paths["research_groups.json"]),
        advisorships_path=str(paths["advisorships.json"]),
        output_path=str(output_path),
    )

    assert output_path.exists()
    assert result["graph_stats"]["nodes"] == 3
    assert result["graph_stats"]["edges"] == 3
    assert result["graph_stats"]["relation_event_totals"] == {
        "article": 1,
        "initiative": 3,
        "research_group": 1,
        "advisorship": 1,
    }
    assert result["graph_stats"]["campus_distribution"] == {
        "Serra": 2,
        "null": 1,
    }
    assert "_complex_network_summary" not in result["graph"]["graph"]

    nodes_by_id = {node["id"]: node for node in result["graph"]["nodes"]}
    assert nodes_by_id[1]["weighted_degree"] == 5
    assert nodes_by_id[1]["campus_id"] == 10
    assert nodes_by_id[2]["classification"] == "student"
    assert nodes_by_id[3]["campus_name"] is None
    assert result["graph_stats"]["top_people_by_weighted_degree"][0]["campus_name"] == (
        "Serra"
    )
    assert set(result["metadata"]["relation_types"]) == {
        "article",
        "initiative",
        "research_group",
        "advisorship",
    }

    edges_by_pair = {
        tuple(sorted((edge["source"], edge["target"]))): edge
        for edge in result["graph"]["edges"]
    }

    assert edges_by_pair[(1, 2)]["weight"] == 3
    assert edges_by_pair[(1, 2)]["article_count"] == 1
    assert edges_by_pair[(1, 2)]["initiative_count"] == 1
    assert edges_by_pair[(1, 2)]["research_group_count"] == 1
    assert edges_by_pair[(1, 2)]["advisorship_count"] == 0
    assert edges_by_pair[(1, 2)]["relation_types"] == [
        "initiative",
        "article",
        "research_group",
    ]

    assert edges_by_pair[(1, 3)]["weight"] == 2
    assert edges_by_pair[(1, 3)]["article_count"] == 0
    assert edges_by_pair[(1, 3)]["initiative_count"] == 1
    assert edges_by_pair[(1, 3)]["research_group_count"] == 0
    assert edges_by_pair[(1, 3)]["advisorship_count"] == 1
    assert edges_by_pair[(1, 3)]["relation_types"] == [
        "initiative",
        "advisorship",
    ]

    assert edges_by_pair[(2, 3)]["weight"] == 1
    assert edges_by_pair[(2, 3)]["article_count"] == 0
    assert edges_by_pair[(2, 3)]["relation_types"] == ["initiative"]


def test_people_relationship_graph_generator_exports_filtered_graph_files(tmp_path):
    paths = _write_sample_inputs(tmp_path, include_null_person=True)
    output_dir = tmp_path / "exports"

    generator = PeopleRelationshipGraphGenerator()
    result = generator.generate_all(
        researchers_path=str(paths["researchers.json"]),
        initiatives_path=str(paths["initiatives.json"]),
        research_groups_path=str(paths["research_groups.json"]),
        advisorships_path=str(paths["advisorships.json"]),
        output_dir=str(output_dir),
    )

    full_graph_path = output_dir / "people_relationship_graph.json"
    collaboration_graph_path = output_dir / "people_collaboration_graph.json"
    students_graph_path = output_dir / "students_relationship_graph.json"
    researchers_graph_path = output_dir / "researchers_only_relationship_graph.json"
    outside_graph_path = output_dir / "outside_ifes_relationship_graph.json"
    null_graph_path = output_dir / "null_researchers_relationship_graph.json"
    students_collaboration_graph_path = output_dir / "students_collaboration_graph.json"
    researchers_collaboration_graph_path = (
        output_dir / "researchers_only_collaboration_graph.json"
    )
    outside_collaboration_graph_path = (
        output_dir / "outside_ifes_collaboration_graph.json"
    )
    null_collaboration_graph_path = (
        output_dir / "null_researchers_collaboration_graph.json"
    )
    research_group_manifest_path = (
        output_dir / "research_group_relationship_graphs_manifest.json"
    )
    research_group_membership_manifest_path = (
        output_dir / "research_group_membership_graphs_manifest.json"
    )
    research_group_graph_path = (
        output_dir
        / "research_group_relationship_graphs"
        / "research_group_200_relationship_graph.json"
    )
    research_group_membership_graph_path = (
        output_dir
        / "research_group_membership_graphs"
        / "research_group_200_membership_graph.json"
    )

    assert full_graph_path.exists()
    assert collaboration_graph_path.exists()
    assert students_graph_path.exists()
    assert researchers_graph_path.exists()
    assert outside_graph_path.exists()
    assert null_graph_path.exists()
    assert students_collaboration_graph_path.exists()
    assert researchers_collaboration_graph_path.exists()
    assert outside_collaboration_graph_path.exists()
    assert null_collaboration_graph_path.exists()
    assert research_group_manifest_path.exists()
    assert research_group_membership_manifest_path.exists()
    assert research_group_graph_path.exists()
    assert research_group_membership_graph_path.exists()

    assert result["full_graph_path"] == str(full_graph_path)
    assert result["collaboration_graph_path"] == str(collaboration_graph_path)
    assert len(result["classification_exports"]) == 4
    assert len(result["collaboration_classification_exports"]) == 4
    assert result["research_group_exports"]["manifest_path"] == str(
        research_group_manifest_path
    )
    assert result["research_group_membership_exports"]["manifest_path"] == str(
        research_group_membership_manifest_path
    )

    full_graph = _load_json(full_graph_path)
    collaboration_graph = _load_json(collaboration_graph_path)
    students_graph = _load_json(students_graph_path)
    researchers_graph = _load_json(researchers_graph_path)
    outside_graph = _load_json(outside_graph_path)
    null_graph = _load_json(null_graph_path)
    students_collaboration_graph = _load_json(students_collaboration_graph_path)
    researchers_collaboration_graph = _load_json(
        researchers_collaboration_graph_path
    )
    outside_collaboration_graph = _load_json(outside_collaboration_graph_path)
    null_collaboration_graph = _load_json(null_collaboration_graph_path)
    research_group_manifest = _load_json(research_group_manifest_path)
    research_group_membership_manifest = _load_json(
        research_group_membership_manifest_path
    )
    research_group_graph = _load_json(research_group_graph_path)
    research_group_membership_graph = _load_json(research_group_membership_graph_path)

    assert full_graph["metadata"]["scope"] == {"type": "full"}
    assert full_graph["graph_stats"]["nodes"] == 4
    assert full_graph["graph_stats"]["isolated_nodes"] == 1
    assert full_graph["graph_stats"]["complex_network_metrics"]["density"] == 0.5
    assert full_graph["graph_stats"]["complex_network_metrics"]["community_count"] == 2
    assert full_graph["graph_stats"]["complex_network_metrics"]["bridge_edge_count"] == 0
    assert full_graph["graph_stats"]["campus_distribution"] == {
        "Serra": 2,
        "null": 2,
    }
    assert collaboration_graph["metadata"]["scope"] == {
        "type": "full",
        "graph_type": "collaboration",
    }
    assert collaboration_graph["graph_stats"]["nodes"] == 4
    assert collaboration_graph["graph_stats"]["edges"] == 3
    assert collaboration_graph["graph_stats"]["relation_event_totals"] == {
        "orientation": 1,
        "project": 3,
        "article": 1,
    }
    assert collaboration_graph["graph_stats"]["campus_distribution"] == {
        "Serra": 2,
        "null": 2,
    }
    assert collaboration_graph["graph_stats"]["complex_network_metrics"]["density"] == 0.5
    assert (
        collaboration_graph["graph_stats"]["complex_network_metrics"]["community_count"]
        == 2
    )

    assert students_graph["metadata"]["scope"] == {
        "type": "classification",
        "classification": "student",
    }
    assert students_graph["graph_stats"]["nodes"] == 2
    assert students_graph["graph_stats"]["edges"] == 1
    assert students_graph["graph_stats"]["classification_distribution"] == {
        "student": 2
    }
    assert students_graph["graph_stats"]["campus_distribution"] == {
        "Serra": 1,
        "null": 1,
    }
    assert students_graph["graph_stats"]["complex_network_metrics"]["density"] == 1.0

    assert researchers_graph["metadata"]["scope"] == {
        "type": "classification",
        "classification": "researcher",
    }
    assert researchers_graph["graph_stats"]["nodes"] == 1
    assert researchers_graph["graph_stats"]["edges"] == 0
    assert researchers_graph["graph_stats"]["campus_distribution"] == {"Serra": 1}

    assert outside_graph["metadata"]["scope"] == {
        "type": "classification",
        "classification": "outside_ifes",
    }
    assert outside_graph["graph_stats"]["nodes"] == 0
    assert outside_graph["graph_stats"]["edges"] == 0

    assert null_graph["metadata"]["scope"] == {
        "type": "classification",
        "classification": "null",
    }
    assert null_graph["graph_stats"]["nodes"] == 1
    assert null_graph["graph_stats"]["edges"] == 0
    assert null_graph["graph_stats"]["classification_distribution"] == {"null": 1}
    assert null_graph["graph_stats"]["campus_distribution"] == {"null": 1}
    assert students_collaboration_graph["metadata"]["scope"] == {
        "type": "classification",
        "graph_type": "collaboration",
        "classification": "student",
    }
    assert students_collaboration_graph["graph_stats"]["nodes"] == 2
    assert students_collaboration_graph["graph_stats"]["edges"] == 1
    assert students_collaboration_graph["graph_stats"][
        "classification_distribution"
    ] == {"student": 2}
    assert students_collaboration_graph["graph_stats"]["campus_distribution"] == {
        "Serra": 1,
        "null": 1,
    }
    assert (
        students_collaboration_graph["graph_stats"]["complex_network_metrics"][
            "density"
        ]
        == 1.0
    )

    assert researchers_collaboration_graph["metadata"]["scope"] == {
        "type": "classification",
        "graph_type": "collaboration",
        "classification": "researcher",
    }
    assert researchers_collaboration_graph["graph_stats"]["nodes"] == 1
    assert researchers_collaboration_graph["graph_stats"]["edges"] == 0
    assert researchers_collaboration_graph["graph_stats"]["campus_distribution"] == {
        "Serra": 1
    }

    assert outside_collaboration_graph["metadata"]["scope"] == {
        "type": "classification",
        "graph_type": "collaboration",
        "classification": "outside_ifes",
    }
    assert outside_collaboration_graph["graph_stats"]["nodes"] == 0
    assert outside_collaboration_graph["graph_stats"]["edges"] == 0

    assert null_collaboration_graph["metadata"]["scope"] == {
        "type": "classification",
        "graph_type": "collaboration",
        "classification": "null",
    }
    assert null_collaboration_graph["graph_stats"]["nodes"] == 1
    assert null_collaboration_graph["graph_stats"]["edges"] == 0
    assert null_collaboration_graph["graph_stats"]["classification_distribution"] == {
        "null": 1
    }
    assert null_collaboration_graph["graph_stats"]["campus_distribution"] == {
        "null": 1
    }

    assert research_group_manifest["metadata"]["scope"] == {
        "type": "research_group_manifest",
        "graph_type": "collaboration",
    }
    assert research_group_manifest["graphs"] == [
        {
            "id": 200,
            "name": "Grupo 1",
            "short_name": "G1",
            "campus_name": "Serra",
            "member_count": 3,
            "nodes": 3,
            "edges": 1,
            "path": (
                "research_group_relationship_graphs/"
                "research_group_200_relationship_graph.json"
            ),
        }
    ]
    assert research_group_membership_manifest["metadata"]["scope"] == {
        "type": "research_group_manifest",
        "graph_type": "membership",
    }
    assert research_group_membership_manifest["graphs"] == [
        {
            "id": 200,
            "name": "Grupo 1",
            "short_name": "G1",
            "campus_name": "Serra",
            "member_count": 3,
            "nodes": 4,
            "edges": 3,
            "path": (
                "research_group_membership_graphs/"
                "research_group_200_membership_graph.json"
            ),
        }
    ]

    assert research_group_graph["metadata"]["scope"] == {
        "type": "research_group",
        "graph_type": "collaboration",
        "research_group": {
            "id": 200,
            "name": "Grupo 1",
            "short_name": "G1",
            "campus_name": "Serra",
            "member_count": 3,
        },
    }
    assert research_group_graph["graph_stats"]["nodes"] == 3
    assert research_group_graph["graph_stats"]["edges"] == 1
    assert research_group_graph["graph_stats"]["relation_event_totals"] == {
        "orientation": 0,
        "project": 1,
        "article": 1,
    }
    assert (
        research_group_graph["graph_stats"]["complex_network_metrics"]["density"]
        == 0.333333
    )
    assert research_group_graph["graph_stats"]["campus_distribution"] == {
        "Serra": 2,
        "null": 1,
    }
    nodes_by_id = {node["id"]: node for node in research_group_graph["graph"]["nodes"]}
    assert nodes_by_id[1]["node_type"] == "person"
    assert nodes_by_id[1]["campus_name"] == "Serra"
    assert nodes_by_id[4]["degree"] == 0
    assert nodes_by_id[1]["degree_centrality"] == 0.5
    assert nodes_by_id[1]["is_hub"] is True
    assert nodes_by_id[4]["community_id"] is not None
    collaboration_edges_by_pair = {
        tuple(sorted((edge["source"], edge["target"]))): edge
        for edge in research_group_graph["graph"]["edges"]
    }
    assert collaboration_edges_by_pair[(1, 2)]["weight"] == 2
    assert collaboration_edges_by_pair[(1, 2)]["project_count"] == 1
    assert collaboration_edges_by_pair[(1, 2)]["article_count"] == 1
    assert collaboration_edges_by_pair[(1, 2)]["orientation_count"] == 0
    assert collaboration_edges_by_pair[(1, 2)]["relation_types"] == [
        "project",
        "article",
    ]
    assert collaboration_edges_by_pair[(1, 2)]["is_bridge"] is True

    assert research_group_membership_graph["metadata"]["scope"] == {
        "type": "research_group",
        "graph_type": "membership",
        "research_group": {
            "id": 200,
            "name": "Grupo 1",
            "short_name": "G1",
            "campus_name": "Serra",
            "member_count": 3,
        },
    }
    assert research_group_membership_graph["graph_stats"]["nodes"] == 4
    assert research_group_membership_graph["graph_stats"]["edges"] == 3
    assert research_group_membership_graph["graph_stats"]["relation_event_totals"] == {
        "present_in": 3,
    }
    assert research_group_membership_graph["graph_stats"]["campus_distribution"] == {
        "Serra": 2,
        "null": 1,
    }
    membership_nodes_by_id = {
        node["id"]: node for node in research_group_membership_graph["graph"]["nodes"]
    }
    membership_edges = research_group_membership_graph["graph"]["edges"]
    group_node_id = "research_group:200"
    assert membership_nodes_by_id[group_node_id]["node_type"] == "research_group"
    assert membership_nodes_by_id[group_node_id]["campus_name"] == "Serra"
    assert membership_nodes_by_id[group_node_id]["member_count"] == 3
    assert membership_nodes_by_id[4]["degree"] == 1
    assert "complex_network_metrics" not in research_group_membership_graph["graph_stats"]
    assert len(membership_edges) == 3
    assert all(edge["target"] == group_node_id for edge in membership_edges)
    assert all(edge["relation_types"] == ["present_in"] for edge in membership_edges)
    assert all(edge["present_in_count"] == 1 for edge in membership_edges)


def test_people_relationship_graph_generator_keeps_group_only_members_as_isolated_nodes(
    tmp_path,
):
    paths = _write_sample_inputs(tmp_path)
    research_groups = _load_json(paths["research_groups.json"])
    research_groups[0]["members"].append(
        {
            "id": 99,
            "name": "Eva",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        }
    )
    paths["research_groups.json"].write_text(
        json.dumps(research_groups, ensure_ascii=False),
        encoding="utf-8",
    )

    output_path = tmp_path / "people_relationship_graph.json"
    generator = PeopleRelationshipGraphGenerator()
    result = generator.generate(
        researchers_path=str(paths["researchers.json"]),
        initiatives_path=str(paths["initiatives.json"]),
        research_groups_path=str(paths["research_groups.json"]),
        advisorships_path=str(paths["advisorships.json"]),
        output_path=str(output_path),
    )

    assert result["graph_stats"]["nodes"] == 4
    assert result["graph_stats"]["isolated_nodes"] == 1

    nodes_by_id = {node["id"]: node for node in result["graph"]["nodes"]}
    assert nodes_by_id[99]["name"] == "Eva"
    assert nodes_by_id[99]["classification"] is None
    assert nodes_by_id[99]["degree"] == 0
    assert nodes_by_id[99]["weighted_degree"] == 0
