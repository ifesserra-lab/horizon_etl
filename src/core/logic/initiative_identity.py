import unicodedata
from typing import Any, Iterable, Optional


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = unicodedata.normalize("NFD", str(value))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text)
    return " ".join(text.lower().split())


def build_identity_key(parts: Iterable[Any]) -> str:
    normalized_parts = [normalize_text(part) for part in parts]
    normalized_parts = [part for part in normalized_parts if part]
    return "|".join(normalized_parts)


def get_existing_initiative_identity(initiative: Any) -> Optional[str]:
    metadata = getattr(initiative, "metadata", None) or {}
    if isinstance(metadata, dict):
        identity = metadata.get("source_identity")
        if identity:
            return identity

    title = getattr(initiative, "name", None)
    if not title:
        return None

    return build_identity_key([title])
