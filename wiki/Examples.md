# Examples

Real-world scenarios showing how to use Code Scalpel through natural conversation with your AI assistant.

## Table of Contents

- [Extracting Code](#extracting-code)
- [Security Analysis](#security-analysis)
- [Safe Refactoring](#safe-refactoring)
- [Test Generation](#test-generation)
- [Cross-File Analysis](#cross-file-analysis)
- [Real-World Scenarios](#real-world-scenarios)

---

## Extracting Code

### Scenario: Extract a Specific Function

**You say:**
> "I need to understand the payment processing logic. Extract the process_payment function from services/payment.py"

**AI Assistant (using Code Scalpel):**
> "Here's the process_payment function:
>
> ```python
> def process_payment(order: Order, payment_method: str) -> Transaction:
>     \"\"\"Process payment for an order using the specified method.\"\"\"
>     if payment_method == 'credit_card':
>         return process_credit_card(order.total)
>     elif payment_method == 'paypal':
>         return process_paypal(order.total)
>     else:
>         raise ValueError(f"Unsupported payment method: {payment_method}")
> ```
>
> This function:
> - Takes an Order object and payment method
> - Routes to different payment processors
> - Returns a Transaction object
> - Raises ValueError for invalid methods
>
> The function is 8 lines, complexity score: 2/10"

**Why this is better:**
- Extracted only the function needed (50 tokens vs 10,000)
- Includes necessary imports automatically
- Ready to discuss or modify

---

### Scenario: Extract Component with Dependencies

**You say:**
> "Show me the UserProfile React component from components/UserProfile.tsx, including any helper hooks it uses"

**AI Assistant (using Code Scalpel):**
> "Here's the UserProfile component and its dependencies:
>
> ```typescript
> // Helper hook (imported from hooks/useUser.ts)
> function useUser(id: string) {
>   const [user, setUser] = useState(null);
>   useEffect(() => {
>     fetchUser(id).then(setUser);
>   }, [id]);
>   return user;
> }
>
> // Main component
> export function UserProfile({ userId }: { userId: string }) {
>   const user = useUser(userId);
>   
>   if (!user) return <div>Loading...</div>;
>   
>   return (
>     <div className="profile">
>       <h1>{user.name}</h1>
>       <p>{user.email}</p>
>     </div>
>   );
> }
> ```
>
> The component:
> - Uses custom hook useUser for data fetching
> - Shows loading state
> - Renders user profile card
> - Complexity: 3/10"

**Why this is helpful:**
- All dependencies included automatically
- No manual hunting through imports
- Complete context for understanding

---

## Security Analysis

### Scenario: Find SQL Injection Vulnerability

**You say:**
> "I'm concerned about SQL injection in this user search function. Can you analyze it?"
> ```python
> def find_user(search_term):
>     user_id = request.args.get("id")
>     query = f"SELECT * FROM users WHERE id = {user_id}"
>     db.execute(query)
>     return db.fetchone()
> ```

**AI Assistant (using Code Scalpel):**
> "⚠️ **CRITICAL: SQL Injection Vulnerability Found**
>
> **CWE-89** - SQL Injection (Severity: CRITICAL)
>
> **Issue:**
> ```
> Line 2: user_id = request.args.get("id")  ← Untrusted input source
> Line 3: query = f"SELECT * FROM users WHERE id = {user_id}"  ← Tainted in SQL
> Line 4: db.execute(query)  ← Dangerous sink
> ```
>
> **Attack example:**
> - User provides: `id=1 OR 1=1`
> - Query becomes: `SELECT * FROM users WHERE id = 1 OR 1=1`
> - Result: ALL users returned instead of one
>
> **Fix:**
> ```python
> def find_user_safe(search_term):
>     user_id = request.args.get("id")
>     query = "SELECT * FROM users WHERE id = %s"
>     db.execute(query, (user_id,))  ← Parameterized query
>     return db.fetchone()
> ```
>
> Using parameterized queries prevents SQL injection by treating the parameter as data, not code."

**Why this matters:**
- Automatically traces taint from input to sink
- Identifies attack vectors
- Suggests proper mitigation

---

### Scenario: Cross-File Security Analysis

**You say:**
> "I'm refactoring the API layer. Make sure no security vulnerabilities are introduced by changes that span multiple files"

**AI Assistant (using Code Scalpel):**
> "Running cross-file security analysis...
>
> ✅ **No critical vulnerabilities found**
>
> **Analysis covered:**
> - All API endpoints (handlers/)
> - Service layer (services/)
> - Database layer (db/)
> - Taint flow across module boundaries
>
> **Results:**
> - 127 files scanned
> - 3,847 data flows analyzed
> - All injection points validated
>
> **Checked for:**
> - SQL injection (CWE-89)
> - Command injection (CWE-78)
> - XSS vulnerabilities (CWE-79)
> - Path traversal (CWE-22)
> - LDAP injection (CWE-90)
>
> Your refactoring is security-safe!"

---

## Safe Refactoring

### Scenario: Rename Function Safely

**You say:**
> "The validate_input function isn't clear. I want to rename it to validate_user_input. Is it safe to do this?"

**AI Assistant (using Code Scalpel):**
> "Analyzing the impact of renaming validate_input → validate_user_input...
>
> ✅ **Safe to rename!**
>
> **Impact Analysis:**
> - Function definition: utils.py line 42
> - Call sites: 5 locations
>   - handlers.py line 156 (direct call)
>   - tests/test_utils.py line 23 (imported function)
>   - services/user.py line 89 (imported function)
>   - admin/views.py line 34 (imported function)
>   - conftest.py line 12 (imported in test fixture)
>
> **Safety checks:**
> ✓ No dependencies on function name in strings
> ✓ No dynamic calls (getattr, eval)
> ✓ All imports are static (not lazy-loaded)
> ✓ No backward compatibility needed
>
> I can update all 5 locations automatically."

**Next step:**
> You: "Go ahead and rename it across all files"
> AI: (applies rename_symbol across all locations)

---

### Scenario: Refactor with Confidence

**You say:**
> "I want to improve this payment processing function for better error handling. Is this refactoring safe?"
> 
> **Original:**
> ```python
> def process_payment(order):
>     try:
>         return stripe.charge(order.total)
>     except Exception:
>         return None
> ```
>
> **New version:**
> ```python
> def process_payment(order):
>     try:
>         return stripe.charge(order.total)
>     except stripe.CardError as e:
>         logger.error(f"Card error: {e}")
>         raise PaymentError(f"Card declined: {str(e)}")
>     except stripe.RateLimitError:
>         logger.warning("Stripe rate limit hit")
>         raise PaymentError("Temporarily unavailable")
> ```

**AI Assistant (using Code Scalpel):**
> "Analyzing the refactoring...
>
> ✅ **Refactoring is SAFE**
>
> **Security Analysis:**
> ✓ No new injection points introduced
> ✓ Error messages don't leak sensitive data
> ✓ Proper exception types used
>
> **Behavioral Analysis:**
> ✓ Function signature unchanged (compatible with callers)
> ✓ Exceptions more specific (better error handling)
> ⚠️ Return values differ: Old code returns None on error, new code raises exception
>
> **Impact:**
> - Callers that check `if result is None:` need updating (3 locations)
> - Callers that catch Exception still work
> - Better error reporting downstream
>
> Recommend: Update 3 call sites to handle PaymentError exception instead of None return."

---

## Test Generation

### Scenario: Generate Comprehensive Tests

**You say:**
> "Generate unit tests for this validation function. I want tests that cover all branches and edge cases."
> ```python
> def validate_email(email: str) -> bool:
>     if not email:
>         return False
>     if '@' not in email:
>         return False
>     parts = email.split('@')
>     if len(parts) != 2:
>         return False
>     local, domain = parts
>     if not domain or '.' not in domain:
>         return False
>     return True
> ```

**AI Assistant (using Code Scalpel):**
> "Analyzing execution paths... Found 8 possible paths.
>
> Here are comprehensive tests covering all branches:
>
> ```python
> import pytest
> from email_validator import validate_email
>
> class TestValidateEmail:
>     \"\"\"Tests covering all execution paths of validate_email\"\"\"
>
>     # Path 1: Empty email
>     def test_empty_string(self):
>         assert validate_email("") is False
>     
>     # Path 2: Email without @
>     def test_no_at_symbol(self):
>         assert validate_email("invalid.email") is False
>     
>     # Path 3: Multiple @ symbols
>     def test_multiple_at_symbols(self):
>         assert validate_email("user@@example.com") is False
>     
>     # Path 4: Domain without dot
>     def test_domain_no_dot(self):
>         assert validate_email("user@localhost") is False
>     
>     # Path 5: Empty domain
>     def test_empty_domain(self):
>         assert validate_email("user@") is False
>     
>     # Path 6: Valid email (basic)
>     def test_valid_email(self):
>         assert validate_email("user@example.com") is True
>     
>     # Path 7: Valid with subdomain
>     def test_valid_email_subdomain(self):
>         assert validate_email("user@mail.example.co.uk") is True
>     
>     # Path 8: Edge case - single char domain
>     def test_single_char_domain(self):
>         assert validate_email("user@x.co") is True
> ```
>
> **Coverage:** 8/8 execution paths covered
> **Complexity:** All branches tested"

---

## Cross-File Analysis

### Scenario: Understand Import Dependencies

**You say:**
> "I'm planning to refactor the billing module. What other parts of the system depend on it?"

**AI Assistant (using Code Scalpel):**
> "Analyzing billing module dependencies...
>
> **Direct imports of billing:**
> - api/handlers.py (3 functions use billing)
> - admin/reports.py (invoice generation)
> - tasks/email.py (billing notifications)
> - tests/test_billing.py (unit tests)
>
> **Call chain examples:**
>
> ```
> api/handlers.py:create_order()
>   └─> billing.process_payment()
>       └─> stripe.charge()
>
> admin/reports.py:generate_invoice_report()
>   └─> billing.calculate_invoice_total()
>       └─> billing.apply_discounts()
>
> tasks/email.py:send_billing_email()
>   └─> billing.get_recent_charges()
> ```
>
> **Impact of changes:**
> - Changing process_payment signature: breaks 5 call sites
> - Changing calculate_invoice_total: breaks 2 locations
> - Adding new payment method: no breaking changes needed
>
> **Safe refactoring approach:**
> 1. Add new functions, don't modify existing ones
> 2. Keep process_payment signature stable
> 3. Test billing heavily (3 services depend on it)"

---

## Real-World Scenarios

### Scenario 1: Emergency Security Patch

**Situation:** You found a security vulnerability that needs immediate fixing.

**You say:**
> "We have a critical SQL injection in the search endpoint. I need:
> 1. Confirm the vulnerability
> 2. Fix it
> 3. Make sure the fix doesn't break anything"

**AI Assistant (using Code Scalpel):**

> **Step 1: Confirm vulnerability**
> ✓ SQL Injection found in search_users (CWE-89)
> ✓ Taint flow: request.args → SQL query
>
> **Step 2: Apply fix**
> ```python
> # BEFORE (vulnerable)
> query = f"SELECT * FROM users WHERE name LIKE '%{search_term}%'"
>
> # AFTER (safe)
> query = "SELECT * FROM users WHERE name LIKE %s"
> cursor.execute(query, (f"%{search_term}%",))
> ```
>
> **Step 3: Impact analysis**
> - Callers of search_users: 4 locations
> - All use return value as iterable: ✓ compatible
> - No breaking changes
> - Unit tests updated: ✓
>
> ✅ **Patch is ready and safe to deploy**

---

### Scenario 2: Refactoring Legacy Code

**Situation:** You're modernizing a 10-year-old codebase.

**You say:**
> "This authentication module is from 2014. I want to refactor it to use modern practices. Help me understand what depends on it and ensure safe changes."

**AI Assistant (using Code Scalpel):**

> **Current state:**
> - 347 lines of code
> - 12 functions
> - Complexity: 7/10
>
> **Dependencies:**
> - 23 files import from auth.py
> - 2 externally-facing APIs depend on current signatures
>
> **Safe refactoring path:**
> 1. Create new auth_v2.py alongside old auth.py
> 2. Migrate services one at a time
> 3. Keep auth.py as legacy fallback
> 4. Deprecate after 6 months
>
> **Step 1: Extract and analyze current functions**
> (Shows 12 function signatures)
>
> **Step 2: Refactor in phases**
> - Phase 1: Internal services (8 files)
> - Phase 2: API endpoints (2 files)
> - Phase 3: Remove legacy auth.py
>
> I can track this migration and verify safety at each step."

---

### Scenario 3: Code Review

**Situation:** A team member submitted a PR with significant changes.

**You say:**
> "Review this pull request for security issues and potential bugs. The PR modifies payment processing and user authentication."

**AI Assistant (using Code Scalpel):**

> **Security Analysis:**
> ✓ No new SQL injection vectors
> ✓ Passwords still hashed properly
> ✓ No hardcoded secrets in code
> ✓ CSRF tokens validated
> ⚠️ One concern found (see below)
>
> **Behavioral Changes:**
> - Payment timeout increased from 30s to 60s
> - User session length extended from 1h to 2h
> - New OAuth2 provider added (Google)
>
> **Concerns:**
>
> 1. **Session timeout change - Verify intent**
>    - Affects security stance
>    - May need admin notification
>    - Recommend: 90 minutes compromise
>
> 2. **Test coverage**
>    - 3 new code paths have no tests
>    - Recommend: Add tests for Google OAuth flow
>
> 3. **Breaking changes**
>    - session.get_remaining_time() now returns different values
>    - 1 location needs updating
>
> **Recommendation:** Approve after addressing 2 tests and verifying session timeout intent with author."

