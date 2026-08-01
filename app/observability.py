import logging

logger = logging.getLogger(__name__)


def log_invocation(model, outcome, gateway_status, elapsed_ms):
    level = logging.INFO if outcome == "success" else logging.WARNING

    logger.log(
        level,
        f"invoke_completed model={model} outcome={outcome} "
        f"gateway_status={gateway_status} elapsed_ms={elapsed_ms:.1f}",
    )
