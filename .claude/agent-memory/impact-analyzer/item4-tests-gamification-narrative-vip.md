---
name: item4-tests-gamif-narrative-vip
description: Impact analysis report for adding/expanding quality tests on Gamification, Narrative, Channel/VIP critical systems (Item 4 post get_service unification)
type: project
---

# Impact Analysis Report: Tests for Critical Systems (Item 4)

**Date:** 2026-06-07  
**Role:** impact-analyzer (Lucien Bot)  
**Feature:** Add/expand specific quality tests for 3 main systems following telegram-bot-hardener skill recs + prior analysis (refactor_testing.md, fases_refactor_testing.md, test-quality-flow patterns). Post get_service unification + EventBus + middlewares.  
**Context:** Follows unificación get_service. Focus tight on Gamif (besitos/reactions/daily/minijuegos), Narrative (story/archetypes/progreso/quiz), Channel Admin/VIP (channel/vip/free-VIP cross). Use 4-6 key tests/system. Gold patterns from atomicity, reaction_full_chain, invariants, broadcast_reaction_flow, vip_flows.

## Executive Summary
Existing test suite strong from Top 10 debt work (Ítems 1-10 in fases/refactor_testing): 
- Gamif heavily covered via reaction atomic (test_broadcast_service_reaction_flow.py: dup, mission-fail-no-rollback, concurrent gather pilot, get_service lifecycle), cross_service_atomicity (partials post-credit, daily atomic gold), invariants (I1-3 besito, I6 reaction), besito unit (credit/debit/insuff/race-mock/commit-param), daily_gift unit, game_service unit (limits), reaction integ.
- Narrative: story_service unit (atomic advance_to_node commit=False, archetype calc, branching points/cost deduct, CRUD), some progress.
- VIP/Channel: vip_flows/complete/lifecycle/ritual/subscription (redeem/expire/reminder/multi), test_vip_service (expir support, ID contracts), test_channel_service (basic + pending), invariants (I4 token, I5 VIP access), cross atomicity/vip integ, free_entry_flow.
- Infra: conftest (db_session in-mem+expire_on_commit=False, sample_* incl story/vip/channel/balance/broadcast, make_user/make_message/make_callback/make_fsm_context MemoryStorage, mock_bot), SQLite+TestSession gold pattern for cross-commit flows (used in atomicity, reaction_full, invariants, streak, vip_lifecycle), get_service tests (in broadcast unit), EventBus partial (schedule_emit patched in besito credit).

**Real gaps vs skill recs (testing-strategy implied by hardener + docs) + recent changes:**
- Gamif: "Sumar puntos no excede máximo" (daily limits in GameService DAILY_*_LIMIT_*, or daily_gift 24h; no global max but TOCTOU/never-neg in cross debit; concurrent real stress beyond mocks/gather in broadcast; redeem reward deduct+tx covered indirect via mission atomic but explicit "canjear recompensa" thin; insuff balance returns False in besito but "mensaje correcto (no silent)" is handler level + some integ; race uses locks FOR UPDATE (tested mocked in besito unit + real-ish gather in broadcast concurrent); post-get_service: subservices (besito in daily/broadcast) own_session=False when passed.
- Narrative: advance persists (tested atomic); archetype "se asigna una sola vez y no cambia" (logic in advance_to_node on ENDING + assign_archetype_to_user; calc_dominant; quiz hardcoded; no test that re-assign on end/quiz doesn't override once set, or assign_to_user idempotent); FSM restore on bot restart w/ RedisStorage (make_fsm uses MemoryStorage only; no RedisStorage test or simulate restart by new context + load state; story quiz FSM in handlers); "rama inválida no rompe flujo, retorna anterior/graceful" (can_access_node rejects but advance returns (False, reason, None); no dedicated invalid branch/choice test for corrupt state prevention); "transiciones inválidas rechazadas (EventBus si aplica para desbloqueos besitos)" (cost check uses direct besito.get_balance; EventBus is one-way besitos_awarded listener in story (on_besitos... just logs PoC, registered bot.py; no test for narrative listener or using bus for unlocks); no invalid trans test using recent bus).
- Channel/VIP: pay user "accede VIP y removido del gratuito" (VIP redeem in vip_service + channel cross? clear_vip_entry in vip; free remove logic in handlers/scheduler? not explicit cross test); "expirado removido VIP sin error aunque ya no en canal" (expire_subscription + scheduler _process_expired does ban/unban; tests cover expire but not "no error if not member"); "ban propaga a ambos canales" (scheduler uses bot.ban/unban per ch; no dedicated test asserting calls to free+VIP); "grant/revoke offline (startup check) funciona" (expired subs created active/past, get_expired + expire; scheduler tests in vip_lifecycle integ + pilots in free_entry; no explicit "bot offline during grant then startup recovers"); "múltiples suscripciones / expiración parcial" (multi-tariff in vip_flow, some active filter; partial one-ch expire in multi-ch scenarios thin).
- Cross/recent impact: get_service unif (lifecycle tests only in broadcast unit; need in besito/daily/story/vip/channel for owns/ close/ no-leak); EventBus (best-effort post-credit in besito, listener in story; need mocks in narrative tests); middlewares (rate/idemp separate units; may affect concurrent tests but not core); ID contracts (TG telegram_id vs PK .id fixed in many but cross fixtures still risk in story/game setups e.g. sample_balance uses TG, story tests sometimes .id); file-vs-mem DB (atomicity gold uses file+TestSession for internal commits in credit/claim; db_session for pure units).
- Coverage holes per fases (Gamif F4 review done: Alta brechas ID duality fixtures, daily atomic (now piloted), concurrent dup reaction (gather pilot), never-neg TOCTOU cross (debit in story/store etc), docstring tx vs impl); Narrative in F6 pending full review; Channels pre-GSD done but cross VIP free/VIP ban/partial thin.
- No "máximo" hard cap in besito (BigInt prevents overflow; limits in game/daily); "usuario sin saldo recibe mensaje correcto" requires handler tests (e.g. story_user, store_user, gamif) using make_callback + assert edit_text contains Lucien message.

**Overall:** Strong foundation but insufficient explicit coverage for the exact 9 bullet points in task (esp concurrent real, archetype immutability, FSM restore, ban prop, offline startup, pay+free-remove, invalid narrative branch). 4-6 key per system = ~15-18 new/expanded tests targeted. Prioritize contract vs impl, deterministic (explicit models not rely samples for ID), gold patterns.

## Mapa de Impacto (archivos de test a tocar/crear, fixtures)
**Test files to touch/create (prefer extend existing per "smallest change" + precedent in refactor):**
- Gamification:
  - Extend: tests/unit/test_besito_service.py (add non-mock concurrent credit/debit using file db? or new race class; explicit "no exceed max" if daily context via game; strengthen insuff + tx register).
  - Extend: tests/unit/test_daily_gift_service.py (concurrent claim within 24h -> at most 1 success; already can_claim/claim_gift).
  - Extend: tests/unit/test_game_service.py (existing 10 tests; add limit not exceeded on multiple play (dice/trivia), concurrent plays respect DAILY_*_LIMIT, reward deduct+tx on win).
  - Extend: tests/integration/test_cross_service_atomicity.py or test_reaction_full_chain.py (add "canjear recompensa" explicit: mission reward deduct registers tx; or via store).
  - Possibly new: tests/integration/test_gamif_points_max_race.py (but tight scope: reuse patterns).
  - Handler side for "mensaje correcto": extend tests/handlers/test_gamification_user_handlers.py or test_story_user_handlers.py (but focus systems/services per task; optional).
- Narrative:
  - Extend: tests/unit/test_story_service.py (add archetype once-only + no change on re-end/assign; invalid branch/choice graceful (returns False, no corrupt progress); invalid trans (cost > bal) rejected no partial; perhaps listener for EventBus).
  - Extend/create integ: tests/integration/test_story_progress.py or add to test_mission_e2e? (advance persists node; FSM state roundtrip: create progress/quiz state, "restart" by new FSMContext/Memory or patch, assert restored; use make_fsm_context).
  - Touch: tests/handlers/test_story_user_handlers.py (for FSM/quiz if needed; low prio).
- Channel Admin / VIP:
  - Extend: tests/integration/test_vip_flow.py + test_vip_flows.py + test_vip_complete_cycle.py + test_vip_subscription_lifecycle.py (add pay-redeem -> VIP sub + free remove cross; expire no error if not member; ban prop to both; multi subs + partial expire; offline grant/revoke via startup/scheduler sim).
  - Extend: tests/unit/test_vip_service.py (startup/expire support already rich post prior; add multi/partial).
  - Extend: tests/unit/test_channel_service.py (ban prop? or cross in integ; grant during offline).
  - Extend: tests/integration/test_free_entry_flow.py (cross free/VIP on redeem/expire).
  - Integ for scheduler offline: reuse vip_lifecycle pattern (SQLite file + patch bot for ban calls).
- General/cross:
  - tests/unit/test_event_bus.py (extend for narrative listener if not; mock wiring).
  - tests/conftest.py (add fixtures if missing: e.g. sample_game_record, make_redis_storage mock or fakeredis if avail, sample_free_channel + sample_vip for cross, event_bus_mock, ensure sample_story with cost/ending).
  - No new top-level files preferred (extend like atomicity was stub->gold); if needed 1-2 integ for narrative FSM/VIP cross.
- Impact on non-test: none (0 prod changes); possible minor fixture ID fixes if story/game setups use .id instead TG (per prior fixes).
- Also touch run_critical_tests.py? or Makefile if new markers, but no.

**Fixtures/mocks needed (gaps):**
- Existing strong: db_session (in-mem tx rollback + expire_on_commit=False good post-multi-commit), sample_user (TG), sample_balance (TG), sample_vip_channel/sample_free_channel, sample_subscription/expired, sample_story_node/choice/archetype, sample_broadcast/reaction_emoji, sample_mission/reward, mock_bot (has ban/unban), make_user/make_message/make_callback/make_fsm_context (MemoryStorage), sample_tariff/token.
- Gaps to add/fix:
  - sample_game_record or explicit in game tests (for limits).
  - Fixture/patch for EventBus: e.g. mock "services.event_bus.schedule_emit" or get_event_bus() in narrative tests (similar to besito credit patches).
  - For FSM restore: extend make_fsm_context or new make_fsm_redis_mock; test by creating state, close/recreate context, load.
  - For concurrent races real: helper to run gather with fresh per-call services? or shared but file db (as in broadcast concurrent test which already uses gather + asserts <=1).
  - Mock for scheduler startup/expire offline: patch bot in integ, create past-dated active sub, call relevant _process or exposed expire methods.
  - For "pay accede + remove free": explicit free_channel + pending? + redeem in VIP cross test; assert sub + no pending or channel leave.
  - Ensure ID contract: all new use .telegram_id for user keys (balance, sub.user_id, claim.user_id, progress.user_id, reaction.user_id, game.user_id).
  - For ban prop: assert mock_bot.ban_chat_member called with VIP ch and FREE ch ids.
  - get_service usage: add TestServiceLifecycleOrGetServiceContext classes to besito/daily/story/vip/channel unit tests (copy pattern from broadcast test).
- DB setup: for race/TOCTOU/atomic cross use file-based SQLite + TestSession (gold from atomicity/reaction_full/invariants); unit pure use db_session. Avoid relying global fixtures for cross-tx.

**Coverage targets:** Add explicit asserts for task bullets; increase service coverage for story (currently some), game (61% slice), vip/channel cross.

## Tests específicos recomendados (con ejemplos de estructura)
Prioritize 4-6 key verifiable per system. Use:
- @pytest.mark.unit / .integration
- @pytest.mark.asyncio where async (reactions, sched)
- DESIRED CONTRACT docstring quoting task bullet.
- Explicit setup (fresh tg=7772xxxx numeric, create models direct, commit, close/reopen db=TestSession() pre-svc for cross).
- Strict: == not in, .count() <=1, balance delta exact, state == expected.
- try/finally: db.close(); engine.dispose()
- Patch for bus/mission/bot/side.
- N806 tolerated for TestSession (precedent).
- GSD + ruff + targeted pytest before broader.

**Gamification (besitos, reacciones, daily gift, minijuegos) - target 5:**
1. Sumar puntos no excede máximo (daily limits game + daily_gift 24h):
   ```python
   # in test_game_service.py or new gamif race integ
   def test_play_dice_does_not_exceed_daily_limit_free(self, db_session, sample_user):
       svc = GameService(db_session)
       # setup 10 prior records today for free
       for _ in range(GameService.DAILY_DICE_LIMIT_FREE):
           svc.record_game_play(...)  # or direct GameRecord
       success, _ = svc.play_dice(sample_user.telegram_id, is_vip=False)
       assert success is False
       # balance unchanged, no tx beyond limit
   ```
   Similar for trivia, VIP higher limit. + concurrent claim_gift in daily test (already atomic pilot, strengthen race).

2. Canjear recompensa descuenta correctamente y registra transacción:
   ```python
   # extend test_cross_service_atomicity.py TestCrossServiceAtomicity or TestDaily...
   async def test_reward_redemption_deducts_and_registers_mission_tx(self, tmp_path):
       ... setup mission + REWARD BESITOS, progress complete via increment
       # assert MISSION tx + balance delta + reward inactive? or delivered
   ```
   (leverages existing deliver path).

3. Usuario sin saldo suficiente recibe mensaje correcto (no error silencioso):
   - In besito: already test_debit_insufficient returns False + balance unchanged.
   - For "mensaje": extend handler test or story test:
     ```python
     # in test_story_service or handler integ
     def test_advance_insufficient_balance_returns_lucien_message_no_partial(self, db_session, sample_user):
         node = StoryNode(..., cost_besitos=1000)
         ...
         success, msg, prog = svc.advance_to_node(sample_user.telegram_id, node.id)
         assert success is False
         assert "besitos" in (msg or "").lower() or "Lucien" voice check  # not silent/None crash
         assert prog is None
         # no tx created
     ```

4-5. Dos requests simultáneos no duplican puntos (race protection usando locks FOR UPDATE existentes):
   ```python
   # extend test_broadcast_service_reaction_flow.py TestCheckAndRegisterReaction or besito
   async def test_concurrent_credits_use_for_update_no_double(self, db_session, sample_user):
       # pre bal=0; use file db variant if needed for contention
       results = await asyncio.gather(
           credit_task1, credit_task2, return_exceptions=True
       )
       successes = [r for r in results if r is True]
       assert len(successes) <= 1
       # bal == amount exactly once; 1 tx
   ```
   (builds on existing concurrent dup reaction + besito unit mock for with_for_update; make deterministic with file+separate sessions if coop issue).

Also: daily claim concurrent within cooldown -> only 1 claim/credit (extend atomic daily test).

**Narrative (story_service, arquetipos, progreso, quiz) - target 5:**
1. Avanzar en historia persiste el nuevo nodo correctamente:
   - Extend existing test_advance_to_node_atomic... + test_advance..._updates... ; assert post commit/refresh current_node_id, visited, chapter.

2. Arquetipo se asigna una sola vez y no cambia:
   ```python
   def test_archetype_assigned_once_on_ending_never_overwritten(self, db_session, sample_user):
       svc = StoryService(db_session)
       # setup progress + ending node
       progress = svc.get_or_create_progress(sample_user.telegram_id)
       progress.archetype = ArchetypeType.EXPLORADOR
       db_session.commit()
       # advance to another ending
       success, _, prog = svc.advance_to_node(..., ending2.id)
       assert success
       db_session.refresh(prog)
       assert prog.archetype == ArchetypeType.EXPLORADOR  # not recalced or changed
       # also test assign_archetype_to_user idempotent/no override
   ```

3. Estado FSM se restaura correctamente si el bot se reinicia (con RedisStorage):
   ```python
   async def test_story_fsm_state_restores_after_simulated_restart(self, make_fsm_context):
       # use quiz state e.g. story quiz answers in FSM data
       ctx1 = await make_fsm_context(user_id=77720001)
       await ctx1.set_state("story:quiz")
       await ctx1.update_data(answers=[1,3,2], current_q=3)
       # "restart": new context (sim Memory; for Redis would patch REDIS or use same storage key)
       ctx2 = await make_fsm_context(user_id=77720001)  # same key= same storage
       state = await ctx2.get_state()
       data = await ctx2.get_data()
       assert state == "story:quiz"
       assert data["answers"] == [1,3,2]
   ```
   (Note: real RedisStorage test would require REDIS_URL or fakeredis; document as Memory sim for restart. Cover in handler integ if FSM used for story quiz.)

4. Rama inválida no rompe el flujo, retorna al nodo anterior o maneja gracefully:
   ```python
   def test_invalid_branch_choice_graceful_no_corrupt_progress(self, db_session, sample_user):
       svc = StoryService(db_session)
       node = ...; bad_choice_id = 999
       success, msg, prog = svc.advance_to_node(uid, node.id, choice_id=bad_choice_id)
       assert success is False or prog.current_node unchanged
       # no exception, visited not polluted, points not added for invalid
   ```

5. Transiciones inválidas rechazadas (usar EventBus reciente si aplica para desbloqueos por besitos):
   ```python
   def test_invalid_transition_cost_or_vip_rejected_no_partial(self, db_session, sample_user):
       node = StoryNode(cost_besitos=9999, required_vip=True)
       ...
       success, msg, _ = svc.advance...
       assert success is False
       assert "besitos" in msg or "VIP" in msg  # graceful Lucien msg
       # no debit, no progress update
   ```
   + test on_besitos_awarded listener receives (patch schedule_emit or call directly; assert log or future side if added; use get_service(StoryService)).

**Channel Admin / VIP (channel_service, vip_service, free/VIP channels) - target 5-6:**
1. Usuario que paga accede a canal VIP y es removido del gratuito:
   ```python
   def test_redeem_vip_grants_vip_sub_and_removes_free_pending_or_access(self, db_session, sample_user, sample_free_channel, sample_vip_channel, sample_tariff):
       vip = VIPService(db_session); ch = ChannelService(db_session)
       # create free pending or sub for user
       token = ...
       sub = vip.redeem_token(token.token_code, sample_user.telegram_id)  # assume sets channel VIP
       assert sub.channel_id == sample_vip_channel.id  # or whatever
       # assert no active free pending, or channel_service marks removed; cross check
   ```

2. Usuario expirado es removido de VIP sin error aunque ya no esté en el canal:
   ```python
   def test_expire_user_not_in_channel_no_error(self, db_session, sample_user, sample_vip_channel):
       sub = ... past end_date, is_active=True
       result = vip_service.expire_subscription(sub.id)
       assert result is True
       # no exception from bot.unban if not member (mock bot or real check in integ)
   ```

3. Acción de ban propaga correctamente a ambos canales:
   ```python
   async def test_ban_user_propagates_to_vip_and_free(self, db_session, mock_bot, sample_user, sample_vip_channel, sample_free_channel):
       # via scheduler or direct?
       with patch... :
           await scheduler._process... or vip.ban_flow(mock_bot)
       mock_bot.ban_chat_member.assert_any_call(chat_id=sample_vip_channel.channel_id, user_id=...)
       mock_bot.ban_chat_member.assert_any_call(chat_id=sample_free_channel.channel_id, ...)
   ```

4. Grant/revoke durante bot offline (startup check) funciona:
   ```python
   def test_offline_grant_recovered_on_startup_expire_check(self, db_session, sample_user, sample_vip_channel, sample_token):
       # create sub with past end but active (sim offline grant/renew missed)
       sub = Subscription(..., end_date=past, is_active=True)
       expired = vip_service.get_expired_subscriptions()
       assert sub in ...
       vip_service.expire_subscription(...)  # or call scheduler private if exposed, or integ sim
       # verify inactive, entry cleared
   ```
   (extend existing subscription_expiration_detection + lifecycle integ).

5-6. Casos de múltiples suscripciones / expiración parcial:
   ```python
   def test_multiple_subscriptions_partial_expire_keeps_active_ones(self, db_session, ...):
       # 2 subs, different channels/end; expire one; assert other remains active, user still VIP via has_other
   ```
   (builds on test_multiple_tariffs + active_subscriptions_filtering + has_other in vip_service units).

## Riesgos y mitigaciones
- **Flaky tests in races (concurrent dup/credit):** asyncio.gather on SQLite (esp in-mem) often cooperative no real overlap (GIL + file lock serializes); FOR UPDATE may not contend visibly. Mitigation: use gold file-based TestSession + explicit separate sessions per task if possible; small sleep(0.01); assert "at most 1" not "exactly 1 race hit"; document "best-effort overlap on SQLite; prod Postgres stronger"; keep existing mock + constraint tests as primary; add note in test (as broadcast concurrent already does).
- **Need DB en memoria with transacciones:** db_session good for units (rollback auto), but internal commits/rollbacks in credit/debit/claim/advance break it (hence file+TestSession gold standard in atomicity etc). Mit: follow pattern exactly for all cross/gamif/narr/vip atomic/race; close/reopen pre svc calls; raw close+dispose in finally.
- **Mocking del EventBus para narrative:** Listener is side-effect log only (PoC); future desbloqueos by besitos would use it. Mit: patch("services.event_bus.schedule_emit") or "services.story_service.get_event_bus" in tests; call on_besitos... directly with payload; assert logged or no mutation to besitos (per docstring). Register in test bot.py equiv if wiring test.
- **FSM/Redis restore:** No real Redis in test env (REDIS_URL conditional); MemoryStorage in fixture is in-proc. Mit: test logic via shared storage key "restart" sim; if fakeredis in reqs-dev use it for one test; else pure unit on progress model + handler state data. Cover "if bot restarts, progress node persists in DB regardless of FSM".
- **Offline grant/revoke + ban prop:** Scheduler private _process_*, bot calls async. Mit: integ use @asyncio + patch AsyncMock bot; call exposed methods (expire, get_expired) or import scheduler bits; for startup, if bot.py has on_startup check use patch there or direct sub expire loop.
- **ID duality / fixture skew:** Story/game/vip cross use mixed .id / .telegram_id historically. Mit: enforce TG in all new setups (sample_user.telegram_id); copy DESIRED CONTRACT comments from vip tests.
- **get_service post-unif leaks:** Sub services (besito inside daily/story etc) must respect owns=False when db passed. Mit: add lifecycle test class to each unit (copy from broadcast); use with get_service(XXXService, db=...) in integ.
- **Handler msgs vs service:** "recibe mensaje correcto" for insuff is in voice/handlers (story_user etc). Mit: scope to service return (False + reason str from LucienVoice); add 1-2 handler integ if time, using make_callback + assert edit_text.
- **Flakiness tz/naive:** Use aware datetime.now(UTC) + _ensure_aware in vip/story; precedent fixed.
- **Scope creep:** Tight to 4-6/system; no broad coverage %; no handler full E2E unless critical; 0 prod.
- Overall risk low: patterns proven (GSD pre-edit, ruff, pytest -k targeted + broader smoke 0 reg).

## Scope propuesto para la primera entrega (tight, verificable)
**Fase 1 tight (verifiable, ~15-18 tests, 1-2 sessions):**
- Gamif 4-5 tests: 1 daily/gift limit+concurrent claim (extend daily unit + cross atomic); 1-2 game limits not exceed + win deduct/tx (extend game unit); 1-2 besito/ broadcast race strengthen (real gather + file if needed, insuff + tx register) + get_service lifecycle in besito/daily unit.
- Narrative 4-5: extend story unit: archetype once-only (2 variants: ending + assign_to), invalid branch/choice graceful, invalid cost trans rejected; + 1 integ FSM restore using make_fsm + progress persist; + 1 EventBus listener receive (mock).
- VIP/Channel 5-6: extend 2-3 vip integ (pay redeem + free remove cross; expire no-member no err; ban calls both ch via mock; multi/partial expire); 1-2 unit vip/channel (offline recovery, get_service lifecycle); 1 scheduler cross in free/vip integ for startup sim.
**Deliverables:** Updated test files (no new unless minimal), all passing targeted pytest -k "gamif or story or vip or channel or besito or daily or game or invariants", ruff clean, GSD logs (pre every edit), updated this memory + perhaps handoff in refactor_testing.md / fases (but scope tight, defer docs if not core). Use explicit fresh TG, file db for races/atomic, DESIRED CONTRACT, strict asserts.
**Verification:** Run: pytest -q -k "besito or daily_gift or game or story or vip or channel or cross_service_atomicity or invariants or reaction" --tb=line ; count new/updated; coverage slice increase on targeted services.
**Next (post this):** If passes, Fase2 expand to handlers E2E for msgs/FSM, property tests, full narrative quiz, real Redis if avail, more ban/ritual matrix.
**Dependencies on prior:** Relies on get_service (already), EventBus (PoC), ID contracts (fixed), atomic patterns (gold).
**No broad:** Stick to the 3 systems + listed bullets; 0 unrelated (e.g. no new trivia/streak unless overlap).

**Handoff notes (per style in atomicity/reaction/invariants):** Smallest change: extend existing units/integs (besito, story, daily, game, vip_flow*, channel, cross_atomic). Gold patterns replicated. 0 prod. GSD pre (this + future edits). Targeted gates + broader smoke 0 reg expected. Future: handler for insuff msg, real concurrent Postgres, EventBus driven unlocks in narr, full FSM Redis integ, ban handler e2e.

This analysis builds on prior subagent work (channels pre-GSD, Top10, Fase reviews). Ready for /gsd:execute-phase or implement if approved. Memory persisted for future impact-analyzer sessions.
