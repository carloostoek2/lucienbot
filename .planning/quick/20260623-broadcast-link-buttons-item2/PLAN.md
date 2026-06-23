# PLAN: Broadcast Link Buttons Wizard Integration (ITEM 2 of 3)

**Item:** broadcast-link-buttons-item2  
**Pool:** broadcast-default-reactions-and-extra-link-buttons  
**Effort:** 5  
**Type:** auto (hardener tight scope)  
**Date:** 2026-06-23  

---

## Objective

Integrate selection of **at most 1** extra button (from catalog pre-defined in ITEM 1) into the broadcast wizard flow.

**In scope (ITEM 2 only, locked):**
- UI in wizard: decision step + single-choice selection from active buttons (or "ninguno")
- Persist via `create_broadcast_message(..., extra_button_id=...)`
- Combined markup (reactions row + optional URL button row) in send + refresh counts
- Preview shows extra button info (label + url or none)
- 0 >1 button ever (single choice enforced in UI)
- **NO** default reactions (that's ITEM 3)
- Use `get_service(BroadcastService)` (already pattern in file)

**Out of scope (locked):**
- NO default reactions flip (ITEM 3)
- NO admin UI for creating/listing buttons (catalog already usable via service; document gap)
- NO >1 button support
- 0 behavior / 0 atomicity impact on protected contracts (reactions, credit, EventBus)

---

## Context (@refs)

**Mandatory reads (do before any edit):**
- `@.grok/agent-memory/impact-analyzer/broadcast-link-buttons-item2.md` (source of truth for scope, risks, tests, decisions)
- `@.planning/quick/20260623-broadcast-link-buttons-item1/PLAN.md` + `SUMMARY.md` (what ITEM 1 delivered)
- `@.grok/agent-memory/impact-analyzer/broadcast-link-buttons-item1.md`
- `@CLAUDE.md` (root) — hardener workflow, 6-agent sequence, pool phrase, 3 critical systems
- `@architecture.md` — layers (handlers → services → models)
- `@rules.md` — ≤50 LOC, verb+context+result, logging, 1 service per handler
- `@services/broadcast/CLAUDE.md` — BroadcastService owns emojis + reactions + now buttons; pattern for catalog
- `@handlers/CLAUDE.md` — 1-service via `get_service`, pure helpers for long wizard funcs, Test*PureHelpers
- `@services/CLAUDE.md` — get_service contract
- `@keyboards/callback_data.py` — broadcast section (bc_* prefixes)
- `@keyboards/inline_keyboards.py` — `reactions_keyboard_with_counts` (stable, used in integration tests)

**Key code to copy verbatim (patterns):**
- Emoji toggle selection in `broadcast_handlers.py:471-486` (`toggle_reaction_selection` + `show_reaction_selection`) — adapt for single choice (replace, not append)
- `build_send_reaction_markup` (handlers/broadcast_handlers.py:34-54) — extend or compose for URL row
- Pure helper pattern from `gamification_user_handlers.py:185-211` (`calculate_emoji_counts_from_reactions`, `reaction_failure_message`) and `handlers/mission_admin_handlers.py:78+` (docstring "Función pura (sin estado ni side-effects).")
- `Test*PureHelpers` pattern from `tests/handlers/test_mission_admin_handlers.py:1119+`, `test_store_admin_handlers.py:911+`
- `create_broadcast_message` call site (broadcast_handlers.py:727-738) — add `extra_button_id`
- `refresh_reaction_markup_counts` (gamification_user_handlers.py:214-236) — must read `broadcast.extra_button_id` and preserve URL row

**Gold tests that must stay green (no attributable regressions):**
- `tests/integration/test_cross_service_atomicity.py`
- `tests/integration/test_reaction_full_chain.py`
- `tests/integration/test_invariants.py` (-k "reaction")
- `tests/integration/test_reaction_limit.py`
- `tests/integration/test_reaction_mission_flow.py`
- `tests/unit/test_broadcast_service.py`
- `tests/unit/test_broadcast_service_reaction_flow.py`
- `tests/integration/test_alembic_heads.py`
- `tests/integration/test_callbackdata_broadcast.py` (markup test imports `build_send_reaction_markup`)
- `tests/handlers/test_gamification_user_handlers.py` (-k "reaction or Reaction")

**Pre-flight commands (run before touching code):**
See "Test Commands" section below.

---

## Constraints (NON-NEGOTIABLE)

1. **0 impact on 3 critical systems:** Gamification (besitos + REACTIONS + daily), Narrative, Channels/VIP. ITEM 2 touches only broadcast wizard + markup (post-send best-effort). `check_and_register_reaction`, credit paths, EventBus observers remain untouched.
2. **Scope locked to ITEM 2:** Wizard UI (states + callbacks + selection), `create_broadcast_message` signature + persist, combined markup in send + refresh, preview. NOTHING else.
3. **BroadcastService owns the domain:** NO new service. Use existing `get_all_buttons`, `get_broadcast_button`.
4. **Function limit ≤50 LOC:** `confirm_and_send_broadcast` is **174 LOC** (pre-existing violation). MUST extract pure helpers (e.g., `build_final_send_markup`, `persist_broadcast_record`) so net growth is zero or negative. New helpers ≤50 LOC. Verify with `inspect.getsourcelines` or `wc -l`.
5. **Naming:** `verb + context + result` (e.g., `build_broadcast_send_markup`, `persist_broadcast_from_state`).
6. **Logging:** `"broadcast_handlers | action | user_id=... | ..."` or `"broadcast_service | ..."` for service calls.
7. **get_service contract:** Already used in broadcast_handlers. No `__init__` changes.
8. **Single choice enforcement:** UI must allow 0 or 1 button. Selecting one replaces any prior. "Ninguno" (default) = no extra button.
9. **reactions_keyboard_with_counts stays stable:** This function is called directly by integration tests (full_chain). Do NOT change its signature. Create a new helper for combined markup (reactions + URL row).
10. **Admin config gap:** Document only. NO admin UI added in ITEM 2. To use feature, buttons must exist via `BroadcastService.create_broadcast_button` (or future admin slice). If catalog empty, selection shows "ninguno" only.
11. **Step numbering:** Decide insertion point (after reactions recommended) and how to handle "Paso X de 6". Options: renumber to "7", keep "6" and accept "Paso X", or use "Paso X" without total. Document decision.
12. **Back navigation:** New states require correct `broadcast_back_*` wiring. Preview back should go to extra button step (if was shown) or protection.
13. **"Ninguno" default:** If user never enters selection or picks "ninguno", `extra_button_id=None` in create.

---

## Decisions (to be confirmed in execution; record in SUMMARY)

1. **Insertion point:** After reactions, before protection (recommended by impact). New states:
   - `waiting_extra_button_decision`
   - `selecting_extra_button`
   Flow: ... → reactions_selected/skip → ask_for_extra_button → ... → ask_for_protection → preview.

2. **Markup helper strategy:** 
   - Keep `build_send_reaction_markup` (pure, used by tests) for reaction row only.
   - Create `build_broadcast_send_markup(broadcast_id, selected_emoji_ids, extra_button)` (or similar) that composes: reactions row (if any) + URL row (if extra).
   - In `refresh_reaction_markup_counts`, if `broadcast.extra_button_id`, load button and build combined markup manually (do not touch `reactions_keyboard_with_counts`).

3. **Extract from `confirm_and_send_broadcast`:** At minimum:
   - `build_final_reply_markup(selected_emojis: list[int], extra_button: BroadcastButton | None, get_emoji, broadcast_id: int) -> InlineKeyboardMarkup | None`
   - `persist_broadcast_record(data: dict, admin_id: int, broadcast_service) -> BroadcastMessage`
   These reduce the 174 LOC monster and keep delta ≤0 for this function.

4. **Admin UI:** Gap documented. No changes to gamification_admin_handlers.py or new admin files in ITEM 2.

5. **Service extension:** Add `extra_button_id: int | None = None` to `create_broadcast_message`. No new getter required (use `get_broadcast().extra_button_id` or `get_broadcast_button(broadcast.extra_button_id)`). Optional: add `get_extra_button_for_broadcast(broadcast_id)` for symmetry with `get_selected_emoji_ids` — decide during impl (low priority).

6. **CallbackData prefix:** Use `bc_extra` or `bc_button`. Verify no collision in `TestBroadcastCallbacksNoCollisions`.

---

## Tasks

### Task 1: Add FSM states + CallbackData + imports

**Objective:** Define new states for extra button decision/selection and the callback(s) to drive single-choice UI.

**Files:**
- `handlers/broadcast_handlers.py`
- `keyboards/callback_data.py`

**Actions (exact):**
1. In `BroadcastStates` (after `selecting_reactions`, before `waiting_protection_decision`):
   ```python
   waiting_extra_button_decision = State()
   selecting_extra_button = State()
   ```
2. In `keyboards/callback_data.py` (BROADCAST section), add:
   ```python
   class ToggleExtraButtonCallback(CallbackData, prefix="bc_extra"):
       """Toggle selección de botón extra (single choice: 0 = ninguno)"""
       button_id: int  # 0 means "ninguno"
   ```
3. Import `ToggleExtraButtonCallback` in broadcast_handlers.py.
4. Add import for `BroadcastButton` type if needed for annotations (or use `Any` / late import).
5. Verify prefix uniqueness: `bc_extra` not colliding with `bc_channel`, `bc_reaction`, `bc_protect`.

**Verification:**
```bash
python -c "
from keyboards.callback_data import ToggleExtraButtonCallback
cb = ToggleExtraButtonCallback(button_id=0)
print('ninguno:', cb.pack())
cb2 = ToggleExtraButtonCallback(button_id=5)
print('btn5:', cb2.pack())
print('prefix ok')
"
```

**GSD pre-log:** Before editing:
```
[$(date)] GSD_PRE TASK1 states_callbacks file=handlers/broadcast_handlers.py,keyboard/callback_data.py action=add_extra_button_states_and_cb
```

---

### Task 2: Extract pure helpers from confirm_and_send_broadcast (fix long func)

**Objective:** Reduce `confirm_and_send_broadcast` (174 LOC) by extracting pure/stateless helpers for markup building and persist. Net LOC of this function must not grow.

**File:**
- `handlers/broadcast_handlers.py`

**Actions (exact):**
1. Create pure helper (before or after `build_send_reaction_markup`):
   ```python
   def build_broadcast_send_markup(
       broadcast_id: int,
       selected_emoji_ids: list[int],
       extra_button,  # BroadcastButton | None
       get_emoji,
   ) -> InlineKeyboardMarkup | None:
       """Construye markup combinado: reacciones (si hay) + botón URL extra (si hay). Función pura."""
       from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
       from keyboards.callback_data import ReactionCallback
       rows = []
       # reactions row
       if selected_emoji_ids:
           reaction_row = []
           for eid in selected_emoji_ids:
               em = get_emoji(eid)
               if em:
                   reaction_row.append(
                       InlineKeyboardButton(
                           text=em.emoji,
                           callback_data=ReactionCallback(broadcast_id=broadcast_id, emoji_id=em.id).pack(),
                       )
                   )
           if reaction_row:
               rows.append(reaction_row)
       # extra button row
       if extra_button:
           rows.append([InlineKeyboardButton(text=extra_button.label, url=extra_button.url)])
       if not rows:
           return None
       return InlineKeyboardMarkup(inline_keyboard=rows)
   ```
   - Docstring: `"Función pura (sin estado ni side-effects)."`
   - ≤50 LOC (target ~25-30).

2. Create thin persist helper (can call service; not strictly pure but delegates):
   ```python
   def persist_broadcast_from_state(
       data: dict, admin_id: int, broadcast_service
   ) -> "BroadcastMessage":
       """Persiste BroadcastMessage desde estado FSM + extra_button_id. Delega a servicio."""
       selected_emojis = data.get("selected_emojis", [])
       extra_button_id = data.get("extra_button_id")
       selected_emoji_ids_str = ",".join(str(eid) for eid in selected_emojis)
       return broadcast_service.create_broadcast_message(
           message_id=0,
           channel_id=data.get("channel_id"),
           admin_id=admin_id,
           text=data.get("text", ""),
           has_attachment=data.get("has_attachment", False),
           attachment_type=data.get("attachment_type"),
           attachment_file_id=data.get("attachment_file_id"),
           has_reactions=len(selected_emojis) > 0,
           is_protected=data.get("is_protected", False),
           selected_emoji_ids=selected_emoji_ids_str,
           extra_button_id=extra_button_id,
       )
   ```
   - Note: service call is inside; this is a thin delegate to keep confirm_and_send short.

3. Refactor `confirm_and_send_broadcast`:
   - Replace inline create + markup build with calls to the two helpers.
   - The function body should shrink or stay same net (extract ≥ lines added for extra button logic).
   - Verify final LOC of `confirm_and_send_broadcast` ≤ original (174) and ideally closer to 50 or documented as known debt if split not complete.

4. Keep `build_send_reaction_markup` for backward compat with existing test (`test_build_send_reaction_markup_uses_reaction_callback`). It can stay as-is (reactions only) or become a thin wrapper; do not break its contract.

**Verification (after edit):**
```bash
python -c "
import inspect
from handlers.broadcast_handlers import build_broadcast_send_markup, persist_broadcast_from_state, confirm_and_send_broadcast
print('build_broadcast_send_markup LOC:', len(inspect.getsourcelines(build_broadcast_send_markup)[0]))
print('persist_broadcast_from_state LOC:', len(inspect.getsourcelines(persist_broadcast_from_state)[0]))
print('confirm_and_send_broadcast LOC:', len(inspect.getsourcelines(confirm_and_send_broadcast)[0]))
"
```

**GSD pre-log:** Before editing broadcast_handlers.py for extraction:
```
[$(date)] GSD_PRE TASK2 extract_pure_helpers file=handlers/broadcast_handlers.py action=extract_build_broadcast_send_markup_and_persist
```

---

### Task 3: Add wizard flow steps (decision + single-choice selection + preview)

**Objective:** Insert extra button step(s) after reactions, update preview, wire back navigation.

**File:**
- `handlers/broadcast_handlers.py`

**Actions (exact):**
1. After `reactions_selected` / `skip_reactions` paths, call new `ask_for_extra_button(target, state)`.
2. Implement `ask_for_extra_button(target, state)`:
   - Load active buttons via `with get_service(BroadcastService) as svc: buttons = svc.get_all_buttons(active_only=True)`
   - If no buttons: auto-skip (set `extra_button_id=None`) and proceed to protection.
   - Render decision keyboard: "🔗 Agregar botón de enlace" / "⏭️ Sin botón extra" + back + cancel.
   - Set state `waiting_extra_button_decision`.
   - Step text: "📋 **Paso X:** Botón extra" (decide numbering; recommend "Paso 4 de 7" or just "Paso 4: Botón extra").
3. On "yes" → `show_extra_button_selection(callback, state)`:
   - List buttons as single-choice toggles using `ToggleExtraButtonCallback(button_id=btn.id)`.
   - Add "⏭️ Ninguno" as `ToggleExtraButtonCallback(button_id=0)`.
   - "✅ Continuar" only enabled if state has 0 or 1 selected (always true for single choice).
   - Selecting a real button sets `selected_extra_button_id = button_id` and clears any prior (replace semantics).
   - Selecting 0 sets `None`.
   - UI shows "✅ " prefix on the chosen one only (like emoji but exclusive).
4. On "reactions_selected" with extra path or "extra_button_selected" → `ask_for_protection`.
5. Update `show_broadcast_preview`:
   - Read `extra_button_id = data.get("extra_button_id")`
   - If set: load via service `button = broadcast_service.get_broadcast_button(extra_button_id)`; show `f"   • Botón extra: {button.label} ({button.url})"`
   - Else: `   • Botón extra: ❌`
   - Keep preview ≤50 LOC or extract a pure `build_preview_text(data, extra_button)` if needed.
6. Wire back nav:
   - `broadcast_back_extra` from extra decision → back to reactions decision/selection (mirror `back_from_protection` logic).
   - From protection back: if extra was shown, go to extra selection; else reactions.
   - Update preview back: go to protection (or extra if we want deeper back).
7. Update step numbers consistently in all text blocks touched (or decide to use "Paso X" without total and document).

**Single choice enforcement (UI):**
- `toggle_extra_button_selection` callback:
  ```python
  button_id = callback_data.button_id
  if button_id == 0:
      await state.update_data(extra_button_id=None)
  else:
      await state.update_data(extra_button_id=button_id)
  await show_extra_button_selection(callback, state)
  ```
- No multi-select list; always exactly one or zero.

**Verification (manual or via test later):**
- Empty catalog → auto-skip to protection.
- One button → selecting it shows ✅ and preview includes it.
- "Ninguno" → extra_button_id=None.

**GSD pre-log:** Before adding wizard methods:
```
[$(date)] GSD_PRE TASK3 wizard_flow file=handlers/broadcast_handlers.py action=add_ask_for_extra_button_show_selection
```

---

### Task 4: Wire send integration (create signature + combined markup)

**Objective:** Pass `extra_button_id` to create, build combined markup on send, attach after message_id update.

**File:**
- `handlers/broadcast_handlers.py`

**Actions (exact):**
1. In `confirm_and_send_broadcast`:
   - Read `extra_button_id = data.get("extra_button_id")`
   - Pass to `persist_broadcast_from_state` or directly to `create_broadcast_message(..., extra_button_id=extra_button_id)`
2. After `create`, load extra button if id:
   ```python
   extra_button = None
   if extra_button_id:
       extra_button = broadcast_service.get_broadcast_button(extra_button_id)
   ```
3. Build markup:
   ```python
   reaction_markup = build_broadcast_send_markup(
       broadcast.id,
       selected_emojis,
       extra_button,
       broadcast_service.get_reaction_emoji,
   )
   ```
   - Note: this replaces the old `build_send_reaction_markup` call for the final markup.
   - `build_send_reaction_markup` remains for its test; we can keep using it internally if we want, but combined is authoritative for send.
4. The rest of send flow unchanged (send without markup, update message_id, edit with final markup).
5. Success message can optionally mention "Botón extra: Sí/No".

**Signature change (service):**
- In `services/broadcast_service.py`:
  ```python
  def create_broadcast_message(
      ...
      selected_emoji_ids: str = None,
      extra_button_id: int = None,  # NEW
  ) -> BroadcastMessage:
      ...
      broadcast = BroadcastMessage(
          ...
          selected_emoji_ids=selected_emoji_ids,
          extra_button_id=extra_button_id,  # NEW
      )
  ```

**Verification:**
- Smoke via python (after wiring) or via handler tests later.

**GSD pre-log:** Before editing send path and service signature:
```
[$(date)] GSD_PRE TASK4 send_integration file=handlers/broadcast_handlers.py,services/broadcast_service.py action=pass_extra_button_id_build_combined_markup
```

---

### Task 5: Update refresh in gamification_user_handlers to preserve extra button

**Objective:** When reactions are clicked and counts refreshed, preserve the extra URL button row if `broadcast.extra_button_id` is set.

**File:**
- `handlers/gamification_user_handlers.py`

**Actions (exact):**
1. In `refresh_reaction_markup_counts`:
   - After building reaction emojis:
   ```python
   extra_button = None
   if getattr(broadcast, "extra_button_id", None):
       extra_button = broadcast_service.get_broadcast_button(broadcast.extra_button_id)
   ```
   - Build combined markup:
     ```python
     if emojis:
         from handlers.broadcast_handlers import build_broadcast_send_markup
         new_markup = build_broadcast_send_markup(
             broadcast_id, [eid for eid, _ in emojis], extra_button, broadcast_service.get_reaction_emoji
         )
     else:
         # only extra button row
         if extra_button:
             from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
             new_markup = InlineKeyboardMarkup(inline_keyboard=[[
                 InlineKeyboardButton(text=extra_button.label, url=extra_button.url)
             ]])
         else:
             new_markup = None
     ```
   - Call `update_reaction_message` with this markup (same as before).
2. **Important:** Do NOT modify `reactions_keyboard_with_counts` signature or body. It stays for tests that call it directly.
3. Ensure the function still works when `extra_button_id` is None (current behavior).
4. Handle the case where `broadcast` passed in may be a MagicMock in tests: use `getattr(broadcast, "extra_button_id", None)` defensively.

**Verification:**
- Existing `test_updates_reaction_counts` must still pass (mock will have no `extra_button_id` or we update mock to include `extra_button_id=None`).
- New test will cover "has extra_button_id → markup has URL row".

**GSD pre-log:** Before editing refresh:
```
[$(date)] GSD_PRE TASK5 refresh_extra file=handlers/gamification_user_handlers.py action=preserve_extra_button_on_count_refresh
```

---

### Task 6: Tests + verifications (new + gold re-runs)

**Objective:** Add minimal coverage for the new paths; re-run all golds; ruff clean.

**Files:**
- `tests/integration/test_callbackdata_broadcast.py` (update collision test, markup test if needed)
- `tests/handlers/test_gamification_user_handlers.py` (update mocks for extra_button_id; add test for refresh with extra)
- `tests/unit/test_broadcast_service.py` (light test for create with extra_button_id)
- (Optional) new integration or handler-level smoke for wizard flow if harness allows; otherwise unit the pure helpers.

**New tests (minimum):**
1. `tests/unit/test_broadcast_service.py`:
   - `test_create_broadcast_message_accepts_extra_button_id` — create with `extra_button_id=5`, assert stored; create without (default None), assert None.
2. `tests/integration/test_callbackdata_broadcast.py`:
   - `test_bc_extra_unique_prefix` — `ToggleExtraButtonCallback(button_id=0).pack().startswith("bc_extra:")`
   - `test_no_prefix_collision_with_bc_extra` — add to the no-collision set.
   - If `build_broadcast_send_markup` is public or we want to test its output, add a test that it produces ReactionCallbacks for emojis + a URL button when extra provided. If kept internal, skip or test via import.
3. `tests/handlers/test_gamification_user_handlers.py`:
   - Update `test_updates_reaction_counts` mock: add `extra_button_id=None` to the MagicMock or use `hasattr` guard in code.
   - Add `test_refresh_preserves_extra_button_url_row`: mock `get_broadcast` with `extra_button_id=7`, `get_broadcast_button(7)` returns button with label/url; assert final markup has a button with `url` (not callback_data) or second row.
4. Pure helper tests (new class at end of appropriate test file or new file):
   - `TestBroadcastPureHelpers`:
     - `test_build_broadcast_send_markup_reactions_only` — emojis in, URL row absent.
     - `test_build_broadcast_send_markup_extra_only` — no emojis, extra button → single row with url.
     - `test_build_broadcast_send_markup_combined` — both rows.
     - `test_build_broadcast_send_markup_none` — empty → None.
   - Import inside tests (per pattern): `from handlers.broadcast_handlers import build_broadcast_send_markup`.

**Exact test commands (post-changes, in order):**
```bash
# Pre-flight (baseline, same as ITEM1 + ITEM2 prep)
pytest tests/integration/test_alembic_heads.py tests/unit/test_broadcast_service.py tests/unit/test_broadcast_service_reaction_flow.py tests/integration/test_cross_service_atomicity.py tests/integration/test_reaction_full_chain.py tests/integration/test_invariants.py -v --tb=line -q -p no:cov --override-ini="addopts="

# Per-task quick
pytest tests/unit/test_broadcast_service.py::TestBroadcastButton -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_callbackdata_broadcast.py -q --tb=line -p no:cov --override-ini="addopts="

# Post full suite (exact order from impact)
pytest tests/integration/test_alembic_heads.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/unit/test_broadcast_service.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_cross_service_atomicity.py -q -k "cross_service_atomicity or TestCrossServiceAtomicity" --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_full_chain.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_invariants.py -q -k "reaction" --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_mission_flow.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_callbackdata_broadcast.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/handlers/test_gamification_user_handlers.py -q -k "reaction or Reaction" --tb=line -p no:cov --override-ini="addopts="
pytest tests/handlers/ -q -k "broadcast" --tb=line -p no:cov --override-ini="addopts=" 2>/dev/null || echo "No dedicated broadcast handler tests (smoke only)"
```

**Ruff + format (after all edits):**
```bash
ruff check --fix handlers/broadcast_handlers.py handlers/gamification_user_handlers.py services/broadcast_service.py keyboards/callback_data.py
ruff format handlers/broadcast_handlers.py handlers/gamification_user_handlers.py services/broadcast_service.py keyboards/callback_data.py
```

**GSD pre-log:** Before running final verification:
```
[$(date)] GSD_PRE TASK6 tests_verification action=full_gold_suite_plus_new_tests
```

**Self-check at end of Task 6:** Executor must append:
```
[$(date)] SELF_CHECK PASSED item=broadcast-link-buttons-item2 all_golds_green markup_has_0_or_1_button preview_correct create_stores_extra refresh_preserves_extra ruff_clean 0_regressions scope_locked
```

---

## Instrucciones para gsd-executor (MANDATORY)

1. **Read this PLAN completely** before touching any file. Re-read impact + CLAUDEs if unsure. Do not infer scope from memory.

2. **GSD pre-log before EVERY edit/gate/ruff/test:**
   - Append line to `.planning/quick/gsd-planner-broadcast-link-buttons-item2.log` with timestamp, phase, file, action.
   - `wc -l` after each append.
   - No edit without preceding pre-log.

3. **Copy patterns at the letter:**
   - Single choice selection: adapt emoji toggle but replace (not append). "✅ " only on chosen, "⬜ " on others + "⏭️ Ninguno".
   - Pure helpers: docstring `"Función pura (sin estado ni side-effects)."`; stateless; import-inside in their tests; `Test*PureHelpers` class at end.
   - `get_service(BroadcastService)` already used; keep 1-service per handler entrypoint.
   - `reactions_keyboard_with_counts` signature unchanged.

4. **Function size:** If after extraction any function >50 LOC that you touched, split further or document as pre-existing debt. Verify with `inspect` or `wc`.

5. **Ruff:** Run `ruff check --fix` + `ruff format` on touched files after edits, before tests.

6. **Do not touch admin handlers for buttons:** If tempted, STOP. Log and skip. Gap is documented.

7. **Back nav correctness:** Every new state must have a back path that lands on a prior valid state with correct text/step.

8. **"Ninguno" default:** If user skips or picks 0, `extra_button_id` must be absent/None in create.

9. **Self-check PASSED:** At very end (after Task 6), append the self-check line with scope confirmation.

10. **Handoff:** After completion, final message: `"Ready for arch-enforcer. Lee PLAN completo antes de editar."`

---

## Test Commands (exact)

**Baseline (before any change in session):**
```bash
pytest tests/integration/test_alembic_heads.py tests/unit/test_broadcast_service.py tests/unit/test_broadcast_service_reaction_flow.py tests/integration/test_cross_service_atomicity.py tests/integration/test_reaction_full_chain.py tests/integration/test_invariants.py -v --tb=line -q -p no:cov --override-ini="addopts="
```

**Project flags (always use for gold runs):**
- `-q --tb=line -p no:cov --override-ini="addopts="`

**Per-task verifications:** See each Task section.

**Full post-implementation suite:** See Task 6.

---

## Risks + Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `confirm_and_send_broadcast` grows beyond 174 LOC | High | High (rule violation) | Extract at least 2 helpers (Task 2) before adding extra logic; verify LOC delta ≤0. |
| Back nav broken (new states) | Medium | Medium (UX broken) | Mirror existing back patterns exactly; test manually or via state machine smoke. |
| Step numbering confusion ("Paso X de 6") | Medium | Low | Decide explicitly (renumber / keep 6 / drop total); document in SUMMARY. |
| `reactions_keyboard_with_counts` accidentally mutated | Low | High (integration tests) | Never edit its body/signature; build combined markup separately. |
| Empty catalog → dead selection step | Low | Low | Auto-skip if `get_all_buttons(active_only=True)` is empty. |
| Admin gap (no UI to create buttons) | Certain | Medium (feature unusable until buttons exist) | Document in code + SUMMARY + impact follow-up. Catalog is service-usable. |
| Callback prefix collision | Low | Medium | Add `bc_extra` to collision test; assert uniqueness. |
| Atomicity gold impact | Very Low | Critical | ITEM 2 does not touch `check_and_register_reaction` or credit paths. Re-run golds explicitly. |
| Markup with URL button breaks ReactionCallback parsing | Low | High | ReactionCallbacks are on first row; URL buttons have no callback_data. Test `test_reaction_callback_still_works_with_combined_markup`. |

---

## Success Criteria (measurable)

1. FSM has `waiting_extra_button_decision` and `selecting_extra_button`; wizard inserts after reactions.
2. `ToggleExtraButtonCallback` exists with prefix `bc_extra`; no prefix collision with other bc_*.
3. `build_broadcast_send_markup` (pure) and `persist_broadcast_from_state` exist; `confirm_and_send_broadcast` LOC ≤174 (ideally reduced).
4. `create_broadcast_message` accepts `extra_button_id: int | None = None` and stores it.
5. Preview shows "Botón extra: label (url)" or "❌".
6. Send attaches combined markup (reactions row + optional URL row) via edit after message_id update.
7. `refresh_reaction_markup_counts` preserves extra button row when `broadcast.extra_button_id` is set; does not modify `reactions_keyboard_with_counts`.
8. Single choice enforced in UI (0 or 1; selecting replaces).
9. All gold tests pass with exact flags; 0 attributable regressions.
10. New tests cover: create with extra, callback prefix, pure markup helper (0/1 button cases), refresh preserves extra.
11. `ruff check --fix` + `ruff format` clean on touched files.
12. GSD pre-logs present for every edit (log line count increased).
13. Self-check PASSED appended with scope confirmation.
14. No files outside task list modified (handlers/broadcast, handlers/gamif_user, service, callback_data; tests as listed).
15. "Ready for arch-enforcer. Lee PLAN completo antes de editar."

---

## Scope Lock Reminder

This PLAN is for **ITEM 2 only**. ITEM 3 is default reactions. Do not start those here. Admin UI for buttons is a separate future item.

---

**End of PLAN.** Executor: read this fully, pre-log every step, copy patterns, protect the 3 critical systems, deliver clean. "Lee PLAN completo antes de editar."
