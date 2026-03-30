import enum
from typing import Any

from research_domain.domain.entities import Advisorship, Fellowship


try:
    from research_domain.domain.entities import AdvisorshipRole
except ImportError:
    try:
        from research_domain.domain.entities.advisorship import AdvisorshipRole
    except ImportError:
        class AdvisorshipRole(enum.Enum):
            STUDENT = "Student"
            SUPERVISOR = "Supervisor"
            CO_SUPERVISOR = "Co-Supervisor"
            BOARD_MEMBER = "Board Member"


def advisorship_supports_members_api(advisorship: Any) -> bool:
    return hasattr(advisorship, "add_member") and hasattr(advisorship, "members")


__all__ = [
    "Advisorship",
    "AdvisorshipRole",
    "Fellowship",
    "advisorship_supports_members_api",
]
