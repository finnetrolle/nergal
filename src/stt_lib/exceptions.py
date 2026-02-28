"""Exceptions for the STT library.

This module defines a hierarchy of exceptions for Speech-to-Text operations.
The exceptions are independent and can be used without any other dependencies.
"""


class STTError(Exception):
    """Base exception for all STT errors.

    All custom exceptions in the STT library should inherit from this class.
    This allows catching all STT-specific errors with a single except clause.

    Attributes:
        message: Human-readable error description.
        cause: Optional underlying exception that caused this error.
    """

    def __init__(
        self,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error description.
            cause: Optional underlying exception that caused this error.
        """
        self.message = message
        self.cause = cause
        super().__init__(message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class STTConnectionError(STTError):
    """Error connecting to STT provider.

    Raised when network issues prevent reaching the STT API.
    """

    pass


class STTUnsupportedFormatError(STTError):
    """Error when audio format is not supported.

    Attributes:
        format: The unsupported audio format.
    """

    def __init__(
        self,
        message: str = "Unsupported audio format",
        format: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the unsupported format error.

        Args:
            message: Human-readable error description.
            format: The unsupported audio format.
            cause: Optional underlying exception.
        """
        self.format = format
        if format:
            message = f"{message}: {format}"
        super().__init__(message, cause)


class AudioTooLongError(STTError):
    """Error when audio duration exceeds maximum allowed.

    Attributes:
        duration_seconds: Actual duration of the audio.
        max_seconds: Maximum allowed duration.
    """

    def __init__(
        self,
        duration_seconds: float,
        max_seconds: int,
    ) -> None:
        """Initialize the audio too long error.

        Args:
            duration_seconds: Actual duration of the audio.
            max_seconds: Maximum allowed duration.
        """
        self.duration_seconds = duration_seconds
        self.max_seconds = max_seconds
        message = (
            f"Audio duration ({duration_seconds:.1f}s) exceeds maximum allowed ({max_seconds}s)"
        )
        super().__init__(message)
