"""Type stubs for esprima - ECMAScript parsing infrastructure."""

from typing import Any

def parseScript(
    code: str,
    options: dict[str, Any] | None = None,
    delegate: Any | None = None,
    *,
    jsx: bool = False,
    tolerant: bool = False,
    comment: bool = False,
    range: bool = False,
    loc: bool = False,
    tokens: bool = False,
) -> Any: ...
def parseModule(
    code: str,
    options: dict[str, Any] | None = None,
    delegate: Any | None = None,
    *,
    jsx: bool = False,
    tolerant: bool = False,
    comment: bool = False,
    range: bool = False,
    loc: bool = False,
    tokens: bool = False,
) -> Any: ...
def parse(
    code: str,
    options: dict[str, Any] | None = None,
    delegate: Any | None = None,
) -> Any: ...
def tokenize(
    code: str,
    options: dict[str, Any] | None = None,
) -> list[Any]: ...

__version__: str
