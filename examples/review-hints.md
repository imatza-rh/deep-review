# .review-hints.md — Example Template

Place a `.review-hints.md` in your project root. The deep-review skill
loads it automatically and injects its content into all agent prompts.

Use this for project-specific patterns that generic reviewers miss.

## Example for a Go + Bubble Tea TUI project

```markdown
# Review Hints

## Framework: Bubble Tea (charmbracelet/bubbletea)
- Model/Update/View pattern — state mutations only in Update()
- tea.Cmd returns are async — don't assume ordering
- lipgloss styles are value types, not references

## Conventions
- All HTTP handlers use the middleware chain in middleware.go
- Store layer uses file-based persistence, not SQL
- go:embed for static assets — changes need `go generate`

## Known gotchas
- VIEWS array order matters — maps to tab indices
- SSE connections need explicit cleanup in shutdown handler
- Theme tokens in theme/ are the source of truth for colors
```

## Example for a Python + FastAPI project

```markdown
# Review Hints

## Framework: FastAPI + SQLAlchemy + Alembic
- Pydantic models validate all input — don't add manual validation
- async endpoints use asyncpg, sync background tasks use psycopg2
- Alembic migrations must be reversible (include downgrade)

## Conventions
- All routes in app/api/v1/ — never add routes to main.py
- Dependency injection via Depends() — don't instantiate services directly
- Tests use factory_boy fixtures, not raw SQL inserts

## Known gotchas
- CORS middleware order matters — must be first
- Background tasks don't have request context — pass data explicitly
- Rate limiter uses Redis — tests need REDIS_URL or will be skipped
```
