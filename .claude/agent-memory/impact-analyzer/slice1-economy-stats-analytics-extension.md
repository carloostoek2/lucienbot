# Impact Analysis: Slice 1 - Economy Stats Expansion (AnalyticsService read-only best-effort methods for Custodio visibility)

**Agent:** impact-analyzer (per .claude/agents/impact-analyzer.md + hardener workflow)
**Date:** 2026-06-16 (current session)
**Context:** Post Item 11/29 (observability-health), Item 10/28 (store besito), Item 9/27 (mission admin), prior besito decoupling (Items 5/6), get_service unification, mw hardening. Following hardener agile standard (pools <=4, 6-agent seq incl explicit impact, documentador at pool close, pool phrase verbatim, 3 crit + atomicity/EventBus/get_service contracts protected, GSD pre inside, copy golds al pie).
**Scope (per user task + "approved economy stats expansion plan"):** ONLY add 3 new read-only best-effort methods + internal helpers in AnalyticsService (services/analytics_service.py). No handler changes yet, no voice/Lucien, no other services mutated, no new tracking/columns/models, no writes. Queries read-only on Besito* models (+ optional User/Subscription overlay best-effort). Methods:
- get_economy_overview(window_days: int | None = 30) -> dict (totals earned/spent, circulation, velocity proxies)
- get_source_attribution(window_days: int | None = 30) -> dict (breakdown by TransactionSource for CREDITs: sum amount, count, %, using BesitoTransaction group + func)
- get_top_earners(limit: int = 20) -> list (order BesitoBalance by total_earned desc; optional User join for usernames; include earned/spent/net)
Reference approved plan sections: "Analytics home" (dashboard/stats/exports for Custodios per CLAUDE/AGENTS), "read-only" (like current Analytics + Health Item11 precedent), "windows" (time-bounded queries for bounded perf/visibility).

**Pool context (verbatim, mandate):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**GSD pre:** Initiated/updated via run_terminal_command appending to .planning/quick/gsd-impact-analyzer-slice1-economy-stats.log (multiple entries with timestamps + findings during exhaustive reads/greps; wc tracked; all discovery via tools; report persisted + MEMORY updated after full map). No file mods to source before/ during analysis (per "No code edits — only analysis").

**References (exhaustive prior research cited):** 
- .claude/agents/impact-analyzer.md (role + memory protocol; types project/feedback/reference)
- Root CLAUDE.md (domains table: Analytics "Dashboard stats, exports CSV"; Observability Health follows "AnalyticsService pattern al pie"; 3 crit: gamif besitos/credits/reactions/daily/missions, narrative, channels-VIP; hardener workflow + 6-agent + documentador + pool phrase; rules: handlers=exactly 1 svc, <50 LOC, verb+ctx+res, "módulo | acción | user_id | resultado" logging, is_admin before admin, get_service; architecture.md, services/CLAUDE.md, handlers/CLAUDE.md)
- AGENTS.md (analytics_handlers, health_service, analytics_service; hardener standard codified from tirones 25-29/Items7-11; pool phrase)
- decisions.md (Item 11 Health full entry + Analytics precedent; Item 10/6/5 besito decoupling + atomicity golds; "Reuses existing patterns al pie (AnalyticsService read-only _get_db/owns/close/direct counts; ... structured logging...)"; adoption of hardener)
- .planning/HARDENING_ROADMAP.md (full sections 1-5: initial analysis clusters, decisions, execution (exact 6-step incl impact-analyzer), What Has Been Done (Items 9/27 10/28 11/29 + Health precedent), What Is Missing (long funcs, remaining debt), Proposed Next; verbatim pool phrases multiple; metrics 0 crit arch, 0 attrib reg, tight scope; cites 27/28/29 *-SUMMARY/PLAN + agent reports)
- .planning/phases/29-observability-health/PLAN.md + 29-*-SUMMARY.md (Health as read-only best-effort following Analytics al pie; exact gold patterns list: lifecycle, logging, get_service 1-call + is_admin in analytics_handlers, direct counts, <=50, best-effort/try/except/degraded, arch comment "Item 11 / ..."; test re-runs list with exact -k + flags; 0 impact phrasing for 3 crit + contracts; bot on_startup, terminal script, voice copy from analytics_dashboard)
- .planning/phases/28-remaining-besito-store/ + 27-mission-admin + prior (golds, self-check PASSED, arch "PASS WITH NOTES 0 critical", test-guardian "suite protege adecuadamente")
- .planning/phases/09-polish-hardening/ (analytics origin: get_dashboard_stats + 2 exports; VERIFICATION of flows/queries)
- .planning/notes/2026-04-05-sistema-auditoria-economia-registre.md + .planning/todos/pending/2026-04-05-sistema-auditoria-economia-historial-movimientos.md (old broader auditoria-economia: new TransactionLog model, integrates logging into Besito/Store/Mission/VIP, user /historial + admin global audit/CSV/filters/stats; "Related: analytics (exportación CSV, estadísticas)"; OUT OF SCOPE for this read-only Slice 1)
- .planning/phases/.../fases_refactor_testing.md (notes dupe total besitos circulation py sum in besito:234-236 vs analytics ~50; "Analytics/stats usan queries directas saltando BesitoService (dupe + bypass)")
- services/analytics_service.py (current impl + queries; see lines below)
- services/health_service.py (pattern copy target; besito queries in sanity)
- services/besito_service.py (domain owner; get_total... + top + tx history; credit/debit that maintain earned/spent)
- handlers/analytics_handlers.py (only prod consumers)
- tests/unit/test_analytics_service.py + tests/handlers/test_analytics_handlers.py + golds (test_invariants.py, test_cross_service_atomicity.py, test_besito_service.py etc)
- models/models.py:200-248 (TransactionSource enum full values incl REACTION/DAILY_GIFT/MISSION/PURCHASE/ADMIN/ANONYMOUS_MESSAGE/GAME/TRIVIA/STREAK_PROTECTION; TransactionType CREDIT/DEBIT; BesitoBalance: user_id BigInt unique, balance/total_earned/total_spent BigInt; BesitoTransaction: user_id FK to balances.user_id, amount signed, type, source, desc, ref_id, created_at; rels)
- models/CLAUDE.md (TransactionSource values, Besito* models)
- .claude/agent-memory/impact-analyzer/ (prior: item11-observability-health.md (template + Analytics read-only + besito sanity queries map + 0-risk 3crit phrasing + test list + gold copy instructions); item10-...md, item9-..., item6-... etc; MEMORY.md)
- scripts/reset_trivia.py, fix_connection_leaks.py (minor direct + old list)
- bot.py:345 (analytics_router include only; no svc calls)
- utils/lucien_voice.py (analytics_dashboard uses stats from current get_dashboard; no new for this slice)
- keyboards/inline_keyboards.py (admin_analytics btn; no change this slice)
- services/CLAUDE.md (Health follows Analytics; cross refs to Item11 impact + hardener)

**Explicit: No dedicated "economy stats expansion plan" or "Slice 1" doc located despite exhaustive searches** (grep -i "economy stats|stats expansion|economy.*expansion|get_economy|source_attribution|top_earners|Slice 1|slice 1|auditoria.*economia" across root/.planning/.claude/ + list_dir .planning/notes/phases/quick/todos + read specific auditoria files + HARDENING/ROADMAP/decisions). Closest/old: the 2026-04 auditoria todo (broader, new model+writes+user history — contrast this scoped read-only analytics extension). Approved scope taken from task description itself + cross-refs in CLAUDE/AGENTS/HARDENING ("Analytics home", read-only best-effort precedent, windows for time-bounded) + Health Item11 (observability extension inside analytics_handlers pattern). Report treats task as authoritative for "approved plan".

---

## Executive Summary (risk level)

**Proposal (Slice 1):** Extend the existing AnalyticsService (the designated home for Custodio-facing dashboard/stats/exports) with exactly 3 new read-only best-effort methods using time windows (default 30d) for economy visibility: overview (earned/spent aggregates, circulation, velocity proxies), source attribution (CREDIT tx breakdown by TransactionSource with sum/count/% via group+func), top earners (BesitoBalance.total_earned order + optional User username overlay + earned/spent/net). Internal helpers only (e.g. window filter, attribution aggregation). Follows Analytics + Health (Item 11) patterns al pie: lifecycle (_get_db/owns/close), direct model queries for speed, best-effort try/except/degraded returns (never blocks/mutates), structured logging "analytics_service | ...", verb+context+result, <50 LOC (helpers for length), arch comments. No prod behavior change.

**Overall risk: LOW** (analogous to item11-observability-health impact which was LOW + executed successfully with arch PASS WITH NOTES 0 crit + test "suite protege adecuadamente"). Pure additive read-only inside Analytics domain (already queries Besito* directly for totals/exports). 0 writes, 0 calls to credit/debit paths, 0 EventBus, 0 new tracking. Re-uses models that already maintain invariants (earned/spent updated only in besito_service credit/debit). Windows bound queries (avoids full-history scans noted as dupe concern in old refactor docs). Future handler slices will use get_service + is_admin precedent (already wired for analytics).

**Key positives:**
- Builds directly on proven precedent (AnalyticsService current + HealthService "Follows AnalyticsService pattern al pie de la letra" + item11 impact/PLAN exact copy instructions for read-only observability).
- Analytics already imports/uses BesitoBalance, BesitoTransaction, User, Subscription (lines 15,50,117,152).
- Protects 3 crit + golds by construction (see below).
- Tight: 1 file only for impl slice (services/analytics_service.py); tests/docs later per hardener.
- No conflict with old auditoria (which wanted new models + side-effect logging + user-facing history); this is Custodio reporting only, using existing earned/spent/source data.

**Risk level rationale (LOW):** Matches item11 (read-only besito sanity counts in health critical_sanity using same models; 0 impact asserted + verified). Current analytics already does full .all() sum for "total_besitos" (50) + tx limited (152) — new methods are similar aggregates + windowed (better even). No mutation sites touched (all besito updates centralized in besito_service credit/debit + locals in composers post-Items5/6/10).

---

## Files/Consumers Map (EVERY consumer + direct Besito* queries; exhaustive from greps + reads)

**AnalyticsService call sites (prod + test):**
- handlers/analytics_handlers.py:32-34: `with get_service(AnalyticsService) as svc: stats = svc.get_dashboard_stats()` (show_stats for /stats Command; is_admin guard + Lucien + try/except)
- handlers/analytics_handlers.py:54-59: `with get_service(AnalyticsService) as svc: ... csv_path = svc.export_users_csv() or export_activity_csv()` (export_data for /export; supports users/activity; file send + logs)
- tests/unit/test_analytics_service.py:15,20,30,44,52,63,70,92: direct `AnalyticsService(db_session)` + calls to get_dashboard_stats / export_* (8 tests; setup inserts BesitoBalance/BesitoTransaction/User/Subscription directly for assertions on keys, total_besitos sum, expiring, new_today, csv contents/paths)
- No other prod consumers: grep for "from services.analytics_service import|AnalyticsService|get_dashboard_stats|export_users_csv|export_activity_csv" returned only above + services/CLAUDE comments + health test mirror note + fix_connection_leaks.py (old script lists "AnalyticsService" for leak cleanup) + scripts/sync_claude.py (name map). bot.py only includes analytics_router (345); no direct svc.
- get_service support: generic in services/__init__.py:80-113 (no Analytics explicit in __all__ but class passable; Health added explicitly for Item11 precedent at line 15/48 comment "Item 11 - Observability / Health (read-only best-effort; follows Analytics pattern)").

**Direct BesitoTransaction / BesitoBalance queries in prod code (non-test, excluding besito_service.py owner):**
- services/analytics_service.py:50: `balances = db.query(BesitoBalance).all(); total_besitos = sum(b.balance for b in balances)` (get_dashboard_stats; note py sum, full scan — cited in fases_refactor_testing.md:374 as dupe with besito get_total)
- services/analytics_service.py:117-121: per-user `db.query(BesitoBalance).filter(BesitoBalance.user_id == user.telegram_id).first()` (inside export_users_csv loop; + Subscription lookup)
- services/analytics_service.py:152-155: `db.query(BesitoTransaction).order_by(...desc()).limit(1000).all()` (export_activity_csv)
- services/health_service.py:206: `neg = db.query(BesitoBalance).filter(BesitoBalance.balance < 0).count()` (check_critical_services_sanity)
- services/health_service.py:209-212: `db.query(BesitoTransaction).filter(BesitoTransaction.created_at >= now - timedelta(hours=1)).count()` (recent_tx_vol)
- scripts/reset_trivia.py:38-42: `session.query(BesitoTransaction).filter( ... source == TransactionSource.TRIVIA, created_at >= today )` (cleanup only; not runtime stats path)
- (besito_service.py owner, for ref: 43 get_or_create Balance query, 229-244 history/tx-by-source, 254 get_top_users order balance, 259 total .all() sum — expected as domain owner; get_total_besitos_in_circulation 256-260)

**Other direct Besito* (tests only, expected for gold fixtures/asserts/golds; not prod risk):**
- Dozens in tests/integration/test_invariants.py (I1-3 setup + asserts on earned/spent/balance), test_cross_service_atomicity.py (tx counts by source post credit, "REACTION" vs "MISSION"), test_besito_service.py (credit/debit tx creation/assert, race queries), test_analytics_service.py (setup), broadcast_*.py, story_service tests, store tests, daily tests, reaction flows, etc. (all use explicit User/BesitoBalance keyed by .telegram_id per ID contract in conftest + phases docs).
- No prod handlers direct import/query of Besito* (per CLAUDE rules: handlers 1 svc only; verified grep).

**Consumers of Besito models/services more broadly (for risk context):**
- BesitoService (owner): credit/debit (update earned/spent + insert Tx with source/type), get_balance_*, history, get_top_users (balance order, NOT earned), get_total (py sum).
- Composers (post hardening): locals on-demand inside credit sites only (reward _deliver, broadcast reactions, game play_*/streaks, daily claim, store debits post-Item10); + obs listeners "MUST NOT credit/debit" (narrative, rewards, broadcast, game, store).
- Health/Analytics (read-only aggregates/sanity).
- Tests + reset script + old fix script.
- No other services hold direct BesitoService (post Items5/6/10 unification).

**No impact areas (0 files mutated outside slice scope):** models/ (no alembic), besito_service.py or credit paths, story/advance/_grant, channel/approve/pending/expire, VIP grant/revoke, store purchase outer logic (only future read stats), missions deliver, broadcast/game/daily/reward (except future stats), middlewares, bot.py on_startup (no new wiring this slice), keyboards, voice (no new renders), handlers except future analytics extension, EventBus (0 emit change).

**Approx lines for touched (services/analytics_service.py only):** Current file ~190 LOC. New: 3 methods (~20-30 LOC each if slim) + 2-4 internal helpers (~10-15 ea) + docstrings + logging + best-effort wrappers + arch comment block (like health 313-318) + possible `from sqlalchemy import func` for attribution group_by. Total delta est +80-150 lines. All <=50 per func via helpers (copy health checks + analytics exports split).

---

## Risks (categorized HIGH/MED/LOW; esp to atomicity/get_service/3 crit)

**To 3 critical systems (MUST 0 behavior/atomicity impact per task + CLAUDE/hardener):**
- **Gamification (besitos credits/reactions/daily/missions — HIGHEST priority):** LOW / 0. New methods are pure SELECT aggregates on existing Balance (earned/spent populated only by besito.credit/debit) + Tx (sources from all credit/debit sites incl REACTION/DAILY_GIFT/MISSION/PURCHASE/GAME/etc). 0 calls to credit_besitos/debit_besitos (even local), 0 change to balance += or total_earned/spent updates, 0 tx insert, 0 EventBus from here. Current analytics already reads balances for "total_besitos" dashboard (50) + health reads neg/recent_tx — this extends the same read surface. Windows prevent perf on large history. Re-runs of golds (invariants + cross + reaction_chains + daily_atomic + besito unit) protect. "0 risk to gamif credits, reaction_mission_flow, daily atomic, partial failure contracts."
- **Narrative (progress/archetypes/FSM/quiz/achievements):** LOW / 0. No touch on UserStory* or story_service (may join User for top_earners usernames best-effort; Subscription optional overlay also read-only). Narrative uses besito debits for node costs + credits for achievements (via MISSION source in _grant); reads here observe only. 0 risk to advance_to_node, quiz, FSM restore.
- **Channels-VIP (pending/approve/expire/bans/subs/grant/revoke):** LOW / 0. Optional Subscription/User overlay in methods (best-effort, like current analytics export_users which already queries Subscription per-user + VIP status). 0 touch on channel_service grant/pending logic, VIPService, expire cron, free_entry ritual. Health already counts active/expiring subs + pending via publics; this is economy overlay only.

**To existing gold contracts (test_invariants I2/I3 balance=earned-spent + monotonic; cross_service_atomicity "credit survives"; besito unit; analytics tests):**
- LOW. Invariants I2/I3 (from test_invariants.py:80-81 docstring "Fundamental economic invariants: balance never negative, accounting identity holds, counters are monotonic."; I1 neg, I2 identity balance==earned-spent, I3 earned/spent only increase via credit/debit paths) are maintained exclusively in besito_service credit (127: total_earned +=; 195: total_spent +=) + debit. New reads (top_earners on total_earned, overview earned/spent sums, attribution on Tx amounts for CREDITs) observe current state; adding no writers = 0 breakage risk. Cross atomicity gold (test_cross_service_atomicity.py: "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + patch schedule_emit + DESIRED + TestSession + strict re-query tx by source + balance delta asserts + 777 + gather + try/finally) covers reaction credit + mission deliver partials; 0 change to any credit path or listeners here. Besito unit (test_besito_service.py: covers get_top_users on balance, get_total, tx by source, credit/debit that set earned/spent/sources) will still hold (new analytics reads are orthogonal). Analytics unit (current 8 tests on dashboard keys/total_besitos/exports using direct inserts) will be extended but existing paths (py sum balances, tx limit queries) untouched by new methods. Note potential future consistency (current dashboard total vs overview circulation; old dupe noted in fases_refactor_testing.md:374 "Duplicación total besitos circulación: besito py sum(all) vs analytics direct query") — but best-effort + read-only, no behavior change required this slice.
- get_service/EventBus: 0 impact (no new consumers this slice; future handlers will follow exactly 1 svc + is_admin precedent from analytics_handlers:32/54 + health). EventBus 0 emission (this is reporting, not award).

**Other (MED/LOW):**
- Perf: MED mitigated (windows default 30d bound queries; current already does full .all() sum + limit 1000 tx; use indexes on created_at/user_id/source per models; best-effort degraded on large windows).
- Dupe queries: LOW (existing pattern; analytics/health bypass BesitoService for aggregates per design for speed/direct; noted in docs but accepted).
- Empty/degraded/edge windows (None/0/large): LOW (best-effort like health; return partials e.g. {"status":"degraded", ...}).
- No new deps; uses existing sqlalchemy (func for group already pattern in codebase? health uses text).
- Logging/LOC/naming: LOW (copy exact "analytics_service | get_economy_overview | window_days=30 | earned=... circulation=..."; <=50 via helpers; verb+ctx+res).

**HIGH risks: None identified under tight scope.**

---

## Recommendations for impl (tight scope for executor; gold patterns to copy)

**Tight scope (per task + hardener "0/0/0" + item11 precedent):** ONLY edit services/analytics_service.py (methods + internal helpers). Add at end of class (after export_activity_csv). Include full arch comment block modeled on health_service.py:313-318 ("# Slice 1 economy stats expansion / read-only best-effort... Analytics home per approved plan (windows); 0 impact on 3 crit + atomicity/EventBus/get_service contracts."). No other files (handlers later; no voice; no __init__ exports needed beyond get_service generic; no plan doc edits here). Est 1 file, +80-150 lines. Safe point: after methods impl + ruff, before tests.

**Gold patterns to copy al pie de la letra (from Analytics current + Health Item11 + item11 impact/PLAN):**
- Lifecycle exact: __init__(self, db: Session = None): self.db=...; self._owns_session = db is None; _get_db(self) -> Session (create SessionLocal if None); close(self) (if owns and db: close; db=None).
- Read-only best-effort: every new method wrapped try: db=...; compute; logger.info(...); return dict/list except Exception as e: logger.warning(f"analytics_service | <meth> | ... error={str(e)[:80]}"); return {"status":"degraded", "error":...} or partial/empty. Never raise to Custodio caller.
- Logging mandatory structured: f"analytics_service | get_economy_overview | window_days={window_days} | earned=... spent=... circulation=..." (user_id=0 convention for non-user ops, like health "user_id=0" + terminal health_check). Every important action.
- <=50 LOC: extract internal e.g. def _get_window_start(self, window_days: int | None) -> datetime | None: ... (or inline slim); def _compute_source_attribution(...) -> dict: group logic. Verb+context+result names.
- Direct models + func for aggregates (already imports Besito* + datetime/timedelta/UTC; add `from sqlalchemy import func` if group_by needed for attribution; use .filter( (created_at >= ...) if window ).group_by(BesitoTransaction.source).with_entities( source, func.sum(...).label('sum'), func.count().label('cnt') ) then py % calc.
- Window handling: `if window_days is not None: since = datetime.now(UTC) - timedelta(days=window_days); q = q.filter(BesitoTransaction.created_at >= since)` (None or omitted = full or default 30 per sig).
- For overview: earned/spent from sum(BesitoBalance.total_earned) etc over window? or from Tx CREDIT/DEBIT sums in window (for "flow" vs stock); circulation = current sum balances (or windowed?); velocity proxies e.g. tx_count / days or earned_per_day (best-effort per task).
- For attribution: filter type==CREDIT (or amount>0), group source, sum amount (note amounts positive for credit), count, compute pct = (sum_i / grand) *100. Dict keyed by source.value.
- For top_earners: q = db.query(BesitoBalance).order_by(desc(BesitoBalance.total_earned)).limit(limit); optionally join User on user_id==telegram_id for username (left outer, best effort; include "username": u.username if u else None or separate lookup). Return list[dict] with "user_id", "earned", "spent", "net" (earned-spent?), "current_balance"?, "rank".
- Best-effort degraded: e.g. overview always returns dict with keys even on partial fail.
- Arch comment + "Item/Slice" traceability (like health "Item 11 / observability health / arch-enforcer").
- Copy from current analytics: export patterns have try/except around tempfile/CSV + logger.error; dashboard no try (but new methods add for best-effort).
- Future-proof (for next slices): comment "Handlers will use: with get_service(AnalyticsService) as svc: ... + is_admin (see analytics_handlers.py:32 precedent + health)".
- No mutation comments in new code.

**Also copy from item11 impact/PLAN verbatim phrasing for 0-impact sections in future PLAN.**

---

## Test surface

**Extend (new coverage for Slice 1):**
- tests/unit/test_analytics_service.py (add Test* for new methods; mirror existing: test_get_economy_overview_keys/default_window, test_..._with_window_filter, test_source_attribution_credits_only_pct, test_top_earners_order_limit_join_username, test_..._best_effort_degraded_on_error (patch query), test_..._empty_data, logging format asserts if caplog; use explicit BesitoBalance + Tx inserts with varied sources/dates/amounts; import_inside or direct).

**Must re-run (golds + targeted to protect contracts):**
- tests/integration/test_invariants.py (full TestBesitoBalanceInvariants I1-I3; uses TestSession + explicit credit/debit that maintain identity/monotonic; re-query post to verify balance==earned-spent etc.)
- tests/integration/test_cross_service_atomicity.py (full: happy + partials + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + patch schedule_emit + DESIRED CONTRACT + TestSession/file + strict tx source/amount asserts + 777 TG + gather return_exceptions + try/finally closes; -k "cross_service_atomicity or TestCrossServiceAtomicity")
- tests/unit/test_besito_service.py (get_top_users, get_total, tx history by source, credit/debit that populate earned/spent/sources used by new analytics reads)
- tests/unit/test_analytics_service.py (existing 8 + new)
- tests/handlers/test_analytics_handlers.py (smoke; current is health-focused with xfail mocks documented non-reg; precedent for future economy handler slices)
- Broader smoke: pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "besitos or atomicity or invariants or reaction_mission or daily or TestAnalytics or analytics or cross_service or TestCrossServiceAtomicity or TestBesitoBalanceInvariants or besito or gamif" tests/ (targeted from item11/29 PLAN + golds)
- Non-pytest: ruff + format --check on analytics_service.py; bot smoke `python -c "import bot; from services.analytics_service import AnalyticsService; print('ok')"`; manual existing /stats /export (admin); python -c exercise new methods with sample db if possible; greps post (0 writes in analytics_service, no credit calls, "analytics_service |" logs, arch comment "Slice 1").

**Pre-existing tolerated (non-attrib to this):** daily concurrent flakes (doc non-reg per prior), N806 in golds (tol + doc), xfail handler mocks (per Item11 precedent).

---

## Handoff notes

**Ready for:** gsd-planner (tight 4-6 phases: prep/GSD baseline + gold copy confirm + greps current queries/LOC/logging; impl 3 methods+helpers in analytics_service + arch comment; ruff; unit tests extend; re-runs golds + broader per list + self-check PASSED; then arch-enforcer (PASS WITH NOTES 0 crit target) + test-guardian ("suite protege adecuadamente") + tests green + explicit documentador launch at close for .planning/HARDENING_ROADMAP.md update (What Has Been Done per slice with outcomes/verifs, What Missing/roadmap refresh, Metrics, BATCH/pool notes + verbatim phrase) + agent-memory/documentador/ + MEMORY.md pointer). Or direct hardener 6-agent if following current standard.

**Delivery:** Slice 1 only (methods in Analytics). Later slices: handlers (add Custodio cmds/cbs for new methods via get_service exactly 1 + is_admin + Lucien render copy analytics_dashboard style), voice, menu, tests handler, docs.

**0-impact guarantees (verbatim for PLAN):** "This is pure reporting; 0 calls to credit/debit; 0 EventBus emission change." "0 behavior/0 atomicity/0 other/0 prod chg (UI/behavior identical; golds re-runs protect)." "Analytics home, read-only, windows per approved plan."

**Suggested verification (for PLAN/executor/arch/test-guardian):** Golds with exact flags + "suite protege"; arch grep/inspect (0 crit, logging format, LOC<=50 via inspect.getsourcelines, 0 bare writes, arch comment, patterns copied); bot smoke; manual stats consistency (current total vs new overview); greps for "Slice 1" / "economy stats" / "analytics_service |"; ruff clean. Cite this impact report + task + item11 precedent.

**Files/paths absolute (key for handoff):**
- /home/ubuntu/repos/lucienbot/services/analytics_service.py (target; current queries at 50/117/152; pattern 20-38)
- /home/ubuntu/repos/lucienbot/handlers/analytics_handlers.py (consumers 32/54)
- /home/ubuntu/repos/lucienbot/services/health_service.py (pattern source 5/202-245/313-318)
- /home/ubuntu/repos/lucienbot/services/besito_service.py (owner 256-260 total, 251-254 top, 127/195 earned/spent)
- /home/ubuntu/repos/lucienbot/tests/integration/test_invariants.py:78 (I1-I3), 97+ (impl)
- /home/ubuntu/repos/lucienbot/tests/integration/test_cross_service_atomicity.py:1 (gold doc + "credit survives...")
- /home/ubuntu/repos/lucienbot/.claude/agent-memory/impact-analyzer/item11-observability-health.md (template)
- /home/ubuntu/repos/lucienbot/.planning/phases/29-observability-health/PLAN.md (gold instructions)
- /home/ubuntu/repos/lucienbot/.claude/agent-memory/impact-analyzer/slice1-economy-stats-analytics-extension.md (this report, to be written)
- .planning/HARDENING_ROADMAP.md (update via documentador post)

**Next after this:** Persist this report to agent-memory (Write + update MEMORY.md index) + GSD log close. Then user/ or orchestrator delegates to planner/executor per hardener.

**Self-check for this analysis:** Exhaustive (multi-grep strategies + glob exclude tests + full reads of core + prior impacts + planning + models + golds + bot/handlers/services); verified no plan doc; 3 crit + golds + consumers + direct queries fully mapped with line cites; 0 edits; follows persona/CLAUDE (short where possible but exhaustive per task "Be exhaustive"); references approved architecture from task + sources.

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

(End of impact report. Ready for planner.)
