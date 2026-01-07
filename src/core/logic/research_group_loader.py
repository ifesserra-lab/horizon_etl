import pandas as pd
from loguru import logger
from research_domain import UniversityController, CampusController, ResearchGroupController, KnowledgeAreaController, ResearcherController, RoleController

from .strategies.base import (
    ResearchGroupMappingStrategy,
    OrganizationStrategy,
    CampusStrategy,
    KnowledgeAreaStrategy,
    ResearcherStrategy,
    RoleStrategy
)

class ResearchGroupLoader:
    def __init__(
        self, 
        mapping_strategy: ResearchGroupMappingStrategy,
        org_strategy: OrganizationStrategy,
        campus_strategy: CampusStrategy,
        area_strategy: KnowledgeAreaStrategy,
        researcher_strategy: ResearcherStrategy,
        role_strategy: RoleStrategy
    ):
        self.mapping_strategy = mapping_strategy
        self.org_strategy = org_strategy
        self.campus_strategy = campus_strategy
        self.area_strategy = area_strategy
        self.researcher_strategy = researcher_strategy
        self.role_strategy = role_strategy
        
        self.uni_ctrl = UniversityController()
        self.campus_ctrl = CampusController()
        self.rg_ctrl = ResearchGroupController()
        self.area_ctrl = KnowledgeAreaController()
        self.researcher_ctrl = ResearcherController()
        self.role_ctrl = RoleController()
        
        # Cache to avoid repeated DB hits
        self._org_id = None
        self._campus_cache = {}
        self._area_cache = {}
        self._role_cache = {}
        self._researcher_cache = {}

    def ensure_organization(self):
        """Ensures organization exists using strategy."""
        if self._org_id:
            return self._org_id
        
        self._org_id = self.org_strategy.ensure(self.uni_ctrl)
        return self._org_id

    def ensure_campus(self, campus_name: str, org_id: int):
        """Ensures Campus exists using strategy."""
        if campus_name in self._campus_cache:
            return self._campus_cache[campus_name]

        campus_id = self.campus_strategy.ensure(self.campus_ctrl, campus_name, org_id)
        if campus_id:
            self._campus_cache[campus_name] = campus_id
        return campus_id
    
    def _try_rollback(self, controller):
        """Attempts to rollback session via private attributes."""
        try:
            if hasattr(controller, '_service') and hasattr(controller._service, '_repository') and hasattr(controller._service._repository, '_session'):
                controller._service._repository._session.rollback()
                logger.debug("Session rolled back successfully.")
        except:
            pass

    def ensure_leader_role(self):
        """Ensures the Leader role exists using strategy."""
        if "leader" in self._role_cache:
            return self._role_cache["leader"]
        
        role = self.role_strategy.ensure_leader(self.role_ctrl)
        if role:
            self._role_cache["leader"] = role
        return role

    def ensure_researcher(self, name: str, email: str = None):
        """Ensures a researcher exists."""
        cache_key = f"{name}|{email}"
        if cache_key in self._researcher_cache:
            return self._researcher_cache[cache_key]

        researcher = self.researcher_strategy.ensure(self.researcher_ctrl, name, email)
        if researcher:
            self._researcher_cache[cache_key] = researcher
        return researcher

    def ensure_knowledge_area(self, area_name: str):
        """Ensures Knowledge Area exists."""
        if not area_name or pd.isna(area_name):
            return None
            
        if area_name in self._area_cache:
            return self._area_cache[area_name]

        area_id = self.area_strategy.ensure(self.area_ctrl, area_name)
        if area_id:
            self._area_cache[area_name] = area_id
        return area_id

    def process_file(self, file_path: str):
        logger.info(f"Processing Research Groups from: {file_path}")
        
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            logger.error(f"Failed to read Excel: {e}")
            return

        self.ensure_leader_role()
        org_id = self.ensure_organization()
        if not org_id:
            logger.error("Organization ID not available. Aborting.")
            return
            
        existing_groups_map = {}
        try:
             all_groups = self.rg_ctrl.get_all()
             for g in all_groups:
                 if g.name:
                     existing_groups_map[g.name] = g
             logger.info(f"Pre-fetched {len(existing_groups_map)} existing groups.")
        except Exception as e:
             logger.warning(f"Could not pre-fetch groups: {e}")

        count = 0
        updated = 0
        skipped = 0
        for _, row_raw in df.iterrows():
            try:
                # Delegate mapping to strategy
                data = self.mapping_strategy.map_row(row_raw.to_dict())
                
                name = data.get('name')
                sigla = data.get('short_name')
                unidade = data.get('campus_name')
                area_name = data.get('area_name')
                site_url = data.get('site_url')
                leaders_raw = data.get('leaders_raw')
                
                if pd.isna(name):
                    continue
                
                area_ids = []
                if pd.notna(area_name):
                    aid = self.ensure_knowledge_area(str(area_name).strip())
                    if aid:
                        area_ids.append(aid)
                
                # Delegate parsing to strategy
                leaders_data = self.mapping_strategy.parse_leaders(leaders_raw)
                
                group = None
                if name in existing_groups_map:
                    group = existing_groups_map[name]
                    if pd.notna(site_url) and getattr(group, 'cnpq_url', None) != site_url:
                        group.cnpq_url = site_url
                        try:
                            self.rg_ctrl.update(group)
                            updated += 1
                        except Exception as e:
                            logger.warning(f"Failed to update group {name}: {e}")
                    skipped += 1
                else:    
                    campus_name = unidade if pd.notna(unidade) else "Campus Desconhecido"
                    campus_id = self.ensure_campus(campus_name, org_id)
                    
                    if not campus_id:
                        continue

                    try:
                        group = self.rg_ctrl.create_research_group(
                            name=name,
                            campus_id=campus_id,
                            organization_id=org_id,
                            short_name=sigla if pd.notna(sigla) else None,
                            cnpq_url=site_url if pd.notna(site_url) else None,
                            knowledge_area_ids=area_ids if area_ids else None
                        )
                        count += 1
                    except Exception as e:
                        logger.error(f"Failed to create group {name}: {e}")
                        self._try_rollback(self.rg_ctrl)
                        continue

                if group and leaders_data:
                    from datetime import date
                    for l_name, l_email in leaders_data:
                        researcher = self.ensure_researcher(l_name, l_email)
                        if researcher:
                            try:
                                self.rg_ctrl.add_leader(
                                    team_id=group.id,
                                    person_id=researcher.id,
                                    start_date=date.today()
                                )
                                logger.debug(f"Leader {l_name} associated to group {name}")
                            except Exception as e:
                                logger.warning(f"Failed to associate leader {l_name} to unit {name}: {e}")
                                self._try_rollback(self.rg_ctrl)

            except Exception as e:
                logger.error(f"Error processing row: {e}")
                self._try_rollback(self.rg_ctrl)
                
        logger.info(f"Loaded {count} New Research Groups. Skipped {skipped} existing (Updated {updated}).")
