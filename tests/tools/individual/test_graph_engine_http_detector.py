"""
Tests for HTTP link detector.

[20251216_FEATURE] v2.1.0 - Test HTTP link detection between client and server
"""

from code_scalpel.graph_engine.http_detector import (
    HTTP_CLIENT_PATTERNS,
    HTTP_ENDPOINT_PATTERNS,
    HTTPLink,
    HTTPLinkDetector,
    HTTPMethod,
    RoutePatternMatcher,
)


class TestHTTPMethod:
    """Tests for HTTPMethod enum."""

    def test_all_methods_defined(self):
        """Test all common HTTP methods are defined."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

        for method in methods:
            http_method = HTTPMethod(method)
            assert http_method.value == method


class TestHTTPPatterns:
    """Tests for HTTP pattern constants."""

    def test_client_patterns_defined(self):
        """Test client-side patterns are defined for all languages."""
        assert "javascript" in HTTP_CLIENT_PATTERNS
        assert "typescript" in HTTP_CLIENT_PATTERNS
        assert "python" in HTTP_CLIENT_PATTERNS

        # Check specific patterns
        assert "fetch" in HTTP_CLIENT_PATTERNS["javascript"]
        assert "axios" in HTTP_CLIENT_PATTERNS["typescript"]

    def test_endpoint_patterns_defined(self):
        """Test server-side patterns are defined for all languages."""
        assert "java" in HTTP_ENDPOINT_PATTERNS
        assert "python" in HTTP_ENDPOINT_PATTERNS
        assert "typescript" in HTTP_ENDPOINT_PATTERNS

        # Check specific patterns
        assert "@GetMapping" in HTTP_ENDPOINT_PATTERNS["java"]
        assert "@app.route" in HTTP_ENDPOINT_PATTERNS["python"]


class TestRoutePatternMatcher:
    """Tests for RoutePatternMatcher class."""

    def test_exact_match(self):
        """Test exact route matching."""
        matcher = RoutePatternMatcher()

        matches, confidence, match_type = matcher.match_routes("/api/users", "/api/users")

        assert matches is True
        assert confidence == 0.95
        assert match_type == "exact"

    def test_pattern_match_with_path_parameter(self):
        """Test pattern matching with path parameters."""
        matcher = RoutePatternMatcher()

        matches, confidence, match_type = matcher.match_routes("/api/users/123", "/api/users/{id}")

        assert matches is True
        assert confidence == 0.8
        assert match_type == "pattern"

    def test_pattern_match_multiple_parameters(self):
        """Test pattern matching with multiple parameters."""
        matcher = RoutePatternMatcher()

        matches, confidence, match_type = matcher.match_routes(
            "/api/users/123/posts/456", "/api/users/{userId}/posts/{postId}"
        )

        assert matches is True
        assert match_type == "pattern"

    def test_dynamic_route_match(self):
        """Test matching dynamic routes."""
        matcher = RoutePatternMatcher()

        # Dynamic route with concatenation (using literal string to represent dynamic route)
        matches, confidence, match_type = matcher.match_routes("/api/v1/users", '"/api/" + version + "/users"')

        # Should detect as dynamic match only
        assert match_type == "dynamic"  # [20251216_BUGFIX] Test must require dynamic match type for dynamic routes

    def test_no_match_different_routes(self):
        """Test non-matching routes."""
        matcher = RoutePatternMatcher()

        matches, confidence, match_type = matcher.match_routes("/api/users", "/api/posts")

        assert matches is False
        assert confidence == 0.0
        assert match_type == "none"

    def test_is_dynamic_route_with_concatenation(self):
        """Test detecting dynamic routes with concatenation."""
        matcher = RoutePatternMatcher()

        # Use string representation of dynamic route (not evaluated Python)
        assert matcher._is_dynamic_route('"/api/" + version + "/users"') is True
        assert matcher._is_dynamic_route("/api/users") is False

    def test_is_dynamic_route_with_template_literal(self):
        """Test detecting template literal routes."""
        matcher = RoutePatternMatcher()

        assert matcher._is_dynamic_route("${baseUrl}/api/users") is True
        assert matcher._is_dynamic_route("/api/users") is False


class TestHTTPLink:
    """Tests for HTTPLink dataclass."""

    def test_create_http_link(self):
        """Test creating an HTTP link."""
        link = HTTPLink(
            client_id="typescript::fetchUsers",
            endpoint_id="java::UserController:getUser",
            method=HTTPMethod.GET,
            client_route="/api/users",
            endpoint_route="/api/users",
            confidence=0.95,
            match_type="exact",
            evidence="Route string match: GET /api/users",
        )

        assert link.client_id == "typescript::fetchUsers"
        assert link.endpoint_id == "java::UserController:getUser"
        assert link.method == HTTPMethod.GET
        assert link.confidence == 0.95

    def test_http_link_to_dict(self):
        """Test converting HTTP link to dictionary."""
        link = HTTPLink(
            client_id="typescript::fetchUsers",
            endpoint_id="java::UserController:getUser",
            method=HTTPMethod.GET,
            client_route="/api/users",
            endpoint_route="/api/users",
            confidence=0.95,
            match_type="exact",
            evidence="Route match",
        )

        d = link.to_dict()
        assert d["client_id"] == "typescript::fetchUsers"
        assert d["endpoint_id"] == "java::UserController:getUser"
        assert d["method"] == "GET"
        assert d["confidence"] == 0.95


class TestHTTPLinkDetector:
    """Tests for HTTPLinkDetector class."""

    def test_create_detector(self):
        """Test creating an HTTP link detector."""
        detector = HTTPLinkDetector()

        assert len(detector.client_calls) == 0
        assert len(detector.endpoints) == 0

    def test_add_client_call(self):
        """Test adding a client-side HTTP call."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUsers",
            method="GET",
            route="/api/users",
        )

        assert len(detector.client_calls) == 1
        assert detector.client_calls[0]["node_id"] == "typescript::fetchUsers"
        assert detector.client_calls[0]["method"] == HTTPMethod.GET

    def test_add_client_call_with_http_method_enum(self):
        """Test adding client call with HTTPMethod enum."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUsers",
            method=HTTPMethod.GET,
            route="/api/users",
        )

        assert detector.client_calls[0]["method"] == HTTPMethod.GET

    def test_add_endpoint(self):
        """Test adding a server-side endpoint."""
        detector = HTTPLinkDetector()

        detector.add_endpoint(
            node_id="java::UserController:getUser",
            method="GET",
            route="/api/users",
        )

        assert len(detector.endpoints) == 1
        assert detector.endpoints[0]["node_id"] == "java::UserController:getUser"

    def test_detect_links_exact_match(self):
        """Test detecting links with exact route match."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_endpoint(
            node_id="java::UserController:getUser",
            method="GET",
            route="/api/users",
        )

        links = detector.detect_links()

        assert len(links) == 1
        assert links[0].client_id == "typescript::fetchUsers"
        assert links[0].endpoint_id == "java::UserController:getUser"
        assert links[0].confidence == 0.95
        assert links[0].match_type == "exact"

    def test_detect_links_pattern_match(self):
        """Test detecting links with pattern match."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUser",
            method="GET",
            route="/api/users/123",
        )

        detector.add_endpoint(
            node_id="java::UserController:getUser",
            method="GET",
            route="/api/users/{id}",
        )

        links = detector.detect_links()

        assert len(links) == 1
        assert links[0].confidence == 0.8
        assert links[0].match_type == "pattern"

    def test_detect_links_no_match_different_methods(self):
        """Test that different HTTP methods don't match."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_endpoint(
            node_id="java::UserController:createUser",
            method="POST",
            route="/api/users",
        )

        links = detector.detect_links()

        assert len(links) == 0

    def test_detect_links_no_match_different_routes(self):
        """Test that different routes don't match."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_endpoint(
            node_id="java::PostController:getPosts",
            method="GET",
            route="/api/posts",
        )

        links = detector.detect_links()

        assert len(links) == 0

    def test_detect_links_multiple_clients_same_endpoint(self):
        """Test multiple clients calling same endpoint."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_client_call(
            node_id="javascript::loadUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_endpoint(
            node_id="java::UserController:getUser",
            method="GET",
            route="/api/users",
        )

        links = detector.detect_links()

        assert len(links) == 2

    def test_get_unmatched_clients(self):
        """Test getting unmatched client calls."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_client_call(
            node_id="typescript::fetchPosts",
            method="GET",
            route="/api/posts",
        )

        detector.add_endpoint(
            node_id="java::UserController:getUser",
            method="GET",
            route="/api/users",
        )

        unmatched = detector.get_unmatched_clients()

        assert len(unmatched) == 1
        assert unmatched[0]["node_id"] == "typescript::fetchPosts"

    def test_get_unmatched_endpoints(self):
        """Test getting unmatched endpoints."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_endpoint(
            node_id="java::UserController:getUser",
            method="GET",
            route="/api/users",
        )

        detector.add_endpoint(
            node_id="java::PostController:getPosts",
            method="GET",
            route="/api/posts",
        )

        unmatched = detector.get_unmatched_endpoints()

        assert len(unmatched) == 1
        assert unmatched[0]["node_id"] == "java::PostController:getPosts"

    def test_build_evidence(self):
        """Test evidence string building."""
        detector = HTTPLinkDetector()

        detector.add_client_call(
            node_id="typescript::fetchUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_endpoint(
            node_id="java::UserController:getUser",
            method="GET",
            route="/api/users",
        )

        links = detector.detect_links()

        assert "GET" in links[0].evidence
        assert "/api/users" in links[0].evidence


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    def test_frontend_backend_connection(self):
        """Test complete frontend-to-backend connection scenario."""
        detector = HTTPLinkDetector()

        # Frontend TypeScript calls
        detector.add_client_call(
            node_id="typescript::src/api/client::function::fetchUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_client_call(
            node_id="typescript::src/api/client::function::createUser",
            method="POST",
            route="/api/users",
        )

        # Backend Java endpoints
        detector.add_endpoint(
            node_id="java::com.example.api::controller::UserController:getUsers",
            method="GET",
            route="/api/users",
        )

        detector.add_endpoint(
            node_id="java::com.example.api::controller::UserController:createUser",
            method="POST",
            route="/api/users",
        )

        links = detector.detect_links()

        # Should have 2 links (GET and POST)
        assert len(links) == 2

        # Check GET link
        get_links = [link for link in links if link.method == HTTPMethod.GET]
        assert len(get_links) == 1
        assert get_links[0].confidence >= 0.9

        # Check POST link
        post_links = [link for link in links if link.method == HTTPMethod.POST]
        assert len(post_links) == 1
        assert post_links[0].confidence >= 0.9

    def test_pattern_based_rest_api(self):
        """Test RESTful API with path parameters."""
        detector = HTTPLinkDetector()

        # Client calls with IDs
        detector.add_client_call(
            node_id="typescript::getUserById",
            method="GET",
            route="/api/users/42",
        )

        detector.add_client_call(
            node_id="typescript::updateUser",
            method="PUT",
            route="/api/users/42",
        )

        # Server endpoints with patterns
        detector.add_endpoint(
            node_id="java::UserController:getUser",
            method="GET",
            route="/api/users/{id}",
        )

        detector.add_endpoint(
            node_id="java::UserController:updateUser",
            method="PUT",
            route="/api/users/{id}",
        )

        links = detector.detect_links()

        # Should match both with pattern matching
        assert len(links) == 2

        for link in links:
            assert link.match_type == "pattern"
            assert link.confidence == 0.8
