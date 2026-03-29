---
name: cs-extract
description: |
  Extract a specific function, class, or method from a file using Code Scalpel.
  Use when you need to show a symbol without reading the entire file—saves 95% of context.
allowed-tools:
  - mcp__codescalpel__extract_code
  - mcp__codescalpel__get_file_context
preamble-tier: 1
---

# /cs-extract — Get Code by Name (Not by Reading)

Extract a function, class, or method from a file without reading the entire file.

## Usage

```bash
/cs-extract src/utils.py function calculate_tax
/cs-extract src/models/User.tsx class UserCard
/cs-extract src/services/auth.py function verify_token
```

## Why This Matters

- **Read entire file:** ~10,000 tokens
- **Extract by name:** ~50 tokens
- **Savings:** 99.5% context efficiency

## Under the Hood

1. If you don't know the symbol name, runs `get_file_context` to list all symbols in the file
2. Calls `extract_code(file_path, target_type, target_name)` to surgically extract just that symbol
3. Returns the code with metadata (line range, dependencies, signature)

## Next Steps

Once you have the code:
- Use `/cs-analyze` to understand structure
- Use `/cs-refactor` to modify safely
- Use `/cs-tests` to generate tests for it

See `CLAUDE.md` for more examples.
