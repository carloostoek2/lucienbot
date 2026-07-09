# PLAN: Reaction Ecosystem Week 2 — Tests + Docs + Debt Closure

**Item:** `reaction-ecosystem-week2` (Hardener-Agile Pool, builds on Week 1)  
**Date:** 2026-07-06  
**Type:** auto (hardener tight scope)  
**Effort:** 5  
**Depends on:** Week 1 closed (✅ per `.grok/agent-memory/documentador/reaction-ecosystem-week1-closed.md`)

---

## Objective

Week 2 closes **test gaps, documentation drift, and Week 1 integration debt** with **0 production code changes** and **0 user-visible behavior change**. Atomicity golds must stay green.

| # | Objective | Current (post-Week 1) | Week 2 target | Prod change? |
|---|-----------|----------------------|---------------|--------------|
| 1 | **Markup parity golden test** | Send + refresh tested in isolation (11 tests); no structural diff | Golden: send vs refresh identical structure (callbacks, row order, extra URL); only button **text** differs when counts > 0 | **Tests only** |
| 2 | **`tracking_failed` → `message_mismatch` test** | `message_id=0` persisted on DB update fail; validator exists; no test ties flows | Broadcast `message_id=0` + real TG `message_id` → `message_mismatch` | **Tests only** |
| 3 | **Migrate `test_reaction_full_chain.py`** | Still mirrors pre-Week-1 handler: `check_and_register_reaction` + manual markup rebuild | Use `process_channel_reaction` (Week 1 debt) | **Tests only** |
| 4 | **Rewrite `services/broadcast/CLAUDE.md`** | Stale: `register_reaction` as prod path; missing validators, `process_channel_reaction`, markup, `message_id` validation | Document real production paths and contracts | **Docs only** |
| 5 | **Defer `credit_besitos(commit=False)`** | Split-tx intentional (Item 6); spike high blast radius | `decisions.md` entry: DEFER with rationale; **no prod spike** | **Decision doc only** |

**Out of scope (locked):**
- NO edits to `services/broadcast_service.py`, `besito_service.py`, handlers, keyboards, validators, models
- NO `credit_besitos(commit=False)` implementation
- NO changes to EventBus observers, `get_service` contract, or atomicity boundaries
- NO dedupe of `test_callbackdata_broadcast.py` unless drift found during parity work

---

## Context (@refs)

**Mandatory reads (do before any edit):**
- `@.grok/agent-memory/impact-analyzer/reaction-ecosystem-week2.md` (source of truth)
- `@.grok/agent-memory/documentador/reaction-ecosystem-week1-closed.md` (Week 1 baseline)
- `@.planning/quick/20260705-reaction-ecosystem-week1/PLAN.md` + SUMMARY (precedent)
- `@CLAUDE.md` — hardener workflow, 6-agent sequence
- `@services/broadcast/CLAUDE.md` — **stale; Task 4 rewrites**
- `@keyboards/broadcast_channel_markup.py` — unified markup (frozen)
- `@services/broadcast/reaction_validators.py` — pure validators (frozen)
- `@services/broadcast_service.py:380-578` — `check_and_register_reaction` + `process_channel_reaction` (frozen)
- `@handlers/gamification_user_handlers.py:214-223` — production handler (frozen)
- `@handlers/broadcast_handlers.py:121,163,1094` — `message_id=0` + `tracking_failed` (frozen)

**Week 1 production path (do not change):**
```python
# handlers/gamification_user_handlers.py
with get_service(BroadcastService) as broadcast_service:
    result = await broadcast_service.process_channel_reaction(
        broadcast_id=..., user_id=..., emoji_id=...,
        username=..., bot=..., channel_id=..., message_id=...,
    )
```

**Markup parity contract (regression lock):**
- **Send:** `build_broadcast_send_markup` → `build_channel_reaction_markup(..., emoji_counts=None)`
- **Refresh (zero counts):** `build_channel_reaction_markup(..., emoji_counts={eid: 0 for eid, _ in entries})`
- **Structure must match:** row count, row order (reactions first, extra URL last), `callback_data` per reaction (`react:`), `url` on extra button
- **Text may differ:** only when refresh has `count > 0` → `f"{emoji} {count}"`

**`tracking_failed` → `message_mismatch` flow:**
```
persist_broadcast_from_state → create_broadcast_message(message_id=0)
  → send succeeds → update_broadcast_message_id fails → tracking_failed
  → row stays message_id=0
handle_reaction → check_and_register_reaction(channel_id, message_id=real TG id)
  → validate_broadcast_context_match: 0 ≠ real id → message_mismatch
```

---

## Constraints (NON-NEGOTIABLE)

1. **0 production code changes** — tests + docs + `decisions.md` only.
2. **0 behavior change** — do NOT relax `validate_broadcast_context_match` to accept `message_id=0`.
3. **Do NOT** implement `credit_besitos(commit=False)` — document DEFER only.
4. **Gold tests must pass** with mandated pytest flags after every task.
5. **GSD pre-log:** `.planning/quick/gsd-reaction-ecosystem-week2.log` before EVERY edit/ruff/pytest.
6. **Ruff:** `ruff check --fix` + `ruff format` on every touched file.

---

## Tasks (implementation order)

### Task 1: Markup parity golden test

**Objective:** Add regression lock asserting send vs refresh produce identical markup **structure**; text parity when all counts are zero.

**Files:**
- `tests/unit/test_broadcast_channel_markup.py` (EDIT — add 1–3 tests)

**Actions (exact):**
1. Add module-level or class helper `_markup_structure(markup)` per impact report:
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
   ```
2. Add `test_send_refresh_structure_parity_reactions_only`:
   - `entries = [(1, "💋"), (2, "❤️")]`
   - `send = build_channel_reaction_markup(bid, entries, emoji_counts=None)`
   - `refresh_zero = build_channel_reaction_markup(bid, entries, emoji_counts={1: 0, 2: 0})`
   - `assert _markup_structure(send) == _markup_structure(refresh_zero)`
   - Per-button text parity when counts all zero
3. Add `test_send_refresh_structure_parity_with_extra_button` (combined reactions + URL row)
4. Add `test_send_refresh_structure_parity_nine_emoji_chunking` (8+1 row split)
5. Add `test_refresh_with_positive_count_structure_same_text_differs`:
   - Structure equal between send and refresh with `{1: 3}`
   - Text on reaction button differs (`"💋"` vs `"💋 3"`)
6. **Do NOT** touch `keyboards/broadcast_channel_markup.py` — if parity fails, test documents regression; do not "fix" prod.

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_channel_markup.py
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK1 file=tests/unit/test_broadcast_channel_markup.py action=add_send_refresh_parity_golden
```

---

### Task 2: `message_id=0` → `message_mismatch` test

**Objective:** Document production failure mode when broadcast tracking fails (`tracking_failed`) and row stays at `message_id=0`.

**Files:**
- `tests/unit/test_broadcast_service_reaction_flow.py` (EDIT — add 1 test in `TestCheckAndRegisterReaction`)

**Actions (exact):**
1. Add `test_message_mismatch_when_broadcast_stuck_at_message_id_zero`:
   ```python
   async def test_message_mismatch_when_broadcast_stuck_at_message_id_zero(
       self, db_session, sample_user, sample_broadcast_message, sample_reaction_emoji, sample_free_channel
   ):
       """Simulates tracking_failed persistence: broadcast sent but message_id never updated."""
       sample_broadcast_message.message_id = 0  # tracking_failed left row at 0
       db_session.commit()
       service = BroadcastService(db_session)
       result = await service.check_and_register_reaction(
           broadcast_id=sample_broadcast_message.id,
           user_id=sample_user.telegram_id,
           emoji_id=sample_reaction_emoji.id,
           bot=AsyncMock(),
           channel_id=sample_free_channel.channel_id,
           message_id=1001,  # real TG message user clicked
       )
       assert result["success"] is False
       assert result["reason"] == "message_mismatch"
   ```
2. Assert **no** `BroadcastReaction` row created (optional but recommended).
3. Place adjacent to existing `test_message_mismatch_message_id_returns_structured_reason` (~L269).
4. **Do NOT** change `reaction_validators.py` — validator behavior is correct.

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_service_reaction_flow.py -k "message_mismatch"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_service_reaction_flow.py
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK2 file=tests/unit/test_broadcast_service_reaction_flow.py action=add_message_id_zero_mismatch_test
```

---

### Task 3: Migrate `test_reaction_full_chain.py` to `process_channel_reaction`

**Objective:** Replace pre-Week-1 manual handler mirror with production service orchestration.

**Files:**
- `tests/integration/test_reaction_full_chain.py` (EDIT)

**Actions (exact):**
1. In `test_reaction_advances_mission_and_updates_keyboard_counts` (~L180-216):
   - **Replace** `check_and_register_reaction` + manual count loop + `reactions_keyboard_with_counts` + `update_reaction_message` block with single call:
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
   - **Remove** lines 191-216 (manual keyboard rebuild + explicit `update_reaction_message`)
2. **Preserve** all downstream asserts:
   - `reaction_result["success"]` + `besitos_awarded == 2`
   - Reaction row in DB
   - Mission progress completed
   - `final_balance == 7` (2 reaction + 5 mission reward)
   - `mock_bot.edit_message_reply_markup.assert_awaited()` with correct `chat_id` / `message_id`
   - Markup contains count: assert `"💋 1"` or `"1"` in `call_args.kwargs` markup button text
3. **Remove** `from keyboards.inline_keyboards import reactions_keyboard_with_counts` if unused after migration.
4. In `test_multiple_reactions_update_counts_correctly` (~L303-326):
   - **Option A (preferred):** migrate both calls to `process_channel_reaction` with `channel_id` + `message_id` from broadcast; drop manual `reactions_keyboard_with_counts` build; assert `mock_bot.edit_message_reply_markup` called twice with count `"🔥 2"` on second call.
   - **Option B (minimal):** keep `check_and_register_reaction` for count-only test but remove dead `_markup = reactions_keyboard_with_counts(...)` line and import.
   - Executor chooses A unless integration flakiness; impact report prefers full migration.
5. Update module docstring: step 3 becomes "Post-reaction UI update via `process_channel_reaction` (service refresh)".

**Pattern to copy:** `tests/unit/test_broadcast_service_reaction_flow.py::TestProcessChannelReaction::test_success_calls_update_reaction_message_with_counts`

**Verification:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_reaction_full_chain.py
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK3 file=tests/integration/test_reaction_full_chain.py action=migrate_to_process_channel_reaction
```

---

### Task 4: Rewrite `services/broadcast/CLAUDE.md`

**Objective:** Replace stale reaction docs with real production paths (post-Week 1).

**Files:**
- `services/broadcast/CLAUDE.md` (EDIT)

**Actions (exact):**
1. **Replace** "Reacciones" section (L41-48) — remove `register_reaction` as primary API. Document:
   - `check_and_register_reaction(...) -> dict` — atomic register + credit + mission best-effort
   - `process_channel_reaction(...) -> dict` — production path: register + post-commit markup refresh
   - `has_user_reacted`, `get_reactions_by_broadcast`, stats helpers (keep)
   - `register_reaction` — **DEPRECATED** legacy sync; do not use in new code
2. **Replace** "Flujo de Broadcast" visitor section (L63-68) with:
   ```
   Visitante reacciona
     → handle_reaction (gamification_user_handlers.py)
     → get_service(BroadcastService) ×1
     → process_channel_reaction(broadcast_id, user_id, emoji_id, channel_id, message_id, bot, username)
         → check_and_register_reaction (validators → INSERT + credit + commit → missions best-effort)
         → on success: build_channel_reaction_markup + update_reaction_message (best-effort)
     → callback.answer from result dict (success / reason / besitos_awarded)
   ```
3. **Add** "Return dict contract" subsection:
   - Success: `{"success": True, "besitos_awarded": N, "id", "broadcast_id", "user_id", "emoji_id", "emoji_char"}`
   - Failure: `{"success": False, "reason": "<code>"}` — codes: `duplicate`, `invalid_broadcast`, `no_reactions`, `message_mismatch`, `invalid_emoji`, `inactive_emoji`, `emoji_not_allowed`, `credit_failed`, `error`
4. **Add** "Validators" subsection → `services/broadcast/reaction_validators.py` — 4 pure read-only functions; `validate_broadcast_context_match` guards channel_id + message_id (incl. `message_id=0` after `tracking_failed`)
5. **Add** "Markup" subsection → `keyboards/broadcast_channel_markup.py`:
   - Send: `build_broadcast_send_markup` / `emoji_counts=None`
   - Refresh: `build_channel_reaction_markup` with counts dict
   - Extra URL: `extra_button_id` on `BroadcastMessage` included in send + refresh
6. **Add** "Message ID tracking" operational note:
   - `create_broadcast_message(message_id=0)` then `update_broadcast_message_id` after TG send
   - If update fails → `tracking_failed`; admin alert; reactions blocked with `message_mismatch`
7. **Add** "Atomicity" note:
   - Reaction INSERT + credit in `check_and_register_reaction`; credit internal commit (split-tx by design, see decisions.md defer entry)
   - Mission delivery + markup refresh post-commit, best-effort
8. **Keep** existing EventBus section (L87-95) — still accurate; cross-reference Item 6.

**Verification:**
```bash
rg "process_channel_reaction|check_and_register_reaction|validate_broadcast|build_channel_reaction_markup|message_mismatch|tracking_failed" services/broadcast/CLAUDE.md
# Manual: no claim that register_reaction is production path
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK4 file=services/broadcast/CLAUDE.md action=rewrite_reaction_paths_and_contracts
```

---

### Task 5: `decisions.md` — DEFER `credit_besitos(commit=False)`

**Objective:** Close Week 2 spike evaluation with explicit deferral and rationale (no prod change).

**Files:**
- `decisions.md` (EDIT — append new `##` section)

**Actions (exact):**
1. Append section (after latest entry):
   ```markdown
   ## Reaction credit atomicity — defer `credit_besitos(commit=False)` (reaction-ecosystem-week2)

   **Motivo:** Week 2 evaluated unifying reaction INSERT + credit into single outer commit via `credit_besitos(..., commit=False)` (mirror `debit_besitos` precedent). Current path uses split-tx: credit's internal `db.commit()` then outer `db.commit()` for reaction row.

   **Riesgos (si se implementara):**
   - Atomicity gold breakage (`test_cross_service_atomicity.py` — "credit survives deliver False", 10+ scenarios)
   - EventBus `schedule_emit` timing change (expects post-credit-commit)
   - Scope creep to all `credit_besitos` callers (REACTION, DAILY, MISSION, GAME, ADMIN, story)

   **Decisión:** **DEFER** — split-tx is intentional per Item 6 (`decisions.md`); gold coverage protects integrity (`credit_failed` + rollback, UniqueConstraint duplicate guard). Revisit only on production orphan-row incident.

   **Resultado:** 0 prod change Week 2; atomicity golds unchanged; documented in impact report + this entry.

   **Refs:** `.grok/agent-memory/impact-analyzer/reaction-ecosystem-week2.md`, `.planning/quick/20260706-reaction-ecosystem-week2/PLAN.md`, `services/broadcast_service.py:440-460`, `test_cross_service_atomicity.py`, `test_broadcast_service_reaction_flow.py::test_credit_failure_rolls_back`
   ```
2. **Do NOT** modify `besito_service.py` or `check_and_register_reaction`.

**Verification:**
```bash
rg "defer.*credit_besitos|commit=False" decisions.md
```

**GSD pre-log:**
```
[$(date)] GSD_PRE TASK5 file=decisions.md action=defer_credit_besitos_commit_false_entry
```

**Self-check (append to log after full gate green):**
```
[$(date)] SELF_CHECK PASSED item=reaction-ecosystem-week2 all_golds_green scope=tests+docs+defer 0_prod_change 0_behavior_change
```

---

## Instrucciones para gsd-executor (MANDATORY)

1. **Lee este PLAN completo** + `@.grok/agent-memory/impact-analyzer/reaction-ecosystem-week2.md` antes de tocar código. No infieras scope de memoria.

2. **GSD pre-log antes de CADA edit/gate/ruff/pytest:**
   - Append a `.planning/quick/gsd-reaction-ecosystem-week2.log`
   - Formato: `[timestamp] GSD_PRE TASKn file=... action=...`
   - `wc -l` en el log después de cada append para confirmar crecimiento.
   - **Sin pre-log → sin edit.**

3. **Orden estricto:** Task 1 → 2 → 3 → 4 → 5. No saltar fases.

4. **0 prod edits guardrail:**
   - Si un test falla, **fix the test expectation only if prod behavior is correct** — never relax validators or change service code Week 2.
   - `git diff --name-only` antes del handoff: must NOT include `services/broadcast_service.py`, `besito_service.py`, `handlers/`, `keyboards/broadcast_channel_markup.py`, `reaction_validators.py`.

5. **Gold test patterns (copiar al pie de la letra):**

   **Markup parity helper:**
   ```python
   def _markup_structure(markup):
       return [
           [{"callback_data": btn.callback_data, "url": getattr(btn, "url", None)} for btn in row]
           for row in markup.inline_keyboard
       ]
   ```

   **message_id=0 mismatch (Task 2):**
   ```python
   sample_broadcast_message.message_id = 0
   db_session.commit()
   result = await service.check_and_register_reaction(
       ..., channel_id=sample_free_channel.channel_id, message_id=1001,
   )
   assert result["success"] is False
   assert result["reason"] == "message_mismatch"
   ```

   **process_channel_reaction migration (Task 3):**
   ```python
   reaction_result = await broadcast_service.process_channel_reaction(
       broadcast_id=broadcast_db_id, user_id=user_id, emoji_id=emoji1_id,
       username="testuser", bot=mock_bot,
       channel_id=broadcast_channel_id, message_id=broadcast_telegram_id,
   )
   assert reaction_result["success"] is True
   mock_bot.edit_message_reply_markup.assert_awaited()
   # Assert count in markup via call_args.kwargs["reply_markup"] or ["new_markup"] per mock path
   ```

   **TestSession / file DB (integration full_chain — keep existing pattern):**
   ```python
   engine, TestSession = self._create_engine_and_session(tmp_path)
   db = TestSession()
   # ... setup commits ...
   db.close()
   db = TestSession()  # fresh session before execution
   ```

   **patch schedule_emit (if needed in reaction_flow):**
   ```python
   with patch("services.besito_service.schedule_emit"):
       result = await service.check_and_register_reaction(...)
   ```

6. **Ruff:** `ruff check --fix` + `ruff format` on every touched file before pytest gate.

7. **Task 4 (docs):** Spanish/English mix OK (match existing CLAUDE.md style); accuracy > brevity; cite real file paths.

8. **Task 5:** Decision entry only — **no** `credit_besitos` signature change.

9. **Self-check PASSED** al final del log con confirmación: 0 prod files, golds green.

10. **Handoff post-success:** SUMMARY conciso en `.planning/quick/20260706-reaction-ecosystem-week2/SUMMARY.md` + confirmación golds green → arch-enforcer → test-guardian.

---

## Test Commands (exact flags — NON-NEGOTIABLE)

**Pytest flags (all commands):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts="
```

**Baseline (run before Task 1 edits):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "reaction or broadcast_service_reaction or cross_service_atomicity or broadcast_channel_markup"
```

**Per-task targeted:**

Task 1:
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_channel_markup.py
```

Task 2:
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_service_reaction_flow.py -k "message_mismatch"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_service_reaction_flow.py
```

Task 3:
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_reaction_full_chain.py
```

**Full reaction gold gate (run after Task 3 + final):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_channel_markup.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/unit/test_broadcast_service_reaction_flow.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_reaction_full_chain.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_cross_service_atomicity.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_invariants.py -k "reaction"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_reaction_mission_flow.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_reaction_limit.py
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/handlers/test_gamification_user_handlers.py -k "reaction"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/integration/test_callbackdata_broadcast.py
```

**Broader smoke (recommended final):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "reaction or broadcast_service_reaction or cross_service_atomicity or broadcast_channel_markup"
```

---

## Risks + Mitigation

| Risk | Level | Mitigation |
|------|-------|------------|
| Accidentally "fix" `message_id=0` by relaxing validator | 🔴 HIGH | Tests only; assert `message_mismatch`; grep prod diff empty |
| `test_reaction_full_chain` migration breaks mission/balance asserts | 🟡 MEDIUM | `process_channel_reaction` wraps same `check_and_register_reaction`; preserve all DB asserts |
| Parity test false positive (compares text not structure) | 🟢 LOW | `_markup_structure` excludes text; separate text assert |
| `credit_besitos(commit=False)` scope creep | 🔴 HIGH if implemented | **DEFER** — decisions.md only |
| Doc drift after rewrite | 🟢 LOW | Grep verify against frozen source files |
| **Overall Week 2** | 🟢 **LOW** | Scope locked: tests + docs + defer |

---

## Success Criteria (measurable)

- [ ] Send vs refresh markup: identical structure (callbacks, row order, extra URL); only count text differs when N>0
- [ ] Broadcast `message_id=0` → reaction returns `message_mismatch`
- [ ] `test_reaction_full_chain.py` primary test uses `process_channel_reaction` (no manual `reactions_keyboard_with_counts` rebuild)
- [ ] `services/broadcast/CLAUDE.md` documents `check_and_register_reaction`, `process_channel_reaction`, validators, markup, message_id validation, tracking_failed note
- [ ] `decisions.md` entry: DEFER `credit_besitos(commit=False)` with gold blast radius rationale
- [ ] All gold tests green with mandated pytest flags
- [ ] **0 production code changes** (`git diff` prod paths empty)
- [ ] GSD pre-logs for every edit; self-check PASSED in log
- [ ] Ruff clean on touched files

---

## Files Summary

**CREATE:**
- _(none)_

**EDIT:**
- `tests/unit/test_broadcast_channel_markup.py` — parity golden tests (Task 1)
- `tests/unit/test_broadcast_service_reaction_flow.py` — `message_id=0` test (Task 2)
- `tests/integration/test_reaction_full_chain.py` — migrate to `process_channel_reaction` (Task 3)
- `services/broadcast/CLAUDE.md` — rewrite reaction flow (Task 4)
- `decisions.md` — defer entry (Task 5)

**NOT TO EDIT:**
- `services/broadcast_service.py`
- `services/besito_service.py`
- `handlers/gamification_user_handlers.py`
- `handlers/broadcast_handlers.py`
- `keyboards/broadcast_channel_markup.py`
- `services/broadcast/reaction_validators.py`
- `keyboards/inline_keyboards.py` (deprecated shim stays)
- `bot.py`, `models/models.py`

**GSD log:** `.planning/quick/gsd-reaction-ecosystem-week2.log`

---

**Handoff:** Ready for `gsd-executor`. Lee PLAN completo + impact report antes de editar. GSD pre-log obligatorio.