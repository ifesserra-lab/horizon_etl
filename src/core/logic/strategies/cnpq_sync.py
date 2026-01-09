from datetime import date, datetime
from typing import Any, Dict, List

from loguru import logger
from research_domain import (
    ResearcherController,
    ResearchGroupController,
    RoleController,
    KnowledgeAreaController,
)


class CnpqSyncLogic:
    """
    Business logic for synchronizing CNPq data with the local database.
    """

    def __init__(self):
        self.rg_ctrl = ResearchGroupController()
        self.res_ctrl = ResearcherController()
        self.role_ctrl = RoleController()
        self.ka_ctrl = KnowledgeAreaController()
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
        from sqlalchemy import text
        
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
                
                # SELF-HEALING: Ensure it exists in 'researchers' table (Joined Inheritance fix)
                # The library might only be inserting into 'persons' if mapping is partial.
                try:
                    session = self.rg_ctrl._service._repository._session
                    # Check if exists in researchers
                    chk_res = text("SELECT 1 FROM researchers WHERE id = :rid")
                    is_researcher = session.execute(chk_res, {"rid": researcher.id}).scalar()
                    
                    if not is_researcher:
                        logger.info(f"Fixing missing 'researchers' row for ID {researcher.id}")
                        # Insert with just ID (other cols are URLs, nullable)
                        ins_res = text("INSERT INTO researchers (id) VALUES (:rid)")
                        session.execute(ins_res, {"rid": researcher.id})
                        session.commit()
                except Exception as e:
                    logger.warning(f"Failed to fix researchers table for {name}: {e}")
                    # Don't block flow
                    pass

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
                        # UPDATE LOGIC for Egressos
                        # If the member is already associated, check if we need to update the end_date
                        # This handles Active -> Egresso transition
                        try:
                            # We need to find the specific association to check dates
                            target_member = next((em for em in existing_members if em.person_id == researcher.id), None)
                            
                            if target_member:
                                current_end_date = target_member.end_date
                                # Check if end_date provided by CNPq is 'new' (we have it, DB doesn't)
                                # or different (CNPq has date, DB has different date)
                                
                                should_update = False
                                if end_date and current_end_date != end_date:
                                    should_update = True
                                
                                if should_update:
                                    logger.info(f"Updating member {name} dates: End {current_end_date} -> {end_date}")
                                    
                                    # Use direct SQL update for safety and to avoid ORM complexity with composite keys/relationships
                                    upd_query = text("""
                                        UPDATE team_members 
                                        SET end_date = :end_dt 
                                        WHERE team_id = :gid AND person_id = :pid
                                    """)
                                    session = self.rg_ctrl._service._repository._session
                                    session.execute(upd_query, {
                                        "end_dt": end_date,
                                        "gid": group_id,
                                        "pid": researcher.id
                                    })
                                    session.commit()
                                else:
                                    logger.debug(f"Member {name} up to date.")

                        except Exception as inner_e:
                            logger.warning(f"Failed to update member {name}: {inner_e}")
                        
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

    def sync_knowledge_areas(self, group_id: Any, lines_data: List[Dict[str, Any]]):
        """
        Syncs research lines as Knowledge Areas and associates them to the group.
        """
        import unicodedata
        from sqlalchemy import text

        def normalize(text):
            if not text: return ""
            return unicodedata.normalize('NFC', str(text).strip())

        if not lines_data:
            return

        try:
            # 1. Fetch/Create Knowledge Areas
            ka_map = {}
            all_kas = self.ka_ctrl.get_all()
            for ka in all_kas:
                if ka.name:
                    ka_map[normalize(ka.name).lower()] = ka

            processed_kas = []
            for line in lines_data:
                raw_name = line.get("nome_da_linha_de_pesquisa")
                if not raw_name:
                    continue
                
                norm_name = normalize(raw_name)
                key = norm_name.lower()
                
                ka = ka_map.get(key)
                if not ka:
                    logger.info(f"Creating new Knowledge Area: {norm_name}")
                    try:
                        ka = self.ka_ctrl.create_knowledge_area(name=norm_name)
                        ka_map[key] = ka # Update map
                    except Exception as e:
                        logger.error(f"Failed to create KA {norm_name}: {e}")
                        continue
                else:
                    logger.debug(f"Using existing KA: {ka.name}")

                if ka:
                    processed_kas.append(ka)

            # 2. Associate with Group (Direct SQL for safety/performance)
            session = self.rg_ctrl._service._repository._session
            
            for ka in processed_kas:
                try:
                    # Check existence
                    check_query = text("SELECT 1 FROM group_knowledge_areas WHERE group_id = :gid AND area_id = :aid")
                    exists = session.execute(check_query, {"gid": group_id, "aid": ka.id}).fetchone()
                    
                    if not exists:
                        logger.info(f"Associating KA '{ka.name}' to Group {group_id}")
                        ins_query = text("INSERT INTO group_knowledge_areas (group_id, area_id) VALUES (:gid, :aid)")
                        session.execute(ins_query, {"gid": group_id, "aid": ka.id})
                    else:
                        logger.debug(f"KA '{ka.name}' already associated to Group {group_id}")
                
                except Exception as e:
                    logger.error(f"Failed to associate KA {ka.id} to Group {group_id}: {e}")
                    # Don't rollback whole transaction, just skip this association? 
                    # Actually, if auto-commit isn't on, we might need to rollback sub-transaction if using Postgres
                    # But here likely wrapping inside outer transaction or session management.
                    # Safe pattern:
                    try:
                        session.rollback()
                    except:
                        pass
            
            session.commit()
            logger.info(f"Synced {len(processed_kas)} research lines/KAs for group {group_id}")

        except Exception as e:
            logger.error(f"Failed to sync knowledge areas for {group_id}: {e}")
            try:
                self.rg_ctrl._service._repository._session.rollback()
            except:
                pass
