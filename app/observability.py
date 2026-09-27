import logging

logger = logging.getLogger(__name__)


def log_invocation(model, outcome, gateway_status, elapsed_ms, app_name, api_key_id):
    level = logging.INFO if outcome == "success" else logging.WARNING

    logger.log(
        level,
        "invoke_completed model=%s outcome=%s gateway_status=%s "
        "elapsed_ms=%.1f app_name=%s api_key_id=%s",
        model,
        outcome,
        gateway_status,
        elapsed_ms,
        app_name,
        api_key_id,
    )
