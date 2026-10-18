def is_model_allowed(
    model: str,
    allowed_models: list[str] | None,
) -> bool:

    if allowed_models is None:
        return True
    return model in allowed_models
