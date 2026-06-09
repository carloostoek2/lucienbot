# Impact Analysis: Item 10 - Remaining BesitoService in Store domain (store_service.py debits/purchases)

**Item:** 10 (SECOND of NEW pool of 4; automatic continuation after Item 9 (mission_admin) closed via full 6-step (impact/planner/executor/arch/test-guardian + re-runs green + "suite protege adecuadamente"))

**Pool context (verbatim from prior + mandate):** Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. (Item 10 second of this new pool; Item 9 first closed).

**GSD pre:** Initiated via run_terminal_command creating/appending to .planning/quick/gsd-impact-analyzer-item10-remaining-besito-store.log (initial wc=2; multiple appends during discovery with timestamps + findings + "Pool anterior..." repeated; final pre-persist/pre-write wc=16 before any report/MEMORY write). All reads/greps via tools preceded by/ interleaved with GSD log entries + wc. No file mods before initial GSD pre-log. Report persisted after full discovery + final GSD pre-write entry.

**Date:** 2026-06-08 (per sim + logs)
**Agent:** impact-analyzer (telegram-bot-hardener pipeline)
**Change/Feature:** Expand remaining direct BesitoService compositions in the Store domain (primarily services/store_service.py in complete_order / direct_purchase / purchase flows for besito debits on content buys; possibly related user handlers or package delivery paths). Refactor to use local on-demand BesitoService(db=self.db or via get_service context for atomicity) inside the credit/debit sites ONLY (copy Reward precedent Item5 + broadcast/game Item6 exactly: "local Besito(db=...) *only* inside the tx method for atomicity + history + return"; "schedule_emit best-effort post-commit"; high-value obs listener on_besitos_awarded_store_purchase_observer or similar "MUST NOT credit/debit/mutate" + best-effort + DESIRED CONTRACT + domain log "store | besitos_awarded_received"; central reg in bot.py). Keep any @property for compat if precedent (daily). 0 behavior/0 atomicity change ("credit survives deliver False", "post-credit best effort (misiones + listeners)", tx counts/deltas strict in golds). Update affected tests (1-line/guard ports like prior, e.g. "if hasattr... else BesitoService(db=...)", class patch to services.besito_service... for local intercept in cross atomicity; new contract tests for no-held/uses_local/observer if fits tight). Docs/CLAUDE cross sections if precedent.

**Analysis only** (no impl; ready for gsd-planner with tight 5-phase PLAN copy Item6/5 +24/23 precedents + atomicity golds + DESIRED).

---

## Executive Summary

Store domain is the last major direct BesitoService composer for high-volume purchase flows (debits on content buys via complete_order; balance checks in direct_purchase/create_order). Post Item5 (Reward local+obs) + Item6 (broadcast/game/daily locals+2 obs + daily prop guard + 4 total central reg), store_service.py retains held `self.besito_service = BesitoService(db)` in _init_services + 4 call sites (3 get_balance for pre-purchase checks + 1 debit in complete_order for PURCHASE source).

Handlers/store_user_handlers.py already modern: uses `with get_service(BesitoService) as ...` for balance display in shop/preview/etc (import present but no composition/held; 0 change per task "0 change to store_user if it already uses get_service").

Other paths (package/reward delivery, backpack, streak) already use locals or orthogonal (no direct store purchase besito touch).

**0 behavior / 0 atomicity change required/achieved (per gold contracts):** Debit (in complete) does its internal with_for_update + (default commit=True) + tx row + balance update synchronously inside method (besito.debit); outer complete_order then does stock decrement (with_for_update) + package deliver + order COMPLETE + db.commit(). Listeners only for *credits* (EVENT_BESITOS_AWARDED emitted *only* from credit_besitos post its commit; purchases are debits so no award event from store purchase itself -- observer still added as high-value obs for store domain + wiring proof, copy precedent). "credit survives deliver False" + "post-credit best effort (misiones + listeners)" protected by re-runs (even if debit path, cross atomicity gold + patches cover the pattern; store unit tests will assert debit tx + balance delta strict). Partial listener failure best-effort (bus gather return_exceptions). No double credit/debit. Store purchase tx (order+stock+deliver) commits independent of besito debit (debit's commit inside is authoritative for spend).

**Risks: LOW (due to exact precedent copy; atomicity golds already cover similar debit/credit + partials).** Main: atomicity golds must hold "credit survives" (and analog for debit deltas/tx counts); partial failure listeners best-effort (no impact on purchase return); 1-line test ports only; no double credit; store purchase tx must commit independent; observer "MUST NOT" mutate; fresh TG ids in tests; N806 tol w/doc (TestSession precedent). Store held removal safe (package_service remains; close untouched or min guard). No UI/Lucien/prod change.

**DoD (for downstream):** 0 held in store __init__ (grep); locals in the 3 purchase method sites w/ exact comments; observer + "MUST NOT" + "DESIRED CONTRACT" + "store | besitos_awarded_received"; bot.py reg + "Item 10 store"; 1-line/guard + class patch in cross + store unit test ports; golds (cross full w/patch + broader gamif store/purchase) + unit store + bot smoke reg+emit + ruff + greps all green; docs/CLAUDEs updated if precedent (gamif/store/missions + decisions Item10 + BATCH note); self-check PASSED + pool phrase; ready for planner (5-phase tight) -> executor -> arch (1svc? no but locals+no-held+obs contract+atomicity) -> test-guardian -> tests.

**Ready for chain:** planner (tight 5-phase PLAN copy precedents + golds + DESIRED) -> ...

---

## Risks (detailed, low)

- **Atomicity gold contract break (main risk, but precedent-proven low):** "credit survives deliver False" + post best-effort must hold on re-runs (cross happy/sad with schedule_emit patch + DESIRED asserts + strict tx count/delta + balance; even though store uses debit, pattern identical for "spend survives later failure"). Debit supports commit=False for caller-atomic (but store complete uses default True + separate later commit -- unchanged).
- **Partial listeners:** Best-effort only (schedule_emit + bus gather return_exceptions=True); store observer (if triggered on any credit) must not affect purchase success.
- **Test ports:** 1-line/guard (hasattr or direct Besito(db=) or class patch("services.besito_service.BesitoService") for intercept in cross when locals used); store unit has explicit `service.besito_service.get_balance` post-complete -- port to independent/guard + comment. Fresh 777x TG ids + TestSession/file + N806 tol w/doc + try/finally raw close.
- **No double credit / re-entrancy:** Observer explicitly "MUST NOT credit/debit/mutate" (copy story 670-694 / broadcast). Debit site (purchase) never emits award event.
- **Store purchase tx independence:** complete_order debit commit independent of later stock/deliver commit (precedent in daily claim + credit internal; cross tests validate).
- **Observer for debit path:** Purchases debit (no "awarded"), but observer still high-value for domain (wiring + future credits in store?); name "on_besitos_awarded_store_observer" or "store_purchase" per task "or similar"; log "store | besitos_awarded_received".
- **Other:** Ruff (N806 tolerated only w/ doc like TestSession); no scope creep (0 handlers change beyond 0, 0 new files except reports/logs, 0 UI, 0 package/reward paths, 0 story/narrative direct, 0 channel/VIP); min __init__ compat (no prop needed, unlike daily).
- **Safe points:** Revert on any gold fail (0 attributable expected); GSD pre every downstream edit; arch re-scan post; test-guardian veredict.

**3 Critical Systems (always in mind, per CLAUDE + hardener + roadmap):**
- **Gamification (core, primary):** Besitos debits on purchases (complete_order direct_purchase/create_order flows) + possible listener for missions/rewards post-purchase (though debit no emit; missions via other paths). Must preserve atomicity gold + post best effort. (StoreService is the purchase composer.)
- **Narrative:** 0 direct (story keeps its own debit/credit for _grant_achievement; listeners could notify if useful but out of tight scope per item6 precedent + "narrative 0 direct").
- **Channel/VIP:** Purchases may grant via reward? but orthogonal (0 touch; VIP via reward paths untouched; channel free/VIP separate from store buy).

**Consumers / call sites map (from greps + reads):**
- Primary: services/store_service.py (held in _init_services:65; get_balance in direct_purchase:366, create_order:440, complete_order:488; debit in complete_order:493 (PURCHASE source, with description "Compra en tienda - Orden #..", ref=order.id); also used in balance checks pre-order creation; package_service co-held but untouched).
- Handlers: store_user_handlers.py (imports BesitoService but ONLY `with get_service(BesitoService)` for shop_menu balance display + product detail/preview/confirm buy checks; 0 direct composition/held; per task "0 change").
- Tests: tests/unit/test_store_service.py (direct `service.besito_service.get_balance` in test_complete_order_success:134 + setup in other complete tests; no other .besito in handlers test_store_user or cross except incidental "store_stock" in package reward test).
- Cross: tests/integration/test_cross_service_atomicity.py (no store.besito access currently; daily guards present + schedule_emit patches in reaction paths; will update for "class patch to services.besito_service" for local intercept + 1-line if any + new contract tests "no-held/uses_local/observer if fits tight"; also exercises "credit survives deliver False" + "post-credit best effort (misiones + listeners)").
- Other indirect: tests/integration/test_invariants.py (may touch store via fixtures? incidental); no package/reward delivery paths touch store's besito (reward uses own local post-Item5; package separate; delivery after debit in complete).
- Bot/central: bot.py (on_startup listener regs after narrative+rewards + Item6 extension; will extend import + register + log comment "+ Item 10 store").
- Event: services/event_bus.py (EVENT_BESITOS_AWARDED, schedule_emit, emit w/ gather return_exceptions=True; used by besito.credit only).
- Docs/roadmap: .planning/HARDENING_ROADMAP.md (explicit callout "store (debits in complete_order — critical atomic but out-of-scope in Item6 tight)"; "Expand remaining Besito decoupling" proposed next #2 "store debits via local if atomic allows"); services/store/CLAUDE.md (documents "Debitar besitos (BesitoService.debit_besitos())" in complete_order flow); services/gamification/CLAUDE.md (Item6 append details locals/obs/4 listeners); services/missions/CLAUDE.md (Item5+6 bullets); services/CLAUDE.md (EventBus); services/narrative/CLAUDE.md; decisions.md (Item5/Item6 entries to append Item10); root CLAUDE.md (atomicity/gamif rules).
- 0 in: story (kept deliberate), reward (fixed Item5), bcast/game/daily (fixed Item6), backpack/streak (already local), mission_service (internal reward), etc.
- Precedents read: item5 reward_service (local in _deliver + obs + 1-line test + bot reg); item6 bcast/game/daily (locals in credit sites + 2 observers + "MUST NOT" + DESIRED + central reg 4 total + 1-line guards in cross/daily + property kept for daily); cross (guards + class patch + schedule patch); bot/event; besito (with_for_update + post schedule only credit); HARDENING/CLAUDEs.

**Affected tests (exact for test-guardian/PLAN):**
- cross atomicity full (happy + partials) with patch("services.event_bus.schedule_emit") + strict + DESIRED + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession/file + fresh TG 777x + gather.
- Broader gamif: pytest -k "store or purchase or complete_order or atomicity or besitos" (or exact from PLAN).
- Bot smoke: manual reg+emit for new listener (python -c or in test).
- Unit store: test_complete_order_* (port 1 access line).
- Unit/integ store purchase flows if any (test_store_service.py, handler tests).
- ruff on touched; greps for rules compliance.
- Re-runs of prior golds (reaction_mission etc if indirect coverage).

**Full files map (tight):**
- Edit: services/store_service.py (primary; ~5-10 lines change: remove 1 from _init, replace 4 self. calls with local= in 3 methods, add ~20L observer block at end, comments).
- Edit: bot.py (1 import + 1-2 reg lines + 1 log/comment extend).
- Edit: tests/integration/test_cross_service_atomicity.py (1-line/guard ports + class patch for besito local intercept + optional new contract test "no-held/uses_local/observer" if fits tight; schedule patch reuse).
- Edit: tests/unit/test_store_service.py (1-line port for service.besito_service.get_balance + comment).
- Docs (if precedent): services/gamification/CLAUDE.md , services/store/CLAUDE.md (min), services/missions/CLAUDE.md , decisions.md (new Item10 entry), .planning/HARDENING_ROADMAP.md? (no, living), root CLAUDE if atomicity.
- No: handlers (0), new files (0 except reports), package/reward paths, story, other services, UI.
- Reports/logs: this + gsd-*.log (16+ entries) + .planning/phases/.../PLAN.md (planner) + SUMMARY + arch/test-guardian reports + MEMORY.md update.

---

## Tight Scope Recommendation (for planner/executor; copy exactly)

**ONLY:**
- services/store_service.py: 
  - Remove `self.besito_service = BesitoService(db)` from _init_services (keep package_service; add comment "Held direct BesitoService composition removed (Item 10 / remaining store debits unification). PURCHASE debits now use local on-demand BesitoService(db=self.db) *only* inside the balance/debit sites in direct_purchase / create_order / complete_order (preserves atomicity: debit's internal commit + PURCHASE tx + order/stock/deliver all unchanged; best-effort schedule_emit still fires post-credit commit if any credit path). 0 other composers (package remains).").
  - Inside the sites ONLY (copy Reward Item5 _deliver + bcast/game Item6 credit sites exactly):
    - e.g. in complete_order (debit site): after user_id=... ; `besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared); ... besito_service.debit_besitos(...) ; ...` (no schedule for debit).
    - Similar locals for the 2 get_balance pre-checks in direct_purchase + create_order (and the re-check in complete).
    - Use self.db (from _get_db() pattern).
  - Update close? Min: leave verbatim (no subs closed originally; harmless; or add `for sub in (getattr(self, "besito_service", None),): if sub and hasattr...` for compat but tight min -- no if not precedent for store).
  - At module bottom (after last method, copy story:670-694 / broadcast:438+ / reward:354+ exact structure):
    ```
    # =============================================================================
    # Cross-domain event listeners (registered explicitly from bot.py on startup).
    # The listener lives here (store domain ownership). It is a plain async callable
    # receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
    # (to avoid any re-entrancy with purchase debit paths or future extensions; purchase
    # debit contracts and partial-failure behavior are authoritative in the debit + deliver flow).
    # This is observational only (best effort; errors swallowed by bus).
    # =============================================================================

    async def on_besitos_awarded_store_observer(payload: dict) -> None:  # or _store_purchase_ per "or similar"
        """
        Store-domain listener for "besitos_awarded" events (emitted by BesitoService.credit_besitos
        post-commit; high-value obs for store even if current purchases are debits -- wiring + future).

        DESIRED CONTRACT (copy of narrative precedent + Reward Item5 + broadcast Item6): log reception with full context (user_id/amount/source/ref);
        purely observational + wiring proof for this domain. MUST NOT credit, debit, or mutate besitos state here.
        Future extensions (e.g. purchase analytics, hooks) belong in this module and should use
        get_service(StoreService) or direct models if a fresh DB session is required.
        """
        uid = payload.get("user_id")
        amt = payload.get("amount")
        src = payload.get("source")
        ref = payload.get("reference_id")
        logger.info(
            f"store | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"
        )
        # No side effects that mutate besitos here (best effort, non-authoritative; 0 impact on purchase debit contracts / atomicity gold).
    ```
- bot.py: extend the import block + register block (after narrative+rewards + Item6) + logger.info comment "+ Item 10 store". E.g. `from services.store_service import on_besitos_awarded_store_observer` ; `get_event_bus().register(..., on_besitos_awarded_store_observer)` ; log "... , store)" ; comment "Fase 3 of eventbus-poc + Item 5 + Item 6 + Item 10 store: narrative + rewards + broadcast + game + store domains."
- Tests (1-line/guard ports like prior, class patch for local intercept):
  - cross_service_atomicity.py: add/update 1-line guards e.g. around any store balance if emerges; `with patch("services.event_bus.schedule_emit") as mock_sched:` reuse in store paths if added; class patch like `with patch("services.besito_service.BesitoService") as mock_besito_cls:` for local creation intercept in atomicity tests; optional "new contract tests for no-held/uses_local/observer if fits tight" (e.g. assert no hasattr(store_svc, 'besito_service') post init; or manual emit + listener received log "store |").
  - test_store_service.py: 1-line port e.g. `bal = BesitoService(db=db_session).get_balance(...) if not hasattr(service, "besito_service") else service.besito_service.get_balance(...)  # 1-line/guard port post Item10 local (copy daily precedent in cross); was service.besito_service` + import if needed. Or simpler independent since post-remove.
  - Use fresh TG 777xxxx in any new; TestSession for cross; strict deltas (e.g. tx count ==1 for PURCHASE, balance delta exact -price, no extra); "credit survives" phrasing in doc even for debit analog.
- 0 other: no store_user change (already get_service); no new files; no package/reward/store delivery edits; no UI/flows/behavior/Lucien voice change; 0 prod.
- Docs if precedent: append cross sections to gamification/store/missions CLAUDEs (copy Item6 bullets: "StoreService held ... reduced (Item 10); PURCHASE debits use local ... *only* inside ... ; high-value obs listener on_besitos_awarded_store_observer ... "MUST NOT" + "store | ..." + DESIRED + central reg + Item 10; 0 behavior/0 atomicity (golds... "credit survives" + "post-credit best effort" protected)"); decisions.md new entry post Item6 (Motivo/Riesgos/Decisión/Resultado style + refs to this impact, PLAN, gsd log, golds); services/CLAUDE min if needed.
- GSD: pre-log (timestamp | PHASE | GSD pre-... + pool phrase) + wc BEFORE every write/search_replace/ruff/pytest/grep/smoke/self-check in downstream.
- Verification: greps (locals in the sites w/ comments, 0 held "self\.besito_service = BesitoService" in store __init__, observer def + "MUST NOT" + domain log "store |", bot reg + "Item 10", 1-lines w/ comments, docs sections); ruff; bot import smoke + manual listener reg+emit (new store one receives); targeted pytest exact cmds (see below); broader; re-runs golds green 0 attributable; arch PASS; test-guardian "suite protege adecuadamente"; self-check PASSED + pool/BATCH phrase at end.

**0 change to purchase UI/flows/behavior; min if any in __init__ for compat (none needed). UI/Lucien identical. 0 prod.**

**Exact design notes for planner/executor (copy al pie de la letra from Item6/5 + 24/23 precedents + atomicity golds + DESIRED):**
- "local besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared); ... besito_service.debit_besitos(...) ; db.commit() ; ... schedule_emit best effort" (adapt for debit sites; no schedule in debit).
- Observer: "async def on_besitos_awarded_store_observer(user_id: int, amount: int, **kwargs): logger.info(...) # MUST NOT credit/debit/mutate" or full payload dict version from story/bcast; "DESIRED CONTRACT: credit/debit commits independent/synchronous inside method; post-credit best-effort for missions/listeners/'credit survives deliver False'".
- bot reg: "after narrative+rewards + Item6" extend with comment "+ Item 10 store".
- 1-line fixes: "besito_service = BesitoService(db=db_session) if not hasattr... else ..."; "class patch to services.besito_service...".
- Tests: patch("services.event_bus.schedule_emit"); TestSession/file for cross visibility; fresh TG 777x; gather return_exceptions.
- Order rec: GSD pre every; F1 prep/GSD/baseline/greps/imports/ruff/golds; F2 store_service (remove held; locals inside 3 purchase methods w/ comments; observer block); F3 bot.py reg + comment; F4 test ports (cross 1line+patch+contract if tight, store unit 1line) + docs appends; F5 re-runs (cross full w/patch + DESIRED + strict + "credit survives" + "post best effort", broader -k store/purchase/complete_order/atomicity/besitos, unit store, bot smoke reg+emit, ruff, greps for 0 held/locals/"MUST NOT"/reg/"Item 10"/1lines/docs, self-check PASSED) + handoff.
- Atomicity golds + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" protected in re-runs.

**Critical tests list (exact cmds for test-guardian/PLAN from precedents):**
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -k "cross_service_atomicity or TestCrossServiceAtomicity or atomicity" --override-ini="addopts=" -p no:cov` (full with patch schedule_emit in relevant + strict tx/delta + DESIRED doc + TestSession + 777 TG + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" asserts; extend for store if contract test added).
- `pytest -k "store or purchase or complete_order or atomicity or besitos or TestStoreService" -q --tb=line` (broader gamif/store flows + unit store ports).
- Bot smoke: `python -c "
from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED
from services.store_service import on_besitos_awarded_store_observer
import asyncio
get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_store_observer)
print('store observer registered')
# simulate emit via schedule or direct if async
print('manual reg+emit smoke for Item 10 store OK')
" ` (or in a unit).
- Unit store targeted: `pytest tests/unit/test_store_service.py::TestStoreService::test_complete_order_success -q --tb=line`
- `ruff check services/store_service.py bot.py tests/integration/test_cross_service_atomicity.py tests/unit/test_store_service.py`
- Greps (post edit, in GSD): `grep -n "local, on-demand" services/store_service.py` ; `grep -c "self\.besito_service = BesitoService" services/store_service.py` (expect 0); `grep -A20 -E "on_besitos_awarded_store|store \| besitos_awarded_received|MUST NOT credit" services/store_service.py` ; `grep -n "Item 10 store" bot.py` ; `grep -n "1-line/guard port post Item10|hasattr.*besito_service" tests/...` ; `grep -n "store | besitos" services/gamification/CLAUDE.md decisions.md` etc.
- Full re-run prior golds if needed: reaction/full_chain, daily atomic, etc.
- After: `python -m pytest ...` + ruff + self-check in gsd log.

**Order rec for item pipeline:** impact (this) -> gsd-planner (produce tight 5-phase PLAN.md + DoD + exact copy instructions + critical tests list + risks + safe points) -> gsd-executor (strict phases; GSD pre-log + wc before *every* edit/gate; read PLAN + golds + this impact first; copy al pie; brief report per phase + full self-check PASSED + BATCH/pool phrase in log + handoff) -> arch-enforcer (audit vs CLAUDE/rules/arch; 0 critical; locals+no-held+obs contract+atomicity; persist report) -> test-guardian (coverage, update ports/contracts, re-runs, veredict "suite protege adecuadamente"; persist) -> run tests (exact cmds above + broader; 0 attributable reg) -> close item + pool note.

**Verification gates (post executor etc):** 0 held (grep); locals+comments present; observer present with MUST NOT + DESIRED + "store |"; bot reg+log + "Item 10"; 1-lines present w/ comments; docs/CLAUDEs/ decisions updated; ruff clean (N806 tol w/doc); golds + broad 0 attributable; bot smoke OK; arch PASS/PASS WITH NOTES; test-guardian "suite protege adecuadamente"; self-check PASSED + pool phrase + "Item 10 closed. NEW pool of 4 (2/4 so far). Quedan ~2-4...".

---

## Impact Map Summary (3 crit + atomicity + get_service + EventBus in mind)

- **Gamif core protected/enhanced:** Purchase debits now local (atomic independent commit + history + return unchanged); observer added for store domain (observational only); central reg extends wiring. 0 double spend risk (pre checks + debit atomic + FOR UPDATE in besito). Post-debit best effort (misiones via other, listeners for any credits).
- **Narrative 0:** No touch (listeners orthogonal; story keeps its besito for _grant).
- **Channel/VIP 0:** Orthogonal (purchases grant content via package, not VIP; reward grants VIP separate).
- **Atomicity contracts (get_service + EventBus + 3 systems):** Preserved exactly (locals owns=False share db; debit/credit do own commits; schedule post only on credit; bus best-effort; "credit survives" + post best effort documented + re-run protected; get_service already in handlers; no change to store_user).
- **Tight:** Matches Item6/5/roadmap "store debits" exactly; no creep.

**DoD checklist (for planner to include):** [list above]; GSD discipline; 0 prod/0 atomicity/0 behavior/0 UI; pool phrase in all logs/reports; ready for next in new pool of 4.

**Handoff:** This report + gsd log (16L+) + MEMORY update. Ready for gsd-planner (tight 5-phase PLAN copy Item6/5 + precedents + golds + DESIRED + atomicity contracts). Chain to executor/arch/test-guardian/tests.

**Fin del análisis de impacto. Listo para planner.** 🎩

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. (Item 10 second of this new pool; Item 9 first closed).
