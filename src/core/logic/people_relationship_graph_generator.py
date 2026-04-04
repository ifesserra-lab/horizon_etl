import json
import os
import warnings
from collections import Counter
from datetime import date, datetime, timezone
from itertools import combinations
from math import ceil, isnan
from typing import Any, Iterable, Optional

import networkx as nx
from loguru import logger
from networkx.algorithms import community as nx_community
from networkx.readwrite import json_graph


RELATION_DESCRIPTIONS = {
    "initiative": "People who appear together in the same initiative team.",
    "article": "People who are linked to the same article record.",
    "research_group": "People whose memberships in the same research group overlap in time.",
    "advisorship": "Supervisor and student connected by an advisorship.",
}

RESEARCH_GROUP_COLLABORATION_RELATION_DESCRIPTIONS = {
    "orientation": "Supervisor and student connected by an advisorship/orientation.",
    "project": "People who appear together in the same research project team.",
    "article": "People who are linked to the same article record.",
}

RESEARCH_GROUP_MEMBERSHIP_RELATION_DESCRIPTIONS = {
    "present_in": "Person is present in the research group node.",
}

CLASSIFICATION_GRAPH_EXPORTS: tuple[tuple[Optional[str], str], ...] = (
    ("student", "students_relationship_graph.json"),
    ("researcher", "researchers_only_relationship_graph.json"),
    ("outside_ifes", "outside_ifes_relationship_graph.json"),
    (None, "null_researchers_relationship_graph.json"),
)

COLLABORATION_CLASSIFICATION_GRAPH_EXPORTS: tuple[
    tuple[Optional[str], str], ...
] = (
    ("student", "students_collaboration_graph.json"),
    ("researcher", "researchers_only_collaboration_graph.json"),
    ("outside_ifes", "outside_ifes_collaboration_graph.json"),
    (None, "null_researchers_collaboration_graph.json"),
)

RESEARCH_GROUP_GRAPH_DIRECTORY = "research_group_relationship_graphs"
RESEARCH_GROUP_GRAPH_MANIFEST = "research_group_relationship_graphs_manifest.json"
RESEARCH_GROUP_MEMBERSHIP_GRAPH_DIRECTORY = "research_group_membership_graphs"
RESEARCH_GROUP_MEMBERSHIP_GRAPH_MANIFEST = (
    "research_group_membership_graphs_manifest.json"
)


class PeopleRelationshipGraphGenerator:
    def generate(
        self,
        researchers_path: str,
        initiatives_path: str,
        research_groups_path: str,
        advisorships_path: str,
        output_path: str,
    ) -> dict[str, Any]:
        logger.info("Generating People Relationship Graph to {}", output_path)

        sources, graph, _research_groups = self._build_graph_from_paths(
            researchers_path=researchers_path,
            initiatives_path=initiatives_path,
            research_groups_path=research_groups_path,
            advisorships_path=advisorships_path,
        )
        result = self._serialize_graph_result(graph, sources=sources)
        self._write_json(output_path, result)

        logger.info(
            "People Relationship Graph successfully generated at {} with {} nodes and {} edges",
            output_path,
            graph.number_of_nodes(),
            graph.number_of_edges(),
        )
        return result

    def generate_all(
        self,
        researchers_path: str,
        initiatives_path: str,
        research_groups_path: str,
        advisorships_path: str,
        output_dir: str,
    ) -> dict[str, Any]:
        logger.info(
            "Generating People Relationship Graph bundle into directory {}", output_dir
        )

        sources, graph, research_groups = self._build_graph_from_paths(
            researchers_path=researchers_path,
            initiatives_path=initiatives_path,
            research_groups_path=research_groups_path,
            advisorships_path=advisorships_path,
        )
        researchers = self._load_json(researchers_path)
        initiatives = self._load_json(initiatives_path)
        advisorship_projects = self._load_json(advisorships_path)

        full_output_path = os.path.join(output_dir, "people_relationship_graph.json")
        full_result = self._serialize_graph_result(graph, sources=sources)
        self._write_json(full_output_path, full_result)

        collaboration_graph = self._build_global_collaboration_graph(
            source_graph=graph,
            researchers=researchers,
            initiatives=initiatives,
            advisorship_projects=advisorship_projects,
        )
        collaboration_output_path = os.path.join(
            output_dir,
            "people_collaboration_graph.json",
        )
        collaboration_result = self._serialize_graph_result(
            collaboration_graph,
            sources=sources,
            scope={"type": "full", "graph_type": "collaboration"},
            relation_descriptions=RESEARCH_GROUP_COLLABORATION_RELATION_DESCRIPTIONS,
            weight_definition=(
                "Each edge weight equals the total number of collaboration "
                "evidences between two people. Every shared research project, "
                "shared article, and orientation adds 1 to the edge weight."
            ),
        )
        self._write_json(collaboration_output_path, collaboration_result)

        classification_exports = []
        for classification, filename in CLASSIFICATION_GRAPH_EXPORTS:
            filtered_graph = self._build_classification_subgraph(graph, classification)
            output_path = os.path.join(output_dir, filename)
            result = self._serialize_graph_result(
                filtered_graph,
                sources=sources,
                scope={
                    "type": "classification",
                    "classification": (
                        "null" if classification is None else classification
                    ),
                },
            )
            self._write_json(output_path, result)
            classification_exports.append(
                {
                    "classification": "null" if classification is None else classification,
                    "path": output_path,
                    "nodes": result["graph_stats"]["nodes"],
                    "edges": result["graph_stats"]["edges"],
                }
            )

        collaboration_classification_exports = []
        for classification, filename in COLLABORATION_CLASSIFICATION_GRAPH_EXPORTS:
            filtered_graph = self._build_classification_subgraph(
                collaboration_graph,
                classification,
            )
            output_path = os.path.join(output_dir, filename)
            result = self._serialize_graph_result(
                filtered_graph,
                sources=sources,
                scope={
                    "type": "classification",
                    "graph_type": "collaboration",
                    "classification": (
                        "null" if classification is None else classification
                    ),
                },
                relation_descriptions=RESEARCH_GROUP_COLLABORATION_RELATION_DESCRIPTIONS,
                weight_definition=(
                    "Each edge weight equals the total number of collaboration "
                    "evidences between two people. Every shared research project, "
                    "shared article, and orientation adds 1 to the edge weight."
                ),
            )
            self._write_json(output_path, result)
            collaboration_classification_exports.append(
                {
                    "classification": "null" if classification is None else classification,
                    "path": output_path,
                    "nodes": result["graph_stats"]["nodes"],
                    "edges": result["graph_stats"]["edges"],
                }
            )

        research_group_manifest = self._export_research_group_graphs(
            graph=graph,
            researchers=researchers,
            initiatives=initiatives,
            research_groups=research_groups,
            advisorship_projects=advisorship_projects,
            sources=sources,
            output_dir=output_dir,
        )

        logger.info(
            "People Relationship Graph bundle generated with {} relationship classification graphs, {} collaboration classification graphs, {} collaboration research-group graphs, and {} membership research-group graphs",
            len(classification_exports),
            len(collaboration_classification_exports),
            len(research_group_manifest["graphs"]),
            len(research_group_manifest["membership_graphs"]),
        )

        return {
            "full_graph_path": full_output_path,
            "collaboration_graph_path": collaboration_output_path,
            "classification_exports": classification_exports,
            "collaboration_classification_exports": collaboration_classification_exports,
            "research_group_exports": research_group_manifest,
            "research_group_membership_exports": research_group_manifest[
                "membership_manifest"
            ],
        }

    def _build_graph_from_paths(
        self,
        researchers_path: str,
        initiatives_path: str,
        research_groups_path: str,
        advisorships_path: str,
    ) -> tuple[dict[str, str], nx.Graph, list[dict[str, Any]]]:
        researchers = self._load_json(researchers_path)
        initiatives = self._load_json(initiatives_path)
        research_groups = self._load_json(research_groups_path)
        advisorship_projects = self._load_json(advisorships_path)

        graph = self._build_graph(
            researchers=researchers,
            initiatives=initiatives,
            research_groups=research_groups,
            advisorship_projects=advisorship_projects,
        )

        return (
            {
                "researchers": researchers_path,
                "initiatives": initiatives_path,
                "research_groups": research_groups_path,
                "advisorships": advisorships_path,
            },
            graph,
            research_groups,
        )

    def _build_graph(
        self,
        researchers: list[dict[str, Any]],
        initiatives: list[dict[str, Any]],
        research_groups: list[dict[str, Any]],
        advisorship_projects: list[dict[str, Any]],
    ) -> nx.Graph:
        graph = nx.Graph()

        self._add_researcher_nodes(graph, researchers)
        self._add_research_group_members(graph, research_groups)
        self._add_article_relationships(graph, researchers)
        self._add_initiative_relationships(graph, initiatives)
        self._add_research_group_overlap_relationships(graph, research_groups)
        self._add_advisorship_relationships(graph, advisorship_projects)
        self._finalize_graph(graph)

        return graph

    @staticmethod
    def _load_json(path: str) -> list[dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
        return payload if isinstance(payload, list) else []

    def _serialize_graph_result(
        self,
        graph: nx.Graph,
        sources: dict[str, str],
        scope: Optional[dict[str, Any]] = None,
        relation_descriptions: Optional[dict[str, str]] = None,
        weight_definition: Optional[str] = None,
        include_complex_network_analysis: bool = True,
    ) -> dict[str, Any]:
        relation_descriptions = relation_descriptions or RELATION_DESCRIPTIONS
        self._finalize_graph(
            graph,
            relation_descriptions=relation_descriptions,
            include_complex_network_analysis=include_complex_network_analysis,
        )
        graph_payload = json_graph.node_link_data(graph, edges="edges")
        return {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sources": sources,
                "scope": scope or {"type": "full"},
                "weight_definition": weight_definition
                or (
                    "Each edge weight equals the total number of relationship "
                    "evidences between two people. Every shared initiative, "
                    "shared article, overlapping research-group membership, and "
                    "advisorship adds 1 to the edge weight."
                ),
                "relation_types": relation_descriptions,
            },
            "graph_stats": self._build_graph_stats(
                graph,
                relation_descriptions=relation_descriptions,
                complex_network_summary=graph.graph.get("_complex_network_summary"),
            ),
            "graph": graph_payload,
        }

    def _write_json(self, output_path: str, payload: dict[str, Any]) -> None:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, ensure_ascii=False, indent=4)

    def _build_classification_subgraph(
        self, graph: nx.Graph, classification: Optional[str]
    ) -> nx.Graph:
        selected_node_ids = [
            node_id
            for node_id, attrs in graph.nodes(data=True)
            if attrs.get("classification") == classification
        ]
        subgraph = graph.subgraph(selected_node_ids).copy()
        self._finalize_graph(subgraph)
        return subgraph

    def _export_research_group_graphs(
        self,
        graph: nx.Graph,
        researchers: list[dict[str, Any]],
        initiatives: list[dict[str, Any]],
        research_groups: list[dict[str, Any]],
        advisorship_projects: list[dict[str, Any]],
        sources: dict[str, str],
        output_dir: str,
    ) -> dict[str, Any]:
        graphs_output_dir = os.path.join(output_dir, RESEARCH_GROUP_GRAPH_DIRECTORY)
        membership_graphs_output_dir = os.path.join(
            output_dir,
            RESEARCH_GROUP_MEMBERSHIP_GRAPH_DIRECTORY,
        )
        manifest_graphs = []
        membership_manifest_graphs = []

        for group in research_groups:
            group_id = group.get("id")
            if group_id is None:
                continue

            member_records = self._group_members_by_person(group)
            member_node_ids = sorted(member_records)

            collaboration_graph = self._build_research_group_collaboration_graph(
                source_graph=graph,
                researchers=researchers,
                initiatives=initiatives,
                advisorship_projects=advisorship_projects,
                member_records=member_records,
            )
            membership_graph = self._build_research_group_membership_graph(
                source_graph=graph,
                group=group,
                member_records=member_records,
            )

            collaboration_output_path = os.path.join(
                graphs_output_dir,
                f"research_group_{group_id}_relationship_graph.json",
            )
            collaboration_result = self._serialize_graph_result(
                collaboration_graph,
                sources=sources,
                scope={
                    "type": "research_group",
                    "graph_type": "collaboration",
                    "research_group": {
                        "id": group_id,
                        "name": group.get("name"),
                        "short_name": group.get("short_name"),
                        "campus_name": self._extract_campus_name(group.get("campus")),
                        "member_count": len(member_node_ids),
                    },
                },
                relation_descriptions=RESEARCH_GROUP_COLLABORATION_RELATION_DESCRIPTIONS,
                weight_definition=(
                    "Each edge weight equals the total number of collaboration "
                    "evidences between two people inside the research group. "
                    "Every shared research project, shared article, and "
                    "orientation adds 1 to the edge weight."
                ),
            )
            self._write_json(collaboration_output_path, collaboration_result)

            membership_output_path = os.path.join(
                membership_graphs_output_dir,
                f"research_group_{group_id}_membership_graph.json",
            )
            membership_result = self._serialize_graph_result(
                membership_graph,
                sources=sources,
                scope={
                    "type": "research_group",
                    "graph_type": "membership",
                    "research_group": {
                        "id": group_id,
                        "name": group.get("name"),
                        "short_name": group.get("short_name"),
                        "campus_name": self._extract_campus_name(group.get("campus")),
                        "member_count": len(member_node_ids),
                    },
                },
                relation_descriptions=RESEARCH_GROUP_MEMBERSHIP_RELATION_DESCRIPTIONS,
                weight_definition=(
                    "Each edge represents one present_in relationship from a "
                    "person node to the research group node."
                ),
                include_complex_network_analysis=False,
            )
            self._write_json(membership_output_path, membership_result)

            manifest_graphs.append(
                {
                    "id": group_id,
                    "name": group.get("name"),
                    "short_name": group.get("short_name"),
                    "campus_name": self._extract_campus_name(group.get("campus")),
                    "member_count": len(member_node_ids),
                    "nodes": collaboration_result["graph_stats"]["nodes"],
                    "edges": collaboration_result["graph_stats"]["edges"],
                    "path": os.path.relpath(collaboration_output_path, output_dir),
                }
            )
            membership_manifest_graphs.append(
                {
                    "id": group_id,
                    "name": group.get("name"),
                    "short_name": group.get("short_name"),
                    "campus_name": self._extract_campus_name(group.get("campus")),
                    "member_count": len(member_node_ids),
                    "nodes": membership_result["graph_stats"]["nodes"],
                    "edges": membership_result["graph_stats"]["edges"],
                    "path": os.path.relpath(membership_output_path, output_dir),
                }
            )

        manifest_payload = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "scope": {
                    "type": "research_group_manifest",
                    "graph_type": "collaboration",
                },
                "graphs_directory": RESEARCH_GROUP_GRAPH_DIRECTORY,
            },
            "graphs": manifest_graphs,
        }
        manifest_path = os.path.join(output_dir, RESEARCH_GROUP_GRAPH_MANIFEST)
        self._write_json(manifest_path, manifest_payload)

        membership_manifest_payload = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "scope": {
                    "type": "research_group_manifest",
                    "graph_type": "membership",
                },
                "graphs_directory": RESEARCH_GROUP_MEMBERSHIP_GRAPH_DIRECTORY,
            },
            "graphs": membership_manifest_graphs,
        }
        membership_manifest_path = os.path.join(
            output_dir,
            RESEARCH_GROUP_MEMBERSHIP_GRAPH_MANIFEST,
        )
        self._write_json(membership_manifest_path, membership_manifest_payload)

        return {
            "manifest_path": manifest_path,
            "graphs_directory": graphs_output_dir,
            "graphs": manifest_graphs,
            "membership_manifest": {
                "manifest_path": membership_manifest_path,
                "graphs_directory": membership_graphs_output_dir,
                "graphs": membership_manifest_graphs,
            },
            "membership_graphs": membership_manifest_graphs,
        }

    def _add_researcher_nodes(
        self, graph: nx.Graph, researchers: list[dict[str, Any]]
    ) -> None:
        for researcher in researchers:
            person_id = self._normalize_person_id(researcher.get("id"))
            if person_id is None:
                continue
            graph.add_node(
                person_id,
                name=researcher.get("name"),
                node_type="person",
                classification=researcher.get("classification"),
                classification_confidence=researcher.get(
                    "classification_confidence"
                ),
                was_student=bool(researcher.get("was_student")),
                was_staff=bool(researcher.get("was_staff")),
                campus_id=self._extract_campus_id(researcher.get("campus")),
                campus_name=self._extract_campus_name(researcher.get("campus")),
            )

    def _add_research_group_members(
        self,
        graph: nx.Graph,
        research_groups: list[dict[str, Any]],
    ) -> None:
        for group in research_groups:
            members = group.get("members") or []
            participants = self._unique_people(
                (
                    member.get("id"),
                    member.get("name"),
                )
                for member in members
            )
            for person_id, person_name in participants.values():
                self._ensure_person_node(graph, person_id, person_name)

    def _add_article_relationships(
        self,
        graph: nx.Graph,
        researchers: list[dict[str, Any]],
    ) -> None:
        article_to_people: dict[int, set[int]] = {}

        for researcher in researchers:
            person_id = self._normalize_person_id(researcher.get("id"))
            if person_id is None:
                continue

            article_ids = {
                article_id
                for article_id in (
                    self._normalize_person_id(article.get("id"))
                    for article in (researcher.get("articles") or [])
                    if isinstance(article, dict)
                )
                if article_id is not None
            }
            for article_id in article_ids:
                article_to_people.setdefault(article_id, set()).add(person_id)

        for people in article_to_people.values():
            for source_id, target_id in combinations(sorted(people), 2):
                self._increment_edge(graph, source_id, target_id, "article")

    def _add_initiative_relationships(
        self,
        graph: nx.Graph,
        initiatives: list[dict[str, Any]],
    ) -> None:
        for initiative in initiatives:
            members = initiative.get("team") or []
            participants = self._unique_people(
                (
                    member.get("person_id"),
                    member.get("person_name"),
                )
                for member in members
            )
            for person_id, person_name in participants.values():
                self._ensure_person_node(graph, person_id, person_name)

            for source_id, target_id in combinations(sorted(participants.keys()), 2):
                self._increment_edge(graph, source_id, target_id, "initiative")

    def _add_research_group_overlap_relationships(
        self,
        graph: nx.Graph,
        research_groups: list[dict[str, Any]],
    ) -> None:
        for group in research_groups:
            memberships_by_person: dict[int, list[tuple[Optional[date], Optional[date]]]] = {}

            for member in group.get("members") or []:
                person_id = self._normalize_person_id(member.get("id"))
                if person_id is None:
                    continue
                interval = self._normalize_membership_interval(member)
                memberships_by_person.setdefault(person_id, []).append(interval)

            for source_id, target_id in combinations(sorted(memberships_by_person), 2):
                source_intervals = memberships_by_person[source_id]
                target_intervals = memberships_by_person[target_id]
                if any(
                    self._intervals_overlap(source_interval, target_interval)
                    for source_interval in source_intervals
                    for target_interval in target_intervals
                ):
                    self._increment_edge(graph, source_id, target_id, "research_group")

    def _add_advisorship_relationships(
        self,
        graph: nx.Graph,
        advisorship_projects: list[dict[str, Any]],
    ) -> None:
        for project in advisorship_projects:
            for advisorship in project.get("advisorships") or []:
                supervisor_id = self._normalize_person_id(
                    advisorship.get("supervisor_id")
                )
                person_id = self._normalize_person_id(advisorship.get("person_id"))
                if (
                    supervisor_id is None
                    or person_id is None
                    or supervisor_id == person_id
                ):
                    continue

                self._ensure_person_node(
                    graph,
                    supervisor_id,
                    advisorship.get("supervisor_name"),
                )
                self._ensure_person_node(
                    graph,
                    person_id,
                    advisorship.get("person_name"),
                )
                self._increment_edge(graph, supervisor_id, person_id, "advisorship")

    def _finalize_graph(
        self,
        graph: nx.Graph,
        relation_descriptions: Optional[dict[str, str]] = None,
        include_complex_network_analysis: bool = False,
    ) -> None:
        relation_descriptions = relation_descriptions or RELATION_DESCRIPTIONS
        weighted_degrees = dict(graph.degree(weight="weight"))
        plain_degrees = dict(graph.degree())

        for node_id, attrs in graph.nodes(data=True):
            attrs["degree"] = plain_degrees.get(node_id, 0)
            attrs["weighted_degree"] = weighted_degrees.get(node_id, 0)
            if attrs.get("classification") is None:
                attrs["classification"] = None

        for _source_id, _target_id, attrs in graph.edges(data=True):
            for relation_type in relation_descriptions:
                attrs.setdefault(f"{relation_type}_count", 0)
            attrs["relation_types"] = [
                relation_type
                for relation_type in relation_descriptions
                if attrs.get(f"{relation_type}_count", 0) > 0
            ]

        if include_complex_network_analysis:
            graph.graph["_complex_network_summary"] = (
                self._annotate_complex_network_analysis(graph)
            )
        else:
            graph.graph.pop("_complex_network_summary", None)

    def _build_graph_stats(
        self,
        graph: nx.Graph,
        relation_descriptions: Optional[dict[str, str]] = None,
        complex_network_summary: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        relation_descriptions = relation_descriptions or RELATION_DESCRIPTIONS
        if graph.is_directed():
            components = list(nx.weakly_connected_components(graph))
        else:
            components = list(nx.connected_components(graph))
        isolated_nodes = list(nx.isolates(graph))
        weighted_degrees = dict(graph.degree(weight="weight"))
        relation_event_totals = self._sum_relation_event_totals(
            graph,
            relation_descriptions=relation_descriptions,
        )

        classification_distribution: Counter[str] = Counter()
        campus_distribution: Counter[str] = Counter()
        for _node_id, attrs in graph.nodes(data=True):
            if attrs.get("node_type", "person") != "person":
                continue
            classification_key = attrs.get("classification")
            classification_distribution[
                "null" if classification_key is None else str(classification_key)
            ] += 1
            campus_key = attrs.get("campus_name")
            campus_distribution["null" if campus_key is None else str(campus_key)] += 1

        top_people = []
        for node_id, weighted_degree in sorted(
            (
                (node_id, degree)
                for node_id, degree in weighted_degrees.items()
                if graph.nodes[node_id].get("node_type", "person") == "person"
            ),
            key=lambda item: (-item[1], str(item[0])),
        )[:20]:
            attrs = graph.nodes[node_id]
            top_people.append(
                {
                    "id": node_id,
                    "name": attrs.get("name"),
                    "classification": attrs.get("classification"),
                    "campus_name": attrs.get("campus_name"),
                    "weighted_degree": weighted_degree,
                    "degree": attrs.get("degree", 0),
                }
            )

        edge_relation_presence = {
            relation_type: sum(
                1
                for _source_id, _target_id, attrs in graph.edges(data=True)
                if attrs.get(f"{relation_type}_count", 0) > 0
            )
            for relation_type in relation_descriptions
        }

        stats = {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "isolated_nodes": len(isolated_nodes),
            "connected_components": len(components),
            "largest_component_size": max(
                (len(component) for component in components), default=0
            ),
            "relation_event_totals": relation_event_totals,
            "edge_relation_presence": edge_relation_presence,
            "classification_distribution": dict(classification_distribution),
            "campus_distribution": dict(campus_distribution),
            "top_people_by_weighted_degree": top_people,
        }

        if complex_network_summary is not None:
            stats["complex_network_metrics"] = complex_network_summary["metrics"]
            stats["top_hubs_by_degree_centrality"] = complex_network_summary[
                "top_hubs"
            ]
            stats["top_brokers_by_betweenness"] = complex_network_summary[
                "top_brokers"
            ]
            stats["communities"] = complex_network_summary["communities"]

        return stats

    def _sum_relation_event_totals(
        self,
        graph: nx.Graph,
        relation_descriptions: Optional[dict[str, str]] = None,
    ) -> dict[str, int]:
        relation_descriptions = relation_descriptions or RELATION_DESCRIPTIONS
        totals = {relation_type: 0 for relation_type in relation_descriptions}
        for _source_id, _target_id, attrs in graph.edges(data=True):
            for relation_type in relation_descriptions:
                totals[relation_type] += int(attrs.get(f"{relation_type}_count", 0))
        return totals

    def _annotate_complex_network_analysis(
        self,
        graph: nx.Graph,
    ) -> dict[str, Any]:
        if graph.is_directed():
            return {
                "metrics": {
                    "density": round(nx.density(graph), 6) if graph.number_of_nodes() else 0.0,
                    "analysis_scope": "skipped_for_directed_graph",
                },
                "top_hubs": [],
                "top_brokers": [],
                "communities": [],
            }

        person_node_ids = [
            node_id
            for node_id, attrs in graph.nodes(data=True)
            if attrs.get("node_type", "person") == "person"
        ]
        analysis_graph = graph.subgraph(person_node_ids).copy()

        if analysis_graph.number_of_nodes() == 0:
            return {
                "metrics": {
                    "density": 0.0,
                    "average_clustering": 0.0,
                    "transitivity": 0.0,
                    "assortativity_by_classification": None,
                    "community_count": 0,
                    "largest_community_size": 0,
                    "modularity": None,
                    "hub_count": 0,
                    "articulation_point_count": 0,
                    "bridge_edge_count": 0,
                    "betweenness_mode": "not_applicable",
                },
                "top_hubs": [],
                "top_brokers": [],
                "communities": [],
            }

        degree_centrality = nx.degree_centrality(analysis_graph)
        clustering = nx.clustering(analysis_graph, weight=None)
        articulation_points = set(nx.articulation_points(analysis_graph))
        bridges = {
            frozenset((source_id, target_id))
            for source_id, target_id in nx.bridges(analysis_graph)
        }
        betweenness_centrality, betweenness_mode = self._compute_betweenness_centrality(
            analysis_graph
        )
        communities, community_mode = self._compute_graph_communities(analysis_graph)
        community_assignments = self._build_community_assignments(communities)

        for node_id in analysis_graph.nodes():
            graph.nodes[node_id]["degree_centrality"] = round(
                degree_centrality.get(node_id, 0.0),
                6,
            )
            graph.nodes[node_id]["betweenness_centrality"] = round(
                betweenness_centrality.get(node_id, 0.0),
                6,
            )
            graph.nodes[node_id]["clustering_coefficient"] = round(
                clustering.get(node_id, 0.0),
                6,
            )
            graph.nodes[node_id]["community_id"] = community_assignments.get(node_id)
            graph.nodes[node_id]["is_articulation_point"] = node_id in articulation_points
            graph.nodes[node_id]["is_hub"] = False

        for source_id, target_id in graph.edges():
            graph[source_id][target_id]["is_bridge"] = (
                frozenset((source_id, target_id)) in bridges
            )

        top_hub_candidates = [
            node_id
            for node_id in analysis_graph.nodes()
            if graph.nodes[node_id].get("degree", 0) > 0
        ]
        hub_count = 0
        if top_hub_candidates:
            hub_count = min(
                len(top_hub_candidates),
                max(1, ceil(len(top_hub_candidates) * 0.05)),
            )
            ranked_hubs = sorted(
                top_hub_candidates,
                key=lambda node_id: (
                    -degree_centrality.get(node_id, 0.0),
                    -graph.nodes[node_id].get("weighted_degree", 0),
                    str(node_id),
                ),
            )
            for node_id in ranked_hubs[:hub_count]:
                graph.nodes[node_id]["is_hub"] = True

        assortativity = self._safe_assortativity_by_classification(analysis_graph)
        modularity = self._safe_modularity(analysis_graph, communities)
        community_sizes = [
            {
                "community_id": community_id,
                "size": len(community_nodes),
            }
            for community_id, community_nodes in enumerate(communities)
        ]

        top_hubs = self._rank_nodes_for_complex_analysis(
            graph=graph,
            node_ids=analysis_graph.nodes(),
            score_lookup=degree_centrality,
            score_key="degree_centrality",
        )
        top_brokers = self._rank_nodes_for_complex_analysis(
            graph=graph,
            node_ids=analysis_graph.nodes(),
            score_lookup=betweenness_centrality,
            score_key="betweenness_centrality",
        )

        return {
            "metrics": {
                "density": round(nx.density(analysis_graph), 6),
                "average_clustering": round(
                    nx.average_clustering(analysis_graph),
                    6,
                ),
                "transitivity": round(nx.transitivity(analysis_graph), 6),
                "assortativity_by_classification": assortativity,
                "community_count": len(communities),
                "largest_community_size": max(
                    (len(community_nodes) for community_nodes in communities),
                    default=0,
                ),
                "community_detection_mode": community_mode,
                "modularity": modularity,
                "hub_count": hub_count,
                "articulation_point_count": len(articulation_points),
                "bridge_edge_count": len(bridges),
                "betweenness_mode": betweenness_mode,
            },
            "top_hubs": top_hubs,
            "top_brokers": top_brokers,
            "communities": community_sizes[:20],
        }

    def _compute_betweenness_centrality(
        self,
        graph: nx.Graph,
    ) -> tuple[dict[Any, float], str]:
        if graph.number_of_edges() == 0:
            return ({node_id: 0.0 for node_id in graph.nodes()}, "not_applicable")

        if graph.number_of_nodes() <= 200 and graph.number_of_edges() <= 2000:
            return (
                nx.betweenness_centrality(graph, weight=None),
                "exact",
            )

        sample_k = min(graph.number_of_nodes(), 64)
        return (
            nx.betweenness_centrality(graph, k=sample_k, weight=None, seed=42),
            f"sampled_k_{sample_k}",
        )

    def _compute_graph_communities(
        self,
        graph: nx.Graph,
    ) -> tuple[list[set[Any]], str]:
        if graph.number_of_nodes() == 0:
            return [], "not_applicable"
        if graph.number_of_edges() == 0:
            return [{node_id} for node_id in graph.nodes()], "isolated_nodes"

        if graph.number_of_nodes() <= 2000 and graph.number_of_edges() <= 20000:
            communities = list(
                nx_community.greedy_modularity_communities(graph, weight="weight")
            )
            return self._normalize_communities(communities), "greedy_modularity"

        communities = list(
            nx_community.asyn_lpa_communities(graph, weight="weight", seed=42)
        )
        return self._normalize_communities(communities), "label_propagation"

    def _normalize_communities(
        self,
        communities: Iterable[Iterable[Any]],
    ) -> list[set[Any]]:
        normalized = [set(community_nodes) for community_nodes in communities]
        return sorted(
            normalized,
            key=lambda community_nodes: (
                -len(community_nodes),
                min((str(node_id) for node_id in community_nodes), default=""),
            ),
        )

    def _build_community_assignments(
        self,
        communities: list[set[Any]],
    ) -> dict[Any, int]:
        assignments: dict[Any, int] = {}
        for community_id, community_nodes in enumerate(communities):
            for node_id in community_nodes:
                assignments[node_id] = community_id
        return assignments

    def _rank_nodes_for_complex_analysis(
        self,
        graph: nx.Graph,
        node_ids: Iterable[Any],
        score_lookup: dict[Any, float],
        score_key: str,
    ) -> list[dict[str, Any]]:
        ranked_nodes = sorted(
            node_ids,
            key=lambda node_id: (
                -score_lookup.get(node_id, 0.0),
                -graph.nodes[node_id].get("weighted_degree", 0),
                str(node_id),
            ),
        )
        return [
            {
                "id": node_id,
                "name": graph.nodes[node_id].get("name"),
                "classification": graph.nodes[node_id].get("classification"),
                "campus_name": graph.nodes[node_id].get("campus_name"),
                score_key: round(score_lookup.get(node_id, 0.0), 6),
                "weighted_degree": graph.nodes[node_id].get("weighted_degree", 0),
                "degree": graph.nodes[node_id].get("degree", 0),
            }
            for node_id in ranked_nodes[:20]
        ]

    def _safe_assortativity_by_classification(
        self,
        graph: nx.Graph,
    ) -> Optional[float]:
        if graph.number_of_edges() == 0:
            return None

        classifications = {
            graph.nodes[node_id].get("classification")
            for node_id in graph.nodes()
        }
        if len(classifications) <= 1:
            return None

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            value = nx.attribute_assortativity_coefficient(graph, "classification")
        if isnan(value):
            return None
        return round(value, 6)

    def _safe_modularity(
        self,
        graph: nx.Graph,
        communities: list[set[Any]],
    ) -> Optional[float]:
        if graph.number_of_edges() == 0 or not communities:
            return None

        value = nx_community.modularity(graph, communities, weight="weight")
        if isnan(value):
            return None
        return round(value, 6)

    def _increment_edge(
        self, graph: nx.Graph, source_id: int, target_id: int, relation_type: str
    ) -> None:
        if graph.has_edge(source_id, target_id):
            attrs = graph[source_id][target_id]
        else:
            graph.add_edge(source_id, target_id, weight=0)
            attrs = graph[source_id][target_id]

        attrs.setdefault(f"{relation_type}_count", 0)
        attrs["weight"] += 1
        attrs[f"{relation_type}_count"] += 1

    def _ensure_person_node(
        self, graph: nx.Graph, person_id: Optional[int], person_name: Optional[str]
    ) -> None:
        if person_id is None:
            return
        if not graph.has_node(person_id):
            graph.add_node(
                person_id,
                name=person_name,
                node_type="person",
                classification=None,
                classification_confidence=None,
                was_student=False,
                was_staff=False,
                campus_id=None,
                campus_name=None,
            )
            return

        existing_name = graph.nodes[person_id].get("name")
        if not existing_name and person_name:
            graph.nodes[person_id]["name"] = person_name

    def _group_members_by_person(
        self,
        group: dict[str, Any],
    ) -> dict[int, dict[str, Any]]:
        members_by_person: dict[int, dict[str, Any]] = {}
        for member in group.get("members") or []:
            person_id = self._normalize_person_id(member.get("id"))
            if person_id is None:
                continue
            entry = members_by_person.setdefault(
                person_id,
                {
                    "person_id": person_id,
                    "person_name": member.get("name"),
                    "memberships": [],
                },
            )
            if not entry.get("person_name") and member.get("name"):
                entry["person_name"] = member.get("name")
            entry["memberships"].append(
                {
                    "role": member.get("role"),
                    "start_date": member.get("start_date"),
                    "end_date": member.get("end_date"),
                    "emails": member.get("emails") or [],
                    "lattes_url": member.get("lattes_url"),
                }
            )
        return members_by_person

    def _build_research_group_membership_graph(
        self,
        source_graph: nx.Graph,
        group: dict[str, Any],
        member_records: dict[int, dict[str, Any]],
    ) -> nx.DiGraph:
        group_id = group.get("id")
        group_node_id = self._research_group_node_id(group_id)
        membership_graph = nx.DiGraph()
        membership_graph.add_node(
            group_node_id,
            node_type="research_group",
            research_group_id=group_id,
            name=group.get("name"),
            short_name=group.get("short_name"),
            description=group.get("description"),
            campus_id=self._extract_campus_id(group.get("campus")),
            campus_name=self._extract_campus_name(group.get("campus")),
            organization_name=self._extract_name(group.get("organization")),
            member_count=len(member_records),
        )

        for person_id in sorted(member_records):
            person_name = member_records[person_id].get("person_name")
            self._copy_person_node(
                source_graph=source_graph,
                target_graph=membership_graph,
                person_id=person_id,
                fallback_name=person_name,
            )
            membership_graph.add_edge(
                person_id,
                group_node_id,
                weight=1,
                present_in_count=1,
                membership_count=len(member_records[person_id]["memberships"]),
                group_roles=self._unique_values(
                    membership.get("role")
                    for membership in member_records[person_id]["memberships"]
                ),
                membership_periods=[
                    {
                        "start_date": membership.get("start_date"),
                        "end_date": membership.get("end_date"),
                    }
                    for membership in member_records[person_id]["memberships"]
                ],
            )

        self._finalize_graph(
            membership_graph,
            relation_descriptions=RESEARCH_GROUP_MEMBERSHIP_RELATION_DESCRIPTIONS,
        )
        return membership_graph

    def _build_research_group_collaboration_graph(
        self,
        source_graph: nx.Graph,
        researchers: list[dict[str, Any]],
        initiatives: list[dict[str, Any]],
        advisorship_projects: list[dict[str, Any]],
        member_records: dict[int, dict[str, Any]],
    ) -> nx.Graph:
        member_ids = set(member_records)
        collaboration_graph = nx.Graph()

        for person_id in sorted(member_ids):
            self._copy_person_node(
                source_graph=source_graph,
                target_graph=collaboration_graph,
                person_id=person_id,
                fallback_name=member_records[person_id].get("person_name"),
            )

        self._add_group_semantic_article_relationships(
            graph=collaboration_graph,
            researchers=researchers,
            member_ids=member_ids,
        )
        self._add_group_semantic_project_relationships(
            graph=collaboration_graph,
            initiatives=initiatives,
            member_ids=member_ids,
        )
        self._add_group_semantic_orientation_relationships(
            graph=collaboration_graph,
            advisorship_projects=advisorship_projects,
            member_ids=member_ids,
        )
        self._finalize_graph(
            collaboration_graph,
            relation_descriptions=RESEARCH_GROUP_COLLABORATION_RELATION_DESCRIPTIONS,
        )
        return collaboration_graph

    def _build_global_collaboration_graph(
        self,
        source_graph: nx.Graph,
        researchers: list[dict[str, Any]],
        initiatives: list[dict[str, Any]],
        advisorship_projects: list[dict[str, Any]],
    ) -> nx.Graph:
        person_ids = {
            node_id
            for node_id, attrs in source_graph.nodes(data=True)
            if attrs.get("node_type", "person") == "person"
        }
        collaboration_graph = nx.Graph()

        for person_id in sorted(person_ids, key=str):
            self._copy_person_node(
                source_graph=source_graph,
                target_graph=collaboration_graph,
                person_id=person_id,
            )

        self._add_group_semantic_article_relationships(
            graph=collaboration_graph,
            researchers=researchers,
            member_ids=person_ids,
        )
        self._add_group_semantic_project_relationships(
            graph=collaboration_graph,
            initiatives=initiatives,
            member_ids=person_ids,
        )
        self._add_group_semantic_orientation_relationships(
            graph=collaboration_graph,
            advisorship_projects=advisorship_projects,
            member_ids=person_ids,
        )
        self._finalize_graph(
            collaboration_graph,
            relation_descriptions=RESEARCH_GROUP_COLLABORATION_RELATION_DESCRIPTIONS,
        )
        return collaboration_graph

    def _copy_person_node(
        self,
        source_graph: nx.Graph,
        target_graph: nx.Graph,
        person_id: int,
        fallback_name: Optional[str] = None,
    ) -> None:
        if target_graph.has_node(person_id):
            return

        if source_graph.has_node(person_id):
            attrs = dict(source_graph.nodes[person_id])
        else:
            attrs = {
                "node_type": "person",
                "name": fallback_name,
                "classification": None,
                "classification_confidence": None,
                "was_student": False,
                "was_staff": False,
                "campus_id": None,
                "campus_name": None,
            }

        if fallback_name and not attrs.get("name"):
            attrs["name"] = fallback_name
        attrs.setdefault("node_type", "person")
        target_graph.add_node(person_id, **attrs)

    def _add_group_semantic_article_relationships(
        self,
        graph: nx.Graph,
        researchers: list[dict[str, Any]],
        member_ids: set[int],
    ) -> None:
        article_to_people: dict[int, set[int]] = {}

        for researcher in researchers:
            person_id = self._normalize_person_id(researcher.get("id"))
            if person_id is None or person_id not in member_ids:
                continue

            article_ids = {
                article_id
                for article_id in (
                    self._normalize_person_id(article.get("id"))
                    for article in (researcher.get("articles") or [])
                    if isinstance(article, dict)
                )
                if article_id is not None
            }
            for article_id in article_ids:
                article_to_people.setdefault(article_id, set()).add(person_id)

        for people in article_to_people.values():
            for source_id, target_id in combinations(sorted(people), 2):
                self._increment_edge(graph, source_id, target_id, "article")

    def _add_group_semantic_project_relationships(
        self,
        graph: nx.Graph,
        initiatives: list[dict[str, Any]],
        member_ids: set[int],
    ) -> None:
        for initiative in initiatives:
            if not self._is_research_project(initiative):
                continue

            participants = sorted(
                {
                    person_id
                    for person_id, _person_name in self._unique_people(
                        (
                            member.get("person_id"),
                            member.get("person_name"),
                        )
                        for member in (initiative.get("team") or [])
                    ).values()
                    if person_id in member_ids
                }
            )
            for source_id, target_id in combinations(participants, 2):
                self._increment_edge(graph, source_id, target_id, "project")

    def _add_group_semantic_orientation_relationships(
        self,
        graph: nx.Graph,
        advisorship_projects: list[dict[str, Any]],
        member_ids: set[int],
    ) -> None:
        for project in advisorship_projects:
            for advisorship in project.get("advisorships") or []:
                supervisor_id = self._normalize_person_id(
                    advisorship.get("supervisor_id")
                )
                person_id = self._normalize_person_id(advisorship.get("person_id"))
                if (
                    supervisor_id is None
                    or person_id is None
                    or supervisor_id == person_id
                    or supervisor_id not in member_ids
                    or person_id not in member_ids
                ):
                    continue
                self._increment_edge(graph, supervisor_id, person_id, "orientation")

    def _unique_people(
        self, people: Iterable[tuple[Any, Any]]
    ) -> dict[int, tuple[int, Optional[str]]]:
        unique_people: dict[int, tuple[int, Optional[str]]] = {}
        for raw_person_id, person_name in people:
            person_id = self._normalize_person_id(raw_person_id)
            if person_id is None:
                continue
            unique_people.setdefault(person_id, (person_id, person_name))
        return unique_people

    @staticmethod
    def _normalize_person_id(person_id: Any) -> Optional[int]:
        if person_id is None:
            return None
        try:
            return int(person_id)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_campus_name(campus: Any) -> Optional[str]:
        if isinstance(campus, dict):
            return campus.get("name")
        if isinstance(campus, str):
            return campus
        return None

    @staticmethod
    def _extract_campus_id(campus: Any) -> Optional[int]:
        if isinstance(campus, dict):
            return PeopleRelationshipGraphGenerator._normalize_person_id(
                campus.get("id")
            )
        return None

    @staticmethod
    def _extract_name(entity: Any) -> Optional[str]:
        if isinstance(entity, dict):
            return entity.get("name")
        if isinstance(entity, str):
            return entity
        return None

    @staticmethod
    def _research_group_node_id(group_id: Any) -> str:
        return f"research_group:{group_id}"

    @staticmethod
    def _unique_values(values: Iterable[Any]) -> list[Any]:
        seen = []
        for value in values:
            if value in (None, "") or value in seen:
                continue
            seen.append(value)
        return seen

    @staticmethod
    def _is_research_project(initiative: dict[str, Any]) -> bool:
        initiative_type = initiative.get("initiative_type")
        if isinstance(initiative_type, dict):
            type_name = initiative_type.get("name")
            if type_name is not None:
                return type_name == "Research Project"
        return True

    @classmethod
    def _normalize_membership_interval(
        cls, member: dict[str, Any]
    ) -> tuple[Optional[date], Optional[date]]:
        start = cls._parse_iso_date(member.get("start_date"))
        end = cls._parse_iso_date(member.get("end_date"))

        if start and end and start > end:
            # Some exported rows carry an invalid "start" later than the end date.
            # In that case we keep only the reliable end boundary to avoid
            # fabricating a long-running overlap with everyone else.
            return None, end

        return start, end

    @staticmethod
    def _intervals_overlap(
        left: tuple[Optional[date], Optional[date]],
        right: tuple[Optional[date], Optional[date]],
    ) -> bool:
        left_start, left_end = left
        right_start, right_end = right

        if left_end and right_start and left_end < right_start:
            return False
        if right_end and left_start and right_end < left_start:
            return False
        return True

    @staticmethod
    def _parse_iso_date(value: Any) -> Optional[date]:
        if not isinstance(value, str) or not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
