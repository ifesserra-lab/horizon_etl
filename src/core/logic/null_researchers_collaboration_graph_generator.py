from typing import Any

from src.core.logic.people_collaboration_graph_generator import (
    PeopleCollaborationGraphGenerator,
)


class NullResearchersCollaborationGraphGenerator(PeopleCollaborationGraphGenerator):
    """
    Null-classification collaboration graph.

    Nodes: people with classification == None (unclassified records).
    Edges: collaboration between two null-classification people (initiative, article, advisorship).
    Edge weight: initiative_count + article_count + advisorship_count.
    """

    def generate(self, researchers_path: str, output_path: str) -> dict[str, Any]:
        return super().generate(
            researchers_path,
            output_path,
            node_filter=lambda p: p.get("classification") is None,
            node_filter_label="classification=null",
        )
