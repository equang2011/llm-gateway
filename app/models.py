from typing import Literal

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class InvokeRequest(BaseModel):
    model: str
    messages: list[Message]


class InvokeResponse(BaseModel):
    model: str
    content: str
    finish_reason: str
    provider_model: str


class ModelInfo(BaseModel):
    alias: str
    provider_model: str


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
