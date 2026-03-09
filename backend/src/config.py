import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Simple Agent API"
    environment: str = "development"
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
    google_search_api_key: str | None = os.getenv("GOOGLE_SEARCH_API_KEY")
    google_search_engine_id: str | None = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    default_model: str = os.getenv("DEFAULT_MODEL", "gemini/gemini-2.5-flash")
    model_registry: list[str] = [
        "gemini/gemini-2.5-flash",
        "gemini/gemini-2.5-flash-lite",
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-8b-instant",
    ]
    default_temperature: float = 0.3
    default_max_output_tokens: int = int(os.getenv("DEFAULT_MAX_OUTPUT_TOKENS", "1200"))
    model_timeout_seconds: float = 30.0
    langgraph_checkpointer: str = os.getenv("LANGGRAPH_CHECKPOINTER", "sqlite")
    langgraph_db_path: str = os.getenv("LANGGRAPH_DB_PATH", "./checkpoints.db")
    postgres_connection_string: str | None = os.getenv("POSTGRES_CONNECTION_STRING")

    @staticmethod
    def model_provider(model: str) -> str:
        return model.split("/", 1)[0].strip().lower()

    @staticmethod
    def provider_model_name(model: str) -> str:
        if "/" in model:
            return model.split("/", 1)[1].strip()
        return model.strip()

    def is_model_available(self, model: str) -> bool:
        provider = self.model_provider(model)
        if provider in {"gemini", "google"}:
            return bool(self.gemini_api_key)
        if provider == "groq":
            return bool(self.groq_api_key)
        return False

    def active_llm_api_key(self, model: str) -> str | None:
        provider = self.model_provider(model)
        if provider in {"gemini", "google"}:
            return self.gemini_api_key
        if provider == "groq":
            return self.groq_api_key
        return None

    def available_models(self) -> list[str]:
        return [model for model in self.model_registry if self.is_model_available(model)]


settings = Settings()
