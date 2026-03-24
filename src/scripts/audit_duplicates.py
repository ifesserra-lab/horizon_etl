import json
import os
import sys

sys.path.append(os.getcwd())

from src.core.logic.duplicate_auditor import DuplicateAuditor


def main():
    auditor = DuplicateAuditor("db/horizon.db")
    report = auditor.run()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
