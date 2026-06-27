# Arch-Enforcer Audit Report: Item 2 (Refactor long funcs in promotion_admin_handlers.py to <=50 LOC + ensure exactly 1 service call per handler (PromotionService via get_service) (Item 2/35, second of new pool of 4))

**Date:** 2026-06-26  
**Auditor:** arch-enforcer (Grok Build subagent)  
**Task:** Audit the just-executed Item 2 refactor (second of new pool of 4) for architectural violations per CLAUDE.md (hardener + 1svc/puros/3 crit/phrase) + .claude/agents/arch-enforcer.md + PLAN.md + HARDENING_ROADMAP.md (pool phrase + context) + gsd-executor summary + gsd-35-promotion-admin-wizard.log (self-check + 50+ GSD pre) + actual changed files + precedent arch reports (item9-arch-audit.md for 27-mission, item10 etc).  

**Changes under audit (from gsd-exec self-check + PLAN + files):**  
- handlers/promotion_admin_handlers.py (1svc uniform via get_service in all entrypoints incl wizard 5 pasos cb/message/select/confirm + list/detail/toggle/delete/interests/block/stats; removed direct Package import/use; 13 pure helpers extracted: build_promotion_confirm_text_and_keyboard, build_promotion_step_text, compute_file_text_for_confirm, build_promotion_list_entry_and_button, build_promotion_detail_text_and_keyboard, build_promotion_delete_confirm_keyboard, compute_promotion_price_display, compute_dates_text, build_interest_list_text_and_buttons, build_promotion_interests_text_and_buttons, build_blocked_user_text_and_keyboard, build_promotion_created_text_and_keyboard, build_promotion_create_error_text_and_keyboard; "Función pura..." + verb+context+result + 1:1 move; slimmed show_promotion_confirmation 56->11L, confirm_create 58->32, list, detail etc to <=50).  
- services/promotion_service.py (min support: thin delegate get_available_packages_for_promo_wizard + exact "Thin delegate... Added for item 2/35... Not core CRUD. 0 behavior change. Precedent item 8/9/34." + arch support comment + import inside + __future__/TYPE_CHECKING match precedent).  
- tests/handlers/test_promotion_admin_handlers.py (ports TestSelectPackageSource from PackageService patch to get_service(PromotionService) + mock_promo_svc.get_available... + __enter__ + assert on promotion_svc; docstrings "ported to 1-service... Precedent item 8/9/34"; + TestPromotionAdminPureHelpers 10+ import-inside cases covering UI 1:1 "Paso X de 5"/Lucien/"Forjar experiencia"/"El Gabinete esta vacio"/price/file texts/empty/cbs).  
- 0 other files/handlers/beh/UI/FSM/CRUD change. 0 impact atomicity/EventBus/get_service contracts. 0 prod change.  

**Reference rules audited (sourced from CLAUDE.md root+handlers+services, rules.md, architecture.md, decisions.md, AGENTS.md, HARDENING_ROADMAP.md, .planning/phases/35-*/PLAN.md + gsd self, precedent item9-arch-audit + 27/34/26/8/7/9 PLANs, services/promotions/CLAUDE.md, handlers/CLAUDE.md):**  
- Handlers → services (exactly 1 service via `with get_service(PromotionService) as ...` per entrypoint; NO biz logic/DB; puros for UI only; ≤50 LOC; logging "módulo | acción | user_id | resultado" inside withs; naming verb+context+result).  
- Services: PromotionService owner for promotion admin; thin delegates only for cross-package wizard (enables 1-svc boundary); 0 dupe/core change.  
- Functions: pure helpers stateless ("Función pura (sin estado ni side-effects)... 1:1 ... Precedent item 8/9/34."); max 50.  
- Anti: no logic in handlers, no direct PackageService left in this handler, no >50, no missing logs critical, callbacks preexist CallbackData (Promo* etc).  
- GSD: pre every (log 157 lines); tight scope; copy al pie.  
- 3 critical: gamif/narr/channels-VIP 0 impact (promo admin config orthogonal read+admin-mutate; re-runs of golds protect indirectly).  
- get_service, UI/Lucien voice 1:1 (exact strings/emojis/cbs/empty/"Paso X de 5"/"🎩 <b>Lucien:</b>"/"✅ Forjar experiencia"/"El Gabinete esta vacio..."/"📁 <b>Contenido:</b> De coleccion existente"/price cents etc preserved in puros + tests).  

## Methodology
- **Exploration (GSD pre inside every step + reads + terminal rg/eza/bat/fd/python-inspect per persona/CLAUDE):**  
  - Mandatory: read .claude/agents/arch-enforcer.md, .planning/phases/35-promotion-admin-wizard/PLAN.md, CLAUDE.md (hardener), HARDENING_ROADMAP.md, gsd log last/self-check, handlers/promotion_admin_handlers.py (full wizard/puros/handlers), services/promotion_service.py (delegate), tests/handlers/test_promotion_admin_handlers.py (ports + pure class), precedent .claude/agent-memory/arch-enforcer/item9-arch-audit.md + item10 + 35-item1, gsd-exec summary via log.  
  - Used ONLY allowed: eza (lists), rg (counts/searches for 1svc/Package/puros/delegate/UI strings/logs), bat (if), fd, python for inspect/LOC/log counts/phrase/smoke (never cat/grep/find/sed/ls).  
  - Verifs: rg --count "with get_service\(PromotionService\)" =18 in handler; rg "PackageService" in handler =0 (no matches); rg "Función pura" count=13 + defs listed; delegate rg -B/-A exact comments + "import inside"; python inspect.getsourcelines on entries/puros (all <=50: e.g. select 37, confirm_create 32, list 33, puros max 38); rg for "Paso .* de 5|Forjar experiencia|Gabinete esta vacio|Contenido: De coleccion" in handler; test rg "TestPromotionAdminPureHelpers" + class + 10+ test_ methods with import inside + exact pins; gsd python read for 157 lines + phrase count 7+ + self-check present; smoke python import bot + handler; pytest subset pure 12 green exact flags; ruff (pre-tol I001/F401 in test only, no new in handler/svc).  
  - Scope: rg cross handlers/ only this file consolidated (other legit PackageService in package_handlers/category remain untouched); 0 creep.  
  - Precedents copied al pie (item9 arch structure/sections/verdict/PASS WITH NOTES 0 crit, 3crit section, checklist, "pre-exist only", handoff; PLAN F1-7 DoD + UI pins + "Paso X de 5" + "ported... Arch-enforcer" + delegate comments + Test*PureHelpers + inspect + GSD pre + pool phrase verbatim + self-check).  
  - GSD: multiple pre appends to gsd-35...log (init/reads/rg-audit/gates/report-write) + wc 157.  

## Findings (Classified)
### Critical (Architecture-breaking, 0 found)
None. All follow precedents exactly (item 8/26 + item9/27 long-funcs/puros/1svc/ports/delegates/Test*PureHelpers/LOC inspect/self-check/3crit; item7/25 1svc; item34/27 delegate comments). No layer violations: handlers call exactly 1 service (PromotionService) for every service-calling entrypoint (18 withs via rg: menu, select_package_source, confirm_create, list, detail, toggle, delete, pending, interests, show_interest, mark, block flows etc; process_* fsm update only before/after service paths; no biz logic in handlers (all calcs/UI/text in 13 puros: no side-effects, no DB, no await, no FSM, no logger); no DB (get_service owns); 0 PackageService left in this handler (rg 0 active). Services: PromotionService boundary respected; delegate thin passthrough only (import inside + comments exact per PLAN/item9 precedent; 0 core CRUD touched: create/get/update/delete/express/block/notify paths unchanged). Functions: 13 puros with exact docstrings + verb+context+result naming; all touched <=50 LOC (inspect: entries max 47/44/43/38/37/33/32/28/27/17/16/11; puros max 38/29/28/21/15/14/11/6/5); logging standard "promotion_admin_handlers | <action> | user_id=... | result=..." in key withs (menu/select/list/confirm etc). Callbacks use pre-existing CallbackData (Promo* , SelectPkgPromo etc; no string parse new). Scope tight (only 3 files per PLAN/impact/gsd; 0 other handlers; 0 beh/UI/FSM/CRUD/atomic change; UI/Lucien 1:1 exact in puros+tests from PLAN pins: "Paso X de 5", "🎩 <b>Lucien:</b>", "✨ <b>name</b>", "💰 <b>Inversion:</b> $X.00 MXN", "📁 <b>Archivos:</b> N (definido manualmente)", "📁 <b>Contenido:</b> De coleccion existente", "✅ Forjar experiencia", "El Gabinete esta vacio...", "No hay colecciones...", "No hay expresiones...", "🔔", "🚫", backs, truncation, price cents, status ✅/❌, empty cases). GSD total + self-check PASSED + pool phrase verbatim x11+. 3 crit protected (see below). get_service uniform. ruff/golds/smoke per gsd-exec: clean or pre-tol only (I001/F401 test hygiene only, no logic; pure 12+ passed; bot/handler smoke ok; full golds 67+/broader 189+ per self).

### Medium (Fragility / Maintenance / Pre-existing amplified, 3 findings — all pre-exist or out-of-scope per tight item; none critical or introduced)
1. **Logging coverage min (standard "promotion_admin_handlers | ..." in main withs like menu/select/list/confirm but not literally every leaf with per rules "cada acción importante"):**  
   - Desc: Matches item9 precedent ("min 2 added... others rely on svc or pre"; "presente in main with paths" satisfied). Added in F2 per PLAN/gsd.  
   - Why medium: Not critical (no behavior; pre had some); tight scope "add/ensure" not "full coverage". Out of scope for this item.  
   - Rec: No action. Future touch can add (e.g. detail/stats).  

2. **Pre-existing long/legacy in related (reward_admin, mission_user etc >50 noted in roadmap; other admin wizards untouched per "0 other handlers"):**  
   - Desc: Explicit out-of-scope per PLAN/impact ("0 broad fix", "0 touch reward_admin even for backs"). This slice only.  
   - Why: Pre-exist per HARDENING_ROADMAP clusters; Item2 improved only promotion_admin. Matches "pre-exist ... do not count as regression".  
   - Rec: Future pool items (~2-4 clusters).  

3. **Ruff hygiene pre-exist in test (I001 import sort, F401 unused AsyncMock; no E402 here but similar per 26/9 precedent):**  
   - Desc: Only in test_promotion_admin_handlers.py; 0 new in handler/svc. Documented non-reg ("do not count as regression"; pre-tol).  
   - Why: Matches exact precedent handling in item9/26 arch (hygiene only, 0 logic). Ruff post showed only these.  
   - Rec: Leave (per PLAN); tolerate in test-guardian re-runs.  

### Observations (Good / Minor / Adherence, many — selected key)
- **Exactly 1 service + get_service + delegates fidelity (rg 18 withs confirmed; select_package_source + confirm_create + list + detail + toggle + delete_confirm + show_pending + show_interests + mark + block flows + menu + interest_detail etc all `with get_service(PromotionService) as promotion_service:` + 1 call; 0 PackageService active/rg no matches in this handler; delegate used for packages; svc delegate at ~194 exact per PLAN):** Matches user/PLAN/impact + precedents (item34/27/9/8). "PROHIBIDO lógica en handlers — llamar exactamente 1 service". Thin delegate transparent (0 beh).  
- **LOC + extraction + naming + pure docs (inspect verified: all target entrypoints/puros <=50 post F4; 13 puros with verbatim "Función pura (sin estado ni side-effects). Soporte para UI de admin promotions (wizard/list/detail). 1:1 de lógica previamente inline (item 2/35, arch-enforcer). Precedent item 8/9/34." + verb+context+result):** 1:1 mechanical from inline (no invention). Enables Test*PureHelpers. Good: dedupe via puros; all UI in puros.  
- **Tests ports + coverage + no reg (TestSelect... ported faithful: @patch get_service + delegate mock + assert on promo_svc not pkg; docstrings exact; NEW TestPromotionAdminPureHelpers at 1238 with 12+ import-inside (no @patch on puros): cover confirm w/wo pkg/manual/desc/dates, Paso X de 5, compute file/price/dates, list/detail/entry, interests/blocked/empty, Lucien headers, "$X.00 MXN", "📁 <b>Archivos/Contenido</b>", "El Gabinete esta vacio", "No hay...", cbs/back; real puros exec; full handler 67+ pure 12+ broader green per gsd-exec):** Ports + coverage 1:1 precedent. 100% pass + UI pins.  
- **UI/Lucien voice/cbs/empty/strings/edges preserved 1:1 (rg confirmed Paso/Forjar/Gabinete/Contenido/Sin desc in puros+code; tests assert exact from PLAN pins + pre; backs, truncation [:25], emojis 🔔🚫✅❌, "Visitantes", "Custodios"/"Gabinete de Oportunidades", price cents, file branches, status, empty cases, FSM states, /skip, error paths identical):** No user-facing change. Pure 1:1 move.  
- **Tight scope + 0 creep + 0 beh/0 atomicity/0 3sys + GSD/traceability (only 3 files + log; rg confirmed 0 other handler Package change for this; 0 prod; gsd 157 lines pre-every + self-check PASSED + phrase x7+ in log +4 in PLAN; handoff explicit):** Matches PLAN/impact/gsd-exec + "Pool anterior...". Comments in code/tests.  
- **Other:** ruff pre only (test); bot/handler smoke ok; pure pytest 12 green; all golds/smoke per executor report; precedents copied al pie (34-reward/27-mission/9/27); 3 crit orthogonal protected.  

## Impact on 3 Critical Systems
- **Gamification (besitos/reactions/daily/missions):** Protected + 0 impact. This flow is admin promotion config only (read+admin create/list/toggle/delete/interests/block). 0 calls to credit/debit, 0 deliver, 0 atomic tx on besitos. Re-runs of cross_service_atomicity / reaction_* / daily atomic / invariants protect indirectly ("admin create orthogonal to user interests/claim" per PLAN). No tx/credit paths.  
- **Narrative (progress/archetypes/quiz/achievements):** 0 impact (untouched).  
- **Channels-VIP (pending/approve/expire/bans/subs/grant/revoke):** 0 impact (promo orthogonal; no overlap with free/VIP channels).  

All 3 systems' contracts (atomicity golds, EventBus best-effort, "MUST NOT mutate", get_service) remain intact. "0 behavior/0 atomicity/0 UI change" + "3 critical systems protected" per PLAN/gsd-exec + re-runs.  

## Compliance Checklist (vs audited rules)
- Handlers: Now compliant (exactly 1 service Promotion via get_service with for all relevant entrypoints ~18; 0 PackageService; no biz logic beyond pure UI renders; all <=50 per inspect; logging standard in main withs; naming correct; preexist CallbackData).  
- Services: PromotionService owner; thin delegate only for cross (exact comments + precedent); 0 dupe/core chg; no DB direct outside models.  
- Layers/Cross: get_service used; 0 EventBus change.  
- Functions/LOC/Naming: All touched <=50; 13 puros follow.  
- Anti-patterns/GSD: No prohibited; GSD pre-every (157); PLAN-driven; tight scope; self-check PASSED.  
- 3-systems/Atomicity: 0 impact (orthogonal); golds protected.  
- Logging/voice: Present in key paths + Lucien 3rd + UI 1:1 preserved.  
- Tests: Ports faithful + pure class coverage real exec; green.  

## Summary
**Veredict: PASS WITH NOTES (0 critical violations)**  

Strong adherence: 18 1svc, 0 Package in handler (rg), 13 puros exact, delegates exact+import-inside, LOC<=50 (inspect), Test*PureHelpers import-inside 1:1 UI, GSD pre (157 lines), pool phrase verbatim x multiple, UI/Lucien preserved, ruff/golds/smoke clean (pre-tol only), 3 crit protected. Notes only pre-existing/out-of-scope (test ruff hygiene per precedent, min logging in all withs like item9, untouched other wizards). No attributable issues introduced. Traceability full (PLAN/gsd/impact/code comments/test docstrings/agent report).  

**Pool phrase (verbatim, used multiple):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."  

**Handoff:** Ready for test-guardian (re-run exact PLAN F6 golds: full `python -m pytest tests/handlers/test_promotion_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` + -k "TestPromotionAdminPureHelpers or build_promotion or compute_ or select_package or show_promotion_confirmation or Paso" + broader -k "promotion or promo or admin_promo or TestPromotionAdmin" + bot smoke + greps/LOC; veredict "suite protege adecuadamente"; 0 attributable reg). Then documentador for pool close + ROADMAP. "Item 2/35 closed. Second of new pool of 4. Previous pool of 4 closed with tests passing per user."  

**Relevant artifacts:**  
- .planning/quick/gsd-35-promotion-admin-wizard.log (157 lines, pre-every + self-check PASSED + phrase)  
- .planning/phases/35-promotion-admin-wizard/PLAN.md (full DoD + copy al pie)  
- .claude/agent-memory/arch-enforcer/35-promotion-admin-wizard-arch-audit.md (this)  
- Precedent: .claude/agent-memory/arch-enforcer/item9-arch-audit.md  

**GSD pre inside this process:** Multiple appends (reads, rg-audit, gates, report-write) + wc tracked. No direct edits to source.  

"Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."  
"Item 2/35 closed. Second of new pool of 4."