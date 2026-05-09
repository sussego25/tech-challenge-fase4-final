class LLMInvokeError(Exception):
    """Raised when the LLM invocation fails."""


class LLMResponseParseError(Exception):
    """Raised when the LLM response cannot be parsed."""
