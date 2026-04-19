from src.flows.cnpq.groups import build_cnpq_sync_summary


def test_build_cnpq_sync_summary_reports_failed_groups():
    summary = build_cnpq_sync_summary(
        [
            {"success": True, "group_id": 1, "group_name": "Ok", "url": "http://ok"},
            {
                "success": False,
                "group_id": 2,
                "group_name": "Broken",
                "url": "http://broken",
            },
        ]
    )

    assert summary["total_groups"] == 2
    assert summary["success_count"] == 1
    assert summary["failed_count"] == 1
    assert summary["warnings"] == [
        {
            "source": "cnpq",
            "severity": "warning",
            "code": "cnpq_group_sync_failed",
            "count": 1,
            "examples": [
                {
                    "group_id": 2,
                    "group_name": "Broken",
                    "url": "http://broken",
                }
            ],
            "message": "CNPq sync failed for 1 group(s); inspect URLs or portal availability.",
        }
    ]
