# 📊 Impact Analysis: Reaction Ecosystem Week 1 Hardening

**Item:** `reaction-ecosystem-week1` (Hardener-Agile Pool, Item 1)  
**Date:** 2026-07-05  
**Agent:** impact-analyzer  
**Mode:** Analysis only — NO code edits

---

## Scope Summary

Week 1 hardening of the broadcast reaction ecosystem with **0 user-visible behavior change** and **0 atomicity/EventBus/get_service contract change**:

| # | Objective | Current state | Target |
|---|-----------|---------------|--------|
| 1 | **Unify markup** | 3 divergent paths + manual URL append | Single pure module: send + refresh + extra URL |
| 2 | **Extract `check_and_register_reaction`** | Monolith **156 LOC** | Pure validators + orchestrator ≤50 LOC each |
| 3 | **Move refresh to service** | `handle_reaction` → `check_and_register_reaction` + `get_broadcast` + `refresh_reaction_markup_counts` | `process_channel_reaction(...)` — handler calls **1 service method** |
| 4 | **Deprecate `register_reaction`** | Already marked DEPRECATED; 9+ test call sites on sync path | Migrate feasible tests to `check_and_register_reaction`; keep legacy with deprecation |

---

## Current Architecture (As-Is)

### Markup — Triplicate Paths

| Path | Location | Purpose | Counts? | Extra URL? | Chunking (8/row)? |
|------|----------|---------|---------|------------|-------------------|
| A | `handlers/broadcast_handlers.py:41-61` `build_send_reaction_markup` | Legacy send helper | No | No | **No** — single row |
| B | `handlers/broadcast_handlers.py:83-114` `build_broadcast_send_markup` | **Production send** (`confirm_and_send_broadcast`) | No | Yes | Yes (`chunk_inline_buttons`) |
| C | `keyboards/inline_keyboards.py:875-898` `reactions_keyboard_with_counts` + `handlers/gamification_user_handlers.py:214-268` `refresh_reaction_markup_counts` manual append | **Production refresh** | Yes (`"💋 3"` format) | Yes (manual row append) | Yes (`_chunk_reaction_buttons`) |

**Production reality:** Path A is **dead code** in runtime — only referenced by tests. `confirm_and_send_broadcast` uses Path B exclusively.

### Reaction Registration

| Method | LOC | Async | Mission delivery | Return type | Status |
|--------|-----|-------|------------------|-------------|--------|
| `register_reaction` | 82 | Sync | Inline `MissionService.increment_progress` (no bot delivery) | `BroadcastReaction \| None` | DEPRECATED (docstring L285-289) |
| `check_and_register_reaction` | **156** | Async | `run_mission_side_effects_isolated` post-commit | `dict` with `success`/`reason`/`besitos_awarded` | **Production path** |

### Handler Flow (`handle_reaction`)

```
get_service(BroadcastService)                    # 1× get_service ✓
  └─ check_and_register_reaction(...)            # service method 1
  └─ get_broadcast(broadcast_id)                 # service method 2  ✗
  └─ refresh_reaction_markup_counts(...)         # helper → 5+ service calls ✗
       ├─ get_selected_emoji_ids
       ├─ get_reactions_by_broadcast
       ├─ get_reaction_emoji (N×)
       ├─ get_broadcast_button (if extra)
       └─ update_reaction_message
```

**Violation:** Handler orchestrates refresh across handler helper + multiple service reads. Target: single `process_channel_reaction`.

---

## Consumer Map (Grep Results)

### `build_send_reaction_markup`

| File | Usage |
|------|-------|
| `handlers/broadcast_handlers.py:41` | Definition |
| `tests/integration/test_callbackdata_broadcast.py:177-188` | `test_build_send_reaction_markup_uses_reaction_callback` |

**Production consumers: 0** (orphan — safe to remove/re-export from unified module).

### `build_broadcast_send_markup`

| File | Usage |
|------|-------|
| `handlers/broadcast_handlers.py:83,1141` | Definition + `confirm_and_send_broadcast` |
| `tests/integration/test_callbackdata_broadcast.py:261-354` | 5 tests in `TestBroadcastPureHelpers` |
| `MEMORY.md`, `decisions.md`, prior impact reports | Documentation only |

### `chunk_inline_buttons`

| File | Usage |
|------|-------|
| `handlers/broadcast_handlers.py:64,109` | Definition + used by `build_broadcast_send_markup` |
| `tests/integration/test_callbackdata_broadcast.py:356-365` | Pure chunk test |

### `reactions_keyboard_with_counts`

| File | Usage |
|------|-------|
| `keyboards/inline_keyboards.py:875` | Definition |
| `handlers/gamification_user_handlers.py:15,239` | Import + refresh path |
| `tests/integration/test_reaction_full_chain.py:24,207,326` | Full-chain markup rebuild (mirrors handler logic) |
| `keyboards/CLAUDE.md:31` | Docs |

### `refresh_reaction_markup_counts`

| File | Usage |
|------|-------|
| `handlers/gamification_user_handlers.py:214,299` | Definition + `handle_reaction` call site |
| `tests/handlers/test_gamification_user_handlers.py:424-439` | `test_refresh_preserves_extra_button_url_row` (direct import) |

### `check_and_register_reaction`

| File | Usage |
|------|-------|
| `services/broadcast_service.py:364` | Definition |
| `handlers/gamification_user_handlers.py:285` | **Production handler** |
| `tests/unit/test_broadcast_service_reaction_flow.py` | **22 tests** (gold unit suite) |
| `tests/integration/test_cross_service_atomicity.py` | 5+ atomicity scenarios |
| `tests/integration/test_invariants.py:414+` | Idempotency invariant |
| `tests/integration/test_reaction_full_chain.py:180` | Full chain |
| `tests/integration/test_reaction_mission_flow.py:388+` | Async production path test |
| `services/broadcast/CLAUDE.md`, `fases_refactor_testing.md` | Docs |

### `register_reaction` (deprecated)

| File | Usage |
|------|-------|
| `services/broadcast_service.py:281` | Definition (already DEPRECATED) |
| `tests/unit/test_broadcast_service.py:232-397` | **6 tests** (success, duplicate, queries, stats, race/SELECT FOR UPDATE) |
| `tests/integration/test_reaction_mission_flow.py:146,364` | Sync workaround comments |
| `tests/integration/test_reaction_limit.py:89-90` | Reaction limit test |

---

## Markup Parity Matrix (Critical for 0 Behavior Change)

| Dimension | Send (`build_broadcast_send_markup`) | Refresh (`reactions_keyboard_with_counts` + manual extra) | Risk if unified wrong |
|-----------|--------------------------------------|-----------------------------------------------------------|----------------------|
| Button text (no reactions yet) | `emoji` char only | `emoji` char only (count=0) | LOW |
| Button text (after reactions) | N/A at send | `"emoji count"` if count>0 else `emoji` | **HIGH** — format must match exactly |
| Callback data | `ReactionCallback(broadcast_id, emoji_id).pack()` → `react:...` | Same | **HIGH** — `handle_reaction` routing |
| Row order | Reaction rows first, extra URL last | Same | **HIGH** — UX parity |
| Extra-only broadcast | URL row only | URL row only (L251-258) | MEDIUM |
| No reactions + no extra | `None` | `None` | LOW |
| Chunking | 8 buttons/row | 8 buttons/row (duplicate helpers) | MEDIUM — Path A had no chunking |
| Emoji ordering | `selected_emoji_ids` iteration order | Same via `get_selected_emoji_ids` | MEDIUM |
| Skipped invalid emoji IDs | `get_emoji` returns None → skip | `get_reaction_emoji` None → skip | LOW |

**Unification contract:** One pure function (suggested signature):

```python
def build_channel_reaction_markup(
    broadcast_id: int,
    emoji_entries: list[tuple[int, str]],  # (id, char)
    *,
    emoji_counts: dict[int, int] | None = None,  # None → send mode (no counts)
    extra_button: BroadcastButton | None = None,
) -> InlineKeyboardMarkup | None
```

- `emoji_counts=None` → send path (Path B behavior)
- `emoji_counts={...}` → refresh path (Path C behavior)
- Extra URL row appended identically in both modes

---

## Proposed `check_and_register_reaction` Decomposition

Current: **156 LOC** (lines 364–519). Target: validators + orchestrator ≤50 LOC each.

### Suggested Pure Validators (no DB writes)

| Function | Input | Output | LOC est. |
|----------|-------|--------|----------|
| `validate_broadcast_exists_for_reaction` | `broadcast \| None` | `reason \| None` | ~8 |
| `validate_broadcast_context_match` | `broadcast, channel_id, message_id` | `reason \| None` | ~12 |
| `validate_reaction_emoji_allowed` | `emoji, emoji_id, selected_ids` | `reason \| None` | ~15 |
| `validate_reaction_not_duplicate` | `has_user_reacted: bool` | `reason \| None` | ~6 |

All return `None` if OK, else reason string matching existing contract:
`invalid_broadcast`, `no_reactions`, `message_mismatch`, `invalid_emoji`, `inactive_emoji`, `emoji_not_allowed`, `duplicate`.

### Orchestrator (stays in `BroadcastService`)

`check_and_register_reaction` (~45 LOC):
1. Load broadcast + run validators
2. INSERT + flush + credit + commit (unchanged transaction boundary)
3. Capture ids before mission side-effects
4. `run_mission_side_effects_isolated` (unchanged)
5. Return dict (unchanged keys)

**Placement options:**
- Validators: `services/broadcast/reaction_validators.py` (new) — `services/broadcast/` dir exists (CLAUDE.md only)
- Or: `services/broadcast_service.py` module-level pure functions above class

---

## Proposed `process_channel_reaction` (Service)

```python
async def process_channel_reaction(
    self,
    broadcast_id: int,
    user_id: int,
    emoji_id: int,
    *,
    username: str | None = None,
    bot=None,
    channel_id: int | None = None,
    message_id: int | None = None,
) -> dict:
    """Register reaction + refresh channel markup on success. Return dict identical to check_and_register_reaction."""
```

**Internal flow (0 behavior change):**
1. `result = await self.check_and_register_reaction(...)` — same args, same dict
2. If `result["success"]`:
   - `broadcast = self.get_broadcast(broadcast_id)`
   - If `broadcast and broadcast.has_reactions`:
     - Build markup via unified pure module (counts from `get_reactions_by_broadcast`)
     - `await self.update_reaction_message(...)` — same swallow-"not modified" semantics
3. Return `result` unchanged (handler still uses `besitos_awarded`, `reason`)

**Handler after refactor:**

```python
with get_service(BroadcastService) as broadcast_service:
    result = await broadcast_service.process_channel_reaction(
        broadcast_id=..., user_id=..., emoji_id=...,
        username=..., bot=..., channel_id=..., message_id=...,
    )
# callback.answer logic unchanged — pure helpers reaction_failure_message stay in handler
```

**Handler helpers to keep in `gamification_user_handlers.py`:**
- `REACTION_FAILURE_MESSAGES` / `reaction_failure_message` — UI mapping (pure, not service concern)
- `calculate_emoji_counts_from_reactions` — move to unified markup module or service private helper

**Handler helpers to remove:**
- `refresh_reaction_markup_counts` → absorbed by `process_channel_reaction`

---

## Risk Assessment

### 🔴 HIGH — Markup Parity Regression

- **Risk:** Unified builder changes button text format, row order, chunking, or `react:` callback packing.
- **Blast radius:** Every channel broadcast with reactions; users cannot react or see wrong counts.
- **Mitigation:**
  - Port existing tests from `TestBroadcastPureHelpers` + `test_refresh_preserves_extra_button_url_row` to unified module tests before deleting old functions.
  - Golden assertions on `inline_keyboard` structure (rows, `callback_data`, `url`, `text`).
  - Keep `reactions_keyboard_with_counts` as thin deprecated wrapper initially (optional safety shim).

### 🔴 HIGH — `check_and_register_reaction` Return Dict Contract

- **Risk:** Any change to `success`/`reason` keys or success payload (`besitos_awarded`, `id`, etc.).
- **Blast radius:** `handle_reaction` UX, gold tests (`test_broadcast_service_reaction_flow`, `cross_service_atomicity`, `invariants`).
- **Mitigation:** Extract validators only; orchestrator body copy-paste with zero logic change in Week 1. Run all 22 unit tests + integration golds.

### 🟡 MEDIUM — Atomicity / Transaction Boundaries

- **Risk:** Accidentally moving credit/INSERT into validator or merging refresh into same DB transaction.
- **Blast radius:** Gamification (besitos), missions, EventBus `besitos_awarded` observer.
- **Mitigation:**
  - Validators: read-only queries only.
  - `process_channel_reaction`: markup refresh **after** `check_and_register_reaction` returns (post-commit); `update_reaction_message` stays best-effort (already swallows errors).
  - Do NOT call `credit_besitos` from refresh path.
  - Re-run: `test_cross_service_atomicity.py`, `test_invariants.py::test_check_and_register_reaction_idempotent_no_duplicate_besitos`.

### 🟡 MEDIUM — Handler Test Breakage

- **Risk:** `TestHandleReaction` mocks `check_and_register_reaction`, `get_broadcast`, `update_reaction_message` separately. After refactor, mocks target `process_channel_reaction` only.
- **Files:** `tests/handlers/test_gamification_user_handlers.py` (10+ reaction tests).
- **Mitigation:** Update mocks in same PR; preserve assert on `callback.answer` strings and `update_reaction_message` kwargs.

### 🟡 MEDIUM — `register_reaction` Test Migration

- **Risk:** Migrating sync tests to async changes mission delivery semantics in tests.
- **Call sites:** 6 unit + 3 integration.
- **Mitigation:**
  - Keep `register_reaction` with `@warnings.deprecated` or existing docstring; do not delete Week 1.
  - Migrate query/stats tests that only need a reaction row to `check_and_register_reaction` with `pytest.mark.asyncio`.
  - `test_register_reaction_uses_select_for_update` — keep on legacy path OR rewrite to assert on `check_and_register_reaction` flush+IntegrityError path.

### 🟢 LOW — Atomicity / EventBus / get_service

- `get_service(BroadcastService)` count stays 1 per handler entry.
- `on_besitos_awarded_broadcast_reaction_observer` untouched.
- `ReactionCallback` prefix `react:` unchanged (`callback_data.py:13-17`).
- Channels-VIP, narrative: **0 direct consumers** of markup paths.

### 🟢 LOW — Broadcast Send Wizard

- `confirm_and_send_broadcast` only changes import for markup builder.
- FSM, preview, extra-button wizard unchanged.

---

## Protected Systems Check

| System | Touch in Week 1? | Protection |
|--------|------------------|------------|
| Gamification (reactions/besitos/missions) | Yes — refactor only | Gold: `cross_service_atomicity`, `reaction_*`, `test_broadcast_service_reaction_flow` |
| Narrative | No direct touch | 0 files in consumer map |
| Channels-VIP | No direct touch | 0 files in consumer map |
| EventBus | No touch | Observer in `broadcast_service.py:611-628` stays |
| get_service contract | Preserved | 1 call, 1 method in `handle_reaction` |

---

## Files to CREATE

| File | Purpose |
|------|---------|
| `keyboards/broadcast_channel_markup.py` | **Unified pure module** — `build_channel_reaction_markup`, shared `_chunk_reaction_buttons`, optional `calculate_emoji_counts_from_reactions` |
| `services/broadcast/reaction_validators.py` | Pure validators extracted from `check_and_register_reaction` (optional but aligns with `services/broadcast/` dir) |
| `tests/unit/test_broadcast_channel_markup.py` | Port markup parity tests (send/refresh/combined/none/chunk/extra) |

## Files to EDIT

| File | Changes |
|------|---------|
| `handlers/broadcast_handlers.py` | Remove `build_send_reaction_markup`, `build_broadcast_send_markup`, `chunk_inline_buttons`; import unified builder in `confirm_and_send_broadcast` |
| `handlers/gamification_user_handlers.py` | Remove `refresh_reaction_markup_counts`, `calculate_emoji_counts_from_reactions`; `handle_reaction` → single `process_channel_reaction` call |
| `services/broadcast_service.py` | Add `process_channel_reaction`; decompose `check_and_register_reaction`; strengthen `register_reaction` deprecation (`warnings.warn` optional) |
| `keyboards/inline_keyboards.py` | Deprecate `reactions_keyboard_with_counts` → thin re-export to unified module (backward compat for `test_reaction_full_chain`) |
| `tests/integration/test_callbackdata_broadcast.py` | Update imports to `keyboards.broadcast_channel_markup` |
| `tests/handlers/test_gamification_user_handlers.py` | Mock `process_channel_reaction`; update/remove `test_refresh_preserves_extra_button_url_row` direct import |
| `tests/integration/test_reaction_full_chain.py` | Optionally use unified builder (behavior-identical) |
| `tests/unit/test_broadcast_service.py` | Migrate feasible tests from `register_reaction` → `check_and_register_reaction` |
| `tests/integration/test_reaction_mission_flow.py` | Migrate sync path where feasible |
| `tests/integration/test_reaction_limit.py` | Migrate to async path where feasible |
| `keyboards/CLAUDE.md` | Document unified module (minimal) |

## Files NOT to EDIT (Week 1)

- `keyboards/callback_data.py` — `ReactionCallback` stable
- `bot.py` — router registration unchanged
- `models/models.py` — schema unchanged
- Mission/Besito services — no composer changes
- EventBus listener registration

---

## Pre-Existing Violations (Document, Do Not Fix Week 1)

| Item | LOC | Note |
|------|-----|------|
| `check_and_register_reaction` | 156 | Week 1 target: split |
| `register_reaction` | 82 | Over 50; deprecated, shrink not required Week 1 |
| `build_send_reaction_markup` | 21 | Orphan — delete via unification |

---

## Tests to Run (Mandatory Gate)

**Flags (non-negotiable):**
```bash
pytest -q --tb=line -p no:cov --override-ini="addopts="
```

### Gold / Critical (must be green)

```bash
# Unit — production reaction path
pytest tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts="

# Integration — atomicity + invariants + full chains
pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_invariants.py -k "reaction" -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_full_chain.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_mission_flow.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="

# Handler + markup + legacy service tests
pytest tests/handlers/test_gamification_user_handlers.py -k "reaction" -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_callbackdata_broadcast.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/unit/test_broadcast_service.py -q --tb=line -p no:cov --override-ini="addopts="
```

### New tests to add (executor)

```bash
pytest tests/unit/test_broadcast_channel_markup.py -q --tb=line -p no:cov --override-ini="addopts="
```

### Broader smoke (recommended)

```bash
pytest -k "reaction or broadcast_service_reaction or cross_service_atomicity" -q --tb=line -p no:cov --override-ini="addopts="
```

---

## Suggested Implementation Order

1. **Create unified markup module** + unit tests (port from `test_callbackdata_broadcast` + refresh preserve test logic) — no caller changes yet.
2. **Wire send path** (`confirm_and_send_broadcast`) to unified module — run callbackdata tests.
3. **Add `process_channel_reaction`** using unified module for refresh — run handler + full_chain tests.
4. **Slim `handle_reaction`** to 1 service call — update handler tests.
5. **Extract validators** from `check_and_register_reaction` — run reaction_flow + atomicity golds.
6. **Deprecate shims** (`reactions_keyboard_with_counts`, `register_reaction` test migration) — final full gate.

---

## Acceptance Criteria Checklist

- [ ] Single `build_channel_reaction_markup` (or equivalent) covers send + refresh + extra URL
- [ ] `handle_reaction`: exactly `1× get_service` + `1× process_channel_reaction`
- [ ] `check_and_register_reaction` split: validators ≤50 LOC, orchestrator ≤50 LOC
- [ ] Return dict from `check_and_register_reaction` byte-identical contract
- [ ] `register_reaction` remains deprecated; tests migrated where feasible
- [ ] All gold tests green with mandated pytest flags
- [ ] 0 user-visible behavior change verified via markup golden tests

---

## Handoff

**Ready for:** `gsd-planner` → `gsd-executor`  
**Risk level:** **MEDIUM-HIGH** (markup parity + handler mock migration; atomicity LOW if transaction boundaries respected)  
**Estimated touch surface:** 8–10 files edit, 2–3 files create, 4–5 test files update