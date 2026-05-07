class SkillError(Exception):
    """Base error for skill framework."""


class SkillNotFoundError(SkillError):
    """Raised when a requested skill name is not registered."""


class SkillValidationError(SkillError):
    """Raised when inputs or outputs fail pydantic validation."""


class SkillInvocationError(SkillError):
    """Raised when a skill fails during prompt render or LLM call and fallback is unavailable."""


class SkillLoadError(SkillError):
    """Raised when a skill folder cannot be loaded at discovery time."""
