import hashlib

SALT = b":horizon-lgpd-v1"

PII_COLUMN_REGISTRY: dict[str, str] = {
    "identification_id": "cpf",
    "email": "email",
    "contact_email": "email",
}


def anonymize_cpf(value: str | None) -> str | None:
    if not value:
        return None
    digest = hashlib.sha256(value.encode("utf-8") + SALT).hexdigest()
    return f"LGPD-{digest[:16]}"


def anonymize_email(value: str | None) -> str | None:
    if not value:
        return None
    digest = hashlib.sha256(value.encode("utf-8") + SALT).hexdigest()
    return f"{digest[:12]}@anon.lgpd"


def anonymize_field(value: str | None, field_type: str) -> str | None:
    if field_type == "cpf":
        return anonymize_cpf(value)
    if field_type == "email":
        return anonymize_email(value)
    return value


def anonymize_person_data(data: dict) -> dict:
    result = dict(data)
    for column, field_type in PII_COLUMN_REGISTRY.items():
        if column in result:
            result[column] = anonymize_field(result[column], field_type)
    return result


def is_anonymized_cpf(value: str | None) -> bool:
    return bool(value and value.startswith("LGPD-"))


def is_anonymized_email(value: str | None) -> bool:
    return bool(value and value.endswith("@anon.lgpd"))
