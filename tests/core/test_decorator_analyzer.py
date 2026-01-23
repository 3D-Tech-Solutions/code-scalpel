"""
Tests for TypeScript Decorator Analyzer.

[20251216_TEST] Tests for Feature 7: TypeScript Decorators + Metadata
"""

from code_scalpel.polyglot.typescript.decorator_analyzer import (
    Decorator,
    DecoratorAnalyzer,
    extract_decorators_from_code,
)


class TestDecoratorExtraction:
    """Test decorator extraction from TypeScript code."""

    def test_extract_class_decorator(self):
        """Test extraction of class-level decorators."""
        code = """
        @Controller('users')
        export class UserController {
            constructor() {}
        }
        """

        result = extract_decorators_from_code(code)

        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "UserController"
        assert len(result["classes"][0]["decorators"]) == 1

        decorator = result["classes"][0]["decorators"][0]
        assert decorator.name == "Controller"
        assert decorator.arguments == ["'users'"]
        assert decorator.is_factory is True

    def test_extract_multiple_class_decorators(self):
        """Test extraction of multiple decorators on a class."""
        code = """
        @Injectable()
        @Controller('users')
        export class UserController {}
        """

        result = extract_decorators_from_code(code)

        assert len(result["classes"]) == 1
        assert len(result["classes"][0]["decorators"]) == 2
        assert result["classes"][0]["decorators"][0].name == "Injectable"
        assert result["classes"][0]["decorators"][1].name == "Controller"

    def test_extract_method_decorator(self):
        """Test extraction of method-level decorators."""
        code = """
        export class UserController {
            @Get(':id')
            async getUser(id: string) {
                return {};
            }
        }
        """

        result = extract_decorators_from_code(code)

        assert len(result["methods"]) == 1
        assert result["methods"][0]["name"] == "getUser"
        assert len(result["methods"][0]["decorators"]) == 1

        decorator = result["methods"][0]["decorators"][0]
        assert decorator.name == "Get"
        assert decorator.arguments == ["':id'"]

    def test_extract_method_with_multiple_decorators(self):
        """Test extraction of multiple decorators on a method."""
        code = """
        export class UserController {
            @Post()
            @UseGuards(AuthGuard)
            async createUser() {}
        }
        """

        result = extract_decorators_from_code(code)

        assert len(result["methods"]) == 1
        assert len(result["methods"][0]["decorators"]) == 2
        assert result["methods"][0]["decorators"][0].name == "Post"
        assert result["methods"][0]["decorators"][1].name == "UseGuards"

    def test_extract_parameter_decorator(self):
        """Test extraction of parameter-level decorators."""
        code = """
        async getUser(@Param('id') id: string) {}
        """

        result = extract_decorators_from_code(code)

        assert len(result["parameters"]) == 1
        assert result["parameters"][0]["parameter_name"] == "id"
        assert result["parameters"][0]["decorator"].name == "Param"

    def test_decorator_factory_vs_simple(self):
        """Test distinction between decorator factories and simple decorators."""
        code = """
        @Injectable()
        @Sealed
        class Service {}
        """

        result = extract_decorators_from_code(code)

        decorators = result["classes"][0]["decorators"]
        assert decorators[0].is_factory is True  # @Injectable()
        assert decorators[1].is_factory is False  # @Sealed

    def test_nested_decorator_names(self):
        """Test decorators with namespaced names."""
        code = """
        @nestjs.Controller('users')
        class UserController {}
        """

        result = extract_decorators_from_code(code)

        assert len(result["classes"]) == 1
        decorator = result["classes"][0]["decorators"][0]
        assert decorator.name == "nestjs.Controller"

    def test_complex_decorator_arguments(self):
        """Test decorators with complex arguments."""
        code = """
        @UseGuards(AuthGuard, RolesGuard)
        class AdminController {}
        """

        result = extract_decorators_from_code(code)

        decorator = result["classes"][0]["decorators"][0]
        assert len(decorator.arguments) == 2
        assert "AuthGuard" in decorator.arguments[0]
        assert "RolesGuard" in decorator.arguments[1]


class TestSecuritySinkDetection:
    """Test security sink detection for decorators."""

    def test_post_decorator_is_security_sink(self):
        """Test that @Post is identified as a security sink."""
        analyzer = DecoratorAnalyzer()
        decorators = [Decorator(name="Post", arguments=[], is_factory=True, line=1)]

        assert analyzer.is_security_sink(decorators) is True

    def test_get_decorator_is_security_sink(self):
        """Test that @Get is identified as a security sink."""
        analyzer = DecoratorAnalyzer()
        decorators = [Decorator(name="Get", arguments=["':id'"], is_factory=True, line=1)]

        assert analyzer.is_security_sink(decorators) is True

    def test_delete_decorator_is_security_sink(self):
        """Test that @Delete is identified as a security sink."""
        analyzer = DecoratorAnalyzer()
        decorators = [Decorator(name="Delete", arguments=[], is_factory=True, line=1)]

        assert analyzer.is_security_sink(decorators) is True

    def test_query_decorator_is_security_sink(self):
        """Test that @Query is identified as a security sink."""
        analyzer = DecoratorAnalyzer()
        decorators = [Decorator(name="Query", arguments=[], is_factory=True, line=1)]

        assert analyzer.is_security_sink(decorators) is True

    def test_non_security_decorator(self):
        """Test that non-security decorators are not flagged."""
        analyzer = DecoratorAnalyzer()
        decorators = [
            Decorator(name="Injectable", arguments=[], is_factory=True, line=1),
            Decorator(name="Component", arguments=[], is_factory=True, line=1),
        ]

        assert analyzer.is_security_sink(decorators) is False

    def test_mixed_decorators(self):
        """Test that security sinks are detected in mixed decorator list."""
        analyzer = DecoratorAnalyzer()
        decorators = [
            Decorator(name="Injectable", arguments=[], is_factory=True, line=1),
            Decorator(name="Post", arguments=[], is_factory=True, line=2),
            Decorator(name="UseGuards", arguments=["AuthGuard"], is_factory=True, line=3),
        ]

        assert analyzer.is_security_sink(decorators) is True


class TestSecurityMetadata:
    """Test security metadata extraction from decorators."""

    def test_get_security_metadata_for_endpoint(self):
        """Test extraction of endpoint metadata."""
        analyzer = DecoratorAnalyzer()
        decorators = [Decorator(name="Get", arguments=["':id'"], is_factory=True, line=1)]

        metadata = analyzer.get_security_metadata(decorators)

        assert metadata["is_endpoint"] is True
        assert "GET" in metadata["http_methods"]
        assert ":id" in metadata["routes"]

    def test_get_security_metadata_for_controller(self):
        """Test extraction of controller metadata."""
        analyzer = DecoratorAnalyzer()
        decorators = [Decorator(name="Controller", arguments=["'users'"], is_factory=True, line=1)]

        metadata = analyzer.get_security_metadata(decorators)

        assert metadata["is_endpoint"] is True
        assert "users" in metadata["routes"]

    def test_get_security_metadata_for_auth(self):
        """Test extraction of authentication metadata."""
        analyzer = DecoratorAnalyzer()
        decorators = [Decorator(name="UseGuards", arguments=["AuthGuard"], is_factory=True, line=1)]

        metadata = analyzer.get_security_metadata(decorators)

        assert metadata["requires_auth"] is True

    def test_get_security_metadata_for_public(self):
        """Test extraction of public access metadata."""
        analyzer = DecoratorAnalyzer()
        decorators = [Decorator(name="Public", arguments=[], is_factory=True, line=1)]

        metadata = analyzer.get_security_metadata(decorators)

        assert metadata["requires_auth"] is False

    def test_get_security_metadata_combined(self):
        """Test extraction of combined security metadata."""
        analyzer = DecoratorAnalyzer()
        decorators = [
            Decorator(name="Controller", arguments=["'users'"], is_factory=True, line=1),
            Decorator(name="Post", arguments=[], is_factory=True, line=2),
            Decorator(name="UseGuards", arguments=["AuthGuard"], is_factory=True, line=3),
        ]

        metadata = analyzer.get_security_metadata(decorators)

        assert metadata["is_endpoint"] is True
        assert "POST" in metadata["http_methods"]
        assert metadata["requires_auth"] is True


class TestNestJSExample:
    """Test extraction from realistic NestJS code."""

    def test_nestjs_controller_example(self):
        """Test extraction from a complete NestJS controller example."""
        code = """
        @Controller('users')
        export class UserController {
            @Get(':id')
            @UseGuards(AuthGuard)
            async getUser(@Param('id') id: string): Promise<UserDto> {
                return this.userService.findById(id);
            }

            @Post()
            @UseGuards(AuthGuard)
            async createUser(@Body() data: CreateUserDto) {
                return this.userService.create(data);
            }
        }
        """

        result = extract_decorators_from_code(code)

        # Check class decorators
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "UserController"
        class_decorators = result["classes"][0]["decorators"]
        assert len(class_decorators) == 1
        assert class_decorators[0].name == "Controller"

        # Check method decorators
        assert len(result["methods"]) == 2

        # First method (getUser)
        get_method = result["methods"][0]
        assert get_method["name"] == "getUser"
        assert len(get_method["decorators"]) == 2
        assert get_method["decorators"][0].name == "Get"
        assert get_method["decorators"][1].name == "UseGuards"

        # Second method (createUser)
        post_method = result["methods"][1]
        assert post_method["name"] == "createUser"
        assert len(post_method["decorators"]) == 2
        assert post_method["decorators"][0].name == "Post"

        # Check parameter decorators
        assert len(result["parameters"]) >= 1
        param_id = [p for p in result["parameters"] if p["parameter_name"] == "id"]
        assert len(param_id) == 1
        assert param_id[0]["decorator"].name == "Param"

    def test_security_analysis_of_nestjs_code(self):
        """Test security analysis of NestJS controller."""
        code = """
        @Controller('users')
        export class UserController {
            @Post()
            @UseGuards(AuthGuard)
            async createUser(@Body() data: CreateUserDto) {
                return this.userService.create(data);
            }
        }
        """

        analyzer = DecoratorAnalyzer()
        result = extract_decorators_from_code(code)

        # Analyze method decorators
        method_decorators = result["methods"][0]["decorators"]

        # Check if it's a security sink
        assert analyzer.is_security_sink(method_decorators) is True

        # Get security metadata
        metadata = analyzer.get_security_metadata(method_decorators)
        assert metadata["is_endpoint"] is True
        assert "POST" in metadata["http_methods"]
        assert metadata["requires_auth"] is True


class TestAcceptanceCriteria:
    """Test acceptance criteria from the problem statement."""

    def test_extract_decorator_names_and_arguments(self):
        """Acceptance: Extract decorator names and arguments."""
        code = """
        @Controller('users')
        @UseGuards(AuthGuard, RolesGuard)
        class UserController {}
        """

        result = extract_decorators_from_code(code)
        decorators = result["classes"][0]["decorators"]

        # Check names
        assert decorators[0].name == "Controller"
        assert decorators[1].name == "UseGuards"

        # Check arguments
        assert "'users'" in decorators[0].arguments[0]
        assert len(decorators[1].arguments) == 2

    def test_preserve_decorator_metadata_for_security_analysis(self):
        """Acceptance: Preserve decorator metadata for security analysis."""
        code = """
        @Post('create')
        async createUser() {}
        """

        analyzer = DecoratorAnalyzer()
        result = extract_decorators_from_code(code)
        decorators = result["methods"][0]["decorators"]

        # Check metadata is preserved
        assert decorators[0].metadata is not None
        assert "raw_args" in decorators[0].metadata

        # Check security analysis works
        assert analyzer.is_security_sink(decorators) is True

    def test_support_class_method_parameter_decorators(self):
        """Acceptance: Support class, method, and parameter decorators."""
        code = """
        @Controller('users')
        export class UserController {
            @Get(':id')
            async getUser(@Param('id') id: string) {}
        }
        """

        result = extract_decorators_from_code(code)

        # Class decorators
        assert len(result["classes"]) > 0
        assert len(result["classes"][0]["decorators"]) > 0

        # Method decorators
        assert len(result["methods"]) > 0
        assert len(result["methods"][0]["decorators"]) > 0

        # Parameter decorators
        assert len(result["parameters"]) > 0

    def test_handle_decorator_factories_vs_simple(self):
        """Acceptance: Handle decorator factories (@Decorator() vs @Decorator)."""
        code = """
        @Injectable()
        @Sealed
        class Service {}
        """

        result = extract_decorators_from_code(code)
        decorators = result["classes"][0]["decorators"]

        # Check factory detection
        assert decorators[0].is_factory is True  # @Injectable()
        assert decorators[1].is_factory is False  # @Sealed
