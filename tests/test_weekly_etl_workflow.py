from pathlib import Path


def test_weekly_etl_workflow_runs_weekly_flows_with_notifications():
    workflow = Path(".github/workflows/weekly-etl.yml").read_text()

    assert 'cron: "0 6 * * 6"' in workflow
    assert "workflow_dispatch:" in workflow
    assert (
        "HORIZON_TELEGRAM_BOT_TOKEN: ${{ secrets.HORIZON_TELEGRAM_BOT_TOKEN }}"
        in workflow
    )
    assert (
        "HORIZON_TELEGRAM_CHAT_ID: ${{ secrets.HORIZON_TELEGRAM_CHAT_ID }}" in workflow
    )
    assert "make weekly-flows" in workflow
    assert "make full-refresh" not in workflow


def test_makefile_weekly_flows_runs_sources_then_exports():
    makefile = Path("Makefile").read_text()

    target = makefile[makefile.index("weekly-flows:") : makefile.index("full-refresh:")]

    assert "weekly-flows: db-reset prefect-server" in target
    assert "app.py all_sources" in target
    assert "app.py export_canonical" in target
    assert "app.py ka_mart" in target
    assert (
        'app.py analytics_mart "$(OUTPUT_DIR)/initiatives_analytics_mart.json"'
        in target
    )
    assert 'app.py people_graph "$(OUTPUT_DIR)"' in target
