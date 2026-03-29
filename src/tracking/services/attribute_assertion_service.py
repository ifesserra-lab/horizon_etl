from typing import Any, Optional

from libbase.services.generic_service import GenericService

from src.tracking.entities import AttributeAssertion


class AttributeAssertionService(GenericService[AttributeAssertion]):
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
        assertion = AttributeAssertion(
            source_record_id=source_record_id,
            canonical_entity_type=canonical_entity_type,
            canonical_entity_id=canonical_entity_id,
            attribute_name=attribute_name,
            value_json=value_json,
            value_hash=value_hash,
            is_selected=is_selected,
            selection_reason=selection_reason,
        )
        self.create(assertion)
        return assertion
