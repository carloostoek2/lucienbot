# PLAN: Broadcast Link Buttons Catalog (ITEM 1 of 3)

**Item:** broadcast-link-buttons-item1  
**Pool:** broadcast-default-reactions-and-extra-link-buttons  
**Effort:** 5  
**Type:** auto (hardener tight scope)  
**Date:** 2026-06-23  

---

## Objective

Implement the **foundation** (catalog only) for reusable Telegram link buttons that can be attached to broadcasts.

**In scope (ITEM 1 only):**
- `BroadcastButton` model (id, label, url, is_active, created_at, optional description)
- Alembic migration: create `broadcast_buttons` table + add nullable `extra_button_id` FK to `broadcast_messages` in the **same** migration
- `BroadcastService` CRUD methods for buttons (following ReactionEmoji pattern exactly)
- Unit tests: new `TestBroadcastButton` class in `tests/unit/test_broadcast_service.py`
- Export `BroadcastButton` in `models/__init__.py`
- Verify alembic heads post-migration
- Run full gold test suite (no attributable regressions)

**Out of scope (locked):**
- NO handlers changes (broadcast_handlers.py, gamification_admin_handlers.py, etc.)
- NO wizard UI, NO selection flow, NO preview, NO attach on send
- NO changes to `build_send_reaction_markup` or markup building
- NO default reactions flip (that's ITEM 3)
- NO behavior/0 atomicity impact on gamification critical paths (reactions, besitos, daily, missions)

**Decision (FK):** Add `extra_button_id` nullable FK to `BroadcastMessage` **now** in ITEM 1 migration. This avoids a second migration in ITEM 2. Column is nullable; no bidirectional relationship added (minimal change).

---

## Context (@refs)

**Mandatory reads (do before any edit):**
- `@.grok/agent-memory/impact-analyzer/broadcast-link-buttons-item1.md` (source of truth for scope, tests, decisions)
- `@CLAUDE.md` (root) — hardener workflow, 6-agent sequence, pool phrase, 3 critical systems
- `@architecture.md` — layers (handlers → services → models)
- `@rules.md` — ≤50 LOC, verb+context+result, logging, 1 service per handler
- `@services/broadcast/CLAUDE.md` — BroadcastService owns emojis + reactions; pattern for catalog additions
- `@models/CLAUDE.md` — Alembic migration rules (no enum-in-table, IF NOT EXISTS, downgrade, heads)
- `@handlers/CLAUDE.md` — 1-service pattern via `get_service`, no DB, no logic
- `@services/CLAUDE.md` — get_service contract, cross-cutting notes

**Key code to copy verbatim (pattern):**
- `services/broadcast_service.py` lines ~42-101: `create_reaction_emoji`, `get_reaction_emoji`, `get_all_emojis`, `update_emoji_value`, `toggle_emoji`, `delete_emoji`
- `models/models.py`: `ReactionEmoji` class (~257-270) as structural template for `BroadcastButton`
- `tests/unit/test_broadcast_service.py`: `TestBroadcastEmoji` class (~12-69) as style template for `TestBroadcastButton`

**Gold tests that must stay green (no attributable regressions):**
- `tests/integration/test_cross_service_atomicity.py` (cross_service_atomicity, TestCrossServiceAtomicity)
- `tests/integration/test_reaction_full_chain.py`
- `tests/integration/test_invariants.py` (-k "reaction")
- `tests/integration/test_reaction_mission_flow.py`
- `tests/integration/test_reaction_limit.py`
- `tests/unit/test_broadcast_service.py`
- `tests/unit/test_broadcast_service_reaction_flow.py`
- `tests/integration/test_alembic_heads.py`
- `tests/integration/test_callbackdata_broadcast.py`
- `tests/handlers/test_gamification_user_handlers.py` (-k "reaction or Reaction")

**Pre-flight commands (run before touching code):**
See "Test Commands" section below.

---

## Constraints (NON-NEGOTIABLE)

1. **0 impact on 3 critical systems:** Gamification (besitos + REACTIONS + daily), Narrative (progress/archetypes/quiz), Channels/VIP (pending/approve/expire/bans/subs + grant/revoke). ITEM 1 touches only catalog; `check_and_register_reaction`, credit paths, EventBus observers, and atomic contracts are untouched.
2. **Scope locked to ITEM 1:** Model + migration + service CRUD + unit tests + exports + heads verification. NOTHING else.
3. **BroadcastService owns the domain:** NO new service. All button logic lives in `BroadcastService`.
4. **Copy ReactionEmoji pattern at the letter:** Same method signatures style, logging, return types, active_only filter, toggle semantics.
5. **Function limit:** Every new method ≤50 LOC (ReactionEmoji already complies; keep new ones short).
6. **Naming:** `verb + context + result` (e.g., `create_broadcast_button`, `get_all_buttons`).
7. **Logging:** `"broadcast_service | create_broadcast_button | label=... | url=... | id=..."`
8. **get_service compatible:** Methods must work via `with get_service(BroadcastService) as svc:` (no special init changes).
9. **Alembic rules (from models/CLAUDE.md):** Descriptive revision id, down_revision = current head, IF NOT EXISTS where appropriate, downgrade implemented, test `alembic upgrade head` + `downgrade -1` on SQLite.
10. **Migration decision (FK):** `extra_button_id` nullable FK added in SAME migration as table creation. No bidirectional `relationship()` on `BroadcastMessage` unless minimal necessity (not needed for ITEM 1).
11. **Validation:** URL validation is LOOSE for ITEM 1 (document as "Telegram link" business requirement, not hard enforcement). Do not block creation on strict `https://t.me/` or `tg://` checks.
12. **No handler edits:** Confirmed by impact and scope lock.

---

## Tasks

### Task 1: Add `BroadcastButton` model + FK column to `BroadcastMessage`

**Objective:** Define the catalog entity and the attachment point on messages.

**Files:**
- `models/models.py`
- `models/__init__.py`

**Actions (exact):**
1. Add `BroadcastButton` class after `ReactionEmoji` (around line 271) or in logical grouping with other broadcast models. Copy structure from `ReactionEmoji`:
   - `__tablename__ = "broadcast_buttons"`
   - `id = Column(Integer, primary_key=True, index=True)`
   - `label = Column(String(100), nullable=False)` — button text
   - `url = Column(String(500), nullable=False)` — Telegram link
   - `description = Column(Text, nullable=True)` — admin note (optional)
   - `is_active = Column(Boolean, default=True)`
   - `created_at = Column(DateTime(timezone=True), server_default=func.now())`
2. Add to `BroadcastMessage` (minimal):
   - `extra_button_id = Column(Integer, ForeignKey("broadcast_buttons.id"), nullable=True)`
   - No `relationship()` back to button (keep minimal; navigation can be added later if needed).
3. Export in `models/__init__.py`:
   - Import: `BroadcastButton,`
   - `__all__`: `"BroadcastButton",`

**Verification (after edit):**
```bash
python -c "
from models.models import BroadcastButton, BroadcastMessage
print('BroadcastButton columns:', [c.name for c in BroadcastButton.__table__.columns])
print('BroadcastMessage has extra_button_id:', hasattr(BroadcastMessage, 'extra_button_id') or 'extra_button_id' in [c.name for c in BroadcastMessage.__table__.columns])
print('Import OK')
"
```

**GSD pre-log:** Before editing, append to `.planning/quick/gsd-planner-broadcast-link-buttons-item1.log`:
```
[$(date)] GSD_PRE TASK1 model_edit file=models/models.py action=add_BroadcastButton_and_FK
```

---

### Task 2: Create Alembic migration (table + FK column in same mig)

**Objective:** Persist the new schema with a single migration.

**Files:**
- `alembic/versions/20260623_add_broadcast_buttons.py` (NEW)

**Migration content (follow recent style, e.g. 20260617, 20260613):**
- `revision = "20260623_add_broadcast_buttons"`
- `down_revision = "20260622_fix_fulfillment_enums"`
- `upgrade()`:
  - `op.create_table("broadcast_buttons", ...)` with all columns + PK + indexes + (optional) unique on label if business wants; keep simple.
  - `op.add_column("broadcast_messages", sa.Column("extra_button_id", sa.Integer(), nullable=True))`
  - `batch_op.create_foreign_key("fk_broadcast_messages_extra_button", "broadcast_buttons", ["extra_button_id"], ["id"])`
- `downgrade()`:
  - Drop FK, drop column, drop table (reverse order).

**Verification (run immediately after creation):**
```bash
# 1. Heads check (must be 1 head after)
pytest tests/integration/test_alembic_heads.py -v --tb=line -q

# 2. Upgrade/downgrade cycle on dev SQLite (lucien_dev.db or in-memory)
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

**GSD pre-log:** Before writing the migration file:
```
[$(date)] GSD_PRE TASK2 migration_create file=alembic/versions/20260623_add_broadcast_buttons.py
```

**Note on current head:** As of planning, head is `20260622_fix_fulfillment_enums`. Confirm before writing migration.

---

### Task 3: Extend `BroadcastService` with button CRUD (copy ReactionEmoji exactly)

**Objective:** Add 6 methods following the established pattern.

**File:**
- `services/broadcast_service.py`

**Placement:** New section after emojis, before or clearly separated from messages:
```python
# ==================== BOTONES DE ENLACE EXTRA ====================
```

**Methods (signatures + behavior to match ReactionEmoji semantics):**
1. `create_broadcast_button(self, label: str, url: str, description: str = None) -> BroadcastButton`
   - Creates with `is_active=True`
   - Log: `logger.info(f"broadcast_service | create_broadcast_button | label={label} | url={url} | id={button.id}")`
2. `get_broadcast_button(self, button_id: int) -> BroadcastButton | None`
3. `get_all_buttons(self, active_only: bool = True) -> list[BroadcastButton]`
4. `toggle_broadcast_button(self, button_id: int) -> bool`
5. `update_broadcast_button(self, button_id: int, label: str = None, url: str = None, description: str = None) -> bool`
   - Only update provided non-None fields
6. `delete_broadcast_button(self, button_id: int) -> bool`

**Rules to enforce in implementation:**
- ≤50 LOC per method (copy style from emoji methods)
- Use existing `get_broadcast_button` internally where appropriate
- No direct DB outside the service's `self.db`
- Compatible with `get_service(BroadcastService)`

**Import:** Add `BroadcastButton` to the imports from `models.models`.

**Verification (after implementation):**
```bash
# Quick smoke via python
python -c "
from services import get_service, BroadcastService
with get_service(BroadcastService) as svc:
    b = svc.create_broadcast_button('Test', 'https://t.me/test')
    print('created:', b.id, b.label)
    print('get_all active:', len(svc.get_all_buttons(active_only=True)))
    print('toggle:', svc.toggle_broadcast_button(b.id))
    print('delete:', svc.delete_broadcast_button(b.id))
print('CRUD smoke OK')
"
```

**GSD pre-log:** Before ANY edit to broadcast_service.py:
```
[$(date)] GSD_PRE TASK3 service_edit file=services/broadcast_service.py action=add_button_crud
```

---

### Task 4: Add `TestBroadcastButton` unit tests (copy TestBroadcastEmoji style)

**Objective:** Cover the new CRUD with the same rigor as emojis.

**File:**
- `tests/unit/test_broadcast_service.py`

**New class:** `TestBroadcastButton` (place after `TestBroadcastEmoji` or grouped with broadcast tests).

**Required tests (minimum, copy structure):**
- `test_create_broadcast_button` — asserts label, url, is_active=True, returns entity
- `test_get_broadcast_button` — using created or fixture
- `test_get_all_buttons_active_only_filter` — create 2 (one inactive), assert filter behavior
- `test_toggle_broadcast_button` — flips is_active
- `test_update_broadcast_button` — partial updates (label only, url only)
- `test_delete_broadcast_button` — deletes and get returns None

**Style rules:**
- Use `db_session` fixture (not direct SessionLocal)
- `service = BroadcastService(db_session)`
- Assert on returned values + re-fetch where relevant
- No mocking of DB for these CRUD tests (real SQLite in-memory)

**Verification:**
```bash
pytest tests/unit/test_broadcast_service.py::TestBroadcastButton -v --tb=line -q
```

**GSD pre-log:** Before editing the test file:
```
[$(date)] GSD_PRE TASK4 tests_edit file=tests/unit/test_broadcast_service.py action=add_TestBroadcastButton
```

---

### Task 5: Full verification (alembic heads + gold tests)

**Objective:** Prove no breakage to protected contracts.

**Commands (exact, run in order):**

Pre-edit baseline (run before any code change in this item):
```bash
pytest tests/integration/test_alembic_heads.py tests/unit/test_broadcast_service.py tests/unit/test_broadcast_service_reaction_flow.py tests/integration/test_cross_service_atomicity.py tests/integration/test_reaction_full_chain.py tests/integration/test_invariants.py -v --tb=line -q -p no:cov --override-ini="addopts="
```

Post-implementation (after Tasks 1-4 complete):
```bash
# 1. Alembic heads (single head)
pytest tests/integration/test_alembic_heads.py -v --tb=line -q

# 2. Unit broadcast service (includes new TestBroadcastButton)
pytest tests/unit/test_broadcast_service.py -v --tb=line -q

# 3. Reaction flow unit
pytest tests/unit/test_broadcast_service_reaction_flow.py -v --tb=line -q

# 4. Cross-service atomicity (gold)
pytest tests/integration/test_cross_service_atomicity.py -v -k "cross_service_atomicity or TestCrossServiceAtomicity" --tb=line -q -p no:cov --override-ini="addopts="

# 5. Full chain
pytest tests/integration/test_reaction_full_chain.py -v --tb=line -q

# 6. Invariants (reaction)
pytest tests/integration/test_invariants.py -v -k "reaction" --tb=line -q

# 7. Reaction limit
pytest tests/integration/test_reaction_limit.py -v --tb=line -q

# 8. Mission flow
pytest tests/integration/test_reaction_mission_flow.py -v --tb=line -q

# 9. Callback data (markup helper, not modified but in impact list)
pytest tests/integration/test_callbackdata_broadcast.py -v --tb=line -q

# 10. Gamification user handlers (reactions)
pytest tests/handlers/test_gamification_user_handlers.py -v -k "reaction or Reaction" --tb=line -q

# 11. Broadcast handler smoke (if any)
pytest tests/handlers/ -v -k "broadcast" --tb=line -q 2>/dev/null || echo "No broadcast handler tests found or none matching"
```

**Ruff + format (after all edits):**
```bash
ruff check --fix models/models.py services/broadcast_service.py tests/unit/test_broadcast_service.py alembic/versions/20260623_add_broadcast_buttons.py
ruff format models/models.py services/broadcast_service.py tests/unit/test_broadcast_service.py alembic/versions/20260623_add_broadcast_buttons.py
```

**GSD pre-log:** Before running final verification suite:
```
[$(date)] GSD_PRE TASK5 verification_run action=full_gold_suite
```

**Self-check at end of Task 5:** Executor must append to log:
```
[$(date)] SELF_CHECK PASSED item=broadcast-link-buttons-item1 all_golds_green alembic_heads=1 ruff_clean scope_locked_to_item1
```

---

## Instrucciones para gsd-executor (MANDATORY)

1. **Read this PLAN completely** before touching any file. Do not infer scope from memory; re-read impact + CLAUDEs if unsure.

2. **GSD pre-log before EVERY edit/gate:**
   - Append a line to `.planning/quick/gsd-planner-broadcast-link-buttons-item1.log` with timestamp, phase, file, action.
   - Use `wc -l` on the log after each append to confirm growth.
   - No edit without a preceding pre-log entry.

3. **Copy ReactionEmoji pattern at the letter:**
   - Method bodies should be ~8-15 LOC like the emoji equivalents.
   - Use same structure: get helper → mutate → commit → return.
   - Logging format: `"broadcast_service | <action> | key=val | ..."`
   - `active_only=True` default filter.

4. **Function size:** If any method exceeds 50 LOC, refactor into a private helper (pure if possible) or split. Verify with `inspect.getsourcelines` or wc.

5. **Logging:** Include the exact example style for create. Extend to toggle/delete/update with similar granularity.

6. **No handler changes:** If you feel the urge to touch broadcast_handlers.py or admin handlers, STOP. That is ITEM 2. Log the temptation and skip.

7. **Migration rules (models/CLAUDE.md):**
   - Descriptive name.
   - `IF NOT EXISTS` for safety where enum/constraint, but for new table it's create.
   - Downgrade must be correct (drop FK before column before table).
   - Test upgrade/downgrade cycle locally.

8. **get_service:** After adding methods, they are automatically available via context manager. No changes to `services/__init__.py` needed.

9. **Ruff:** Run `ruff check --fix` + `ruff format` on touched files after edits, before tests.

10. **Self-check PASSED:** At the very end (after Task 5), append the self-check line with scope confirmation.

11. **Handoff:** After completion, the final message must be:  
    `"Ready for gsd-executor. Lee PLAN completo antes de editar."` (No: you are the executor. The handoff from planner is this PLAN. Your final output after success should be a concise SUMMARY + path to this PLAN + confirmation all verifications passed.)

---

## Test Commands (exact)

**Baseline (before any change in session):**
```bash
pytest tests/integration/test_alembic_heads.py tests/unit/test_broadcast_service.py tests/unit/test_broadcast_service_reaction_flow.py tests/integration/test_cross_service_atomicity.py tests/integration/test_reaction_full_chain.py tests/integration/test_invariants.py -v --tb=line -q -p no:cov --override-ini="addopts="
```

**Project flags (always use for these gold runs):**
- `-q --tb=line -p no:cov --override-ini="addopts="`

**Per-task verifications:** See each Task section.

**Full post-implementation suite:** See Task 5.

---

## Risks + Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Alembic heads bifurcation | Low | High (blocks deploys) | Run `test_alembic_heads.py` immediately after migration; downgrade/upgrade cycle; single down_revision. |
| FK breaks existing BroadcastMessage fixtures | Low | Medium | Column is nullable; existing inserts omit it → OK. Fixtures in conftest create without extra_button_id. |
| Atomicity gold tests fail due to schema change | Very Low | Critical | ITEM 1 does not touch `check_and_register_reaction`, credit paths, or EventBus. Nullable FK is inert until used. Re-run golds explicitly. |
| Method >50 LOC | Low | Medium | Copy emoji pattern (already <20 LOC each); enforce in review. |
| URL validation over-reach | Low | Low | Explicit: loose validation only. Document in code comment. |
| Accidental handler edit | Medium (temptation) | High (scope creep) | Hard rule in constraints + PLAN; pre-log + self-check will catch. Stop if file not in task list. |
| Missing export in models/__init__.py | Low | Medium | Explicit task; verification import smoke. |

---

## Success Criteria (measurable)

1. `BroadcastButton` model exists with required columns; importable from `models`.
2. `BroadcastMessage` has `extra_button_id` nullable FK (no breaking change to existing rows).
3. Migration file `20260623_add_broadcast_buttons.py` exists; `alembic heads` reports exactly 1 head.
4. `BroadcastService` has exactly the 6 CRUD methods for buttons; each ≤50 LOC; logging follows pattern.
5. `TestBroadcastButton` class exists with ≥6 tests; all pass.
6. All gold tests from impact report pass with `-q --tb=line` and project flags; 0 attributable regressions.
7. `ruff check --fix` + `ruff format` clean on touched files.
8. GSD pre-logs present for every edit (log file line count increased).
9. Self-check PASSED appended with scope confirmation.
10. No files outside the task list were modified (models, service, one test file, one migration, __init__).

---

## Scope Lock Reminder

This PLAN is for **ITEM 1 only**. ITEM 2 will handle wizard integration, markup, preview, and `create_broadcast_message(..., extra_button_id=...)`. ITEM 3 is default reactions. Do not start those here.

---

**End of PLAN.** Executor: read this fully, pre-log every step, copy patterns, protect the 3 critical systems, deliver clean.
