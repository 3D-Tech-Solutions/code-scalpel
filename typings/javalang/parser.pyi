# Type stubs for javalang.parser module

class JavaSyntaxError(Exception):
    position: tuple[int, int] | None
    description: str
