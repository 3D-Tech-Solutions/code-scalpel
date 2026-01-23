# Type stubs for javalang package
from . import ast as ast
from . import parser as parser
from . import tree as tree

class parse:
    @staticmethod
    def parse(code: str) -> tree.CompilationUnit: ...
