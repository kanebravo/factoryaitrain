"""
Custom exceptions for the RFP Proposal Generator application.
"""

class RFPParserError(Exception):
    """Custom exception for errors during RFP parsing."""
    pass

class LLMGenerationError(Exception):
    """Custom exception for errors during LLM content generation."""
    def __init__(self, message: str, agent_name: str = "Unknown Agent"):
        super().__init__(message)
        self.agent_name = agent_name
        self.message = message

    def __str__(self):
        return f"Agent '{self.agent_name}': {self.message}"

class MermaidValidationError(LLMGenerationError):
    """Custom exception for errors during Mermaid script validation."""
    def __init__(self, message: str, agent_name: str = "TechnicalWriterAgent"):
        super().__init__(message, agent_name=agent_name)

    def __str__(self): # Overriding to be more specific if needed, or can rely on parent
        return f"Mermaid Validation Error (Agent '{self.agent_name}'): {self.message}"

class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass

class ProposalGenerationError(Exception):
    """A general wrapper for errors occurring during the main proposal generation flow."""
    def __init__(self, message: str, stage: str = "Unknown Stage", original_exception: Exception = None):
        super().__init__(message)
        self.stage = stage
        self.original_exception = original_exception
        self.message = message

    def __str__(self):
        if self.original_exception:
            return f"Proposal Generation Error at stage '{self.stage}': {self.message} (Caused by: {type(self.original_exception).__name__}: {self.original_exception})"
        return f"Proposal Generation Error at stage '{self.stage}': {self.message}"
