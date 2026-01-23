"""Type stubs for esprima.error_handler - Error handling."""

class Error(Exception):
    """Base error class for esprima parsing errors."""

    message: str
    name: str
    index: int
    lineNumber: int
    column: int
    description: str

    def __init__(
        self,
        message: str,
        index: int | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> None: ...

class ErrorHandler:
    """Error handler for the parser."""

    tolerant: bool
    errors: list[Error]

    def __init__(self) -> None: ...
    def recordError(self, error: Error) -> None: ...
    def tolerate(self, error: Error) -> None: ...
    def createError(
        self,
        index: int,
        line: int,
        col: int,
        description: str,
    ) -> Error: ...
    def throwError(
        self,
        index: int,
        line: int,
        col: int,
        description: str,
    ) -> None: ...
    def tolerateError(
        self,
        index: int,
        line: int,
        col: int,
        description: str,
    ) -> None: ...
