import os
import json
from datetime import datetime
from collections import Counter
from typing import Any, List, Optional

from eo_lib import InitiativeController, OrganizationController
from loguru import logger
from research_domain import (
    CampusController,
    KnowledgeAreaController,
    ResearcherController,
    ResearchGroupController,
)
from research_domain.domain.entities import Advisorship, Fellowship

from src.core.ports.export_sink import IExportSink
from sqlalchemy import text


class CanonicalDataExporter:
    """
    Exports domain entities from the database to canonical JSON files.

    This class orchestrates the extraction of various entities (Organizations, Campuses,
    Knowledge Areas, Researchers, Initiatives) using their respective controllers
    and serializes them into a standardized format for external consumption.

    Attributes:
        sink (IExportSink): The destination for the exported data (e.g., File, S3).
        org_ctrl (OrganizationController): Controller for organizations.
        campus_ctrl (CampusController): Controller for campuses.
        ka_ctrl (KnowledgeAreaController): Controller for knowledge areas.
        researcher_ctrl (ResearcherController): Controller for researchers.
        initiative_ctrl (InitiativeController): Controller for initiatives.
    """

    def __init__(self, sink: IExportSink):
        """
        Initializes the CanonicalDataExporter.

        Args:
            sink (IExportSink): The strategy for exporting the data.
        """
        self.sink = sink
        self.org_ctrl = OrganizationController()
        self.campus_ctrl = CampusController()
        self.ka_ctrl = KnowledgeAreaController()
        self.researcher_ctrl = ResearcherController()
        self.initiative_ctrl = InitiativeController()

    def _export_entities(self, data: List[Any], output_path: str, entity_name: str):
        """
        Helper to serialize and export a list of entities.
        """
        logger.info(f"Exporting {len(data)} {entity_name}...")
        try:
            export_data = []
            for item in data:
                if isinstance(item, dict):
                    export_data.append(item)
                elif hasattr(item, "to_dict"):
                    export_data.append(item.to_dict())
                else:
                    # Fallback for entities without to_dict (should not happen with SerializableMixin)
                    export_data.append(
                        {
                            "id": getattr(item, "id", None),
                            "name": getattr(item, "name", "Unknown"),
                        }
                    )

            self.sink.export(export_data, output_path)
            logger.info(f"Successfully exported {entity_name} to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export {entity_name}: {e}")
            raise e

    def export_organizations(self, output_path: str):
        """
        Exports all organizations to a JSON file.

        Args:
            output_path (str): The destination file path.
        """
        data = self.org_ctrl.get_all()
        self._export_entities(data, output_path, "Organizations")

    def export_campuses(self, output_path: str, campus_filter: Optional[str] = None):
        """
        Exports campuses to a JSON file, optionally filtered by name.

        Args:
            output_path (str): The destination file path.
            campus_filter (Optional[str]): name of campus to filter.
        """
        data = self.campus_ctrl.get_all()
        if campus_filter:
            data = [c for c in data if c.name.lower() == campus_filter.lower()]
        self._export_entities(data, output_path, "Campuses")

    def export_knowledge_areas(self, output_path: str):
        """
        Exports all knowledge areas to a JSON file.

        Args:
            output_path (str): The destination file path.
        """
        data = self.ka_ctrl.get_all()
        self._export_entities(data, output_path, "Knowledge Areas")

    def export_researchers(self, output_path: str):
        """
        Exports all researchers to a JSON file.

        Args:
            output_path (str): The destination file path.
        """
        # Fetch raw list
        researchers = self.researcher_ctrl.get_all()
        
        # Enrichment Data
        # 1. Initiatives (Researcher -> [Initiatives])
        # We need to scan all initiatives' teams/members to map person_id -> initiative list
        # This is expensive but necessary without direct person->initiative DB queries available in current controllers
        person_initiatives_map = {}
        try:
            initiatives = self.initiative_ctrl.get_all()
            from eo_lib import TeamController
            team_ctrl = TeamController()
            
            # Pre-fetch all Research Group IDs to identify "Group Teams" (non-project teams)
            rg_ids = {getattr(g, "id", None) for g in self.researcher_ctrl._service._repository._session.execute(text("SELECT id FROM research_groups")).fetchall()}
            
            for init in initiatives:
                try:
                    teams = self.initiative_ctrl.get_teams(init.id)
                    for t in teams:
                        t_id = getattr(t, "id", t.get("id") if isinstance(t, dict) else None)
                        
                        # FILTER: If the team is a Research Group, memberships in this team 
                        # should not count as being PART OF the initiative in the Researchers canonical export.
                        if t_id in rg_ids:
                            continue
                            
                        if t_id:
                            members = team_ctrl.get_members(t_id)
                            for m in members:
                                p_id = m.person_id
                                if p_id:
                                    if p_id not in person_initiatives_map:
                                        person_initiatives_map[p_id] = []
                                    
                                    # Consolidate roles if person is in multiple teams (unlikely now with filter, but safe)
                                    existing = next((i for i in person_initiatives_map[p_id] if i["id"] == init.id), None)
                                    role_name = m.role.name if m.role else "Member"
                                    
                                    if not existing:
                                        person_initiatives_map[p_id].append({
                                            "id": init.id,
                                            "name": init.name,
                                            "status": init.status,
                                            "roles": [role_name]
                                        })
                                    else:
                                        if role_name not in existing["roles"]:
                                            existing["roles"].append(role_name)
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Failed to fetch initiatives for researcher enrichment: {e}")

        # 2. Research Groups (Researcher -> [Groups])
        # We can reuse the same logic if we know which teams are groups
        # OR we can use the Group members if exposed. 
        # ResearchGroupController usually exposes `get_members`? No, it exposes `get_all` groups.
        # But groups are Teams.
        person_groups_map = {}
        try:
            rg_ctrl = ResearchGroupController()
            all_rgs = rg_ctrl.get_all()
            
            # Pre-fetch group IDs
            rg_ids = {getattr(g, "id", None): getattr(g, "name", "Unknown") for g in all_rgs}
            
            # Since RGs are teams, we might have already processed them in initiatives if they are linked there?
            # No, RGs are distinct entities in the domain lib, but they implement Team interface or are wrapped.
            # Usually RG has a mirrored Team.
            # If we don't have a direct "get members of group" in the controller, we rely on the DB or dgp_cnpq_lib.
            # Checking `ResearchGroupController` in `research_domain`... 
            # Assuming we can access the underlying team or members.
            # If not easy, we might skip or do a best effort.
            # Strategy: Access the database session again to query group_members tables directly for speed.
            
            session = rg_ctrl._service._repository._session
            
            # Query group members (person_id -> group info)
            # Schema: research_groups.id matches teams.id (joined inheritance or logical link)
            # Members are in team_members table.
            # Query group members (person_id -> group info)
            # Schema: research_groups.id matches teams.id (joined inheritance or logical link)
            # Members are in team_members table.
            
            # Correct Query with 3-way join
            g_query = text("""
                SELECT tm.person_id, rg.id, t.name
                FROM team_members tm
                JOIN research_groups rg ON tm.team_id = rg.id
                JOIN teams t ON rg.id = t.id
            """)
            g_result = session.execute(g_query).fetchall()
            for row in g_result:
                pid, gid, gname = row[0], row[1], row[2]
                if pid not in person_groups_map: person_groups_map[pid] = []
                person_groups_map[pid].append({"id": gid, "name": gname})
                
        except Exception as e:
            logger.warning(f"Failed to fetch research groups for researcher enrichment: {e}")

        # 3. Knowledge Areas (Researcher -> [KAs])
        person_kas_map = {}
        try:
            # Query researcher_knowledge_areas
            # uses researcher_id (which should map to person_id/researcher.id)
            k_query = text("""
                SELECT rka.researcher_id, ka.id, ka.name
                FROM researcher_knowledge_areas rka
                JOIN knowledge_areas ka ON rka.area_id = ka.id
            """)
            k_result = session.execute(k_query).fetchall()
            for row in k_result:
                pid, kid, kname = row[0], row[1], row[2]
                if pid not in person_kas_map: person_kas_map[pid] = []
                person_kas_map[pid].append({"id": kid, "name": kname})

        except Exception as e:
            logger.warning(f"Failed to fetch KAs for researcher enrichment: {e}")


        # Enrich and Export
        export_data = []
        for r in researchers:
            r_dict = r.to_dict() if hasattr(r, "to_dict") else {
                "id": getattr(r, "id", None),
                "name": getattr(r, "name", "Unknown"),
                "lattes_id": getattr(r, "lattes_id", None),
                "email": getattr(r, "email", None),
            }
            
            p_id = r_dict.get("id")
            
            # Attach details
            initiatives_data = []
            for init in person_initiatives_map.get(p_id, []):
                # Standardize roles to English and pick primary if single string preferred
                # User previously had a single string, but let's provide the first one found 
                # or join them if we want to be thorough. 
                # To match previous structure but with correct data:
                role_map = {
                    "Coordenador": "Coordinator",
                    "Pesquisador": "Researcher",
                    "Estudante": "Student",
                    "Líder": "Leader",
                    "Membro": "Member"
                }
                translated_roles = [role_map.get(r, r) for r in init["roles"]]
                
                init_export = init.copy()
                init_export["role"] = translated_roles[0] # Primary role
                del init_export["roles"]
                initiatives_data.append(init_export)

            r_dict["initiatives"] = initiatives_data
            r_dict["research_groups"] = person_groups_map.get(p_id, [])
            r_dict["knowledge_areas"] = person_kas_map.get(p_id, [])
            
            export_data.append(r_dict)

        logger.info(f"Exporting {len(export_data)} Researchers...")
        self.sink.export(export_data, output_path)
        logger.info(f"Successfully exported enriched Researchers to {output_path}")

    def export_initiatives(self, output_path: str):
        """
        Exports enriched initiatives (with types, organizations, and team members) to a JSON file.

        This method aggregates data from multiple controllers to provide a complete
        view of each initiative, including its team structure with roles.

        Args:
            output_path (str): The destination file path.
        """
        from eo_lib import TeamController

        team_ctrl = TeamController()
        initiatives = self.initiative_ctrl.get_all()
        rg_ctrl = ResearchGroupController()
        # Pre-fetch all Research Groups for finding matches
        # Map <team_id> -> <ResearchGroup>
        rgs_by_team_id = {}
        try:
            all_rgs = rg_ctrl.get_all()
            for rg in all_rgs:
                 rg_id = getattr(rg, "id", None)
                 if rg_id:
                     rgs_by_team_id[rg_id] = rg
        except Exception as e:
            logger.warning(f"Failed to fetch Research Groups for export mapping: {e}")

        # Fetch Knowledge Areas mapping for Groups (Not used in Initiatives anymore, but keep if needed for other methods)
        group_kas_map = {}
        # Fetch Knowledge Areas mapping for Initiatives
        initiative_kas_map = {}

        try:
             from sqlalchemy import text
             session = rg_ctrl._service._repository._session
             
             # Group KAs (Optional enrichment if needed elsewhere)
             g_query = text("""
                SELECT gka.group_id, ka.id, ka.name
                FROM group_knowledge_areas gka
                JOIN knowledge_areas ka ON gka.area_id = ka.id
             """)
             g_result = session.execute(g_query).fetchall()
             for row in g_result:
                 gid = row[0]
                 if gid not in group_kas_map: group_kas_map[gid] = []
                 group_kas_map[gid].append({"id": row[1], "name": row[2]})

             # Initiative KAs
             i_query = text("""
                SELECT ika.initiative_id, ka.id, ka.name
                FROM initiative_knowledge_areas ika
                JOIN knowledge_areas ka ON ika.area_id = ka.id
             """)
             i_result = session.execute(i_query).fetchall()
             for row in i_result:
                 iid = row[0]
                 if iid not in initiative_kas_map: initiative_kas_map[iid] = []
                 initiative_kas_map[iid].append({"id": row[1], "name": row[2]})
                 
        except Exception as e:
            logger.warning(f"Failed to fetch Knowledge Area mappings: {e}")

        # Normalize types and orgs to handle both dicts and objects
        raw_types = self.initiative_ctrl.list_initiative_types()
        types = {}
        for t in raw_types:
            t_id = t.get("id") if isinstance(t, dict) else getattr(t, "id", None)
            if t_id:
                types[t_id] = t

        raw_orgs = self.org_ctrl.get_all()
        orgs = {}
        for o in raw_orgs:
            o_id = o.get("id") if isinstance(o, dict) else getattr(o, "id", None)
            if o_id:
                orgs[o_id] = o

        serialized_data = []
        for item in initiatives:
            # Enriched Initiative Type
            init_type = types.get(item.initiative_type_id)
            if init_type:
                type_data = {
                    "id": (
                        init_type.get("id")
                        if isinstance(init_type, dict)
                        else getattr(init_type, "id", None)
                    ),
                    "name": (
                        init_type.get("name")
                        if isinstance(init_type, dict)
                        else getattr(init_type, "name", None)
                    ),
                    "description": (
                        init_type.get("description")
                        if isinstance(init_type, dict)
                        else getattr(init_type, "description", None)
                    ),
                }
            else:
                type_data = None

            # Enriched Organization
            org = orgs.get(item.organization_id)
            if org:
                org_data = {
                    "id": (
                        org.get("id")
                        if isinstance(org, dict)
                        else getattr(org, "id", None)
                    ),
                    "name": (
                        org.get("name")
                        if isinstance(org, dict)
                        else getattr(org, "name", None)
                    ),
                    "short_name": (
                        org.get("short_name")
                        if isinstance(org, dict)
                        else getattr(org, "short_name", None)
                    ),
                }
            else:
                org_data = None

            # Enriched Team
            team_list = []
            
            # Identify Research Group
            research_group_data = None
            
            try:
                teams = self.initiative_ctrl.get_teams(item.id)
                for t_dict in teams:
                    t_id = t_dict.get("id")
                    if t_id:
                        # Check if this team is a Research Group
                        if t_id in rgs_by_team_id and not research_group_data:
                            rg_obj = rgs_by_team_id[t_id]
                            rg_id_val = getattr(rg_obj, "id", None)
                            research_group_data = {
                                "id": rg_id_val,
                                "name": getattr(rg_obj, "name", "Unknown")
                            }
                        
                        # FILTER: Skip adding members if the team is a Research Group
                        # These members are reported in the group's own context,
                        # not as direct initiative participants.
                        if t_id in rgs_by_team_id:
                            continue

                        members = team_ctrl.get_members(t_id)

                        # Aggregate roles by person
                        person_map = {}  # person_id -> member_data
                        for m in members:
                            p_id = m.person_id
                            if p_id not in person_map:
                                person_map[p_id] = {
                                    "person_id": p_id,
                                    "person_name": (
                                        m.person.name if m.person else "Unknown"
                                    ),
                                    "roles": [],  # Collect role names here
                                    "start_date": (
                                        m.start_date.isoformat()
                                        if m.start_date
                                        else None
                                    ),
                                    "end_date": (
                                        m.end_date.isoformat() if m.end_date else None
                                    ),
                                }

                            role_name = m.role.name if m.role else "Member"
                            if role_name not in person_map[p_id]["roles"]:
                                person_map[p_id]["roles"].append(role_name)

                        # Add aggregated members to team_list
                        for p_data in person_map.values():
                            team_list.append(p_data)
            except Exception as e:
                logger.warning(f"Could not fetch teams for initiative {item.id}: {e}")

            serialized_data.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "status": item.status,
                    "description": item.description,
                    "start_date": (
                        item.start_date.isoformat() if item.start_date else None
                    ),
                    "end_date": item.end_date.isoformat() if item.end_date else None,
                    "initiative_type_id": item.initiative_type_id,
                    "initiative_type": type_data,
                    "organization_id": item.organization_id,
                    "organization": org_data,
                    "parent_id": item.parent_id,
                    "team": team_list,
                    "research_group": research_group_data,
                    "knowledge_areas": initiative_kas_map.get(item.id, []),
                    "external_partner": (
                        item.metadata.get("external_partner")
                        if item.metadata and isinstance(item.metadata, dict)
                        else getattr(item.metadata, "external_partner", None)
                        if item.metadata
                        else None
                    ),
                    "external_research_group": (
                        item.metadata.get("external_research_group")
                        if item.metadata and isinstance(item.metadata, dict)
                        else getattr(item.metadata, "external_research_group", None)
                        if item.metadata
                        else None
                    ),
                }
            )

        logger.info(f"Exporting {len(serialized_data)} enriched Initiatives...")
        self.sink.export(serialized_data, output_path)
        logger.info(f"Successfully exported enriched Initiatives to {output_path}")

    def export_initiative_types(self, output_path: str):
        """
        Exports all initiative types to a JSON file.

        Args:
            output_path (str): The destination file path.
        """
        data = self.initiative_ctrl.list_initiative_types()
        self._export_entities(data, output_path, "Initiative Types")

    def export_all(self, output_dir: str):
        """
        Exports all canonical data to the specified directory.
        Generates: organizations, campuses, knowledge_areas, researchers, initiatives, initiative_types
        """
        logger.info(f"Starting Canonical Data Export to {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

        self.export_organizations(
            os.path.join(output_dir, "organizations_canonical.json")
        )
        self.export_campuses(os.path.join(output_dir, "campuses_canonical.json"))
        self.export_knowledge_areas(
            os.path.join(output_dir, "knowledge_areas_canonical.json")
        )
        self.export_researchers(os.path.join(output_dir, "researchers_canonical.json"))
        self.export_initiatives(os.path.join(output_dir, "initiatives_canonical.json"))
        self.export_initiative_types(
            os.path.join(output_dir, "initiative_types_canonical.json")
        )
        self.export_advisorships(
            os.path.join(output_dir, "advisorships_canonical.json")
        )
        self.export_fellowships(
            os.path.join(output_dir, "fellowships_canonical.json")
        )

        logger.info("Canonical Data Export completed.")

    def export_advisorships(self, output_path: str):
        """
        Exports all advisorships to a JSON file.
        """
        session = self.initiative_ctrl._service._repository._session
        query = text("""
            SELECT 
                a.id, i.name, i.status, i.description, i.start_date, i.end_date,
                a.student_id, p_std.name as student_name,
                a.supervisor_id, p_sup.name as supervisor_name,
                a.fellowship_id,
                f.name as fellowship_name,
                f.description as fellowship_description,
                f.value as fellowship_value,
                i.parent_id, 
                p_init.name as parent_name,
                p_init.status as parent_status,
                p_init.description as parent_description,
                p_init.start_date as parent_start_date,
                p_init.end_date as parent_end_date
            FROM advisorships a
            JOIN initiatives i ON a.id = i.id
            LEFT JOIN persons p_std ON a.student_id = p_std.id
            LEFT JOIN persons p_sup ON a.supervisor_id = p_sup.id
            LEFT JOIN initiatives p_init ON i.parent_id = p_init.id
            LEFT JOIN fellowships f ON a.fellowship_id = f.id
        """)
        result = session.execute(query).fetchall()
        
        projects_map = {}
        orphans = []
        
        for row in result:
            adv_data = {
                "id": row.id,
                "name": row.name,
                "status": row.status,
                "description": row.description,
                "start_date": (
                    row.start_date.isoformat() 
                    if hasattr(row.start_date, "isoformat") 
                    else str(row.start_date) if row.start_date else None
                ),
                "end_date": (
                     row.end_date.isoformat()
                     if hasattr(row.end_date, "isoformat")
                     else str(row.end_date) if row.end_date else None
                ),
                "student_id": row.student_id,
                "student_name": row.student_name,
                "supervisor_id": row.supervisor_id,
                "supervisor_name": row.supervisor_name,
                "fellowship": {
                    "id": row.fellowship_id,
                    "name": row.fellowship_name,
                    "description": row.fellowship_description,
                    "value": row.fellowship_value
                } if row.fellowship_id else None
            }
            
            if row.parent_id:
                if row.parent_id not in projects_map:
                    projects_map[row.parent_id] = {
                        "id": row.parent_id,
                        "name": row.parent_name,
                        "status": row.parent_status,
                        "description": row.parent_description,
                        "start_date": (
                            row.parent_start_date.isoformat() 
                            if hasattr(row.parent_start_date, "isoformat") 
                            else str(row.parent_start_date) if row.parent_start_date else None
                        ),
                        "end_date": (
                             row.parent_end_date.isoformat()
                             if hasattr(row.parent_end_date, "isoformat")
                             else str(row.parent_end_date) if row.parent_end_date else None
                        ),
                        "advisorships": []
                    }
                projects_map[row.parent_id]["advisorships"].append(adv_data)
            else:
                orphans.append(adv_data)
        
        # 3. Fetch Team Members for all parent projects
        parent_ids = [pid for pid in projects_map.keys() if pid is not None]
        if parent_ids:
            # Format IDs for raw SQL IN clause
            ids_str = ",".join(str(pid) for pid in parent_ids)
            members_query = text(f"""
                SELECT 
                    it.initiative_id,
                    p.name as person_name,
                    r.name as role_name
                FROM initiative_teams it
                JOIN team_members tm ON it.team_id = tm.team_id
                JOIN persons p ON tm.person_id = p.id
                JOIN roles r ON tm.role_id = r.id
                WHERE it.initiative_id IN ({ids_str})
            """)
            try:
                members_result = session.execute(members_query).fetchall()
                
                logger.info(f"Team fetch: Identified {len(parent_ids)} parents. Found {len(members_result)} members total.")
                
                for m_row in members_result:
                    pid = m_row[0]  # initiative_id
                    if pid in projects_map:
                        if "team" not in projects_map[pid]:
                            projects_map[pid]["team"] = []
                        projects_map[pid]["team"].append({
                            "name": m_row[1], # person_name
                            "role": m_row[2]  # role_name
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch team members for parent projects: {e}")
        
        # Ensure 'team' and 'advisorships' fields exist for all (even if empty)
        for p in projects_map.values():
            if "team" not in p:
                p["team"] = []
            if "advisorships" not in p:
                p["advisorships"] = []

        # Combine grouped projects, filtering out projects without advisorships
        final_data = [p for p in projects_map.values() if p.get("advisorships")]
        
        if orphans:
            final_data.append({
                "id": None,
                "name": "Sem Projeto Associado",
                "status": "N/A",
                "team": [],
                "description": "Bolsistas sem vínculo direto com um projeto de pesquisa estruturado no SigPesq.",
                "advisorships": orphans
            })
        
        logger.info(f"Filtered export: {len(final_data)} parent projects with advisorships (excluded {len(projects_map) - len([p for p in projects_map.values() if p.get('advisorships')])} projects without advisorships)")
        self.sink.export(final_data, output_path)
        logger.info(f"Successfully exported {len(final_data)} parent projects with advisorships to {output_path}")

    def export_fellowships(self, output_path: str):
        """
        Exports all fellowships to a JSON file.
        """
        session = self.initiative_ctrl._service._repository._session
        query = text("SELECT * FROM fellowships")
        result = session.execute(query).fetchall()
        data = []
        for row in result:
            data.append({
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "value": row.value
            })
        
        self.sink.export(data, output_path)
        logger.info(f"Successfully exported {len(data)} Fellowships to {output_path}")

    def generate_advisorship_mart(self, input_path: str, output_path: str):
        """
        Generates an analytical data mart from the hierarchical advisorship JSON.
        """
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                projects = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load canonical advisorships for mart: {e}")
            return

        mart_projects = []
        global_stats = {
            "total_projects": 0,
            "total_advisorships": 0,
            "total_active_advisorships": 0,
            "total_monthly_investment": 0.0,
            "program_distribution": Counter(),
            "investment_per_program": Counter(),
            "volunteer_count": 0,
        }

        supervisors_counter = Counter()

        for p in projects:
            # We also process "Sem Projeto Associado" if it has advisorships
            if not p.get("advisorships"):
                continue

            if p.get("id"):  # Real projects
                global_stats["total_projects"] += 1

            p_metrics = {
                "id": p.get("id"),
                "name": p.get("name"),
                "total_students": len(p["advisorships"]),
                "active_students": 0,
                "monthly_investment": 0.0,
                "main_program": "N/A",
                "team_size": len(p.get("team", [])),
            }

            p_programs = Counter()

            for adv in p["advisorships"]:
                global_stats["total_advisorships"] += 1

                # Active Status
                if adv.get("status") == "Active":
                    p_metrics["active_students"] += 1
                    global_stats["total_active_advisorships"] += 1

                # Fellowship Info
                fell = adv.get("fellowship")
                if fell:
                    prog_name = fell.get("name", "Unknown")
                    val = fell.get("value", 0.0)

                    p_metrics["monthly_investment"] += val
                    global_stats["total_monthly_investment"] += val

                    p_programs[prog_name] += 1
                    global_stats["program_distribution"][prog_name] += 1
                    global_stats["investment_per_program"][prog_name] += val

                if not fell or fell.get("value", 0.0) == 0.0:
                    global_stats["volunteer_count"] += 1

                # Supervisor Stats
                sup_name = adv.get("supervisor_name")
                if sup_name:
                    supervisors_counter[sup_name] += 1

            if p_programs:
                p_metrics["main_program"] = p_programs.most_common(1)[0][0]

            if p.get("id"):
                mart_projects.append(p_metrics)

        # Finalizing global stats
        participation_ratio = (
            global_stats["total_advisorships"] / global_stats["total_projects"]
            if global_stats["total_projects"] > 0
            else 0
        )
        volunteer_percentage = (
            (global_stats["volunteer_count"] / global_stats["total_advisorships"]) * 100
            if global_stats["total_advisorships"] > 0
            else 0
        )

        global_stats.update(
            {
                "program_distribution": dict(global_stats["program_distribution"]),
                "investment_per_program": dict(global_stats["investment_per_program"]),
                "participation_ratio": round(participation_ratio, 2),
                "volunteer_percentage": round(volunteer_percentage, 2),
                "total_monthly_investment": round(
                    global_stats["total_monthly_investment"], 2
                ),
            }
        )

        # Rankings
        rankings = {
            "top_supervisors": [
                {"name": name, "count": count}
                for name, count in supervisors_counter.most_common(10)
            ],
            "top_projects_by_investment": sorted(
                [
                    {"name": p["name"], "value": round(p["monthly_investment"], 2)}
                    for p in mart_projects
                ],
                key=lambda x: x["value"],
                reverse=True,
            )[:10],
        }

        final_mart = {
            "projects": mart_projects,
            "global_stats": global_stats,
            "rankings": rankings,
            "generated_at": datetime.now().isoformat(),
        }

        self.sink.export([final_mart], output_path)
        logger.info(
            f"Successfully generated Advisorship Analytics Mart to {output_path}"
        )
