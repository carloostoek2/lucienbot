# Arch Audit: broadcast-link-buttons-item2

**Verdict:** PASS
**Critical violations:** 0

**Item:** broadcast-link-buttons-item2 (ITEM 2 of 3 in broadcast-link-buttons pool)
**Effort:** 5
**Date:** 2026-06-23
**Auditor:** arch-enforcer (override Lucien)
**Protocol:** followed ~/.grok/agents/arch-enforcer.md + root CLAUDE.md (hardener workflow, 6-agent, pool phrase, 3 crits) + non-negotiable Lucien rules + PLAN/SUMMARY verbatim

## Scope Verified
- **Files touched (exactly as PLAN + SUMMARY + expected):**
  1. `handlers/broadcast_handlers.py` (states + ToggleExtra import + 4 pure extracts incl build_broadcast_send_markup/persist_*/preview/selection_keyboard + wizard steps ask/show/toggle/back + preview update + confirm refactored + step nums to de 7 + __future__/TYPE_CHECKING)
  2. `keyboards/callback_data.py` (ToggleExtraButtonCallback bc_extra)
  3. `services/broadcast_service.py` (create_broadcast_message sig + extra_button_id= param + store)
  4. `handlers/gamification_user_handlers.py` (refresh_reaction_markup_counts preserves extra via getattr+isinstance guard + manual row append; reactions_keyboard_with_counts untouched)
  5. `tests/unit/test_broadcast_service.py` (test_create..._accepts_extra_button_id)
  6. `tests/integration/test_callbackdata_broadcast.py` (bc_extra prefix test + collision update + TestBroadcastPureHelpers 4 tests import-inside)
  7. `tests/handlers/test_gamification_user_handlers.py` (mock extra=None + new test_refresh_preserves_extra_button_url_row)
- **Confirmed no scope creep:** searches across repo for new symbols (ToggleExtraButtonCallback, build_broadcast_send_markup, extra_button in wizard, etc.) hit ONLY listed files + tests. 0 admin handlers, 0 inline_keyboards, 0 bot.py, 0 other services, 0 models change (pre ITEM1), 0 reaction credit paths.
- **Out-of-scope locked:** NO default reactions (ITEM3), NO admin UI for buttons (gap documented), 0 >1 button, 0 impact on gamif reaction credit/atomicity/EventBus, reactions_keyboard_with_counts sig+body stable.

## Findings
### Critical (none)
- 0 critical violations of layers, get_service, DB outside models, duplication, >50 LOC (new/extracts), scope, 3 crits, atomicity golds, EventBus "MUST NOT mutate".
- Exactly 1 get_service(BroadcastService) per relevant broadcast entrypoint (confirm, preview, ask_for_extra, show_extra, reactions paths delegate); channel steps use ChannelService separately (pre-existing pattern, appropriate).
- No DB/models direct in handlers (only TYPE_CHECKING import for annotation; all via service calls).
- New/extracted pure helpers <=50 LOC + docstring "Función pura (sin estado ni side-effects).": build_broadcast_send_markup (34), persist_broadcast_from_state (18), build_broadcast_preview_text (28), build_extra_button_selection_keyboard (34), ask_for_extra_button (44), show_* (27/31), toggle (12).
- confirm_and_send_broadcast: 164 LOC (from ~174 pre, delta -10 <=0 per PLAN mandate; pre-existing debt acknowledged, extract succeeded).
- Naming: verb + context + result (build_*, persist_*, ask_for_*, show_*, toggle_*).
- Logging: follows existing patterns in error/success paths ("broadcast_handlers | action | ...", "broadcast_service | ..."); new paths covered in confirm/attach; service create_button had good format from ITEM1. Minor: create_broadcast_message log still old-style (pre-existing, not new code).
- Markup: build_broadcast_send_markup composes reactions row (if) + single extra URL row (if); single button enforced in UI (replace semantics, "ninguno" id=0 → None).
- Single choice: enforced (state sets/replaces; UI shows ✅ on chosen only; 0 or 1 always).
- "Ninguno" default: extra_button_id=None flows to create.
- Step numbering: "de 7" (extra Paso 4, protection 5) updated consistently in touched strings.
- Back nav wired correctly (mirrors existing).
- Scope: empty catalog auto-skip documented; no admin UI added.
- 0 files outside PLAN list.
- 0 impact on reaction paths: check_and_register_reaction, register_reaction, get_selected_emoji_ids etc. unchanged (read has_reactions/emoji_ids only; extra orthogonal). EventBus observers untouched.
- 3 crits protected: Gamification (reactions/besitos/daily/golds untouched), Narrative (none), Canales-VIP (none). Atomicity golds (cross, full_chain, invariants-k-reaction etc.) not affected in code (markup post-send best-effort).
- get_service contract: respected (1 per, no __init__ changes).
- Refresh: uses stable reactions_keyboard_with_counts + append; getattr(broadcast, "extra_button_id", None) + isinstance(int) for mock safety (no break on tests).
- build_send_reaction_markup untouched (compat for its test).

### Medium / Observations
- confirm_and_send_broadcast remains >50 LOC (164) — pre-existing violation reduced per PLAN; not introduced by ITEM2. Further split would be welcome in future but out of this tight scope.
- Logging not 100% uniform (e.g. final success "Broadcast enviado: ..." lacks full | user_id | ; create msg log legacy) — pre-existing style, new error paths use "broadcast_handlers | ..." format.
- In show_broadcast_preview / some paths: get_service(Broadcast) inside conditional (read-only for button info) — acceptable (1 total per entry), but could hoist for consistency if desired.
- No change to reactions_keyboard_with_counts (enforced).
- Admin UI gap for buttons still open (documented in code + SUMMARY; catalog usable via service).
- Ruff clean post (as per SUMMARY).

### Positive / Compliance Highlights
- Pure helper extraction + Test*PureHelpers pattern copied verbatim (import-inside, no patch on puros, 1:1 coverage of cases: reactions_only / extra_only / combined / none).
- Markup combine enforced: reactions first row (callbacks), extra second row (url only).
- GSD pre-logs: every edit/gate/test/ruff (planner log 50 lines + self-check PASSED with "all_golds_green ... scope_locked").
- All gold tests + new (per PLAN exact cmds) executed green (SUMMARY); 0 attributable regressions on reaction/atomicity paths.
- Tests reflect contracts: service create extra, cb prefix/collision, pure markup behaviors, refresh preserve (2 rows + url).
- Back/FSM/step wiring mirrors precedents.
- 0 behavior change outside broadcast wizard + markup best-effort.

## Compliance Checklist
- [x] Capas respetadas (handlers: exactly 1 get_service per entrypoint / no logic no DB; services: domain owner; models: data)
- [x] Scope del PLAN respetado (ITEM2 wizard+sig+markup+refresh+tests; locked)
- [x] Logging adecuado (existing + required format in critical paths)
- [x] Funcs <=50 (new/pures/ touched; confirm delta<=0)
- [x] Naming verb+context+result
- [x] get_service contract + 1 call/handler
- [x] 0 duplicación services
- [x] 0 DB fuera models
- [x] Markup combine + single button enforced
- [x] No default reactions / no admin UI
- [x] 0 impacto reaction credit / atomicity / EventBus (golds protected)
- [x] 3 critical systems protected (orthogonal)
- [x] GSD pre + self-check PASSED
- [x] Tests new + golds reflect contracts

## Handoff
**PASS 0 critical → test-guardian.**

Next: test-guardian (re-run exact gold suite from PLAN/SUMMARY + targeted new; confirm "suite protege adecuadamente"; no attributable regressions; coverage for puros + refresh + create).

**References (read during audit):**
- PLAN + SUMMARY: `.planning/quick/20260623-broadcast-link-buttons-item2/`
- Impact ITEM2: `.grok/agent-memory/impact-analyzer/broadcast-link-buttons-item2.md`
- Arch anterior (item1): `.grok/agent-memory/arch-enforcer/broadcast-link-buttons-item1.md` + its gsd log
- Test-guardian previo (item1): `.planning/quick/gsd-test-guardian-broadcast-link-buttons-item1.log` + report
- CLAUDEs: root, handlers/, services/, services/broadcast/, keyboards/ (implied)
- rules.md, architecture.md, AGENTS.md
- GSD planner log: `.planning/quick/gsd-planner-broadcast-link-buttons-item2.log` (50 lines)
- Code: broadcast_handlers.py (helpers 64-183, states 194, ask 642+, confirm 997+, LOC verified via inspect), service create 176+, callback_data 754+, gamif refresh 214+, tests as listed.
- Gold cmds / self-check in PLAN/SUMMARY

**Pool reminder:** Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

**Self-check for auditor:** All mandatory reads + pre-log appends before reads/writes done. Evidence-based. Strict but fair. 0 criticals. 
