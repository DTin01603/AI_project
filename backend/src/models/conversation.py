from __future__ import annotations

from dataclasses import dataclass


_VALID_ROLES = frozenset({"user", "assistant", "system"})


@dataclass(frozen=True)
class Conversation:
    id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Message:
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str

    def __post_init__(self) -> None:
        if self.role not in _VALID_ROLES:
            raise ValueError(
                f"Invalid role {self.role!r}; expected one of {sorted(_VALID_ROLES)}"
            )
        if not self.content:
            raise ValueError("Message.content must be non-empty")
