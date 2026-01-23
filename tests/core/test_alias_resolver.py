"""
Tests for Bundler/Module Alias Resolver.

[20251216_TEST] Tests for Feature 8: Bundler/Module Alias Resolution
"""

import json

from code_scalpel.polyglot.alias_resolver import AliasResolver, create_alias_resolver


class TestTsconfigAliases:
    """Test alias loading from tsconfig.json."""

    def test_load_simple_alias(self, tmp_path):
        """Test loading a simple alias from tsconfig.json."""
        tsconfig = {"compilerOptions": {"paths": {"@utils": ["./src/utils"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        assert resolver.has_alias("@utils")
        assert "src/utils" in resolver.resolve("@utils")

    def test_load_wildcard_alias(self, tmp_path):
        """Test loading wildcard aliases from tsconfig.json."""
        tsconfig = {"compilerOptions": {"paths": {"@ui/*": ["./src/ui/*"], "@data/*": ["./packages/data/src/*"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        assert resolver.has_alias("@ui")
        assert resolver.has_alias("@data")

    def test_load_alias_with_base_url(self, tmp_path):
        """Test loading aliases with baseUrl."""
        tsconfig = {
            "compilerOptions": {
                "baseUrl": "./src",
                "paths": {"@utils": ["./common/utils"]},
            }
        }

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        assert resolver.has_alias("@utils")
        # Should resolve relative to baseUrl
        resolved = resolver.resolve("@utils")
        assert "src" in resolved and "common/utils" in resolved

    def test_multiple_targets_uses_first(self, tmp_path):
        """Test that multiple targets use the first one."""
        tsconfig = {"compilerOptions": {"paths": {"@utils": ["./src/utils", "./lib/utils"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        resolved = resolver.resolve("@utils")
        assert "src/utils" in resolved
        assert "lib/utils" not in resolved

    def test_missing_tsconfig(self, tmp_path):
        """Test that missing tsconfig.json doesn't cause errors."""
        resolver = AliasResolver(tmp_path)

        # Should not have any aliases
        assert len(resolver.get_all_aliases()) == 0

    def test_invalid_tsconfig_json(self, tmp_path):
        """Test that invalid JSON doesn't cause errors."""
        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            f.write("{ invalid json }")

        resolver = AliasResolver(tmp_path)

        # Should not crash, just have no aliases
        assert len(resolver.get_all_aliases()) == 0


class TestWebpackAliases:
    """Test alias loading from webpack.config.js."""

    def test_load_webpack_alias(self, tmp_path):
        """Test loading aliases from webpack.config.js."""
        webpack_config = """
        const path = require('path');

        module.exports = {
          resolve: {
            alias: {
              '@ui': path.resolve(__dirname, 'src/ui'),
              '@data': path.resolve(__dirname, 'packages/data/src')
            }
          }
        };
        """

        webpack_path = tmp_path / "webpack.config.js"
        with open(webpack_path, "w") as f:
            f.write(webpack_config)

        resolver = AliasResolver(tmp_path)

        assert resolver.has_alias("@ui")
        assert resolver.has_alias("@data")
        assert "src/ui" in resolver.resolve("@ui")

    def test_missing_webpack_config(self, tmp_path):
        """Test that missing webpack config doesn't cause errors."""
        resolver = AliasResolver(tmp_path)

        # Should not crash
        assert isinstance(resolver.get_all_aliases(), dict)


class TestViteAliases:
    """Test alias loading from vite.config.ts."""

    def test_load_vite_alias(self, tmp_path):
        """Test loading aliases from vite.config.ts."""
        vite_config = """
        export default {
          resolve: {
            alias: {
              '@ui': '/src/ui',
              '@data': '/packages/data/src'
            }
          }
        };
        """

        vite_path = tmp_path / "vite.config.ts"
        with open(vite_path, "w") as f:
            f.write(vite_config)

        resolver = AliasResolver(tmp_path)

        assert resolver.has_alias("@ui")
        assert resolver.has_alias("@data")
        assert "src/ui" in resolver.resolve("@ui")

    def test_load_vite_alias_relative(self, tmp_path):
        """Test loading relative aliases from vite.config.ts."""
        vite_config = """
        export default {
          resolve: {
            alias: {
              '@ui': './src/ui',
              '@data': './packages/data'
            }
          }
        };
        """

        vite_path = tmp_path / "vite.config.ts"
        with open(vite_path, "w") as f:
            f.write(vite_config)

        resolver = AliasResolver(tmp_path)

        assert resolver.has_alias("@ui")
        assert "src/ui" in resolver.resolve("@ui")


class TestAliasResolution:
    """Test alias resolution logic."""

    def test_resolve_exact_match(self, tmp_path):
        """Test resolving an exact alias match."""
        tsconfig = {"compilerOptions": {"paths": {"@utils": ["./src/utils"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        resolved = resolver.resolve("@utils")
        assert resolved.endswith("src/utils")

    def test_resolve_with_subpath(self, tmp_path):
        """Test resolving an alias with a subpath."""
        tsconfig = {"compilerOptions": {"paths": {"@ui/*": ["./src/ui/*"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        resolved = resolver.resolve("@ui/components/Button")
        assert "src/ui/components/Button" in resolved

    def test_resolve_no_match(self, tmp_path):
        """Test that unmatched paths are returned as-is."""
        resolver = AliasResolver(tmp_path)

        # No aliases defined, should return as-is
        assert resolver.resolve("./relative/path") == "./relative/path"
        assert resolver.resolve("module-name") == "module-name"

    def test_resolve_partial_match_not_triggered(self, tmp_path):
        """Test that partial matches don't trigger resolution."""
        tsconfig = {"compilerOptions": {"paths": {"@ui": ["./src/ui"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        # @uicomponents should not match @ui
        assert resolver.resolve("@uicomponents") == "@uicomponents"


class TestFileResolution:
    """Test resolving aliases to actual files."""

    def test_resolve_to_existing_file(self, tmp_path):
        """Test resolving an alias to an existing file."""
        # Create directory structure
        src_dir = tmp_path / "src" / "ui"
        src_dir.mkdir(parents=True)

        # Create file
        button_file = src_dir / "Button.ts"
        button_file.write_text("export class Button {}")

        # Create tsconfig
        tsconfig = {"compilerOptions": {"paths": {"@ui/*": ["./src/ui/*"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        # Resolve to file
        resolved_file = resolver.resolve_to_file("@ui/Button")

        assert resolved_file is not None
        assert resolved_file.name == "Button.ts"
        assert resolved_file.exists()

    def test_resolve_to_index_file(self, tmp_path):
        """Test resolving an alias to an index file."""
        # Create directory structure
        components_dir = tmp_path / "src" / "components"
        components_dir.mkdir(parents=True)

        # Create index file
        index_file = components_dir / "index.ts"
        index_file.write_text("export * from './Button';")

        # Create tsconfig
        tsconfig = {"compilerOptions": {"paths": {"@components": ["./src/components"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        # Resolve to directory (should find index.ts)
        resolved_file = resolver.resolve_to_file("@components")

        assert resolved_file is not None
        assert resolved_file.name == "index.ts"

    def test_resolve_to_nonexistent_file(self, tmp_path):
        """Test that resolving to nonexistent file returns None."""
        tsconfig = {"compilerOptions": {"paths": {"@utils": ["./src/utils"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        # File doesn't exist
        resolved_file = resolver.resolve_to_file("@utils/nonexistent")

        assert resolved_file is None


class TestAcceptanceCriteria:
    """Test acceptance criteria from the problem statement."""

    def test_load_aliases_from_tsconfig(self, tmp_path):
        """Acceptance: Load aliases from tsconfig.json."""
        tsconfig = {
            "compilerOptions": {
                "paths": {
                    "@ui/*": ["./src/ui/*"],
                    "@data/*": ["./packages/data/src/*"],
                    "@utils": ["./src/common/utils"],
                }
            }
        }

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        # Check all aliases are loaded
        assert resolver.has_alias("@ui")
        assert resolver.has_alias("@data")
        assert resolver.has_alias("@utils")

    def test_resolve_aliased_imports(self, tmp_path):
        """Acceptance: Resolve aliased imports in import resolution."""
        tsconfig = {"compilerOptions": {"paths": {"@ui/*": ["./src/ui/*"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        # Test resolution
        resolved = resolver.resolve("@ui/components")
        assert "src/ui/components" in resolved

    def test_convenience_function(self, tmp_path):
        """Test the convenience function for creating resolvers."""
        tsconfig = {"compilerOptions": {"paths": {"@utils": ["./src/utils"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = create_alias_resolver(tmp_path)

        assert isinstance(resolver, AliasResolver)
        assert resolver.has_alias("@utils")


class TestMultiSourceAliases:
    """Test loading aliases from multiple sources."""

    def test_aliases_from_multiple_sources(self, tmp_path):
        """Test that aliases are loaded from all available sources."""
        # Create tsconfig with some aliases
        tsconfig = {"compilerOptions": {"paths": {"@ui/*": ["./src/ui/*"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        # Create vite config with additional aliases
        vite_config = """
        export default {
          resolve: {
            alias: {
              '@components': '/src/components'
            }
          }
        };
        """

        vite_path = tmp_path / "vite.config.ts"
        with open(vite_path, "w") as f:
            f.write(vite_config)

        resolver = AliasResolver(tmp_path)

        # Should have aliases from both sources
        assert resolver.has_alias("@ui")
        assert resolver.has_alias("@components")

    def test_get_all_aliases(self, tmp_path):
        """Test retrieving all loaded aliases."""
        tsconfig = {"compilerOptions": {"paths": {"@ui/*": ["./src/ui/*"], "@data/*": ["./packages/data/*"]}}}

        tsconfig_path = tmp_path / "tsconfig.json"
        with open(tsconfig_path, "w") as f:
            json.dump(tsconfig, f)

        resolver = AliasResolver(tmp_path)

        aliases = resolver.get_all_aliases()

        assert "@ui" in aliases
        assert "@data" in aliases
        assert len(aliases) >= 2
