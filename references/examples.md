# Calibration Examples

These worked examples calibrate severity classification and false positive filtering. Consult them when uncertain.

## Example 1: Real Finding — Critical (SQL Injection)

**Diff:**
```python
# api/views.py
def search_users(request):
    query = request.GET.get("q", "")
    results = User.objects.raw(f"SELECT * FROM users WHERE name LIKE '%{query}%'")
    return JsonResponse({"users": list(results)})
```

**Analysis:** External input (`request.GET`) flows directly into a raw SQL query without parameterization.
**Data flow:** `request.GET("q") → search_users:3 → User.objects.raw:3`
**Framework check:** Django ORM parameterizes `.filter()` calls automatically, but `.raw()` with f-string bypasses this.
**Disproval attempt:** No upstream sanitization. No middleware filtering `q` parameter. Public endpoint (no auth required).
**Verdict:** `Critical` `confirmed` — any user can inject SQL via the `q` parameter.

**Formatted finding:**
```
### 1. SQL injection via unsanitized search parameter `confirmed`

**`api/views.py:3`** — unauthenticated users can execute arbitrary SQL

**Data flow:** `request.GET("q") → search_users:3 → User.objects.raw:3`

​```python
results = User.objects.raw(f"SELECT * FROM users WHERE name LIKE '%{query}%'")
​```

**Fix:**
​```python
results = User.objects.raw("SELECT * FROM users WHERE name LIKE %s", [f"%{query}%"])
​```
```

## Example 2: False Positive — Framework Handles It

**Diff:**
```python
# api/views.py
@app.post("/users")
async def create_user(user: UserCreate):
    db_user = User(**user.model_dump())
    db.add(db_user)
    return db_user
```

**Initial reaction:** "Mass assignment! User-controlled fields go directly into the model."
**Framework check:** FastAPI + Pydantic validates input against the `UserCreate` schema. Only fields defined in the schema are accepted. Extra fields are silently dropped.
**Disproval:** The `UserCreate` schema acts as an allowlist. Even if the request includes `is_admin=true`, Pydantic strips it unless `UserCreate` explicitly has that field.
**Verdict:** Drop. The framework's input validation prevents mass assignment.

**Lesson:** Always check what the framework does before flagging input handling. Pydantic schemas, Django Forms, and similar tools are purpose-built defenses.

## Example 3: Severity Calibration — Warning, Not Critical

**Diff:**
```python
# auth/tokens.py
def verify_token(token: str, expected: str) -> bool:
    return token == expected
```

**Analysis:** String comparison of auth tokens is vulnerable to timing attacks — an attacker can determine the token character-by-character by measuring response time.
**Preconditions:** Attacker needs (1) network access to the endpoint, (2) ability to make many requests with precise timing, (3) low network jitter.
**Framework check:** No rate limiting. But the endpoint is internal-only (bound to 127.0.0.1).
**Disproval attempt:** Being internal-only means the attacker needs local access, which significantly limits exploitation.
**Verdict:** `Warning` `likely` — real issue (should use `hmac.compare_digest`), but exploitability requires local network access, making it Warning not Critical.

**Formatted finding:**
```
### 1. Non-constant-time token comparison `likely`

**`auth/tokens.py:2`** — timing side-channel could leak token value to local network attackers

​```python
return token == expected  # vulnerable to timing attack
​```

**Fix:** `return hmac.compare_digest(token.encode(), expected.encode())`
```

## Example 4: Correctly Dropped — Intentional Behavior

**Diff:**
```python
# retry.py
except Exception:
    pass  # Best-effort cleanup; primary operation already succeeded
```

**Initial reaction:** "Silent error swallowing! This hides bugs."
**Context check:** The comment explains this is intentional cleanup after the main operation succeeded. The `except Exception: pass` is deliberately broad because any cleanup failure is non-critical.
**Git history:** `git log --oneline -3 retry.py` shows a commit message: "Add best-effort cleanup with intentional broad exception handling."
**Verdict:** Drop. The commit message and comment confirm this is intentional. Flagging it would be noise.

## Example 5: Suggestion — Not Broken But Improvable

**Diff:**
```python
# sync.py
async def sync_all_items(items: list[Item]):
    for item in items:
        await fetch_and_update(item)  # sequential, one at a time
```

**Analysis:** Sequential async calls where concurrent execution is possible. For 100 items with 200ms latency each, this takes 20 seconds instead of ~200ms with concurrency.
**Is it broken?** No — it's correct, just slow.
**Is it in a hot path?** Called from a background job that runs every 5 minutes.
**Verdict:** `Suggestion` `confirmed` — correct but could use `asyncio.gather()` with a semaphore for concurrency. Low urgency since it's a background job.
