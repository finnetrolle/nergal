"""Tool-specific exceptions.

This module provides exception classes for errors that may occur
during tool execution.

Example:
    >>> from nergal.tools.exceptions import ToolExecutionError
    ...
    >>> try:
    ...     result = await tool.execute(args)
    ... except ToolExecutionError as e:
    ...     print(f"Tool failed: {e}")
"""


class ToolError(Exception):
    """Base exception for tool-related errors.

    All tool-specific exceptions inherit from this base class.
    This allows for catching all tool-related errors with a single
    except clause.

    Attributes:
        message: Error message describing what went wrong.

    Examples:
        >>> try:
        ...     await tool.execute(args)
        ... except ToolError as e:
        ...     print(f"Tool error: {e}")
    """

    def __init__(self, message: str) -> None:
        """Initialize the tool error.

        Args:
            message: Error message describing what went wrong.
        """
        self.message = message
        super().__init__(message)


class ToolExecutionError(ToolError):
    """Error raised when tool execution fails.

    This exception is raised when a tool encounters an error
    during execution, such as:
    - File not found
    - Permission denied
    - Invalid arguments
    - External service unavailable

    Attributes:
        tool_name: Name of the tool that failed.
        message: Error message describing what went wrong.

    Examples:
        >>> from nergal.tools.exceptions import ToolExecutionError
        ...
        >>> if not os.path.exists(path):
        ...     raise ToolExecutionError(
        ...         tool_name="file_read",
        ...         message=f"File not found: {path}"
        ...     )
    """

    def __init__(self, tool_name: str, message: str) -> None:
        """Initialize the tool execution error.

        Args:
            tool_name: Name of the tool that failed.
            message: Error message describing what went wrong.
        """
        self.tool_name = tool_name
        # Call parent with just the message, store full representation separately
        super().__init__(message)
        self._full_message = f"[{tool_name}] {message}"

    def __str__(self) -> str:
        """Return string representation with tool name prefix."""
        return self._full_message


class ToolTimeoutError(ToolError):
    """Error raised when tool execution times out.

    This exception is raised when a tool takes longer than the
    allowed timeout to complete.

    Attributes:
        tool_name: Name of the tool that timed out.
        timeout: Timeout value in seconds.

    Examples:
        >>> try:
        ...     await asyncio.wait_for(tool.execute(args), timeout=30)
        ... except asyncio.TimeoutError:
        ...     raise ToolTimeoutError(
        ...         tool_name="shell_execute",
        ...         timeout=30
        ...     )
    """

    def __init__(self, tool_name: str, timeout: float) -> None:
        """Initialize the tool timeout error.

        Args:
            tool_name: Name of the tool that timed out.
            timeout: Timeout value in seconds.
        """
        self.tool_name = tool_name
        self.timeout = timeout
        super().__init__(f"[{tool_name}] Execution timed out after {timeout:.1f} seconds")


class ToolValidationError(ToolError):
    """Error raised when tool arguments fail validation.

    This exception is raised when the provided arguments to a tool
    do not match the expected schema or contain invalid values.

    Attributes:
        tool_name: Name of the tool with invalid arguments.
        field: Name of the field that failed validation (optional).
        message: Error message describing the validation failure.

    Examples:
        >>> if not isinstance(args.get("count"), int):
        ...     raise ToolValidationError(
        ...         tool_name="my_tool",
        ...         field="count",
        ...         message="count must be an integer"
        ...     )
    """

    def __init__(self, tool_name: str, field: str | None = None, message: str = "") -> None:
        """Initialize the tool validation error.

        Args:
            tool_name: Name of the tool with invalid arguments.
            field: Name of the field that failed validation (optional).
            message: Error message describing the validation failure.
        """
        self.tool_name = tool_name
        self.field = field
        self.message = message

        if field:
            msg = f"[{tool_name}] Validation failed for field '{field}': {message}"
        else:
            msg = f"[{tool_name}] Validation failed: {message}"

        super().__init__(msg)


class SecurityPolicyViolationError(ToolError):
    """Error raised when a tool violates security policy.

    This exception is raised when a tool attempts to perform an
    action that is not allowed by the security policy, such as:
    - Accessing files outside the workspace
    - Executing disallowed commands
    - Making requests to blocked domains

    Attributes:
        tool_name: Name of the tool that violated policy.
        reason: Description of why the action was denied.

    Examples:
        >>> if not policy.is_path_allowed(path):
        ...     raise SecurityPolicyViolationError(
        ...         tool_name="file_read",
        ...         reason="Path is outside workspace directory"
        ...     )
    """

    def __init__(self, tool_name: str, reason: str) -> None:
        """Initialize the security policy violation error.

        Args:
            tool_name: Name of the tool that violated policy.
            reason: Description of why the action was denied.
        """
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"[{tool_name}] Security policy violation: {reason}")
