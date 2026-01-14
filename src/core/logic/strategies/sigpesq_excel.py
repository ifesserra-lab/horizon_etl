import re
from typing import List, Optional, Tuple

import pandas as pd
from loguru import logger

from .base import (CampusStrategy, KnowledgeAreaStrategy, OrganizationStrategy,
                   ResearcherStrategy, ResearchGroupMappingStrategy,
                   RoleStrategy)


class SigPesqOrganizationStrategy(OrganizationStrategy):
    def ensure(self, uni_ctrl) -> int:
        """Ensures IFES exists."""
        try:
            all_orgs = uni_ctrl.get_all()
            for org in all_orgs:
                if org.name == "IFES":
                    logger.info(f"Organization found: {org.name} (ID: {org.id})")
                    return org.id
        except Exception as e:
            logger.error(f"Error fetching organizations: {e}")

        try:
            ufsc = uni_ctrl.create_university(
                name="IFES", short_name="Instituto Federal do Espirito Santo"
            )
            logger.info(f"Organization created: {ufsc.name} (ID: {ufsc.id})")
            return ufsc.id
        except Exception as e:
            logger.error(f"Failed to create organization: {e}")
            return None


class SigPesqCampusStrategy(CampusStrategy):
    def ensure(self, campus_ctrl, campus_name: str, org_id: int) -> int:
        """Ensures Campus exists."""
        try:
            all_campuses = campus_ctrl.get_all()
            for campus in all_campuses:
                c_org = getattr(campus, "organization_id", None)
                if campus.name == campus_name and (c_org is None or c_org == org_id):
                    logger.debug(f"Campus found: {campus.name}")
                    return campus.id
        except Exception as e:
            logger.error(f"Error fetching campuses: {e}")

        try:
            campus = campus_ctrl.create_campus(name=campus_name, organization_id=org_id)
            logger.info(f"Campus created: {campus.name} (ID: {campus.id})")
            return campus.id
        except Exception as e:
            logger.error(f"Error creating campus '{campus_name}': {e}")
            return None


class SigPesqKnowledgeAreaStrategy(KnowledgeAreaStrategy):
    def ensure(self, area_ctrl, area_name: str) -> Optional[int]:
        """Ensures Knowledge Area exists."""
        if not area_name or pd.isna(area_name):
            return None

        try:
            all_areas = area_ctrl.get_all()
            for area in all_areas:
                if area.name == area_name:
                    return area.id
        except Exception as e:
            logger.error(f"Error fetching areas: {e}")

        try:
            area = area_ctrl.create_knowledge_area(name=area_name)
            logger.info(f"Knowledge Area created: {area.name}")
            return area.id
        except Exception as e:
            logger.error(f"Error creating area '{area_name}': {e}")
            return None


class SigPesqResearcherStrategy(ResearcherStrategy):
    def ensure(self, researcher_ctrl, name: str, email: str = None):
        """Ensures a researcher exists using strict idempotency."""
        try:
            all_res = researcher_ctrl.get_all()
            # 1. Try to find by identification_id (email) - Primary Key logic for source
            if email:
                for res in all_res:
                    if getattr(res, "identification_id", None) == email:
                        logger.debug(f"Researcher found by email: {email}")
                        return res

            # 2. Fallback to name
            for res in all_res:
                if res.name == name:
                    logger.debug(f"Researcher found by name: {name}")
                    return res
        except Exception as e:
            logger.error(f"Error fetching researchers: {e}")

        try:
            emails = [email] if email else []
            res = researcher_ctrl.create_researcher(
                name=name, emails=emails, identification_id=email
            )
            logger.info(f"Researcher created: {name} (ID: {email})")
            return res
        except Exception as e:
            logger.error(f"Error creating researcher '{name}': {e}")
            return None


class SigPesqRoleStrategy(RoleStrategy):
    def ensure_leader(self, role_ctrl):
        """Ensures the Leader role exists."""
        try:
            role = role_ctrl.get_or_create_leader_role()
            logger.info(f"Role 'Leader' ensured (ID: {role.id})")
            return role
        except Exception as e:
            logger.error(f"Error ensuring leader role: {e}")
            return None


class SigPesqExcelMappingStrategy(ResearchGroupMappingStrategy):
    """Concrete strategy for mapping SigPesq Excel data."""

    def map_row(self, row: dict) -> dict:
        """Maps SigPesq Excel columns to standardized keys."""
        return {
            "name": row.get("Nome"),
            "short_name": row.get("Sigla"),
            "campus_name": row.get("Unidade"),
            "area_name": row.get("AreaConhecimento"),
            "site_url": row.get("Column1"),
            "leaders_raw": row.get("Lideres"),
        }

    def parse_leaders(self, leaders_str: str) -> List[Tuple[str, Optional[str]]]:
        """Parses leaders string in 'Name (email)' format."""
        if not leaders_str or pd.isna(leaders_str):
            return []

        parts = re.split(r"[,;]", str(leaders_str))
        leaders = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            match = re.match(r"^(.*?)\s*\((.*?)\)$", part)
            if match:
                name = match.group(1).strip()
                email = match.group(2).strip()
                leaders.append((name, email))
            else:
                leaders.append((part, None))
        return leaders
