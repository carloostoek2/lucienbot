# PLAN: Reduce direct BesitoService composition in StoreService (debits in complete_order / balance checks in purchase flows) (Item 10 / second of new pool of 4, automatic chain after Item 9 closed full 6-step + "suite protege" + tests green)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-08  
**Focus:** Tight, conservative, phased reduction of *held direct composition* of BesitoService inside StoreService (the PURCHASE debit/balance composer for content buys). Per impact-analyzer recs + precedents (Reward Item5/23: held→local inside _deliver_besitos only + obs listener + central reg + 1-line test; Item6 broadcast/game/daily: locals in credit sites + 2 obs + "MUST NOT" + DESIRED + central reg 4 total + 1-line guards in cross/daily + property kept for daily; atomicity golds in test_cross_service_atomicity): use **local on-demand `BesitoService(db=self.db)` *only inside the debit/balance call sites*** (the methods/blocks that perform debit_besitos or get_balance for pre-purchase checks: complete_order ~493 debit + rechecks ~488, direct_purchase ~366, create_order ~440). This preserves 100% atomicity/tx control of the caller's tx (besito debit internal commit + PURCHASE tx source + history + order/stock/deliver outer commit all as before). Remove the `__init__` / _init_services held `self.besito_service = BesitoService(db)`. PackageService held remains untouched. close() untouched (store never closed subs; getattr not present). Add one high-value *observational* EventBus listener `on_besitos_awarded_store_observer` (copy story_service.py:670-694 + reward/broadcast expanded templates: "Cross-domain event listeners" block + "MUST NOT credit/debit/mutate" + best-effort + DESIRED CONTRACT + log "store | besitos_awarded_received"; purely observational, 0 mutation, 0 re-entrancy risk with purchase debit paths; high-value for domain wiring + future even if current purchases are debits). Central explicit registration in bot.py on_startup (extend the cross-domain listeners block after Item6 narrative+rewards+broadcast+game; add import + register call + extend logger.info + comment "+ Item 10 store"). Exactly the 1-line/guard test ports (hasattr guards or class patch to services.besito_service.BesitoService for local intercept; "if hasattr(store, 'besito_service') else BesitoService(db=...)"; no new tests beyond tight ports/guards) in `tests/integration/test_cross_service_atomicity.py` (schedule patch reuse + contract "no-held/uses_local/observer if fits tight") + `tests/unit/test_store_service.py` (the `service.besito_service.get_balance` access in test_complete_order_success ~134 + setup in other complete tests). Targeted docs updates ONLY if precedent (cross CLAUDE sections like Item6 in gamification/store/missions/CLAUDE.md + decisions.md new Item10 entry mirroring Item5/6 style). **Zero prod behavior change** (purchase returns/deltas/tx counts/source=PURCHASE/history identical; "credit survives deliver False" + "post-credit best effort (misiones + listeners)" protected by gold re-runs even for debit analog), **zero atomicity impact** (local shares the db; debit/credit do their internal commits; best-effort listeners/schedule never affect purchase return or partial-failure contracts per gold), **zero other composers touched** (package_service remains; reward/package delivery already local or orthogonal; 0 store_user change — already uses get_service), **zero new files** (except opt SUMMARY), **zero UI/Lucien/prod change**. 5 small phases (prep/GSD/baseline, refactor StoreService, bot reg + docs if precedent, 1-line/guard test ports, final verif+self-check). Full GSD pre-log discipline on `.planning/quick/gsd-remaining-besito-store.log` before *every* edit/gate/verif/ruff/pytest/grep/smoke/self-check. Follow structure/patrones/snippets **al pie de la letra** from successful precedents (23-reward-besito-eventbus-decoupling/PLAN.md + gsd + SUMMARY; 24-remaining-besito-compositions/PLAN + 24-SUMMARY + gsd (BATCH/POOL language, 1-line guards, daily property kept, observer "MUST NOT" + DESIRED + central reg, locals in credit sites, cross atomicity ports); 25/26/27 for pool phrase + self-check structure + handoff; HARDENING_ROADMAP store debits remaining + proposed #2; atomicity golds tests/integration/test_cross_service_atomicity.py (guards, patch schedule_emit, TestSession/file, 777, gather, DESIRED, "credit survives deliver False", "post-credit best effort (misiones + listeners)", strict tx/deltas); besito_service.py (credit path + schedule); store_service.py sites; bot.py reg block; event_bus; CLAUDEs gamif/store cross for Item5/6/10; root CLAUDE/AGENTS).

**Input principal (source of truth):** 
- User prompt's complete impact-analyzer report for Item 10: `.claude/agent-memory/impact-analyzer/item10-remaining-besito-store.md` (full read + GSD pre-log + wc before reads/writes; exec summary + risks atomicity/best-effort/loops + mapa de impacto with targets store_service.py complete_order/direct_purchase/create_order for besito debits/balance + tests with 1-line accesses + scope tight proposal: locals in the exact debit/balance sites for atomicity + history + source=PURCHASE, optional high-value obs listener "MUST NOT" + DESIRED + "store | besitos_awarded_received", central reg in bot.py with "+ Item 10 store", 1-line/guard ports like prior (hasattr or class patch("services.besito_service.BesitoService") for local intercept in cross; "if hasattr... else BesitoService(db=...)"; new contract tests for no-held/uses_local/observer if fits tight; docs/CLAUDEs if precedent; 0 behavior/0 atomicity change ("credit survives deliver False", "post-credit best effort (misiones + listeners)", tx counts/deltas strict in golds); precedents Reward Item5 + broadcast/game Item6 + daily guards + atomicity golds + DESIRED; "Item 10 SECOND of NEW pool of 4; automatic continuation after Item 9 (mission_admin) closed via full 6-step"; "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. (Item 10 second of this new pool; Item 9 first closed)"; "GSD pre: Initiated via run_terminal_command creating/appending to .planning/quick/gsd-impact-analyzer-item10-remaining-besito-store.log"; "Analysis only (no impl; ready for gsd-planner with tight 5-phase PLAN copy Item6/5 +24/23 precedents + atomicity golds + DESIRED)"; DoD (for downstream): 0 held in store __init__ (grep); locals in the 3 purchase method sites w/ exact comments; observer + "MUST NOT" + "DESIRED CONTRACT" + "store | besitos_awarded_received"; bot.py reg + "Item 10 store"; 1-line/guard + class patch in cross + store unit test ports; golds (cross full w/patch + broader gamif store/purchase) + unit store + bot smoke reg+emit + ruff + greps all green; docs/CLAUDEs updated if precedent (gamif/store/missions + decisions Item10 + BATCH note); self-check PASSED + pool phrase; ready for planner (5-phase tight) -> executor -> arch (1svc? no but locals+no-held+obs contract+atomicity) -> test-guardian -> tests; "Handoff: This report + gsd log (16+ entries) + MEMORY update. Ready for gsd-planner (tight 5-phase PLAN copy Item6/5 + precedents + golds + DESIRED + atomicity contracts). Chain to executor/arch/test-guardian/tests.").
- Exhaustive discovery by planner (current code state post-Item5/6/9/23/24/25/26/27 + Item9 mission_admin close: store_service.py:65 holds `self.besito_service = BesitoService(db)` in _init_services; get_balance at direct_purchase:366, create_order:440, complete_order:488 (recheck); debit at complete_order:493 (PURCHASE source, with description "Compra en tienda - Orden #..", ref=order.id, default commit=True); _init_services:62-66, close:68-72 untouched for subs; package_service co-held untouched; handlers/store_user_handlers.py already modern (uses `with get_service(BesitoService) as ...` for balance display in shop/preview/etc; import present but 0 composition/held; per task "0 change to store_user if it already uses get_service"); tests: tests/unit/test_store_service.py (direct `service.besito_service.get_balance` in test_complete_order_success:134 + setup in other complete tests; no other .besito in handlers test_store_user or cross except incidental "store_stock" in package reward test); cross: tests/integration/test_cross_service_atomicity.py (no store.besito access currently; daily guards present at 726-728/762 "if hasattr(daily_svc, "besito_service") else BesitoService(db=...)" + schedule_emit patches in reaction paths; will update for "class patch to services.besito_service.BesitoService" for local intercept + 1-line if any + new contract tests "no-held/uses_local/observer if fits tight"; also exercises "credit survives deliver False" + "post-credit best effort (misiones + listeners)"); bot.py:200-210 has the cross-domain reg block (now 4 listeners from Item5/6: narrative + rewards + broadcast + game) + imports 69-77; story_service.py:670-694 exact "Cross-domain event listeners" block + on_besitos_awarded_from_gamification + "MUST NOT call back into credit/debit besitos" + best-effort + log "narrative | besitos_awarded_received" (copy source); reward_service.py:354+ and broadcast_service.py:170+ post-Item5/6 observer blocks with full DESIRED + MUST NOT + domain log (copy sources); event_bus.py:23 EVENT_BESITOS_AWARDED + schedule_emit + DESIRED CONTRACT + gather return_exceptions; besito_service.py:107-150 credit (with_for_update + commit + post _schedule_besitos_awarded_event which does schedule_emit; debit 152+ does with_for_update + commit param default True, NO emit — only credits award event); decisions.md has the full Item5/Item6 entries to mirror for Item10; services/store/CLAUDE.md (documents "Debitar besitos (BesitoService.debit_besitos())" in complete_order flow); services/gamification/CLAUDE.md (Item6 append details locals/obs/4 listeners); services/missions/CLAUDE.md (Item5+6 bullets); services/CLAUDE.md (EventBus); root CLAUDE.md (atomicity/gamif rules); HARDENING_ROADMAP.md (explicit callout "store (debits in complete_order — critical atomic but out-of-scope in Item6 tight)"; "Expand remaining Besito decoupling" proposed next #2 "store debits via local if atomic allows"); 23-PLAN.md + gsd-reward-besito-eventbus.log + 24-PLAN + 24-SUMMARY + gsd-remaining-besito-compositions.log (exact structure, GSD style, snippets, BATCH/POOL language "4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", self-check structure with phases/DoD/gates/archivos/tests/rules/desviaciones/critical tests list/"Item X/24 closed. BATCH... Ready for ... + arch-enforcer re-scan (enfocado en ... + 3 critical systems) + test-guardian (correr los tests críticos listados)", "Copia patrones **al pie de la letra**" section, "Instrucciones para gsd-executor" with "read PLAN + golds + impact first; GSD pre every; tight; copy al pie; re-verify golds + 'credit survives' + DESIRED strings; self-check with pool phrase at end"); 25/26/27 PLANs + SUMMARYs (pool phrase "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. (This is the Nth of the new pool of 4 per impact + PLAN + prior SUMMARY BATCH close; previous batch of 4 closed with tests passing, self-check PASSED, and explicit BATCH note.)", self-check handoff "Item 7/25 closed. First of new pool of 4. Previous batch of 4 ... closed with tests passing per 24-SUMMARY BATCH note + self-check PASSED. Ready for arch-enforcer re-scan (enfocado en ...) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4.", "Item 8/26 closed. Second of new pool of 4. ...", "Item 9/27 closed. ..."; "Previous batch of 4 (Item 7/25 + Item 6/24) closed..."); atomicity gold for TestSession+patch+DESIRED+strict+"credit survives deliver False"+"post-credit best effort (misiones + listeners)"+N806+777+try/finally+gather+guards; gsd-impact-analyzer-item10-remaining-besito-store.log (16+ entries); current source (post Item9 mission_admin close via full 6-step).
- Precedents + gold (exact structure, GSD, phases, DoD, snippets, self-check, executor instrs): `.planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md` + SUMMARY.md + gsd-reward-besito-eventbus.log (Item5: held→local inside _deliver + rewards observer listener + central reg + 1-line in 1 test + docs only missions/CLAUDE + decisions; 5 phases F1-F5; GSD pre every; copy story listener block al pie de la letra; atomicity gold re-runs with patch+DESIRED+TestSession+strict+"credit survives"; self-check PASSED with handoff + critical tests list); `.planning/phases/24-remaining-besito-compositions/PLAN.md` + 24-*-SUMMARY.md + gsd-remaining-besito-compositions.log (Item6: locals inside credit/debit methods only for broadcast/game/daily; 1-2 obs listeners high-value; 1-line fixes + hasattr daily precedent; BATCH "4 items completed in this tirón (Item 6 final of max 4)"; self-check with pool phrase; GSD 50+ per phase); 25-reward-handlers-1service-loc/PLAN + SUMMARY + gsd (first of new pool of 4; "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4..."; "Item 7/25 closed. First of new pool of 4. Previous batch of 4 (ending with Item 6/24 ...) closed with tests passing per 24-SUMMARY BATCH note + self-check PASSED. Ready for arch-enforcer re-scan (...) + test-guardian (...) + gsd-executor del siguiente item del pool de 4."; self-check structure); 26-store-admin-long-funcs/PLAN + 26-*-SUMMARY + gsd (second of new pool; "Item 8/26 closed. Second of new pool of 4. ..."); 27-mission-admin-long-funcs/PLAN + 27-*-SUMMARY + gsd (third of new pool; "Item 9/27 closed. ..."); 22-critical-tests-three-systems/PLAN.md (handoff named the reduce as next); 21-getservice-unification/PLAN.md (local db= for shared/owns=False, get_service for high-level contexts); 20-reward-gamif-rules-compliance/PLAN.md + 19-eventbus-poc/PLAN.md + 19-*-SUMMARY.md + gsd-*.logs; gold tests `tests/integration/test_cross_service_atomicity.py` (full _create_engine_and_session tmp_path + TestSession reopen pre-svc, DESIRED CONTRACT TG ID, patch event_bus, strict dict/balance/progress/tx asserts, N806, happy + partial fail paths, try/finally dispose, "post-credit best effort", daily guards "if hasattr... else BesitoService(db=...)", schedule patch, 777 TG, gather); `tests/unit/test_store_service.py` (complete_order success path with service.besito_service access); besito unit (credit with EventBus patch, DESIRED, TG 777 + N806 doc); event_bus unit + story/reward/broadcast listener test coverage.
- Project rules (non-negotiable): CLAUDE.md (3 critical systems: gamif core (besitos debits on purchases via complete_order/direct_purchase/create_order flows + possible listener for missions/rewards post-purchase (though debit no emit; missions via other paths)); narrative 0 direct (story keeps its own debit/credit for _grant_achievement; listeners orthogonal); channel/VIP 0 (purchases may grant via reward? but orthogonal (0 touch; VIP via reward paths untouched; channel free/VIP separate from store buy)); EventBus for *notifications* (obs-only, "MUST NOT credit/debit" contract), local db= inside methods for atomic credits (per Reward fix), get_service where lifecycle, <50 LOC, logging "módulo | acción | user_id | resultado", GSD pre-log before edits, handlers exactly-1-service), rules.md (≤50 LOC per func, naming verb+context+result, anti-patterns), architecture.md (handlers→services→models; no logic in handlers), models/CLAUDE.md (tx for atomics, no raw, Alembic rules), decisions.md (EventBus + mw + Item5/6 reduce entries to extend after), services/gamification/CLAUDE.md + store/CLAUDE.md + missions/CLAUDE.md + narrative/CLAUDE.md (current cross notes + "MUST NOT credit" contract for listeners), services/CLAUDE.md, handlers/CLAUDE.md.
- Current state (post prior Items 1/5/6/9/23-27 + Item9 mission_admin close via full 6-step): strong (emit wired only in credit success post-commit, 4 listeners + central reg, atomicity gold protects credit vs best-effort sides + reaction/mission chains + invariants + daily atomic with guards, store_user already get_service, held composition still present only in store_service for purchase besito touch among the high-volume; package co-held untouched; other paths (package/reward delivery, backpack, streak) already use locals or orthogonal (no direct store purchase besito touch)). This Item reduces *one* remaining high-volume site safely (tight: only store_service; 0 other composers per "0 other files (0 store_user -- already get_service; 0 package/reward delivery)").
- "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. (Item 10 second of this new pool; Item 9 first closed)."

**GSD enforcement:** Executor MUST prefix **every** modification, gate, verification, ruff, pytest, grep, smoke, or summary step with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-remaining-besito-store.log`. Use identical discipline and entry style as gsd-impact-analyzer-item10-remaining-besito-store.log / gsd-remaining-besito-compositions.log / gsd-reward-besito-eventbus.log / gsd-reward-handlers-1service-loc.log / gsd-store-admin-long-funcs.log (pre + post + counts, "GSD pre-edit <file> (F<N> <short motive>) - <desc + refs DoD + patrones copiados al pie de la letra>", wc tracking). No edits (even to PLAN or log beyond appends) without pre-log. Planner already did initial pre-create/pre-write entries (see log, 2 lines at PLAN time).

---

## 1. Alcance preciso (In / Out explícito)

### En esta entrega (scope "tight" per analyzer recs + "smallest change" + precedents + 0 behavior/0 atomicity/0 other composers/0 other files):
- **StoreService refactor (reduce held composition):**
  - `services/store_service.py`: Remove `self.besito_service = BesitoService(db)` from _init_services (line ~65; keep package_service; add comment "Held direct BesitoService composition removed (Item 10 / remaining store debits unification). PURCHASE debits now use local on-demand BesitoService(db=self.db) *only* inside the balance/debit sites in direct_purchase / create_order / complete_order (preserves atomicity: debit's internal commit + PURCHASE tx + order/stock/deliver all unchanged; best-effort schedule_emit still fires post-credit commit if any credit path). 0 other composers (package remains)."). Inside the sites ONLY (copy Reward Item5 _deliver + bcast/game Item6 credit sites exactly):
    - e.g. in complete_order (debit site ~493): after user_id=... ; `besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared); ... besito_service.debit_besitos(...) ; ...` (no schedule for debit; debit internal commit authoritative).
    - Similar locals for the get_balance pre-checks in direct_purchase (~366) + create_order (~440) and the re-check in complete_order (~488).
    - Use self.db (from _get_db() pattern). Add db.commit() after local debit/balance if needed for caller visibility (per precedent in daily claim + credit internal; cross tests validate); but keep outer complete_order stock/deliver/order COMPLETE + db.commit() unchanged.
  - Update close? Min: leave verbatim (no subs closed originally; harmless; store close only does owns_session + db close; no getattr besito list).
  - At module bottom (after last method, copy story:670-694 / broadcast:170+ / reward:354+ exact structure; optional per impact "optional high-value obs listener"):
    ```
    # =============================================================================
    # Cross-domain event listeners (registered explicitly from bot.py on startup).
    # The listener lives here (store domain ownership). It is a plain async callable
    # receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
    # (to avoid any re-entrancy with purchase debit paths or future extensions; purchase
    # debit contracts and partial-failure behavior are authoritative in the debit + deliver flow).
    # This is observational only (best effort; errors swallowed by bus).
    # =============================================================================

    async def on_besitos_awarded_store_observer(payload: dict) -> None:
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
    (Name per impact "on_besitos_awarded_store_observer" or "on_besitos_awarded_store_purchase_observer"; "store | besitos_awarded_received" log exact; "MUST NOT credit/debit/mutate" exact copy; DESIRED CONTRACT copy; best effort; observational; 0 mutation; future get_service; 0 impact on purchase contracts.)
- **Listener + central registration (observational, best-effort, no command side):**
  - `bot.py`: If listener added, extend the cross-domain listeners block (after scheduler, after the existing narrative + rewards + broadcast + game registers from Item5/6; add import `from services.store_service import on_besitos_awarded_store_observer` + one register call + extend the logger.info line to include ", store"). Explicit, central, no import side-effects. Comment updated (e.g. "Fase 3 of eventbus-poc + Item 5 + Item 6 + Item 10 store: narrative + rewards + broadcast + game + store domains.").
- **1-line/guard test ports only (no new tests/cases, no new test files):**
  - `tests/integration/test_cross_service_atomicity.py`: 1-line or guard around any store balance if emerges in store purchase atomic paths; `with patch("services.event_bus.schedule_emit") as mock_sched:` reuse in store paths if added; class patch like `with patch("services.besito_service.BesitoService") as mock_besito_cls:` or `with patch("services.besito_service.BesitoService.debit_besitos")` for local creation/intercept in atomicity tests exercising complete_order (or direct/create balance checks); optional "new contract tests for no-held/uses_local/observer if fits tight" (e.g. assert no hasattr(store_svc, 'besito_service') post init; or manual emit + listener received log "store |"); keep exact asserts on deltas/tx/source=PURCHASE/"credit survives"/DESIRED strings/patch schedule_emit; docstrings update "1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"; N806 tol w/doc for TestSession; fresh TG 777x if new; TestSession/file + try/finally raw close+dispose; gather return_exceptions.
  - `tests/unit/test_store_service.py`: 1-line port for `service.besito_service.get_balance` post-complete (e.g. `bal = BesitoService(db=db_session).get_balance(...) if not hasattr(service, "besito_service") else service.besito_service.get_balance(...)  # 1-line/guard port post Item10 local (copy daily precedent in cross); was service.besito_service` + import if needed; or simpler independent since post-remove; add comment "# 1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"); keep exact asserts on deltas/tx/source=PURCHASE.
  - 0 new test files/cases (coverage for new listener comes from re-runs of paths that exercise credit (any) + existing event_bus/story/reward/broadcast listener tests + manual smoke of register+emit; re-runs of cross happy/sad with patch + broader gamif -k "store or purchase or complete_order or atomicity or besitos" protect the debit/balance paths + atomicity contracts).
- **Docs (minimal, cross-domain + targeted if precedent):**
  - `services/gamification/CLAUDE.md` (or services/store/CLAUDE.md): Append/update the existing "Cross-domain notifications (EventBus PoC Item 1)" / Item6 section with note on Item 10 reduction in StoreService (locals inside the exact debit/balance sites in complete_order/direct_purchase/create_order only; high-value obs listener on_besitos_awarded_store_observer "MUST NOT" + "store | ..." + DESIRED + central reg + Item 10; 0 behavior/0 atomicity (golds... "credit survives" + "post-credit best effort" protected)); refs to this PLAN + impact + gsd log + atomicity gold + 23/24 precedents.
  - `services/missions/CLAUDE.md`: Append 1 bullet to the existing "Cross-domain notifications (EventBus) (Item 5 ...)" section (or new sub) noting the continuation for the remaining store purchase composer (locals for atomic debits + history + PURCHASE source, optional high-value listener, 0 other services/files touched per tight, refs to this PLAN + 23/24-PLAN + impact).
  - `decisions.md`: Append new decision entry "## Reduce direct BesitoService composition in StoreService (debits in complete_order / balance checks in purchase flows) (Item 10 / second of new pool of 4)" following the exact style/structure of the Item 5/6 entries (Motivo, Riesgos (críticos incl atomicity + partial failure contracts from golds + re-entrancy if listener credited + "credit survives" for debit analog), Decisión (locals inside the exact debit/balance sites ONLY for the 3 purchase methods + high-value obs listener "MUST NOT" + DESIRED + "store | ..." + central reg in bot.py with "+ Item 10 store" + 1-line/guard ports in cross + store unit + targeted docs if precedent), Resultado (0 behavior/0 atomicity change, held removed for this composer, listener wired if, gates, handoff, pool "second of new pool of 4")).
  - `bot.py` (if listener): extend the reg comment to reference "+ Item 10 store".
- **Gates + re-runs (protect 0 regression + atomicity gold + listener wiring + purchase/atomicity contracts):**
  - Targeted re-runs of: `tests/integration/test_cross_service_atomicity.py` (gold full happy + sad/partials with patch("services.event_bus.schedule_emit") + strict + DESIRED + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession/file + 777 TG + gather + N806 tol w/doc; extend for store purchase atomic if contract test added; guards exercised); broader `pytest -k "store or purchase or complete_order or atomicity or besitos or TestStoreService" -q --tb=line -p no:cov --override-ini="addopts="` (broader gamif/store flows + unit store ports); bot smoke: manual reg+emit for new listener (python -c or in test); unit store targeted `pytest tests/unit/test_store_service.py::TestStoreService::test_complete_order_success -q --tb=line`; ruff on touched; greps (post edit, in GSD): `grep -n "local, on-demand" services/store_service.py` ; `grep -c "self\.besito_service = BesitoService" services/store_service.py` (expect 0); `grep -A20 -E "on_besitos_awarded_store|store \| besitos_awarded_received|MUST NOT credit" services/store_service.py` ; `grep -n "Item 10 store" bot.py` ; `grep -n "1-line/guard port post Item10|hasattr.*besito_service" tests/...` ; `grep -n "store | besitos" services/gamification/CLAUDE.md decisions.md` etc.
  - Patch schedule_emit + DESIRED CONTRACT style where verifying emit (as in atomicity gold + Item1/5/6).
  - 0 new test files/cases (coverage for listener via re-runs of credit paths (any) + smoke of register+emit + existing event_bus/story/reward/broadcast listener tests).
- **Behavior/contracts:** All purchase paths (direct_purchase, create_order, complete_order) return identical (order or (exito, msg), balance checks pre-purchase identical, debit in complete with PURCHASE source + description "Compra en tienda - Orden #.." + ref=order.id + internal commit authoritative; order/stock/deliver outer commit unchanged). The event is still emitted (best-effort) on every credit (including any future store credits); if new listener, it receives when registered (log only, no mutation). No user-visible or admin-visible change. Partial failure contracts (debit tx commits even if later stock/deliver or listeners "fail"; credit tx commits even if later mission/listeners "fail") protected by golds (re-runs protect "credit survives deliver False" + "post-credit best effort (misiones + listeners)" even for debit analog).
- **Artefacts:** This PLAN.md + GSD entries (pre every) in the dedicated log + (optional post-exec) SUMMARY.md. Pool note "second of new pool of 4" at F5 self-check + log. Handoff explicit to gsd-executor of this PLAN (then arch-enforcer focused on locals/no-held/observer/"MUST NOT"/DESIRED/atomicity golds + test-guardian + gsd-executor siguiente of pool 4).

**Archivos que se modificarán (exactos, por orden de fases; prefer extend, minimal):**
1. `.planning/quick/gsd-remaining-besito-store.log` (all phases, pre only via echo; no "edit" of source).
2. `services/store_service.py` (F2: _init_services remove held + comments; locals inside the 3 purchase methods' debit/balance sites (complete_order ~493 debit + rechecks ~488, direct~366, create~440); optional observer at bottom).
3. `bot.py` (F3: import + register in on_startup + log line + comment "+ Item 10 store", *only if* listener added).
4. `tests/integration/test_cross_service_atomicity.py` (F4: 1-line/guard ports + class patch for besito local intercept + optional new contract test "no-held/uses_local/observer" if fits tight; schedule patch reuse; docstring update "1-line/guard port post Item 10..."; keep exact asserts on deltas/tx/source=PURCHASE/"credit survives"/DESIRED/patch schedule_emit; N806 tol w/doc; 777 if new; TestSession/file + try/finally + gather).
5. `tests/unit/test_store_service.py` (F4: 1-line port for service.besito_service.get_balance + comment "# 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer)"; import if needed; keep exact asserts).
6. (If precedent/docs): `services/gamification/CLAUDE.md` or `services/store/CLAUDE.md` (F3/F5: append cross-domain section); `services/missions/CLAUDE.md` (F5: append 1 bullet); `decisions.md` (F5: append Item10 decision entry after Item6).
7. Re-runs/gates/verifs/smokes do not modify (except log appends + ruff auto-fixes if any on touched).

**Fuera explícitamente (nada de scope creep, per "tight" + "0 other files (0 store_user -- already get_service; 0 package/reward delivery)" + "1-line/guard only" + precedents + "second of new pool of 4"):**
- **NO** other files in services/ (no broadcast_service, game_service, daily_gift, story beyond its existing listener, reward_service (already done Item5), mission_service, package/vip, backpack, streak_promotion, trivia_*, user, channel, vip, analytics, scheduler, backup, __init__.py exports, etc.).
- **NO** handlers (store_user_handlers.py — already uses get_service(BesitoService); per task "0 change"; store_admin_handlers.py — already compliant post Item8; no other).
- **NO** new test files, no new test methods/cases (only the 1-line/guard ports in the *existing* listed tests; no extension of event_bus tests or atomicity for "new listener" coverage or "store purchase atomic" beyond tight ports/guards if they emerge — re-runs + smoke suffice; "no new tests beyond tight").
- **NO** changes to close() body, to non-purchase methods (create_product/get_*/update_*/delete_*/cart_*/stats), to package co-init, to any return strings/dicts or LucienVoice, to order/stock/deliver logic, to TransactionSource.PURCHASE description/ref.
- **NO** migration to get_service() for the local debits/balances (use direct BesitoService(db=...) to keep tx/owns semantics explicit inside the atomic purchase flows; get_service is for handlers/contexts per 21 precedent; handlers already use it).
- **NO** editing CLAUDEs/decisions except the specified if precedent (gamif/store/missions + decisions.md); no AGENTS/ROADMAP/root CLAUDE/handlers/CLAUDE beyond cross if precedent.
- **NO** touching models, alembic, config, utils, middlewares, keyboards, bot startup beyond the reg block (if listener).
- **NO** new events, no change to besitos_awarded payload, no removal of schedule_emit from credit.
- **NO** broad "reduce all compositions" (only this one held site in StoreService for purchase besito touch per analyzer + "0 other files").
- **NO** behavior or contract changes (0 impact on partial failure, 0 on "credit survives deliver False", 0 on purchase returns/deltas/tx counts/source=PURCHASE/history, 0 on order/stock/deliver, 0 on UI/Lucien).
- **NO** adding tests for listeners beyond re-runs/smoke (tight scope).

**Comportamiento observable:** Identical for all purchase flows (direct_purchase returns (order, None) or (None, error); create_order same; complete_order returns (True, ...) or (False, error); balance checks pre-purchase identical; debit in complete with PURCHASE source + description "Compra en tienda - Orden #.." + ref=order.id + internal commit authoritative for spend; order/stock/deliver outer commit unchanged; besitos_awarded event still emitted (best-effort) on every credit from any source; the new observer receives when registered (log only, no mutation). No user-visible or admin-visible change. The 3 critical systems (gamif as source of debits/credits, missions/rewards via atomic, narrative as existing listener) remain protected.

---

## 2. Fases ordenadas (5 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Preparación (GSD log, baseline, fixtures/mocks/patterns confirm, patrones gold)
**Objective:** Establecer disciplina GSD para el Item (log touched by planner with 2+ lines), confirmar baseline de archivos tocados (ruff + targeted pytest verdes pre-cambios), mapear sites de composición actual + debit/balance call sites + listener patterns + bot reg + atomicity/purchase golds + daily hasattr precedent, preparar setups para the 1-line/guard ports (fresh TG or sample_user, db_session, TestSession for cross), confirmar that credits inside besito still exercise schedule_emit (via patch in re-runs) and that store purchase paths (complete_order debit + balance rechecks) are exercised in cross/unit (even if no direct store.besito access yet). Sin cambios de lógica aún. Safe point inicial.

**DoD checklist (marcar al completar):**
- [ ] Log `.planning/quick/gsd-remaining-besito-store.log` exists with planner INIT/DISCOVERY/PLANNING/pre-write entries (≥2 lines) + at least 1 pre-F1 of executor.
- [ ] Baseline: ruff clean on `services/store_service.py`, `tests/integration/test_cross_service_atomicity.py`, `tests/unit/test_store_service.py`, `bot.py` (and spot on story_service.py for listener pattern + reward_service.py for post-Item5 gold + broadcast for Item6 gold).
- [ ] Baseline targeted pytest verdes (clean flags): `pytest tests/unit/test_store_service.py -q --tb=line -p no:cov --override-ini="addopts="`, `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (gold), spot `pytest tests/handlers/test_store_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (if exists; 0 change expected), spot story/besito units for patterns.
- [ ] Confirm gold patterns via grep/lectura: DESIRED CONTRACT, patch("services.event_bus.schedule_emit"), "post-credit ... best effort", listener comment block + "MUST NOT" in story_service.py:670+, bot.py on_startup register block (200-210, now with 4), atomicity "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + daily guards "if hasattr(daily_svc, "besito_service") else BesitoService(db=...)" at 726-728/762 + class patch precedent, N806 tolerance if any, TG-style or sample_user, local db= for shared session in atomic flows, Reward local inside _deliver + 1-line test comment precedent from 23, broadcast/game locals in credit sites + 2 obs + "MUST NOT" + DESIRED + central reg 4 total from 24.
- [ ] Mocks/fixtures list: db_session (for local Besito(db=)), TestSession + tmp_path for cross, mock_bot, sample_user/sample_product/sample_order, patch schedule_emit ready, get_event_bus for smoke, fresh TG 7772xxxx for ID contract.
- [ ] Grep current composition: `grep -n "besito_service\|BesitoService(self.db)\|self\.besito_service" services/store_service.py` shows the sites (init held _init_services:65, get_balance 366/440/488, debit 493, close no besito); confirm only the 3 purchase methods' balance/debit sites will change to local.
- [ ] Grep for UI pins from golds/DESIRED strings (e.g. "credit survives deliver False", "post-credit best effort (misiones + listeners)", "DESIRED CONTRACT", "MUST NOT credit", "if hasattr.*besito_service", "BesitoService\(db=", "TestSession", "777", "gather", "schedule_emit", "PURCHASE", "complete_order", "direct_purchase", "create_order").
- [ ] Read precedents (23/24 PLAN + gsd logs excerpts for locals + observer + 1-line/guard + bot reg + self-check + BATCH/POOL; 25/26/27 for pool phrase + self-check structure + handoff "Item X/25 closed. First/Second/... of new pool of 4. Previous batch of 4 ... closed with tests passing per 24-SUMMARY BATCH note + self-check PASSED. Ready for arch-enforcer re-scan (enfocado en ...) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4."; atomicity gold for guards + patch + DESIRED + TestSession + strict + "credit survives" + "post-credit best effort" + N806 + 777 + try/finally + gather; HARDENING_ROADMAP for store debits remaining + proposed #2; impact10 for exact scope/files/sites/comments/observer name/log/1-line style; 23/24 gsd for GSD entry style + "Copia patrones **al pie de la letra**" + "Instrucciones para gsd-executor").
- [ ] GSD pre + post entries for baseline (≥5-10 total for F1).
- [ ] Safe point F1.

**Archivos:** Log + (lectura/grep/ruff/pytest; 0 edits to prod/tests in F1).

**Cambios clave (bullets accionables):**
- Ejecutar comandos de baseline (ver Instructions).
- Grep/lectura rápida de patterns (story listener block, bot reg, atomicity patch+docstring + daily guard, store unit complete_order test access site ~134, reward post-Item5 as local gold, broadcast/game as Item6 gold, impact10 exact sites/comments/observer name/log/1-line style, 25/26/27 pool phrase + self-check + handoff language).
- Confirm import of BesitoService will be available for any 1-line (or note minimal import companion).
- Actualizar log con "F1 baseline verde + patterns confirmed (story listener copy source, atomicity/reaction golds for atomicity, daily hasattr precedent, Reward local inside _deliver+1-line test, broadcast/game locals+2 obs+Item6, 1-2 access sites in store unit + cross daily guards, impact10 scope 4 files max (svc + bot if + 1-2 tests), pool 'second of new pool of 4', previous batch closed per 24/25/26 SUMMARY) + ready for refactor".
- (No code changes.)

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff on touched py (store_service, its test, cross atomicity, bot + spot story/reward/broadcast).
- `pytest tests/unit/test_store_service.py -q --tb=line -p no:cov --override-ini="addopts="`
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (gold)
- Spot `pytest tests/handlers/test_store_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (if exists; 0 change).
- Grep confirm (composition + UI pins from golds/DESIRED) + GSD entries + "F1 safe point".

**Riesgos + mitigaciones:**
- Riesgo: baseline shows pre-existing unrelated fails (alembic, xfails in besito for lifecycle, daily concurrent, cross daily !success, N806 in gold, SA warnings, etc.) → Mit: document in log; use targeted -k; do not count as regression of this Item (precedent in 27/26/25/24/23/22/19/20).
- Riesgo: the store unit test has direct service.besito_service access in complete_order tests → Mit: the 1-line/guard port in F4 will adjust; F1 gates run pre-change (test will pass now via held).
- Riesgo: cross has no store.besito access yet (only daily guards) → Mit: F1 confirms the hasattr guard pattern exists in the file (288/727/726-728/762 daily precedent); F4 will add/ensure 1-line guard or class patch for store paths if they exercise complete_order in atomicity (or new contract test if fits tight per impact "if fits tight"); re-runs protect.
- Bajo: time on baseline → Mit: targeted, parallel commands where safe but prefer sequential for log.

**Safe point:** Baseline verde + patterns confirmed + "F1 safe point - ready for StoreService refactor; no source changed yet". Reversible (nada editado en fuentes aún).

---

### Fase 2: Refactor StoreService (remove held; local Besito on-demand inside the exact debit/balance sites in complete_order/direct_purchase/create_order; listener if high-value)
**Objective:** Ejecutar el core change for store (high-volume purchase debit/balance path): remover la composición held en _init_services, re-implementar the balance/debit call sites (direct_purchase ~366 get_balance, create_order ~440 get_balance, complete_order ~488 recheck + ~493 debit) usando local BesitoService(db=self.db) para the calls (copia el patrón de "local for shared db" de atomicity golds + Reward Item5 _deliver_besitos + bcast/game Item6 credit sites + getservice normalization). Mantener 100% comportamiento (purchase returns/deltas/tx counts/source=PURCHASE/history, order/stock/deliver outer, "Compra en tienda - Orden #.." description, ref=order.id, internal debit commit authoritative). close() untouched (store never closed subs). Logging estándar. Decisión en primer GSD de F2: agregar high-value obs listener (store domain for wiring + future) + nombre exacto (on_besitos_awarded_store_observer per impact); si sí, append at bottom + prepare for central reg in F3. GSD pre every edit. Ruff + smoke + targeted (note: the 1 access test will be ported in F4; gate other paths + service itself). Safe point.

**DoD checklist:**
- [ ] _init_services no longer sets self.besito_service (comment explaining reduction + local-only for purchase debits/balance; scope other composers untouched; package_service remains).
- [ ] direct_purchase, create_order, complete_order use local `besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared)` for the get_balance/debit calls (docstring or inline comment updated to note "local on-demand (shared db preserves atomicity of PURCHASE debit + order/stock/deliver + history + return)"); success path + error paths identical; db.commit() after local debit/balance if needed for caller visibility (per precedent in daily claim + credit internal; cross tests validate); outer complete_order stock/deliver/order COMPLETE + db.commit() unchanged.
- [ ] All other methods untouched (create_product/get_*/update_*/delete_*/cart_*/stats, package co-init, close).
- [ ] (If listener decision YES): listener added at bottom of store_service.py (after close): full comment block "Cross-domain event listeners..." + async def with docstring quoting "MUST NOT credit/debit/mutate", "observational best-effort for store domain", "no re-entrancy risk with purchase debit paths", log "store | besitos_awarded_received | ...", no mutation code. Decision + name logged in GSD. Full copy from story 670-694 + reward/broadcast expanded templates per impact (DESIRED CONTRACT (copy of narrative precedent + Reward Item5 + broadcast Item6), "MUST NOT credit, debit, or mutate besitos state here", "0 impact on purchase debit contracts / atomicity gold", "future extensions (e.g. purchase analytics, hooks) ... use get_service(StoreService)").
- [ ] Ruff limpio + format; GSD pre each edit + pre-gate.
- [ ] Smoke: import StoreService + basic (non-purchase paths or product CRUD).
- [ ] Grep: `grep -n "self\.besito_service = " services/store_service.py` → 0 (active); "BesitoService(db=self.db)" present in the purchase sites with exact comment; (if listener) def + "MUST NOT credit" + "store | besitos_awarded_received" present.
- [ ] Targeted store unit (excluding or noting the 1 failing access test until F4) + cross atomicity spot (if it exercises complete_order or purchase paths) pass where applicable; 0 regressions in non-purchase store paths.
- [ ] GSD "F2 safe point" documented.

**Archivos:** `services/store_service.py` (only for edits; tests/docs later).

**Cambios clave (bullets accionables, orden: _init_services then purchase sites; listener last if):**
- Pre-log GSD "pre-edit services/store_service.py (F2 remove held + local in purchase sites) - refs DoD F2 + copy local db= pattern from atomicity gold + Reward Item5 _deliver_besitos + bcast/game Item6 credit sites + getservice norm; 1-line/guard test ports deferred to F4; listener decision in this phase GSD (on_besitos_awarded_store_observer YES per impact high-value for store domain + wiring proof); read pre done".
- Edit _init_services (around line 62-66):
  ```python
  def _init_services(self):
      """Inicializa servicios dependientes con la misma sesión."""
      db = self._get_db()
      # Held direct BesitoService composition removed (Item 10 / remaining store debits unification).
      # PURCHASE debits/balance checks now use local on-demand BesitoService(db=self.db) *only*
      # inside the balance/debit sites in direct_purchase / create_order / complete_order (preserves atomicity:
      # debit's internal commit + PURCHASE tx + order/stock/deliver all unchanged;
      # best-effort schedule_emit still fires post-credit commit if any credit path).
      # PackageService remains held (scope: other composers untouched per Item 10 tight).
      # self.besito_service = BesitoService(db)  # REMOVED (was here)
      self.package_service = PackageService(db)
  ```
- Edit the purchase sites (first direct_purchase ~366 get_balance, then create_order ~440 get_balance, then complete_order ~488 recheck + ~493 debit; keep all logic identical except the instantiation + add db.commit() after local if needed for visibility; comments "local, on-demand; owns=False (db shared)"):
  ```python
  # ... (inside direct_purchase, after stock check)
  # Verificar saldo
  besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared); balance check for atomic pre-purchase
  balance = besito_service.get_balance(user_id)
  if balance < product.price:
      return None, LucienVoice.store_balance_insufficient(product.price, balance)
  ```
  (Analogous for create_order ~440 total_price check.)
  ```python
  # ... (inside complete_order, after order fetch + PENDING check)
  # Verificar saldo nuevamente
  besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared); recheck for atomicity with debit
  balance = besito_service.get_balance(user_id)
  if balance < order.total_price:
      return False, "Saldo insuficiente"

  # Cobrar besitos
  success = besito_service.debit_besitos(
      user_id=user_id,
      amount=order.total_price,
      source=TransactionSource.PURCHASE,
      description=f"Compra en tienda - Orden #{order.id}",
      reference_id=order.id,
  )
  # (no schedule for debit; debit internal commit authoritative; outer stock/deliver/order COMPLETE + db.commit() unchanged)
  ```
- (If decision YES in F2 GSD): append at very end (after last method or close; full copy from story 670-694 + reward/broadcast expanded per impact template):
  ```python
  # =============================================================================
  # Cross-domain event listeners (registered explicitly from bot.py on startup).
  # The listener lives here (store domain ownership). It is a plain async callable
  # receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
  # (to avoid any re-entrancy with purchase debit paths or future extensions; purchase
  # debit contracts and partial-failure behavior are authoritative in the debit + deliver flow).
  # This is observational only (best effort; errors swallowed by bus).
  # =============================================================================

  async def on_besitos_awarded_store_observer(payload: dict) -> None:
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
  (Name confirmed in F2 first GSD: "on_besitos_awarded_store_observer" per impact; "store | besitos_awarded_received" exact; "MUST NOT credit, debit, or mutate besitos state here" exact copy; DESIRED CONTRACT copy; best effort; observational; 0 mutation; future get_service; 0 impact on purchase contracts; arch comment "item10 / remaining besito store / arch-enforcer" if precedent.)
- Post edit: ruff --fix + format --check (apply if needed); smoke `python -c "from services.store_service import StoreService; ..."` (product paths); grep for the removal + local (+ listener if).
- GSD entry post-gate.
- Re-run relevant store tests (the besitos access test will be noted for F4; other paths green).

**Tests que deben pasar antes de avanzar:**
- Ruff on store_service.py.
- `pytest tests/unit/test_store_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "not test_complete_order_success"` (or full with expectation the 1 access will be ported in F4; document).
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (at least the purchase/complete_order paths if exercised, or daily/reaction as proxy).
- Spot broader if relevant.
- Grep + smoke + "F2 safe point".

**Riesgos + mitigaciones:**
- Riesgo: atomicity of purchase broken (debit now in "local" vs held) → Mit: local uses `db=self.db` (exact shared session as the old held one had); debit does its own commit inside (as always, default True); the subsequent stock/deliver/order COMPLETE + db.commit() is unchanged; gold test_cross_service_atomicity (which protects "credit survives" + post best effort + strict tx/delta) will be re-run in F4/F5 and protects the pattern (debit analog "spend survives later failure" covered by re-runs of complete_order paths + cross); local creation is cheap and matches "on-demand" rec + Reward/Item6 precedent.
- Riesgo: close() or owns semantics affected → Mit: no change to close body (store close only does owns_session + db close; never closed subs); the local inside purchase creates a non-owning instance (db passed) whose close() is no-op.
- Riesgo: test that does `service.besito_service` now fails → Mit: exactly the 1-line/guard port planned for F4; F2 gates exclude or note it (test will pass now via held).
- Riesgo: listener decision wrong (name/scope) → Mit: log the decision in GSD; if added, copy story block al pie de la letra (adapt 3-4 words per impact template); removable in F3 if needed (but tight scope prefers final in F2).
- Riesgo: db.commit() after local debit affects outer atomicity → Mit: per precedent in daily claim + credit internal (cross tests validate); outer complete_order commit for stock/deliver/order is separate and unchanged; debit commit inside is authoritative for spend (per impact "debit internal commit authoritative").
- Mit general: targeted, DESIRED-style comments in the edit, GSD, patch schedule_emit in re-runs (even if debit path, pattern identical for contracts).

**Safe point:** Post-ruff + greps + non-purchase store tests green + GSD "F2 safe point - held removed, local Besito(db=) in the 3 purchase method sites (complete_order debit + rechecks, direct/create balance checks) only; 0 behavior change in purchase paths; close safe; listener added if high-value (name logged); 1 access test deferred to F4". Reversible by restoring the _init_services line + 4-5 purchase sites (pre F2 commit).

---

### Fase 3: Agregar listener store-domain + registro central en bot.py + comments + docs if precedent
**Objective:** Añadir el listener observacional store-domain (copy exact pattern from story_service.py:670-694 + reward/broadcast expanded templates, adapt for "store" domain + "MUST NOT credit" contract + DESIRED + "store | besitos_awarded_received"; high-value for wiring + future per impact). Registro explícito central en bot.py on_startup (extend the block after Item6 narrative+rewards+broadcast+game). Logging "store | ...". No side effects. GSD pre, ruff, smoke (import + manual register+emit under loop), re-run story/besito/broadcast to protect inverse credit + emit. Optional cross CLAUDE sections like Item6 (gamif/store/missions) + decisions Item10 entry if precedent (per impact "docs/CLAUDEs updated if precedent"). No behavior. Safe point.

**DoD checklist:**
- [ ] Listener added at bottom of store_service.py (after any __del__ or end of file): full comment block "Cross-domain event listeners..." + async def (name decided in F2/F3 first GSD, e.g. `on_besitos_awarded_store_observer(payload: dict) -> None`) with docstring quoting "MUST NOT credit/debit", "observational best-effort for store domain", "no re-entrancy risk with purchase debit paths", log line "store | besitos_awarded_received | ...", no mutation code. Full copy from story 670-694 + reward/broadcast templates per impact (DESIRED CONTRACT (copy of narrative precedent + Reward Item5 + broadcast Item6), "MUST NOT credit, debit, or mutate besitos state here", "0 impact on purchase debit contracts / atomicity gold", best effort, observational, future get_service, no mutation).
- [ ] bot.py: import added (from services.store_service import ...), register call added after the game one (or after rewards per impact "after narrative+rewards + Item6"), logger.info extended (e.g. "... (besitos_awarded -> narrative, rewards, broadcast, game, store)"), comment updated "+ Item 10 store".
- [ ] Comments in both places reference this Item / "following narrative precedent (Item 1) + Item5/6".
- [ ] (If precedent/docs): cross CLAUDE sections added/appended (gamif/store/missions) + decisions.md Item10 entry mirroring Item5/6 (Motivo/Riesgos/Decisión/Resultado + refs + pool "second of new pool of 4").
- [ ] Ruff limpio on touched; GSD pre every.
- [ ] Smoke: python -c import bot (or manual under asyncio loop: get_event_bus().register + emit payload + caplog or print); listener callable.
- [ ] Re-runs: story unit + besito credit + broadcast reaction (emit still fires, no breakage to _grant inverse credit or reaction credits); 0 regressions.
- [ ] Safe point.

**Archivos:** `services/store_service.py`, `bot.py`. (Docs if precedent.)

**Cambios clave (bullets accionables):**
- Pre-log per file "pre-edit <file> (F3 add store listener / central reg) - copy story_service.py:670-694 block + def + reward/broadcast expanded templates per impact; adapt name/log prefix/domain 'store |' + 'MUST NOT credit/debit/mutate' + DESIRED CONTRACT (narrative+Reward5+broadcast6) + '0 impact on purchase debit contracts / atomicity gold'; bot reg after game (or after rewards per impact) + comment '+ Item 10 store'; refs DoD F3 + Item1/5/6 precedent + impact10 exact observer block; (docs if precedent)".
- In store_service.py (append at very end, after the last def or __del__; full per impact template):
  ```python
  # =============================================================================
  # Cross-domain event listeners (registered explicitly from bot.py on startup).
  # The listener lives here (store domain ownership). It is a plain async callable
  # receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
  # (to avoid any re-entrancy with purchase debit paths or future extensions; purchase
  # debit contracts and partial-failure behavior are authoritative in the debit + deliver flow).
  # This is observational only (best effort; errors swallowed by bus).
  # =============================================================================

  async def on_besitos_awarded_store_observer(payload: dict) -> None:
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
  (Name per F2/F3 GSD decision; "on_besitos_awarded_store_observer" recommended per impact; "store | besitos_awarded_received" exact; "MUST NOT credit, debit, or mutate besitos state here" exact; DESIRED CONTRACT copy; best effort; observational; 0 mutation; future get_service; 0 impact on purchase contracts; arch comment "item10 / remaining besito store / arch-enforcer" if precedent.)
- In bot.py (near the existing cross-domain block, ~200-210):
  - Add to the from services... imports: `from services.store_service import on_besitos_awarded_store_observer`
  - After the game register line:
    ```python
    get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_store_observer)
    logger.info("Event listeners registrados (besitos_awarded -> narrative, rewards, broadcast, game, store)")
    ```
  - Keep/update the comment: "# Cross-domain listeners (explicit, central, no import side-effects). Fase 3 of eventbus-poc + Item 5 + Item 6 + Item 10 store: narrative + rewards + broadcast + game + store domains."
- (If precedent/docs): append to CLAUDEs (gamif/store/missions) + decisions.md (full Item10 entry after Item6; Motivo/Riesgos/Decisión/Resultado + refs to this PLAN + impact + gsd log + golds + "second of new pool of 4").
- Post: ruff --fix + format on touched; smoke; re-run story + besito + broadcast targeted.
- GSD + "F3 safe point".

**Tests gates:**
- Ruff on the touched files.
- `pytest tests/unit/test_story_service.py tests/unit/test_besito_service.py tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts="` (protect inverse + emit + reaction credits).
- Smoke bot import or manual listener register+emit.
- Grep for the new def + register call (+ docs if).
- (If docs) spot CLAUDEs/decisions.

**Riesgos + mitigaciones:**
- Riesgo: duplicate listener name or import collision → Mit: unique name in store; explicit import in bot.
- Riesgo: listener registration order or multiple in tests → Mit: tests use patch or fresh bus per Item1/5/6 precedent; prod reg is idempotent-tolerant (bus allows dups).
- Riesgo: "store" listener name confusion with "store purchase" → Mit: docstring + log prefix make domain clear; it's observational only; name per impact "on_besitos_awarded_store_observer".
- Riesgo: docs not precedent (no CLAUDEs/decisions) → Mit: impact says "if precedent"; F3 GSD decision logged; if added, copy style from Item5/6 exactly.
- Mit: copy the comment block verbatim (adapt 3-4 words per impact), use exact log format from narrative/rewards/broadcast.

**Safe point:** Post gates + GSD "F3 safe point - store listener added (MUST NOT credit, best effort, copy of story+reward+broadcast al pie de la letra per impact), central reg in bot (after game, comment +Item10 store), 0 side effects, emit still fires to all, story/besito/broadcast protected, (docs if precedent). Reversible: delete the listener def + remove the register line + import (+ docs if)."

---

### Fase 4: 1-line/guard ports in tests (cross atomicity + store unit) + re-runs subset + verif
**Objective:** Aplicar las modificaciones de test (1-line/guard in cross atomicity.py + store unit test: guards like daily precedent "if hasattr... else BesitoService(db=...)", class patch("services.besito_service.BesitoService...") for local intercept in complete_order tests, keep exact asserts on deltas/tx/source=PURCHASE/"credit survives"/DESIRED strings/patch schedule_emit; docstrings update "1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"; no new test files). Luego re-ejecutar subset de golds que ejercitan store purchase / complete_order / cross atomicity + patch schedule_emit donde se verifica. Confirmar 0 regressions atribuibles + que el emit sigue ocurriendo (best effort). GSD pre every.

**DoD checklist:**
- [ ] Exactly the 1-line/guard changes in `tests/integration/test_cross_service_atomicity.py` (around daily guards 726/762 if store paths added or contract test; class patch to services.besito_service.BesitoService for local intercept in complete_order tests; schedule patch reuse; docstring update "1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"; keep exact asserts on deltas/tx/source=PURCHASE/"credit survives"/DESIRED/patch schedule_emit; N806 tol w/doc for TestSession; fresh TG 777x if new; TestSession/file + try/finally + gather); all now pass (or guards protect pre-exist paths).
- [ ] Exactly the 1-line/guard change in `tests/unit/test_store_service.py` (the service.besito_service.get_balance access in test_complete_order_success ~134 + setup in other complete tests) to guard + fallback BesitoService(db=...) + exact comment "# 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer)"; import if needed; all asserts on deltas/tx/source=PURCHASE preserved and pass.
- [ ] Re-runs subset: targeted cross atomicity (happy/sad with patch + strict + DESIRED + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession/file + 777 + gather + N806 tol w/doc); unit store complete_order paths; broader -k "store or purchase or complete_order or atomicity or besitos" spot if quick; all green with 0 attributable reg.
- [ ] Patch schedule_emit executed in at least the atomicity re-run (verified emit still scheduled; pattern identical for store paths even if debit).
- [ ] Grep/inspección: no more `service.besito_service` in the store test active code (or guarded); 1-line comments present; cross guards/class patch present with comments; listener coverage exercised via re-runs (credit paths which schedule) + smoke if in F3.
- [ ] Ruff on the test files; GSD pre + "F4 re-runs done".
- [ ] Safe point.

**Archivos:** `tests/integration/test_cross_service_atomicity.py`, `tests/unit/test_store_service.py` (the 1-line/guard ports only; 0 new test files).

**Cambios clave:**
- Pre-log "pre-edit <test> (F4 1-line/guard port) - change ... to ... with comment '# 1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)'; refs DoD F4 + impact '1-line/guard ports in cross + store unit (hasattr guards or class patch to services.besito_service.BesitoService for local; if hasattr... else BesitoService(db=...))' + atomicity gold + daily precedent + 23/24 1-line style; keep exact asserts on deltas/tx/source=PURCHASE/'credit survives'/DESIRED/patch schedule_emit; no new tests beyond tight".
- The edits (examples per impact/PLAN):
  - cross (daily guard site or new store path if emerges; class patch for local intercept):
    ```python
    final_bal = (
        daily_svc.besito_service.get_balance(saved_tg)
        if hasattr(daily_svc, "besito_service")
        else BesitoService(db).get_balance(saved_tg)
    )  # 1-line fix post local-in-claim (F5); daily precedent guard (726)
    ```
    (For store complete_order in atomicity if exercised: similar guard or direct Besito(db=) fallback; class patch:)
    ```python
    with patch("services.besito_service.BesitoService") as mock_besito_cls:  # class patch for local intercept in complete_order (post Item10 local besito)
        # or patch("services.besito_service.BesitoService.debit_besitos", ...)
        ...
    ```
    Docstring update: "1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)".
  - store unit ~134 (test_complete_order_success + other complete tests):
    ```python
    balance = BesitoService(db=db_session).get_balance(sample_user.id) if not hasattr(service, "besito_service") else service.besito_service.get_balance(sample_user.id)  # 1-line/guard port post Item10 local (copy daily precedent in cross); was service.besito_service
    ```
    (Import `from services.besito_service import BesitoService` at top or inside if not resolvable; minimal companion counted in 1-line delta per tight.)
- Post: ruff; targeted pytest cross + store unit; broader -k spot; GSD post + counts.
- Grep for the fix + "F4 gates + 0 new regressions attributable".

**Tests gates (obligatorios):**
- Ruff on the test files.
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (with patch if in happy; guards/class patch exercised; exact asserts on deltas/tx/source=PURCHASE/"credit survives"/DESIRED/patch schedule_emit; N806 tol w/doc; TestSession/file + try/finally + gather + 777 if new).
- `pytest tests/unit/test_store_service.py -q --tb=line -p no:cov --override-ini="addopts="` (complete_order paths; 1-line guard exercised).
- `pytest -k "store or purchase or complete_order or atomicity or besitos or TestStoreService or TestCrossServiceAtomicity" -q --tb=line -p no:cov --override-ini="addopts="` (broader but targeted; document unrelated pre-exist).
- Grep for the fix + "F4 gates + 0 new regressions attributable".

**Riesgos + mitigaciones:**
- Riesgo: the 1-line test now exercises a fresh BesitoService instance → Mit: it only reads balance post-commit (the debit already committed via the local inside complete_order); identical to before. Gold atomicity re-run confirms tx + delta + PURCHASE source.
- Riesgo: class patch on BesitoService intercepts local creation (as intended) → Mit: per impact "class patch to services.besito_service.BesitoService for local intercept in cross when locals used"; this is the desired behavior for verifying the local is created and used; test asserts on deltas/tx/source remain identical.
- Riesgo: unrelated fails in broader re-runs → Mit: document (precedent 27/26/25/24/23/22); focus "0 attributable to this Item's 1-line/guard ports".
- Riesgo: listener not "covered" because units don't run bot startup → Mit: re-runs of credit paths (which schedule) + smoke of register+emit (as in Item1/5/6 F3/F5) + note in log that coverage is via the emit path + existing event_bus tests; no new test code per tight scope.
- Riesgo: N806 or TestSession in cross → Mit: tolerate + document per PLAN "N806 tolerance with doc" + precedent in atomicity gold + besito unit; not regression.

**Safe point:** Post all gates + GSD "F4 safe point - 1-line/guard ports applied in cross + store unit (hasattr guards + class patch for local intercept per daily precedent + impact; docstrings updated '1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)'; all store unit + cross atomicity re-runs green (0 attributable reg); patch schedule_emit verified; exact asserts on deltas/tx/source=PURCHASE/'credit survives'/DESIRED preserved; now local besito in store purchase paths would be intercepted by class patch and guarded by hasattr. Reversible by the 1-line/guard revert."

---

### Fase 5: Re-runs golds + rules verif + self-check PASSED + handoff (second of new pool of 4; prior batch closed)
**Objective:** Re-ejecutar TODOS los golds que protegen el flujo de store purchase / complete_order / atomicity / besito debit + patch schedule_emit donde se verifica + broader gamif -k "store or purchase or complete_order or atomicity or besitos". Confirmar 0 regressions atribuibles + que el emit sigue ocurriendo (best effort). Si listener added, smoke register+emit (receives). Actualizar docs (CLAUDEs + decisions Item10 entry + bot reg comment if). Completar GSD log con self-check PASSED explícito + lista de "tests críticos a re-correr en futuro" + pool phrase "Item 10/28 closed. Second of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + ...) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos) + gsd-executor del siguiente item del pool de 4.". Opcional SUMMARY.md. Handoff para siguiente item del pool 4 + guardians. GSD pre every.

**DoD checklist (marcar al completar):**
- [ ] Todos los archivos tocados (store_service.py, bot.py if reg, 2 tests, docs if) pasan ruff check + format --check.
- [ ] Grep global/por archivo: 0 "self\.besito_service = " (active) en store_service.py; presence of locals in the 3 purchase method sites w/ exact comments "local, on-demand; owns=False (db shared)"; (if listener) observer def + "MUST NOT credit/debit/mutate" + "DESIRED CONTRACT" + "store | besitos_awarded_received"; register call + extended log in bot.py + comment "+ Item 10 store"; the 1-line/guard comments in cross + store unit ("# 1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"); cross-domain sections in CLAUDEs if precedent; Item10 entry in decisions.md.
- [ ] Re-runs finales de targeted críticos (cross atomicity full happy/sad with patch schedule_emit + strict + DESIRED + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession/file + 777 + gather + N806 tol w/doc; broader `pytest -k "store or purchase or complete_order or atomicity or besitos or TestStoreService or TestCrossServiceAtomicity" -q --tb=line -p no:cov --override-ini="addopts="`; unit store complete_order paths; bot smoke manual listener reg+emit if listener; story/besito/broadcast spot to protect inverse/emit/reaction credits).
- [ ] Patch schedule_emit executed in at least the atomicity re-run (verified emit still scheduled from local credits; pattern identical for store paths).
- [ ] GSD log tiene entradas para cada fase + pre-gates + self-check al final con estructura completa: lista de fases/DoD/gates/archivos modificados/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3-4 files + log + PLAN + opt SUMMARY + 0/0/0/0 behavior chg in purchase returns/deltas/tx/source=PURCHASE/history/order/stock/deliver/UI, locals in the exact debit/balance sites only, observer + "MUST NOT credit/debit/mutate" + DESIRED + "store | ..." if added, central reg + "+ Item 10 store" if, 1-line/guard ports in cross + store unit with class patch/hasattr + comments, no new tests beyond ports/guards, no other files, logging, no prod change, 3 crit + atomicity contracts + get_service/EventBus protected)/desviaciones (si las; e.g. ruff hygiene as chore 0 logic per 27/26/25/24 precedent, pre-exist fails/warns/xfails doc non-reg per PLAN risk/mit)/tests críticos para futuro (cross atomicity full w/patch + strict + DESIRED + "credit survives" + "post-credit best effort (misiones + listeners)" + TestSession/file + 777 + gather + N806 tol w/doc; broader -k "store or purchase or complete_order or atomicity or besitos"; unit store complete_order paths; bot smoke reg+emit if listener; ruff + greps + LOC verifiers; story/besito/broadcast spot)/"Item 10/28 closed. Second of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + ...) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4.".
- [ ] Self-check explícito "Self-Check: PASSED".
- [ ] (Opcional pero recomendado) SUMMARY.md en el dir de la phase con executive + refs al log + comandos de re-verif (sigue estructura de 27/26/25/24/23/22/21/20/19).
- [ ] Safe point final + criterio de éxito del plan.

**Archivos:** Ninguno nuevo (log + opcional SUMMARY; edits ya hechos en F2-F4; docs if precedent in F3/F5).

**Cambios clave:** Solo ejecución de comandos (ver Instructions) + echo al log. Usar run_terminal para gates finales + conteos + greps + self-check append. (If docs precedent in F3/F5: the appends to CLAUDEs/decisions.)

**Tests gates (obligatorios):**
- Ruff on all touched py.
- Full targeted + combined:
  ```
  ./venv/bin/python -m pytest tests/integration/test_cross_service_atomicity.py tests/unit/test_store_service.py -q --tb=line -p no:cov --override-ini="addopts="
  ```
- Broader smoke: `pytest -k "store or purchase or complete_order or atomicity or besitos or TestStoreService or TestCrossServiceAtomicity" -q --tb=line -p no:cov --override-ini="addopts="`
- Patch schedule_emit verification in at least one re-run (atomicity or besito).
- Bot smoke: `python -c "
from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED
from services.store_service import on_besitos_awarded_store_observer
import asyncio
get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_store_observer)
print('store observer registered')
# simulate emit via schedule or direct if async
print('manual reg+emit smoke for Item 10 store OK')
" ` (or in a unit; if listener added).
- Grep for all criteria + "F5 gates + 0 new regressions attributable + pool 'second of new pool of 4'".
- (If listener) manual smoke register+emit.

**Riesgos + mitigaciones:**
- Riesgo: 1-line/guard tests now exercise fresh BesitoService or no sub → Mit: they only read/post or patch; debit already committed via the local inside complete_order; golds re-runs confirm tx + delta + PURCHASE source + "credit survives" + post best effort. Guards preserve compat.
- Riesgo: unrelated fails in broader re-runs → Mit: document (precedent 27/26/25/24/23/22); focus "0 attributable to this Item's 1-line/guard ports".
- Riesgo: listener not "covered" because units don't run bot startup → Mit: re-runs of credit paths (schedule) + smoke register+emit (as in Item1/5/6 F3/F5) + note in log; no new test code per tight.
- Riesgo: pool phrase missing → Mit: explicit in F5 self-check entry + final log line (verbatim "Item 10/28 closed. Second of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + ...) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos) + gsd-executor del siguiente item del pool de 4.").
- Riesgo: batch/pool language inconsistent with 25/26/27 → Mit: copy verbatim from 25/26/27 SUMMARY/self-check ("Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. (This is the Nth of the new pool of 4 per impact + PLAN + prior SUMMARY BATCH close; previous batch of 4 closed with tests passing, self-check PASSED, and explicit BATCH note.)" + "Item 10/28 closed. Second of new pool of 4. ... Ready for ... + gsd-executor del siguiente item del pool de 4.").

**Safe point final + criterio de éxito:** Todos DoD F5 + self-check PASSED en log with pool phrase + handoff. El plan completo + log GSD son evidencia para siguiente agente (gsd-executor next item del pool 4 o arch-enforcer/test-guardian). 0 breakage en critical systems or purchase contracts; the 3 systems (gamif, missions/rewards, narrative) remain protected; held composition reduced for this site following the bus loose-coupling precedent safely. "second of new pool of 4" recorded. Handoff explicit: ready for gsd-executor of this PLAN (then arch-enforcer focused on locals/no-held/observer/"MUST NOT"/DESIRED/atomicity golds + test-guardian + gsd-executor siguiente of pool 4).

---

## 3. Estrategia de tests general

- **Unit para lógica de purchase sites (now with locals):** db_session fixture (in-mem or file per gold); direct create product/order or complete_order setup + call the purchase/complete; post-port the access uses explicit local BesitoService(db=) or hasattr guard + direct (same as the one created inside the purchase method); asserts on return (order or (exito, msg)), tx source via other queries if needed (PURCHASE), no double debit. Patch("services.event_bus.schedule_emit") around the purchase call to verify emit still scheduled (best effort, as in atomicity gold + besito unit from Item1/5/6; pattern identical for store even if debit path).
- **Integration para flujos cross (atomicity gold, purchase atomic if emerges, invariants):** file SQLite + TestSession (gold exact from test_cross_service_atomicity.py); patch schedule_emit; strict asserts on balance delta, BesitoTransaction source==PURCHASE + reference_id=order.id, order row, stock decrement, "debit survives later best-effort" path (the local debit still commits even if later stock/deliver or listener would "fail"). Re-run full happy + partials (e.g. debit ok, stock error → debit tx present; !success debit → no stock/deliver/order COMPLETE; balance insufficient → no debit). Guards/class patch exercised for local intercept.
- **Listener coverage (no new files/cases per tight):** exercised by (a) re-runs of credit paths (besito unit, atomicity, any store future credit, broadcast/game/daily/reward) which call schedule_emit; (b) smoke/manual in F3/F5: get_event_bus().register(the store listener) + await bus.emit(...) + caplog or assert logged (copy from Item1/5/6 F3 test_event_bus addition); (c) existing event_bus unit + story/reward/broadcast listener tests (they cover the bus + existing listeners; the new one is symmetric). When bot startup is exercised (smoke), all listeners are registered.
- **Gates:** always `-p no:cov --override-ini="addopts="` for clean exit (precedent all recent phases 27/26/25/24/23/22/21/19); targeted -k first (store, purchase, complete_order, atomicity, cross, besitos_awarded); broader smoke at end filtered by keywords; ruff pre/post; GSD pre each.
- **ID / DESIRED CONTRACT:** in the 1-line/guard fixes + any docstring updates, quote "credit survives deliver False", "PURCHASE tx + history log + return", "best-effort listeners no afectan purchase contracts", "debit internal commit authoritative". Use sample_user / db_session / fresh TG 7772xxxx as in the files (or per atomicity gold). N806 tolerated + doc for TestSession (exact precedent in gold).
- **Precedente --override-ini + N806 (if surfaces):** tolerate + document (atomicity gold has it for TestSession; besito unit has for TG 77728001).
- **No scope creep en tests:** only the 1-line/guard ports in the *existing* listed tests; re-runs protect existing + the emit contract. No new methods even if cheap. Story accesses untouched (story keeps held per precedent).
- **Cobertura logging:** not asserted in tests; gate is manual inspection during F2/F3 (listener log if added) + inclusion in GSD + re-runs of purchase paths (which log "Orden ...").

---

## 4. Decisiones de diseño (el executor debe confirmar o registrar desviación en el primer GSD entry de la fase relevante)

1. **Nombre del listener store-domain (if high-value decision YES):** `on_besitos_awarded_store_observer` (per impact "on_besitos_awarded_store_observer" or "on_besitos_awarded_store_purchase_observer"; prefer "on_besitos_awarded_store_observer" for domain clarity). Confirm in F2 (or F3) first GSD; document. Bus tolerates dups but distinct preferred for ownership clarity.
2. **Cómo mantener purchase atómico con local Besito:** `besito_service = BesitoService(db=self.db)` — pasa la sesión compartida; el local tendrá owns=False y su close no-op. El debit_besitos hace su propio commit (como siempre, default True) + (no schedule for debit); el outer commit (stock/deliver/order COMPLETE) es idéntico. Esto replica exactamente lo que el held hacía antes (mismo db object). No usar get_service aquí (get_service es para contextos de alto nivel/handlers per 21; local directo preserva el "dentro de la tx de caller" explícito). El emit post-commit de credit sigue ocurriendo — listeners best-effort. db.commit() after local debit/balance if needed for caller visibility (per precedent in daily claim + credit internal; cross tests validate); outer complete_order commit unchanged.
3. **Payload handling + logging en listener (if added):** Idéntico al de narrative/rewards/broadcast (uid/amt/src/ref); log prefix "store | besitos_awarded_received | ...". Incluir el comentario grande "Cross-domain event listeners..." (copy from story 670-675) adaptado para el dominio + "0 impact on purchase debit contracts / atomicity gold / partial failure".
4. **Docstring MUST NOT credit:** Copiar espíritu exacto de story + reward Item5 + broadcast Item6: "It MUST NOT call back into credit/debit besitos to avoid re-entrancy with <domain> <debit/credit> paths... best effort, non-authoritative." + "DESIRED CONTRACT (copy of narrative precedent + Reward Item5 + broadcast Item6)". Colocar en el def + en el bloque de comentarios. "MUST NOT credit, debit, or mutate besitos state here" exact copy.
5. **1-line/guard fix en tests + daily precedent:** Cambiar solo la(s) línea(s) de acceso (store unit direct .besito_service.get_balance → hasattr guard + direct BesitoService(db=...) or fallback with comment "# 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer)"; cross patch/guard sites → ensure guard + class patch to services.besito_service.BesitoService (or .debit_besitos) for local intercept + 1-line comment "1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"; daily precedent guards (if hasattr(store, "besito_service") else BesitoService(db=...).get_balance(...) or similar fallback). Mantener todos los asserts/textos idénticos (deltas/tx/source=PURCHASE/"credit survives"/DESIRED/patch schedule_emit). Para el patch en cross (if store complete_order exercised): class patch target "services.besito_service.BesitoService" (or .debit_besitos) (to intercept local created inside purchase); 1-line comment.
6. **close() en StoreService:** Dejar verbatim (store close only does owns_session + db close; never closed subs; no getattr besito list; harmless).
7. **Registro en bot.py (if listener):** Después de los existentes (narrative + rewards + broadcast + game); extender el logger.info; mantener/actualizar el comentario "Cross-domain listeners (explicit, central...) + Item 10 store".
8. **Actualizaciones de docs (if precedent):** gamif/CLAUDE or store/CLAUDE append to existing Item1/6 section (note Item10 reduction + listener if); missions/CLAUDE append 1 bullet to Item5/6 section; decisions.md append full Item10 entry after Item6 (exact style Motivo/Riesgos/Decisión/Resultado + "second of new pool of 4" + handoff); bot reg comment if. No other docs.
9. **Log file GSD:** `.planning/quick/gsd-remaining-besito-store.log`. Formato:
   ```
   === 2026-06-08Txx:xx:xx+00:00 | PHASE 2 | GSD pre-edit services/store_service.py (F2 remove held + local in purchase sites) - Agregar local BesitoService(db=self.db) en direct_purchase/create_order/complete_order (balance/debit sites); remover self.besito_service= en _init_services; copiar patrón db= compartido de atomicity gold + Reward Item5 _deliver_besitos + bcast/game Item6 credit sites + getservice norm; refs DoD F2 + impacto analyzer (mantener atomicidad, 0 behavior chg). Listener decision: on_besitos_awarded_store_observer (high-value para store domain + wiring proof per impact).
   ```
   (o pre-ruff, pre-pytest -k "store or purchase or complete_order or atomicity", pre-grep "besito_service =", pre-final-self-check). Apuntar 5-10+ entries por fase (como precedentes 27/26/25/24/23). Al final: self-check + pool phrase "Item 10/28 closed. Second of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + ...) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4."
10. **Comandos concretos:** Ver sección Instrucciones abajo. Siempre con -p no:cov + override para pytest targeted. Para smoke listener + emit (bajo loop): usa un snippet con asyncio o pytest caplog. Para pool note: echo al log en F5 self-check.
11. **Cualquier desviación:** Registrar en GSD entry de la fase + nota breve al final del PLAN o en SUMMARY. Executor confirma decisiones de nombre de listener, si se agregó, cómo estructuró el local Besito(db=) (1 línea o con var, por método), si el import en tests fue necesario, si cross tuvo store complete_order paths a portear, etc. Si difiere del "preferido", explica brevemente (mantén espíritu tight + gold + 0 behavior).

Cualquier decisión que difiera de lo anterior debe registrarse en el GSD log + nota breve al final del PLAN o en SUMMARY posterior.

---

## 5. Criterios de verificación + gates finales

**Criterios de éxito del Item (medibles, para self-check del executor):**
- Held composition removed: `grep -c "self\.besito_service = BesitoService" services/store_service.py` (active) == 0; local on-demand `BesitoService(db=self.db)` present in the 3 purchase method sites (direct_purchase, create_order, complete_order) with exact comments "local, on-demand; owns=False (db shared)".
- (If listener added): def present with "MUST NOT credit/debit/mutate" + "DESIRED CONTRACT" + domain log ("store | besitos_awarded_received"); register call + extended log in bot.py on_startup + comment "+ Item 10 store".
- 1-line/guard fixes only: exactly the access/patch/guard lines (and minimal imports/guards) changed in the listed tests (cross atomicity, store unit); all relevant unit tests now pass (or guards protect); docstrings updated "1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"; class patch to services.besito_service.BesitoService for local intercept; hasattr guards or fallback "if hasattr... else BesitoService(db=...)"; exact asserts on deltas/tx/source=PURCHASE/"credit survives"/DESIRED/patch schedule_emit preserved.
- Docs (if precedent): cross-domain section in gamif/CLAUDE or store/CLAUDE; append in missions/CLAUDE; Item10 decision entry in decisions.md (style of Item5/6); bot reg comment if.
- 0 behavior change: re-runs of store unit (complete_order returns identical (exito, msg), PURCHASE tx present with correct source/desc/ref, balance delta exact -price, order/stock/deliver committed), cross atomicity (PURCHASE tx present if store path exercised, "credit survives" partials protected, balance delta exact, guards/class patch exercised, "besitos_awarded" local in reaction dicts if overlap), broader -k filtered (store/purchase/complete_order/atomicity/besitos) — all green with 0 regressions attributable.
- Emit still fires: patch schedule_emit asserts in at least one re-run (atomicity or besito); when registered, new listener receives (smoke).
- Ruff limpio + format --check on all touched py (svc + tests + bot if) + docs if (docs spot).
- Verificaciones de reglas/patrones: GSD pre every (counts 5-10+/fase, total 30+); logging format in listener if + purchase methods; comments reference Item 10 + precedents; LOC of touched funcs preserved or <50 (no change); 0 new files (except optional SUMMARY); scope exactly as listed (no store_user change, no package/reward delivery edits, no get_service for locals, no new tests beyond 1-line/guard ports, no handler changes, 0 other files per "0 other files (0 store_user -- already get_service; 0 package/reward delivery)").
- GSD log completo con pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro para estos cambios" (cross atomicity full w/patch + strict + DESIRED + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession/file + 777 + gather + N806 tol w/doc; broader -k "store or purchase or complete_order or atomicity or besitos"; unit store complete_order paths; bot smoke reg+emit if listener; ruff + greps + LOC verifiers; story/besito/broadcast spot) + "Item 10/28 closed. Second of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + ...) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4.".
- Safe point final documentado; item listo para siguiente en pool 4 y guardians.
- Comportamiento de usuario final idéntico (compras directas/carrito, completado de órdenes, cobro de besitos con fuente PURCHASE, saldos, mensajes Lucien, historial, stock decremento, entrega de paquetes).

**Gates por fase (ver secciones de fases para detalles):**
- Pre-edit: GSD log entry.
- Post-edit: ruff + targeted pytest (cuando aplique) + smoke + grep/LOC + GSD entry de resultado.
- Avanzar solo si gate verde (o documentar desviación menor).
- F4/F5: re-runs obligatorios de golds + broader smoke filtrado + self-check + pool phrase.

**Comando combinado sugerido para gates finales (adaptar por fase; targeted primero):**
```
./venv/bin/python -m pytest -k "TestStoreService or complete_order or direct_purchase or create_order or TestCrossServiceAtomicity or store or purchase or atomicity or besitos or cross_service_atomicity" -q --tb=line -p no:cov --override-ini="addopts="
```
Para suites específicas: `pytest tests/unit/test_store_service.py ...` (con flags).  
Ruff: `./venv/bin/python -m ruff check services/store_service.py bot.py tests/integration/test_cross_service_atomicity.py tests/unit/test_store_service.py --fix && ./venv/bin/python -m ruff format --check ...`  
Grep rules: `grep -n "self\.besito_service = \|besito_service = BesitoService(db=\|on_besitos_awarded_store\|store \| besitos_awarded_received\|MUST NOT credit\|Cross-domain event listeners\|Item 10 store\|1-line/guard port post Item 10\|hasattr.*besito_service" services/store_service.py bot.py tests/integration/test_cross_service_atomicity.py tests/unit/test_store_service.py | head -30`  
Smoke listener (if added): `python -c "
import asyncio
from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED
from services.store_service import on_besitos_awarded_store_observer
bus = get_event_bus()
bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_store_observer)
print('store listener registered')
# (under running loop or use caplog in pytest for the log line)
" `
Pool note (F5): `echo "=== $(date -Iseconds) | F5 | Item 10/28 closed. Second of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + ...) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4. Self-Check: PASSED." >> .planning/quick/gsd-remaining-besito-store.log`

---

## Instrucciones para el gsd-executor

Este PLAN.md ES tu prompt de ejecución. Síguelo al pie de la letra, sin scope creep. El trabajo es para UNA persona (tú) + disciplina GSD total. Este es el **segundo item de un nuevo pool de 4** (Item 10 / 28-remaining-besito-store, post Item9 mission_admin close via full 6-step + "suite protege" + tests green); el batch anterior de 4 quedó cerrado con tests pasando (ver .planning/phases/24-remaining-besito-compositions/24-remaining-besito-compositions-SUMMARY.md + 25/26/27 SUMMARYs + self-checks PASSED + BATCH/POOL notes); el flujo continúa automáticamente con gsd-executor para este item (y luego los siguientes 2 del pool de 4). 

**CONFIRMACIÓN OBLIGATORIA (incluir en tu output final y en el self-check del log):** Este es el segundo de un nuevo pool de 4 (Item 10 / 28-remaining-besito-store). El batch anterior de 4 quedó cerrado con tests pasando: ver .planning/phases/24-remaining-besito-compositions/24-remaining-besito-compositions-SUMMARY.md ("**BATCH:** 4 items completed in this tirón (Item 6 final of max 4). ... Item 6/24 closed. BATCH: 4 items completed in this tirón (final of max 4). **Status:** COMPLETE - Self-Check: PASSED") + su gsd-remaining-besito-compositions.log (self-check PASSED + BATCH COMPLETE NOTE al final) + 25/26/27 SUMMARYs + self-checks PASSED + re-runs verdes en F5 de esos items. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

1. **GSD discipline (non-negotiable, como en todas las phases exitosas 27/26/25/24/23/22/21/20/19 + item2/5/6/7/8/9 logs):**
   - ANTES de **cualquier** modificación (search_replace/write/edit en fuentes o log o SUMMARY), antes de ruff, pytest, grep de verif, smoke, o resumen: append al log.
   - Log: `.planning/quick/gsd-remaining-besito-store.log` (cross-ref gsd-impact-analyzer-item10-remaining-besito-store.log del analyzer si útil).
   - Crea/append al archivo si necesario (planner ya hizo INIT + pre-write con 2 entries; wc tracked; primer entry de executor puede confirmar + wc).
   - Formato de entry (copia estilo **al pie de la letra** de gsd-impact-analyzer-item10-remaining-besito-store.log / gsd-remaining-besito-compositions.log / gsd-reward-besito-eventbus.log / gsd-reward-handlers-1service-loc.log / gsd-store-admin-long-funcs.log):
     ```
     === 2026-06-08Txx:xx:xx+00:00 | PHASE 2 | GSD pre-edit services/store_service.py (F2 remove held + local in purchase sites) - Agregar local BesitoService(db=self.db) en direct_purchase/create_order/complete_order (balance/debit sites); remover self.besito_service= en _init_services; copiar patrón db= compartido de atomicity gold + Reward Item5 _deliver_besitos + bcast/game Item6 credit sites + getservice norm + story/reward/broadcast listener comments; refs DoD F2 + impacto analyzer (mantener atomicidad, 0 behavior chg). Listener decision: on_besitos_awarded_store_observer (high-value para store domain + wiring proof per impact).
     ```
     Luego ejecuta el comando de edit/tool.
   - También pre-gate (pre-pytest, pre-ruff, pre-grep "besito_service =|on_besitos_awarded_store|MUST NOT", pre-final-self-check, pre-SUMMARY si produces).
   - Cuenta las entradas; apunta a varias por fase (5-10+ totales por fase como precedentes item2 46+, 24 55+, 25 40+, 26 800+, 27 similar). Al final del Item el log debe tener el self-check completo + POOL note.
   - Usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE N | ..." >> .planning/quick/gsd-remaining-besito-store.log` (o printf). Nunca edites sin pre-log. wc -l después de appends clave.

2. **Orden estricto:** Ejecuta Fase 1 → gates → Fase 2 (refactor StoreService; locals inside the exact debit/balance sites in complete_order/direct_purchase/create_order; listener decision + optional append) → gates → Fase 3 (listener + reg + docs if precedent) → gates → Fase 4 (1-line/guard ports in cross + store unit) → gates → Fase 5 (re-runs golds + verif final + self-check + POOL confirm) → gates finales. **No saltes fases ni hagas "todo de una".** Marca DoD mentalmente o en el log al completar cada checklist. Al final de cada fase documenta "F<N> safe point" + "F<N> COMPLETE" en log (como item2/5/6/7/8/9 logs). Al final de F5: pool phrase verbatim + handoff "Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4."

3. **Herramientas y comandos concretos (usa run_terminal_command para estos; copia los de sección 5 + precedents):**
   - GSD logs + wc: `echo "..." >> log; wc -l log`
   - Mkdir (si planner no lo hizo completamente): `mkdir -p .planning/phases/28-remaining-besito-store`
   - Ruff: `./venv/bin/python -m ruff check <file> --fix` ; `./venv/bin/python -m ruff format --check <file>` (apply si "would reformat" como chore 0 logic per precedent 27/26/25/24/23).
   - Pytest targeted (siempre con estos flags para exit limpio): `./venv/bin/python -m pytest <path or -k "expr"> -q --tb=line -p no:cov --override-ini="addopts="`
     - Ejemplos exactos en sección 5 arriba + 27/26/25/24/23 F4/F5.
   - Grep de reglas: `grep -n "self\.besito_service = \|BesitoService(db=self.db)\|on_besitos_awarded_store\|store \| besitos_awarded_received\|MUST NOT credit\|Cross-domain event listeners\|Item 10 store\|1-line/guard port post Item 10\|hasattr.*besito_service" services/store_service.py bot.py tests/integration/test_cross_service_atomicity.py tests/unit/test_store_service.py | head -30`
   - LOC (siempre inspect si aplica): `./venv/bin/python -c 'import inspect; from services.store_service import StoreService; ...'` (raro aquí; foco en tests).
   - Smokes: `./venv/bin/python -c "from services.store_service import StoreService; print('import ok')"; ./venv/bin/python -c "import bot; print('bot import ok')"`
   - Para smoke listener + emit (bajo loop): usa un snippet con asyncio.get_event_loop().run_until_complete o pytest caplog en un test temporal si es el camino más barato (pero scope tight → prefer el smoke simple + nota que re-runs de credit paths cubren el schedule).
   - Para contar/inspeccionar: `grep -c "def " services/xxx_service.py` o `python -c 'import inspect; ...'`.
   - Evita sleeps; usa comandos directos. Si tool soporta background para integ lentas, úsalo pero log secuencial prefer.
   - Al final F5: re-ejecuta los combinados + broader smoke filtrado por store/purchase/complete_order/atomicity/besitos + self-check en log + pool phrase + optional SUMMARY write.
   - Para pool update: en F5 self-check append + final echo con verbatim pool phrase + "Item 10/28 closed. Second of new pool of 4. ... Ready for ... + gsd-executor del siguiente item del pool de 4."

4. **Patrones a copiar (no reinventar; **al pie de la letra** de golds):**
   - Listener + comment block + "MUST NOT credit/debit/mutate" + best-effort + DESIRED: copia EXACTA de `services/story_service.py:670-694` (el bloque # Cross-domain... + async def on_besitos_awarded_from_gamification + docstring + log "narrative | ..." + final comment); adapta solo el prefijo de log ("store |" vs "narrative |"), el nombre del def (decisión F2/F3), y 2-3 frases de "store domain" + "0 impact on purchase debit contracts / atomicity gold / partial failure" + PLAN F2/F3 expanded templates with "DESIRED CONTRACT (copy of narrative precedent + Reward Item5 + broadcast Item6)", "MUST NOT credit, debit, or mutate besitos state here", "future extensions (e.g. purchase analytics, hooks) ... use get_service(StoreService)". Colócalo al final del archivo después de la clase/close si se agrega. Copia también de reward_service.py:354+ y broadcast_service.py:170+ para el expanded template con "DESIRED CONTRACT (copy of narrative precedent + Reward Item5 + broadcast Item6)".
   - Registro central + comentario en bot.py: copia de `bot.py:200-210` (get_event_bus().register + logger.info); extiende después de los existentes (narrative + rewards + broadcast + game); actualiza el comment "Cross-domain listeners (explicit, central...) + Item 10 store".
   - Local Besito with shared db para atomicity: copia espíritu de setups en `tests/integration/test_cross_service_atomicity.py` (_create... + TestSession + db=TestSession() para services que hacen commit interno) + normalización owns en 21-getservice (db= passed → owns=False); + el Reward Item5 precedent `besito_service = BesitoService(db=self.db)` dentro del método (_deliver_besitos) + comment "local, on-demand; owns=False (db shared); credit commits internally as before"; + bcast/game Item6 locals in credit sites; aquí es directo BesitoService(db=self.db) dentro de los sites de balance/debit (no get_service, per PLAN "NO migration to get_service for the local debits/balances (use direct ... to keep tx/owns semantics explicit inside the atomic flows)").
   - Patch schedule_emit + DESIRED CONTRACT + strict asserts: copia de `tests/integration/test_cross_service_atomicity.py` (el patch en el happy path + asserts de balance/tx/source + docstring "post-credit misiones (best effort) + event listeners (best effort)") + besito unit post-Item1 + event_bus tests + reaction_mission_flow stricts. Re-runs in F4/F5.
   - 1-line/guard test fix + comment + daily hasattr: minimal como en ports de Item5/6 (cambio de acceso + nota "# 1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer); was ...") + daily precedent guards (if hasattr(service, "besito_service") else BesitoService(db=...).get_balance(...) or similar fallback; class patch to services.besito_service.BesitoService for local intercept in cross when locals used).
   - GSD entries detalladas: "pre-xxx <file> (F<N> <motivo>) - <desc + refs DoD + patrones copiados al pie de la letra de item5/6 PLAN + gsd-reward-besito-eventbus.log + gsd-remaining-besito-compositions.log + impact10 + atomicity gold + daily precedent + 25/26/27 pool phrase>"; wc; style de item2/5/6/7/8/9 (46+/55+/40+/800+/...) y 24/25/26/27 (BATCH/POOL + self-check full + critical + handoff).
   - Safe points + self-check al final del log: estructura de item5/6/7/8/9 (lista fases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3-4 files + log + PLAN + opt SUMMARY + 0/0/0/0, locals in the exact debit/balance sites only, observer + "MUST NOT credit/debit/mutate" + DESIRED + "store | ..." if, central reg + "+ Item 10 store" if, 1-line/guard ports with class patch/hasattr + comments, no new tests beyond ports/guards, no other files, logging, no prod change, 3 crit + atomicity contracts + get_service/EventBus protected)/desviaciones/tests críticos/"Item 10/28 closed. Second of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + ...) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4.") + 24/25/26/27 BATCH/POOL note.
   - Precedentes de PLAN/GSD + handoff + pool/batch: .planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md (y SUMMARY + log que nombra el pool context), 24/25/26/27 PLANs + SUMMARYs + gsd logs citados (BATCH "4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", "Item 7/25 closed. First of new pool of 4. Previous batch of 4 (ending with Item 6/24 ...) closed with tests passing per 24-SUMMARY BATCH note + self-check PASSED. Ready for arch-enforcer re-scan (...) + test-guardian (...) + gsd-executor del siguiente item del pool de 4.", "Item 8/26 closed. Second of new pool of 4. ...", "Item 9/27 closed. ..."; pool phrase verbatim); 22/21/20/19 + gsd-*.log citados; "second of new pool of 4" al final.
   - Atomicity gold: `tests/integration/test_cross_service_atomicity.py` (file+TestSession, try/finally dispose/close, DESIRED, patch event, strict == on deltas/counts, "credit survives deliver False", "post-credit best effort (misiones + listeners)", N806 with doc, fresh TG 777x, daily guards "if hasattr... else BesitoService(db=...)", class patch precedent, gather return_exceptions).
   - N806 tolerance with doc: copy from besito unit (TestBesitoServiceRaceCondition or similar) + atomicity gold for TestSession.
   - "Copia patrones **al pie de la letra**": story listener block verbatim (adapt 3-4 words), bot reg block verbatim (extend), Reward local inside _deliver + 1-line test comment, atomicity gold patch+DESIRED+file+TestSession+strict+"credit survives deliver False"+"post-credit best effort (misiones + listeners)"+N806+777+try/finally+gather+guards, daily hasattr guard + fallback, Item5/6 1-line/guard ports + comments, 25/26/27 pool phrase + self-check structure + handoff language verbatim.
   - 3 critical systems + atomicity contracts + get_service/EventBus: siempre en mente (gamif primary for purchase debits + listener for missions/rewards post-purchase (though debit no emit); narrative 0 direct; channel/VIP 0; locals owns=False share db; debit/credit do own commits; schedule post only on credit; bus best-effort; "credit survives" + post best effort documented + re-run protected; get_service already in handlers/store_user; no change to store_user per task).

5. **Decisiones (sección 4 del PLAN):** Al inicio de la fase relevante (primer GSD entry de la fase), registra qué decidiste para nombre de listener, si se agregó, cómo estructuraste el local Besito(db=) (1 línea o con var, por método), si el import en tests fue necesario, si cross tuvo store complete_order paths a portear, etc. Si difieres del "preferido", explica brevemente (mantén espíritu tight + gold + 0 behavior).

6. **Gates y re-runs:** 
   - Corre los targeted pytest con los flags exactos de arriba + por-fase.
   - Si un unrelated fail preexistente aparece (ej. alembic_heads, daily concurrent UNIQUE, cross daily !success pre patches en priors, N806 in gold, SA warnings, Runtime emit not awaited, Deprecation utcnow, MovedIn20, unraisable), documéntalo en log pero **no lo cuentes como regression del Item** (precedent 27/26/25/24/23/22/19/20 "Riesgo: baseline shows pre-existing unrelated fails ... document; do not count as regression").
   - Re-run de atomicity gold full (happy + sad/partials with patch schedule_emit + strict + DESIRED + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession/file + 777 + gather + N806 tol w/doc) + broader -k "store or purchase or complete_order or atomicity or besitos" + unit store complete_order paths + bot smoke reg+emit if listener + story/besito/broadcast spot is obligatorio en F5 (y spot en F2/F3/F4 si relevante).
   - Siempre GSD pre- antes del pytest/ruff/grep grande.
   - Al final F5: re-ejecuta los combinados + broader smoke filtrado + self-check + pool phrase verbatim + handoff.

7. **Alcance (recuerda siempre):** Solo edita los archivos listados en "Archivos que se modificarán" + el log GSD + (este PLAN ya está) + opcional SUMMARY.md al final. Si sientes la tentación de "reducir más composiciones (story etc)", "agregar tests para el listener", "cambiar a get_service", "tocar handlers o package/reward delivery", "editar más docs", "agregar listeners para daily", detente: scope tight para esta entrega (recomendado por analyzer: solo store_service held + locals inside the exact 3 purchase methods' debit/balance sites + optional high-value obs listener + central reg if + 1-line/guard ports in cross + store unit + targeted docs if precedent; 0 other files per "0 other files (0 store_user -- already get_service; 0 package/reward delivery)"; "second of new pool of 4"). El analyzer + 27/26/25/24/23 handoff recomendaron empezar tight aquí.

8. **Al final del Item (F5) + pool 4:**
   - Completa el self-check en el log (lista de fases, DoD cumplidos, archivos modificados, tests que pasaron, reglas verificadas (GSD pre every, scope tight 3-4 files + log + PLAN + opt SUMMARY + 0/0/0/0, locals in the exact debit/balance sites only, observer + "MUST NOT credit/debit/mutate" + DESIRED + "store | ..." if, central reg + "+ Item 10 store" if, 1-line/guard ports with class patch/hasattr + comments, no new tests beyond ports/guards, no other files, logging, no prod change, 3 crit + atomicity contracts + get_service/EventBus protected), desviaciones (si las hubo), tests críticos a re-correr en futuro (lista explícita), "Item 10/28 closed. Second of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + ...) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4.").
   - (Opcional pero recomendado) Produce `.planning/phases/28-remaining-besito-store/SUMMARY.md` con executive + refs al log GSD + comandos de re-verificación (sigue estructura de 27/26/25/24/23/22/21/20/19).
   - Confirma en log: "Self-Check: PASSED" + el pool phrase verbatim.
   - Reporta (en tu salida final o log) que el pool de 4 items continúa (this is second); propone si user quiere más en futuro (but do not initiate without new prompt per user instr).
   - El siguiente agente (gsd-executor siguiente item del pool 4 o arch-enforcer/test-guardian) usará el log + este PLAN + los cambios como fuente de verdad. Arch-enforcer re-scan enfocado en los sitios reducidos (locals + no-held + obs contract + atomicity golds). Test-guardian: re-correr los tests críticos listados en self-check.

9. **Si algo no está claro o difiere del "reporte del analyzer":** El prompt del usuario + este PLAN (basado en discovery completa + el reporte completo descrito en el prompt + handoff explícito de 27/26/25/24-SUMMARY/PLAN + 23/22 handoff + impact10 + gsd-impact-analyzer-item10 log) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad real de nombre/firma/contrato (e.g. listener name exacto, si cross tiene store complete_order paths a portear); de lo contrario, elige conservadoramente siguiendo precedentes (story listener copy, atomicity gold for the local db= + patch + guards + TestSession + strict + "credit survives" + "post-credit best effort" + N806 + 777 + try/finally + gather, bot reg block, 1-line/guard minimal + daily hasattr, Reward/Item6 local inside + 1-line test comment, 25/26/27 pool phrase + self-check structure + handoff language verbatim, GSD style) y registra la elección en GSD.

**¡Ejecuta con disciplina total. Cierra el Item de forma limpia, segura, medible y con trazabilidad GSD completa. La reducción de la composición held en StoreService (vía el patrón del bus para loose coupling de notificaciones, manteniendo el command debit local para atomicity) queda hecha sin impacto en los 3 sistemas críticos ni en los contratos de compra/partial failure. Segundo de nuevo pool de 4. Listo para arch-enforcer + test-guardian + siguiente item del pool de 4 (flujo continúa automáticamente).**

---

**Fin del PLAN para 28-remaining-besito-store (Item 10, second of new pool of 4).**

Referencias rápidas para el executor (actualizar con líneas reales durante ejecución si cambian):
- Impact report (source of truth): .claude/agent-memory/impact-analyzer/item10-remaining-besito-store.md (mapa, risks, scope 4 files max (svc + bot if + 1-2 tests), "second of new pool of 4", "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters...", helper/observer examples on_besitos_awarded_store_observer + "MUST NOT credit/debit/mutate" + DESIRED CONTRACT + "store | besitos_awarded_received", sites complete_order~493 debit + rechecks~488 + direct~366 + create~440, tests 1-line/guard ports + class patch to services.besito_service.BesitoService for local intercept + "if hasattr... else BesitoService(db=...)", "no new tests beyond tight", 0 behavior/0 atomicity/0 other files (0 store_user -- already get_service; 0 package/reward delivery), design "local Besito(db=...) *only* inside the tx method for atomicity + history + return", "schedule_emit best-effort post-commit", "high-value obs listener ... 'MUST NOT credit/debit/mutate' + best-effort + DESIRED CONTRACT + domain log 'store | besitos_awarded_received'", "central reg in bot.py", "1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)", golds (cross full w/patch + broader gamif store/purchase), docs/CLAUDEs if precedent, decisions Item10, self-check PASSED + pool phrase, handoff to planner (5-phase tight) -> executor -> arch (locals+no-held+obs contract+atomicity) -> test-guardian -> tests).
- Gold cross/race/atomic + patch + "best effort" note + daily guards + class patch precedent + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession + 777 + gather + N806 + strict: `tests/integration/test_cross_service_atomicity.py`.
- Story listener precedent (copy source): `services/story_service.py:670-694` (comment + on_besitos_awarded_from_gamification + "MUST NOT" + log).
- Reward/Item5 local inside method + observer + 1-line test + bot reg precedent: `services/reward_service.py` post-Item5 (_deliver_besitos local + observer at 354+).
- Broadcast/Item6 local inside credit sites + observer + 1-line/guard + bot reg precedent: `services/broadcast_service.py` (locals in register_reaction + check_and_register_reaction + observer at 170+).
- Daily/Item6 local inside claim + property kept + hasattr guards precedent: `services/daily_gift_service.py` + tests at 288/727-728 + fallback to BesitoService(db) + cross 726/762 class patch adjust.
- Central reg precedent: `bot.py:200-210` + imports 69-77 (extend after existing + "+ Item 10 store").
- EventBus + schedule_emit + DESIRED: `services/event_bus.py:23-...` (contract), schedule_emit, get.
- Store sites (complete_order debit~493 + rechecks~488, direct~366, create~440, _init~65 held, close untouched): `services/store_service.py`.
- Besito credit (with_for_update + post schedule) + debit (with_for_update + commit param): `services/besito_service.py:107-150` (credit) + 152+ (debit).
- Store unit test access site (1-line port): `tests/unit/test_store_service.py` (test_complete_order_success ~134 + other complete tests).
- Precedentes PLAN/GSD + handoff + pool/batch: `.planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md` (y SUMMARY + log), 24/25/26/27 PLANs + SUMMARYs + gsd logs citados ("4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", "Item 7/25 closed. First of new pool of 4. Previous batch of 4 (ending with Item 6/24 ...) closed with tests passing per 24-SUMMARY BATCH note + self-check PASSED. Ready for arch-enforcer re-scan (...) + test-guardian (...) + gsd-executor del siguiente item del pool de 4.", "Item 8/26 closed. Second of new pool of 4. ...", "Item 9/27 closed. ..."; pool phrase verbatim "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. (This is the Nth of the new pool of 4 per impact + PLAN + prior SUMMARY BATCH close; previous batch of 4 closed with tests passing, self-check PASSED, and explicit BATCH note.)"); 22/21/20/19 + gsd-*.log citados; "second of new pool of 4" al final.
- GSD log para este Item: `.planning/quick/gsd-remaining-besito-store.log`
- Reglas: `CLAUDE.md`, `rules.md`, `architecture.md`, `handlers/CLAUDE.md`, `services/CLAUDE.md`, `services/missions/CLAUDE.md`, `services/gamification/CLAUDE.md`, `services/store/CLAUDE.md`, `models/CLAUDE.md`, `decisions.md`, `AGENTS.md`, HARDENING_ROADMAP.md.
- Next: gsd-executor para este item (F1→F5 strict) → self-check + pool note "second of new pool of 4" → arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) → test-guardian (re-correr críticos listados) → gsd-executor siguiente item del pool de 4.

Listo para gsd-executor. Ejecuta F1 → ... → F5 con GSD pre en cada paso + self-check PASSED + POOL confirm al final. Handoff explícito.

**Hecho con 💋 para Diana (Señorita Kinky) — gsd-planner subagent (Item 10, second of new pool of 4, post Item9 mission_admin close via full 6-step + "suite protege" + tests green).**

Self-Check (planner): PASSED.