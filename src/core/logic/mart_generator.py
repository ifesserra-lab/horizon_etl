from typing import List, Dict, Any
from loguru import logger
import json
import os
from research_domain import KnowledgeAreaController, ResearchGroupController, CampusController

class KnowledgeAreaMartGenerator:
    def __init__(self):
        self.ka_ctrl = KnowledgeAreaController()
        self.rg_ctrl = ResearchGroupController()
        self.campus_ctrl = CampusController()

    def generate(self, output_path: str):
        """
        Generates a Research Area Mart JSON file.
        Associates knowledge areas with research groups and campuses.
        """
        logger.info(f"Generating Knowledge Area Mart to {output_path}")
        
        try:
            # 1. Fetch data from DB
            all_areas = self.ka_ctrl.get_all()
            all_groups = self.rg_ctrl.get_all()
            all_campuses = self.campus_ctrl.get_all()

            logger.info(f"Loaded {len(all_areas)} areas, {len(all_groups)} groups, and {len(all_campuses)} campuses.")

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
                    "campuses": set()
                }

            for group in all_groups:
                campus_name = campus_map.get(group.campus_id, "Unknown")
                
                # Check groups knowledge areas
                if hasattr(group, 'knowledge_areas'):
                    for area in group.knowledge_areas:
                        if area.id in area_mart:
                            area_mart[area.id]["groups_count"] += 1
                            area_mart[area.id]["groups"].append({
                                "id": group.id,
                                "name": group.name,
                                "campus": campus_name
                            })
                            area_mart[area.id]["campuses"].add(campus_name)

            # 3. Finalize structure (convert set to list)
            mart_list = []
            for area_id in sorted(area_mart.keys()):
                item = area_mart[area_id]
                item["campuses"] = sorted(list(item["campuses"]))
                mart_list.append(item)

            # 4. Save to JSON
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(mart_list, f, indent=4, ensure_ascii=False)

            logger.info(f"Knowledge Area Mart successfully generated at {output_path}")
            return mart_list

        except Exception as e:
            logger.error(f"Failed to generate Knowledge Area Mart: {e}")
            raise e
