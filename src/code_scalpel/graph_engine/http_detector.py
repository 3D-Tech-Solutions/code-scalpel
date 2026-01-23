"""
HTTP Link Detector - Connects frontend API calls to backend endpoints.

[20251216_FEATURE] v2.1.0 - HTTP link detection across frontend/backend boundaries

This module detects connections between frontend API calls (fetch, axios, etc.)
and backend endpoints (@GetMapping, @app.route, etc.). It analyzes:

- Client-side HTTP calls (JavaScript/TypeScript)
- Server-side endpoint definitions (Python/Java)
- Route matching with confidence scoring

Example:
    >>> detector = HTTPLinkDetector()
    >>> detector.add_client_call("typescript::fetchUsers", "GET", "/api/users")
    >>> detector.add_endpoint("java::UserController:getUser", "GET", "/api/users")
    >>> links = detector.detect_links()
    >>> for link in links:
    ...     print(f"{link.client_id} -> {link.endpoint_id}: {link.confidence}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


# [20251216_FEATURE] HTTP methods for route matching
class HTTPMethod(Enum):
    """HTTP request methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    # [20251216_BUGFIX] Add missing standard HTTP methods CONNECT and TRACE for completeness
    CONNECT = "CONNECT"
    TRACE = "TRACE"


# [20251216_FEATURE] Client-side HTTP patterns as per problem statement
HTTP_CLIENT_PATTERNS = {
    "javascript": ["fetch", "axios.get", "axios.post", "$http", "ajax"],
    "typescript": ["fetch", "axios", "HttpClient"],
    "python": ["requests.get", "requests.post", "httpx.get"],
}

# [20251216_FEATURE] Server-side endpoint patterns as per problem statement
HTTP_ENDPOINT_PATTERNS = {
    "java": ["@GetMapping", "@PostMapping", "@RequestMapping", "@RestController"],
    "python": ["@app.route", "@router.get", "@api_view"],
    "typescript": ["@Get", "@Post", "@Controller"],
}


# [20251216_FEATURE] HTTP link between client and server
@dataclass
class HTTPLink:
    """
    A detected link between a client API call and a server endpoint.

    Attributes:
        client_id: Universal node ID of client call
        endpoint_id: Universal node ID of server endpoint
        method: HTTP method
        client_route: Route string from client
        endpoint_route: Route string from endpoint
        confidence: Confidence score (0.0-1.0)
        match_type: Type of route match (exact, pattern, dynamic)
        evidence: Human-readable explanation
    """

    client_id: str
    endpoint_id: str
    method: HTTPMethod
    client_route: str
    endpoint_route: str
    confidence: float
    match_type: str
    evidence: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "client_id": self.client_id,
            "endpoint_id": self.endpoint_id,
            "method": self.method.value,
            "client_route": self.client_route,
            "endpoint_route": self.endpoint_route,
            "confidence": self.confidence,
            "match_type": self.match_type,
            "evidence": self.evidence,
        }


# [20251216_FEATURE] Route pattern matching with confidence scoring
class RoutePatternMatcher:
    """
    Matcher for HTTP route patterns with confidence scoring.

    Handles:
    - Exact matches: "/api/users" == "/api/users" (confidence 0.95)
    - Pattern matches: "/api/users/{id}" ~= "/api/users/123" (confidence 0.8)
    - Dynamic routes: "/api/" + version + "/users" (confidence 0.5)
    """

    def match_routes(self, client_route: str, endpoint_route: str) -> tuple[bool, float, str]:
        """
        Match client route against endpoint route.

        Args:
            client_route: Route from client call
            endpoint_route: Route from endpoint definition

        Returns:
            Tuple of (matches, confidence, match_type)
        """
        # Exact match
        if client_route == endpoint_route:
            return True, 0.95, "exact"

        # Pattern match (e.g., /api/users/{id} matches /api/users/123)
        if self._is_pattern_match(client_route, endpoint_route):
            return True, 0.8, "pattern"

        # Check if either route is dynamic (contains variables)
        client_is_dynamic = self._is_dynamic_route(client_route)
        endpoint_is_dynamic = self._is_dynamic_route(endpoint_route)

        if client_is_dynamic or endpoint_is_dynamic:
            # [20251216_BUGFIX] For dynamic routes, return dynamic match type with
            # confidence based on fuzzy match quality. AI agents need to know this
            # IS a dynamic route requiring human confirmation.
            if self._fuzzy_match(client_route, endpoint_route):
                return True, 0.5, "dynamic"
            else:
                # [20251216_BUGFIX] Even without fuzzy match, flag as dynamic with
                # very low confidence so agents know human review is required.
                # Extract path segments to check for any structural similarity.
                if self._has_structural_similarity(client_route, endpoint_route):
                    return True, 0.3, "dynamic"
                # One route is dynamic - return low confidence dynamic match
                # to ensure proper flagging for human review
                return False, 0.0, "dynamic"

        return False, 0.0, "none"

    def _has_structural_similarity(self, client_route: str, endpoint_route: str) -> bool:
        """Check if routes have structural similarity (common path segments)."""

        # Extract clean path segments from dynamic route
        def extract_segments(route: str) -> set:
            # Remove quotes, variables, and split by common delimiters
            clean = re.sub(r'["\'\s+]', "", route)
            clean = re.sub(r"\$\{[^}]+\}", "", clean)  # Remove template vars
            clean = re.sub(r"version|baseUrl|api_url", "", clean, flags=re.IGNORECASE)  # Common vars
            segments = set(clean.split("/"))
            return {s for s in segments if s and len(s) > 2}  # Non-empty, meaningful

        client_segments = extract_segments(client_route)
        endpoint_segments = extract_segments(endpoint_route)

        # Check for common meaningful segments
        common = client_segments & endpoint_segments
        return len(common) > 0

    def _is_pattern_match(self, client_route: str, endpoint_route: str) -> bool:
        """Check if routes match with path parameter patterns."""
        # Convert endpoint pattern to regex
        # /api/users/{id} -> /api/users/[^/]+
        pattern = re.sub(r"\{[^}]+\}", r"[^/]+", endpoint_route)
        pattern = f"^{pattern}$"

        return re.match(pattern, client_route) is not None

    def _is_dynamic_route(self, route: str) -> bool:
        """Check if route contains dynamic parts (variables)."""
        # Look for common dynamic route indicators
        indicators = [
            "+",  # String concatenation
            "${",  # Template literals
            "` + ",  # Template string concatenation
            "params.",  # Parameter access
        ]
        return any(ind in route for ind in indicators)

    def _fuzzy_match(self, client_route: str, endpoint_route: str) -> bool:
        """Fuzzy match for dynamic routes."""
        # Extract static parts and compare
        client_parts = re.split(r"[+${}]", client_route)
        endpoint_parts = re.split(r"[+${}]", endpoint_route)

        # Check if any static parts match
        client_static = [p.strip("'\" ") for p in client_parts if p.strip("'\" ")]
        endpoint_static = [p.strip("'\" ") for p in endpoint_parts if p.strip("'\" ")]

        # If they share common path segments, consider it a match
        common = set(client_static) & set(endpoint_static)
        return len(common) > 0


# [20251216_FEATURE] Main HTTP link detector
class HTTPLinkDetector:
    """
    Detector for HTTP links between frontend and backend.

    This class identifies connections between client-side API calls and
    server-side endpoints by matching routes and HTTP methods.

    Example:
        >>> detector = HTTPLinkDetector()
        >>> detector.add_client_call("ts::fetchUsers", "GET", "/api/users")
        >>> detector.add_endpoint("java::getUser", "GET", "/api/users")
        >>> links = detector.detect_links()
    """

    def __init__(self):
        """Initialize HTTP link detector."""
        self.client_calls: list[dict] = []
        self.endpoints: list[dict] = []
        self.matcher = RoutePatternMatcher()

    def add_client_call(
        self,
        node_id: str,
        method: str | HTTPMethod,
        route: str,
        metadata: dict | None = None,
    ) -> None:
        """
        Add a client-side HTTP call.

        Args:
            node_id: Universal node ID
            method: HTTP method (GET, POST, etc.)
            route: Route string
            metadata: Optional additional metadata
        """
        if isinstance(method, str):
            method = HTTPMethod(method.upper())

        self.client_calls.append(
            {
                "node_id": node_id,
                "method": method,
                "route": route,
                "metadata": metadata or {},
            }
        )

    def add_endpoint(
        self,
        node_id: str,
        method: str | HTTPMethod,
        route: str,
        metadata: dict | None = None,
    ) -> None:
        """
        Add a server-side endpoint.

        Args:
            node_id: Universal node ID
            method: HTTP method
            route: Route string
            metadata: Optional additional metadata
        """
        if isinstance(method, str):
            method = HTTPMethod(method.upper())

        self.endpoints.append(
            {
                "node_id": node_id,
                "method": method,
                "route": route,
                "metadata": metadata or {},
            }
        )

    def detect_links(self) -> list[HTTPLink]:
        """
        Detect all HTTP links between clients and endpoints.

        Returns:
            List of HTTPLink objects with confidence scores
        """
        links: list[HTTPLink] = []

        for client in self.client_calls:
            for endpoint in self.endpoints:
                # Methods must match
                if client["method"] != endpoint["method"]:
                    continue

                # Try to match routes
                matches, confidence, match_type = self.matcher.match_routes(client["route"], endpoint["route"])

                if matches:
                    evidence = self._build_evidence(client, endpoint, match_type, confidence)

                    link = HTTPLink(
                        client_id=client["node_id"],
                        endpoint_id=endpoint["node_id"],
                        method=client["method"],
                        client_route=client["route"],
                        endpoint_route=endpoint["route"],
                        confidence=confidence,
                        match_type=match_type,
                        evidence=evidence,
                    )
                    links.append(link)

        return links

    def _build_evidence(self, client: dict, endpoint: dict, match_type: str, confidence: float) -> str:
        """Build human-readable evidence string."""
        method = client["method"].value
        route = client["route"]

        if match_type == "exact":
            return f"Route string match: {method} {route}"
        elif match_type == "pattern":
            return f"Pattern match: {method} {route} ~= {endpoint['route']}"
        elif match_type == "dynamic":
            return f"Dynamic route match: {method} {route} (low confidence)"
        else:
            return f"Unknown match type: {match_type}"

    def get_unmatched_clients(self) -> list[dict]:
        """Get client calls that have no matching endpoints."""
        matched_clients = set()

        for client in self.client_calls:
            for endpoint in self.endpoints:
                if client["method"] != endpoint["method"]:
                    continue

                matches, _, _ = self.matcher.match_routes(client["route"], endpoint["route"])
                if matches:
                    matched_clients.add(client["node_id"])
                    break

        return [c for c in self.client_calls if c["node_id"] not in matched_clients]

    def get_unmatched_endpoints(self) -> list[dict]:
        """Get endpoints that have no matching client calls."""
        matched_endpoints = set()

        for endpoint in self.endpoints:
            for client in self.client_calls:
                if client["method"] != endpoint["method"]:
                    continue

                matches, _, _ = self.matcher.match_routes(client["route"], endpoint["route"])
                if matches:
                    matched_endpoints.add(endpoint["node_id"])
                    break

        return [e for e in self.endpoints if e["node_id"] not in matched_endpoints]
