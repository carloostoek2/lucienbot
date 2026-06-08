---
name: item6-remaining-besito-compositions
description: Impact analysis for Item 6 (final in tirón): Unify remaining direct BesitoService compositions (tight scope: broadcast/game/daily_gift primary high-volume; reduce held/lazy to local on-demand in credit/debit methods per Reward precedent; use EventBus for obs notifications; preserve all atomicity gold contracts; 1-line test fixes; docs/decisions updates). Analysis + memory only; 0 source edits.
type: project
---

# Impact Analysis Report: Remaining Direct BesitoService Compositions Unification (Item 6)

**Date:** 2026-06-07  
**Role:** impact-analyzer (Lucien Bot)  
**Feature:** "Unify remaining direct BesitoService compositions" — focus high-volume/critical services still holding direct BesitoService (beyond RewardService/Item5 + Story listener precedent + get_service norm): broadcast_service (reactions → REACTION credits), game_service (minijuegos/dice/trivia/streaks → GAME/TRIVIA credits + bonuses), daily_gift_service (daily claims → DAILY_GIFT credits). Possibly note store (debits) but tight no-touch. Align EventBus "besitos_awarded" (post-credit best-effort), local Besito(db=) inside credit/debit methods for atomic tx control (shared db, owns=False), 0 behavior/0 atomicity change. 4th/final in tirón (max 4).  
**Context:** Post Item1 (EventBus + narrative listener + schedule_emit in credit), Item5 (Reward held removed; local only in _deliver_besitos + rewards-domain observer + central bot reg; atomicity golds gold), get_service unification, cross_service_atomicity + reaction_mission + invariants golds protecting partials ("credit survives mission/reward fail", REACTION+MISSION txs, balance deltas exact). Many services still do `self.besito_service = BesitoService(self.db)` or lazy/property for initiating credits/debits. MissionService already clean (delegates via Reward). Backpack already local on-demand. Story deliberately retains held (debit commit=False for atomic progress + credit in _grant). Streak uses locals. Handlers vary (some get_service for query, direct for admin/anon).

## Executive Summary

**Current state (post prior items):**
- EventBus: credit_besitos (any source: REACTION, DAILY_GIFT, GAME, TRIVIA, MISSION via reward, etc.) does internal commit + _schedule_besitos_awarded_event (best-effort via schedule_emit + bus.emit with gather return_exceptions=True; errors per-listener logged/swallowed; never affects credit return, never rolls back). Payload standard (user_id, amount, source.value, reference_id, description, timestamp).
- Listeners so far: narrative (on_besitos_awarded_from_gamification in story_service.py; obs log only; "MUST NOT credit/debit"; registered central in bot.py on_startup) + rewards (on_besitos_awarded_rewards_observer post-Item5; same contract for MISSION deliveries).
- Reward precedent (Item5): removed held `self.besito_service` from __init__ (Package/VIP untouched); `_deliver_besitos` uses local short-lived `besito_service = BesitoService(db=self.db)` (shared for owns=False); close getattr harmless; added domain listener + reg; 1-line test fix in unit reward; 0 atomic impact (credit still sync inside deliver; MISSION tx + history + return msg/balance identical; partials "credit survives deliver=False" preserved).
- Story precedent: still holds (used for pre-advance get_balance + debit(commit=False) + credit in _grant_achievement); added listener for obs (no mutation).
- get_service: standardized (reduces leaks); many handlers use `with get_service(X) as svc`.
- Atomicity contracts (gold in test_cross_service_atomicity.py + reaction_mission_flow + invariants): Credit (REACTION/DAILY_GIFT etc.) commits independently inside besito.credit; post-credit mission progress+deliver (separate tx via increment_and_deliver in broadcast path) + bus listeners are best-effort. Partial failure explicit/desired (e.g. reaction credit + progress can survive inactive reward/ stock=0/ deliver False/ mission error; no rollback of prior credit; no exception to reaction handler). Tests use file SQLite + TestSession reopen + raw close/dispose for cross-commit visibility. Local "besitos_awarded" field in BroadcastReaction/reaction_result dicts is *per-emoji value* (distinct from bus event name; unchanged).
- Direct held sites (from full grep): broadcast (held in __init__, 2 credit sites in register_reaction + check_and_register_reaction), game (held in __init__, 4+ credit sites in play_dice/play_trivia + streak bonuses; +1 local in _build_streak_failure_state for has_sufficient), daily (lazy @property creating on _get_db; used in claim_gift), store (held via _init_services; balance checks + debit in complete_order), story (held), backpack (local inside get_backpack_summary — precedent good), streak (local inside claim), mission (0 direct), reward (now fixed to local), + some handlers (direct BesitoService() or get_service for queries; scope services only), tests (direct access for patch/balance).
- High-volume/critical user-facing: reactions (broadcast + auto-mission), games (dice/trivia daily limits + streaks + promo hooks), daily gift (24h claim). Store debits also critical (purchase atomicity with stock/deliver).

**Key outcome of analysis:** Tight unification feasible for top 3 (broadcast/game/daily) by replacing held/lazy with local `BesitoService(db=...)` *inside the specific credit/debit methods only* (preserves: credit's internal commit + source + ref + schedule_emit + return bool/balance/msg; caller's tx context for record/claim/order; atomic "credit survives later failure" contracts). For post-award obs, add 1-2 domain listeners (e.g. broadcast/game) if high-value (pure log; MUST NOT mutate besitos; central reg in bot.py). 0 prod behavior change. Verifiable via re-runs of golds + unit + 1-line test patches for direct .besito_service accesses (precedent from reward unit + atomic daily hasattr fallbacks). Aligns rules: services own domain (credit/debit stay in besito; broadcast owns reaction record+credit+mission inc; game owns play+record+credit; daily owns claim+credit), EventBus for cross *notifications* (not delivery), get_service lifecycle where appropriate, <50 LOC (local inst is 1 line), logging, no handler logic.

**Overall recommendation:** Proceed with *tight scope* (broadcast + game + daily_gift core only; locals inside credit paths; optional 1-2 obs listeners + reg; minimal 1-line test fixes + hasattr guards for compat; targeted docs/decisions/CLAUDE updates; no store/mission/story/backpack/handler changes; re-execute exactly the atomic/reaction/daily/game/besito/event paths). 0 atomicity/partial-failure impact. Ready for GSD executor (4th/final in tirón).

## Riesgos Clave (énfasis atomicity + best-effort + loops)

1. **Atomicity breaker if credit/debit moved out or made best-effort:**
   - Riesgo: In broadcast: credit inside check_and_register_reaction (before main db.commit; reaction record + credit conceptually together; then best-effort mission tx separate). register_reaction legacy path also. Daily claim_gift: claim insert + credit (commit only on credit success) + get_balance. Game play_*: credit(s) then GameRecord insert + commit (streak bonuses multiple credits before record). Store complete: balance check + debit (commits inside) + stock + deliver + order update. If refactored to "emit intent" + listener does credit: best-effort (schedule may noop if no loop, listener err swallowed, no await) → credit may not happen or post-return → cross_atomicity happy fails (no REACTION/DAILY/GAME tx, balance delta=0, "credit survives" partials broken, reaction_result["besitos_awarded"] wrong or missing, mission not triggered from reaction, purchase fails silently, daily claim returns success without besitos). Callers (handlers) see wrong Lucien msg/balance.
   - Mitigación (required, per Reward precedent): **Keep direct synchronous credit_besitos / debit_besitos call using *local* BesitoService(db=shared) inside the exact method** (e.g. inside check_and_register_reaction try, inside claim_gift, inside play_dice_game / play_trivia / streak bonus blocks). Local shares db for owns=False (close harmless); credit still does its *internal* commit + schedule exactly as held did. Debit in store uses default commit=True. This keeps "post-credit best effort" contract identical (mission inc + listeners after credit commit).
   - Additional: In broadcast check_ path, the second mission tx is *already* best-effort (try/except around increment_and_deliver; logged warning only; reaction credit not rolled). Atomic golds assert exactly that.

2. **Listeners that fail or mutate affect delivery / create loops:**
   - Riesgo: New listener (broadcast/game domain) raises → (erroneously) thought to impact credit. Or future code in listener does credit/debit (loop with own reaction/game/daily award path; or double-count if source filter absent; esp dangerous for high-volume like reactions/games).
   - Mitigación: Bus contract already: gather(return_exceptions=True); per-listener warning only; never to schedule_emit caller or credit return. Listener contract (copy exact from narrative/rewards): "purely observational + wiring proof"; "MUST NOT credit, debit, or mutate besitos state here" (explicit in docstring + comment block); "best effort, non-authoritative; 0 impact on ... contracts". Log only (e.g. "broadcast | besitos_awarded_received | ... | source=REACTION"). Source in payload allows future filter (e.g. ignore own REACTION if extending), but PoC=log. Registration central/explicit in bot.py (no import side-effects). Duplicates tolerated by bus. Removability: delete listener def + 1 register line + import = zero residual.

3. **Test breakage + patching assumptions + daily special casing:**
   - Riesgo: Code/tests doing `svc.besito_service` or `patch.object(svc.besito_service, "credit_besitos"...)` or `hasattr(service, "besito_service")` break post-removal of held. Daily uses lazy property (not __init__ attr always) + explicit hasattr fallbacks in unit concurrent + cross atomic daily subtests; also patch.object(daily_svc.besito_service...) for credit-fail rollback test. Broadcast reaction_flow unit has assert hasattr + _owns_session=False (get_service lifecycle gold). Store unit has 1 direct balance assert. Game units: 0 direct .besito access (assert on return dicts + db records; good). Cross atomic uses independent BesitoService(db) for most queries but daily paths special-case the property.
   - Mitigación: 1-line fixes only (precedent reward unit + atomic hasattr): change access sites to independent `BesitoService(db=...).get_balance(...)` or keep/update hasattr guards for the property case (e.g. `daily_svc.besito_service if hasattr... else BesitoService(db).get...`); for patch sites targeting the credit inside claim: switch to `patch("services.daily_gift_service.BesitoService")` (or patch the claim_gift internal) or patch.object on a temp local if needed. Atomic daily subtests already have the fallback pattern (post-Item5 awareness). Re-run (no edit) suffices for game units. Lifecycle/close: services with injected db never close() in most tests (precedent); removing held reduces one sub.close call (safe). schedule_emit patches in atomic/besito will still fire from the *local* credit calls inside broadcast/game/daily methods.
   - No pollution of atomic golds: local credit still emits schedule exactly; patch around reaction/claim covers it.

4. **Duplication / source confusion / best-effort visibility in tests:**
   - Riesgo: Multiple credits (e.g. game trivia + streak bonus both GAME source) emit multiple events; listeners receive all (incl. own domain's); tests using patch schedule_emit around one path may count more (but asserts are usually "called" not exact count). "besitos_awarded" event vs local field confusion (already documented in decisions + atomic docstrings + reaction tests).
   - Mitigación: Payload has source + ref; listeners log full. Tests already tolerant (e.g. atomic happy asserts mock_sched.called + exact tx counts from models, not event count). Keep distinction docs. No change to local reaction_result["besitos_awarded"] (per-emoji).

5. **Other (minor):**
   - Removability of bus + pattern: adding 1-2 listeners + 2-3 register lines = easy revert (zero residual on services).
   - get_service: no impact (listeners global to bus; services with db= injected don't expose besito publicly after change).
   - Performance: local Besito per credit (rare per user action) = negligible.
   - Scope creep: tight = do not touch store (debit critical for purchase), story (atomic commit=False debit), mission (already clean), backpack (already local), handlers (some direct but out of scope; they should prefer get_service for queries).
   - VIP/anon handlers create direct Besito (e.g. for cost checks); not in tight scope.

**Mitigación general:** Tight scope + "0 prod / 0 atomic change" + re-execute *exactly* the tests covering credit paths (unit broadcast reaction_flow + daily claim/concurrent + game trivia, cross atomic full (daily+reaction+reward), reaction_* flows, invariants, besito unit (schedule patches), event_bus unit (extend for new listeners), mission_e2e, store if borderline). GSD workflow + ruff + pytest gates before edits (here analysis + memory only). Follow Reward/Item5 structure verbatim for consistency.

## Mapa de Impacto (archivos, cambios, listeners)

**Core services (tight primary scope: broadcast/game/daily only):**
- `services/broadcast_service.py` (high-volume reactions; critical for cross atomicity gold + mission auto-deliver):
  - Keep import (or lazy inside methods).
  - `__init__`: delete `self.besito_service = BesitoService(self.db)` line. Add detailed comment (modeled on reward): "# Held direct BesitoService composition reduced (Item 6); REACTION credits now use local on-demand BesitoService(db=self.db) *only* inside register_reaction / check_and_register_reaction (preserves atomicity: credit internal commit + REACTION tx + best-effort mission inc + schedule_emit; local 'besitos_awarded' in reaction dict unchanged). close() getattr will be harmless."
  - `register_reaction` (legacy?): replace `self.besito_service.credit_besitos(...)` with local `besito_service = BesitoService(self.db); besito_service.credit_besitos(...)` inside the try (before/around the db.commit).
  - `check_and_register_reaction` (primary path): same — local inside try (credit before main commit; note mission inc already separate best-effort after).
  - `close()`: the `for sub in (getattr(self, "besito_service", None),):` becomes no-op (None); leave verbatim or update comment minimally ("Cerrar subs (inofensivo...)").
  - (No logic change; return dicts, logs, reaction record identical.)
  - Optional high-value: add at bottom (broadcast domain ownership, parallel to story/reward):
    ```python
    async def on_besitos_awarded_for_broadcast(payload: dict) -> None:
        """Broadcast-domain listener for 'besitos_awarded' (incl. our own REACTION credits).
        Best-effort, observational only. Log + future e.g. stats. MUST NOT credit/debit (avoid loops).
        """
        uid = payload.get("user_id")
        amt = payload.get("amount")
        src = payload.get("source")
        ref = payload.get("reference_id")
        logger.info(f"broadcast | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}")
    ```
  - Exports/docstrings: minor (note EventBus participation for reaction credits).

- `services/game_service.py` (high-volume minijuegos; dice + trivia + streak milestones + VIP variants):
  - `__init__`: delete held `self.besito_service = ...`; keep other _user/_vip; add comment analogous ("GAME/TRIVIA credits now local on-demand inside play_* methods...").
  - `play_dice_game`: local for the win credit (if won: besitos=...; besito=BesitoService(self.db); credit...).
  - `play_trivia`: locals for correct credit + (inside if is_correct and streak in milestones) the bonus credit(s). (Note: multiple credits per play possible; each emits independently.)
  - `_build_streak_failure_state`: already uses local `besito_service = BesitoService(self.db)` for has_sufficient_balance — keep/consistent.
  - `close()`: remove besito from the for-sub tuple (or leave getattr safe).
  - (0 change to limits, streak calc, record payout, promo hooks, return dicts with "besitos"/"besitos_total". Credits still before record commit.)
  - Optional high-value listener (game domain): similar `on_besitos_awarded_for_games` logging GAME/TRIVIA sources; "MUST NOT...".

- `services/daily_gift_service.py` (daily claims; 24h cooldown; concurrent gold in atomic + unit):
  - No __init__ held (uses lazy property + _besito_service_instance).
  - Refactor property or deprecate: inside `claim_gift` only, use local `besito_service = BesitoService(self._get_db())` (or self._get_db() passed); replace `besito_service = self.besito_service` + uses. Keep property for now (backward for any external) or remove if no other uses (grep shows only claim + test accesses).
  - Update docstring for claim_gift / property.
  - `close`: no change (property internal).
  - (Credit + claim insert + commit on success + balance in msg identical.)
  - Optional: listener `on_besitos_awarded_for_daily` if value (DAILY_GIFT source obs).

- `services/store_service.py` (NOT in tight primary scope per recs; noted for completeness):
  - Still holds via _init_services; uses for get_balance (pre-purchase checks in direct/create) + debit in complete_order (PURCHASE, commit=True inside).
  - Debit is authoritative for purchase atomic (debit + stock with_for_update + deliver + order COMPLETE + low-stock alerts). Similar risk profile to broadcast credit.
  - If future item: local inside complete_order (and checks) + keep held for other? or full reduce. Test impact: 1 assert in unit store_service.
  - Backpack already does local for balance in summary (good pattern).

- Other services (0 change in this item):
  - `mission_service.py`: already 0 direct Besito (delegates increment → reward.deliver for BESITOS; clean post-Item5).
  - `story_service.py`: retain held (debit commit=False for atomic advance_to_node progress+cost; credit in _grant; listener already present).
  - `backpack_service.py`: already local on-demand in get_backpack_summary (besito for balance); leave.
  - `streak_promotion_service.py`: uses local inside claim_for_streak for debit; leave.
  - `reward_service.py`: post-Item5 state (local only in _deliver_besitos); listeners already 2 (narrative+rewards).
  - `besito_service.py`: no change (the emitter).
  - `event_bus.py`: no change (supports N listeners).

**Registration / bootstrap (if adding 1-2 listeners):**
- `bot.py`:
  - Add imports e.g. `from services.broadcast_service import on_besitos_awarded_for_broadcast` (and/or game).
  - In on_startup (after rewards/narrative registers): add the new one(s).
  - Update comment: "Fase 3 of eventbus-poc + Item 5 + Item 6: narrative, rewards, broadcast/game".
  - Log: extend "Event listeners registrados (besitos_awarded -> narrative, rewards, broadcast)".
  - (If no listeners added in tight: 0 change to bot.py.)

**Docs (must update for accuracy + cross-cutting rule):**
- `services/CLAUDE.md`: Expand "Cross-cutting: Internal EventBus" to list current subscribers (narrative, rewards, + broadcast/game if added) + note "other initiators (broadcast reactions, game plays, daily claims, store debits) use local Besito on-demand inside credit/debit (Item 6) or retained held for atomic reasons (story)".
- `services/gamification/CLAUDE.md`: Add/update "Cross-domain notifications" section (or extend existing EventBus para); note consumers (narrative, rewards) + initiators now using local pattern (broadcast/game/daily as primary post-Item6); "broadcast/game/daily own their credit paths + emit; listeners obs only".
- `services/broadcast/CLAUDE.md`: Add section at end "## Cross-domain notifications (EventBus PoC + Item 6)" modeled on gamif/narrative: "Broadcast initiates REACTION credits via local Besito inside check_and_register_reaction/register (for atomic record+credit); this emits besitos_awarded; [if listener] owns listener here for post-credit obs; registration central in bot.py; best-effort + MUST NOT credit/debit; ref event_bus + decisions + atomicity golds (credit survives mission fail)."
- `services/store/CLAUDE.md`: Optionally note the debit path + besito use (pre complete_order); "atomic with stock/deliver"; future unification possible.
- `services/missions/CLAUDE.md`: Already has cross from Item5; minor cross-ref if needed ("see also gamif initiators like broadcast/game/daily using local pattern").
- `services/narrative/CLAUDE.md`: Minor update or cross-ref to list of listeners.
- `decisions.md`: Append full entry after the Item5 reward one (Motivo/Riesgos/Decisión/Resultado style, refs to Item1/5 + this report + golds + PLAN if any; emphasize tight scope, locals preserve atomicity, 1-2 listeners optional high-value, 1-line tests, 0 behavior/0 atomicity).
- Optional: root CLAUDE.md / architecture (high-level no); fases_refactor_testing.md append for the item.

**Other (low/no impact):**
- Handlers (broadcast_handlers, gamification_*, game_user_handlers, daily via gamif): call 1 service (broadcast/game/daily); no direct besito access on them post-get_service norm; 0 changes. (Some legacy direct Besito in admin/vip handlers for queries — out of scope.)
- `services/__init__.py`: no change (exports already).
- Tests using independent BesitoService(db) for post-asserts (most integ + atomic queries): unaffected.
- No new files.

**New artifacts (minimal):**
- This report + MEMORY.md pointer.
- (If listeners: defs live in their service.py files, ownership domain.)

**0 prod behavior change expected.** All returns, tx sources (REACTION/DAILY_GIFT/GAME/TRIVIA), balances, Lucien msgs, reaction_result dicts, mission auto-deliver on reaction, daily cooldowns, game limits/streaks/payouts, purchase debits identical. Only internal structure (no more held collaborator on these 3) + optional obs + docs.

## Tests Críticos Afectados o a Actualizar

**Affected (must 1-line fix for green; tight):**
- `tests/unit/test_broadcast_service_reaction_flow.py`:
  - `test_composer_sub_closes_are_harmless_for_passed_db`: `assert hasattr(svc, "besito_service")` → change to `assert not hasattr(svc, "besito_service") or svc.besito_service is None` (or remove if only for this; keep test for get_service lifecycle on broadcast itself). Comment "# post Item6 held reduction".
- `tests/unit/test_daily_gift_service.py`:
  - `test_claim_gift_success`: `balance = service.besito_service.get_balance(...)` → `balance = BesitoService(db_session).get_balance(...)` (add import if needed; or use service.get_gift_amount() no — needs real balance post-credit).
  - `test_concurrent_first_claims...`: the bal = (service.besito_service... if hasattr else ...) → update fallback or use independent; keep the <=10 assert.
- `tests/integration/test_cross_service_atomicity.py` (gold; daily atomic sub-tests):
  - Daily happy/fail paths: `daily_svc.besito_service.get_balance` (with hasattr) + `patch.object(daily_svc.besito_service, "credit_besitos"...)` → update to use the fallback pattern already partially present (e.g. `BesitoService(db).get...`); for patch, change to `patch("services.daily_gift_service.BesitoService", ...)` or patch inside claim path. The "if hasattr ... else BesitoService(db)" already in some places (line ~726-729); extend it. No change to REACTION paths or main asserts (tx counts, deltas, "credit survives").
  - Other atomic (reaction + mission, reward): use independent Besito mostly; patch schedule around reaction will cover subsequent emits from game/daily if exercised; no edit needed.
- `tests/unit/test_store_service.py` (if store touched or for completeness; 1 site):
  - `assert service.besito_service.get_balance(...)` in complete_order test → `BesitoService(db=...).get...` (1-line + import).
- Game units (`tests/unit/test_game_service.py`): 0 direct .besito_service accesses (grep confirmed; they patch load_questions, assert return["besitos"], query GameRecord/BesitoTransaction directly in some, call close()). Re-run only for coverage of credit paths post-refactor. Good.

**Strongly recommend extend/verify (no breakage, coverage for wiring + regression on atomic/credit flows):**
- `tests/unit/test_event_bus.py`: If 1-2 new listeners added: extend `test_narrative_listener...` or add parallel `test_broadcast_listener_is_invoked...` / game (fresh bus, register the on_..., emit with source=REACTION/GAME, assert log "broadcast | besitos_awarded_received | source=REACTION").
- `tests/unit/test_besito_service.py`: schedule_emit patches exercised more (via new credit sites); no edit.
- `tests/integration/test_reaction_mission_flow.py`, `test_reaction_full_chain.py`, `test_reaction_limit.py`, `test_invariants.py`, `test_mission_e2e.py`: indirect (reaction credits trigger missions; daily/game may be in flows); re-run targeted to confirm REACTION/DAILY txs + balances + no double-credits.
- `tests/integration/test_cross_service_atomicity.py` full (beyond daily): happy_path_reaction... (patch schedule captures REACTION + any MISSION; assert called true; tx counts + deltas verify credit inside); daily sub-tests as above.
- `tests/handlers/...` (gamif integration, store_user mocks): they mock at handler level or use real via get_service; no .besito on broadcast/game/daily instances exposed.
- General: `tests/conftest.py` (no change); ensure db_session / TestSession work (they do for locals).
- New tests? (tight: minimal/none for green gate): None strictly. Listener wiring covered by extending event_bus (like narrative). If easy: 1 assert in atomic happy after patch that "besitos_awarded" event count >=1 for the source, but not required (existing schedule + model tx asserts suffice).
- No handler test changes (credit not directly callable from most user paths in units).

**Gates for this item (as prior):** ruff clean + format; pytest -q -k "broadcast or daily_gift or game or atomicity or reaction or mission or besitos_awarded or event_bus or store_complete or invariants" (or broader) pass; targeted cross flows (reaction_mission, daily atomic, game trivia streaks); bot import/smoke + manual register+emit if listeners; greps for 0 "self.besito_service = BesitoService" in the 3 services, local "BesitoService(self.db)" present in credit methods, listener blocks if added + "MUST NOT", register lines + log, 1-line comments in tests, docs sections; GSD pre every; self-check. 0 unintended prod impact.

**Coverage lift:** These paths already exercised (reaction golds, daily concurrent/atomic, game units recent, besito, cross); this tightens collaborator surface + adds listener parity if chosen. Atomicity golds untouched (gold).

## Riesgos y Mitigaciones (detallado; ver también Executive)

(Repeated/expanded from above for standalone report; same mitigations apply.)

- Atomicity / partial contracts (gold tests): Mitigated by locals inside methods only + credit's internal commit always. Re-execute full cross_service_atomicity + reaction chains + daily subtests + invariants (I1-I3 besito, I6 reaction).
- Best-effort drops / schedule in no-loop tests: Mitigated by patch("...schedule_emit") around the caller (reaction/claim/play) in golds; asserts are "called" or tx presence, not strict listener side. schedule_emit debug-logs when no loop (acceptable in pure unit).
- Test pollution / direct access: 1-line fixes + hasattr guards (daily already had them); use independent BesitoService(db) for queries (already pattern in most integ/atomic).
- Loops / re-entrancy: Explicit "MUST NOT credit/debit" contract in listener docstrings + CLAUDEs + decisions; source= allows future guard; PoC only logs.
- Removability / conservative: Yes (bus + listeners easy delete; locals are just "BesitoService(db=)" which was already done in backpack/reward internals).
- 0 change to local reaction "besitos_awarded" field vs bus event: Documented; tests distinguish (model field vs event).
- Handlers / get_service: No exposure of internal besito on the service instances after; callers unaffected.
- Future extensions (e.g. backpack hint on award, stats): Belong in listeners using get_service or models (fresh session if needed); not mutate besitos.

## Scope Propuesto para la Entrega (tight, verificable, alineado con EventBus + get_service + Reward precedent; lista de cambios mínimos)

**Tight scope (mínimo verificable, 0 comportamiento observable cambiado, sigue "services dueños de dominio" + "menos acoplamiento directo held" + EventBus para cross notifications + atomicity contracts gold):**

1. **services/broadcast_service.py (principal, high-volume):**
   - Remover línea de composición en `__init__`.
   - Refactor the two credit sites (`register_reaction`, `check_and_register_reaction`): crear instancia local corta-vida `besito_service = BesitoService(self.db)` justo antes del credit call (dentro del try; preserva el commit flow y el besitos_awarded local en dict).
   - Actualizar close y docstrings/comments (incluyendo "Item 6").
   - (Opcional high-value tight): añadir listener `on_besitos_awarded_for_broadcast` al final + comment block "MUST NOT credit/debit".
   - (Opcional: actualizar broadcast/CLAUDE.md inline.)

2. **services/game_service.py (principal):**
   - Remover held en `__init__`.
   - Refactor credit sites en `play_dice_game` (win), `play_trivia` (correct + streak bonus block): locales `besito_service = BesitoService(self.db)`.
   - _build_streak_failure_state ya usa local — consistente.
   - Actualizar close + comments.
   - (Opcional): listener `on_besitos_awarded_for_games`.

3. **services/daily_gift_service.py (principal):**
   - En `claim_gift`: usar local `besito_service = BesitoService(self._get_db())` (reemplazar self.besito_service = self... y usos); mantener property por compat o deprecate con comment.
   - Actualizar claim_gift doc + property comment.
   - (Opcional): listener para DAILY_GIFT.

4. **Tests (mínimo para verde + wiring):**
   - 1-line fixes (or hasattr updates) en: test_broadcast_service_reaction_flow.py (lifecycle assert), test_daily_gift_service.py (2 claim/bal sites), test_cross_service_atomicity.py (daily atomic access + patch sites; extend existing fallbacks), test_store_service.py (1 if including or note).
   - Si listeners: extender test_event_bus.py con 1-2 tests análogos (fresh bus + register + emit + assert log "xxx | besitos_awarded_received").
   - Re-ejecutar (sin más edits): los units de broadcast/daily/game, cross atomicity full, reaction_*_flow / full_chain / limit / invariants, mission_e2e, besito (patches), event_bus, store unit. Confirm: credits still produce correct tx source + balance delta + schedule_emit; no double; partials (credit survives) intact; listeners (existing + new) invoked; no .besito_service held exposed on the 3 services.

5. **Docs + bootstrap (mínimos obligatorios):**
   - services/CLAUDE.md (expand EventBus section).
   - services/gamification/CLAUDE.md (cross-domain section or extend).
   - services/broadcast/CLAUDE.md (new cross-domain subsection).
   - decisions.md (append Item 6 entry, exact style of Item5).
   - bot.py (imports + registers + log update *only if* adding the 1-2 listeners; otherwise 0).
   - (Opcional tight: store/CLAUDE note, missions cross-ref.)

**No scope (out of tight):**
- No tocar store_service (o solo 1-line test si se quiere; debit path out), story (retained for atomic debit commit=False), mission/backpack/streak (already good or clean), reward (post-Item5), handlers (even direct Besito creations), other services.
- No cambiar contratos de play_*/claim_gift/check_and_register_reaction/complete_order, tx sources, return values, local "besitos_awarded" fields, mission increment_and_deliver, or atomic partials.
- No mover créditos fuera de sus métodos (rompería ownership + atomicity).
- No inyección de bus (sigue singleton PoC + central register).
- No nuevos archivos de test o handlers.
- No updates a atomicity tests más allá de los 1-line accesses + re-runs (contratos intactos).
- No close() calls nuevos en tests.
- Futuro (post-entrega): aplicar a store; listeners con lógica real (e.g. refresh hints); property tests "nunca REACTION sin BroadcastReaction row"; full unification sweep; get_service for game/broadcast in more handlers.

**Verificabilidad de la entrega:**
- Post-cambio: `BroadcastService(db).besito_service` (y equiv para game) → AttributeError or None; daily property may remain but credit uses local.
- `check_and_register_reaction` / `play_trivia` / `claim_gift` siguen retornando éxito + besitos correctos + txs + schedule; reaction dicts idénticos.
- `get_event_bus()` tiene N listeners (existing +1-2); emitir uno con source=REACTION causa logs de "broadcast | ..." (si added).
- Todos los tests de reaction atomic/golds + daily claim/concurrent/atomic + game trivia + cross flows + besito + event_bus pasan sin reg.
- Grep: 0 "self.besito_service = BesitoService" en los 3 services; locals presentes en los métodos de crédito.
- Ruff limpio; imports bot limpios (si listeners); logs convención; 0 diffs en comportamiento para visitantes/custodios (reacciones dan mismos besitos + misiones, juegos mismos payouts/límites, daily mismo claim).
- Atomic golds: REACTION + DAILY tx counts exact, balances deltas, "credit survives" partials, schedule called, no double credits.

**Alineación:**
- Reglas: handlers 1-service (ya), services dueño dominio (broadcast owns reaction+credit+mission-inc; game owns play+credit+record; daily owns claim+credit; besito owns credit/emission), <50 LOC (local cabe), logging, EventBus para cross notifications (no duplicación de delivery), get_service donde lifecycle.
- Voz Lucien / arquitectura: sin cambios visibles.
- GSD: este análisis es pre-edit (report solo en memoria); cualquier impl futura usaría /gsd:execute-phase o quick + gates (este es 4th/final en tirón).
- Removable: sí (bus + listeners + pattern).
- Precedents: Reward (Item5 local+listener), backpack (local), narrative (listener), atomic golds (credit best-effort post).

Este scope es la "entrega tight" recomendada: reduce composiciones directas (held → local on-demand en paths de crédito), incorpora dominios broadcast/game/daily al patrón EventBus (si listeners high-value), mantiene atomicidad 100% y contratos de partial-failure de los golds, mínimo churn en tests (1-line), verificable inmediatamente. Lista explícita de tests críticos a re-correr post-impl: full cross_service_atomicity, test_reaction_mission_flow + full_chain + limit, test_daily_gift_service (claim+concurrent), test_broadcast_service_reaction_flow + unit, test_game_service (trivia paths), test_besito_service, test_event_bus (extended), test_invariants, mission_e2e, bot smoke + register.

**Handoff:** Listo para GSD + impl si se aprueba (usar /gsd:execute-phase o quick con gates). Persistido en agent-memory para contexto futuro (ver MEMORY.md actualizado). Cierra el batch de EventBus / reduce-compositions follow-ups (Item1/5 + este 6). 0 prod impact; contratos de atomicity (gold) preservados.

---
**Fin del reporte de impacto (Item 6).** Hecho con precisión para preservar contratos de Lucien Bot.
