# Language-Specific Review Patterns

> **Contents**: Python — Go — Rust — Java — Shell/Bash — Ansible/YAML — JavaScript/TypeScript — Meta-Patterns (Language-Agnostic)

High-signal patterns — issues that are both common and impactful. Consult for the relevant language.

## Python

**Security:**
- `subprocess.call(shell=True)` with string interpolation → command injection
- `pickle.loads()` on untrusted data → arbitrary code execution
- `yaml.load()` without `Loader=SafeLoader` → code execution
- `eval()`, `exec()` with external input → code execution
- f-string or `.format()` in SQL queries → SQL injection (use parameterized queries)
- `os.path.join()` with user input without sanitizing `..` → path traversal
- `requests.get(user_url)` without URL validation → SSRF
- `hashlib.md5/sha1` for password hashing → use `bcrypt`/`argon2`

**Correctness:**
- Mutable default arguments (`def f(x=[])`) — shared across calls
- `except Exception` or bare `except:` swallowing errors silently
- `is` vs `==` for value comparison (only use `is` for None/singletons)
- Dictionary iteration while modifying — RuntimeError
- Missing `async`/`await` — returns coroutine object instead of result
- `datetime.now()` vs `datetime.utcnow()` vs timezone-aware — timezone bugs

**Performance:**
- String concatenation in loops → O(n²), use `''.join()` or list
- `in` on list vs set for membership testing → O(n) vs O(1)
- Reading entire file into memory for large files → use streaming/chunked reads

## Go

**Security:**
- Unsanitized user input in `fmt.Sprintf` used for SQL/commands
- Missing `defer resp.Body.Close()` → resource leak
- `crypto/rand` vs `math/rand` — use `crypto/rand` for security-sensitive randomness
- `net/http` default client follows redirects — SSRF risk with user-controlled URLs

**Correctness:**
- Goroutine leaks — goroutines started without cancellation context or done channel
- Range loop variable capture in goroutine closure — captures pointer, not value (pre-Go 1.22)
- Nil map write — panics (must `make(map[K]V)` first)
- Interface nil check pitfall — typed nil vs interface nil
- Deferred function argument evaluation — evaluated at defer time, not execution time
- Missing error check — `err` returned but not checked (especially `rows.Close()`, `f.Close()`)
- Error wrapping: `fmt.Errorf("...: %w", err)` vs `%v` — unwrapping breaks with `%v`

**Performance:**
- `sync.Mutex` vs `sync.RWMutex` — use RWMutex for read-heavy workloads
- Unbuffered channels as semaphores in hot paths → contention
- `context.WithCancel` not called → goroutine and memory leak

## Rust

**Security:**
- `unsafe` blocks — review every one; justify why safe alternatives don't work
- `.unwrap()` / `.expect()` in library code → panic in caller's context
- `std::mem::transmute` — almost always wrong; use safe casts
- Raw pointer dereference without lifetime/aliasing proof

**Correctness:**
- `Send`/`Sync` trait violations when using interior mutability
- Lifetime annotations that are too permissive → dangling references
- `.clone()` to satisfy the borrow checker — hides ownership design issues
- `match` arms that use `_` catch-all and silently ignore new variants after enum extension
- Integer overflow in release builds (wraps silently, unlike debug builds which panic)

**Performance:**
- Unnecessary `.collect()` between iterator chains — allocates intermediate `Vec`
- `Arc<Mutex<T>>` when `Arc<RwLock<T>>` or lock-free alternatives fit better

## Java

**Security:**
- `ObjectInputStream.readObject()` on untrusted data → deserialization attacks
- `Runtime.exec()` with string concatenation → command injection
- `String.format()` in SQL → injection (use PreparedStatement)
- Reflection with user-controlled class names → arbitrary code execution

**Correctness:**
- Missing `@Override` — method doesn't actually override (signature mismatch)
- `equals()` without `hashCode()` → broken HashMap/HashSet behavior
- `ConcurrentModificationException` from iterating and modifying collections
- `try-with-resources` missing → resource leak (connections, streams)
- `==` on Integer objects outside [-128, 127] cache range → false negatives

**Performance:**
- String concatenation in loops → use `StringBuilder`
- Autoboxing in tight loops → unnecessary object creation
- `synchronized` on wrong granularity → contention or insufficient locking

## Shell / Bash

**Security:**
- Unquoted variables in command arguments → word splitting, glob expansion
- `eval` with external input → command injection
- Temp files with predictable names → symlink attacks (use `mktemp`)
- `curl | bash` patterns without checksum verification

**Correctness:**
- Missing `set -euo pipefail` — scripts continue after errors
- `[ $var = "value" ]` without quoting `$var` — breaks on spaces or empty
- `cd` without error check — subsequent commands run in wrong directory
- Array handling differences between bash and sh/dash

## Ansible / YAML

**Security:**
- Secrets in plain text (should be in vault or env vars)
- `become: yes` without `become_user` — defaults to root
- `shell:` or `command:` with Jinja2 variables — command injection

**Correctness:**
- Missing `when:` conditions on tasks that should be conditional
- `register:` variable used without checking `.rc` or `.failed`
- Missing `changed_when: false` on idempotent commands — false change reports
- YAML gotchas: `yes`/`no`/`on`/`off` parsed as booleans, `1:2` as sexagesimal

## JavaScript / TypeScript

**Security:**
- `innerHTML` or `dangerouslySetInnerHTML` with unsanitized input → XSS
- `eval()`, `new Function()` with external input
- Prototype pollution via `Object.assign` or spread with user-controlled keys
- Missing CSRF tokens on state-changing endpoints
- CORS: `Access-Control-Allow-Origin: *` with credentials → security hole

**Correctness:**
- `==` vs `===` — type coercion surprises
- Missing `await` on async functions — returns Promise instead of value
- `forEach` with `async` callback — doesn't await iterations
- Array sort without comparator — sorts as strings (`[10, 9, 80].sort()` → `[10, 80, 9]`)
- React: missing dependencies in `useEffect`/`useMemo`/`useCallback` dependency arrays
- Event listener leaks — `addEventListener` without corresponding `removeEventListener`

## Meta-Patterns (Language-Agnostic)

These apply everywhere:

- **TOCTOU (Time-of-check to time-of-use)** — checking a condition then acting on it without atomicity (file existence check → file open, permission check → action)
- **Logging secrets** — credentials, tokens, or PII in log statements, error messages, or stack traces
- **Inconsistent error handling** — some functions in a module handle errors gracefully while siblings don't (diverged copies)
- **Mixing sync and async** — blocking calls inside async functions (blocks the event loop)
- **Hardcoded limits that should be configurable** — magic numbers for timeouts, retries, buffer sizes
- **Missing pagination** — API endpoints or DB queries that return unbounded results
- **IDOR (Insecure Direct Object Reference)** — accessing resources by ID without ownership verification
- **Mass assignment** — accepting user-controlled fields directly into data models without allowlisting
