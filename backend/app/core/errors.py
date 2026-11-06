class ResearchFlowError(Exception):
    """Base class for domain errors."""


class PolicyError(ResearchFlowError):
    """A source or action is blocked by robots/terms policy."""


class LLMUnavailable(ResearchFlowError):
    """No configured LLM provider is currently usable."""


class BudgetExceeded(ResearchFlowError):
    """A run or daily budget would be exceeded."""


class ValidationError(ResearchFlowError):
    """Structured output failed validation."""
