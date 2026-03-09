from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatTurn:
    user_message: str
    assistant_message: str


@dataclass
class CapturedQuestion:
    raw_message: str
    locale: str | None
    channel: str | None
    model: str | None
    received_at: datetime


@dataclass
class NormalizedRequest:
    request_id: str
    message: str
    locale: str
    channel: str
    model: str
    constraints: dict[str, float | int]
    meta: dict[str, datetime]


@dataclass
class ModelUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class ModelResult:
    request_id: str
    provider: str
    model: str
    answer_text: str
    finish_reason: str
    usage: ModelUsage
