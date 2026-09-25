"""
JARVIS V2 - Exception Hierarchy
Structured, typed domain exceptions for error classification and self-correction.
"""

class JarvisError(Exception):
    """Base exception for all Jarvis domain errors."""
    def __init__(self, message: str, recoverable: bool = False, details: dict = None):
        super().__init__(message)
        self.message = message
        self.recoverable = recoverable
        self.details = details or {}

class SecurityPolicyError(JarvisError):
    """Raised when an operation is rejected by policy engine."""
    pass

class ConfirmationDeniedError(JarvisError):
    """Raised when user denies explicit confirmation for sensitive action."""
    pass

class ToolExecutionError(JarvisError):
    """Raised when a tool encounters an unrecoverable execution failure."""
    pass

class ProviderUnavailableError(JarvisError):
    """Raised when an LLM provider times out or fails health check."""
    pass

class AcousticError(JarvisError):
    """Raised when microphone or audio hardware fails."""
    pass

class StorageError(JarvisError):
    """Raised when database or vector persistence fails."""
    pass
