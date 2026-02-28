"""Exceptions for Agent system."""


class MaxIterationsExceeded(Exception):
    """Raised when tool call loop exceeds max iterations.

    This exception is raised when the agent's tool call loop
    exceeds the configured maximum number of iterations without
    producing a final response.

    Attributes:
        max_iterations: The maximum number of iterations allowed.

    Examples:
        >>> raise MaxIterationsExceeded(10)
        MaxIterationsExceeded: Tool call loop exceeded maximum of 10 iterations
    """

    def __init__(self, max_iterations: int) -> None:
        self.max_iterations = max_iterations
        super().__init__(
            f"Tool call loop exceeded maximum of {max_iterations} iterations"
        )
