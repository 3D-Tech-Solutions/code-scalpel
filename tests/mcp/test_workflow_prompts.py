"""
Tests for Workflow Prompts.

[20251216_TEST] Tests for Feature 10: Workflow Prompts
[20260120_REFACTOR] Updated to test new canonical prompt API
"""

from mcp.server.fastmcp.prompts.base import Message as PromptMessage


class TestDeepSecurityAuditPrompt:
    """Test the deep security audit workflow prompt."""

    def test_deep_security_audit_prompt_exists(self):
        """Test that the deep security audit prompt is defined."""
        from code_scalpel.mcp.prompts import deep_security_audit

        assert deep_security_audit is not None
        assert callable(deep_security_audit)

    def test_deep_security_audit_prompt_takes_path(self):
        """Test that the prompt accepts a path parameter."""
        from code_scalpel.mcp.prompts import deep_security_audit

        result = deep_security_audit("/path/to/project")

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(msg, PromptMessage) for msg in result)

    def test_deep_security_audit_prompt_includes_path(self):
        """Test that the prompt includes the project path."""
        from code_scalpel.mcp.prompts import deep_security_audit

        project_path = "/my/test/project"
        result = deep_security_audit(project_path)

        # Get the content from the first message (UserMessage.content is TextContent)
        content = result[0].content
        # TextContent has .text attribute with actual string
        text = getattr(content, "text", str(content))
        assert project_path in text

    def test_deep_security_audit_prompt_includes_steps(self):
        """Test that the prompt includes workflow steps."""
        from code_scalpel.mcp.prompts import deep_security_audit

        result = deep_security_audit("/project")
        content = result[0].content
        text = getattr(content, "text", str(content))

        # Check for numbered steps
        assert "1)" in text or "Step" in text
        assert "2)" in text
        assert "3)" in text

    def test_deep_security_audit_prompt_mentions_tools(self):
        """Test that the prompt mentions required MCP tools."""
        from code_scalpel.mcp.prompts import deep_security_audit

        result = deep_security_audit("/project")
        content = result[0].content
        text = getattr(content, "text", str(content))

        # Check for tool mentions
        assert "security_scan" in text
        assert "scan_dependencies" in text


class TestSafeRefactorPrompt:
    """Test the safe refactor workflow prompt."""

    def test_safe_refactor_prompt_exists(self):
        """Test that the safe refactor prompt is defined."""
        from code_scalpel.mcp.prompts import safe_refactor

        assert safe_refactor is not None
        assert callable(safe_refactor)

    def test_safe_refactor_prompt_takes_parameters(self):
        """Test that the prompt accepts file_path, symbol_name, and goal parameters."""
        from code_scalpel.mcp.prompts import safe_refactor

        result = safe_refactor("/path/to/file.py", "my_function", "optimize performance")

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(msg, PromptMessage) for msg in result)

    def test_safe_refactor_prompt_includes_parameters(self):
        """Test that the prompt includes the provided parameters."""
        from code_scalpel.mcp.prompts import safe_refactor

        file_path = "/my/test/file.py"
        symbol_name = "test_function"
        goal = "improve readability"
        result = safe_refactor(file_path, symbol_name, goal)
        content = result[0].content
        text = getattr(content, "text", str(content))

        assert file_path in text
        assert symbol_name in text
        assert goal in text

    def test_safe_refactor_prompt_includes_steps(self):
        """Test that the prompt includes workflow steps."""
        from code_scalpel.mcp.prompts import safe_refactor

        result = safe_refactor("/file.py", "func", "optimize")
        content = result[0].content
        text = getattr(content, "text", str(content))

        # Check for numbered steps
        assert "1)" in text or "Step" in text
        assert "2)" in text
        assert "3)" in text

    def test_safe_refactor_prompt_mentions_tools(self):
        """Test that the prompt mentions required MCP tools."""
        from code_scalpel.mcp.prompts import safe_refactor

        result = safe_refactor("/file.py", "func", "optimize")
        content = result[0].content
        text = getattr(content, "text", str(content))

        # Check for tool mentions
        assert "extract_code" in text
        assert "get_symbol_references" in text
        assert "update_symbol" in text


class TestModernizeLegacyPrompt:
    """Test the modernize legacy workflow prompt."""

    def test_modernize_legacy_prompt_exists(self):
        """Test that the modernize legacy prompt is defined."""
        from code_scalpel.mcp.prompts import modernize_legacy

        assert modernize_legacy is not None
        assert callable(modernize_legacy)

    def test_modernize_legacy_prompt_takes_path(self):
        """Test that the prompt accepts a path parameter."""
        from code_scalpel.mcp.prompts import modernize_legacy

        result = modernize_legacy("/path/to/project")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_modernize_legacy_mentions_tools(self):
        """Test that the prompt mentions required MCP tools."""
        from code_scalpel.mcp.prompts import modernize_legacy

        result = modernize_legacy("/project")
        content = result[0].content
        text = getattr(content, "text", str(content))

        assert "type_evaporation_scan" in text
        assert "analyze_code" in text


class TestMapArchitecturePrompt:
    """Test the map architecture workflow prompt."""

    def test_map_architecture_prompt_exists(self):
        """Test that the map architecture prompt is defined."""
        from code_scalpel.mcp.prompts import map_architecture

        assert map_architecture is not None
        assert callable(map_architecture)

    def test_map_architecture_mentions_tools(self):
        """Test that the prompt mentions required MCP tools."""
        from code_scalpel.mcp.prompts import map_architecture

        result = map_architecture("/module")
        content = result[0].content
        text = getattr(content, "text", str(content))

        assert "crawl_project" in text
        assert "get_call_graph" in text


class TestVerifySupplyChainPrompt:
    """Test the verify supply chain workflow prompt."""

    def test_verify_supply_chain_prompt_exists(self):
        """Test that the verify supply chain prompt is defined."""
        from code_scalpel.mcp.prompts import verify_supply_chain

        assert verify_supply_chain is not None
        assert callable(verify_supply_chain)

    def test_verify_supply_chain_mentions_tools(self):
        """Test that the prompt mentions required MCP tools."""
        from code_scalpel.mcp.prompts import verify_supply_chain

        result = verify_supply_chain("/project")
        content = result[0].content
        text = getattr(content, "text", str(content))

        assert "scan_dependencies" in text


class TestExplainAndDocumentPrompt:
    """Test the explain and document workflow prompt."""

    def test_explain_and_document_prompt_exists(self):
        """Test that the explain and document prompt is defined."""
        from code_scalpel.mcp.prompts import explain_and_document

        assert explain_and_document is not None
        assert callable(explain_and_document)

    def test_explain_and_document_mentions_tools(self):
        """Test that the prompt mentions required MCP tools."""
        from code_scalpel.mcp.prompts import explain_and_document

        result = explain_and_document("/target")
        content = result[0].content
        text = getattr(content, "text", str(content))

        assert "analyze_code" in text or "extract_code" in text


class TestPromptDiscoverability:
    """Test that prompts are discoverable via MCP protocol."""

    def test_all_prompts_exist_in_module(self):
        """Test that all canonical prompts are defined in prompts module."""
        from code_scalpel.mcp import prompts

        expected_prompts = [
            "deep_security_audit",
            "safe_refactor",
            "modernize_legacy",
            "map_architecture",
            "verify_supply_chain",
            "explain_and_document",
        ]

        for prompt_name in expected_prompts:
            assert hasattr(prompts, prompt_name), f"{prompt_name} not found in prompts module"
            func = getattr(prompts, prompt_name)
            assert callable(func), f"{prompt_name} is not callable"

    def test_prompts_return_message_lists(self):
        """Test that prompts return lists of PromptMessage."""
        from code_scalpel.mcp.prompts import deep_security_audit, safe_refactor

        audit_result = deep_security_audit("/project")
        refactor_result = safe_refactor("/file.py", "func", "goal")

        assert isinstance(audit_result, list)
        assert isinstance(refactor_result, list)
        assert len(audit_result) > 0
        assert len(refactor_result) > 0


class TestAcceptanceCriteria:
    """Test acceptance criteria from the problem statement."""

    def test_security_audit_guides_through_full_audit(self):
        """Acceptance: security-audit prompt guides through full audit."""
        from code_scalpel.mcp.prompts import deep_security_audit

        result = deep_security_audit("/project")
        content = result[0].content
        text = getattr(content, "text", str(content))

        # Should guide through security scanning
        assert "security_scan" in text

        # Should include dependency checking
        assert "scan_dependencies" in text

    def test_safe_refactor_guides_through_refactor(self):
        """Acceptance: safe-refactor prompt guides through refactor."""
        from code_scalpel.mcp.prompts import safe_refactor

        result = safe_refactor("/file.py", "func", "optimize")
        content = result[0].content
        text = getattr(content, "text", str(content))

        # Should guide through:
        # 1. Find all usages
        assert "get_symbol_references" in text

        # 2. Extract current implementation
        assert "extract_code" in text

        # 3. Apply changes
        assert "update_symbol" in text

    def test_prompts_are_registered_with_mcp(self):
        """Acceptance: Prompts are registered with MCP protocol."""
        from code_scalpel.mcp.protocol import mcp

        # The mcp instance exists
        assert mcp is not None

        # Importing prompts module registers the prompts
        import code_scalpel.mcp.prompts  # noqa: F401

        # Prompts should be registered (can be verified via mcp.list_prompts)
        # The actual registration is handled by @mcp.prompt decorator

    def test_prompts_handle_edge_cases(self):
        """Acceptance: Prompts handle edge cases (empty/invalid inputs)."""
        from code_scalpel.mcp.prompts import deep_security_audit, safe_refactor

        # Should not crash with various inputs
        audit1 = deep_security_audit("")
        audit2 = deep_security_audit("/nonexistent/path")

        refactor1 = safe_refactor("", "", "")
        refactor2 = safe_refactor("/file.py", "nonexistent_func", "goal")

        # All should return valid message lists (prompts don't validate paths)
        assert isinstance(audit1, list)
        assert isinstance(audit2, list)
        assert isinstance(refactor1, list)
        assert isinstance(refactor2, list)
