"""Scrubs PII from existing source_records.raw_payload_json rows.

Historically payloads were stored raw, so SigPesq advisorship records carry
real CPFs (OrientadoCpf), raw student/advisor emails and phone numbers.
Applies scrub_source_record_payload (CPF anonymized, phones nulled, emails
anonymized) to every stored payload. payload_hash is left untouched — it
hashes the original payload and keeps dedup semantics stable.

Usage:
    python scripts/scrub_payload_pii.py [--apply] [--db db/horizon.db]
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.logic.pii_anonymizer import scrub_source_record_payload  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="db/horizon.db")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        rows = conn.execute(
            "SELECT id, raw_payload_json FROM source_records WHERE raw_payload_json IS NOT NULL"
        ).fetchall()

        updates: list[tuple[str, int]] = []
        stats = {"total": len(rows), "changed": 0, "cpf": 0, "unparseable": 0}
        for rid, pj in rows:
            try:
                payload = json.loads(pj)
            except Exception:
                stats["unparseable"] += 1
                continue
            scrubbed = scrub_source_record_payload(payload)
            if scrubbed != payload:
                stats["changed"] += 1
                if (
                    isinstance(payload, dict)
                    and payload.get("OrientadoCpf") is not None
                ):
                    stats["cpf"] += 1
                updates.append((json.dumps(scrubbed, ensure_ascii=False), rid))

        print(
            f"payloads: {stats['total']}, com PII a limpar: {stats['changed']} "
            f"(com CPF: {stats['cpf']}), invalidos: {stats['unparseable']}"
        )

        if not args.apply:
            print("Dry-run. Re-run with --apply.")
            return

        with conn:
            conn.executemany(
                "UPDATE source_records SET raw_payload_json = ? WHERE id = ?",
                updates,
            )
        print(f"Applied: {len(updates)} payloads limpos.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
