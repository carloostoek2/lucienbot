# PLAN: Reaction Ecosystem Week 1 Hardening

**Item:** `reaction-ecosystem-week1` (Hardener-Agile Pool, Item 1)  
**Date:** 2026-07-05  
**Type:** auto (hardener tight scope)  
**Effort:** 5  

---

## Objective

Week 1 hardening of the broadcast reaction ecosystem with **0 user-visible behavior change** and **0 atomicity/EventBus/get_service contract change**:

| # | Objective | Current | Target |
|---|-----------|---------|--------|
| 1 | **Unify markup** | 3 divergent paths + manual URL append | Single pure module: send + refresh + extra URL |
| 2 | **Extract `check_and_register_reaction`** | Monolith **156 LOC** | Pure validators + orchestrator ≤50 LOC each |
| 3 | **Move refresh to service** | Handler orchestrates 3+ service calls | `process_channel_reaction(...)` — handler calls **1 service method** |
| 4 | **Deprecate `register_reaction`** | DEPRECATED; 9+ test call sites on sync path | Migrate feasible tests; keep legacy with deprecation |

**Out of scope (locked):**
- NO changes to `ReactionCallback` / `callback_data.py`
- NO changes to `bot.py` router registration
- NO changes to models/schema/migrations
- NO changes to Mission/Besito composers beyond refactor-only moves
- NO changes to EventBus observer `on_besitos_awarded_broadcast_reaction_observer`
- NO Channels-VIP, Narrative, or other domains

---

## Context (@refs)

**Mandatory reads (do before any edit):**
- `@.grok/agent-memory/impact-analyzer/reaction-ecosystem-week1.md` (source of truth)
- `@CLAUDE.md` — hardener workflow, 6-agent sequence, 3 critical systems
- `@architecture.md` — handlers → services → models
- `@rules.md` — ≤50 LOC, verb+context+result, 1 service per handler
- `@services/broadcast/CLAUDE.md` — reaction atomicity, local BesitoService, observer
- `@handlers/CLAUDE.md` — get_service contract
- `@keyboards/CLAUDE.md` — callback_data stability

**Key code (copy verbatim for parity):**
- Send markup: `handlers/broadcast_handlers.py:83-114` `build_broadcast_send_markup` + `chunk_inline_buttons:64-66`
- Refresh markup: `keyboards/inline_keyboards.py:875-898` `reactions_keyboard_with_counts` + `_chunk_reaction_buttons:868-872`
- Refresh orchestration: `handlers/gamification_user_handlers.py:214-268` `refresh_reaction_markup_counts`
- Counts helper: `handlers/gamification_user_handlers.py:185-192` `calculate_emoji_counts_from_reactions`
- Handler flow: `handlers/gamification_user_handlers.py:271-311` `handle_reaction`
- Production registration: `services/broadcast_service.py:364-519` `check_and_register_reaction`
- Deprecated sync: `services/broadcast_service.py:281-362` `register_reaction`

**Markup parity contract (0 behavior change):**
```python
def build_channel_reaction_markup(
    broadcast_id: int,
    emoji_entries: list[tuple[int, str]],  # (id, char)
    *,
    emoji_counts: dict[int, int] | None = None,  # None → send mode (no counts)
    extra_button: BroadcastButton | None = None,
) -> InlineKeyboardMarkup | None
```
- `emoji_counts=None` → send path (emoji char only, `react:` callbacks, 8/row chunking)
- `emoji_counts={...}` → refresh path (`"emoji count"` if count>0 else `emoji`, same callbacks)
- Extra URL row appended last in both modes

---

## Constraints (NON-NEGOTIABLE)

1. **0 behavior change, 0 atomicity change** — byte-identical UX, return dicts, transaction boundaries.
2. **`handle_reaction`:** exactly `1× get_service(BroadcastService)` + `1× process_channel_reaction` (after Task 4).
3. **Functions ≤50 LOC** — verb+context+result naming; pure helpers docstring `"Función pura."`
4. **Validators:** read-only queries only; NO writes, NO credit, NO commit inside validators.
5. **`process_channel_reaction`:** markup refresh **after** `check_and_register_reaction` returns (post-commit); `update_reaction_message` best-effort (swallow "not modified").
6. **Do NOT** merge refresh into the same DB transaction as reaction INSERT/credit.
7. **Do NOT** delete `register_reaction` Week 1 — deprecate + migrate tests where feasible.
8. **GSD pre-log:** `.planning/quick/gsd-reaction-ecosystem-week1.log` before EVERY edit/gate/ruff/pytest.

---

## Tasks (implementation order)

### Task 1: Unified markup module + unit tests

**Objective:** Create `keyboards/broadcast_channel_markup.py` with single builder covering send + refresh + extra URL. Port gold tests before any caller changes.

**Files:**
- `keyboards/broadcast_channel_markup.py` (NEW)
- `tests/unit/test_broadcast_channel_markup.py` (NEW)

**Actions (exact):**
1. Create `keyboards/broadcast_channel_markup.py` with:
   - `chunk_reaction_buttons(buttons, max_per_row=8)` — copy from `chunk_inline_buttons` / `_chunk_reaction_buttons`. Docstring: `"Función pura."`
   - `calculate_emoji_counts_from_reactions(reactions: list) -> dict[int, int]` — move from `gamification_user_handlers.py:185-192` (identical logic). Docstring: `"Función pura."`
   - `build_channel_reaction_markup(broadcast_id, emoji_entries, *, emoji_counts=None, extra_button=None)` — unified builder per parity contract above. Docstring: `"Función pura."`
   - Optional thin adapter for send path signature compatibility:
     ```python
     def build_broadcast_send_markup(broadcast_id, selected_emoji_ids, extra_button, get_emoji):
         """Wrapper send-path; delegates to build_channel_reaction_markup. Función pura."""
     ```
2. Create `tests/unit/test_broadcast_channel_markup.py` — port ALL cases from `TestBroadcastPureHelpers` in `tests/integration/test_callbackdata_broadcast.py:258-365`:
   - reactions_only, extra_only, combined, none, chunks_nine_emojis, chunk_pure
   - ADD refresh-mode tests mirroring `reactions_keyboard_with_counts` behavior:
     - count=0 → text is emoji only
     - count>0 → text is `f"{emoji} {count}"`
   - ADD `test_refresh_preserves_extra_button_url_row` logic (from `test_gamification_user_handlers.py:404-439`) using unified builder directly
   - ADD `test_build_send_reaction_markup_uses_reaction_callback` equivalent (orphan path parity)
3. **Do NOT** delete old functions yet — module exists standalone first.

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/unit/test_broadcast_channel_markup.py
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK1 markup_module file=keyboards/broadcast_channel_markup.py action=create_unified_builder+tests
```

---

### Task 2: Wire send path to unified module

**Objective:** `confirm_and_send_broadcast` uses unified builder; remove duplicate send helpers from handler.

**Files:**
- `handlers/broadcast_handlers.py`
- `tests/integration/test_callbackdata_broadcast.py`

**Actions (exact):**
1. In `confirm_and_send_broadcast` (~line 1141): import `build_broadcast_send_markup` from `keyboards.broadcast_channel_markup` (or call `build_channel_reaction_markup` directly with `emoji_counts=None`).
2. **Delete** from `broadcast_handlers.py`:
   - `build_send_reaction_markup` (lines 41-61) — orphan, tests only
   - `build_broadcast_send_markup` (lines 83-114)
   - `chunk_inline_buttons` (lines 64-66)
3. Update `tests/integration/test_callbackdata_broadcast.py`:
   - `TestBroadcastPureHelpers` imports → `keyboards.broadcast_channel_markup`
   - `test_build_send_reaction_markup_uses_reaction_callback` → import from unified module or test via `build_channel_reaction_markup`
   - `test_chunk_inline_buttons_pure` → `chunk_reaction_buttons` from unified module
4. Run callbackdata tests — markup structure must be byte-identical (rows, text, callback_data, url).

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/integration/test_callbackdata_broadcast.py -k "broadcast_channel_markup or TestBroadcastPureHelpers or build_send_reaction"
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK2 wire_send file=handlers/broadcast_handlers.py action=import_unified_remove_duplicates
```

---

### Task 3: `process_channel_reaction` + refresh in service

**Objective:** Move refresh orchestration from handler helper into `BroadcastService.process_channel_reaction`.

**Files:**
- `services/broadcast_service.py`
- `keyboards/broadcast_channel_markup.py` (import in service)

**Actions (exact):**
1. Add `async def process_channel_reaction(self, broadcast_id, user_id, emoji_id, *, username=None, bot=None, channel_id=None, message_id=None) -> dict`:
   ```python
   """Register reaction + refresh channel markup on success. Return dict identical to check_and_register_reaction."""
   ```
2. Internal flow (copy-paste semantics from `refresh_reaction_markup_counts` + `handle_reaction`):
   - `result = await self.check_and_register_reaction(...)` — same args, same dict
   - If `result.get("success")`:
     - `broadcast = self.get_broadcast(broadcast_id)`
     - If `broadcast and broadcast.has_reactions`:
       - `selected_emoji_ids = self.get_selected_emoji_ids(broadcast_id)`
       - `reactions = self.get_reactions_by_broadcast(broadcast_id)`
       - `emoji_counts = calculate_emoji_counts_from_reactions(reactions)` (from unified module)
       - Build `emoji_entries` via `get_reaction_emoji` loop (skip None)
       - `extra_button = self.get_broadcast_button(extra_id)` if `extra_button_id` int
       - `new_markup = build_channel_reaction_markup(..., emoji_counts=emoji_counts, extra_button=extra_button)`
       - `await self.update_reaction_message(bot=bot, channel_id=..., message_id=..., new_markup=new_markup)` if markup not None
   - Return `result` unchanged
3. **Do NOT** change `check_and_register_reaction` body in this task.
4. **Do NOT** slim handler yet — `handle_reaction` still calls old path; service method exists for Task 4.

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/integration/test_reaction_full_chain.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/unit/test_broadcast_service_reaction_flow.py
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK3 process_channel_reaction file=services/broadcast_service.py action=add_refresh_orchestration
```

---

### Task 4: Slim `handle_reaction` to 1 service call

**Objective:** Handler calls only `process_channel_reaction`; remove handler refresh helpers.

**Files:**
- `handlers/gamification_user_handlers.py`
- `tests/handlers/test_gamification_user_handlers.py`

**Actions (exact):**
1. Replace `handle_reaction` body (lines 284-301) with:
   ```python
   with get_service(BroadcastService) as broadcast_service:
       result = await broadcast_service.process_channel_reaction(
           broadcast_id=broadcast_id,
           user_id=user.id,
           emoji_id=emoji_id,
           username=user.username,
           bot=callback.bot,
           channel_id=callback.message.chat.id,
           message_id=callback.message.message_id,
       )
   # callback.answer logic UNCHANGED — uses result["success"], besitos_awarded, reason + reaction_failure_message
   ```
2. **Delete** from `gamification_user_handlers.py`:
   - `refresh_reaction_markup_counts` (lines 214-268)
   - `calculate_emoji_counts_from_reactions` (lines 185-192) — now in unified module
3. **Keep** in handler: `REACTION_FAILURE_MESSAGES`, `reaction_failure_message` (UI mapping, pure)
4. Update `tests/handlers/test_gamification_user_handlers.py` `TestHandleReaction`:
   - Mock `process_channel_reaction` instead of `check_and_register_reaction` + `get_broadcast` + `update_reaction_message` separately
   - `test_registers_reaction` → assert `process_channel_reaction.assert_called_once()` with same kwargs
   - `test_updates_reaction_counts` → mock `process_channel_reaction` returning `{"success": True, "besitos_awarded": 5}`; refresh now internal to service — either remove granular update_reaction_message assert OR add service-level test (prefer moving refresh assert to service test if needed)
   - `test_refresh_preserves_extra_button_url_row` → move to `tests/unit/test_broadcast_channel_markup.py` (Task 1) or new service unit test; remove direct `refresh_reaction_markup_counts` import
5. Grep verify: `handle_reaction` has exactly 1 `get_service` and 1 service method call.

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/handlers/test_gamification_user_handlers.py -k "reaction or TestHandleReaction"
rg "get_service|check_and_register_reaction|process_channel_reaction" handlers/gamification_user_handlers.py
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK4 slim_handler file=handlers/gamification_user_handlers.py action=process_channel_reaction_only
```

---

### Task 5: Extract validators from `check_and_register_reaction`

**Objective:** Split 156 LOC monolith into pure validators (≤50 LOC each) + orchestrator (≤50 LOC).

**Files:**
- `services/broadcast/reaction_validators.py` (NEW)
- `services/broadcast_service.py`

**Actions (exact):**
1. Create `services/broadcast/reaction_validators.py` with pure functions (each docstring `"Función pura."`):
   - `validate_broadcast_exists_for_reaction(broadcast) -> str | None` — returns reason or None
   - `validate_broadcast_context_match(broadcast, channel_id, message_id) -> str | None`
   - `validate_reaction_emoji_allowed(emoji, emoji_id, selected_ids) -> str | None`
   - `validate_reaction_not_duplicate(has_user_reacted: bool) -> str | None`
   - Reason strings MUST match existing contract: `invalid_broadcast`, `no_reactions`, `message_mismatch`, `invalid_emoji`, `inactive_emoji`, `emoji_not_allowed`, `duplicate`
2. Refactor `check_and_register_reaction` orchestrator (~45 LOC):
   - Load broadcast + emoji + selected_ids + has_user_reacted
   - Run validators in same order as current code (lines 386-415)
   - **Copy-paste unchanged:** INSERT + flush + credit + commit + mission side-effects + return dict + IntegrityError handling (lines 417-519)
3. **Zero logic change** in transaction body — validators are extract-only.
4. Verify orchestrator + each validator ≤50 LOC via inspect/wc.

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/unit/test_broadcast_service_reaction_flow.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/integration/test_cross_service_atomicity.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/integration/test_invariants.py -k "reaction"
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK5 validators file=services/broadcast/reaction_validators.py action=extract_pure_validators
```

---

### Task 6: Deprecate shims + migrate `register_reaction` tests

**Objective:** Thin deprecated wrappers remain; migrate feasible sync tests to async production path.

**Files:**
- `keyboards/inline_keyboards.py`
- `services/broadcast_service.py`
- `tests/unit/test_broadcast_service.py`
- `tests/integration/test_reaction_mission_flow.py`
- `tests/integration/test_reaction_limit.py`
- `keyboards/CLAUDE.md` (minimal doc note)

**Actions (exact):**
1. `reactions_keyboard_with_counts` in `inline_keyboards.py` → thin deprecated wrapper delegating to `build_channel_reaction_markup` (keep signature for `test_reaction_full_chain.py` backward compat).
2. `register_reaction` — strengthen deprecation:
   - Keep method body unchanged
   - Add `warnings.warn("register_reaction is deprecated; use check_and_register_reaction", DeprecationWarning, stacklevel=2)` at top OR keep existing docstring DEPRECATED marker
3. Migrate tests in `tests/unit/test_broadcast_service.py` `TestBroadcastReactions` + `TestBroadcastQueries` + `TestBroadcastStats`:
   - `test_register_reaction_success` → `pytest.mark.asyncio` + `check_and_register_reaction` with `pytest.mark.filterwarnings("ignore::DeprecationWarning")` if needed
   - `test_register_reaction_duplicate` → async path duplicate assert on `result["success"]` False, `reason=="duplicate"`
   - Query/stats tests: seed reactions via `check_and_register_reaction` instead of `register_reaction`
   - **Keep** `test_register_reaction_uses_select_for_update` on legacy path OR rewrite to assert flush+IntegrityError on async path (executor choice: keep legacy for SELECT FOR UPDATE semantics)
4. Migrate `tests/integration/test_reaction_mission_flow.py` and `test_reaction_limit.py` sync workarounds where comments indicate feasible.
5. Optional: update `tests/integration/test_reaction_full_chain.py` to use unified builder (behavior-identical).

**Verification (full gate):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "reaction or broadcast_channel_markup or TestBroadcastPureHelpers or TestHandleReaction"
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK6 deprecate_migrate action=shims+test_migration
```

**Self-check (append to log after full gate green):**
```
[$(date)] SELF_CHECK PASSED item=reaction-ecosystem-week1 all_golds_green scope=week1_hardening 0_behavior_change 0_atomicity_change handle_reaction=1svc+1method
```

---

## Instrucciones para gsd-executor (MANDATORY)

1. **Lee este PLAN completo** + impact report antes de tocar código. No infieras scope de memoria.

2. **GSD pre-log antes de CADA edit/gate/ruff/pytest:**
   - Append a `.planning/quick/gsd-reaction-ecosystem-week1.log`
   - Formato: `[timestamp] GSD_PRE TASKn file=... action=...`
   - `wc -l` en el log después de cada append para confirmar crecimiento.
   - **Sin pre-log → sin edit.**

3. **Orden estricto:** Task 1 → 2 → 3 → 4 → 5 → 6. No saltar fases.

4. **Gold test patterns (copiar al pie de la letra):**

   **TestSession / file DB (integration atomicity):**
   ```python
   from tests.conftest import TestSession  # or project pattern
   # Use TestSession for cross-service atomicity tests; never share session across concurrent tasks
   ```

   **patch schedule_emit (reaction flow unit tests):**
   ```python
   with patch("services.besito_service.schedule_emit") as mock_schedule:
       result = await service.check_and_register_reaction(...)
       # Assert credit happened; schedule_emit called best-effort post-commit
   ```

   **reaction_result dict asserts (handler + service):**
   ```python
   assert result["success"] is True
   assert result["besitos_awarded"] == expected_value
   assert result.get("reason") is None  # on success
   # Failure:
   assert result["success"] is False
   assert result["reason"] == "duplicate"  # or invalid_broadcast, etc.
   ```

   **import-inside tests for pure helpers:**
   ```python
   def test_chunk_reaction_buttons_pure(self):
       from keyboards.broadcast_channel_markup import chunk_reaction_buttons
       # ... asserts
   ```

   **TestHandleReaction mock pattern (after Task 4):**
   ```python
   @patch("handlers.gamification_user_handlers.get_service")
   async def test_registers_reaction(self, mock_get_service, make_callback):
       mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
       mock_instance.process_channel_reaction = AsyncMock(
           return_value={"success": True, "besitos_awarded": 5}
       )
       # ... assert process_channel_reaction.assert_called_once() with kwargs
   ```

5. **Pure helpers:** docstring exact `"Función pura."` — no DB, no bot, no side effects.

6. **Markup parity:** Before deleting old builders, run side-by-side assert on `inline_keyboard` structure (rows count, button text, callback_data prefix `react:`, url row last).

7. **Atomicity guardrails:**
   - Validators: read-only only
   - `process_channel_reaction`: refresh AFTER `check_and_register_reaction` returns (post-commit)
   - Do NOT call `credit_besitos` from refresh path
   - Do NOT touch `on_besitos_awarded_broadcast_reaction_observer`

8. **LOC enforcement:** `python -c "import inspect; ..."` or `wc -l` per function after edits. All ≤50.

9. **Ruff:** `ruff check --fix` + `ruff format` on every touched file before pytest gate.

10. **Self-check PASSED** al final del log con confirmación de constraints.

11. **Handoff post-success:** SUMMARY conciso + path PLAN + confirmación golds green → arch-enforcer → test-guardian.

---

## Test Commands (exact flags — NON-NEGOTIABLE)

**Primary gate (run after each task + final):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "reaction or broadcast_channel_markup or TestBroadcastPureHelpers or TestHandleReaction"
```

**Per-task targeted (in addition to primary gate):**

Task 1:
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_channel_markup.py
```

Task 2:
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_callbackdata_broadcast.py
```

Task 3:
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_reaction_full_chain.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_service_reaction_flow.py
```

Task 5:
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_service_reaction_flow.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_cross_service_atomicity.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_invariants.py -k "reaction"
```

**Full gold suite (Task 6 final gate):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_service_reaction_flow.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_cross_service_atomicity.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_invariants.py -k "reaction"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_reaction_full_chain.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_reaction_mission_flow.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_reaction_limit.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/handlers/test_gamification_user_handlers.py -k "reaction"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_callbackdata_broadcast.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_service.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_channel_markup.py
```

**Baseline (run before Task 1 edits):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "reaction or broadcast_channel_markup or TestBroadcastPureHelpers or TestHandleReaction"
```

---

## Risks + Mitigation

| Risk | Level | Mitigation |
|------|-------|------------|
| Markup parity regression (text format, row order, chunking, `react:` packing) | 🔴 HIGH | Port all `TestBroadcastPureHelpers` + refresh preserve test BEFORE deleting old functions; golden asserts on `inline_keyboard` |
| Return dict contract change | 🔴 HIGH | Validators extract-only; orchestrator body copy-paste; run 22 unit reaction_flow tests |
| Accidental transaction merge (refresh in same tx as credit) | 🟡 MEDIUM | `process_channel_reaction` refresh strictly post-commit; re-run atomicity + invariants |
| Handler test mock breakage | 🟡 MEDIUM | Update mocks to `process_channel_reaction` in same PR as handler slim |
| `register_reaction` test migration changes semantics | 🟡 MEDIUM | Keep legacy for SELECT FOR UPDATE test; migrate query/stats only; filter DeprecationWarning |
| EventBus / get_service / observer | 🟢 LOW | Untouched by design; grep verify post-Task 4 |

---

## Success Criteria (measurable)

- [ ] `build_channel_reaction_markup` covers send + refresh + extra URL (single module)
- [ ] `handle_reaction`: exactly `1× get_service` + `1× process_channel_reaction`
- [ ] `check_and_register_reaction`: validators ≤50 LOC each, orchestrator ≤50 LOC
- [ ] Return dict from `check_and_register_reaction` byte-identical contract
- [ ] `register_reaction` remains deprecated; feasible tests migrated
- [ ] All gold tests green with mandated pytest flags
- [ ] 0 user-visible behavior change (markup golden tests pass)
- [ ] GSD pre-logs for every edit; self-check PASSED in log
- [ ] Ruff clean on touched files

---

## Files Summary

**CREATE:**
- `keyboards/broadcast_channel_markup.py`
- `services/broadcast/reaction_validators.py`
- `tests/unit/test_broadcast_channel_markup.py`

**EDIT:**
- `handlers/broadcast_handlers.py`
- `handlers/gamification_user_handlers.py`
- `services/broadcast_service.py`
- `keyboards/inline_keyboards.py`
- `tests/integration/test_callbackdata_broadcast.py`
- `tests/handlers/test_gamification_user_handlers.py`
- `tests/unit/test_broadcast_service.py`
- `tests/integration/test_reaction_mission_flow.py` (feasible)
- `tests/integration/test_reaction_limit.py` (feasible)
- `keyboards/CLAUDE.md` (minimal)

**NOT TO EDIT:**
- `keyboards/callback_data.py`, `bot.py`, `models/models.py`, Mission/Besito composers, EventBus registration

---

**Handoff:** Ready for `gsd-executor`. Lee PLAN completo + impact report antes de editar. GSD pre-log en `.planning/quick/gsd-reaction-ecosystem-week1.log`.