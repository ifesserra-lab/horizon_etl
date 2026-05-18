from typing import Any

from src.core.logic.people_collaboration_graph_generator import (
    PeopleCollaborationGraphGenerator,
)


class ResearchersCollaborationGraphGenerator(PeopleCollaborationGraphGenerator):
    """
    Researchers-only collaboration graph.

    Nodes: people with classification == 'researcher'.
    Edges: collaboration between two researchers (initiative, article, advisorship).
    Edge weight: same as global graph — initiative_count + article_count + advisorship_count.
    """

    def generate(self, researchers_path: str, output_path: str) -> dict[str, Any]:
        return super().generate(
            researchers_path,
            output_path,
            node_filter=lambda p: p.get("classification") == "researcher",
            node_filter_label="classification=researcher",
        )
