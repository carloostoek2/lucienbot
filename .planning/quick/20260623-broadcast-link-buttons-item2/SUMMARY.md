# SUMMARY: broadcast-link-buttons-item2 (ITEM 2 of 3)

**Item:** broadcast-link-buttons-item2  
**Pool:** broadcast-default-reactions-and-extra-link-buttons  
**Effort:** 5  
**Role:** gsd-executor (hardener-agile)  
**Date:** 2026-06-23  
**Status:** COMPLETE — self-check PASSED

---

## Objective Delivered

Integrate selection of **at most 1** extra button (from catalog) into the broadcast wizard flow.

**In scope (ITEM 2 only):**
- UI in wizard: decision step + single-choice selection from active buttons (or "ninguno")
- Persist via `create_broadcast_message(..., extra_button_id=...)`
- Combined markup (reactions row + optional URL button row) in send + refresh counts
- Preview shows extra button info (label + url or none)
- 0 >1 button ever (single choice enforced in UI)
- Use `get_service(BroadcastService)`
- Paso insertion after reactions
- Extract pure helpers so confirm_and_send net delta LOC <=0
- All golds green, 0 regressions

**Out of scope (enforced):**
- NO default reactions (ITEM 3)
- NO admin UI for buttons (gap documented)
- reactions_keyboard_with_counts signature/body untouched

---

## Files Modified (scope lock verified)

Only these (per PLAN + impact):
1. `handlers/broadcast_handlers.py` — FSM states, ToggleExtraButtonCallback import, pure helpers (build_broadcast_send_markup, persist_broadcast_from_state, build_broadcast_preview_text, build_extra_button_selection_keyboard), wizard steps (ask_for_extra, show_..., toggle, continue, backs), preview update, confirm refactored to use helpers + extra, step numbers to "de 7", from __future__ + TYPE_CHECKING
2. `keyboards/callback_data.py` — ToggleExtraButtonCallback (bc_extra)
3. `services/broadcast_service.py` — create_broadcast_message(..., extra_button_id: int | None = None)
4. `handlers/gamification_user_handlers.py` — refresh_reaction_markup_counts preserves extra (uses reactions_keyboard + manual row append; getattr + isinstance guard for mocks)
5. `tests/unit/test_broadcast_service.py` — test_create..._accepts_extra_button_id
6. `tests/integration/test_callbackdata_broadcast.py` — bc_extra prefix/collision tests + TestBroadcastPureHelpers (4 tests, import-inside)
7. `tests/handlers/test_gamification_user_handlers.py` — mock extra_button_id=None + test_refresh_preserves_extra_button_url_row

No other files touched.

---

## Tasks Execution (exact order from PLAN)

### Task 1: Add FSM states + CallbackData + imports
- Pre-logged (multiple)
- Added waiting_extra_button_decision, selecting_extra_button after selecting_reactions
- Added ToggleExtraButtonCallback(prefix="bc_extra", button_id: int) after bc_protect
- Imported in broadcast_handlers
- Verified pack: bc_extra:0 / bc_extra:5 ; states present
- Prefix uniqueness checked

### Task 2: Extract pure helpers from confirm_and_send_broadcast
- Pre-logged before each edit
- Added build_broadcast_send_markup (31 LOC, "Función pura (sin estado ni side-effects).")
- Added persist_broadcast_from_state (20 LOC, delegates create with extra)
- Refactored confirm to use them + read extra_button_id; net LOC 166 (was 174, delta -8)
- build_send_reaction_markup untouched (for its test contract)
- Verified with inspect: helpers <=50, confirm reduced
- "Función pura..." docstring + verb+context+result naming

### Task 3: Add wizard flow steps (decision + single-choice + preview + back)
- Pre-logged
- Insertion after reactions (ask_for_extra_button called from reactions_selected/skip_reactions)
- ask_for_extra: loads via get_service, auto-skip if no active buttons (set None), shows decision keyboard
- show_extra_button_selection: single choice (replace), "⏭️ Ninguno" (id=0), ✅ prefix only on chosen, "✅ Continuar"
- toggle_extra: sets/replaces in state, re-renders
- extra_button_continue -> protection
- Back nav: broadcast_back_extra (decision->reactions, selection->decision); protection back prefers extra selection if buttons active
- Preview: reads extra_button_id, loads, shows "Botón extra: label (url)" or "❌"
- Step numbering: all updated to "de 7"; protection now "Paso 5 de 7", extra "Paso 4 de 7" (decision documented in SUMMARY)
- Extracted build_broadcast_preview_text + build_extra_button_selection_keyboard (puros) to keep show_* <=50 (preview 31, selection 27 after)
- All new wizard funcs + touched <=50 verified

### Task 4: Wire send integration (create signature + combined markup)
- Pre-logged
- Service: create_broadcast_message accepts extra_button_id=None, stores in model
- Persist (from T2) + confirm already pass it; load + build_broadcast_send_markup for combined (reactions or url or both) after create
- Markup attached post message_id update (edit)
- Smoke import + sig + handlers load PASS
- build_send_reaction_markup kept for compat

### Task 5: Update refresh in gamification_user_handlers to preserve extra button
- Pre-logged
- refresh: loads extra via getattr(broadcast, "extra_button_id", None) + isinstance(int) guard (mock safe)
- If emojis: reactions_keyboard_with_counts (stable) for row + append url row if extra → Inline
- Else if extra only: url row
- Never None when extra present; update called when markup
- reactions_keyboard_with_counts signature/body untouched
- Uses build? No — manual compose to preserve counts (build is plain for send)
- Verified: uses getattr, no direct call to reactions_ in extra path for build, sig stable

### Task 6: Tests + verifications (new + gold re-runs)
- Pre-logged before ruff/tests
- Ruff --fix + format on 4 files → clean (N814, F821, F841 auto-fixed + manual guards)
- New tests:
  - unit: test_create_broadcast_message_accepts_extra_button_id (with + default None)
  - callbackdata: test_bc_extra_unique_prefix; added to no-collision set (4 prefixes); test_no_... len==4
  - gamif handlers: updated mock extra=None; added test_refresh_preserves_extra_button_url_row (2 rows, url present)
  - TestBroadcastPureHelpers (4 tests, import-inside per pattern): reactions_only, extra_only, combined, none
- Exact test commands run (in order, project flags):
  - all golds + new (alembic, unit broadcast x2, cross atomicity, full_chain, invariants-k reaction, limit, mission_flow, callbackdata, gamif-k reaction, handlers-k broadcast)
- All 70+ baseline → post: full green (29 callbackdata, 27 gamif incl new, etc.)
- 0 attributable regressions
- Reacciones: full_chain + gamif reaction + invariants + limit + mission all green WITH extra button support (no break)
- Self-check appended

---

## Gold Tests & Contracts Protected

**Re-ran (all green):**
- test_alembic_heads
- test_broadcast_service + reaction_flow (incl new create extra test)
- cross_service_atomicity (gold)
- reaction_full_chain, invariants (reaction), reaction_limit, reaction_mission_flow
- callbackdata_broadcast (29p incl pures + bc_extra)
- gamification_user_handlers (-k reaction, 27p incl preserve test)
- handlers broadcast smoke (1p)

**Protected (0 impact):**
- check_and_register_reaction, register_reaction, credit paths untouched
- EventBus observers untouched
- Atomicity contracts (golds re-executed)
- 3 critical systems (gamif reactions/besitos/daily, narrative, channels-VIP) — no mutation
- get_service contract respected
- reactions_keyboard_with_counts signature + behavior for callers/tests unchanged
- build_send_reaction_markup contract for its test untouched

---

## Constraints & Rules Compliance

- ✅ GSD pre-log before EVERY edit/gate/ruff/test (log grew to 50 lines)
- ✅ Functions new/touched <=50 LOC (verified inspect; confirm pre-existing debt documented reduced)
- ✅ Naming: verb + context + result (build_broadcast_send_markup, persist_broadcast_from_state, ask_for_extra_button, etc.)
- ✅ Logging follows (existing + new in paths)
- ✅ get_service used (no __init__ changes)
- ✅ Single choice enforced in UI (0 or 1; select replaces; ninguno default)
- ✅ reactions_keyboard_with_counts untouched
- ✅ Admin UI gap documented only (no changes)
- ✅ "Ninguno" default → extra_button_id=None in create
- ✅ Step numbering: de 7 + explicit (protection 5, extra 4); all touched strings updated
- ✅ Back nav correct per mirrors
- ✅ Ruff clean
- ✅ 0 files outside list
- ✅ 0 behavior / 0 atomicity on protected

---

## Metrics / Evidence

- Log lines: 50 (pre-logs + self-check)
- New states: 2
- New cb: 1 (bc_extra)
- Pure helpers extracted: 4 (send markup, persist, preview text, selection keyboard)
- New tests: 1+2+1+4 = 8
- Gold suites re-executed: 11+ commands, all green
- confirm_and_send LOC: 166 (from 174)
- Wizard/pure/refresh LOCs all <=50 post split
- Re-runs: 0 regressions

---

## Deviations / Auto-fixes

- Minor: ruff F821 (BroadcastMessage forward) → __future__ + TYPE_CHECKING + quoted + noqa
- Minor: F841 (emoji_counts temp) + N814 (alias) auto by structure change
- Refresh logic: used reactions_keyboard + manual append (not build_send) to preserve counts on refresh (build_send is plain for initial send); aligns "manually" + "do not touch" + "counts" goal
- Step numbering: chose renumber total to 7 + shift protection (clearer than keeping 6); documented
- Unbound + MagicMock truthy attr: added isinstance(int) guard on extra_id (defensive, keeps mock tests passing without touching every mock)
- Append for pure test class: used terminal heredoc after repeated search_replace ws match fail (pre-logged; equivalent edit)

All within scope, no architecture change, 3 crit protected.

---

## Decisions (recorded)

1. Insertion: after reactions, before protection (as recommended).
2. Markup: keep build_send_reaction for compat/test; new build_broadcast_send for combined (plain emojis at send time); refresh composes with counts via stable keyboard + append.
3. Extract: 4 puros to satisfy <=50 on touched + confirm delta<=0.
4. Step nums: "Paso X de 7", protection=5, extra=4. Updated all touched strings.
5. Admin gap: only docs (service usable for manual catalog).
6. "Ninguno": id=0 → None in state/create.

---

## Handoff

**self-check PASSED**

All verifications per PLAN executed. All golds green (incl reacciones with extra button present). Scope 100% respected. 0 attributable regressions. 0 impact on 3 critical systems or atomicity/EventBus/get_service contracts.

Ready for arch-enforcer. Lee PLAN completo antes de editar.

---

**Pool status reminder (per hardener standard):** Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

**References:** 
- PLAN: `.planning/quick/20260623-broadcast-link-buttons-item2/PLAN.md`
- Impact: `.grok/agent-memory/impact-analyzer/broadcast-link-buttons-item2.md`
- ITEM1: `.planning/quick/20260623-broadcast-link-buttons-item1/PLAN.md` + SUMMARY
- GSD log: `.planning/quick/gsd-planner-broadcast-link-buttons-item2.log` (50 lines)
- This SUMMARY

**End of executor SUMMARY for broadcast-link-buttons-item2.**

## Self-Check: PASSED
