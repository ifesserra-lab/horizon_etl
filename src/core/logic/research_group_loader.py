import pandas as pd
from loguru import logger
from research_domain import UniversityController, CampusController, ResearchGroupController, KnowledgeAreaController, ResearcherController, RoleController

class ResearchGroupLoader:
    def __init__(self):
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
        """Ensures UFSC exists."""
        if self._org_id:
            return self._org_id

        # Lookup First
        try:
            all_orgs = self.uni_ctrl.get_all()
            for org in all_orgs:
                if org.name == "UFSC":
                    self._org_id = org.id
                    logger.info(f"Organization found: {org.name} (ID: {org.id})")
                    return self._org_id
        except Exception as e:
            logger.error(f"Error fetching organizations: {e}")
            
        # Create if not found
        try:
            ufsc = self.uni_ctrl.create_university(name="UFSC", short_name="Federal University")
            self._org_id = ufsc.id
            logger.info(f"Organization created: {ufsc.name} (ID: {ufsc.id})")
        except Exception as e:
            logger.error(f"Failed to create organization: {e}")
            # Try to manual rollback if possible or just fail
            self._try_rollback(self.uni_ctrl)
            
        return self._org_id

    def ensure_campus(self, campus_name: str, org_id: int):
        """Ensures Campus exists."""
        if campus_name in self._campus_cache:
            return self._campus_cache[campus_name]

        # Lookup First
        try:
            all_campuses = self.campus_ctrl.get_all()
            for campus in all_campuses:
                # Check optional org_id if exists in model
                c_org = getattr(campus, 'organization_id', None)
                if campus.name == campus_name and (c_org is None or c_org == org_id):
                     self._campus_cache[campus_name] = campus.id
                     logger.debug(f"Campus found: {campus.name}")
                     return campus.id
        except Exception as e:
             logger.error(f"Error fetching campuses: {e}")

        # Create
        try:
            campus = self.campus_ctrl.create_campus(
                name=campus_name, 
                organization_id=org_id
            )
            self._campus_cache[campus_name] = campus.id
            logger.info(f"Campus created: {campus.name} (ID: {campus.id})")
            return campus.id
        except Exception as e:
            logger.error(f"Error creating campus '{campus_name}': {e}")
            self._try_rollback(self.campus_ctrl)
            return None
    
    def _try_rollback(self, controller):
        """Attempts to rollback session via private attributes."""
        try:
            # controller._service._repository._session.rollback()
            if hasattr(controller, '_service') and hasattr(controller._service, '_repository') and hasattr(controller._service._repository, '_session'):
                controller._service._repository._session.rollback()
                logger.info("Session rolled back successfully.")
        except:
            pass

    def ensure_leader_role(self):
        """Ensures the Leader role exists."""
        if "leader" in self._role_cache:
            return self._role_cache["leader"]
        
        try:
            role = self.role_ctrl.get_or_create_leader_role()
            self._role_cache["leader"] = role
            logger.info(f"Role 'Leader' ensured (ID: {role.id})")
            return role
        except Exception as e:
            logger.error(f"Error ensuring leader role: {e}")
            return None

    def ensure_researcher(self, name: str, email: str = None):
        """Ensures a researcher exists."""
        cache_key = f"{name}|{email}"
        if cache_key in self._researcher_cache:
            return self._researcher_cache[cache_key]

        # Lookup by name/email (simplistic for now)
        try:
            all_res = self.researcher_ctrl.get_all()
            for res in all_res:
                if res.name == name:
                    self._researcher_cache[cache_key] = res
                    return res
        except Exception as e:
            logger.error(f"Error fetching researchers: {e}")

        # Create
        try:
            emails = [email] if email else []
            res = self.researcher_ctrl.create_researcher(
                name=name, 
                emails=emails,
                identification_id=email # Use email as ID (User requirement)
            )
            self._researcher_cache[cache_key] = res
            logger.info(f"Researcher created: {name} (ID: {email})")
            return res
        except Exception as e:
            logger.error(f"Error creating researcher '{name}': {e}")
            self._try_rollback(self.researcher_ctrl)
            return None

    def _parse_leaders(self, leaders_str: str):
        """Parses leaders string like 'Name (email), Name2 (email2)'."""
        if not leaders_str or pd.isna(leaders_str):
            return []
        
        import re
        # Pattern to match "Name (email)" or just "Name"
        # Supports comma or semicolon separation
        parts = re.split(r'[,;]', str(leaders_str))
        leaders = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            match = re.match(r'^(.*?)\s*\((.*?)\)$', part)
            if match:
                name = match.group(1).strip()
                email = match.group(2).strip()
                leaders.append((name, email))
            else:
                leaders.append((part, None))
        return leaders

    def ensure_knowledge_area(self, area_name: str):
        """Ensures Knowledge Area exists."""
        if not area_name or pd.isna(area_name):
            return None
            
        if area_name in self._area_cache:
            return self._area_cache[area_name]

        # Lookup First
        try:
            # Assuming get_all exists
            all_areas = self.area_ctrl.get_all()
            for area in all_areas:
                if area.name == area_name:
                    self._area_cache[area_name] = area.id
                    return area.id
        except Exception as e:
            logger.error(f"Error fetching areas: {e}")

        # Create
        try:
            # create_knowledge_area(name)
            area = self.area_ctrl.create_knowledge_area(name=area_name)
            self._area_cache[area_name] = area.id
            logger.info(f"Knowledge Area created: {area.name}")
            return area.id
        except Exception as e:
            logger.error(f"Error creating area '{area_name}': {e}")
            self._try_rollback(self.area_ctrl)
            return None

    def process_file(self, file_path: str):
        logger.info(f"Processing Research Groups from: {file_path}")
        
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            logger.error(f"Failed to read Excel: {e}")
            return

        # 0. Ensure Role
        self.ensure_leader_role()

        # 1. Ensure Org
        org_id = self.ensure_organization()
        if not org_id:
            logger.error("Organization ID not available. Aborting.")
            return
            
        # Pre-fetch existing groups to avoid UniqueViolation
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
        for _, row in df.iterrows():
            try:
                # Map columns
                name = row.get('Nome')
                sigla = row.get('Sigla')
                unidade = row.get('Unidade')
                area_name = row.get('AreaConhecimento')
                site_url = row.get('Column1')
                
                if pd.isna(name):
                    continue
                
                # 3. Ensure Knowledge Area
                area_ids = []
                if pd.notna(area_name):
                    aid = self.ensure_knowledge_area(str(area_name).strip())
                    if aid:
                        area_ids.append(aid)
                
                # Parse Leaders
                leaders_data = self._parse_leaders(row.get('Lideres'))
                
                group = None
                # Check existence
                if name in existing_groups_map:
                    group = existing_groups_map[name]
                    
                    # Update cnpq_url if changed
                    if pd.notna(site_url) and getattr(group, 'cnpq_url', None) != site_url:
                        group.cnpq_url = site_url
                        try:
                            self.rg_ctrl.update(group)
                            updated += 1
                        except Exception as e:
                            logger.warning(f"Failed to update group {name}: {e}")
                            
                    skipped += 1
                else:    
                    # 2. Ensure Campus
                    campus_name = unidade if pd.notna(unidade) else "Campus Desconhecido"
                    campus_id = self.ensure_campus(campus_name, org_id)
                    
                    if not campus_id:
                        continue

                    # 4. Create Group
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

                # 5. Associate Leaders
                if group and leaders_data:
                    from datetime import date
                    for l_name, l_email in leaders_data:
                        researcher = self.ensure_researcher(l_name, l_email)
                        if researcher:
                            try:
                                # Start date is today if not specified
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
                logger.error(f"Error processing row {row}: {e}")
                self._try_rollback(self.rg_ctrl)
                
        logger.info(f"Loaded {count} New Research Groups. Skipped {skipped} existing (Updated {updated}).")
