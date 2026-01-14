import json
import os
from typing import Any, Dict, List, Optional

from loguru import logger
from research_domain import (
    CampusController,
    KnowledgeAreaController,
    ResearchGroupController,
)


class KnowledgeAreaMartGenerator:
    def __init__(self):
        self.ka_ctrl = KnowledgeAreaController()
        self.rg_ctrl = ResearchGroupController()
        self.campus_ctrl = CampusController()

    def generate(self, output_path: str, campus_filter: Optional[str] = None):
        """
        Generates a Research Area Mart JSON file.
        Associates knowledge areas with research groups and campuses.

        Args:
            output_path: Destination JSON file path.
            campus_filter: Optional campus name to filter groups.
        """
        logger.info(
            f"Generating Knowledge Area Mart to {output_path} (Filter: {campus_filter})"
        )

        try:
            # 1. Fetch data from DB
            all_areas = self.ka_ctrl.get_all()
            all_groups = self.rg_ctrl.get_all()
            all_campuses = self.campus_ctrl.get_all()

            logger.info(
                f"Loaded {len(all_areas)} areas, {len(all_groups)} groups, and {len(all_campuses)} campuses."
            )

            # Filter groups by campus if requested
            groups_to_process = all_groups
            if campus_filter:
                target_campus = next(
                    (
                        c
                        for c in all_campuses
                        if c.name.lower() == campus_filter.lower()
                    ),
                    None,
                )
                if not target_campus:
                    logger.warning(
                        f"Campus '{campus_filter}' not found. Mart will have 0 groups."
                    )
                    groups_to_process = []
                else:
                    groups_to_process = [
                        g for g in all_groups if g.campus_id == target_campus.id
                    ]
                    logger.info(
                        f"Filtered {len(groups_to_process)} groups for campus {target_campus.name}"
                    )

            # Create campus map for optimization
            campus_map = {c.id: c.name for c in all_campuses}

            # 2. Process data
            # Pre-calculate mapping: area_id -> list of group data
            area_mart = {}
            for area in all_areas:
                area_mart[area.id] = {
                    "area_id": area.id,
                    "area_name": area.name,
                    "groups_count": 0,
                    "groups": [],
                    "campuses": set(),
                }

            for group in groups_to_process:
                campus_name = campus_map.get(group.campus_id, "Unknown")

                # Check groups knowledge areas
                if hasattr(group, "knowledge_areas"):
                    for area in group.knowledge_areas:
                        if area.id in area_mart:
                            area_mart[area.id]["groups_count"] += 1
                            area_mart[area.id]["groups"].append(
                                {
                                    "id": group.id,
                                    "name": group.name,
                                    "campus": campus_name,
                                }
                            )
                            area_mart[area.id]["campuses"].add(campus_name)

            # 3. Finalize structure (convert set to list)
            mart_list = []
            for area_id in sorted(area_mart.keys()):
                item = area_mart[area_id]
                if item["groups_count"] > 0:
                    item["campuses"] = sorted(list(item["campuses"]))
                    mart_list.append(item)

            # 4. Save to JSON
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(mart_list, f, indent=4, ensure_ascii=False)

            logger.info(f"Knowledge Area Mart successfully generated at {output_path}")
            return mart_list

        except Exception as e:
            logger.error(f"Failed to generate Knowledge Area Mart: {e}")
            raise e
