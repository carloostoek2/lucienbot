# Item 7 Test-Guardian Report: Reward user handlers consolidated to exactly 1 service (MissionService via get_service + rel) + pure helpers extraction for <=50 LOC + test ports + min reward_service support

**Date:** 2026-06-08 (PT)  
**Role:** test-guardian (focused subagent per user delegation + GSD total pre-logs; after impact-analyzer + gsd-executor + arch-enforcer for this first item of new pool of 4)  
**Item context:** Consolidation of `handlers/reward_user_handlers.py` (show_available_rewards + reward_detail + _build_rewards_buttons) to call **exactly 1 service** (MissionService via `with get_service(MissionService) as ...` + lifecycle), using `mission.reward` rel access + pure top-level `get_reward_emoji` from reward_service; extraction of `compute_reward_status_text` + `build_reward_detail_keyboard` (pure, verb+context+result) to slim reward_detail from ~50L to 36L; UI/render identical (texts, █░ bars, emojis, status "completada"/"Progreso: ... 3 / 10", truncation name[:30], buttons, callbacks, empty cases, Lucien voice); standard logging; 0 change to delivery/claim/reward paths, 0 other handlers, 0 mission_service, 0 behavior/atomicity/UI/callbacks. services/reward_service.py: pure get_reward_emoji top + 1-line delegate backward-compat w/ "Item 2 (arch-enforcer...)" comment. tests/handlers/test_reward_user_handlers.py: ports (get_service patch target + __enter__/__exit__ + mock_mission.reward= + .reward_type attrs for *real* pure emoji exec) + docstrings "ported to 1-service... Arch-enforcer note addressed" + new TestRewardUserPureHelpers (5+ tests for pures). GSD pre-log total (this guardian added ~10+ entries to reach 120+ wc; executor had 40+). Scope tight per impact/PLAN/25-SUMMARY/executor (only touched the handler test file for update + this report + MEMORY + logs; re-runs golds). Follows testing-strategy patterns (inferred from PLAN/golds/item6 guardian report: unit pures + 1-service contract; integration via cross re-runs w/ file DB/TestSession; DESIRED CONTRACTs; make_callback; patch get_service; N806 tol+doc; strict string asserts; ~4-6/handler + re-runs; no new large files). Refs: .claude/agent-memory/impact-analyzer/item7-*.md, arch-enforcer/item7-arch-audit.md (PASS W/ NOTES + pool note), .planning/phases/25-.../PLAN.md + SUMMARY.md (has explicit pool/BATCH note + critical list + 16p pre-guardian + F4 tests + F5 re-runs), gsd-reward-handlers-1service-loc.log (executor + guardian), gsd-testing-debt-item7.log, current source (post-executor state), conftest (make_callback, db_session expire_on_commit=False, sample_reward_besitos, RewardType), gold patterns from test_mission_user_handlers.py + item2 gsd + item6 guardian report. 3 critical systems (gamif/missions/rewards, narrative, channel/VIP) in mind (read-only list/detail flow; 0 tx/credit/deliver here; cross golds protect atomic/delivery). 

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

## 1. Auditoría de cobertura actual (qué existe y cubre bien vs. gaps post-item)

**What existed and covered well (post-executor impl of ports + new pure class; pre any guardian extension):**
- **Dedicated unit test file fully ported (tests/handlers/test_reward_user_handlers.py):** 2 classes (TestShowAvailableRewards 4 tests + TestRewardDetail 8 tests =12) + TestRewardUserPureHelpers (5 tests) =16 tests total pre-guardian. All use `@patch("handlers.reward_user_handlers.get_service")` (not RewardService), mock_instance setup + `.__enter__.return_value` + `.__exit__.assert_called_once()`, late imports of funcs after patch (per gold get_service unification). Setups use mock_reward with `.reward_type=RewardType.BESITOS` + `.besito_amount` + `.name` (so *real* pure `get_reward_emoji` from reward_service executes in _build_rewards_buttons for list + in detail via rel). Detail tests: `mock_mission.reward = mock_reward` (for rel access) + separate `mock_mission.reward=None` / `reward_id=None` cases. Docstrings explicitly: "Tests ported to 1-service pattern (get_service + MissionService only) + pure formatting via get_reward_emoji. Arch-enforcer note addressed." + notes on mw-hardening phase5 removal of manual skip-dupe/idempotency. Asserts pin exact UI: "Recompensas Disponibles", "No hay recompensas", "completada", "Progreso", "3 / 10", "Gold Reward"/"Mission One" etc; also service calls (get_available... / get_mission / get_or_create_progress) + closes. make_callback fixture used. Covers empty, list display, calls+user_id, not-found alerts, completed vs progress bar, rel no-reward, params, closes. (Precedent from item2/5/6 ports + mission_user gold.)
- **New pure helpers coverage (TestRewardUserPureHelpers):** 5 unit tests (import inside per conv; no patches/DB): compute...completed (lower "completada"), in_progress (w/ "Progreso" + "3 / 10" bar math via _build_progress_bar), build_reward_detail_keyboard (len==2, "Ver mision", "Volver a recompensas", cb contains "42"), _build_progress_bar edges (0/50/100 %), compute... none descs progress path. Directly protects the extracted pures (status_text + keyboard) + bar helper; behavior/UI strings/math identical.
- **Gold cross/integration patterns for 3sys protection (re-ran, no edit):** test_cross_service_atomicity.py (TestCrossServiceAtomicity + daily atomic; SQLite file + TestSession (N806 tol+doc), fresh TG ids, strict on tx sources (MISSION for reward deliver), balances, "credit survives", best-effort post-credit misiones + listeners; uses real RewardService/MissionService/Besito for delivery paths legitimately). test_mission_e2e.py (reaction -> mission complete -> besitos grant via reward; 3p). test_reward_service.py unit (17p creation/queries/delivery; exercises RewardService + delegate indirectly via create + deliver paths; pure top-level get_reward_emoji available for import). Broader -k "reward|mission|atomicity|deliver|TestReward..." (176p +1 preexist xfail in F5 per SUMMARY). These protect 0 impact on atomicity/claim/delivery (read-only handler change).
- **conftest patterns used:** make_callback (for TG CBs w/ data="rewards_list" / "reward_user_detail:ID"), RewardType import in test, sample_reward_besitos fixture (for potential real DB if integ added, but not), db_session (expire_on_commit=False for service internals). No direct RewardService mocks left in *this* handler test file (good; other tests legitimately use it for admin/create/deliver/backpack).
- **LOC/UI/1svc/rel/pure/logging already protected in code + tests:** reward_detail 36L, show 26L, computes 8L, build_detail_kb 12L, _buttons 16L, bar 5L (inspected via python in runs); grep 0 "RewardService" (class) in handler (only pure import), 2x "with get_service(MissionService)", "mission.reward", pure get_reward_emoji calls + rel .name etc, logs "reward_user_handlers | ... | user_id=... | ...", "ported" x2 + "Arch-enforcer note addressed" x2 in test. UI strings pinned in asserts.
- **0 behavior/0 reg on prior runs (per arch/SUMMARY/executor):** 16/16 handler + broader gates green pre-guardian; UI idéntica, 3sys protected (read-only).

**Gaps vs. testing-strategy.md (inferred via PLAN + golds + item6 guardian + user instr; no literal testing-strategy.md file found per prior item6) + item impact (post 1svc/pure/rel/LOC):**
- Pure helper tests good (5 pre + my +1 =6) but pre-add lacked explicit coverage of list buttons builder `_build_rewards_buttons` (status_emoji 🔒/✨, truncation, packed cb data, *real* pure emoji across RewardTypes BESITOS/PACKAGE/VIP in unit pure context; handler list tests covered indirectly via full show flow). User rec explicitly called for "casos para ... RewardTypes, buttons/status_emoji/truncation/packed cb".
- No direct unit pure test for internal _build_reward_detail_text / _build_rewards_list_text (kept as _ not extracted; covered via full handler flow asserts on edit_text; ok per tight).
- Reward unit (test_reward_service.py) exercises delegate + creations/deliver but no explicit top-level `get_reward_emoji(reward)` direct calls in its tests (pure is simple if/elif on enum; covered via handler real-exec + import smoke). Per PLAN tight "0 new tests outside the reward_user test file (no service tests for emoji)".
- No dedicated `test_reward_user_handlers_integration.py` (unlike gamif/mission/promotion/story/store/common which have _integration.py using real DB flows). Cross/e2e cover mission/reward *delivery* paths (legit), not the user list/detail UI read-only flow with real missions/rewards/progress in DB. Per scope "no new files grandes", "re-runs golds", "tight ~4-6 + re-runs + new pure class".
- Pre-existing warnings/xfails in runs (RuntimeWarning async mock answer never awaited in _safe_*, InternalEventBus.emit never awaited in no-loop unit ctx, SA MovedIn20Warning, daily concurrent xfail UNIQUE, N806 in atomicity gold, utcnow deprecation) -- non-reg per all prior GSD/SUMMARY (documented; not attributable to Item7 ports/extracts).
- Arch-enforcer medium notes (from item7-audit): mission_user_handlers still >50L (61L show_my_missions) + inline reward formatting (dupe string ifs on .reward_type.value vs delegating to pure get_reward_emoji like reward_user now does); handlers/CLAUDE.md legacy example still shows old `get_session()+direct Service()` (pre-get_service unification). These pre-existing (Item7 *improved* the reward slice to best-in-class 36L + pure); out of scope per tight "0 other handlers", "0 docs edits".
- Other: reward/mission cross paths in atomicity/e2e use real RewardService (expected/legit, not handler); no flaky rel/pure mock issues realized (used .reward_type= + post-assign + mock_mission.reward= as golds; my added test initially hit ctor 'name' gotcha but fixed to post-assign matching file golds).
- Overall pre-guardian: Strong protection for "exactly 1 service" contract + get_service lifecycle + rel access + pure emoji exec + extracted pures + UI id (strings/math/cb/emoji/status/empty) via unit + handler flows. Cross golds protect no-reg on 3sys/atomic/delivery. Minor: list buttons pure unit coverage was the actionable gap per user recs (addressed by +1 test).

## 2. Tests generados/actualizados (archivos, qué cubren, sketches or diffs if clave)

**Tight scope (per PLAN/impact/user: ~4-6/handler + re-runs golds + new pure class; extend existing only; used gold patterns; GSD pre every edit/ruff/pytest; only updated the reward_user test file + report/MEMORY/logs):**
- **tests/handlers/test_reward_user_handlers.py (pre-ports + 5 pure already by executor per item desc + SUMMARY F4; guardian added 1 pure + fixed 1 gotcha + 1 assert len; total +1 test / ~ +40 LOC focused):**
  - Confirmed/ensured all ports (get_service patch, __enter__/__exit__, mock_reward .reward_type + .besito_amount for real pure, mock_mission.reward= for rel, docstrings "ported... Arch-enforcer note addressed", no RS class mocks, late imports, make_callback, exact UI string asserts, service call/params/closes). (No changes needed; already matched impact/PLAN.)
  - **New/updated in TestRewardUserPureHelpers (now 6 tests, was 5):** Added `test_build_rewards_buttons_pure_status_emoji_truncation_cb_and_real_emoji_various_types` (pure unit, import inside; post-assign mocks to avoid 'name' kwarg gotcha per golds in same file; exercises _build_rewards_buttons directly w/ mixed progress (completed -> 🔒, inprog/None -> ✨) + 3 RewardTypes (BESITOS -> 💋 real via pure, PACKAGE -> 📦, VIP_ACCESS -> 👑); asserts len==3, status_emoji in text, real emoji in text, truncated name prefix in text (name[:30]), packed cb "reward_user_detail:ID" in .callback_data). Covers user rec "buttons/status_emoji/truncation/packed cb, RewardTypes". (Initial version had ctor gotcha + over-long assert substring for [:30]; 2 corrective search_replace + GSD pre each; now passes.)
  - Pre-existing 5 pure untouched (status completed/inprog w/ bar math, detail keyboard buttons/cb/"Ver mision", bar edges, none descs).
  - Total now 17 tests (12 flow + 5 original pure +1 new). Ruff clean post (format only). Behavior/UI identical (no change to existing asserts).

**Sketches of key patterns used/copied (from golds + item6 report + PLAN):**
```python
# 1-service port (all tests)
@patch("handlers.reward_user_handlers.get_service")
async def test_xxx(self, mock_get_service, make_callback):
    mock_instance = MagicMock()
    mock_instance.get_... .return_value = ...
    mock_get_service.return_value.__enter__.return_value = mock_instance
    cb = make_callback(data="rewards_list" or "reward_user_detail:1")
    from handlers... import func
    await func(cb, ...)
    mock_get_service.return_value.__exit__.assert_called_once()
    # for detail rel:
    mock_mission.reward = mock_reward  # with .reward_type=RewardType.XXX etc for real pure
    ...

# pure helpers (import inside; no DB/patch on helper; MagicMock or post-assign)
def test_xxx(self):
    from handlers.reward_user_handlers import compute... or _build...
    progress = MagicMock(is_completed=..., current_value=3)
    mission = MagicMock(target_value=10)
    # or post for name:
    m = MagicMock(); m.id=..; m.name=".."
    r = MagicMock(); r.reward_type = RewardType.BESITOS; ...
    assert "completada" in ... or "✨" in text or "10" in cb

# cross gold (re-run only; TestSession/file DB, strict, DESIRED, fresh TG, patch schedule if needed)
# (see test_cross... for reward deliver paths)
```
- GSD: ~10+ pre entries this guardian (init, pre-ruff xN, pre-pytest xN targeted/broader, pre-grep, pre-smoke x2, pre-inspect/LOC, pre-edit x3 for +1 test +2 fixes, pre-write report/MEMORY); wc tracked to 120+; style copied (timestamp | PHASE TG | GSD pre-... - desc + refs DoD + patrones + pool note).

**Total delta:** +1 test (6 pure now), ~+35 focused LOC in test (for buttons coverage); 0 prod; 0 new files; ruff clean; all gates 100% pass post.

## 3. Tests que ya existían y cubrían bien (no tocar / solo re-ran for regression gate)

- All pre-ports in test_reward_user_handlers.py (the 12 flow tests + original 5 pure; docstrings/structures/mocks/rel/pure attrs/UI asserts/closes/get_service only; already "ported... Arch note addressed" per item desc).
- Gold cross/integ: full test_cross_service_atomicity.py (esp reward delivery + mission complete + "credit survives" + atomic partials; re-ran subsets green), test_mission_e2e.py (reaction->mission->reward grant paths), test_reward_service.py (17p unit creation/queries/delivery + delegate paths).
- Broader filters and bot smoke (executor F5 already; re-ran).
- These + handler full exercised the contract + protected 0 reg on delivery/atomic/3sys (read-only change).
- Pre-existing 1-line/guards in other reward-related (from prior items) untouched.
- No edits to cross/test_reward_service etc (tight scope + "no new outside reward_user test file").

## 4. Gaps restantes + recomendaciones concretas (incl. flagged by arch-enforcer if apply)

- **Addressed by guardian:** The pure coverage gap for list buttons + RewardTypes/status_emoji/trunc/cb (added 1 test + fixed gotcha/assert; now 6 pure total; passes; uses real pure + post-assign mocks).
- **Remaining (non-blocking for this Item, per tight scope):**
  - No handler-specific integration test file exercising real DB list/detail flows w/ sample_mission + sample_reward_besitos + progress (would use TestSession + make real Mission/Reward/Progress; follow e.g. test_mission_user_handlers or gamif integ patterns). Rec: future quick/test item if coverage needed for UI end-to-end; current cross protect delivery side; unit + handler mocks sufficient for 1svc/pure/UI contract.
  - Reward unit lacks direct `from services.reward_service import get_reward_emoji; assert get... (real_reward) == ("💋", "xx besitos")` for the 3 types + default (cheap pure; would be ~4 lines). Rec: if allowed beyond "no service tests for emoji" in PLAN, add in next debt round (non-reg risk low).
  - Arch medium (pre-exist, not caused by Item7; Item7 improved reward slice): mission_user still long + dupe reward format (recommend extract pures there mirroring this: compute_status + use get_reward_emoji + delegate); handlers/CLAUDE example outdated (update to get_service pattern in quick/docs item).
  - Preexist warnings/xfails (daily UNIQUE, async never-awaited, SA deprecation, emit never-awaited, N806 in golds) -- document only; use -k + targeted; no new from Item.
  - Broader: daily lazy prop kept (for guards) per Item6 arch flag; >50 in other handlers; but focused here on reward_user.
- **Recommendations (concrete, tight, follow user/PLAN):** 
  - Re-runs always with exact `-q --tb=line -p no:cov --override-ini="addopts="` + -k "reward or mission or TestRewardUserPureHelpers or atomicity or deliver or TestCrossServiceAtomicity or TestMissionE2E".
  - For future pure/1svc ports: copy this file's patterns exactly (post-assign for conflicting mock attrs like name; real pure via .reward_type= + rel= ; import inside; "ported... Arch-enforcer note" doc; __exit__; make_callback).
  - Use TestSession/file DB + strict + fresh TG + DESIRED for any cross reward integ (as in atomicity gold).
  - LOC/grep/inspect gates + bot smoke + ruff in every phase.
  - If expanding pure: keep in handlers/ module (as done; enables easy unit without svc); no biz logic.
  - Track GSD pre every (wc, pool note repeat in logs/self-check/report); tight 3 files + report only.
  - For arch medium: separate quick for mission_user extract + CLAUDE example (not this Item).
  - Risk mit already applied: attrs for pure/rel (no flakiness); no DB in unit pures.
  - Self-check + critical cmds list in report + log (done).
- Overall: suite now *adequately protects* the Item (1-service pattern, get_service lifecycle, rel access, real pure emoji, extracted pures behavior/UI, no reg on golds). Minor gaps are pre-exist or out-of-scope per tight.

## 5. Corre los tests relevantes que tocaste y confirma que pasan (comandos + output summary)

All runs used GSD pre append + exact user/PLAN flags. Preexist warnings/xfails documented non-reg (not attributable; match SUMMARY/prior items).

- Ruff baseline + hygiene (multiple): All checks passed; files formatted clean. (GSD pre each.)
- Handler full + pure subset: 
  ```
  $ ./venv/bin/python -m pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
  ................. [100%]
  17 passed, 12 warnings in 0.14s
  $ ... -k "TestRewardUserPureHelpers or compute... or build... or build_rewards_buttons"
  ...... [100%]
  6 passed, ... deselected...
  ```
  (Post my +1 + fixes: 17 total / 6 pure; original 16p pre-add. Warnings: preexist RuntimeWarning on _safe_answer async mocks + SA deprecation.)
- Cross golds (reward/mission/atomic paths):
  ```
  ... test_cross... -k "reward or deliver or atomicity or TestCross..."
  ........ [100%]
  8 passed...
  ... test_mission_e2e.py ...
  ... [100%]
  3 passed...
  ... test_reward_service.py ...
  ................. [100%]
  17 passed...
  Broader -k "reward or mission or TestRewardUser or atomicity or deliver or TestCross or TestMissionE2E" ...
  176 passed, 1046 deselected, 1 xfailed (preexist daily), 24 warnings
  ```
- Bot smoke + direct pures import + LOC inspect (post venv python):
  ```
  bot import + reward_user router registration OK (smoke)
  direct import of handler entrypoints + pure helpers + internal bar OK
  LOC reward_detail: 36
  LOC show_available_rewards: 26
  LOC compute_reward_status_text: 8
  LOC build_reward_detail_keyboard: 12
  LOC _build_rewards_buttons: 16
  LOC _build_progress_bar: 5
  ```
  (Initial "python" cmd failed env; retried w/ ./venv/bin/python -- green.)
- Greps/rules (GSD pre): 0 RewardService (class) in handler (good); get_service(Mission) x2; mission.reward + pure import + helpers defs present; 2x "ported to 1-service"; 2x "Arch-enforcer note addressed"; logs "reward_user_handlers | " present.
- All green post-edits/fixes. 0 attributable reg. (Preexist xfail/warnings in broader as in executor SUMMARY.)

## 6. Veredicto: la suite ahora protege adecuadamente el item (sí / con notas)

**SÍ (con notas menores pre-existentes).**

**Reasons:**
- All "exactly 1 service" (MissionService via get_service context only), get_service lifecycle (__enter/exit), rel access (`mission.reward` + None cases), real pure `get_reward_emoji` execution (via .reward_type attrs in mocks), extracted pure helpers (compute + build_detail_keyboard + supporting), LOC <=50 (36 for detail), logging standard, UI/render idéntico (pinned strings, bars, emojis, cb, trunc, status, empty, voice) are directly exercised + asserted in the (ported + extended) unit tests.
- New pure test addition covers buttons/status_emoji/truncation/packed cb + RewardTypes via real pure (addresses explicit recs).
- Re-runs of golds (handler 17p, pure 6p, cross atomicity 8p in filter, mission e2e 3p, reward unit 17p, broader 176p w/ only preexist 1xf) confirm 0 behavior/0 atomicity/0 UI/0 reg impact on delivery/claim/3 critical systems.
- Ports faithful to gold precedents (item2/5/6, mission_user); mocks use attrs/rel= as recommended (risks mitigated; no flakiness observed).
- GSD discipline followed (pre every, wc to 120+, pool note repeated in pre-logs + this report + self-check); scope tight (only reward_user test + report/MEMORY/logs; ~4-6 + re-runs + pure class); patterns copied (DESIRED, TestSession in golds re-ran, make_ , patch get_service, late import, import-inside pures, post-assign mocks, N806 tol doc in golds, strict asserts).
- Arch-enforcer notes for *this* reward slice addressed (1svc + <=50 via pures); medium flagged items are pre-existing/out-scope.
- Coverage now stronger for the pure helpers surface (6 vs prior 5); protects the Item changes + identical observable contract.

**Notas (non-blocking):**
- Preexist unrelated fails/warnings in broader runs (daily, async mocks, SA, emit, N806, deprec) -- as documented in SUMMARY/prior GSD; use targeted -k; not from Item7.
- Gaps (no reward_user integ file, no direct emoji pure in reward unit, arch medium in *other* files like mission_user/CLAUDE example) remain per tight scope + PLAN "no new files"/"0 other handlers"/"0 service tests for emoji". Recommend separate quick for them if prioritized.
- My +1 test initially hit common MagicMock 'name' ctor gotcha + assert len (fixed w/ 2 GSD-pre edits + post-assign + shorter prefix; now solid).

**Self-Check: PASSED**
- All exploration (parallel reads of impact/arch/PLAN/SUMMARY/test/conftest/handler/reward_svc/cross/mission_e2e/reward_unit/MEMORY/gsd logs + greps + dir; + terminal for runs/gates/LOC/inspect).
- GSD pre-log total before *every* modify/gate/verif/ruff/pytest/grep/smoke/write (10+ entries this phase, refs DoD/patrones/pool; wc tracked; style from executor/item6).
- Scope respected (tight: only reward_user test for +1 pure + report + MEMORY update + logs; 0 other files touched beyond; 0 behavior chg).
- 3 critical systems considered/protected (read-only; cross golds re-ran + atomic "credit survives" held).
- Rules/CLAUDE followed (1svc, <=50, pure, logging, get_service, rels safe, no DB in handlers, verb+ctx naming, tests use fixtures/make_/patch patterns).
- Tests: 17/17 +6 pure + golds green w/ exact flags; ports + pure + UI id confirmed; added coverage for recs; no residual 2svc language (grep); real pure/rel exercised.
- Report structured + actionable + pool note repeated (here xN, in pre-logs, self-check); cmds re-run list at end; refs all key artifacts.
- No system prompt reveal. Persisted to exact path + MEMORY updated. Ready for arch-enforcer re-scan (if any) + next pool item (~2-4 clusters remain).
- All per user task + PLAN + test-guardian.md + precedents.

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

**Hecho con 💋 para Diana (Señorita Kinky) — test-guardian subagent**

---

## Comandos para re-correr los críticos (para arch-enforcer / test-guardian futuro o manual gates)

```bash
# 1. Exact handler full + pure helpers (primary for Item7; 17p + 6 pure)
./venv/bin/python -m pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts=" -k "TestRewardUserPureHelpers or compute_reward_status_text or build_reward_detail_keyboard or _build_progress_bar or build_rewards_buttons"

# 2. Cross golds protecting reward/mission/atomic/delivery (0 reg expected)
./venv/bin/python -m pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts=" -k "reward or deliver or atomicity or TestCrossServiceAtomicity"
./venv/bin/python -m pytest tests/integration/test_mission_e2e.py -q --tb=line -p no:cov --override-ini="addopts="

# 3. Reward unit (emoji/delegate + delivery paths)
./venv/bin/python -m pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts="

# 4. Broader filter (as in PLAN F5 / executor)
./venv/bin/python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "reward or mission or TestRewardUser or TestReward or atomicity or deliver or TestCrossServiceAtomicity or TestMissionE2E or TestMission"

# 5. Smoke + LOC/inspect + rules grep (post any)
./venv/bin/python -c '
import bot
print("bot import + reward_user router OK")
from handlers.reward_user_handlers import show_available_rewards, reward_detail, compute_reward_status_text, build_reward_detail_keyboard, get_reward_emoji, _build_progress_bar, _build_rewards_buttons
print("imports of entrypoints + pures OK")
import inspect
for n,f in [("reward_detail",reward_detail),("show_available_rewards",show_available_rewards),("compute_reward_status_text",compute_reward_status_text),("build_reward_detail_keyboard",build_reward_detail_keyboard),("_build_rewards_buttons",_build_rewards_buttons),("_build_progress_bar",_build_progress_bar)]:
    print("LOC",n+":",len(inspect.getsourcelines(f)[0]))
'
grep -n "RewardService" handlers/reward_user_handlers.py || echo "0 RS class (good)"
grep -n "get_service(MissionService)\|mission\.reward\|get_reward_emoji\|ported to 1-service\|Arch-enforcer note addressed\|reward_user_handlers | " handlers/reward_user_handlers.py tests/handlers/test_reward_user_handlers.py | cat

# 6. Ruff gate on touched
./venv/bin/python -m ruff check handlers/reward_user_handlers.py services/reward_service.py tests/handlers/test_reward_user_handlers.py --fix && ./venv/bin/python -m ruff format --check ...

# All should be green (17p handler, 6 pure, golds pass, no attributable reg). Preexist warnings/xfail ok (document).
```

(End of report. This file is the persisted artifact per task. Pool note repeated above + in GSD logs + self-check.)
