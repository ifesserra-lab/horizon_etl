"""Camada de compatibilidade com o pacote ``research_domain``.

Glossario de termos
-------------------
ResearchDomain:
    Biblioteca de dominio compartilhada que fornece entidades academicas, como
    orientacoes e bolsas, usadas pelos fluxos do Horizon ETL.

Compatibilidade:
    Adaptacao local para manter o ETL funcionando com versoes diferentes do
    ``research_domain`` enquanto nomes, caminhos de importacao ou APIs publicas
    ainda variam entre releases.

Advisorship:
    Entidade de orientacao academica. No ETL, representa relacoes entre
    estudante, supervisor, possiveis coorientadores e membros de banca.

Fellowship:
    Entidade de bolsa ou financiamento associado a uma orientacao ou iniciativa.

AdvisorshipRole:
    Enumeracao dos papeis que uma pessoa pode assumir dentro de uma orientacao.
    Este modulo tenta importar a enumeracao oficial e, se ela nao existir na
    versao instalada, fornece uma definicao minima com os papeis esperados pelo
    ETL.

Members API:
    API baseada em ``add_member`` e ``members`` para representar participantes
    de uma orientacao. Quando disponivel, ela substitui campos legados como
    ``student_id`` e ``supervisor_id``.

Fallback:
    Implementacao local usada apenas quando a versao instalada do
    ``research_domain`` nao oferece o simbolo esperado. O fallback preserva o
    contrato necessario para os fluxos do ETL sem alterar a biblioteca externa.
"""

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
