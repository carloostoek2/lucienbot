# 🛡️ Test-Guardian Report: broadcast-link-buttons-item2

**Item:** broadcast-link-buttons-item2 (ITEM 2 of 3)
**Pool:** broadcast-default-reactions-and-extra-link-buttons
**Effort:** 5
**Role:** test-guardian (hardener-agile)
**Date:** 2026-06-23
**Verdict:** **SUITE PROTEGE ADECUADAMENTE**

---

## Executive Summary

ITEM 2 (wizard integration for at most 1 extra link button) was implemented with **zero impact** on the 3 critical systems (gamification reactions/besitos, narrative, channels-VIP) and **zero mutation** of atomicity contracts / EventBus paths / get_service contract.

- **New tests added:** 8 (create extra + bc_extra prefix/collision update + 4 pure helpers + refresh preserve)
- **Gold suites re-executed:** 11+ commands per PLAN Task 6 — all green
- **Baseline combined suite:** ~71 passed (post; increased from item1 due to new coverage)
- **0 attributable regressions**
- **Reactions continue to work with extra button in markup** — ReactionCallbacks remain on row 0; URL row appended as row 1 (no callback_data)
- **Single choice enforced** — pure markup cases + UI replace semantics (0 or 1); "ninguno" (id=0) → None
- **reactions_keyboard_with_counts** signature/body untouched (stable for counts + integration tests)
- **Nullable FK inert** — existing BroadcastMessage fixtures continue to work

---

## Coverage Audit

### New Code Coverage (ITEM 2 contracts)

| Area | Test | Status |
|------|------|--------|
| Service create with extra | `test_create_broadcast_message_accepts_extra_button_id` | ✅ (with id + default None) |
| Callback prefix | `test_bc_extra_unique_prefix` | ✅ `bc_extra:` |
| No collision | `test_no_prefix_collision_between_broadcasts` | ✅ len==4 (incl bc_extra) |
| Pure: reactions only | `test_build_broadcast_send_markup_reactions_only` | ✅ 1 row, react: prefix, no url |
| Pure: extra only | `test_build_broadcast_send_markup_extra_only` | ✅ 1 row, url only, no cb |
| Pure: combined | `test_build_broadcast_send_markup_combined` | ✅ 2 rows: react row0 + url row1 |
| Pure: none | `test_build_broadcast_send_markup_none` | ✅ None |
| Refresh preserve extra | `test_refresh_preserves_extra_button_url_row` | ✅ 2 rows when extra; url present; reaction row via stable keyboard |
| Single choice (markup/UI) | covered by pure combined/extra_only + replace semantics in toggle | ✅ at most 1 url row; 0 or 1 enforced |

**Pure helpers:** import-inside per pattern; `TestBroadcastPureHelpers` class; docstring "Función pura (sin estado ni side-effects)."; all <=50 LOC.

**Existing golds remain meaningful:**
- Fixtures create without `extra_button_id` (nullable) — all gold tests using BroadcastMessage passed.
- `reactions_keyboard_with_counts` called directly by full_chain etc. — still works (we append, never mutate it).
- Reaction flow (full_chain, gamif reaction handlers, invariants, limit, mission) all green post-change.

### Gold Tests Protected (from PLAN Task 6)

| Test | Count (post) | Flags Used | Result |
|------|--------------|------------|--------|
| `test_alembic_heads.py` | 4 | `-q --tb=line -p no:cov --override-ini="addopts="` | ✅ 4 passed |
| `test_broadcast_service.py` (full) | 22 | same | ✅ 22 passed (incl new create + button tests) |
| `test_broadcast_service_reaction_flow.py` | 22 | same | ✅ 22 passed |
| `test_cross_service_atomicity.py` (-k ...) | 10 | same | ✅ 10 passed |
| `test_reaction_full_chain.py` | 2 | same | ✅ 2 passed |
| `test_invariants.py` (-k reaction) | 1 | same | ✅ 1 passed |
| `test_reaction_limit.py` | 3 | same | ✅ 3 passed |
| `test_reaction_mission_flow.py` | 4 | same | ✅ 4 passed |
| `test_callbackdata_broadcast.py` | 29 | same | ✅ 29 passed (incl 4 pures + bc_extra + collision) |
| `test_gamification_user_handlers.py` (-k reaction) | 27 | same | ✅ 27 passed (incl preserve test) |
| `tests/handlers/ -k broadcast` (smoke) | 1 | same | ✅ 1 passed |

**Combined baseline (6 core golds):** 71 passed (post-item2).

---

## Commands Executed (verbatim from PLAN Task 6)

**Per-task quick (as run):**
```bash
pytest tests/unit/test_broadcast_service.py::TestBroadcastButton -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_callbackdata_broadcast.py -q --tb=line -p no:cov --override-ini="addopts="
```

**Post full suite (exact order from PLAN/impact):**
```bash
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
pytest tests/handlers/ -q -k "broadcast" --tb=line -p no:cov --override-ini="addopts=" 2>/dev/null || echo "..."
```

All executed with project flags: `-q --tb=line -p no:cov --override-ini="addopts="`

Also ran combined baseline (PLAN pre-flight style) for completeness: 71 passed.

---

## Reaction Paths + Atomic Contracts Verification

**Confirmed untouched (design + prior arch + code search):**
- `check_and_register_reaction` — no references to `BroadcastButton` or `extra_button_id`
- `register_reaction` — no references
- `on_besitos_awarded_broadcast_reaction_observer` — no references
- `create_broadcast_message` signature extended only (additive default param); reaction paths read `has_reactions`/`selected_emoji_ids` only
- EventBus wiring in bot.py untouched
- `reactions_keyboard_with_counts` signature/body unchanged

**Atomicity golds re-ran clean:**
- `test_cross_service_atomicity.py` (10): credit survives, best-effort, partials — green
- `test_reaction_full_chain.py` (2): reaction → besitos → mission → keyboard — green
- `test_invariants.py` (-k reaction): I6 idempotent — green

**Reacciones with extra button in markup:**
- Pure `combined`: row0 uses `ReactionCallback` (react: prefix), row1 is URL (no cb_data)
- `refresh` when extra: uses stable `reactions_keyboard_with_counts` for reaction row + appends URL row
- All reaction golds (full_chain, gamif -k reaction, limit, mission, invariants) green with the new code paths active (defensive getattr for mocks, None case continues to work)
- `test_refresh_preserves_extra_button_url_row` explicitly exercises refresh WITH extra_button_id=7 and asserts 2-row markup with url present and reaction row having callback_data

---

## Fixture + Mock Compatibility

**`sample_broadcast_message` (conftest):** omits `extra_button_id` → works (nullable).

**Gamif handler mocks:** updated to include `extra_button_id=None` in `test_updates_reaction_counts`; new preserve test provides `extra_button_id=7` + button mock. Code uses `getattr(broadcast, "extra_button_id", None)` + `isinstance(extra_id, int)` guard → mocks without the attr do not break.

**No breakage to callers of `build_send_reaction_markup`** (its dedicated test still passes; we kept the function for compat).

---

## Self-Check

- [x] Read PLAN.md + SUMMARY.md (mandatory)
- [x] Read impact-analyzer ITEM2
- [x] Read arch audit (PASS 0 crit)
- [x] Read gsd-planner log + SELF_CHECK PASSED line
- [x] Read changed source: broadcast_handlers (helpers/wizard/confirm/refresh paths), gamif_user (refresh), service (sig), callback_data (bc_extra)
- [x] Read new tests (create, prefix/collision, 4 pures import-inside, refresh preserve)
- [x] Read gold tests (cross atomicity, full_chain, invariants-k-reaction, limit, mission, callbackdata, broadcast_service*, gamif reaction, alembic)
- [x] Re-ran PER-TASK + EXACT PLAN Task6 post suite + combined baseline with required flags
- [x] Verified new tests cover: pure helpers (4 cases 0/1), create extra (with+default), prefix (bc_extra + collision len=4), refresh preserve (url row), single choice (markup produces <=1 url row; UI replace)
- [x] Verified golds protect: 0 attributable regressions on atomicity/reaction paths
- [x] Verified reacciones siguen funcionando con botón extra en markup (react: on row0; golds green; explicit preserve test)
- [x] reactions_keyboard_with_counts untouched; build_send_reaction_markup compat preserved
- [x] 0 impact on 3 crits, atomicity contracts, EventBus, get_service
- [x] Veredict: "suite protege adecuadamente" + evidence (counts, commands, results)
- [x] Persist report + gsd log + MEMORY pointer
- [x] Handoff ready

---

## Evidence Summary

| Metric | Value |
|--------|-------|
| New tests | 8 (1 create + 2 cb + 4 pure + 1 refresh) |
| Gold commands re-executed | 11+ (exact PLAN order) |
| Baseline combined (post) | 71 passed |
| Alembic heads | 4 passed |
| Cross atomicity gold | 10 passed |
| Reaction full chain | 2 passed |
| Invariants (reaction) | 1 passed |
| Callbackdata (post) | 29 passed |
| Gamif reaction (post) | 27 passed |
| Attributable regressions | 0 |
| Reaction paths mutated | 0 |
| Critical system impact | 0 |
| Reacciones + extra markup | protected (row0 react:, golds green, explicit test) |
| Single choice | protected (0/1 url row in pures; UI replace) |
| reactions_keyboard_with_counts | untouched (sig + body) |

---

## Handoff

**Ready for:** pytest final por orquestador + review loop effort5

**Next (per SUMMARY/PLAN):** ITEM 3 would be default reactions flip (out of scope here).

**Pool status reminder:** Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. (If applicable.)

---

**References:**
- PLAN: `.planning/quick/20260623-broadcast-link-buttons-item2/PLAN.md`
- SUMMARY: `.planning/quick/20260623-broadcast-link-buttons-item2/SUMMARY.md`
- Impact: `.grok/agent-memory/impact-analyzer/broadcast-link-buttons-item2.md`
- Arch audit: `.grok/agent-memory/arch-enforcer/broadcast-link-buttons-item2.md`
- GSD planner: `.planning/quick/gsd-planner-broadcast-link-buttons-item2.log` (50 lines + self-check)
- This report: `.grok/agent-memory/test-guardian/broadcast-link-buttons-item2.md`
- GSD test-guardian log: `.planning/quick/gsd-test-guardian-broadcast-link-buttons-item2.log`

**End of test-guardian report.**
