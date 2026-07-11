"""Repairs identity values corrupted by the LGPD re-hash bug.

The before_flush hook used to re-anonymize already-hashed values, so every
ORM update advanced persons.identification_id (and person_emails.email) one
step along a hash chain: h1 = H(seed), h2 = H(h1), ...

This script rebuilds the chains from every recoverable seed and repairs:

- seed = lattes_id (from researchers.cnpq_url)   -> reset to H(lattes_id)
- seed = real CPF   (from SigPesq payloads)      -> reset to H(cpf)
- seed = person name (CNPq pollution)            -> NULL (name is not an identity)
- seed = email      (SigPesq pollution)          -> NULL (email lives in person_emails)
- unrecoverable chain                            -> reported; NULLed only with --null-unknown

person_emails.email chains are reset to H1(raw_email) when the raw email is
recoverable from source payloads.

Usage:
    python scripts/repair_hash_chains.py [--apply] [--null-unknown] [--db db/horizon.db]
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hashlib  # noqa: E402

from src.core.logic.pii_anonymizer import SALT  # noqa: E402

MAX_DEPTH = 40

_EMAIL_FIELD_RE = re.compile(r'"(\w*[Ee]mail\w*)":\s*"([^"@]+@[^"]+)"')


def _h(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8") + SALT).hexdigest()
    return f"LGPD-{digest[:16]}"


def _h_email(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8") + SALT).hexdigest()
    return f"{digest[:12]}@anon.lgpd"


def _chain(seed: str, hash_fn) -> list[str]:
    out, h = [], seed
    for _ in range(MAX_DEPTH):
        h = hash_fn(h)
        out.append(h)
    return out


def collect_payload_seeds(conn: sqlite3.Connection) -> tuple[set[str], set[str]]:
    """Returns (cpf_seeds, email_seeds) from raw source payloads."""
    cpfs: set[str] = set()
    emails: set[str] = set()
    for (pj,) in conn.execute("SELECT raw_payload_json FROM source_records"):
        if not pj:
            continue
        if "Cpf" in pj or "cpf" in pj:
            try:
                d = json.loads(pj)
            except Exception:
                d = {}
            for k, v in d.items():
                if "cpf" in k.lower() and v is not None:
                    s = str(v).strip()
                    if s:
                        cpfs.add(s)
                        cpfs.add(s.zfill(11))
        for _field, email in _EMAIL_FIELD_RE.findall(pj):
            e = email.strip()
            if e and not e.endswith("@anon.lgpd"):
                emails.add(e)
                emails.add(e.lower())
    return cpfs, emails


def build_ident_index(
    conn: sqlite3.Connection, seed_conn: sqlite3.Connection
) -> dict[str, dict]:
    """chain-hash -> {kind, canonical} for every recoverable seed.

    seed_conn may point at a pre-scrub backup: after scrub_payload_pii runs,
    payloads no longer hold raw CPF/email seeds, so chains must be rebuilt
    from the backup while repairs are applied to the live DB.
    """
    index: dict[str, dict] = {}

    def register(seed: str, kind: str, canonical):
        for h in _chain(seed, _h):
            # first registration wins; lattes/cpf registered before name/email
            index.setdefault(h, {"kind": kind, "canonical": canonical})

    for (url,) in conn.execute(
        "SELECT cnpq_url FROM researchers WHERE cnpq_url IS NOT NULL AND cnpq_url != ''"
    ):
        lattes = url.rstrip("/").rsplit("/", 1)[-1].strip()
        if lattes.isdigit():
            register(lattes, "lattes", _h(lattes))

    cpfs, emails = collect_payload_seeds(seed_conn)
    for cpf in cpfs:
        register(cpf, "cpf", _h(cpf))

    for pid, name in conn.execute(
        "SELECT id, name FROM persons WHERE name IS NOT NULL"
    ):
        for variant in {name, name.strip(), name.upper(), name.strip().upper()}:
            if variant:
                register(variant, "name", None)

    for email in emails:
        register(email, "email", None)

    return index


def build_email_index(seed_conn: sqlite3.Connection) -> dict[str, str]:
    """chain-hash -> canonical H1(raw_email) for stored anonymized emails."""
    _, emails = collect_payload_seeds(seed_conn)
    index: dict[str, str] = {}
    for e in emails:
        canonical = _h_email(e)
        for h in _chain(e, _h_email):
            index.setdefault(h, canonical)
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="db/horizon.db")
    parser.add_argument(
        "--seed-db",
        default=None,
        help="DB to read raw CPF/email seeds from (use a pre-scrub "
        "backup when the live DB payloads were already scrubbed)",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--null-unknown",
        action="store_true",
        help="also NULL unrecoverable LGPD- identifications",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    seed_conn = sqlite3.connect(args.seed_db) if args.seed_db else conn
    try:
        ident_index = build_ident_index(conn, seed_conn)

        resets: list[tuple[str, int]] = []
        nulls: list[int] = []
        unknown: list[int] = []
        stats = {
            "lattes": 0,
            "cpf": 0,
            "name": 0,
            "email": 0,
            "unknown": 0,
            "already_ok": 0,
        }

        for pid, ident in conn.execute(
            "SELECT id, identification_id FROM persons "
            "WHERE identification_id LIKE 'LGPD-%'"
        ):
            info = ident_index.get(ident)
            if info is None:
                stats["unknown"] += 1
                unknown.append(pid)
                continue
            stats[info["kind"]] += 1
            if info["canonical"] is None:
                nulls.append(pid)
            elif info["canonical"] != ident:
                resets.append((info["canonical"], pid))
            else:
                stats["already_ok"] += 1

        email_index = build_email_index(seed_conn)
        email_resets: list[tuple[str, int]] = []
        email_unknown = 0
        for eid, email in conn.execute(
            "SELECT id, email FROM person_emails WHERE email LIKE '%@anon.lgpd'"
        ):
            canonical = email_index.get(email)
            if canonical is None:
                email_unknown += 1
            elif canonical != email:
                email_resets.append((canonical, eid))

        print("identification_id classification:", stats)
        print(f"  -> reset to canonical H1: {len(resets)}")
        print(f"  -> NULL (name/email pollution): {len(nulls)}")
        print(
            f"  -> unknown kept: {0 if args.null_unknown else len(unknown)}"
            f"{' (will NULL)' if args.null_unknown else ''}"
        )
        print(f"person_emails: reset {len(email_resets)}, unknown {email_unknown}")

        if not args.apply:
            print("\nDry-run. Re-run with --apply.")
            return

        with conn:
            # Free the unique index before re-assigning canonical values.
            all_touched = (
                [pid for _, pid in resets]
                + nulls
                + (unknown if args.null_unknown else [])
            )
            conn.executemany(
                "UPDATE persons SET identification_id = NULL WHERE id = ?",
                [(pid,) for pid in all_touched],
            )
            for canonical, pid in resets:
                clash = conn.execute(
                    "SELECT id FROM persons WHERE identification_id = ? AND id != ?",
                    (canonical, pid),
                ).fetchone()
                if clash:
                    print(
                        f"  ! canonical ident of person {pid} already used by {clash[0]}; left NULL"
                    )
                    continue
                conn.execute(
                    "UPDATE persons SET identification_id = ? WHERE id = ?",
                    (canonical, pid),
                )
            conn.executemany(
                "UPDATE person_emails SET email = ? WHERE id = ?",
                email_resets,
            )
        print("Applied.")
    finally:
        if seed_conn is not conn:
            seed_conn.close()
        conn.close()


if __name__ == "__main__":
    main()
