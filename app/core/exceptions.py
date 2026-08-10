class AIServiceError(Exception):
    """Base exception for AI service failures."""


class AITimeoutError(AIServiceError):
    """AI provider request timed out."""


class AIRateLimitError(AIServiceError):
    """AI provider rate limit was exceeded."""


class AIOutputValidationError(AIServiceError):
    """AI output could not be validated against the expected schema."""

class AIPrerequisiteError(Exception):
    """Required data for an AI operation is missing."""
