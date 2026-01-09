from datetime import date, datetime
from typing import Any, Dict, List

from loguru import logger
from research_domain import (
    ResearcherController,
    ResearchGroupController,
    RoleController,
)


class CnpqSyncLogic:
    """
    Business logic for synchronizing CNPq data with the local database.
    """

    def __init__(self):
        self.rg_ctrl = ResearchGroupController()
        self.res_ctrl = ResearcherController()
        self.role_ctrl = RoleController()
        self._leader_role_id = None

    def _get_leader_role_id(self):
        if not self._leader_role_id:
            role = self.role_ctrl.get_or_create_leader_role()
            self._leader_role_id = role.id
        return self._leader_role_id

    def _parse_date(self, date_str: str) -> date:
        """Parses date from 'DD/MM/YYYY' format or returns today."""
        if not date_str:
            return date.today()
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except Exception:
            return date.today()

    def sync_group(self, group_id: Any, cnpq_data: Dict[str, Any]):
        """
        Updates group basic info from CNPq data using direct SQL to avoid ORM side effects.
        """
        try:
            # Update fields if present in cnpq_data
            nome_cnpq = cnpq_data.get("nome_grupo")
            
            # Patch: ignore 'CNPq' which is a header branding in some mirrors
            if nome_cnpq and nome_cnpq.upper() != "CNPQ":
                from sqlalchemy import text
                
                # Use direct SQL to avoid loading the object and potentially messing up relationships
                session = self.rg_ctrl._service._repository._session
                
                # Check current name first to avoid unnecessary updates
                check_query = text("SELECT name FROM research_groups WHERE id = :gid")
                current_name = session.execute(check_query, {"gid": group_id}).scalar()
                
                if current_name != nome_cnpq:
                    logger.info(f"Updating group name: '{current_name}' -> '{nome_cnpq}'")
                    update_query = text("UPDATE research_groups SET name = :nm WHERE id = :gid")
                    session.execute(update_query, {"nm": nome_cnpq, "gid": group_id})
                    session.commit()
                    logger.info(f"Group {group_id} name updated successfully.")
                else:
                    logger.debug(f"Group {group_id} name is already up to date.")

        except Exception as e:
            logger.error(f"Failed to sync group {group_id}: {e}")
            try:
                if hasattr(self, 'rg_ctrl'):
                     self.rg_ctrl._service._repository._session.rollback()
            except Exception:
                pass

    def sync_members(self, group_id: Any, members_data: List[Dict[str, Any]]):
        """
        Synchronizes members of a research group.
        """
        import unicodedata
        
        def normalize(text):
            if not text: return ""
            # NFC normalization + strip + lowercase for robust matching
            return unicodedata.normalize('NFC', str(text).strip()).lower()

        # Fetch all once to avoid N+1 and many session calls
        all_res = self.res_ctrl.get_all()
        # Create a map for quick lookup: norm -> researcher
        res_map = {}
        for r in all_res:
            if r.name:
                res_map[normalize(r.name)] = r
            if hasattr(r, 'identification_id') and r.identification_id:
                res_map[normalize(r.identification_id)] = r

        for m_data in members_data:
            name = m_data.get("name")
            if not name:
                continue

            try:
                # 1. Ensure Researcher exists
                search_name = normalize(name)
                researcher = res_map.get(search_name)

                if researcher:
                    logger.debug(f"Researcher '{name}' already exists (ID: {researcher.id}). Using existing.")
                else:
                    logger.info(f"Creating new researcher: {name}")
                    try:
                        # Use nested transaction to allow rollback of just this failure without invalidating the whole session
                        session = self.rg_ctrl._service._repository._session
                        session.begin_nested()
                        try:
                            researcher = self.res_ctrl.create_researcher(
                                name=name, identification_id=name
                            )
                            session.commit() # Commit the savepoint
                            # Add to map to handle potential duplicates within the SAME group
                            res_map[search_name] = researcher
                        except Exception as e:
                            session.rollback() # Rollback to savepoint
                            raise e # Re-raise to be caught by outer except
                    except Exception:
                        # If creation failed (likely UniqueViolation/IntegrityError), look it up directly
                        # get_all() might have missed it due to limits or race conditions
                        logger.warning(f"Creation failed for {name}, trying direct DB lookup.")
                        from sqlalchemy import text
                        session = self.rg_ctrl._service._repository._session
                        # Try to find by identification_id (most reliable for duplicates) or name
                        query = text("SELECT id, name FROM persons WHERE identification_id = :iid OR name = :nm")
                        row = session.execute(query, {"iid": name, "nm": name}).fetchone()
                        if row:
                            from research_domain.domain.entities import Researcher
                            researcher = Researcher(name=row[1])
                            researcher.id = row[0]
                            logger.info(f"Recovered existing researcher ID {researcher.id} for {name}")
                        else:
                            logger.error(f"Could not create nor find researcher {name}. Skipping.")
                            continue

                # 2. Get/Create Role
                role_name = m_data.get("role", "Pesquisador")
                # Try to find existing role
                role = None
                all_roles = self.role_ctrl.get_all()
                for r in all_roles:
                    if r.name.lower() == role_name.lower():
                        role = r
                        break

                if not role:
                    logger.info(f"Creating new role: {role_name}")
                    role = self.role_ctrl.create_role(name=role_name)

                # 3. Associate with group using the service's add_member
                start_date = self._parse_date(m_data.get("data_inicio"))
                end_date = (
                    self._parse_date(m_data.get("data_fim"))
                    if m_data.get("data_fim")
                    else None
                )

                try:
                    # Accessing service directly as controller doesn't expose generic add_member
                    # Check for existing membership to avoid duplicates
                    existing_members = self.rg_ctrl._service.get_members(group_id)
                    already_associated = False
                    for em in existing_members:
                        if em.person_id == researcher.id:
                            # Already associated. We could check role/dates here if needed.
                            # For now, let's just skip to avoid duplicates.
                            already_associated = True
                            break
                    
                    if not already_associated:
                        self.rg_ctrl._service.add_member(
                            team_id=group_id,
                            person_id=researcher.id,
                            role_id=role.id,
                            start_date=start_date,
                            end_date=end_date
                        )
                        logger.info(f"Member {name} ({role_name}) associated to group {group_id}")
                    else:
                        logger.debug(f"Member {name} already associated to group {group_id}. Skipping.")
                        
                except Exception as e:
                    logger.warning(f"Could not associate member {name}: {e}")
                    # Rollback for this specific association failure
                    try:
                        self.rg_ctrl._service._repository._session.rollback()
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"Error syncing member {name}: {e}")
                try:
                    self.rg_ctrl._service._repository._session.rollback()
                except Exception:
                    pass

        # Final commit for the whole group batch to be extra sure
        try:
            self.rg_ctrl._service._repository._session.commit()
        except Exception:
            pass
