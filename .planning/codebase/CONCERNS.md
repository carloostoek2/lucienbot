# Codebase Concerns

**Analysis Date:** 2026-03-29

## Tech Debt

**1. No Test Coverage:**
- Issue: Zero automated tests in codebase
- Files: Entire codebase (no `tests/` directory)
- Impact: High risk of regressions, manual testing required for all changes, difficult to refactor safely
- Fix approach: Add pytest with unit tests for services first, then integration tests for handlers

**2. Large Handler Files:**
- Issue: Handler files exceed 1000 lines
- Files: 
  - `handlers/story_admin_handlers.py` (1,119 lines)
  - `handlers/package_handlers.py` (922 lines)
  - `handlers/promotion_admin_handlers.py` (912 lines)
- Impact: Difficult to navigate, high cognitive load, merge conflicts likely
- Fix approach: Split by feature area (e.g., `story_admin_create.py`, `story_admin_edit.py`, `story_admin_list.py`)

**3. Database Session Management:**
- Issue: Services rely on `__del__` for session cleanup
- Files: All service files (`services/*.py`)
- Impact: Sessions may not close properly under load, potential connection exhaustion
- Fix approach: Use context managers or dependency injection with proper lifecycle management

**4. Incomplete Feature (Story/Narrative):**
- Issue: TODO comment indicates incomplete implementation
- Files: `handlers/story_admin_handlers.py:1107`
  ```python
  # TODO: Implementar metodo para obtener logros
  ```
- Impact: Feature gap, may cause confusion for developers
- Fix approach: Implement the missing method or remove the feature placeholder

## Known Bugs

**1. Race Condition in Token Redemption:**
- Symptoms: Two users click same token simultaneously, both might get access
- Files: `services/vip_service.py::redeem_token()`
- Trigger: Concurrent token redemption requests
- Workaround: Tokens are single-use by design, but race condition exists between validation and marking as used
- Fix approach: Add database-level unique constraint or use SELECT FOR UPDATE

**2. Scheduler May Miss Expirations:**
- Symptoms: VIP users not removed exactly at expiry time
- Files: `services/scheduler_service.py`
- Trigger: Scheduler runs every 30 seconds; if bot restarts, may miss window
- Workaround: None currently
- Fix approach: Add startup check for expired subscriptions, use persistent job queue

**3. Memory Storage for FSM:**
- Symptoms: User state lost on bot restart
- Files: `bot.py` (uses `MemoryStorage()`)
- Trigger: Bot restart during multi-step conversation
- Workaround: Users must restart conversation
- Fix approach: Use `RedisStorage` or `SQLiteStorage` for persistence

## Security Considerations

**1. Admin ID Validation:**
- Risk: Admin IDs checked only in handler filters, not at service level
- Files: `handlers/admin_handlers.py::is_admin()`
- Current mitigation: Callback query filters
- Recommendations: Add admin validation in service methods for defense in depth

**2. No Rate Limiting:**
- Risk: Users can spam commands, potentially overwhelming bot
- Files: All handlers
- Current mitigation: None detected
- Recommendations: Add aiogram middleware for rate limiting (e.g., `aiogram-dialog` or custom middleware)

**3. Token URL Exposure:**
- Risk: Token codes visible in URL, may be logged or leaked
- Files: `handlers/vip_handlers.py`
- Current mitigation: Tokens are single-use
- Recommendations: Use shorter-lived tokens or add IP-based validation

**4. SQL Injection (Low Risk):**
- Risk: String interpolation in some queries (though SQLAlchemy ORM is used)
- Files: Need audit of all `db.query()` calls
- Current mitigation: SQLAlchemy ORM parameterization
- Recommendations: Audit for any f-string usage in queries

## Performance Bottlenecks

**1. N+1 Query in Subscriber List:**
- Problem: Loading subscribers with user info triggers N+1 queries
- Files: `handlers/vip_handlers.py::list_subscribers()`
- Cause: `subscription.user` accessed in loop without eager loading
- Improvement path: Use `joinedload(User)` in query

**2. Full Table Scan for Pending Requests:**
- Problem: `get_ready_to_approve()` scans all pending requests
- Files: `services/channel_service.py`
- Cause: No index on `scheduled_approval_at` column
- Improvement path: Add database index on `pending_requests(scheduled_approval_at, status)`

**3. Scheduler Polling Inefficiency:**
- Problem: Scheduler polls database every 30 seconds regardless of load
- Files: `services/scheduler_service.py`
- Cause: Fixed interval polling
- Improvement path: Use dynamic interval based on next scheduled event

## Fragile Areas

**1. Callback Data Parsing:**
- Files: Multiple handlers parse callback data with string manipulation
  ```python
  tariff_id = int(callback.data.replace("select_tariff_", ""))
  ```
- Why fragile: String changes break parsing silently
- Safe modification: Use structured callback data or constants
- Test coverage: None

**2. Timezone Handling:**
- Files: `services/scheduler_service.py`, `services/vip_service.py`
- Why fragile: Mix of `datetime.utcnow()` and timezone-aware datetimes
- Safe modification: Standardize on timezone-aware datetimes everywhere
- Test coverage: None

**3. Bot Username in URLs:**
- Files: `handlers/vip_handlers.py`
  ```python
  token_url = f"https://t.me/{(await callback.bot.get_me()).username}?start={token.token_code}"
  ```
- Why fragile: API call on every token generation, could fail
- Safe modification: Cache bot username or pass as dependency
- Test coverage: None

## Scaling Limits

**1. SQLite Database:**
- Current capacity: ~100 concurrent users (estimated)
- Limit: SQLite file locking under write load
- Scaling path: Migrate to PostgreSQL (already supported via `DATABASE_URL`)

**2. Single Bot Instance:**
- Current capacity: One instance only
- Limit: aiogram polling doesn't support horizontal scaling
- Scaling path: Switch to webhook mode with load balancer, or use Redis for distributed FSM

**3. In-Memory Scheduler:**
- Current capacity: Single process
- Limit: Scheduler state lost on restart
- Scaling path: Use external job queue (Celery, RQ, or Redis-based scheduler)

## Dependencies at Risk

**1. aiogram 3.4.1:**
- Risk: Breaking changes in v4.x (currently in development)
- Impact: Major refactor required for upgrade
- Migration plan: Monitor aiogram changelog, plan migration before v3 EOL

**2. SQLAlchemy 2.0.28:**
- Risk: None currently (stable version)
- Impact: N/A
- Migration plan: N/A

**3. python-dotenv:**
- Risk: None (mature library)
- Impact: N/A
- Migration plan: N/A

## Missing Critical Features

**1. No Backup/Restore:**
- Problem: Database file can be corrupted or lost
- Blocks: Disaster recovery
- Fix approach: Add backup command and scheduled backups

**2. No Analytics/Reporting:**
- Problem: Limited visibility into bot usage
- Blocks: Data-driven decisions
- Fix approach: Add analytics dashboard or export functionality

**3. No Multi-Language Support:**
- Problem: All messages in Spanish only
- Blocks: International expansion
- Fix approach: Add i18n framework (e.g., `gettext` or `aiogram-i18n`)

## Test Coverage Gaps

**1. Service Layer:**
- What's not tested: All service methods
- Files: `services/*.py`
- Risk: Business logic bugs undetected until production
- Priority: HIGH

**2. Database Migrations:**
- What's not tested: Schema changes
- Files: `models/models.py`
- Risk: Migration failures corrupt data
- Priority: HIGH

**3. Edge Cases:**
- What's not tested: Token expiry, concurrent requests, timezone boundaries
- Files: `services/vip_service.py`, `services/scheduler_service.py`
- Risk: Bugs in critical flows (VIP access, subscription expiry)
- Priority: HIGH

**4. Handler Integration:**
- What's not tested: End-to-end message flows
- Files: `handlers/*.py`
- Risk: Regression in user-facing features
- Priority: MEDIUM

---

*Concerns audit: 2026-03-29*
