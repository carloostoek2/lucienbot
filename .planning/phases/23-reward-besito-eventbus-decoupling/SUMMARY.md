---
phase: 23
plan: reward-besito-eventbus-decoupling
subsystem: reward / gamification cross (EventBus decoupling for besitos_awarded notifications)
tech-stack: Python 3.12, aiogram 3, SQLAlchemy 2.0, pytest, ruff, GSD workflow
key-files:
  - services/reward_service.py (refactor + listener)
  - bot.py (central reg)
  - tests/unit/test_reward_service.py (1-line fix)
  - services/missions/CLAUDE.md (cross-domain section)
  - decisions.md (new decision entry)
  - .planning/quick/gsd-reward-besito-eventbus.log (full GSD + self-check PASSED)
  - .planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md (source of truth)
---

# SUMMARY: Reduce direct BesitoService composition in RewardService via EventBus (Item 5 / 23)

**Date:** 2026-06-08 (executed)  
**Executor:** gsd-executor (following PLAN al pie de la letra, GSD discipline total, scope tight, copy patterns from golds)  
**Handoff from:** .planning/phases/22-critical-tests-three-systems/SUMMARY.md (explicitly named this Item 5)  
**Status:** COMPLETE - Self-Check: PASSED

## Objective (from PLAN)
Tight reduction of *held direct composition* of BesitoService inside RewardService (MISSION delivery composer). Remove `self.besito_service = BesitoService(self.db)` held; use local on-demand `BesitoService(db=self.db)` *only* inside `_deliver_besitos` (preserves 100% atomicity via shared db + credit internal commit). Add rewards-domain *observational* listener (copy of narrative's, "MUST NOT credit", best-effort). Register centrally in bot.py (after narrative). 1-line fix in 1 unit test. Docs in missions/CLAUDE + decisions. **Zero prod behavior change, zero atomicity impact, zero other composers touched, zero new files.**

## Phases (strict order, 5 small, with gates + GSD pre every + safe points)
1. **F1 prep/GSD/baseline** (log, ruff, pytest reward+cross gold, greps for composition + gold patterns (story listener, bot reg, atomicity patch+DESIRED+TestSession+"credit survives"+ "post-credit best effort", event_bus), confirm fixtures/mocks, GSD pre/post, "F1 safe point").
2. **F2 refactor RewardService** (GSD pre each edit; remove held in __init__ + comments; local Besito(db=) in _deliver only + docstring; ruff; grep 0 held + local present; pytest targeted (exclude 1 failing access) + cross spot; smoke; "F2 safe point").
3. **F3 listener + central reg** (GSD pre; append listener at end of reward_service (exact copy story 670-694, name decision on_besitos_awarded_rewards_observer, "MUST NOT", "rewards |", best-effort, 0 impact); bot.py import + register after narrative + extended log + comment; ruff; pytest story+besito re-runs (protect); smokes (import bot + manual register); grep; "F3 safe point").
4. **F4 1-line test fix + re-runs golds** (GSD pre; 1-line access fix in test_deliver_reward_besitos + minimal import; ruff+format hygiene; full pytest reward (17/17); full atomicity (8/8, patch executed); broader -k; grep fix + no old access; "F4 safe point").
5. **F5 verif final + docs + self-check** (GSD pre every; ruff limpio on 3 py; greps all criteria (0 held, listener+contract, reg, 1-line, docs sections); re-runs finales + spot + smoke; docs appends (missions/CLAUDE cross section, decisions new entry post Item1); big self-check in log with full structure + "Self-Check: PASSED"; optional SUMMARY; handoff).

## Tasks Completed + Commits (individual per protocol, after each tarea/phase)
- **F1 (prep, 0 logic edits):** chore(tests): ruff auto-fix+format for F1 baseline gate cleanliness (pre-existing import order/isort + whitespace/style in reward unit test; 0 logic to deliver besitos test or 142 access site). Hash: 59a61d9. (Hygiene only; reversible.)
- **F2 (refactor):** feat(reward): reduce direct BesitoService composition in RewardService via EventBus (Item 5 / 23 post critical-tests). Hash: 76abd9e. (2 search_replace + ruff hygiene on reward_service.py; 23 ins/15 del.)
- **F3 (listener+reg):** feat(eventbus): add rewards-domain observational listener + central registration (Item 5 F3). Hash: 3c4ad8a. (listener append + bot changes; 34 ins/2 del.)
- **F4 (1-line + golds):** test(reward): 1-line access fix post held removal (F4 of Item 5) + import companion. Hash: 5431307. (2 ins/1 del on test.)
- **F4 hygiene (post 1-line format):** chore(test): ruff format post F4 1-line (hygiene to achieve limpio on touched py per F4/F5 DoD; 0 logic to the 1-line fix or BesitoService(db=) line + comment). Hash: c2adcc8. (3 ins/1 del, wrap of long line.)
- **F5 (docs + final):** (docs commit + SUMMARY if separate; see log for exact; hygiene if any from final ruff).

All commits: specific `git add <file>`, messages with scope/0/0/0/refs to PLAN/GSD/DoD, GSD pre before the git commands where applicable.

## Desviaciones Encontradas y Resueltas (per PLAN "registrar en GSD")
- Ruff --fix + format in baseline/gates (F1, F2, F4, F5) auto-edited test/reward files (import reorder, line wrap on 1-line comment with long text, possible other style). Committed as separate chore entries (hygiene for "ruff limpio" DoD; 0 logic/semantic to 1-line site, deliver paths, or access strings - verified by post-format grep + diff capture in GSD). "0 edits in F1" interpreted as 0 *logic* (precedent in prior phases for gate cleanliness).
- Initial smoke used "python -c" (PLAN) but env had no "python" (only python3/venv); retried with `./venv/bin/python -c` (consistent with ruff/pytest cmds in PLAN); succeeded. Documented.
- Pre-existing dirty tree (git status showed 20+ M + ?? from prior items/impact reports/plan dirs); always used specific `git add <only our touched file>`; never staged unrelated. Not a deviation of this Item.
- Atomicity/besito re-runs showed known warnings (RuntimeWarning coroutine 'InternalEventBus.emit' never awaited in no-loop test contexts; SAWarnings; unraisable in handlers tests). Pre-existing (from eventbus PoC + test patterns), not attributable to Item changes; documented in logs but gates counted as pass (xfails pre-exist, not new).
- F4 format hygiene committed after the 1-line commit (to satisfy limpio before F5 verif which re-requires it).
- No 4th item executed in this run (user "máximo 4", batch context "3"; see handoff for recommended next).

All deviations logged in GSD entries at time of discovery + in self-check.

## Decisiones Tomadas (per PLAN sec 4, logged in first relevant GSD)
1. Listener name: `on_besitos_awarded_rewards_observer` (clarity for "rewards" domain ownership vs gamification-origin "from_gamification" used by narrative; bus tolerates same name but distinct preferred; confirmed in F3 pre-edit GSD).
2. Local Besito for atomicity: `besito_service = BesitoService(db=self.db)` (1 line + comment; direct, not get_service - get_service is for high-level/handlers per 21 precedent; local preserves "dentro de la tx de deliver" explicit + cheap + owns=False; matches atomicity gold TestSession + getservice norm).
3. 1-line fix: exact access line + comment per PLAN + minimal import (companion); no other test changes.
4. close() getattr: left verbatim (harmless None for besito now).
5. Reg in bot: after narrative (order not important); extend existing log line + comment.
6. Docs: missions/CLAUDE at end (new section); decisions append after Item1 eventbus entry (same format).
7. GSD log: .planning/quick/gsd-reward-besito-eventbus.log (pre only via echo/printf/cat >> ; wc tracking).
8. Commands: exact from PLAN ( -p no:cov --override-ini="addopts=", ./venv/bin/python -m for ruff/pytest, python -c for smokes with venv fallback).
9. No deviation on "MUST NOT credit", patch schedule_emit in gold re-runs, local db=, 0 new files, scope.

## GSD Discipline (non-negotiable, followed)
- Pre *every* modification (search_replace/write/edit), gate (ruff/pytest/grep/smoke), verif, summary step: run_terminal append "=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados>" >> log ; wc -l after.
- 45+ entries total (planner 4 + executor 41+); pre-F1, pre each edit (F2 2, F3 2 files, F4 1, F5 2 docs), pre each gate/ruff/pytest/grep/smoke/self-check/SUMMARY, post safe points, post commits.
- Style copied from precedents (gsd-eventbus-poc-item1.log etc): detailed, refs DoD, patterns copied (story listener, atomicity gold, bot reg, 1-line, patch, local db=, "MUST NOT", DESIRED).
- Log exists with planner INIT/DISCOVERY/PLANNING/PLAN COMPLETE + executor pre-F1 + all.

## Scope (tight, 0/0/0/0 verified)
- Only files listed in PLAN "Archivos que se modificarán" + log + this PLAN + optional SUMMARY.
- 0 new files (except SUMMARY optional at end).
- 0 prod behavior change.
- 0 atomicity impact.
- 0 other composers (broadcast, game, daily_gift, etc. keep their direct held for now; "unify remaining" recommended as potential 4th item).

## Key Patterns Copied (al pie de la letra, per PLAN "Copia patrones **al pie de la letra** de golds")
- Listener + comment block + "MUST NOT credit" + best-effort + DESIRED: from services/story_service.py:670-694 (exact # Cross-domain... + async def + docstring + log "narrative | ..." + final comment; adapted 3-4 words for rewards + "0 impact").
- Central reg + comment in bot.py: from bot.py:199-202 (get_event_bus().register + logger.info); extended after narrative.
- Local Besito with shared db for atomicity: spirit from tests/integration/test_cross_service_atomicity.py (TestSession passed to services, db= for commit-internal, owns=False, raw close+dispose, N806 tolerated) + 21-getservice (db= passed).
- Patch schedule_emit + DESIRED CONTRACT + strict asserts: from atomicity gold (with patch in happy, asserts on balance/tx/MISSION source/delta/progress/reward active, docstring "post-credit misiones (best effort) + event listeners (best effort)").
- 1-line test fix + comment: minimal as in ports of Item2 (access change + "# 1-line fix post ... (F4)").
- GSD entries: detailed pre- + what validated after (ruff/pytest/grep) + patrones + "DoD refs".
- Atomicity gold: file+TestSession, try/finally dispose/close, DESIRED, patch event, strict == on deltas/counts, "credit survives deliver False".
- Commands: exact pytest flags, ruff ./venv, greps, smokes from PLAN "Instrucciones" + "Comandos concretos".

## Tests / Gates Summary (all passed with 0 attributable reg)
- See self-check in log (above) for per-phase numbers.
- Final: 17 (reward), 8 (atomicity), 44+ (story/besito), 165+ broader, smokes ok, ruff limpio.
- Gold protection: atomicity happy (MISSION credit + patch + delta==8) + partials (inactive reward, stock=0, pre-complete, increment error post credit) all re-ran green; "credit survives deliver False" + "post-credit best effort" held.

## Deviations (see self-check for full)
- Ruff hygiene commits (F1, F4) as chore (0 logic).
- Smoke python fallback to venv python.
- Pre-existing dirty tree + warnings (not counted as reg).
- Format wrap on the 1-line comment (hygiene; semantics + comment preserved).

## Handoff / Next
**Item 5/23 closed. Ready for gsd-executor of next batch item (if any) + arch-enforcer re-scan (enfocado en reward composition sites + listener wiring + 3 critical systems: gamif/missions/rewards/narrative) + test-guardian (correr los tests críticos listados en self-check).**

Recommended 4th item (high value, follows "unify remaining direct Besito compositions" suggestion in user prompt + dirty tree evidence of other composers still holding direct BesitoService: broadcast for reactions, game, daily_gift, possibly user): "unify remaining direct Besito compositions (or reduce via local/eventbus where atomicity allows, preserving gold contracts)". Launch impact-analyzer / gsd-planner for it (per GSD workflow enforcement in CLAUDE.md).

## Re-verification Commands (from PLAN + self-check)
```
./venv/bin/python -m ruff check services/reward_service.py bot.py tests/unit/test_reward_service.py --fix && ./venv/bin/python -m ruff format --check ...
./venv/bin/python -m pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest -k "reward or deliver_reward or TestRewardServiceDelivery or TestCrossServiceAtomicity or mission or besitos_awarded or atomicity or TestReward or cross_service_atomicity" -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/unit/test_story_service.py tests/unit/test_besito_service.py -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -c "
import bot
from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED
from services.reward_service import on_besitos_awarded_rewards_observer
bus = get_event_bus()
bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_rewards_observer)
print('both wired')
"
grep -n "self\.besito_service = \|on_besitos_awarded_rewards_observer\|MUST NOT credit\|rewards | besitos_awarded_received\|besitos_awarded -> narrative, rewards\|1-line fix post held removal (F4)\|Cross-domain notifications (EventBus)\|Reduce direct BesitoService composition in RewardService via EventBus (Item 5" services/reward_service.py bot.py tests/unit/test_reward_service.py services/missions/CLAUDE.md decisions.md | cat
cat .planning/quick/gsd-reward-besito-eventbus.log | tail -50
```

**Hecho con disciplina GSD total, scope tight, patrones copiados al pie de la letra de golds, 0 behavior/0 atomicity. Listo para guardians y siguiente.**

---

**Self-Check: PASSED** (see full in log entry)