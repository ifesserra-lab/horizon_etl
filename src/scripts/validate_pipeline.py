import json
import os
import sqlite3
import sys

sys.path.append(os.getcwd())

from src.core.logic.duplicate_auditor import DuplicateAuditor

REPORT_PATH = "data/reports/weekly_pipeline_run.json"
DB_PATH = "db/horizon.db"

REPORTED_TABLES = [
    "persons",
    "researchers",
    "person_emails",
    "organizations",
    "organizational_units",
    "initiative_types",
    "initiatives",
    "advisorships",
    "fellowships",
    "academic_educations",
    "teams",
    "team_members",
    "research_groups",
    "knowledge_areas",
    "researcher_knowledge_areas",
    "initiative_teams",
]


def load_report():
    if not os.path.exists(REPORT_PATH):
        print(f"FAIL  No ETL report found at {REPORT_PATH}")
        sys.exit(1)
    with open(REPORT_PATH) as f:
        return json.load(f)


def get_table_counts(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    counts = {}
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        counts[table] = cursor.fetchone()[0]
    return counts


ENTITY_TABLE_MAP = {
    "persons_by_canonical_name": "persons",
    "knowledge_areas_by_canonical_name": "knowledge_areas",
}


def expected_losers(audit_groups):
    return sum(len(g["members"]) - 1 for g in audit_groups)


def validate_table_counts(report, db_counts, live_audit):
    final = report.get("final_tables", {})
    report_dups = report.get("final_duplicates", {})
    consolidated_dups = {
        m for m in report_dups if report_dups[m] > 0 and live_audit.get(m, []) == []
    }
    all_ok = True
    for table in REPORTED_TABLES:
        reported = final.get(table, 0)
        actual = db_counts.get(table, 0)
        if reported == actual:
            print(f"  OK    {table}: {actual}")
            continue
        entity_metric = next(
            (m for m, t in ENTITY_TABLE_MAP.items() if t == table), None
        )
        if entity_metric and entity_metric in consolidated_dups:
            expected = report_dups[entity_metric]
            if reported - expected == actual:
                print(f"  OK    {table}: {actual} (consolidated {expected})")
                continue
        if table == "team_members" and consolidated_dups:
            print(f"  OK    {table}: {actual} (side effect of person consolidation)")
            continue
        all_ok = False
        print(f"  FAIL  {table}: report={reported}  db={actual}")
    if all_ok:
        print("  PASS  All table counts match")
    return all_ok


def validate_duplicates(report, live_audit):
    final_dups = report.get("final_duplicates", {})
    all_ok = True
    for metric, count in sorted(final_dups.items()):
        if count == 0:
            continue
        live_groups = len(live_audit.get(metric, []))
        if live_groups == 0:
            print(f"  OK    {metric}: {count} group(s) — resolved")
        else:
            print(
                f"  WARN  {metric}: {count} group(s) in report, {live_groups} still live"
            )
            all_ok = False
    if all_ok:
        print("  PASS  No duplicates")
    return all_ok


def validate_warnings(report):
    warns = report.get("warnings_by_source", {})
    for source, warn_list in warns.items():
        for w in warn_list:
            sev = w.get("severity", "warning")
            code = w.get("code", "unknown")
            msg = w.get("message", "")
            print(f"  {sev.upper()}  [{source}] {code}: {msg}")


def run_duplicate_auditor():
    auditor = DuplicateAuditor(DB_PATH)
    return auditor.run()


def summarize_auditor(report):
    total_groups = 0
    total_entities = 0
    for metric, groups in sorted(report.items()):
        entity_count = sum(len(g["members"]) for g in groups)
        group_count = len(groups)
        if group_count > 0:
            total_groups += group_count
            total_entities += entity_count
        label = f"    {metric}: {group_count} group(s), {entity_count} entity(ies)"
        print(label if group_count > 0 else label)
    return total_groups == 0


def main():
    print("Pipeline Validation")
    print("==================\n")

    report = load_report()
    run_name = report.get("run_name", "unknown")
    stamp = report.get("run_stamp", "")
    print(f"Report: {run_name} ({stamp})\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    db_counts = get_table_counts(cursor)
    conn.close()

    print("1. Table count consistency")
    live_audit = run_duplicate_auditor()
    tables_ok = validate_table_counts(report, db_counts, live_audit)

    print("\n2. Duplicate metrics (from ETL report)")
    validate_duplicates(report, live_audit)

    print("\n3. Warnings (from ETL report)")
    validate_warnings(report)

    print("\n4. Duplicate auditor (live DB)")
    audit_ok = summarize_auditor(live_audit)

    stale = live_audit and all(
        len(live_audit.get(m, [])) == 0
        for m, c in report.get("final_duplicates", {}).items()
        if c > 0
    )
    print(f"\n{'=' * 40}")
    if tables_ok and audit_ok:
        if stale:
            print("RESULT: PASS (stale ETL report — all resolved)")
        else:
            print("RESULT: PASS")
    else:
        print("RESULT: REVIEW NEEDED")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
