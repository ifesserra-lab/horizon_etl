"""Nulls out polluted persons.identification_id values.

Two ingestion paths historically wrote non-CPF data into identification_id
(a CPF-like identity column, LGPD-hashed on write by the session hook):

- CNPq group sync passed the member NAME  -> stored as anonymize_cpf(name)
- SigPesq excel passed the leader EMAIL   -> stored as anonymize_cpf(email)

Both are recomputable, so pollution is detected deterministically:

- name-hash:  identification_id == anonymize_cpf(person.name)
- email-hash: sha256 digest prefix shared with one of the person's own
  anonymized emails (anonymize_cpf and anonymize_email hash the same source
  string; the first 12 hex chars of the digest coincide)

Legitimate values are kept:

- lattes-hash: identification_id == anonymize_cpf(lattes_id from cnpq_url)
- anything else (unknown provenance, e.g. a real hashed CPF)

Usage:
    python scripts/cleanup_fake_identifications.py [--apply] [--db db/horizon.db]

Default is dry-run; pass --apply to write.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.logic.pii_anonymizer import anonymize_cpf  # noqa: E402


def classify(conn: sqlite3.Connection) -> dict[str, list[int]]:
    rows = conn.execute(
        """
        SELECT p.id, p.name, p.identification_id, r.cnpq_url
        FROM persons p
        LEFT JOIN researchers r ON r.id = p.id
        WHERE p.identification_id IS NOT NULL AND p.identification_id != ''
        """
    ).fetchall()

    emails_by_person: dict[int, list[str]] = {}
    for pid, email in conn.execute("SELECT person_id, email FROM person_emails"):
        emails_by_person.setdefault(pid, []).append(email or "")

    buckets: dict[str, list[int]] = {
        "fake_name_hash": [],
        "fake_email_hash": [],
        "legit_lattes_hash": [],
        "unknown": [],
    }

    for pid, name, ident, cnpq_url in rows:
        ident = ident.strip()

        name_candidates = {name or "", (name or "").strip()}
        if ident in {anonymize_cpf(n) for n in name_candidates if n}:
            buckets["fake_name_hash"].append(pid)
            continue

        if ident.startswith("LGPD-"):
            digest16 = ident[len("LGPD-") :]
            email_prefixes = {
                e.split("@", 1)[0]
                for e in emails_by_person.get(pid, [])
                if e.endswith("@anon.lgpd")
            }
            if any(digest16.startswith(prefix) for prefix in email_prefixes if prefix):
                buckets["fake_email_hash"].append(pid)
                continue

        lattes_id = (cnpq_url or "").rstrip("/").rsplit("/", 1)[-1].strip()
        if lattes_id.isdigit() and ident == anonymize_cpf(lattes_id):
            buckets["legit_lattes_hash"].append(pid)
            continue

        buckets["unknown"].append(pid)

    return buckets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="db/horizon.db")
    parser.add_argument(
        "--apply", action="store_true", help="write changes (default: dry-run)"
    )
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        buckets = classify(conn)
        for label, ids in buckets.items():
            print(f"{label}: {len(ids)}")

        to_null = buckets["fake_name_hash"] + buckets["fake_email_hash"]
        if not args.apply:
            print(
                f"\nDry-run: would NULL identification_id of {len(to_null)} persons. "
                "Re-run with --apply."
            )
            return

        with conn:
            conn.executemany(
                "UPDATE persons SET identification_id = NULL WHERE id = ?",
                [(pid,) for pid in to_null],
            )
        print(f"\nApplied: identification_id set to NULL for {len(to_null)} persons.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
