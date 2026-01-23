# Troubleshooting

Common issues and solutions when using Code Scalpel.

## Installation Issues

### ModuleNotFoundError: No module named 'code_scalpel'

**Symptom:**
```
ModuleNotFoundError: No module named 'code_scalpel'
```

**Solutions:**

1. **Verify installation:**
   ```bash
   pip list | grep code-scalpel
   ```

2. **Reinstall:**
   ```bash
   pip uninstall code-scalpel
   pip install code-scalpel
   ```

3. **Check Python version:**
   ```bash
   python --version  # Should be 3.10+
   ```

4. **Virtual environment issue:**
   ```bash
   # Activate your virtualenv
   source venv/bin/activate
   
   # Reinstall
   pip install code-scalpel
   ```

### ImportError: cannot import name 'tomllib'

**Symptom:**
```
ImportError: cannot import name 'tomllib' from 'tomli'
```

**Cause:** Python < 3.11 needs `tomli` instead of `tomllib`

**Solution:**
```bash
pip install tomli
```

### Z3 Solver Not Found

**Symptom:**
```
ModuleNotFoundError: No module named 'z3'
```

**Solution:**
```bash
# Install Z3 solver
pip install z3-solver

# Or install with all optional dependencies
pip install code-scalpel[all]
```

---

## Configuration Issues

### "SCALPEL_MANIFEST_SECRET not set"

**Symptom:**
```
SecurityError: SCALPEL_MANIFEST_SECRET environment variable not set
```

**Solution:**

1. **Initialize configuration:**
   ```bash
   python -m code_scalpel init
   ```

2. **Or manually set:**
   ```bash
   # Generate secure secret
   python -c "import secrets; print(secrets.token_hex(32))"
   
   # Add to .env
   echo "SCALPEL_MANIFEST_SECRET=<generated-secret>" >> .env
   ```

3. **Load .env in Python:**
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

### "Policy integrity verification failed"

**Symptom:**
```
SecurityError: Policy file hash mismatch
```

**Causes:**
1. Policy files modified after manifest generation
2. Wrong secret key
3. Corrupted manifest

**Solutions:**

1. **Regenerate manifest:**
   ```bash
   code-scalpel regenerate-manifest
   ```

2. **Verify secret:**
   ```bash
   echo $SCALPEL_MANIFEST_SECRET
   # Should match value in .env
   ```

3. **Reset policies:**
   ```bash
   # Backup current policies
   cp -r policies policies.bak
   
   # Reinitialize
   python -m code_scalpel init --force
   ```

---

## MCP Connection Issues

### "MCP server not responding"

**Symptom:**
- AI assistant can't connect to Code Scalpel
- No response from tools

**Solutions:**

1. **Check server is running:**
   ```bash
   # Test manually
   python -m code_scalpel.mcp.server
   ```

2. **Verify MCP configuration:**
   
   **VS Code** (`.vscode/mcp.json`):
   ```json
   {
     "mcpServers": {
       "code-scalpel": {
         "command": "python",
         "args": ["-m", "code_scalpel.mcp.server"],
         "env": {
           "SCALPEL_PROJECT_ROOT": "${workspaceFolder}"
         }
       }
     }
   }
   ```
   
   **Claude Desktop** (`claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "code-scalpel": {
         "command": "python",
         "args": ["-m", "code_scalpel.mcp.server"]
       }
     }
   }
   ```

3. **Check Python path:**
   ```bash
   which python
   # Use absolute path in MCP config if needed
   ```

4. **Enable debug logging:**
   ```json
   {
     "env": {
       "SCALPEL_LOG_LEVEL": "DEBUG"
     }
   }
   ```

### Docker Connection Issues

**Symptom:**
- Docker container starts but tools fail
- Permission errors

**Solutions:**

1. **Volume mount permissions:**
   ```bash
   docker run -i --rm \
     -v $(pwd):/workspace \
     -u $(id -u):$(id -g) \
     3dtechsolutions/code-scalpel:latest
   ```

2. **Check Docker logs:**
   ```bash
   docker logs <container-id>
   ```

3. **Test manually:**
   ```bash
   docker run -it --rm \
     3dtechsolutions/code-scalpel:latest \
     python -c "from code_scalpel import __version__; print(__version__)"
   ```

---

## Extraction Issues

### "Symbol not found"

**Symptom:**
```
SymbolNotFoundError: Function 'calculate_taxes' not found
```

**Solutions:**

1. **Check available symbols:**
   ```python
   context = get_file_context(file_path="utils.py")
   print(context.functions)
   # See actual function names
   ```

2. **Use exact name:**
   ```python
   # ❌ Wrong
   extract_code(target_name="calculateTax")  # CamelCase
   
   # ✅ Correct
   extract_code(target_name="calculate_tax")  # snake_case
   ```

3. **For class methods:**
   ```python
   # Use ClassName.method_name format
   extract_code(
       target_type="method",
       target_name="Calculator.add"
   )
   ```

### "File not found"

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'utils.py'
```

**Solutions:**

1. **Use absolute paths:**
   ```python
   # ❌ Wrong
   extract_code(file_path="utils.py")
   
   # ✅ Correct
   import os
   extract_code(file_path=os.path.abspath("utils.py"))
   ```

2. **Check working directory:**
   ```python
   import os
   print(os.getcwd())
   ```

3. **Set SCALPEL_PROJECT_ROOT:**
   ```bash
   export SCALPEL_PROJECT_ROOT=/path/to/project
   ```

### Windows Path Issues

**Symptom:**
```
Invalid path: C:\Users\Name\project
```

**Solution:**

Use forward slashes on all platforms:

```python
# ❌ Wrong (Windows backslashes)
file_path = "C:\\Users\\Name\\project\\file.py"

# ✅ Correct (forward slashes)
file_path = "C:/Users/Name/project/file.py"

# Or use pathlib
from pathlib import Path
file_path = str(Path("C:/Users/Name/project/file.py"))
```

---

## Security Scanning Issues

### "No vulnerabilities detected" (False Negative)

**Symptom:**
- Known vulnerability not detected
- Taint analysis misses flow

**Solutions:**

1. **Lower confidence threshold:**
   ```python
   security_scan(
       code=code,
       min_confidence=0.5  # Default is 0.7
   )
   ```

2. **Specify entry points:**
   ```python
   security_scan(
       code=code,
       entry_points=["handle_request", "process_input"]
   )
   ```

3. **Use cross-file scan:**
   ```python
   # For vulnerabilities spanning files
   cross_file_security_scan(
       entry_file="api/handlers.py",
       entry_points=["handle_request"],
       max_depth=5
   )
   ```

### "Too many false positives"

**Symptom:**
- Legitimate code flagged as vulnerable

**Solutions:**

1. **Raise confidence threshold:**
   ```python
   security_scan(
       code=code,
       min_confidence=0.9  # More strict
   )
   ```

2. **Review taint flow:**
   ```python
   for vuln in result.vulnerabilities:
       print("Taint flow:")
       for step in vuln.taint_flow:
           print(f"  {step}")
       # Verify if flow is actually exploitable
   ```

### Symbolic Execution Timeout

**Symptom:**
```
TimeoutError: Symbolic execution exceeded 30 seconds
```

**Solutions:**

1. **Increase timeout:**
   ```python
   symbolic_execute(
       code=function,
       timeout=60  # Increase to 60 seconds
   )
   ```

2. **Reduce path limit:**
   ```python
   symbolic_execute(
       code=function,
       max_paths=5  # Reduce from default 10
   )
   ```

3. **Simplify function:**
   - Extract smaller subfunctions
   - Reduce loop complexity

---

## Performance Issues

### "Token limit exceeded"

**Symptom:**
- AI assistant context window full
- Too much code returned

**Solutions:**

1. **Use extraction instead of full file read:**
   ```python
   # ❌ Inefficient
   full_file = read_file("large_file.py")  # 10,000 tokens
   
   # ✅ Efficient
   function = extract_code(
       file_path="large_file.py",
       target_name="process"
   )  # 50 tokens (99% savings)
   ```

2. **Limit context depth:**
   ```python
   extract_code(
       file_path="file.py",
       target_name="function",
       include_context=True,
       context_depth=1  # Reduce from 2
   )
   ```

3. **Disable cross-file deps:**
   ```python
   extract_code(
       file_path="file.py",
       target_name="function",
       include_cross_file_deps=False
   )
   ```

### "Analysis too slow"

**Symptom:**
- Long wait times for analysis
- Operations timing out

**Solutions:**

1. **Enable caching:**
   ```bash
   export CODE_SCALPEL_CACHE_ENABLED=true
   ```

2. **Reduce max_depth:**
   ```python
   get_call_graph(
       file_path="file.py",
       max_depth=2  # Reduce from 3
   )
   ```

3. **Limit file count:**
   ```python
   crawl_project(
       project_root="/project",
       file_pattern="**/*.py",  # Be specific
       max_files=500  # Add limit
   )
   ```

4. **Use selective scanning:**
   ```python
   # ❌ Scan entire project
   security_scan(project_root="/project")
   
   # ✅ Scan specific files
   security_scan(code=specific_file_code)
   ```

---

## Tier & Licensing Issues

### "Tier limit exceeded"

**Symptom:**
```
TierLimitError: Community tier limited to 50 findings
```

**Solutions:**

1. **Check current tier:**
   ```bash
   echo $SCALPEL_TIER
   ```

2. **Upgrade to Pro/Enterprise:**
   ```bash
   # Set tier
   export SCALPEL_TIER=pro
   
   # Provide license file
   export SCALPEL_LICENSE_PATH=/path/to/license.jwt
   ```

3. **For Community tier workarounds:**
   - Process files in batches
   - Filter results by severity
   - Use more specific queries

### "License validation failed"

**Symptom:**
```
LicenseError: Invalid or expired license
```

**Solutions:**

1. **Check license file:**
   ```bash
   ls -l $SCALPEL_LICENSE_PATH
   cat $SCALPEL_LICENSE_PATH | head -1
   ```

2. **Verify license not expired:**
   ```bash
   # Decode JWT (body only)
   python -c "
   import jwt
   token = open('license.jwt').read()
   print(jwt.decode(token, options={'verify_signature': False}))
   "
   ```

3. **Contact support:**
   - Email: time@3dtechsolutions.us
   - Include license ID and error message

---

## Language Support Issues

### "Unsupported language"

**Symptom:**
```
LanguageError: Language 'kotlin' not supported
```

**Supported Languages:**
- ✅ Python (full support)
- ✅ JavaScript/TypeScript (full support)
- ✅ Java (AST parsing)
- ✅ Go (AST parsing)
- ✅ Rust (AST parsing)
- ✅ Ruby (AST parsing)
- ✅ PHP (AST parsing)

**Solution:**
For unsupported languages, basic extraction may still work via tree-sitter.

### JavaScript/TypeScript Parsing Errors

**Symptom:**
```
ParseError: Invalid syntax in JavaScript code
```

**Solutions:**

1. **Specify language explicitly:**
   ```python
   extract_code(
       file_path="file.jsx",
       target_name="Component",
       language="jsx"  # Explicit
   )
   ```

2. **Check JSX/TSX:**
   ```python
   # For React components
   extract_code(
       file_path="Component.tsx",
       language="tsx"
   )
   ```

---

## Common Error Messages

### "Object of type None is not subscriptable"

**Cause:** Trying to access attribute of None

**Solution:** Check that symbol exists first:
```python
context = get_file_context(file_path="file.py")
if "target_function" in context.functions:
    result = extract_code(target_name="target_function")
```

### "Path traversal detected"

**Cause:** Path escapes project root

**Solution:** Use `validate_paths` first:
```python
result = validate_paths(
    paths=[user_path],
    base_path="/project"
)

if result.results[0].valid:
    extract_code(file_path=user_path)
```

### "Maximum recursion depth exceeded"

**Cause:** Circular dependencies or too deep call graph

**Solutions:**

1. **Limit depth:**
   ```python
   get_call_graph(max_depth=2)
   ```

2. **Disable transitive deps:**
   ```python
   get_cross_file_dependencies(resolve_transitive=False)
   ```

---

## Getting Help

### Enable Debug Logging

```bash
export SCALPEL_LOG_LEVEL=DEBUG
export SCALPEL_ENABLE_TRACING=true
```

### Collect Diagnostic Info

```bash
# Version info
python -m code_scalpel --version

# Environment
python -m code_scalpel config show

# Test installation
python -m pytest tests/ -k "smoke" -v
```

### Report Issues

1. **GitHub Issues:** https://github.com/3D-Tech-Solutions/code-scalpel/issues
2. **Include:**
   - Code Scalpel version
   - Python version
   - OS and environment
   - Minimal reproduction code
   - Error message and traceback

### Community Support

- **Discussions:** GitHub Discussions for Q&A
- **Examples:** Check `examples/` directory
- **Documentation:** This wiki

---

**Related Pages:**
- [Installation](Installation) - Setup guide
- [Configuration](Configuration) - Environment variables
- [MCP Tools Reference](MCP-Tools-Reference) - API documentation
