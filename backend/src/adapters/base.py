from dataclasses import dataclass
from typing import Protocol


@dataclass
class AdapterOutput:
    answer_text: str
    finish_reason: str = "stop"
    input_tokens: int = 0
    output_tokens: int = 0


class BaseAdapter(Protocol):
    provider: str

    def invoke(
        self,
        *,
        model: str,
        messages: list,
        constraints: dict[str, float | int],
    ) -> AdapterOutput: ...
