---
phase: quick
plan: vip-admin-subscriber-list-sort-reduce
type: auto
item: VIP admin subscriber list sort + reduce time
source: impact-analyzer + user-request
mode: standard
strict_tdd: true
---

# PLAN: VIP admin subscriber list sort + reduce time

**Item:** vip-admin-subscriber-list-sort-reduce  
**Pool:** 1/1 (standalone quick)  
**Effort:** 4  
**Type:** auto (feature, channels-VIP surface)  
**Date:** 2026-07-28  
**Impact:** `.grok/agent-memory/impact-analyzer/vip-admin-subscriber-list-sort-reduce.md`

---

## Objective

Custodios need two admin improvements on the VIP subscriber list:

1. **List order:** most recently subscribed at the top (`Subscription.created_at.desc()`, tiebreak `id.desc()`).
2. **Reduce time:** from a subscriber profile, shorten remaining VIP by N days **or** set an earlier expiry date — **without** expelling, banning, or deactivating the subscription.

Outcome (observable): admin list shows newest first; reduce only moves `end_date` earlier while `is_active=True` and `end_date > now`; scheduler never kicks as a side-effect of a successful reduce.

---

## Scope

### In
- Change `VIPService.get_subscriber_list_page` order_by to `created_at.desc(), id.desc()`.
- New `VIPService.admin_reduce_subscription_time(...)` — mutates **only** `end_date` (earlier), keeps `is_active=True`.
- Admin UI: profile button «Reducir tiempo» + FSM (mode → free text → confirm).
- Pure parse helpers for days / date (`%d/%m/%Y`).
- Lucien voice strings for reduce prompts / confirm / success / errors.
- Callback action `"reduce"` (+ mode selection callbacks).
- Unit + handler + callback pack tests; gold/smoke re-runs.

### Out / Non-goals
- **NO** call or copy of `admin_revoke_subscription` / ban / kick / `is_active=False`.
- **NO** EventBus emit (not extend/grant; no `EVENT_VIP_ACTIVATED`).
- **NO** model / migration changes (`created_at` already exists on `Subscription`).
- **NO** change to `search_active_subscribers` order (still `end_date.asc` — out of scope).
- **NO** change to grant/redeem/token/expire/scheduler expire job semantics.
- **NO** touch gamification, narrative, besitos credit/debit logic, store, missions.
- **NO** user-facing (non-admin) UI.
- **NO** docs/ROADMAP (documentador later if pool closes).

### Constraints (NON-NEGOTIABLE)
1. channels-VIP critical surface: reduce must leave `end_date > now` after success; reject `would_expire` with **zero** DB mutation.
2. Handlers: exactly **1** `with get_service(VIPService)` call on confirm; start/mode/input handlers may do at most 1 snapshot read (mirror besitos debit).
3. Funcs ≤50 LOC; naming verb+contexto+resultado; logging `f"{module} | acción | user_id=... | resultado=..."`.
4. `is_admin` on every admin callback/message (lambda + `_deny_non_admin_*`).
5. Pure helpers for parse (docstring: `"Función pura (sin estado ni side-effects)."`).
6. Strict TDD: write failing tests first per task, then implement.

---

## Assumptions

| ID | Assumption | Rationale |
|----|------------|-----------|
| A1 | Sort key is **first subscribe time** = `Subscription.created_at` (not updated on extend). | Impact + model; extend only mutates `end_date`. |
| A2 | Reduce by days: `new_end = current_end - timedelta(days=N)`; require `N >= 1` integer. | Symmetric inverse of extend-by-days mental model. |
| A3 | Reduce by date: free text `DD/MM/YYYY` end-of-day UTC (`23:59:59` UTC) or date-only midnight UTC — **use date at 23:59:59 UTC** so "same calendar day" is usable. | Reversible product choice; document in code comment. |
| A4 | Result codes: `"ok"`, `"not_found"`, `"inactive"`, `"invalid_args"`, `"would_expire"`, `"not_earlier"`. | Stable for handler mapping + tests. |
| A5 | Mode keyboard reuses `SubscriberActionCallback` with `action="reduce_days"` / `action="reduce_date"` (no new CallbackData class required). Confirm uses `SubscriberConfirmCallback(action="reduce")`. | Minimal surface; pack tests still cover `"reduce"`. |
| A6 | Successful reduce does **not** notify the visitor (admin-only feedback). Kick still has user notify — leave that alone. | Non-expel product intent. |
| A7 | Pagination tests only assert counts today; add explicit order test; update only if order asserts appear. | Impact medium risk. |

---

## Architecture Approach (QUÉ + CÓMO)

### QUÉ — truths after implementation
1. `get_subscriber_list_page` returns active subs ordered newest `created_at` first (`id` desc tiebreak).
2. `admin_reduce_subscription_time(days=N)` shortens `end_date` by N days, keeps `is_active=True`, never bans.
3. `admin_reduce_subscription_time(new_end_date=D)` sets earlier `end_date` when `now < D < current_end`.
4. Any reduce that would yield `end_date <= now` returns `(False, "would_expire", {})` with **no** commit.
5. Exactly one of `days` / `new_end_date`; both or neither → `"invalid_args"`.
6. Confirm handler calls VIPService once via `get_service`; no BesitoService, no ban API.
7. Golds: VIP lifecycle, revoke, grant_internal, cross_service_atomicity / reaction_ / daily_gift / invariants stay green.

### CÓMO — placement
```
handlers/vip_subscriber_admin_handlers.py  →  FSM + 1 get_service(VIPService) on confirm
services/vip_service.py                    →  sort + admin_reduce_subscription_time
keyboards/* + utils/lucien_voice.py        →  UI surface only
models/                                    →  NO TOUCH
```

### Pattern to copy (al pie)

| Pattern | Path | Adapt |
|---------|------|-------|
| end_date-only mutate (extend) | `VIPService.grant_internal_vip_access_for_subscription` (`services/vip_service.py` ~673–729) | Same load-by-id + `_ensure_aware` + commit; **subtract/set earlier** instead of add days; **omit** EventBus `schedule_emit` / `EVENT_VIP_ACTIVATED`; **omit** tariff swap |
| What NOT to do (kick) | `VIPService.admin_revoke_subscription` (~916–989) | Never ban, never `is_active=False`, never `vip_expired()` DM |
| FSM free-text + confirm | debit besitos in `handlers/vip_subscriber_admin_handlers.py` (~600–716) | mode step extra; confirm calls reduce instead of BesitoService |
| Pure helpers | same file: `parse` style + `"Función pura..."` docstring | `parse_reduce_days_input`, `parse_reduce_end_date_input` |
| Profile keyboard button | `subscriber_profile_keyboard` | Add reduce **above** Expulsar |
| Logging | existing vip_subscriber_admin / vip_service | `vip_service \| admin_reduce_subscription_time \| user_id={admin} \| subscription_id=... \| resultado=...` |

### Service contract (exact)

```python
def admin_reduce_subscription_time(
    self,
    subscription_id: int,
    admin_id: int,
    *,
    days: int | None = None,
    new_end_date: datetime | None = None,
) -> tuple[bool, str, dict]:
    """
    Shortens VIP end_date only. Never ban/revoke/is_active=False. No EventBus.
    Returns (ok, result_code, meta).
    """
```

**Algorithm (executor must follow):**
1. Validate XOR: exactly one of `days is not None` / `new_end_date is not None`; if `days` then `days >= 1` int; else fail `"invalid_args"`.
2. Load subscription by id; missing → `"not_found"`.
3. If not `is_active` or end_date missing/≤now → `"inactive"`.
4. `current = _ensure_aware(subscription.end_date)`; `now = datetime.now(UTC)`.
5. If days: `candidate = current - timedelta(days=days)`; if date: `candidate = _ensure_aware(new_end_date)` (normalize to UTC).
6. If `candidate <= now` → `"would_expire"` (no mutate).
7. If `candidate >= current` → `"not_earlier"` (no mutate).
8. `subscription.end_date = candidate`; **do not** touch `is_active`, ban, user vip_entry_*, tariff_id; `db.commit()`; refresh.
9. Log success; return `(True, "ok", {"subscription_id", "old_end_date", "new_end_date", "user_id"})`.
10. **Forbidden:** `bot.ban_chat_member`, `is_active=False`, `schedule_emit`, any EventBus, BesitoService.

### Sort change (exact)

In `get_subscriber_list_page`:
```python
.order_by(Subscription.created_at.desc(), Subscription.id.desc())
```
Update docstring from "end_date ASC" → "created_at DESC, id DESC".

### FSM (exact)

```python
class SubscriberAdminStates(StatesGroup):
    # existing...
    reduce_choosing_mode = State()
    reduce_waiting_input = State()
    reduce_confirming = State()
```

**Flow:**
1. `SubscriberActionCallback(action="reduce")` → snapshot via 1 VIPService; `_save_profile_context`; prompt mode keyboard; state `reduce_choosing_mode`.
2. Mode: `action="reduce_days"` | `action="reduce_date"` → store `reduce_mode` in FSM; prompt text (days or date); state `reduce_waiting_input`.
3. Message handler: pure parse; on fail re-prompt; on ok store `reduce_days` or `reduce_new_end_iso`; show confirm keyboard `action="reduce"`; state `reduce_confirming`.
4. Confirm: validate FSM sub id; **exactly 1** `with get_service(VIPService) as svc: ok, code, meta = svc.admin_reduce_subscription_time(...)`; clear state; success/fail voice + profile keyboard.

### Pure helpers (handlers module)

```python
def parse_reduce_days_input(text: str) -> int | None:
    """Parse positive integer days for VIP reduce. Función pura (sin estado ni side-effects)."""

def parse_reduce_end_date_input(text: str) -> datetime | None:
    """Parse DD/MM/YYYY → aware UTC end-of-day. Función pura (sin estado ni side-effects)."""
```

Date format strict: `datetime.strptime(stripped, "%d/%m/%Y").replace(hour=23, minute=59, second=59, tzinfo=UTC)`.

### File map

| Action | File |
|--------|------|
| Edit | `services/vip_service.py` |
| Edit | `handlers/vip_subscriber_admin_handlers.py` |
| Edit | `keyboards/callback_data.py` (comment on allowed actions) |
| Edit | `keyboards/inline_keyboards.py` |
| Edit | `utils/lucien_voice.py` |
| Edit | `tests/unit/test_vip_service.py` |
| Edit | `tests/handlers/test_vip_subscriber_admin_handlers.py` |
| Edit | `tests/integration/test_callbackdata_vip.py` |
| **No touch** | `models/*`, `admin_revoke_subscription` body, grant/redeem paths, scheduler expire, EventBus observers, besito services, narrative |

### UI surface

**Keyboard** (`subscriber_profile_keyboard`): insert button before Expulsar:
```python
InlineKeyboardButton(
    text="⏱ Reducir tiempo",
    callback_data=SubscriberActionCallback(action="reduce", **ctx).pack(),
)
```

Mode keyboard (new helper `subscriber_reduce_mode_keyboard(sub_id, channel_id, page)`):
- «Por días» → `action="reduce_days"`
- «Por fecha» → `action="reduce_date"`
- Cancel → profile callback

**Voice** (add static methods on `LucienVoice`, third person, elegant):
- `admin_subscriber_reduce_mode_prompt(display, user_id)`
- `admin_subscriber_reduce_days_prompt(display)`
- `admin_subscriber_reduce_date_prompt(display)`  # mention DD/MM/YYYY
- `admin_subscriber_reduce_confirm(display, summary: str)`  # summary e.g. "-5 días" or "vence 01/08/2026"
- `admin_subscriber_reduce_success(display, new_expiry: str)`
- Reuse `admin_subscriber_action_failed(reason)` for errors (map codes to short Spanish reasons).

**callback_data.py** comment update:
```python
action: str  # "extend" | "grant_besitos" | "debit_besitos" | "reduce" | "reduce_days" | "reduce_date" | "kick"
```
And confirm: include `"reduce"`.

---

## Context (@refs)

**Mandatory reads before any edit:**
- `@.grok/agent-memory/impact-analyzer/vip-admin-subscriber-list-sort-reduce.md`
- `@CLAUDE.md` — 1 svc/handler, ≤50 LOC, logging, 3 crit
- `@architecture.md` + `@rules.md`
- `@handlers/CLAUDE.md` + `@services/vip/CLAUDE.md`
- Patterns: `grant_internal_vip_access_for_subscription`, `admin_revoke_subscription` (anti-pattern), debit FSM in `vip_subscriber_admin_handlers.py`
- Existing tests: `TestSubscriberAdminVIPService`, `tests/handlers/test_vip_subscriber_admin_handlers.py`

**GSD log file for executor:** `.planning/quick/gsd-vip-admin-subscriber-list-sort-reduce.log`  
(append timestamped lines before every edit/gate/test)

---

## Tasks

### Task 1: Service — list sort + `admin_reduce_subscription_time` (Strict TDD)

**type:** tdd  
**Objective:** Newest-first list; reduce only mutates `end_date` earlier with hard reject on would-expire; never ban/deactivate/EventBus.  
**Files:**
- `tests/unit/test_vip_service.py` (add under `TestSubscriberAdminVIPService`)
- `services/vip_service.py`

**Actions:**
1. **RED** — add tests (names exact):
   - `test_get_subscriber_list_page_orders_by_created_at_desc`
     - Create ≥3 active subs with distinct `created_at` (set explicitly after insert if server_default collides; use `db_session` commit + update `created_at` if needed). Assert page0 ids order newest→oldest; tiebreak via id when needed.
   - `test_admin_reduce_subscription_time_by_days_keeps_active`
     - end_date moves earlier by N days; `is_active is True`; no ban mock needed.
   - `test_admin_reduce_subscription_time_by_new_end_date`
     - sets earlier date; active remains True.
   - `test_admin_reduce_subscription_time_rejects_would_expire`
     - days large enough that candidate ≤ now → `(False, "would_expire", _)`; end_date unchanged.
   - `test_admin_reduce_subscription_time_rejects_not_earlier`
     - new_end ≥ current → `"not_earlier"`; no mutate.
   - `test_admin_reduce_subscription_time_rejects_invalid_args`
     - both None / both set / days=0 / days=-1.
   - `test_admin_reduce_subscription_time_never_sets_inactive`
     - after successful reduce, `is_active is True` and query still appears in `get_subscriber_list_page` / snapshot not None.
2. **GREEN** — implement sort + method per Architecture Approach; use `_ensure_aware`; log with `admin_id` as `user_id` field.
3. Update `get_subscriber_list_page` docstring.
4. Keep method ≤50 LOC (split private pure calc if needed, e.g. `_compute_reduced_end_candidate` as module-level pure or private method).

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/unit/test_vip_service.py::TestSubscriberAdminVIPService
```

**Commit:** `test(vip): add sort+reduce unit coverage` then `feat(vip): sort subscribers by created_at; reduce end_date only`  
(or single work-unit if executor prefers one commit after green — prefer **one atomic commit** for Task 1 after green: `feat(vip): newest-first list + admin reduce time service`)

---

### Task 2: UI surface + pure parse helpers

**type:** tdd  
**Objective:** Button/callback/voice/mode keyboard + pure parsers ready for handlers; no production FSM yet beyond helpers.  
**Files:**
- `handlers/vip_subscriber_admin_handlers.py` (pure helpers only this task if preferred — or with Task 3)
- `keyboards/callback_data.py`
- `keyboards/inline_keyboards.py`
- `utils/lucien_voice.py`
- `tests/handlers/test_vip_subscriber_admin_handlers.py` (TestPureHelpers)
- `tests/integration/test_callbackdata_vip.py`

**Actions:**
1. **RED** pure helper tests:
   - `parse_reduce_days_input("5") == 5`; `"0"/"" /"abc"/negative → None`
   - `parse_reduce_end_date_input("01/08/2026")` returns aware UTC 23:59:59; bad format → None
2. **RED** callback pack: `SubscriberActionCallback(action="reduce", ...)` pack contains `reduce`.
3. **GREEN** implement helpers, keyboard button + `subscriber_reduce_mode_keyboard`, voice methods, comment updates.
4. Keep helpers pure; no DB.

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/handlers/test_vip_subscriber_admin_handlers.py::TestPureHelpers \
  tests/integration/test_callbackdata_vip.py
```

**Commit:** `feat(vip): reduce-time UI surface and parse helpers`

---

### Task 3: Handler FSM reduce flow + handler tests + golds

**type:** tdd  
**Objective:** Full admin reduce FSM wired; confirm = exactly 1 VIPService call; kick path untouched.  
**Files:**
- `handlers/vip_subscriber_admin_handlers.py`
- `tests/handlers/test_vip_subscriber_admin_handlers.py`

**Actions:**
1. Add FSM states (3) to `SubscriberAdminStates`.
2. Handlers (mirror debit structure; all ≤50 LOC; extract pure text builders if needed):
   - `start_subscriber_reduce` — filter `F.action == "reduce"`
   - `choose_subscriber_reduce_mode` — filter `F.action.in_({"reduce_days", "reduce_date"})` or two handlers
   - `process_reduce_input` — message on `reduce_waiting_input`
   - `confirm_subscriber_reduce` — `SubscriberConfirmCallback.filter(F.action == "reduce")` + state `reduce_confirming`
3. Confirm body (critical):
   ```python
   with get_service(VIPService) as svc:
       ok, code, meta = svc.admin_reduce_subscription_time(
           callback_data.subscription_id,
           admin_id,
           days=data.get("reduce_days"),
           new_end_date=parsed_dt_or_none,
       )
   ```
   Map codes to voice; never call revoke.
4. **RED→GREEN** handler tests with `_mock_vip_ctx`:
   - start reduce calls snapshot once
   - confirm calls `admin_reduce_subscription_time` **once** with expected kwargs
   - confirm does **not** call `admin_revoke_subscription`
   - FSM mismatch clears / rejects (reuse pattern)
5. Run targeted + golds.

**Verification (targeted):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/unit/test_vip_service.py::TestSubscriberAdminVIPService \
  tests/handlers/test_vip_subscriber_admin_handlers.py \
  tests/integration/test_callbackdata_vip.py
```

**Golds / smoke (mandatory, 0 attributable regressions):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "vip or TestVIPSubscriptionLifecycle or admin_revoke or grant_internal_vip_access_for_subscription"

python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "cross_service_atomicity or reaction_ or daily_gift or invariants"
```

**Self-check (executor, after all green):**
- [ ] `rg -n "admin_reduce_subscription_time" services/vip_service.py handlers/`
- [ ] `rg -n "admin_revoke_subscription" handlers/vip_subscriber_admin_handlers.py` — only kick confirm path
- [ ] `rg -n "schedule_emit|EVENT_VIP" services/vip_service.py` — no new emit in reduce method
- [ ] `rg -n "with get_service\\(VIPService\\)" handlers/vip_subscriber_admin_handlers.py` — confirm reduce has exactly 1 call site
- [ ] LOC: `python -c "import inspect; from handlers import vip_subscriber_admin_handlers as m; ..."` all new funcs ≤50
- [ ] Logging present on reduce success/fail
- [ ] Self-check **PASSED**

**Commit:** `feat(vip): admin FSM to reduce subscription time without kick`

---

## Success Criteria

| # | Criterion | How verified |
|---|-----------|--------------|
| 1 | List orders by `created_at` desc | unit test + manual admin list |
| 2 | Reduce by days keeps VIP active | unit test |
| 3 | Reduce by date works | unit test |
| 4 | would_expire rejected, no mutate | unit test |
| 5 | Reduce never bans / never `is_active=False` | unit + handler assert no revoke |
| 6 | Confirm = 1 get_service(VIPService) | handler test mock call count |
| 7 | Golds green | exact pytest cmds above |
| 8 | 0 EventBus on reduce | code review / rg |
| 9 | Funcs ≤50, logging, is_admin | self-check |

---

## Risks + Mitigations

| Level | Risk | Mitigation in tasks |
|-------|------|---------------------|
| Critical | reduce to end_date ≤ now → scheduler ban | Task 1 reject `would_expire` before commit; tests |
| Critical | accidental reuse of revoke | Separate method; handler never imports ban; Task 3 assert no revoke call |
| Medium | `created_at` vs last-extend confusion | Document A1; sort only `created_at` |
| Medium | pagination order assumptions | Explicit order test; keep count tests |
| Low | search still end_date.asc | Non-goal; do not change |
| Medium | date timezone naive SQLite | Always `_ensure_aware`; store aware UTC |
| Low | LOC >50 on confirm | Pure helpers + map error text helper |

---

## Instrucciones para gsd-executor

1. **Strict TDD MODE IS ACTIVE.** Test runner: `python -m pytest`. For each task: write/adjust tests → run RED → implement → GREEN → commit work-unit.
2. **GSD pre-log** before every edit/gate/test — append to `.planning/quick/gsd-vip-admin-subscriber-list-sort-reduce.log`:
   `$(date -u +%Y-%m-%dT%H:%M:%S+00:00) | PHASE N | GSD pre-T# - <desc>; DoD: ...; copy: ...`
3. **Copy patterns al pie** from Architecture Approach table. Do not invent a second reduce path.
4. **Layer rules:** handlers only route; services own business rules; models untouched; no SQL outside models/services existing patterns.
5. **Protect 3 crit:** gamification untouched; narrative untouched; channels-VIP: only list order + end_date shorten; grant/revoke/expire/ban contracts unchanged.
6. **EventBus:** reduce must **not** emit. Extend still may emit (no change to grant_internal).
7. **get_service:** confirm reduce uses `with get_service(VIPService) as svc:` exactly once.
8. **Commits:** atomic per task (conventional commits, no AI co-author trailer).
9. **Do not** expand scope to search sort, bulk reduce, user notification, or ROADMAP.
10. After Task 3 greens + self-check PASSED → write brief SUMMARY stub at  
    `.planning/quick/20260728-vip-admin-subscriber-list-sort-reduce/SUMMARY.md`  
    (executor may leave for later if orchestrator prefers; preferred: short bullets + test cmds run).
11. Ready for **arch-enforcer** then **test-guardian** after self-check.

### Test command flags (always)
```
-q --tb=line -p no:cov --override-ini="addopts="
```

### Mock policy
- Handler tests: mock `get_service` context + autospec VIPService (existing `_mock_vip_ctx`).
- Unit service tests: real `db_session` fixtures; **no** mock of ban for reduce (ban must not be invoked — method has no bot param).
- Do not mock business logic under test inside VIPService unit tests.

---

## Definition of Done

- [ ] All 3 tasks committed
- [ ] Targeted pytest green
- [ ] Gold/smoke pytest green
- [ ] Self-check PASSED
- [ ] PLAN truths 1–7 hold
- [ ] ready for arch-enforcer: yes

---

## Handoff

**ready_for_executor: yes**  
**task_count: 3**  
**plan_path:** `.planning/quick/20260728-vip-admin-subscriber-list-sort-reduce/PLAN.md`
