from typing import Any

from src.core.logic.people_collaboration_graph_generator import (
    PeopleCollaborationGraphGenerator,
)


class OutsideIfesCollaborationGraphGenerator(PeopleCollaborationGraphGenerator):
    """
    Outside-IFES collaboration graph.

    Nodes: people with classification == 'outside_ifes'.
    Edges: collaboration between two outside-IFES people (initiative, article, advisorship).
    Edge weight: initiative_count + article_count + advisorship_count.
    """

    def generate(self, researchers_path: str, output_path: str) -> dict[str, Any]:
        return super().generate(
            researchers_path,
            output_path,
            node_filter=lambda p: p.get("classification") == "outside_ifes",
            node_filter_label="classification=outside_ifes",
        )
