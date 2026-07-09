# 📊 Impact Analysis: Reaction Ecosystem Week 2

**Item:** `reaction-ecosystem-week2` (Week 2 — builds on completed Week 1)  
**Date:** 2026-07-06  
**Agent:** impact-analyzer  
**Mode:** Analysis only — NO code edits

---

## Scope Summary

Week 2 is **test + documentation + debt closure** on top of Week 1 (unified markup, `process_channel_reaction`, slim handler). **Default constraint: 0 behavior change.** Atomicity golds must stay green.

| # | Objective | Current state (post-Week 1) | Week 2 target | Prod code change? |
|---|-----------|----------------------------|---------------|-------------------|
| 1 | **Markup parity test** | Send + refresh tested separately in `test_broadcast_channel_markup.py` (11 tests); no explicit structural diff test | Golden test: send vs refresh produce identical structure (callbacks, row order, extra URL); only button **text** differs (counts) | **Tests only** |
| 2 | **`tracking_failed` test** | `publish_broadcast_to_channel` returns `tracking_failed` when `update_broadcast_message_id` fails; broadcast row stays `message_id=0`; `message_mismatch` validators exist but no test ties the two flows | When broadcast persisted with `message_id=0` (update failed), reaction with real TG `message_id` → `message_mismatch` | **Tests only** |
| 3 | **Update `services/broadcast/CLAUDE.md`** | Stale: documents legacy `register_reaction` as prod path; missing `check_and_register_reaction`, `process_channel_reaction`, validators, `message_id` validation, extra buttons in reaction refresh | Document real paths and contracts | **Docs only** |
| 4 | **Migrate `test_reaction_full_chain.py`** | Still mirrors **pre-Week-1 handler**: `check_and_register_reaction` + manual `reactions_keyboard_with_counts` + `update_reaction_message` | Use `process_channel_reaction` (Week 1 debt) | **Tests only** |
| 5 | **`credit_besitos(commit=False)` spike** | `credit_besitos` always `db.commit()` internally (L141); `debit_besitos` has `commit=False` precedent; reaction path relies on split-tx by design (Item 6 decisions) | Evaluate atomicity; spike **only if risky**; else document defer in `decisions.md` | **Defer recommended** |

---

## Week 1 Baseline (Completed — Do Not Re-Implement)

Week 1 is **closed** per `.grok/agent-memory/documentador/reaction-ecosystem-week1-closed.md` (101+ tests green).

| Deliverable | Location | Status |
|-------------|----------|--------|
| Unified markup | `keyboards/broadcast_channel_markup.py` — `build_channel_reaction_markup`, `build_broadcast_send_markup`, `calculate_emoji_counts_from_reactions` | ✅ Done |
| Validators | `services/broadcast/reaction_validators.py` — 4 pure functions | ✅ Done |
| Service orchestration | `BroadcastService.process_channel_reaction` (register + post-commit refresh) | ✅ Done |
| Slim handler | `handle_reaction` → `1× get_service` + `1× process_channel_reaction` | ✅ Done |
| Unit coverage | `TestProcessChannelReaction` (4 tests), `test_broadcast_channel_markup.py` (11 tests) | ✅ Done |
| Deprecated shim | `reactions_keyboard_with_counts` → thin delegate to unified builder | ✅ Done |

**Production handler (current):**

```python
# handlers/gamification_user_handlers.py:214-223
with get_service(BroadcastService) as broadcast_service:
    result = await broadcast_service.process_channel_reaction(
        broadcast_id=..., user_id=..., emoji_id=...,
        username=..., bot=..., channel_id=..., message_id=...,
    )
```

---

## Objective 1: Markup Parity Test

### As-Is

| Path | Entry | `emoji_counts` | Button text |
|------|-------|----------------|-------------|
| **Send** | `build_broadcast_send_markup` → `build_channel_reaction_markup(..., emoji_counts=None)` | `None` | `emoji` char only |
| **Refresh** | `process_channel_reaction` → `build_channel_reaction_markup(..., emoji_counts={...})` | dict | `emoji` if count=0; `"emoji N"` if N>0 |

Both paths share `build_channel_reaction_markup` (Week 1 unification). Existing tests cover send and refresh **in isolation** (`test_broadcast_channel_markup.py`, duplicated in `test_callbackdata_broadcast.py::TestBroadcastPureHelpers`).

### Gap

No test asserts **structural parity** between send and refresh for the same `(broadcast_id, emoji_entries, extra_button)`:

- Same number of rows
- Same row order (reactions first, extra URL last)
- Same `callback_data` per reaction button (`react:` prefix)
- Same `url` on extra button
- **Only** `text` may differ when refresh counts are all zero (should match send exactly)

### Proposed Test (executor)

Add to `tests/unit/test_broadcast_channel_markup.py` (or dedicated `test_markup_send_refresh_parity`):

```python
def _markup_structure(markup):
    """Normalize markup to comparable structure (exclude count text)."""
    return [
        [
            {
                "callback_data": btn.callback_data,
                "url": getattr(btn, "url", None),
            }
            for btn in row
        ]
        for row in markup.inline_keyboard
    ]

# Cases: reactions-only, extra-only, combined, 9-emoji chunking
send = build_channel_reaction_markup(bid, entries, emoji_counts=None, extra_button=extra)
refresh_zero = build_channel_reaction_markup(bid, entries, emoji_counts={eid: 0 for eid, _ in entries}, extra_button=extra)
assert _markup_structure(send) == _markup_structure(refresh_zero)
# Per-button text parity when counts all zero
# refresh with count>0: structure same, text differs only on reaction buttons
```

### Risk

| Risk | Level | Mitigation |
|------|-------|------------|
| False positive if test compares `text` | LOW | Compare structure separately from text |
| Duplicate coverage with existing 11 tests | LOW | Parity test is the **regression lock** Week 2 explicitly asks for |

### Files to touch

| File | Change |
|------|--------|
| `tests/unit/test_broadcast_channel_markup.py` | **CREATE** 1–3 parity tests |
| `tests/integration/test_callbackdata_broadcast.py` | Optional: dedupe or import shared helper (out of scope unless drift found) |

**Prod files: 0**

---

## Objective 2: `tracking_failed` → `message_mismatch` Test

### As-Is Flow

```
persist_broadcast_from_state → create_broadcast_message(message_id=0)   # handlers/broadcast_handlers.py:163
    → send_broadcast_to_channel (TG send succeeds)
    → update_broadcast_message_id(broadcast_id, sent_message.message_id)
         └─ if False → return ("tracking_failed", sent_message.message_id)   # L116-121
    → Admin alert: "Las reacciones podrían fallar."   # L1094-1098
```

Broadcast row retains **`message_id=0`** when DB update fails (message was sent to channel; tracking broken).

When user reacts:

```
handle_reaction passes channel_id=callback.message.chat.id, message_id=callback.message.message_id (real TG id)
    → check_and_register_reaction
    → validate_broadcast_context_match(broadcast, channel_id, message_id)
         broadcast.message_id == 0 ≠ real message_id → "message_mismatch"   # reaction_validators.py:26-27
```

### Existing Coverage

| Test | Covers |
|------|--------|
| `test_message_mismatch_message_id_returns_structured_reason` | Wrong `message_id` (888888 vs stored 1001) — **not** `message_id=0` scenario |
| `test_message_mismatch_channel_returns_structured_reason` | Wrong `channel_id` |
| Handler `test_shows_failure_message_per_reason[message_mismatch-...]` | UI mapping only (mocked service) |
| `test_broadcast_handlers` | Mocks `update_broadcast_message_id`; **no** `tracking_failed` path test |

### Gap

No test documents the **production failure mode**: broadcast sent + tracked as `message_id=0` → reaction blocked with `message_mismatch`.

### Proposed Test (executor)

**Unit** (minimal, fast) in `tests/unit/test_broadcast_service_reaction_flow.py`:

```python
async def test_message_mismatch_when_broadcast_stuck_at_message_id_zero(...):
    sample_broadcast_message.message_id = 0  # simulates tracking_failed persistence
    db_session.commit()
    result = await service.check_and_register_reaction(
        ...,
        channel_id=sample_free_channel.channel_id,
        message_id=1001,  # real TG message user clicked
    )
    assert result["reason"] == "message_mismatch"
```

**Optional integration** in `tests/integration/test_reaction_full_chain.py` or new small test: create broadcast with `message_id=0`, call `process_channel_reaction` with mismatched TG ids, assert no reaction row + no credit.

### Risk

| Risk | Level | Mitigation |
|------|-------|------------|
| Accidentally "fix" by accepting `message_id=0` | **HIGH** if prod change | **Tests only** — do not relax validator |
| Confusion with `invalid_broadcast` | LOW | `message_id=0` is valid row; context match is correct guard |

### Files to touch

| File | Change |
|------|--------|
| `tests/unit/test_broadcast_service_reaction_flow.py` | **ADD** `message_id=0` scenario |
| `tests/handlers/test_broadcast_handlers.py` | Optional: `tracking_failed` publish unit test (orthogonal but valuable) |

**Prod files: 0**

---

## Objective 3: Update `services/broadcast/CLAUDE.md`

### Stale Content (must replace)

Current CLAUDE.md (L41-68) describes:

- `register_reaction` as visitor flow (obsolete; **DEPRECATED**)
- No `check_and_register_reaction` return dict contract
- No `process_channel_reaction`
- No `validate_broadcast_context_match` / `message_id` validation
- No `extra_button_id` in reaction refresh path
- No `build_channel_reaction_markup` / send path
- No `update_broadcast_message_id` / `tracking_failed` operational note

### Required Documentation Sections

| Section | Content |
|---------|---------|
| **Production reaction path** | `handle_reaction` → `process_channel_reaction` → `check_and_register_reaction` |
| **Return dict contract** | `success` + `besitos_awarded` / `reason` codes (`duplicate`, `message_mismatch`, `credit_failed`, etc.) |
| **Validators** | `services/broadcast/reaction_validators.py` — pure, read-only |
| **Markup** | `keyboards/broadcast_channel_markup.py` — send (`emoji_counts=None`) vs refresh (counts dict) |
| **Extra URL button** | `extra_button_id` on `BroadcastMessage`; included in send + refresh via `build_channel_reaction_markup` |
| **Message ID validation** | Handler passes `channel_id` + `message_id` from callback; mismatch → `message_mismatch` (incl. `message_id=0` after `tracking_failed`) |
| **Atomicity note** | Reaction INSERT + credit in `check_and_register_reaction`; mission delivery post-commit best-effort; markup refresh post-commit best-effort |
| **Deprecated** | `register_reaction` — legacy sync; do not use in new code |
| **EventBus** | Keep existing Item 6 observer section (still accurate) |

### Risk

| Risk | Level |
|------|-------|
| Doc drift from code | LOW — single source files listed above |
| Accidental behavior change | **NONE** — docs only |

### Files to touch

| File | Change |
|------|--------|
| `services/broadcast/CLAUDE.md` | **EDIT** — rewrite Reacciones + Flujo sections |

---

## Objective 4: Migrate `test_reaction_full_chain.py`

### As-Is (Week 1 debt)

`test_reaction_advances_mission_and_updates_keyboard_counts` (L180-216):

```python
reaction_result = await broadcast_service.check_and_register_reaction(...)
# Manual keyboard rebuild (pre-Week-1 handler logic):
selected_emoji_ids = broadcast_service.get_selected_emoji_ids(...)
reactions = broadcast_service.get_reactions_by_broadcast(...)
emoji_counts = { ... manual loop ... }
emojis_for_keyboard = [ ... ]
new_markup = reactions_keyboard_with_counts(broadcast_db_id, emojis_for_keyboard, emoji_counts)
await broadcast_service.update_reaction_message(...)
```

`test_multiple_reactions_update_counts_correctly` (L303-326): uses `check_and_register_reaction` twice + manual count logic; builds markup but **does not** call `update_reaction_message`.

### Target

Replace primary test execution block with:

```python
reaction_result = await broadcast_service.process_channel_reaction(
    broadcast_id=broadcast_db_id,
    user_id=user_id,
    emoji_id=emoji1_id,
    username="testuser",
    bot=mock_bot,
    channel_id=broadcast_channel_id,
    message_id=broadcast_telegram_id,
)
```

Assertions to preserve:

- Mission progress + balance (2 + 5 = 7)
- `mock_bot.edit_message_reply_markup` called with correct `chat_id` / `message_id`
- Markup contains count `"💋 1"` or equivalent (via call kwargs, not manual rebuild)
- Reaction row + besitos credit unchanged

### Consumer / Dependency Map

| Symbol | File | After migration |
|--------|------|-----------------|
| `reactions_keyboard_with_counts` | `test_reaction_full_chain.py:24,207,326` | **Remove import** if unused |
| `reactions_keyboard_with_counts` | `keyboards/inline_keyboards.py:848` | Keep deprecated shim (other refs none in prod) |
| `check_and_register_reaction` | `test_cross_service_atomicity.py`, `test_reaction_mission_flow.py`, unit golds | **Untouched** — still valid for atomicity-focused tests |
| `process_channel_reaction` | `test_broadcast_service_reaction_flow.py::TestProcessChannelReaction` | Pattern to copy |

### Risk

| Risk | Level | Mitigation |
|------|-------|------------|
| Integration test becomes less explicit about keyboard math | LOW | Assert via `edit_message_reply_markup` kwargs |
| `process_channel_reaction` mocks `bot` requirement | LOW | Test already uses `mock_bot` |
| Mission side-effects ordering | LOW | Same underlying `check_and_register_reaction` |

### Files to touch

| File | Change |
|------|--------|
| `tests/integration/test_reaction_full_chain.py` | **EDIT** — migrate to `process_channel_reaction`; drop manual markup rebuild |

**Prod files: 0**

---

## Objective 5: `credit_besitos(commit=False)` Evaluation

### Current Transaction Model

```
check_and_register_reaction:
  1. db.add(BroadcastReaction); db.flush()
  2. BesitoService(db).credit_besitos(...)  → internal db.commit()  # besito_service.py:141
  3. db.commit()  # reaction row
  4. run_mission_side_effects_isolated(...)  # separate session, best-effort
```

`credit_besitos` signature (no `commit` param):

```python
def credit_besitos(self, user_id, amount, source, description=None, reference_id=None) -> bool:
    ...
    db.commit()  # always
    self._schedule_besitos_awarded_event(...)  # post-commit
```

`debit_besitos` **has** `commit: bool = True` — used by `story_service.advance_to_node`, `store_service`, `streak_promotion_service` for caller-atomic outer commits.

### Why Split-Tx Exists (Intentional)

Documented in `decisions.md` Item 6 + `fases_refactor_testing.md` brecha #5:

- "credit's internal commit as before" preserves gold contracts
- `test_cross_service_atomicity.py`: **"credit survives deliver False"**
- `test_broadcast_service_reaction_flow.py::test_credit_failure_rolls_back`: patches `credit_besitos` return False → reaction row rolled back via outer `db.rollback()` after failed credit
- EventBus `schedule_emit` fires post-credit-commit (besito_service.py + event_bus.py comments)

### Spike Scope (if pursued)

Would require:

1. Add `commit: bool = True` to `credit_besitos` (mirror debit)
2. When `commit=False`: skip `db.commit()` and **defer** `_schedule_besitos_awarded_event` until outer commit
3. Update `check_and_register_reaction` to `credit_besitos(..., commit=False)` + single outer `db.commit()`
4. Re-run **all** credit-path golds: cross atomicity, reaction flow, invariants, daily, game, reward delivery, EventBus listener tests

### Risk Assessment

| Risk | Level | Notes |
|------|-------|-------|
| Atomicity gold breakage | **HIGH** | 10+ integration scenarios in `test_cross_service_atomicity.py` |
| EventBus emit timing change | **HIGH** | Observers expect post-credit-commit; premature emit if outer rolls back |
| Orphan reaction without credit | MEDIUM | Already guarded by `credit_failed` + rollback today |
| Scope creep to all credit callers | **HIGH** | REACTION, DAILY, MISSION, GAME, ADMIN, story achievements |

### Recommendation: **DEFER** (document, do not spike in Week 2)

| Criterion | Assessment |
|-----------|------------|
| Is current path "risky" in production? | **No** — years of gold coverage; UniqueConstraint + credit_failed rollback protect integrity |
| Would `commit=False` improve user-visible behavior? | **No** — 0 behavior change constraint |
| Would golds break? | **Likely** — atomicity tests assume current commit boundaries |

**Action:** Add `decisions.md` entry: "Reaction credit atomicity — defer `credit_besitos(commit=False)`; split-tx intentional per Item 6; revisit only if orphan-row production incident."

**Prod files: 0** (decision doc only)

---

## Consumer Map (Grep — Week 2 Relevant)

### `build_channel_reaction_markup` / `build_broadcast_send_markup`

| File | Usage |
|------|-------|
| `keyboards/broadcast_channel_markup.py` | Definitions |
| `services/broadcast_service.py:563` | Refresh in `process_channel_reaction` |
| `handlers/broadcast_handlers.py:1080` | Send in `confirm_and_send_broadcast` |
| `tests/unit/test_broadcast_channel_markup.py` | 11 unit tests |
| `tests/integration/test_callbackdata_broadcast.py` | Duplicated pure helper tests |

### `process_channel_reaction`

| File | Usage |
|------|-------|
| `services/broadcast_service.py:530` | Definition |
| `handlers/gamification_user_handlers.py:215` | **Production handler** |
| `tests/unit/test_broadcast_service_reaction_flow.py::TestProcessChannelReaction` | 4 unit tests |
| `tests/handlers/test_gamification_user_handlers.py` | Handler mocks `process_channel_reaction` |

### `check_and_register_reaction`

| File | Usage |
|------|-------|
| `services/broadcast_service.py:380` | Definition; called by `process_channel_reaction` |
| `tests/unit/test_broadcast_service_reaction_flow.py` | 14+ unit tests (gold) |
| `tests/integration/test_cross_service_atomicity.py` | Atomicity gold |
| `tests/integration/test_reaction_full_chain.py` | **Debt — manual path** |
| `tests/integration/test_reaction_mission_flow.py` | Mission chain |
| `tests/integration/test_reaction_limit.py` | Limit enforcement |
| `tests/integration/test_invariants.py` | Idempotency |

### `validate_broadcast_context_match`

| File | Usage |
|------|-------|
| `services/broadcast/reaction_validators.py:18` | Pure validator |
| `services/broadcast_service.py:410` | Orchestrator call site |

### `message_id=0` / `tracking_failed`

| File | Usage |
|------|-------|
| `handlers/broadcast_handlers.py:121,163,1094` | Persist 0 + tracking_failed handling |
| `services/broadcast_service.py:225` | `update_broadcast_message_id` |

### `reactions_keyboard_with_counts` (deprecated shim)

| File | Usage |
|------|-------|
| `keyboards/inline_keyboards.py:848` | Thin delegate |
| `tests/integration/test_reaction_full_chain.py:24,207,326` | **Only remaining test consumer** |

---

## Risk Assessment (Week 2 Overall)

| Area | Level | Rationale |
|------|-------|-----------|
| Markup parity test | 🟢 LOW | Tests only; unified builder already in prod |
| tracking_failed test | 🟢 LOW | Tests only; documents existing guard |
| CLAUDE.md update | 🟢 LOW | Docs only |
| full_chain migration | 🟡 MEDIUM | Integration test rewrite — run full reaction gate after |
| credit_besitos spike | 🔴 HIGH if implemented | **Defer** — gold blast radius |
| **Overall Week 2** | 🟢 **LOW** | If scope locked to tests + docs + defer |

---

## Protected Systems Check

| System | Week 2 touch? | Protection |
|--------|---------------|------------|
| Gamification (reactions/besitos/missions) | Tests/docs only | Gold gate unchanged; no prod edits |
| Narrative | No | 0 files |
| Channels-VIP | No | 0 files |
| EventBus | No (if defer spike) | Observer untouched |
| get_service contract | No | Handler already 1× service call |
| Atomicity | No (if defer spike) | `test_cross_service_atomicity.py` must stay green |

---

## Files to CREATE

| File | Purpose |
|------|---------|
| _(none required)_ | Parity + tracking tests extend existing files |

## Files to EDIT

| File | Changes | Obj |
|------|---------|-----|
| `tests/unit/test_broadcast_channel_markup.py` | Add send↔refresh structural parity test(s) | 1 |
| `tests/unit/test_broadcast_service_reaction_flow.py` | Add `message_id=0` → `message_mismatch` test | 2 |
| `services/broadcast/CLAUDE.md` | Rewrite reaction flow + real API paths | 3 |
| `tests/integration/test_reaction_full_chain.py` | Migrate to `process_channel_reaction` | 4 |
| `decisions.md` | Entry: defer `credit_besitos(commit=False)` for reactions | 5 |

## Files NOT to EDIT (Week 2)

- `services/broadcast_service.py` — behavior frozen
- `services/besito_service.py` — no `commit=False` spike
- `handlers/gamification_user_handlers.py` — already slimmed Week 1
- `handlers/broadcast_handlers.py` — tracking_failed behavior frozen
- `keyboards/broadcast_channel_markup.py` — markup frozen
- `services/broadcast/reaction_validators.py` — validators frozen
- `bot.py`, `models/models.py`, mission/besito services

---

## Tests to Run (Mandatory Gate)

**Flags (non-negotiable):**
```bash
pytest -q --tb=line -p no:cov --override-ini="addopts="
```

### After Week 2 changes

```bash
# New / extended unit tests
pytest tests/unit/test_broadcast_channel_markup.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts="

# Migrated integration
pytest tests/integration/test_reaction_full_chain.py -q --tb=line -p no:cov --override-ini="addopts="

# Full reaction gold gate (must stay green)
pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_invariants.py -k "reaction" -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_mission_flow.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/handlers/test_gamification_user_handlers.py -k "reaction" -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_callbackdata_broadcast.py -q --tb=line -p no:cov --override-ini="addopts="
```

### Broader smoke (recommended)

```bash
pytest -k "reaction or broadcast_service_reaction or cross_service_atomicity or broadcast_channel_markup" -q --tb=line -p no:cov --override-ini="addopts="
```

---

## Suggested Implementation Order

1. **Markup parity test** — fast, no integration deps; locks Week 1 unification.
2. **`message_id=0` / tracking_failed test** — unit test in reaction_flow; documents ops failure mode.
3. **Migrate `test_reaction_full_chain.py`** — replace manual refresh with `process_channel_reaction`; run integration gate.
4. **Update `services/broadcast/CLAUDE.md`** — align docs with migrated tests + real paths.
5. **Document defer in `decisions.md`** — `credit_besitos(commit=False)` not pursued Week 2; cite gold blast radius.

---

## Acceptance Criteria Checklist

- [ ] Send vs refresh markup: identical structure (callbacks, row order, extra URL); only count text differs
- [ ] Broadcast `message_id=0` (tracking failed) → reaction returns `message_mismatch`
- [ ] `services/broadcast/CLAUDE.md` documents `check_and_register_reaction`, `process_channel_reaction`, validators, extra buttons, message_id validation
- [ ] `test_reaction_full_chain.py` uses `process_channel_reaction` (no manual `reactions_keyboard_with_counts` rebuild in primary test)
- [ ] `credit_besitos(commit=False)` decision documented (defer unless incident-driven)
- [ ] All gold tests green with mandated pytest flags
- [ ] **0 prod behavior change**

---

## Handoff

**Ready for:** `gsd-planner` → `gsd-executor`  
**Risk level:** **LOW** (tests + docs; atomicity safe if spike deferred)  
**Estimated touch surface:** 4 files edit, 0 prod code, ~3–5 new test cases  
**Depends on:** Week 1 closed (✅)