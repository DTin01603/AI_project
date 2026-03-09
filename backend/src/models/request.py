from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    locale: str | None = None
    channel: str | None = None
    model: str | None = None
