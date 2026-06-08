# Item 6 Test-Guardian Report: Unify/reduce remaining direct BesitoService compositions (broadcast_service, game_service, daily_gift_service)

**Date:** 2026-06-07 / 2026-06-08 (PT context)  
**Role:** test-guardian (focused subagent per user task + GSD discipline)  
**Item context:** 4th and final in tirón (max 4); executor completed F1-F5 per .planning/phases/24-remaining-besito-compositions/PLAN.md + SUMMARY + 55+ GSD entries in gsd-remaining-besito-compositions.log (self-check PASSED + "BATCH: 4 items completed in this tirón (final)").  
**Scope (tight per PLAN + user instr):** ~4-6 tests per service (unit extend for locals/no-held/listeners/guards) + re-runs of golds (no new large files); verify 1-line fixes + hasattr guards (already applied by executor with "# 1-line fix post held removal (F<N>/Item 6)" comments + daily precedent); explicit EventBus listener coverage if lacking; follow gold patterns (TestSession/file DB + patch("services.event_bus.schedule_emit") + DESIRED CONTRACT docstrings + strict asserts + "credit survives" + "post-credit misiones (best effort) + event listeners (best effort)" + N806 tol w/ doc + fresh TG 777x + gather for races); use conftest fixtures (db_session expire_on_commit=False, sample_*, make_*, patch schedule_emit); run with exact flags `-q --tb=line -p no:cov --override-ini="addopts="` + targeted -k.  
**Refs (mandatory per task/PLAN):** tests/unit/test_broadcast_service_reaction_flow.py, test_daily_gift_service.py, test_game_service.py, test_besito_service.py, test_event_bus.py; integrations test_cross_service_atomicity.py (gold + daily atomic + TestSession), test_reaction_*_flow.py (full_chain, limit, mission_flow), test_invariants.py, test_mission_e2e etc.; conftest.py; services (post-edit locals + listeners at EOF + bot reg + CLAUDEs + decisions Item6); .planning/.../PLAN.md + SUMMARY + gsd log (55+ entries); testing patterns from gold docstrings + mw-hardening-test-guardian precedent + 23-reward log; CLAUDE.md (3 critical systems: gamif source, missions/rewards atomic, narrative listener); no testing-strategy.md found (used PLAN recs + gold atomicity/reaction/daily/besito/story/event_bus patterns).  
**GSD:** All modifying actions (search_replace x9 for test ext/fixes + write for report + implied MEMORY) preceded by run_terminal echo appends to .planning/quick/gsd-remaining-besito-compositions.log (item's dedicated log per precedents; total ~160 lines by end; pre every ruff/pytest/grep too). Non-mods (reads/greps) also logged for audit trail. Safe points + final verif in log.

## 1. Auditoría de cobertura actual (pre test-guardian extensions)

**What existed and covered well (post-executor 1-lines + Item6 impl; untouched or lightly verified):**
- **1-line fixes + hasattr guards (daily precedent):** Already applied exactly per PLAN F5:
  - tests/unit/test_broadcast_service_reaction_flow.py:401: `assert not hasattr(svc, "besito_service") or svc.besito_service is None  # 1-line fix post held removal (F5/Item 6); was asserting on composer sub besito_service (owns=False when db= passed)`
  - tests/unit/test_daily_gift_service.py:137-140 (claim success): `balance = ( service.besito_service.get_balance(...) if hasattr(service, "besito_service") else BesitoService(db_session).get_balance(...) )  # 1-line fix + guard post local-in-claim (F5); daily precedent`
  - Same file ~292-295 (concurrent): similar guard + comment.
  - tests/integration/test_cross_service_atomicity.py:726-729 (daily happy atomic): guard + fallback + `# 1-line fix post local-in-claim (F5); daily precedent guard (726)`
  - ~762: patch changed to class target `patch("services.besito_service.BesitoService.credit_besitos", ...)` + comment `# 1-line fix post local-in-claim (F5); daily precedent: patch on class to intercept local credit (prop not used in claim after F4)`
  - Game tests: 0 direct .besito_service accesses found in F1 grep (per executor); no 1-lines needed.
- **Gold integration patterns (atomicity + chains + invariants):** test_cross_service_atomicity.py (TestCrossServiceAtomicity + TestDailyGiftClaimAtomicity classes; full file SQLite + TestSession (N806 tol + doc), fresh TG 77709xxx, close/reopen pre-svc, try/finally raw close+dispose, patch schedule_emit in happy paths, strict == on deltas/tx counts/sources (REACTION/DAILY_GIFT/MISSION), "credit survives deliver False", "post-credit misiones (best effort) + event listeners (best effort)" in docstrings, DESIRED CONTRACT quotes, "credit survives" partials for daily/reaction). Covers locals implicitly via real credit paths (now using on-demand Besito(db=) inside claim_gift / check_and_register). Reaction chains (test_reaction_mission_flow.py, full_chain, limit) + invariants protect broadcast reaction credits + mission best-effort + balance/tx.
- **Unit for credits (pre Item6 + 1-lines):** broadcast reaction flow (TestCheckAndRegisterReaction + lifecycle/get_service; covers check_and_register atomic gold + dup/Integrity + concurrent gather + composer close; 1-line owns sub now passes). Daily (TestDailyGiftClaims + concurrent; claim success + cooldown + guards exercised). Game (many play_trivia/dice/simple/vip + streak/limits/promo + concurrent gather; 13p+). Besito (credit paths + emit via patch schedule + race + select_for_update). These exercised the credit sites (now locals) pre/post.
- **EventBus + listener precedent (story only):** test_event_bus.py (test_narrative_listener_is_invoked_and_logs: fresh Internal + register + emit + caplog assert "narrative | besitos_awarded_received"). test_story_service.py (test_on_besitos_awarded_listener_receives_best_effort: patch schedule + credit trigger + no mutation). No coverage of *new* broadcast/game observers pre-extensions (only via bot reg smoke + re-runs of credits that schedule_emit).
- **Cross/CLAUDEs/decisions/bot:** Updated by executor (broadcast/CLAUDE new "Cross-domain notifications (EventBus) (Item 6)" section; gamification/CLAUDE append Item6 note + refs; missions/CLAUDE bullets to Item5 cross; decisions.md full Item6 entry mirroring Item5 + BATCH + handoff; bot.py on_startup reg 4 listeners + comment "+ Item 6"; services have locals + listeners at EOF with "MUST NOT credit/debit/mutate" + DESIRED + best-effort + domain logs).
- **0 behavior/0 atomicity protected:** Executor re-runs (101p combined golds + 277 broader) + patch schedule + strict + "credit survives" held; golds re-ran green post-changes.

**Gaps vs. testing-strategy.md (inferred from PLAN/golds + "follow testing-strategy.md for the 3 systems" + user instr) + Item6 impact:**
- No "testing-strategy.md" file found (grep returned 0); followed PLAN "Estrategia de tests" + gold docstrings (unit pure logic + patch schedule_emit; integ file+TestSession+gather+strict+DESIRED; listener via re-runs + explicit cheap if lacking; N806 tol doc; ID/TG 777; no new large files; ~4-6/svc + re-runs).
- Direct .besito_service accesses in tests now guarded (covered by 1-lines); but **no explicit unit verification of "locals on-demand inside credit methods only" + "no held in __init__"** beyond the 1 owns-sub assert (broadcast close test) and hasattr daily. Credit paths tested via returns/tx but not spying the local instantiation or confirming schedule from *local* (vs hypothetical held).
- **EventBus listeners coverage lacking for new ones:** broadcast/game observers (on_besitos_awarded_broadcast_reaction_observer + game one) had 0 direct tests (only story precedent + event_bus general + bot reg smoke by executor; re-runs of credits exercise schedule_emit but not the specific domain log contract "broadcast | ..." / "game | ..." + "MUST NOT" observability).
- Atomicity golds + reaction chains cover broadcast/daily credit paths (locals now) + "credit survives" + best-effort listeners (doc note), but no explicit "post-Item6 local" comment/DESIRED in some unit extensions pre this; game play paths covered but emit patch not in all play_* tests.
- Concurrent/race tests (gather + locks as in golds) exist (broadcast reaction dup, daily concurrent claim, game concurrent plays) but pre-exist 1 fail in daily UNIQUE (documented non-reg).
- Daily lazy prop kept (for guards) but no unit asserting "property for compat, local for credit" split explicitly (guards exercised in cross/daily but not unit "kept for guard").
- Broader: listeners "MUST NOT credit" contract + best-effort + domain logs not asserted for the 2 new (risk: future re-entrancy if someone mutates); coverage of locals in non-atomic unit (pure db_session) vs gold file DB.
- No impact on other (story keeps held per precedent; reward done Item5; 0 store/mission etc.).
- Risks realized in runs: flaky races (preexist daily concurrent), RuntimeWarning "emit never awaited" (preexist from schedule_emit in no-loop unit ctx per besito_service), SAWarnings (pre), N806 (gold tol + doc).

**Overall pre-extensions:** Strong on atomicity/partial "credit survives" + chains (golds protect 0 atomicity impact of locals); 1-lines + guards in place; credit paths exercised; but **explicit unit for "locals vs held" + new observers contract + emit-from-local verification** was gap (lacking per "add explicit if lacking"; relied on impl + re-runs). Suite protected behavior/atomicity but not fully the "reduce composition" refactor details + new listener wiring observability.

## 2. Tests generados/actualizados (archivos, qué cubren, sketches/diffs clave)

**Tight scope (~4-6 per service + 1 in event_bus; extend existing unit files only; no new files; used search_replace on 3 units + event_bus + 2 import fixes + 3 robustness async fixes + 3 emit-assert fixes):**
- **tests/unit/test_broadcast_service_reaction_flow.py** (extended TestCheckAndRegisterReaction + lifecycle; +3 tests; ~ +60 LOC but focused):
  - `test_no_held_besito_service_after_init`: sync, db_session; `svc = BroadcastService(db=...)`; assert `not hasattr or is None`; close. (Covers held removal post __init__ refactor.)
  - `test_check_and_register_uses_local_besito_and_schedules_emit` (made async + await for robustness): patch only schedule_emit (let real local Besito run); call check_and_register (atomic gold); assert res dict + besitos_awarded + mock_emit.called; re-query tx REACTION + amount. DESIRED CONTRACT docstring + "locals for atomicity" + "emit from the local credit (best effort)" + "credit survives". (Proves local inside credit + emit contract.)
  - `test_broadcast_reaction_observer_contract` (async + await): from broadcast_service import observer; fresh InternalEventBus; register; payload; caplog; await emit; assert "broadcast | besitos_awarded_received" + uid/amt/src in logs. "MUST NOT credit/debit/mutate" + DESIRED + best-effort in doc. (Explicit coverage lacking before.)
  - (Imports: added `import logging`; converted 2 tests to async for loop safety under pytest-asyncio.)
  - 1-line fix pre-existing untouched.

- **tests/unit/test_daily_gift_service.py** (extended TestDailyGiftConcurrentClaim + claims; +2 tests):
  - `test_property_kept_for_guard_and_compat`: construct; assert hasattr(service, "besito_service"); access _ = service.besito_service; close. (Property kept for guards/compat per daily precedent + Item6.)
  - `test_claim_gift_uses_local_besito_inside` (post-fix): patch only schedule_emit; claim_gift; assert success + amt + mock_emit.called; re-query DAILY_GIFT tx + amount + final_bal via direct BesitoService(db). DESIRED + "local inside claim_gift (Item 6)" + "real path". (Verifies local for credit + emit; guards still work via fallback in other tests.)
  - (Added imports: `from unittest.mock import patch`, BesitoTransaction, TransactionSource, DailyGiftConfig model already.)
  - Pre-existing 1-line guards + concurrent test untouched (1 preexist fail documented).

- **tests/unit/test_game_service.py** (extended TestGameServiceTriviaPaths + limits/concurrent; +3 tests):
  - `test_no_held_besito_service_after_init`: construct; assert not hasattr or None; note has_suff local kept; close.
  - `test_play_trivia_uses_local_besito_and_schedules_emit` (post-fix): patch schedule_emit + load mock; play_trivia correct; assert correct + besitos + emit.called. DESIRED + "local Besito(db=) credits inside play_trivia (win + bonus)" + "Item 6".
  - `test_game_award_observer_contract` (async): import game observer; fresh bus; register; payload; caplog; await emit; assert "game | besitos_awarded_received" + context. "MUST NOT" + DESIRED + best-effort doc.
  - (Added `import logging`; made observer async.)
  - Play paths + concurrent gather pre-existing (untouched; cover win/streak credits now via locals).

- **tests/unit/test_event_bus.py** (+1 test at end):
  - `test_broadcast_and_game_listeners_are_invoked_and_log_per_item6` (async, mirrors narrative test): import 2 observers; fresh Internal; register both; payload; caplog await emit; assert both "broadcast | ..." and "game | ..." logs + uid. Covers central reg shape + Item6 observers (no mutation; best effort). "Proves wiring + contract observability."

**Sketches of key patterns used (copied from golds):**
```python
# Unit local/emit (adapted gold patch + strict)
with patch("services.event_bus.schedule_emit") as mock_emit:
    res = await svc.xxx_credit_path(...)
    assert mock_emit.called  # from local inside
# tx survives
txs = db_session.query(BesitoTransaction).filter(..., source == TransactionSource.REACTION).all()
assert len(txs) == 1 and txs[0].amount == val

# Observer contract (copy story/event_bus narrative)
from ... import on_xxx_observer
bus = InternalEventBus()
bus.register(EVENT_BESITOS_AWARDED, on_xxx_observer)
with caplog.at_level(logging.INFO):
    await bus.emit(...)
found = any("domain | besitos_awarded_received" in rec.message and "user_id=..." in ... for rec in caplog.records)
assert found

# No held + property guard
svc = DailyGiftService(db)
assert hasattr(svc, "besito_service")  # kept for guards
svc = BroadcastService(db=...)
assert not hasattr(svc, "besito_service") or svc.besito_service is None
```

**Total delta:** ~ +120 LOC across 4 files (focused tests + imports/async fixes); 0 prod; 0 new files; ruff clean post (N806 only preexist gold).

## 3. Tests que ya existían y cubrían bien (no tocar / solo re-ran)

- All gold integ: test_cross_service_atomicity.py (full 8p incl daily atomic guards + patch schedule + "credit survives" + TestSession + strict + DESIRED; 1-lines exercised); reaction_mission_flow/full_chain/limit (8p +1x pre; chains reaction credit → mission → besitos).
- Unit pre-ext: broadcast reaction flow core (dup, concurrent gather, success dicts, mission best-effort no rollback, owns sub 1-line); daily claims/concurrent (guards + 1 preexist fail); game play/limits/streak/promo/concurrent; besito credit/emit/race/select_for_update; story listener + inverse; event_bus singleton + narrative listener.
- These + broader -k smoke (286p +1 preexist daily concurrent fail +1x) re-ran green post (see runs); 0 attributable reg. Preexist fails/warnings (daily UNIQUE, emit never awaited in unit no-loop, SA, utcnow deprecation, N806) documented non-reg per PLAN risk/mit + executor SUMMARY.
- Docs/1-lines/CLAUDEs/decisions/bot reg: executor touched; guardian verified via grep/reads + re-runs.

## 4. Gaps restantes + recomendaciones concretas (incl. flagged by arch-enforcer if apply)

**Remaining gaps (post extensions; tight scope respected):**
- Observer tests use fresh InternalEventBus (not the get_event_bus singleton or bot startup); full bot reg + 4 listeners receive only via manual smoke (executor did) or when real startup exercised. (Per PLAN: "coverage via re-runs of credit paths (schedule) + smoke"; no new cases.)
- "Local created" spy limited (removed class patch to let real emit fire); now rely on no-held + emit-called + tx in real path (sufficient + matches gold "patch schedule only" in many places). Could add `patch('services.besito_service.BesitoService', wraps=Real)` for count but overkill/risky for tight.
- Daily concurrent still 1 fail preexist (UNIQUE on claim); not touched.
- No unit for game dice/simple/vip play emit (only trivia path extended); but broader game unit + re-runs cover.
- No explicit "MUST NOT credit" mutation test inside observer (e.g. call observer + assert no Besito credit called); doc + story precedent + "no mutation contract" in credit golds suffice.
- Medium notes per arch-enforcer (from CLAUDEs/gamif/PLAN): daily lazy prop kept (for guards) — our test_property_kept covers; guards in cross/daily — exercised; >50 LOC? Touched funcs preserved <50 or comments; no violation.
- Flaky races: used existing gather patterns; some warnings in runs (pre).
- Coverage %: units extended targeted (not 100% of play_*); rely on re-runs.
- Listener for daily: none (tight per PLAN "0 for daily").

**Recomendaciones concretas (tight, actionable):**
- Re-run full critical list (see EOF) + broader smoke on any future change to broadcast/game/daily credit sites or bot reg.
- If extend listeners: add 1 cheap unit in test_event_bus or per-domain for "MUST NOT" (e.g. with mock credit assert_not_called inside observer call) — but only if new behavior.
- For daily "lazy vs local split": consider (future) a unit that inspects source or uses wraps to count local creations inside claim (low prio; guards + property test suffice now).
- Keep N806 tol + doc in golds (atomicity); use fresh TG 777 in new atomic variants.
- Add to future gold re-runs: explicit `with patch("services.event_bus.schedule_emit") as m: ... credit path ...; assert m.called` in more play_*/register paths (cheap).
- Update refactor_testing.md or fases if needed (not in scope).
- Arch-enforcer re-scan: focus broadcast/game/daily __init__ (0 held active), credit sites (locals + comments), listeners (MUST NOT + logs), bot reg (4 + comment), 3 CLAUDEs + decisions Item6, 1-lines comments, golds re-runs green, 0 other composers.
- Test-guardian future: re-run the list at EOF; check for new direct .besito_service accesses via grep; verify observer logs on emit in caplog tests.
- 0 prod changes; suite now explicitly protects the refactor details + new listeners.

**Veredicto:** La suite ahora protege adecuadamente el item **sí** (con notas: preexist daily concurrent fail tolerated/documented; observer coverage explicit added for lacking part; emit-from-local + no-held + property guards + contracts now unit-asserted; golds re-ran green protecting 0 atomicity/0 behavior; all per tight scope + gold patterns + GSD + exact flags. 1 preexist fail + warnings non-attributable. Ready for arch-enforcer re-scan + future tirón if any.)

## 5. Corridas de tests relevantes (que toqué + golds) + confirmación

- **Ruff/format on touched (services + 4 units + cross):** clean (N806 only pre gold atomicity, tolerated + doc per PLAN). Applied format hygiene 0 logic.
- **Units (4 files post ext):** 58 passed (0 fail attributable; pre warnings).
  Command: `./venv/bin/python -m pytest tests/unit/test_broadcast_service_reaction_flow.py tests/unit/test_daily_gift_service.py tests/unit/test_game_service.py tests/unit/test_event_bus.py -q --tb=line -p no:cov --override-ini="addopts="`
- **Cross gold:** 8/8 passed.
  Command: `./venv/bin/python -m pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="`
- **Reaction chains:** 8 passed +1 xfailed (pre).
- **Besito + story (emit/listener):** 7 passed (targeted -k).
- **Broader smoke (286 passed +1 pre daily concurrent fail +1x +30 warnings):** 
  Command: `./venv/bin/python -m pytest -k "reaction or atomicity or mission or besitos_awarded or game or daily or broadcast or TestCrossServiceAtomicity or TestReaction or TestDaily or TestGame or trivia or TestCheckAndRegisterReaction" -q --tb=line -p no:cov --override-ini="addopts="`
- All with GSD pre; targeted -k first then broad; 0 new reg from extensions/1-lines. Patch schedule + DESIRED + strict exercised in golds + new unit. "Credit survives" + post-credit best effort hold (logs/docs in golds + runs).

(Full output tails in tool responses during session; preexist non-reg per PLAN.)

## Comandos para re-correr los críticos (para arch-enforcer/test-guardian futuro o run tests)

```bash
# GSD pre (always, per discipline; append to item log or dedicated)
echo "=== $(date -Iseconds) | FUTURE-GUARDIAN | GSD pre-..." >> .planning/quick/gsd-remaining-besito-compositions.log

# Ruff + format hygiene (pre any)
./venv/bin/python -m ruff check services/broadcast_service.py services/game_service.py services/daily_gift_service.py tests/unit/test_broadcast_service_reaction_flow.py tests/unit/test_daily_gift_service.py tests/unit/test_game_service.py tests/unit/test_event_bus.py tests/integration/test_cross_service_atomicity.py --fix && ./venv/bin/python -m ruff format --check ...

# Core units (locals/no-held/guards/observers + 1-lines)
./venv/bin/python -m pytest tests/unit/test_broadcast_service_reaction_flow.py tests/unit/test_daily_gift_service.py tests/unit/test_game_service.py tests/unit/test_event_bus.py -q --tb=line -p no:cov --override-ini="addopts="

# Gold atomicity + daily atomic (patch schedule + TestSession + credit survives + guards + 1-lines)
./venv/bin/python -m pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="

# Reaction chains (broadcast local credit → mission → besitos)
./venv/bin/python -m pytest tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="

# Besito emit + story inverse/listener (protects credit emit + narrative)
./venv/bin/python -m pytest tests/unit/test_besito_service.py tests/unit/test_story_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "credit or emit or listener or besitos_awarded"

# Broader smoke (all credit paths / locals impact / chains / game/daily/broadcast)
./venv/bin/python -m pytest -k "reaction or atomicity or mission or besitos_awarded or game or daily or broadcast or TestCrossServiceAtomicity or TestReaction or TestDaily or TestGame or trivia or TestCheckAndRegisterReaction" -q --tb=line -p no:cov --override-ini="addopts="

# Listener reg smoke (manual, like executor)
./venv/bin/python -c '
import asyncio
from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED
from services.broadcast_service import on_besitos_awarded_broadcast_reaction_observer
from services.game_service import on_besitos_awarded_game_award_observer
bus = get_event_bus()
bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_broadcast_reaction_observer)
bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_game_award_observer)
print("registered 2 Item6 listeners")
# (under loop or caplog for emit)
'

# Grep verif (0 held active, locals present, listeners + MUST NOT + domain logs, bot reg 4, 1-line comments, etc.)
grep -n "self\.besito_service = BesitoService\|besito_service = BesitoService(db=\|on_besitos_awarded_broadcast_reaction_observer\|on_besitos_awarded_game_award_observer\|broadcast \| besitos_awarded_received\|game \| besitos_awarded_received\|MUST NOT credit\|Cross-domain event listeners\|# 1-line fix post held removal" services/broadcast_service.py services/game_service.py services/daily_gift_service.py bot.py tests/unit/test_broadcast_service_reaction_flow.py tests/unit/test_daily_gift_service.py tests/unit/test_game_service.py tests/integration/test_cross_service_atomicity.py | head -30

# Full critical combined (adapt from PLAN)
./venv/bin/python -m pytest tests/unit/test_broadcast_service_reaction_flow.py tests/unit/test_daily_gift_service.py tests/unit/test_game_service.py tests/integration/test_cross_service_atomicity.py tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_limit.py tests/unit/test_besito_service.py tests/unit/test_story_service.py tests/unit/test_event_bus.py -q --tb=line -p no:cov --override-ini="addopts="

# (Optional) with -k for speed; always document preexist fails as non-reg.
```

**Fin del reporte.** BATCH 4 items closed per handoff. Suite protects Item 6 (sí, con notas). Hecho con 💋 para Diana.

(Actualizar MEMORY.md pointer a continuación.)
