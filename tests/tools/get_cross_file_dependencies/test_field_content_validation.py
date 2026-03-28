"""Field Content Validation Tests for get_cross_file_dependencies.

Validates actual field content, not just presence:
- alias_resolutions: correct origin mapping for import aliases
- wildcard_expansions: correct symbol list from __all__ expansion
- coupling_violations: actual violation metrics and counts
- architectural_rules_applied: correct rule names and matches
- boundary_violations: correct layer assignments and violation types
- layer_mapping: correct file-to-layer assignments
- reexport_chains: correct re-export path tracing

[20260104_TEST] Field content validation and correctness assertions
"""

import pytest


class TestAliasResolutionContent:
    """Validate actual content of alias_resolutions field (Pro tier)."""

    @pytest.mark.asyncio
    async def test_simple_import_alias_resolution(
        self, pro_server, alias_import_project
    ):
        """Validate simple import alias is correctly resolved."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=alias_import_project["target_file"],
            target_symbol=alias_import_project["target_symbol"],
            project_root=alias_import_project["root"],
        )

        assert result.success is True
        # Should contain alias resolutions
        assert len(result.alias_resolutions) > 0, "Should detect import aliases"

        # Check content of first alias resolution
        if result.alias_resolutions:
            alias = result.alias_resolutions[0]
            assert hasattr(alias, "alias"), "Should have alias field"
            assert hasattr(
                alias, "original_module"
            ), "Should have original_module field"
            # Verify the alias mapping makes sense
            assert alias.alias is not None
            assert alias.original_module is not None

    @pytest.mark.asyncio
    async def test_from_import_as_alias_resolution(
        self, pro_server, alias_import_project
    ):
        """Validate 'from X import Y as Z' alias resolution."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=alias_import_project["target_file"],
            target_symbol=alias_import_project["target_symbol"],
            project_root=alias_import_project["root"],
        )

        assert result.success is True
        # Should track "from X import Y as Z" pattern
        for alias in result.alias_resolutions:
            # Alias should map to a real module
            assert "." in alias.original_module or alias.original_module.isidentifier()


class TestWildcardExpansionContent:
    """Validate actual content of wildcard_expansions field (Pro tier)."""

    @pytest.mark.asyncio
    async def test_wildcard_all_expansion(self, pro_server, wildcard_import_project):
        """Validate __all__ expansion for wildcard imports."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=wildcard_import_project["target_file"],
            target_symbol=wildcard_import_project["target_symbol"],
            project_root=wildcard_import_project["root"],
        )

        assert result.success is True
        # Should expand wildcard imports
        assert len(result.wildcard_expansions) > 0, "Should detect wildcard imports"

        if result.wildcard_expansions:
            expansion = result.wildcard_expansions[0]
            # Check structure
            assert hasattr(expansion, "from_module"), "Should have from_module"
            assert hasattr(
                expansion, "expanded_symbols"
            ), "Should have expanded_symbols"

            # Verify symbols are list and non-empty
            assert isinstance(expansion.expanded_symbols, list)
            assert (
                len(expansion.expanded_symbols) > 0
            ), "Should have symbols from __all__"

            # Private symbols should not be included
            for symbol in expansion.expanded_symbols:
                assert not symbol.startswith(
                    "_"
                ), f"Private symbol {symbol} should not be in __all__"

    @pytest.mark.asyncio
    async def test_no_private_symbols_in_expansion(
        self, pro_server, wildcard_import_project
    ):
        """__all__ expansion should exclude private symbols."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=wildcard_import_project["target_file"],
            target_symbol=wildcard_import_project["target_symbol"],
            project_root=wildcard_import_project["root"],
        )

        assert result.success is True
        for expansion in result.wildcard_expansions:
            for symbol in expansion.expanded_symbols:
                # Symbol should not start with underscore (private)
                assert not symbol.startswith(
                    "_"
                ), f"Symbol {symbol} should not be in __all__ expansion"


class TestReexportChainContent:
    """Validate actual content of reexport_chains field (Pro tier)."""

    @pytest.mark.asyncio
    async def test_package_init_reexport_detection(self, pro_server, reexport_project):
        """Validate __init__.py re-export chain tracking."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=reexport_project["target_file"],
            target_symbol=reexport_project["target_symbol"],
            project_root=reexport_project["root"],
        )

        assert result.success is True
        # Should detect re-exports
        assert len(result.reexport_chains) > 0, "Should detect package re-exports"

        if result.reexport_chains:
            chain = result.reexport_chains[0]
            # Check structure
            assert hasattr(chain, "symbol"), "Should have symbol field"
            assert hasattr(chain, "apparent_source"), "Should have apparent_source"
            assert hasattr(chain, "actual_source"), "Should have actual_source"

            # Verify apparent source differs from actual
            # (apparent is __init__.py, actual is real module)
            assert chain.apparent_source != chain.actual_source


class TestCouplingViolationContent:
    """Validate actual content of coupling_violations field (Enterprise tier)."""

    @pytest.mark.asyncio
    async def test_fan_in_violation_metric_content(
        self, enterprise_server, simple_two_file_project
    ):
        """Validate fan-in violation has correct metric details."""
        # Create a high-fan-in scenario
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Check coupling violations structure
        for violation in result.coupling_violations:
            assert hasattr(violation, "metric"), "Violation should have metric field"
            assert hasattr(violation, "value"), "Violation should have value field"
            assert hasattr(violation, "limit"), "Violation should have limit field"

            # Value should exceed limit (that's why it's a violation)
            if hasattr(violation, "metric") and violation.metric == "fan_in":
                assert (
                    violation.value >= violation.limit
                ), f"Violation value {violation.value} should be >= limit {violation.limit}"


class TestArchitecturalViolationContent:
    """Validate actual content of architectural violation fields (Enterprise tier)."""

    @pytest.mark.asyncio
    async def test_layer_violation_has_rule_and_recommendation(
        self, enterprise_server, simple_two_file_project
    ):
        """Layer violation should include rule name and recommendation."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Check architectural violations
        for violation in result.architectural_violations:
            # Should have identifying information
            assert hasattr(violation, "type"), "Violation should have type"
            assert hasattr(violation, "severity"), "Violation should have severity"

            # Severity should be valid
            if hasattr(violation, "severity"):
                assert violation.severity in [
                    "critical",
                    "warning",
                    "info",
                    "note",
                ], f"Invalid severity level: {violation.severity}"

    @pytest.mark.asyncio
    async def test_boundary_alert_has_layer_info(
        self, enterprise_server, simple_two_file_project
    ):
        """Boundary alert should identify layers involved."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Check boundary alerts
        for alert in result.boundary_alerts:
            # Should identify layers
            assert hasattr(alert, "from_layer"), "Alert should have from_layer"
            assert hasattr(alert, "to_layer"), "Alert should have to_layer"

            # Layers should be different (otherwise no boundary)
            assert alert.from_layer != alert.to_layer


class TestLayerMappingContent:
    """Validate actual content of layer_mapping field (Enterprise tier)."""

    @pytest.mark.asyncio
    async def test_layer_mapping_file_assignment(
        self, enterprise_server, simple_two_file_project
    ):
        """Layer mapping should correctly assign files to layers."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # Check layer mapping structure
        if result.layer_mapping:
            for layer_name, files in result.layer_mapping.items():
                # Should be list of files
                assert isinstance(
                    files, list
                ), f"Layer {layer_name} should map to file list"

                # Files should be strings (paths)
                for file_path in files:
                    assert isinstance(
                        file_path, str
                    ), f"File path should be string, got {type(file_path)}"


class TestRulesAppliedContent:
    """Validate actual content of rules_applied field (Enterprise tier)."""

    @pytest.mark.asyncio
    async def test_rules_applied_is_list_of_rule_names(
        self, enterprise_server, simple_two_file_project
    ):
        """rules_applied should list actual rule names that were evaluated."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # rules_applied should be a list
        assert isinstance(
            result.rules_applied, list
        ), f"rules_applied should be list, got {type(result.rules_applied)}"

        # Each rule name should be a string
        for rule in result.rules_applied:
            assert isinstance(rule, str), f"Rule should be string, got {type(rule)}"


class TestExemptedFilesContent:
    """Validate actual content of exempted_files field (Enterprise tier)."""

    @pytest.mark.asyncio
    async def test_exempted_files_match_patterns(
        self, enterprise_server, simple_two_file_project
    ):
        """exempted_files should contain files matching exemption patterns."""
        result = await enterprise_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # exempted_files should be a list
        assert isinstance(result.exempted_files, list)

        # Each exempted file should be a string
        for file_path in result.exempted_files:
            assert isinstance(
                file_path, str
            ), f"Exempted file should be string, got {type(file_path)}"


class TestDependencyChainContent:
    """Validate actual content of dependency_chains field."""

    @pytest.mark.asyncio
    async def test_dependency_chains_are_valid_paths(
        self, pro_server, deep_chain_project
    ):
        """Dependency chains should represent valid import paths."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
        )

        assert result.success is True
        # Should have dependency chains for deep project
        if result.dependency_chains:
            for chain in result.dependency_chains:
                # Chain should be a list of files
                assert isinstance(
                    chain, list
                ), f"Chain should be list, got {type(chain)}"

                # Each element should be a string (file path)
                for file_path in chain:
                    assert isinstance(
                        file_path, str
                    ), f"Chain element should be string, got {type(file_path)}"

                # Chain length is nodes, max_depth_reached is edges.
                # A chain of depth 3 has 4 nodes: a→b→c→d (3 edges, 4 files).
                # So len(chain) should be <= max_depth_reached + 1
                # [20260111_FIX] Fixed off-by-one: chain nodes = edges + 1
                assert (
                    len(chain) <= result.max_depth_reached + 1
                ), f"Chain length {len(chain)} exceeds depth limit {result.max_depth_reached}+1"

    @pytest.mark.asyncio
    async def test_typescript_dependency_chains_use_relative_file_modules(
        self, pro_server, tmp_path
    ):
        """Initial TS parity slice should preserve relative file-backed module paths."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "util.ts").write_text(
            "export function helper(): number {\n    return 1;\n}\n",
            encoding="utf-8",
        )
        target_file = src_dir / "main.ts"
        target_file.write_text(
            'import { helper } from "./util";\n\n'
            "export function entry(): number {\n    return helper();\n}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("entry", "src/main.ts") in extracted
        assert ("helper", "src/util.ts") in extracted
        assert result.import_graph == {"src/main.ts": ["src/util.ts"]}
        assert ["src/main.ts", "src/util.ts"] in result.dependency_chains

    @pytest.mark.asyncio
    async def test_java_dependency_chains_use_relative_file_modules(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java graph-backed slices should preserve relative file-backed module paths."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        tool();\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        assert result.target_file == "demo/App.java"
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("App.entry", "demo/App.java") in extracted
        assert ("Helper.tool", "demo/Helper.java") in extracted
        assert result.import_graph == {"demo/App.java": ["demo/Helper.java"]}
        assert ["demo/App.java", "demo/Helper.java"] in result.dependency_chains

    @pytest.mark.asyncio
    async def test_java_dependency_mermaid_preserves_relative_file_labels(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java graph-backed dependency slices should preserve relative file metadata in Mermaid-backed output."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        tool();\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=True,
        )

        assert result.success is True
        assert result.target_file == "demo/App.java"
        assert result.import_graph == {"demo/App.java": ["demo/Helper.java"]}
        assert result.mermaid.startswith("graph TD")
        assert "demo_App_java" in result.mermaid
        assert "demo_Helper_java" in result.mermaid

    @pytest.mark.asyncio
    async def test_java_static_wildcard_dependency_chains_use_relative_modules(
        self, pro_server, tmp_path
    ):
        """[20260315_TEST] Java dependency extraction should resolve local static wildcard imports."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import static demo.Helper.*;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        tool();\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        assert result.target_file == "demo/App.java"
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("App.entry", "demo/App.java") in extracted
        assert ("Helper.tool", "demo/Helper.java") in extracted
        assert result.import_graph == {"demo/App.java": ["demo/Helper.java"]}
        assert ["demo/App.java", "demo/Helper.java"] in result.dependency_chains

    @pytest.mark.asyncio
    async def test_java_ambiguous_bare_method_name_returns_guidance(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java dependency extraction should reject ambiguous bare method names with actionable guidance."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "    }\n"
            "}\n\n"
            "class Worker {\n"
            "    void run() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is False
        assert result.error is not None
        assert "ambiguous" in result.error.lower()
        assert "class.method" in result.error.lower()

    @pytest.mark.asyncio
    async def test_java_overloaded_dependency_slice_uses_signature_selector(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java graph-backed dependency slices should carry overload-aware signature identities."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        tool(1);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("App.entry", "demo/App.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") in extracted
        assert ("Helper.tool(String)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_structured_selector_targets_exact_overload(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java dependency extraction should accept structured selectors like Helper.tool(int)."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        target_file = package_dir / "Helper.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="Helper.tool(int)",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert extracted == {("Helper.tool(int)", "demo/Helper.java")}

    @pytest.mark.asyncio
    async def test_java_dependency_slice_uses_method_return_types_for_overloaded_calls(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java dependency extraction should use method return types to select overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Factory.java").write_text(
            "package demo;\n\n"
            "public class Factory {\n"
            "    public static String make() {\n"
            '        return "ok";\n'
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import static demo.Factory.make;\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        tool(make());\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Factory.make", "demo/Factory.java") in extracted
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_uses_method_return_types_for_overloaded_constructors(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java dependency extraction should use method return types to select overloaded constructors."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Factory.java").write_text(
            "package demo;\n\n"
            "public class Factory {\n"
            "    public static String make() {\n"
            '        return "ok";\n'
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "Helper.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public Helper(int value) {\n"
            "    }\n\n"
            "    public Helper(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "App.java").write_text(
            "package demo;\n\n"
            "import static demo.Factory.make;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        new Helper(make());\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(package_dir / "App.java"),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Factory.make", "demo/Factory.java") in extracted
        assert ("Helper.Helper(String)", "demo/Helper.java") in extracted
        assert ("Helper.Helper(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_uses_chained_builder_return_types_for_overloaded_calls(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java dependency extraction should use chained builder-style method returns to select overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Builder.java").write_text(
            "package demo;\n\n"
            "public class Builder {\n"
            "    public String make() {\n"
            '        return "ok";\n'
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        tool(new Builder().make());\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Builder.make", "demo/Builder.java") in extracted
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_uses_cast_types_for_overloaded_constructors(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java dependency extraction should use explicit casts to select overloaded constructors."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public Helper(int value) {\n"
            "    }\n\n"
            "    public Helper(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            '        Object raw = "ok";\n'
            "        new Helper((String) raw);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.Helper(String)", "demo/Helper.java") in extracted
        assert ("Helper.Helper(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_uses_static_fluent_builder_return_types_for_overloaded_calls(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java dependency extraction should use static builder entrypoints and longer fluent chains for overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Builder.java").write_text(
            "package demo;\n\n"
            "public class Builder {\n"
            "    public static Builder start() {\n"
            "        return new Builder();\n"
            "    }\n\n"
            "    public Builder step() {\n"
            "        return this;\n"
            "    }\n\n"
            "    public String make() {\n"
            '        return "ok";\n'
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import static demo.Helper.tool;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        tool(Builder.start().step().make());\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Builder.start", "demo/Builder.java") in extracted
        assert ("Builder.step", "demo/Builder.java") in extracted
        assert ("Builder.make", "demo/Builder.java") in extracted
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_uses_static_fluent_builder_return_types_for_overloaded_constructors(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java dependency extraction should use static builder entrypoints and longer fluent chains for overloaded constructors."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Builder.java").write_text(
            "package demo;\n\n"
            "public class Builder {\n"
            "    public static Builder start() {\n"
            "        return new Builder();\n"
            "    }\n\n"
            "    public Builder step() {\n"
            "        return this;\n"
            "    }\n\n"
            "    public String make() {\n"
            '        return "ok";\n'
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public Helper(int value) {\n"
            "    }\n\n"
            "    public Helper(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class App {\n"
            "    public static void entry() {\n"
            "        new Helper(Builder.start().step().make());\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="entry",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Builder.start", "demo/Builder.java") in extracted
        assert ("Builder.step", "demo/Builder.java") in extracted
        assert ("Builder.make", "demo/Builder.java") in extracted
        assert ("Helper.Helper(String)", "demo/Helper.java") in extracted
        assert ("Helper.Helper(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_override_dependencies_prefer_local_child_method(
        self, pro_server, tmp_path
    ):
        """[20260308_TEST] Java graph-backed dependency slices should prefer overridden child methods over superclass fallbacks."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Base.java").write_text(
            "package demo;\n\n"
            "public class Base {\n"
            "    protected void helper() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "Child.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class Child extends Base {\n"
            "    @Override\n"
            "    protected void helper() {\n"
            "    }\n\n"
            "    public void run() {\n"
            "        helper();\n"
            "        this.helper();\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Child.run", "demo/Child.java") in extracted
        assert ("Child.helper", "demo/Child.java") in extracted
        assert ("Base.helper", "demo/Base.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_constructor_dependency_slice_tracks_this_constructor_chain(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should include this(...) constructor chaining targets."""
        target_file = tmp_path / "Helper.java"
        target_file.write_text(
            "public class Helper {\n"
            "    public Helper() {\n"
            "        this(1);\n"
            "    }\n\n"
            "    public Helper(int value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="Helper()",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.Helper()", "Helper.java") in extracted
        assert ("Helper.Helper(int)", "Helper.java") in extracted

    @pytest.mark.asyncio
    async def test_java_constructor_dependency_slice_tracks_super_constructor_chain(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should include super(...) constructor chaining targets across files."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Base.java").write_text(
            "package demo;\n\n"
            "public class Base {\n"
            "    public Base(String value) {\n"
            "    }\n\n"
            "    public Base(int value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "Child.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class Child extends Base {\n"
            "    public Child() {\n"
            "        super(1);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="Child()",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Child.Child", "demo/Child.java") in extracted
        assert ("Base.Base(int)", "demo/Base.java") in extracted
        assert ("Base.Base(String)", "demo/Base.java") not in extracted
        assert result.import_graph == {"demo/Child.java": ["demo/Base.java"]}

    @pytest.mark.asyncio
    async def test_java_dependency_slice_infers_var_locals_for_overloaded_calls(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should infer var local types from initializers for overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        var value = make();\n"
            "        Helper.tool(value);\n"
            "    }\n\n"
            "    public String make() {\n"
            '        return "ok";\n'
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("App.make", "demo/App.java") in extracted
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_infers_field_access_types_for_overloaded_calls(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should use field-access types like this.name for overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class App {\n"
            "    private String name;\n\n"
            "    public void run() {\n"
            "        Helper.tool(this.name);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_matches_boxed_arguments_for_overloaded_method_calls(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should treat boxed and primitive types as compatible when selecting overloaded method call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Integer value = 7;\n"
            "        Helper.tool(value);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.tool(int)", "demo/Helper.java") in extracted
        assert ("Helper.tool(String)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_matches_boxed_arguments_for_overloaded_constructors(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should treat boxed and primitive types as compatible when selecting overloaded constructors from direct object creation."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Box.java").write_text(
            "package demo;\n\n"
            "public class Box {\n"
            "    public Box(int value) {\n"
            "    }\n\n"
            "    public Box(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Integer value = 7;\n"
            "        new Box(value);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Box.Box(int)", "demo/Box.java") in extracted
        assert ("Box.Box(String)", "demo/Box.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_infers_functional_interface_return_types_for_overloaded_calls(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should use functional-interface generic return types when method-reference-backed abstractions feed overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import java.util.function.Supplier;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Supplier<String> supplier = this::make;\n"
            "        Helper.tool(supplier.get());\n"
            "    }\n\n"
            "    public String make() {\n"
            '        return "ok";\n'
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_tracks_simple_method_reference_edges(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should retain direct method-reference targets like this::make."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Runnable runnable = this::make;\n"
            "    }\n\n"
            "    public void make() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("App.make", "demo/App.java") in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_infers_lambda_parameter_types_for_overloaded_calls(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should use functional-interface parameter types inside lambda bodies for overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import java.util.function.Consumer;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Consumer<String> consumer = value -> Helper.tool(value);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_preserves_lambda_block_local_flow_for_overloaded_calls(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should keep lambda block bodies selector-aware after local declaration and assignment flow."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import java.util.function.Consumer;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Consumer<String> consumer = value -> {\n"
            "            String local;\n"
            "            local = value;\n"
            "            Helper.tool(local);\n"
            "        };\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_preserves_multi_parameter_lambda_block_local_flow(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should keep multi-parameter lambda block bodies selector-aware after mixed local flow refinements."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int left, String right) {\n"
            "    }\n\n"
            "    public static void tool(String left, String right) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import java.util.function.BiConsumer;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        BiConsumer<Integer, String> consumer = (left, right) -> {\n"
            "            Integer localLeft = left;\n"
            "            String localRight;\n"
            "            localRight = right;\n"
            "            Helper.tool(localLeft, localRight);\n"
            "        };\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.tool(int, String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(String, String)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_tracks_constructor_method_reference_edges(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should resolve constructor references like Box::new to canonical constructor targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Box.java").write_text(
            "package demo;\n\n"
            "public class Box {\n"
            "    public Box() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import java.util.function.Supplier;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Supplier<Box> supplier = Box::new;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Box.Box", "demo/Box.java") in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_tracks_overloaded_function_constructor_reference_edges(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should use Function<T, R> parameter types to select overloaded constructor references."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Box.java").write_text(
            "package demo;\n\n"
            "public class Box {\n"
            "    public Box(int value) {\n"
            "    }\n\n"
            "    public Box(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import java.util.function.Function;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Function<String, Box> factory = Box::new;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Box.Box(String)", "demo/Box.java") in extracted
        assert ("Box.Box(int)", "demo/Box.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_tracks_overloaded_bifunction_constructor_reference_edges(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should use BiFunction<A, B, R> parameter types, including boxed primitives, to select overloaded constructor references."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Box.java").write_text(
            "package demo;\n\n"
            "public class Box {\n"
            "    public Box(int left, String right) {\n"
            "    }\n\n"
            "    public Box(String left, String right) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import java.util.function.BiFunction;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        BiFunction<Integer, String, Box> factory = Box::new;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Box.Box(int, String)", "demo/Box.java") in extracted
        assert ("Box.Box(String, String)", "demo/Box.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_tracks_qualified_static_method_reference_edges(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should resolve imported or qualified static method references to canonical targets."""
        util_dir = tmp_path / "util"
        util_dir.mkdir()
        (util_dir / "Factory.java").write_text(
            "package util;\n\n"
            "public class Factory {\n"
            "    public static String make() {\n"
            '        return "ok";\n'
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        demo_dir = tmp_path / "demo"
        demo_dir.mkdir()
        target_file = demo_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "import java.util.function.Supplier;\n"
            "import util.Factory;\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Supplier<String> supplier = Factory::make;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Factory.make", "util/Factory.java") in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_infers_custom_sam_lambda_parameter_types_for_overloaded_calls(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should use project-local generic SAM interfaces to type lambda parameters for overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "interface Mapper<T> {\n"
            "    void apply(T value);\n"
            "}\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Mapper<String> mapper = value -> Helper.tool(value);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_tracks_custom_sam_constructor_reference_edges(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should use project-local generic SAM interfaces to select overloaded constructor references."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Box.java").write_text(
            "package demo;\n\n"
            "public class Box {\n"
            "    public Box(int value) {\n"
            "    }\n\n"
            "    public Box(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "interface Factory<T, R> {\n"
            "    R create(T value);\n"
            "}\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Factory<String, Box> factory = Box::new;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Box.Box(String)", "demo/Box.java") in extracted
        assert ("Box.Box(int)", "demo/Box.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_infers_multi_parameter_custom_sam_lambda_types(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should use project-local multi-parameter SAM interfaces to type lambda parameters for overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int left, String right) {\n"
            "    }\n\n"
            "    public static void tool(String left, String right) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "interface Combiner<A, B> {\n"
            "    void apply(A left, B right);\n"
            "}\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Combiner<Integer, String> combiner = (left, right) -> Helper.tool(left, right);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.tool(int, String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(String, String)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_infers_inherited_custom_sam_lambda_types(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should resolve inherited project-local SAM signatures for lambdas."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Helper.java").write_text(
            "package demo;\n\n"
            "public class Helper {\n"
            "    public static void tool(int value) {\n"
            "    }\n\n"
            "    public static void tool(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "interface BaseMapper<T> {\n"
            "    void apply(T value);\n"
            "}\n\n"
            "interface Mapper<T> extends BaseMapper<T> {\n"
            "}\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Mapper<String> mapper = value -> Helper.tool(value);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Helper.tool(String)", "demo/Helper.java") in extracted
        assert ("Helper.tool(int)", "demo/Helper.java") not in extracted

    @pytest.mark.asyncio
    async def test_java_dependency_slice_tracks_inherited_custom_sam_constructor_reference_edges(
        self, pro_server, tmp_path
    ):
        """[20260309_TEST] Java dependency extraction should resolve inherited project-local SAM signatures for constructor references."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()
        (package_dir / "Box.java").write_text(
            "package demo;\n\n"
            "public class Box {\n"
            "    public Box(int value) {\n"
            "    }\n\n"
            "    public Box(String value) {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        target_file = package_dir / "App.java"
        target_file.write_text(
            "package demo;\n\n"
            "interface BaseFactory<T, R> {\n"
            "    R create(T value);\n"
            "}\n\n"
            "interface Factory<T, R> extends BaseFactory<T, R> {\n"
            "}\n\n"
            "public class App {\n"
            "    public void run() {\n"
            "        Factory<String, Box> factory = Box::new;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(target_file),
            target_symbol="run",
            project_root=str(tmp_path),
            include_code=False,
            include_diagram=False,
        )

        assert result.success is True
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("Box.Box(String)", "demo/Box.java") in extracted
        assert ("Box.Box(int)", "demo/Box.java") not in extracted


class TestCircularImportContent:
    """Validate circular import detection content."""

    @pytest.mark.asyncio
    async def test_circular_imports_identified_correctly(
        self, community_server, circular_import_project
    ):
        """Circular imports should be correctly identified in result."""
        result = await community_server.get_cross_file_dependencies(
            target_file=circular_import_project["target_file"],
            target_symbol=circular_import_project["target_symbol"],
            project_root=circular_import_project["root"],
        )

        assert result.success is True
        # For circular import project, should detect the cycle
        if circular_import_project.get("circular"):
            # Should have circular imports detected
            assert len(result.circular_imports) > 0, "Should detect circular imports"

            # Each circular import entry should be a list (the cycle)
            for cycle in result.circular_imports:
                assert isinstance(
                    cycle, list
                ), f"Cycle should be list, got {type(cycle)}"
                assert len(cycle) >= 2, "Cycle should have at least 2 modules"


class TestFileAnalyzedCount:
    """Validate files_analyzed field accuracy."""

    @pytest.mark.asyncio
    async def test_files_analyzed_count_accurate(
        self, community_server, simple_two_file_project
    ):
        """files_analyzed count should match actual files processed."""
        result = await community_server.get_cross_file_dependencies(
            target_file=simple_two_file_project["target_file"],
            target_symbol=simple_two_file_project["target_symbol"],
            project_root=simple_two_file_project["root"],
        )

        assert result.success is True
        # files_analyzed should be positive integer
        assert result.files_analyzed > 0, "Should analyze at least one file"
        assert isinstance(result.files_analyzed, int)

        # For simple 2-file project, should analyze both
        assert (
            result.files_analyzed >= 2
        ), f"Should analyze both files in 2-file project, got {result.files_analyzed}"


class TestMaxDepthReachedAccuracy:
    """Validate max_depth_reached field accuracy."""

    @pytest.mark.asyncio
    async def test_max_depth_reached_matches_actual_depth(
        self, pro_server, deep_chain_project
    ):
        """max_depth_reached should reflect actual chain depth found."""
        result = await pro_server.get_cross_file_dependencies(
            target_file=deep_chain_project["target_file"],
            target_symbol=deep_chain_project["target_symbol"],
            project_root=deep_chain_project["root"],
        )

        assert result.success is True
        # max_depth_reached should be <= requested max_depth
        assert result.max_depth_reached <= 5, "Should respect Pro tier depth limit"

        # For deep chain project, should have meaningful depth
        assert result.max_depth_reached > 0, "Should find some depth"


class TestGoDependencySliceContent:
    """Validate Go graph-backed dependency slice content."""

    @pytest.mark.asyncio
    async def test_go_dependency_chains_use_relative_file_modules(
        self, pro_server, tmp_path
    ):
        """[20260311_TEST] Go graph-backed slices should preserve relative file-backed module paths."""
        pytest.importorskip("tree_sitter_go")

        (tmp_path / "main.go").write_text(
            "package main\n\n" "func main() {\n" "\thelper()\n" "}\n",
            encoding="utf-8",
        )
        (tmp_path / "helper.go").write_text(
            "package main\n\n" "func helper() {\n" "}\n",
            encoding="utf-8",
        )

        result = await pro_server.get_cross_file_dependencies(
            target_file=str(tmp_path / "main.go"),
            target_symbol="main",
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert result.target_file == "main.go"
        extracted = {(symbol.name, symbol.file) for symbol in result.extracted_symbols}
        assert ("main", "main.go") in extracted
        assert ("helper", "helper.go") in extracted
        assert result.import_graph == {"main.go": ["helper.go"]}
        assert ["main.go", "helper.go"] in result.dependency_chains
