import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from loguru import logger


def telegram_flow_state_handlers() -> dict[str, list]:
    return {
        "on_running": [notify_telegram_flow_started],
        "on_completion": [notify_telegram_flow_finished],
        "on_failure": [notify_telegram_flow_finished],
        "on_crashed": [notify_telegram_flow_finished],
        "on_cancellation": [notify_telegram_flow_finished],
    }


def notify_telegram_flow_started(flow: Any, flow_run: Any, state: Any) -> bool:
    text = _build_flow_report(
        flow,
        flow_run,
        state,
        title="Horizon ETL flow started",
        timestamp_label="Started at",
    )
    return send_telegram_message(text, success_log="Telegram flow start report sent.")


def notify_telegram_flow_finished(flow: Any, flow_run: Any, state: Any) -> bool:
    text = _build_flow_report(
        flow,
        flow_run,
        state,
        title="Horizon ETL flow report",
        timestamp_label="Finished at",
    )
    return send_telegram_message(text, success_log="Telegram flow report sent.")


def send_telegram_etl_report_summary(report: dict[str, Any]) -> bool:
    text = _build_etl_report_summary(report)
    return send_telegram_message(
        text,
        success_log="Telegram ETL final report summary sent.",
    )


def send_telegram_message(
    text: str,
    *,
    success_log: str = "Telegram message sent.",
) -> bool:
    token = _getenv("HORIZON_TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
    chat_id = _getenv("HORIZON_TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.debug(
            "Telegram flow report skipped: HORIZON_TELEGRAM_BOT_TOKEN/"
            "TELEGRAM_BOT_TOKEN or HORIZON_TELEGRAM_CHAT_ID/TELEGRAM_CHAT_ID "
            "is not configured."
        )
        return False

    payload = urlencode(
        {
            "chat_id": chat_id,
            "text": text[:4096],
            "disable_web_page_preview": "true",
        }
    ).encode()
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            response.read()
    except Exception as exc:
        logger.warning(f"Failed to send Telegram message: {exc}")
        return False

    logger.info(success_log)
    return True


def _getenv(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _build_flow_report(
    flow: Any,
    flow_run: Any,
    state: Any,
    *,
    title: str,
    timestamp_label: str,
) -> str:
    state_name = getattr(state, "name", None) or getattr(state, "type", "Unknown")
    flow_name = getattr(flow, "name", "Unknown flow")
    run_name = getattr(flow_run, "name", None) or "unknown run"
    run_id = getattr(flow_run, "id", None)
    message = getattr(state, "message", None)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        title,
        f"Flow: {flow_name}",
        f"Run: {run_name}",
        f"State: {state_name}",
        f"{timestamp_label}: {timestamp}",
    ]

    run_url = _build_prefect_run_url(run_id)
    if run_url:
        lines.append(f"Run URL: {run_url}")

    parameters = getattr(flow_run, "parameters", None)
    if parameters:
        lines.append(f"Parameters: {_format_parameters(parameters)}")

    if message:
        lines.append(f"Message: {str(message)[:500]}")

    return "\n".join(lines)


def _build_etl_report_summary(report: dict[str, Any]) -> str:
    steps = report.get("steps", [])
    success_count = sum(1 for step in steps if step.get("status") == "success")
    failed_steps = [
        step.get("step_name", "unknown")
        for step in steps
        if step.get("status") == "failed"
    ]
    failed_count = len(failed_steps)

    lines = [
        "Horizon ETL final report",
        f"Run: {report.get('run_name', 'unknown')}",
        f"Started at: {report.get('started_at', 'unknown')}",
        f"Finished at: {report.get('finished_at', 'unknown')}",
        f"Steps: {success_count} success, {failed_count} failed",
    ]

    duration = _sum_step_durations(steps)
    if duration is not None:
        lines.append(f"Total measured duration: {duration}s")

    saved_deltas = _sum_saved_entity_deltas(steps)
    if saved_deltas:
        lines.append(f"Saved deltas: {_format_key_values(saved_deltas)}")

    final_tables = report.get("final_tables") or {}
    if final_tables:
        lines.append(f"Final tables: {_format_key_values(final_tables)}")

    final_duplicates = report.get("final_duplicates") or {}
    if final_duplicates:
        lines.append(f"Final duplicates: {_format_key_values(final_duplicates)}")

    warnings_by_source = report.get("warnings_by_source") or {}
    warning_counts = _count_warnings_by_source(warnings_by_source)
    if warning_counts:
        lines.append(f"Warnings: {_format_key_values(warning_counts)}")

    tracking_totals = (report.get("tracking_summary") or {}).get("totals") or {}
    if tracking_totals:
        lines.append(f"Tracking: {_format_key_values(tracking_totals)}")

    if failed_steps:
        lines.append(f"Failed steps: {', '.join(failed_steps)}")

    report_path = report.get("report_path")
    if report_path:
        lines.append(f"Report: {Path(report_path)}")

    return "\n".join(lines)


def _sum_step_durations(steps: list[dict[str, Any]]) -> float | None:
    durations = [
        step.get("duration_seconds")
        for step in steps
        if isinstance(step.get("duration_seconds"), (int, float))
    ]
    if not durations:
        return None
    return round(sum(durations), 2)


def _sum_saved_entity_deltas(steps: list[dict[str, Any]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for step in steps:
        for row in step.get("saved_entities") or []:
            entity = row.get("entity")
            delta = row.get("delta")
            if not entity or not isinstance(delta, int):
                continue
            totals[entity] = totals.get(entity, 0) + delta
    return totals


def _format_key_values(values: dict[str, Any]) -> str:
    return ", ".join(f"{key}={values[key]}" for key in sorted(values))


def _count_warnings_by_source(
    warnings_by_source: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    return {
        source: len(warnings)
        for source, warnings in warnings_by_source.items()
        if warnings
    }


def _build_prefect_run_url(run_id: Any) -> str | None:
    if not run_id:
        return None

    ui_url = os.getenv("PREFECT_UI_URL")
    if not ui_url:
        api_url = os.getenv("PREFECT_API_URL")
        ui_url = api_url.removesuffix("/api") if api_url else None

    if not ui_url:
        return None

    return f"{ui_url.rstrip('/')}/runs/flow-run/{run_id}"


def _format_parameters(parameters: dict[str, Any]) -> str:
    parts = []
    for key, value in sorted(parameters.items()):
        parts.append(f"{key}={value!r}")
    return ", ".join(parts)
