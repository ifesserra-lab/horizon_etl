from typing import Any, Optional

from libbase.controllers.generic_controller import GenericController

from src.tracking.entities import AttributeAssertion
from src.tracking.service_factory import TrackingServiceFactory
from src.tracking.services import AttributeAssertionService


class AttributeAssertionController(GenericController[AttributeAssertion]):
    def __init__(self, service: Optional[AttributeAssertionService] = None):
        super().__init__(
            service or TrackingServiceFactory.create_attribute_assertion_service()
        )

    def create_assertion(
        self,
        *,
        source_record_id: int,
        canonical_entity_type: str,
        canonical_entity_id: int,
        attribute_name: str,
        value_hash: str,
        value_json: Optional[Any] = None,
        is_selected: bool = False,
        selection_reason: Optional[str] = None,
    ) -> AttributeAssertion:
        return self._service.create_assertion(
            source_record_id=source_record_id,
            canonical_entity_type=canonical_entity_type,
            canonical_entity_id=canonical_entity_id,
            attribute_name=attribute_name,
            value_hash=value_hash,
            value_json=value_json,
            is_selected=is_selected,
            selection_reason=selection_reason,
        )
