import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from loguru import logger


def telegram_flow_state_handlers() -> dict[str, list]:
    return {
        "on_completion": [notify_telegram_flow_finished],
        "on_failure": [notify_telegram_flow_finished],
        "on_crashed": [notify_telegram_flow_finished],
        "on_cancellation": [notify_telegram_flow_finished],
    }


def notify_telegram_flow_finished(flow: Any, flow_run: Any, state: Any) -> bool:
    token = _getenv("HORIZON_TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
    chat_id = _getenv("HORIZON_TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.debug(
            "Telegram flow report skipped: HORIZON_TELEGRAM_BOT_TOKEN/"
            "TELEGRAM_BOT_TOKEN or HORIZON_TELEGRAM_CHAT_ID/TELEGRAM_CHAT_ID "
            "is not configured."
        )
        return False

    text = _build_flow_report(flow, flow_run, state)
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
        logger.warning(f"Failed to send Telegram flow report: {exc}")
        return False

    logger.info("Telegram flow report sent.")
    return True


def _getenv(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _build_flow_report(flow: Any, flow_run: Any, state: Any) -> str:
    state_name = getattr(state, "name", None) or getattr(state, "type", "Unknown")
    flow_name = getattr(flow, "name", "Unknown flow")
    run_name = getattr(flow_run, "name", None) or "unknown run"
    run_id = getattr(flow_run, "id", None)
    message = getattr(state, "message", None)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "Horizon ETL flow report",
        f"Flow: {flow_name}",
        f"Run: {run_name}",
        f"State: {state_name}",
        f"Finished at: {timestamp}",
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
