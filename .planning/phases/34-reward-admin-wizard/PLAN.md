# PLAN: Refactor long functions in reward_admin_handlers.py to <=50 LOC + ensure exactly 1 service call per handler (RewardService via get_service) (Item 2/34 / second of new pool of 4)

**Type:** gsd-planner output (for gsd-executor + hardener seq: arch-enforcer + test-guardian + documentador at pool close)  
**Date:** 2026-06-26  
**Focus:** Tight, conservative, phased refactor of `handlers/reward_admin_handlers.py` (long wizard flows + inline UI/biz calc in show_package_selection, show_tariff_selection, show_reward_confirmation, show_pkg_confirmation_from_reward, confirm_create_pkg_from_reward, confirm_create_reward, list_rewards, reward_admin_detail, delete flows + process_* steps + direct multi-service usage: PackageService via get_service in 2 places, bare VIPService() in tariff display + confirm, RewardService in create/list/detail paths). Ensure **every handler entrypoint calls exactly 1 service** (RewardService via standardized `with get_service(RewardService) as reward_service:` context + get_service lifecycle). Extract pure helpers (verb+context+result; stateless, no side-effects, importable, unit-testable; "Función pura...") for UI/wizard formatting and builders (e.g. `build_reward_confirm_text_and_keyboard`, `build_package_selection_text_and_buttons`, `build_tariff_selection_buttons`, `build_pkg_confirmation_text_and_keyboard`, `compute_reward_type_text`, `build_reward_list_entry_and_button`, `build_reward_detail_text_and_keyboard`, `build_reward_delete_confirm_keyboard` etc.) to bring all functions <=50 LOC source. Minimal support ONLY in `services/reward_service.py` (thin delegates for cross: `get_available_packages_for_rewards`, `get_all_tariffs`, `get_tariff`, and thin orchestration `create_package_for_reward_wizard` so handler boundary = exactly RewardService only; + 1-line delegates + arch/"item34 / arch-enforcer long-funcs note addressed. Precedent item7/8/9" comments). Create/update ONLY `tests/handlers/test_reward_admin_handlers.py` (new if absent; add `TestRewardAdminPureHelpers` class with 8-12+ import-inside pure unit tests covering UI strings, keyboards, summaries, list entries, empty/edge cases; port any direct other-svc patches if found). **0 other handlers touched** (mission_admin, store_admin, reward_user etc. untouched). **0 behavior change in reward CRUD/create/deliver** (create_reward_besitos/package/vip, get_*, update, soft-delete, deliver paths, claim, atomicity untouched). **0 delivery/gamif credit/narrative impact** (admin config only; orthogonal to user claim/credit). UI/render identical 1:1 (Lucien 3rd person, exact wizard "Paso X de 5", "Resumen de la recompensa", package lines, tariff lines, "Crear esta recompensa?", list "✅/❌ name (type)", detail content, buttons, backs to "admin_missions"/"list_rewards", truncation, empty states). 3 critical systems (gamif, narrative, channel/VIP) always in mind (this flow is admin reward config read+mutate; orthogonal to credit/increment/deliver/claim; re-runs protect indirectly). GSD pre-log discipline on `.planning/quick/gsd-reward-admin-wizard.log` before every edit/gate/verif. Follow structure/patrones/snippets **al pie de la letra** from successful precedents (25-reward-handlers-1service-loc, 26-store-admin-long-funcs, 27-mission-admin-long-funcs + their gsd logs + SUMMARIES + handoffs). Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. "Item 2/34 closed. Second of new pool of 4. Ready for arch-enforcer + test-guardian + documentador + Item 3".

**Input principal (source of truth):** 
- Complete impact-analyzer report (if present in .grok or .claude/agent-memory for this item; otherwise this PLAN + HARDENING_ROADMAP sec5 "Proposed Next #2" + initial bloat clusters + Item7/8/9 patterns are authoritative).
- `.planning/HARDENING_ROADMAP.md` (sec5 Proposed Next #2, initial bloat, Item7/8/9 patterns, pool phrase, metrics, 3 crit).
- Precedents + golds: `.planning/phases/25-reward-handlers-1service-loc/PLAN.md` + SUMMARY + gsd log (first-of-pool 1-service + pure helpers + ports + LOC inspect + self-check + "first of new pool of 4"); `.planning/phases/26-store-admin-long-funcs/PLAN.md` + SUMMARY + gsd (second-of-pool long funcs wizard + delegates + puros + Test*PureHelpers + UI 1:1 + 0 beh); `.planning/phases/27-mission-admin-long-funcs/PLAN.md` + SUMMARY + gsd (first-of-pool long admin + delegates for cross-reward + many puros + ports of ~12 + TestMissionAdminPureHelpers + arch PASS W NOTES 0 crit + testg "suite protege" + self-check + pool phrase); 20-reward-gamif PLAN + item2 gsd (delegate + pure + 1-line + port + helper tests + LOC + self-check); 24 SUMMARY for BATCH language; current source (reward_admin_handlers.py with multi-svc + bare VIP + long show/confirm/process flows; reward_service.py with pure get_reward_emoji + delegate + no cross delegates for pkgs/tariffs yet); CLAUDE.md (root + handlers + services + models), rules.md (≤50 LOC, verb+context+result, logging "módulo | acción | user_id | resultado", exactly 1 service per handler entrypoint), architecture.md (handlers→services→models), decisions.md (hardener adoption), AGENTS.md, services/missions/CLAUDE.md + services/rewards context if any, models/CLAUDE.md (rels safe), handlers/CLAUDE.md (1svc + puros pattern from Items 7-9).
- Current reward_admin_handlers.py (full wizard + package sub-wizard + bare VIP + multi get_service + long funcs); reward_service.py (current methods + get_reward_emoji pattern to copy for new delegates); package_service.py (get_available_packages_for_rewards exists); vip_service.py (get_all_tariffs/get_tariff exist); absence of tests/handlers/test_reward_admin_handlers.py (confirmed via grep; will create new with puros tests).

**GSD enforcement:** Executor MUST prefix **every** modification / pre-gate / verification / ruff / pytest / grep / smoke / self-check / summary with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-reward-admin-wizard.log` (cross-ref impact if present). Use identical discipline, entry style, wc -l tracking, "pre-xxx <file> (F<N> <short motive>) - <desc + refs DoD + patrones copiados al pie de la letra>", and self-check structure as gsd-reward-handlers-1service-loc.log / gsd-store-admin-long-funcs.log / gsd-mission-admin-long-funcs.log (40-800+ entries, phases + SAFE POINT + FINAL self-check PASSED + POOL/BATCH note). No edits (even to PLAN/log beyond appends) without pre-log. Planner will do INIT + pre-write.

---

## 1. Alcance preciso (In / Out explícito + archivos exactos)

### En esta entrega (scope "tight" per precedents + "no creep" + 0/0/0):
- **handlers/reward_admin_handlers.py** (core): Ensure/keep **exactly `with get_service(RewardService) as reward_service:`** (1 call only per entrypoint/handler, including all message FSM steps and cb steps for reward wizard, package sub-wizard, tariff select, list, detail, toggle, delete). Remove bare `VIPService()` instantiations (show_tariff_selection, show_reward_confirmation) and direct `from services.vip_service import VIPService`; remove direct `from services.package_service import PackageService` (or keep only if type annotation absolutely required, no instantiation/use); replace all cross calls with reward_service delegates (get_available_packages_for_rewards, get_all_tariffs, get_tariff, and create_package_for_reward_wizard for the sub-create flow). Extract 6-10+ pure helpers to slim long flows (show_package_selection, show_tariff_selection, show_reward_confirmation, show_pkg_confirmation_from_reward, confirm_create_*, list_rewards, reward_admin_detail, delete flows, wizard step builders). Recommended extracts (copy logic 1:1 for identical render; verb+context+result; pure = no with, no await, no logger, no FSM/state, no DB):
  - `build_reward_confirm_text_and_keyboard(data: dict, pkg=None, tariff=None) -> tuple[str, InlineKeyboardMarkup]`
  - `build_package_selection_text_and_buttons(packages: list) -> tuple[str, list[list[InlineKeyboardButton]]]`
  - `build_tariff_selection_buttons(tariffs: list) -> list[list[InlineKeyboardButton]]`
  - `build_pkg_confirmation_text_and_keyboard(data: dict) -> tuple[str, InlineKeyboardMarkup]`
  - `compute_reward_type_text(reward_type, besito_amount=None, pkg=None, tariff=None) -> str`
  - `build_reward_list_entry_and_button(reward) -> tuple[str, list[InlineKeyboardButton]]`
  - `build_reward_detail_text_and_keyboard(reward) -> tuple[str, InlineKeyboardMarkup]`
  - `build_reward_delete_confirm_keyboard(reward_id: int) -> InlineKeyboardMarkup`
  - Possibly small `compute_reward_status_emoji(is_active) -> str`, `build_wizard_step_text(step, title, prompt, example=None) -> str`.
  Keep all other process_* validation (name len, int parses, /skip, file collection) as-is if already small or slim inline. Preserve: is_admin guards (lambdas), FSM states (RewardWizardStates + PackageFromRewardStates), state update_data/get_data/clear/set_state, late imports in tests, callback packing (Reward*Callback, RewardTypeCallback, SelectTariffCallback, RewardSelectPkgCallback), /skip, error paths/answers, cancel cbs to "admin_missions", internal calls (toggle -> detail), Lucien voice 3rd person, exact strings/emojis ("🎁", "💋", "📦", "👑", "Paso X de 5", "Resumen de la recompensa", "Resumen del paquete", "Crear esta recompensa?", "No hay paquetes disponibles...", "No hay tarifas...", list "✅/❌ name (type)", detail bullets, buttons "✅/❌ Activar/Desactivar", "🗑️ Eliminar", "🔙 Volver", "list_rewards"), truncation name[:30], stock display for pkgs (∞/num), empty cases, alerts. Post: verify no function >50 lines (inspect.getsourcelines); all entrypoints 1 svc Reward via get_service; grep 0 "PackageService" active + 0 "VIPService" active in handler. No new direct imports of Package/VIP; no DB; no biz logic (CRUD in svc; calcs/UI in puros or svc). Use delegates for reads and sub-create.
- **services/reward_service.py** (soporte mínimo only):
  - Add thin delegates (passthrough; place near other admin helpers; exact style from item8/9 + arch comments):
    ```python
    def get_available_packages_for_rewards(self) -> list["Package"]:
        """Thin delegate to PackageService.get_available_packages_for_rewards().
        Added for item34: enables reward_admin_handlers package selection in reward wizard to call exactly 1 service (RewardService) per handlers/CLAUDE + arch rules.
        Not core CRUD. 0 behavior change. Precedent item8/9.
        """
        from services.package_service import PackageService
        return PackageService(db=self._get_db()).get_available_packages_for_rewards()

    def get_all_tariffs(self, active_only: bool = True) -> list["Tariff"]:
        """Thin delegate to VIPService.get_all_tariffs(active_only).
        Added for item34: enables reward_admin_handlers tariff selection for VIP rewards to call exactly 1 service (RewardService).
        Not core CRUD. 0 behavior change. Precedent item8/9.
        """
        from services.vip_service import VIPService
        return VIPService(db=self._get_db()).get_all_tariffs(active_only=active_only)

    def get_tariff(self, tariff_id: int) -> "Tariff | None":
        """Thin delegate to VIPService.get_tariff(tariff_id).
        Added for item34: enables reward_admin_handlers tariff lookup in confirm/display.
        Not core CRUD. 0 behavior change. Precedent item8/9.
        """
        from services.vip_service import VIPService
        return VIPService(db=self._get_db()).get_tariff(tariff_id)
    ```
  - Add thin orchestration for package sub-create (so confirm_create_pkg_from_reward entrypoint uses only RewardService):
    ```python
    def create_package_for_reward_wizard(self, name: str, description: str, store_stock: int, reward_stock: int, files: list[dict], created_by: int) -> "Package":
        """Thin orchestration: create package (store_stock=-2) + add files for reward wizard.
        Added for item34: enables reward_admin_handlers package creation sub-wizard to call exactly 1 service (RewardService).
        Not core reward CRUD. 0 behavior change. Precedent pattern for cross in admin wizards.
        """
        from services.package_service import PackageService
        ps = PackageService(db=self._get_db())
        pkg = ps.create_package(name=name, description=description, store_stock=store_stock, reward_stock=reward_stock, created_by=created_by)
        for i, f in enumerate(files or []):
            ps.add_file_to_package(package_id=pkg.id, file_id=f["file_id"], file_type=f["file_type"], file_name=f.get("file_name"), order_index=i)
        return pkg
    ```
  - (If pattern) 1-line instance delegates for the read ones with comment "# Backward-compatible delegate added for Item 34 (arch-enforcer 1-service rule for reward_admin handlers)."
  - Arch comment near delegates: "# Support added for reward_admin_handlers 1-service + pure extract (item34). Arch-enforcer long-funcs + multi-service note addressed. Precedent item7/8/9."
  - 0 changes to: create_reward_*, get_reward/get_all_rewards/get_rewards_by_type, update_reward, delete_reward, deliver_reward + all _deliver_*, try_claim_*, has_mission_*, log_reward_delivery, get_user_reward_history, get_reward_stats, _get_mission_*, close, _init_services, held package/vip, atomicity contracts, event listeners, anything in claim/delivery paths.
- **tests/handlers/test_reward_admin_handlers.py** (create if absent; only its test file):
  - If no prior file: create skeleton with pytestmark unit, imports, make_* fixtures usage if needed, and `TestRewardAdminPureHelpers` class at end (import inside per conv; 8-12+ cases covering pure helpers 1:1: confirm texts with/wo pkg/tariff/desc, package selection buttons/texts (name, file_count, stock ∞/num), tariff buttons (name + days), pkg confirm summary, reward list entry (status + name + type), detail text/keyboard (content, toggle label conditional, delete, back), delete confirm kb, empty/edge (no pkgs, no tariffs, None desc, truncation), reward type text branches).
  - If file existed with direct PackageService/VIPService patches: port them to get_service(RewardService) + mock delegate returns + assert on reward_svc calls (not other); update docstrings "Tests ported to 1-service pattern (get_service(RewardService) only + delegates for packages/tariffs + puros). Arch-enforcer note addressed. Precedent item7/8/9."
  - Keep/add: asserts on edit_text/answer exact phrases matching handler (UI 1:1), state transitions for wizards, cb.answer, empty cases.
  - 0 direct Package/VIP/Reward bare patches left post (only get_service patch on RewardService).
- **GSD + artefacts**: run_terminal append BEFORE every edit/write/gate/verif (to .planning/quick/gsd-reward-admin-wizard.log); track wc -l; specific git add only touched (if committing); ruff/pytest gates with exact flags `-p no:cov --override-ini="addopts="`; self-check PASSED at end with full structure (phases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0 behavior chg in reward CRUD/deliver, 1svc Reward via get_service + delegates for cross, LOC<=50 via inspect, logging, pure helpers tests 8-12+ import-inside, no prod chg)/desviaciones/tests críticos para futuro (reward admin handler test or pure class, reward unit for delegates, cross -k "reward or admin_missions or TestRewardAdmin or TestRewardAdminPureHelpers", bot smoke, ruff+greps+LOC verifiers)/"Item 2/34 closed. Second of new pool of 4. Previous pool of 4 closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en reward_admin_handlers: exactly 1 service + <=50L + no direct Package/VIP + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + documentador (ROADMAP + learnings + agent-memory) + gsd-executor del siguiente item del pool de 4").
- **Verification**: the 3 (or 4) files ruff clean; handler test/pure class 100% pass (behavior identical); critical list re-run (reward unit for delegates + handler/pure tests + broader -k reward|admin_missions|TestRewardAdmin + bot smoke + line counts <=50 post via inspect + outputs match pre via test asserts on strings/emojis/cbs + 0 beh change in create/list/detail/toggle/delete + wizard package subflow + reward select); 0 change to gamif credit or narrative or channel/VIP contracts (re-runs of cross/gamif golds protect indirectly); "admin create is orthogonal to user progress/claim" per precedent. Greps: 0 "PackageService" active + 0 "VIPService" active in handler (except comments); count with get_service(RewardService); delegates present in svc with comments; logging format; UI strings in puros.
- Memory: cross-ref this PLAN + GSD log + HARDENING_ROADMAP + precedents.

**Archivos que se modificarán (exactos, por orden de fases; prefer extend, minimal):**
1. `.planning/quick/gsd-reward-admin-wizard.log` (all phases, pre only via echo; no "edit" of source beyond appends; wc tracked).
2. `services/reward_service.py` (F2: min support -- thin delegates get_available_packages_for_rewards, get_all_tariffs, get_tariff + thin create_package_for_reward_wizard + arch comments + 1-line delegates if pattern; 0 core CRUD).
3. `handlers/reward_admin_handlers.py` (F3: remove direct PackageService import/use + bare VIPService instantiations; all entrypoints use with get_service(RewardService) only; use delegates for pkgs/tariffs/package-create; extract 6-10+ pure helpers; slim all listed long flows + callers to <=50 LOC; ensure/keep exactly 1 svc per entrypoint; add/ensure logs standard; UI render 1:1).
4. `tests/handlers/test_reward_admin_handlers.py` (F4: create if absent; add TestRewardAdminPureHelpers (import inside) + any ports; keep 100% coverage of puros + UI pins; behavior identical).
5. Re-runs/gates/verifs/smokes do not modify (except ruff auto-fixes if any on touched + log appends).

**Fuera explícitamente (nada de scope creep, per "tight" + precedents + "0 otros handlers" + "0 behavior change en reward CRUD/deliver" + "0 atomicity" + "0 docs más allá de lo necesario" + 3 crit protected):**
- **NO** otros handlers (reward_user_handlers.py, mission_admin_handlers.py, store_admin_handlers.py, gamification_admin, promotion_admin, story_admin, channel, vip, common, broadcast, free_channel, etc. — even if they touch rewards or admin_missions backs).
- **NO** package_service.py or vip_service.py (no changes; delegates call them; their methods remain canonical; unit tests unchanged).
- **NO** models (no new props), 0 keyboards/* (no new builders or cb changes), 0 bot.py, 0 handlers/__init__.py, 0 services/__init__.py, 0 utils, 0 lucien_voice, 0 config, 0 middlewares.
- **NO** changes to core RewardService: create_reward_besitos/package/vip, get_reward/get_all/get_by_type, update_reward, delete_reward, deliver_reward + all _deliver_*/claim/log/history/stats/close/held/observers/atomic contracts.
- **NO** change to user mission claim/delivery (increment_and_deliver, deliver_reward) or atomicity golds.
- **NO** new tests outside the reward_admin test file (no service tests for delegates/pures beyond the pure class).
- **NO** edición de CLAUDEs (incl services/missions/CLAUDE.md, services/rewards if any, handlers/CLAUDE.md), decisions.md, AGENTS, ROADMAP, fase_*, docs/, o cualquier .md excepto este PLAN + el log GSD (impact if present + MEMORY by documentador at close).
- **NO** broad "fix all reward flows" or "touch reward_user for parity" or "refactor package/vip".
- **NO** behavior or contract changes (0 impact on reward create values, wizard FSM transitions, package sub-create semantics, UI strings/emojis/buttons/cbs, alerts, empty/error cases; delegates transparent; extracts pure 1:1 move of prior inline).
- 0 impact on 3 critical systems' core contracts (gamif credit/debit/reactions/daily/missions deliver/claim, narrative progress/archetypes/achievements/quiz, channel/VIP grant/revoke/pending/approve/expire/ban/subs; this flow admin reward config only (read+admin-mutate); orthogonal to user claim/credit; re-runs protect indirectly).
- 0 prod chg.

**Comportamiento observable idéntico + reglas:** All text construction, emoji choice, button labels/texts (exact wizard steps, "Resumen...", package "name (N archivos, stock: ∞/X)", tariff "name (D dias)", "Crear esta recompensa?", list "✅/❌ name (type)", detail content + conditional toggle, delete "Estas seguro...", backs, truncation), cb packing, logging format, empty/error cases ("No hay recompensas", "No hay paquetes...", "No hay tarifas...", "Recompensa no encontrada", "Error al..."), wizard FSM steps/transitions (RewardWizardStates + PackageFromRewardStates, /skip, name>=3, amount>=1, stock>=0, file collection until /done, state data name/desc/reward_type/besito_amount/package_id/tariff_id/pkg_*, set waiting_* / selecting_* / confirming / clear), package create inside reward flow (store=-2, reward stock, files), confirm summaries, list/detail formats, navigation (back to admin_missions/list_rewards), are in puros (mechanical 1:1 move of existing inline) or the entry handlers or svc (unchanged CRUD). Delegates are transparent passthroughs. Extraction preserves every string/emoji/branch/cb/data exactly. Handlers call exactly 1 service (RewardService); funciones <=50 LOC post-extract; logging en formato estándar "reward_admin_handlers | <action> | user_id=... | resultado=..." para acciones importantes; get_service context manager; sin lógica de negocio en handlers; sin acceso DB fuera de models; pure helpers (no side effects, importable, fácil unit test, verb+context+result naming). 3 sistemas críticos protegidos (admin config orthogonal; 0 side effects en gamif credit / narrative / VIP-channel; re-runs protect).

**Artefactos:** Este PLAN.md + entradas GSD completas en el log dedicado (pre every) + (si procede en executor) SUMMARY.md posterior (seguir precedente 27/26/25/24). Memory/hand-off apunta desde PLAN + GSD + documentador at close (ROADMAP + agent-memory + MEMORY pointer).

---

## 2. Fases ordenadas (5 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Preparación (GSD log init/confirm, baseline, fixtures/patterns, patrones gold, LOC actual, confirm 1svc + direct cross sites, UI strings for pinning)

**Objective:** Establecer disciplina GSD para el Item (log touched); confirmar baseline (ruff clean + targeted pytest verde pre-cambios); mapear estado actual (multi get_service + bare VIP + long show/confirm/process flows with inline UI/calc + package sub-wizard); inspect LOC on key long funcs; grep for PackageService/VIPService direct + get_service(RewardService) sites + "with get_service" count; confirm fixtures (make_callback, make_fsm_context, make_message); patrones gold (get_service patch + __enter__/__exit__ from item7/8/9 ports + mission_user; real pure via attrs if any; mock_reward_svc delegates for pkgs/tariffs); identificar los helpers a extraer (confirm text+kb, package selection, tariff buttons, pkg confirm, list entry+button, detail text+kb, delete confirm kb, type text) from current inline + precedents; confirmar UI strings exactas para pinning ( "Paso X de 5", "Resumen de la recompensa", "Resumen del paquete", "Crear esta recompensa?", "No hay paquetes disponibles para recompensas", "No hay tarifas VIP configuradas", "💋 Besitos"/"📦 Paquete"/"👑 Acceso VIP", package "name (N archivos, stock: X)", tariff "name (D dias)", list "✅/❌ name (type)", detail bullets, toggle "Activar/Desactivar", "🗑️ Eliminar", "🔙 Volver", "list_rewards", truncation, empty states); GSD pre/post (varias); "F1 safe point - baseline verde + ready for F2; no source changed yet".

**DoD checklist (marcar al completar):**
- [ ] Log `.planning/quick/gsd-reward-admin-wizard.log` exists with planner INIT/pre-write entries (wc >=1) + at least 1 pre-F1 of executor.
- [ ] Baseline: ruff clean on the target files (handler + reward_service + test if exists or will-create).
- [ ] Baseline targeted pytest verde (clean flags exact): `./venv/bin/python -m pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (or reward unit) + any existing admin handler smoke; expect green.
- [ ] Confirm gold patterns via grep/lectura + python inspect: current long flows LOC (show_package_selection, show_tariff_selection, show_reward_confirmation, confirm_create_pkg_from_reward, list_rewards, reward_admin_detail, delete_confirm etc.); grep -n "get_service(RewardService)" + "PackageService" + "VIPService" in handler (map sites); mock patterns in precedent tests (get_service patch + __enter__ + __exit__ asserts, delegate mocks, exact text asserts, state checks); strings for pinning listed above.
- [ ] Read precedents (25/26/27 PLANs + gsd logs + SUMMARIES for ports + helper extract + delegates + Test*PureHelpers + LOC inspect + self-check + pool phrase + BATCH language; 20/item2 for delegate + pure + 1-line + port; HARDENING_ROADMAP sec5 + pool33 close).
- [ ] GSD pre + post entries for baseline (multiple; wc tracked).
- [ ] Safe point F1.

**Archivos:** Log + (lectura/grep/ruff/pytest/inspect; 0 edits to prod/tests in F1 except hygiene ruff if auto).

**Cambios clave (bullets accionables):**
- Ejecutar comandos de baseline (ver "Instrucciones para el gsd-executor" + sección 5).
- Grep/lectura + python -c inspect for LOC + patterns (copy from item7/8/9 F1/F3 gates).
- Actualizar log con "F1 baseline verde + patterns confirmed (multi-svc + bare VIP + long wizard flows; UI strings pinned; previous pool closed per phrase; this is second of new pool of 4) + ready for F2".
- (No code changes in F1 logic.)

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff on touched.
- Targeted pytest (reward related or handler baseline).
- Grep/inspect confirm + GSD entries + "F1 safe point".

**Riesgos + mitigaciones:**
- Riesgo: baseline shows pre-existing unrelated fails (daily concurrent, N806 in golds, warnings) → Mit: document in log (precedent "do not count as regression"); use targeted -k; focus "0 attributable to this Item".
- Riesgo: LOC count varies by comments/docstring → Mit: use inspect.getsourcelines (incl def) as in precedents; trim only if post-extract >50; mechanical extract will drop.
- Bajo: no dedicated test_reward_admin_handlers.py yet → Mit: F4 will create with pure class; ports N/A or minimal.

**Safe point:** Baseline verde + patterns confirmed (multi-svc + bare + long flows + UI pins) + "F1 safe point - ready for reward_service min support (delegates); no source changed yet". Reversible (nada editado en fuentes aún).

---

### Fase 2: Soporte mínimo en RewardService (thin delegates for packages/tariffs + thin create for sub-wizard + arch comments)

**Objective:** Add thin delegates so the handler's reward wizard (package select, tariff select, package create sub-flow, confirm display) can call exactly 1 service (RewardService) without importing/using PackageService or VIPService directly. Add arch comments. This enables (and maintains) the handlers to comply with exactly 1 service at boundary. Ruff + smoke + grep (defs present) + targeted reward/package/vip tests (non-blocking). GSD pre. Safe point.

**DoD checklist:**
- [ ] Thin delegates `get_available_packages_for_rewards`, `get_all_tariffs(active_only=True)`, `get_tariff(tariff_id)` added to `services/reward_service.py` (passthrough via fresh XXXService(db=self._get_db()); docstrings exact "Thin delegate to ... Added for item34: enables reward_admin_handlers ... to call exactly 1 service (RewardService) per handlers/CLAUDE + arch rules. Not core CRUD. 0 behavior change. Precedent item8/9.").
- [ ] Thin orchestration `create_package_for_reward_wizard(name, description, store_stock, reward_stock, files, created_by) -> Package` added (internal PackageService(db); docstring similar; handles create + loop add_file).
- [ ] Arch comment present near delegates or top: "# Support added for reward_admin_handlers 1-service + pure extract (item34). Arch-enforcer long-funcs + multi-service note addressed. Precedent item7/8/9."
- [ ] (If pattern) 1-line instance delegates with "Backward-compatible delegate added for Item 34..." comment.
- [ ] Imports necesarios (Package, Tariff via quotes or from models).
- [ ] Sin cambios de comportamiento: delegados retornan idéntico a direct calls (smoke).
- [ ] Ruff limpio en el archivo.
- [ ] Smoke de import + llamada básica (delegates + create thin) pasa.
- [ ] Grep confirma defs: `grep -n "def get_available_packages_for_rewards\|def get_all_tariffs\|def get_tariff\|def create_package_for_reward_wizard" services/reward_service.py`.
- [ ] GSD pre-edit + pre-gate entries en el log.
- [ ] Safe point.

**Archivos:** `services/reward_service.py`

**Cambios clave (bullets accionables, orden sugerido):**
- Pre-log GSD "pre-edit services/reward_service.py (F2 add min support delegates + create thin + arch comments) - refs DoD F2 + copy exact delegate style from item8/9 PLAN F2 + impact patterns + get_reward_emoji precedent for pure compat if any; read pre done; 0 change to core reward CRUD/deliver/claim/atomic".
- Insert delegates + create thin (after existing admin helpers or near get_all_rewards; use self._get_db() per precedents).
- Add arch comment.
- Post-edit: ruff + smoke + grep.
- GSD "F2 safe point".

**Tests que deben pasar antes de avanzar (gates de F2):**
- Ruff en el archivo.
- Smoke: python -c exercising delegates + create thin (mock or real as safe).
- Grep defs.
- Targeted reward/package/vip unit spot (non-blocking).
- GSD + "F2 safe point".

**Riesgos + mitigaciones:**
- Riesgo bajo: other callers of package/vip direct (reward_admin was one; mission/store use their own delegates or direct per domain) → Mit: delegates internal to reward admin flow; other domains keep legit direct use.
- Riesgo: duplication of read paths → Mit: thin passthrough; no signature change; tests unchanged.
- Ningún test directo de nuevos delegates en svc units (los de handlers los ejercitarán post-port); F4 + re-runs validan.

**Safe point:** Post-ruff + smoke + grep + GSD "F2 safe point - thin delegates + create thin added; arch comments; 0 behavior change in core; only this file touched (reversible)". Handler baseline ready for 1svc enforcement + extract.

---

### Fase 3: Refactor handlers de reward admin (asegurar exactly-1-service + extraer helpers puros para <=50 LOC; UI idéntica; logging; remove direct cross services)

**Objective:** En `reward_admin_handlers.py`, asegurar que todos los entrypoints (cb + message FSM steps for reward wizard, package sub-wizard, tariff, list, detail, toggle, delete) cumplan "exactly 1 service" (RewardService via get_service; convert all; remove bare VIP + direct Package use). Extraer 6-10+ helpers puros (build_* / compute_* verb+context+result; "Función pura...") del cuerpo de las long flows de forma que show_package_selection, show_tariff_selection, show_reward_confirmation, show_pkg_confirmation_from_reward, confirm_create_*, list_rewards, reward_admin_detail, delete flows + callers queden <=50 líneas fuente (ideal <50 estricto post). Preservar exactamente el mismo render (textos, emojis, botones, callbacks, alerts, wizard steps, confirm resúmenes, list "✅/❌", detail content, toggle conditional, backs, truncation, empty). Añadir/estandarizar logging en formato "reward_admin_handlers | <action> | user_id=... | result=..." dentro de los withs post data exitosa. Ruff + inspect LOC + grep 0 PackageService active + 0 VIPService active + 1svc Reward + new defs + GSD. Safe point.

**DoD checklist:**
- [ ] Imports: `from services import get_service`, `from services.reward_service import RewardService`; **0** menciones activas a `PackageService` or `VIPService` (grep ==0 active).
- [ ] All cb/message entrypoints use `with get_service(RewardService) as reward_service:` (incl package sub-wizard confirm, tariff select, confirm display that previously did bare/cross).
- [ ] Package select uses `reward_service.get_available_packages_for_rewards()`; tariff uses `reward_service.get_all_tariffs(...)` / `get_tariff(...)`; package create sub uses `reward_service.create_package_for_reward_wizard(...)`; confirm display uses delegates for enrichment.
- [ ] Helpers puros extraídos: at least the list in Alcance (build_reward_confirm..., build_package_selection..., build_tariff..., build_pkg_confirmation..., compute_reward_type_text, build_reward_list..., build_reward_detail..., build_reward_delete...); lógica copiada 1:1 (sin side effects, sin DB, sin async, sin FSM).
- [ ] Long flows fuente <=50 líneas post-extract (inspect.getsourcelines <=50).
- [ ] Logging estándar presente dentro de los with (post data exitosa).
- [ ] Comportamiento idéntico: mismos textos, botones, callbacks, alerts, wizard steps, empty cases, truncation.
- [ ] GSD pre + gates (ruff, inspect LOC, grep 1svc + 0 cross, smoke import, targeted) verdes.
- [ ] Safe point.

**Archivos:** `handlers/reward_admin_handlers.py`

**Cambios clave (bullets accionables + snippets a copiar al pie de precedentes):**
- Pre-log GSD "pre-edit handlers/reward_admin_handlers.py (F3 ensure 1svc + extract puros) - refs DoD F3 + copy get_service+with from item7/8/9 + delegate usage + pure extract style (insert near section, replace inline, docstring 'Función pura...', inspect LOC, UI 1:1 pins); read pre done".
- Confirm/asegurar imports al inicio (0 cross services active).
- In each long show/confirm: replace inline build with calls to puros; call delegates inside the with.
- Insert puros (near other helpers; verb+context+result; docstring "Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (wizard/list/detail). 1:1 de lógica previamente inline (item34, arch-enforcer).").
- Añadir/asegurar logs estándar dentro de withs post-success.
- Post: ruff + format; inspect LOC <=50 for target funcs; grep 0 cross active + 1svc present + new defs; smoke import.
- UI render 1:1 verified by test pins in F4.

**Tests que deben pasar antes de avanzar:**
- Ruff en el handler.
- Smoke: python -c "from handlers.reward_admin_handlers import ... (all puros + entrypoints if importable); print('ok')"
- Inspect LOC for key long (all <=50).
- Grep: 0 PackageService/VIPService active; get_service(RewardService) present; puros present.
- (Funcionales gateados en F4).

**Riesgos + mitigaciones:**
- Riesgo: UI/render divergence after extract → Mit: extraction is pure copy-paste 1:1; F4 tests pin exact strings/emojis/cbs; keep all consts.
- Riesgo: LOC still 50 by boilerplate → Mit: trim docstring + comment "extracted for <=50 LOC rule (Item 34 / arch-enforcer)", precedente item7/8.
- Riesgo: rel/None cases → Mit: keep guards already present; tests cover edges.

**Safe point:** Post-ruff + LOC<=50 + grep 0 cross + 1svc + GSD "F3 safe point - all entrypoints 1svc Reward via get_service + delegates; puros extracted; UI identical; logging compliant". Handler recompiles; F4 validates observable contract.

---

### Fase 4: Crear/actualizar tests de reward_admin_handlers + agregar tests para helpers puros extraídos

**Objective:** Crear (si ausente) o actualizar `tests/handlers/test_reward_admin_handlers.py` para proteger "exactly 1 service" + pure helpers. Añadir clase `TestRewardAdminPureHelpers` con unit tests puros (import inside; cubrir branches de confirm, package selection, tariff buttons, list entry, detail, delete kb, empty/edges, type text). Sin parches a Package/VIP directos. Ruff + suite verde (comportamiento idéntico). GSD pre. Safe point.

**DoD checklist:**
- [ ] 0 parches directos de PackageService o VIPService en el archivo de tests (solo get_service patch on RewardService + delegate mocks).
- [ ] All tests use `@patch("handlers.reward_admin_handlers.get_service")` + mock_context.__enter__/__exit__ asserts.
- [ ] Setups configure mock_reward_svc delegates (get_available_packages_for_rewards, get_all_tariffs, get_tariff, create_package_for_reward_wizard) to return test data.
- [ ] Docstrings actualizadas: "Tests ported to 1-service pattern (get_service(RewardService) only + delegates for packages/tariffs + puros). Arch-enforcer note addressed. Precedent item7/8/9."
- [ ] Nueva clase `TestRewardAdminPureHelpers` (o equiv) al final: 8-12+ tests (import inside); cover confirm text (with/wo pkg/tariff/desc), package selection (buttons/texts with ∞/num stock, file_count), tariff buttons (name+days), pkg confirm summary, reward list entry (status+name+type, truncation), detail text+kb (content, conditional toggle, delete, back), delete confirm kb, empty cases, reward type text branches, edges.
- [ ] Asserts de texto, llamadas, y parámetros de servicio se mantienen y pasan (idénticos).
- [ ] Ruff limpio.
- [ ] GSD pre + gate: suite verde.
- [ ] Safe point.

**Archivos:** `tests/handlers/test_reward_admin_handlers.py`

**Cambios clave (bullets accionables, copiar al pie de item7/8/9 F4):**
- Pre-log GSD "pre-edit tests/handlers/test_reward_admin_handlers.py (F4 add pure helper tests + ports/creation) - refs DoD F4 + copy from item7/8/9 PLAN F4 (get_service patch, __enter__/__exit__, delegate mocks, docstrings 'ported...', Test*PureHelpers class with import inside, UI 1:1 pins); read pre done".
- Si el archivo no existe: crear skeleton (pytestmark, imports básicos, class TestRewardAdminPureHelpers con los casos).
- Si existe: port setups a get_service(Reward) + delegate mocks; actualizar docstrings; agregar la clase al final.
- Post: ruff; full pytest del archivo (o pure subset); grep residual cross ==0.

**Tests que deben pasar antes de avanzar:**
- `./venv/bin/python -m pytest tests/handlers/test_reward_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (o -k "TestRewardAdminPureHelpers") → verdes (textos/cbs/rows/edges idénticos).
- Ruff.
- Grep 0 cross active.

**Riesgos + mitigaciones:**
- Riesgo: tests que confiaban en mocks de otros servicios fallan por attrs → Mit: configurar delegates explícitamente; 1:1 pins en puros.
- Riesgo: nuevos helper tests fallan por nombre/firma → Mit: nombres confirmados en F3 GSD + sección 4; ajustar conservador.

**Safe point:** Suite verde post-F4 + ruff + GSD "F4 safe point - reward admin tests (new or ported) confirm 1-service + puros; TestRewardAdminPureHelpers added + pass; behavior identical; arch notes addressed".

---

### Fase 5: Re-runs de golds + verificación final de reglas + self-check + handoff (segundo de nuevo pool de 4)

**Objective:** Re-ejecutar golds que protegen paths de rewards (reward unit for delegates + handler/pure tests + broader -k reward|admin_missions|TestRewardAdmin + bot smoke). Verificar reglas (1 service, LOC<=50, logging, puros, 0 cross active). Completar GSD log con self-check PASSED explícito + lista de "tests críticos". Confirmar en self-check/PLAN: "este es el segundo de un nuevo pool de 4"; citar pool phrase. Handoff a arch-enforcer/test-guardian + documentador + gsd-executor del siguiente item. Safe point final.

**DoD checklist:**
- [ ] Re-runs: reward unit targeted (get_all_rewards, get_reward, create_reward_*, delegates if exercised) green; handler/pure tests green; broader `-k "reward or admin_missions or TestRewardAdmin or TestRewardAdminPureHelpers or deliver or TestCross or atomicity" -q --tb=line -p no:cov --override-ini="addopts="` (documentar pre-exist unrelated); bot smoke `python -c "import bot; print('routers incl reward_admin ok')"`.
- [ ] Ruff limpio en los archivos tocados.
- [ ] Verificación de reglas (grep/inspect + en log):
  - `grep -n "PackageService\|VIPService" handlers/reward_admin_handlers.py | grep -v "#\|comment\|NOTE"` → 0 active.
  - `python -c 'import inspect; from handlers.reward_admin_handlers import ...; ... print("LOC:", len(inspect.getsourcelines(fn)[0]))'` → all target <=50.
  - Logging formato "reward_admin_handlers | ..." presente en key paths.
  - get_service(RewardService) + delegates + puros usados + tests added.
  - 1 service rule + <=50 + logging + puros + no biz logic en handler.
- [ ] GSD entries completas para F5 + log final con self-check PASSED + estructura completa (lista fases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0 beh chg, 1svc+delegates+puros, LOC<=50, logging, pure tests, no prod chg)/desviaciones/tests críticos para futuro (reward handler/pure tests, reward unit for delegates, cross reward/admin_missions, atomicity reward paths, bot smoke, ruff+greps+LOC)/"Item 2/34 closed. Second of new pool of 4. Previous pool of 4 closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en reward_admin_handlers: exactly 1 service + <=50L + no direct Package/VIP + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + documentador (update ROADMAP + learnings + agent-memory report + MEMORY pointer) + gsd-executor del siguiente item del pool de 4").
- [ ] Self-check explícito "Self-Check: PASSED".
- [ ] (Opcional recomendado) SUMMARY.md en el dir de la phase con executive + refs al log + comandos de re-verif.
- [ ] Safe point final + criterio de éxito del plan.

**Archivos:** Ninguno nuevo (solo log + opcional SUMMARY; edits ya en F2-F4).

**Cambios clave:** Solo ejecución de comandos + echo al log.

**Tests gates (obligatorios):**
- Re-runs targeted + broader filtrado.
- Ruff.
- Greps + inspect LOC + smoke bot.
- GSD pre cada + "F5 FINAL + self-check PASSED + POOL phrase + handoff".

**Riesgos + mitigaciones:**
- Riesgo: re-runs muestran flakes preexistentes → Mit: documentar; no contar como regression (precedente).
- Ninguno nuevo.

**Safe point final + criterio de éxito:** Todos DoD de F5 + self-check PASSED en log con la nota explícita de "segundo de nuevo pool de 4" + pool phrase + handoff. El plan completo + log GSD son evidencia para el siguiente agente. 0 breakage; UI idéntica; reglas cumplidas; 3 sistemas críticos protegidos (admin config orthogonal; re-runs protegen).

---

## 3. Estrategia de tests general (creación + puros + re-runs)

**Creación/ports en test_reward_admin_handlers (F4):**
- Seguir exactamente el patrón de `tests/handlers/test_mission_admin_handlers.py` / `test_store_admin_handlers.py` (item9/8 F4): @patch("handlers.reward_admin_handlers.get_service"), mock_get_service.return_value.__enter__.return_value = mock_instance, asserts en __exit__.assert_called, setups configure mock_reward_svc delegates (get_available..., get_all_tariffs, get_tariff, create_package...) to return lists/objs, calls asserts on reward_svc only (no Package/VIP), docstrings "ported to 1-service... Arch-enforcer note addressed".
- Si el archivo no existe: crear skeleton + la clase TestRewardAdminPureHelpers (import inside per convención del archivo).
- Actualizar/confirmar docstrings de clases a "Tests ported to 1-service pattern (get_service(RewardService) only + delegates for cross + pure UI helpers). Arch-enforcer note addressed. Precedent item7/8/9."

**Nuevos tests para pure helpers (F4):**
- Ubicación: mismo archivo (o nuevo si no existía); mantiene co-localizado.
- Enfoque: unit tests puros (datos de entrada falsos con MagicMock mínimos o simples objetos; import inside test funcs; no @patch on the helpers; no service mocks para los puros mismos).
- Casos mínimos (copiar espíritu de Test*PureHelpers en item7/8/9 + impact pins):
  - build_reward_confirm_text_and_keyboard: with/wo pkg/tariff/desc → "Resumen de la recompensa", "Sin descripcion", "💋 50 besitos", "📦 name", "👑 name", "✅ Crear", "❌ Cancelar".
  - build_package_selection_text_and_buttons: empty → "No hay paquetes..."; with pkgs → buttons contain name, file_count, "stock: ∞"/"stock: X"; "➕ Crear nuevo paquete" + cancel.
  - build_tariff_selection_buttons: list → buttons "name (D dias)"; + cancel.
  - build_pkg_confirmation_text_and_keyboard: summary with name/desc/files/stock.
  - build_reward_list_entry_and_button: status ✅/❌ + name[:30] + (type); cb pack contains id.
  - build_reward_detail_text_and_keyboard: Lucien header, name, desc or "Sin descripcion", type bullets, content, toggle label conditional, delete, back.
  - build_reward_delete_confirm_keyboard: "✅ Si, eliminar", "❌ Cancelar", back to detail.
  - compute_reward_type_text: besitos/pkg/vip branches.
  - Edges: truncation, None, 0/empty.
- Estos tests sirven como "test-guardian" para los puros: cualquier refactor futuro debe pasar estos.

**Re-runs de golds (F5, y spot en F1/F3/F4):**
- Reward unit: `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts="` (create/get/update/delete + delegates if exercised).
- Handler/pure: the reward_admin test file (or pure subset -k "TestRewardAdminPureHelpers or build_ or compute_").
- Cross / reward-admin flows: `-k "reward or admin_missions or TestRewardAdmin or deliver or TestCrossServiceAtomicity or atomicity"`.
- Objetivo: confirmar que el código de render (ahora delegando a puros) produce los mismos textos, botones, alerts, y que los calls a servicio siguen siendo solo RewardService via get_service + delegates.
- Bot smoke para router registration.

**Gates generales por fase / final:**
- Ruff: `./venv/bin/python -m ruff check <file> --fix`; `./venv/bin/python -m ruff format --check <file>`.
- Pytest targeted limpio: siempre con `-p no:cov --override-ini="addopts="`.
- Grep de reglas: 0 cross active en handler; LOCs <=50 via inspect; imports de get_service + delegates + puros presentes; logging formato presente; 1svc + puros + get_service + delegates.
- Smoke bot import.
- Cobertura de logging: manual grep/inspección + inclusión en GSD.

---

## 4. Decisiones de diseño que el executor debe confirmar (o registrar desviación en el primer GSD entry de la fase relevante)

1. **Nombres de los helpers puros extraídos:** `build_reward_confirm_text_and_keyboard`, `build_package_selection_text_and_buttons`, `build_tariff_selection_buttons`, `build_pkg_confirmation_text_and_keyboard`, `compute_reward_type_text`, `build_reward_list_entry_and_button`, `build_reward_detail_text_and_keyboard`, `build_reward_delete_confirm_keyboard` (u equivalentes verb+context+result). Confirmar o elegir alternativa equivalente en primer GSD de F3; documentar.
2. **Delegates en RewardService:** Nombres `get_available_packages_for_rewards`, `get_all_tariffs`, `get_tariff`, `create_package_for_reward_wizard` (thin passthrough/orchestration; docstrings con "Added for item34" + "Precedent item8/9"). 1-line instance delegates si sigue patrón item7.
3. **Logging en los handlers editados:** Agregar/confirmar logs en formato "reward_admin_handlers | <action> | user_id=... | result=..." para key actions (create, list, detail, confirm, toggle, delete, package sub create). Dentro del with post data exitosa.
4. **Patrón de tests para puros:** Ejecutar puros directamente con datos simples/MagicMock (import inside); no @patch en los helpers; handler tests cubren flujo vía real (con mocks de svc). Seguir item7/8/9 F4/F5.
5. **Rel/None cases en confirm/detail:** Mantener guards existentes ("if not pkg", "if not tariff"); tests cubren None paths.
6. **Conteo estricto de ≤50 LOC:** Usar `inspect.getsourcelines(func)[0]` (cuenta def inclusive). Trim docstring + comentario "extracted for <=50 LOC rule (Item 34 / arch-enforcer)" si boilerplate empuja.
7. **Actualización de docstrings de tests:** "ported to 1-service (RewardService) + delegates for cross + puros. Arch-enforcer note addressed. Precedent item7/8/9."
8. **Log file para GSD:** `.planning/quick/gsd-reward-admin-wizard.log`. Cada pre- hace echo con refs a DoD + patrones copiados. wc tracked. Al final self-check + pool phrase + handoff.
9. **Creación de test file si no existe:** Crear `tests/handlers/test_reward_admin_handlers.py` con TestRewardAdminPureHelpers (8-12+). No se cuenta como "nuevo test fuera de scope" porque es el "its test file" para este handler.
10. **Cualquier decisión que difiera:** Registrar en GSD + nota breve. Elegir conservadoramente siguiendo precedentes.

Cualquier decisión que difiera de lo anterior debe registrarse en el GSD log + nota breve.

---

## 5. Criterios de verificación + gates finales + lista de comandos

**Criterios de éxito del Item (medibles, para self-check del executor):**
- Los handlers de reward admin no contienen ninguna referencia activa a PackageService o VIPService (import o uso) — grep activo ==0.
- Usan exclusivamente `get_service(RewardService)` vía context manager (with) + delegates para cross (pkgs/tariffs/package-create); exactamente 1 service por entrypoint.
- Long flows + helpers relevantes <=50 LOC fuente (inspect <=50); puros extraídos (build_* / compute_* verb+context+result) y usados para el render.
- Tests (nuevo o actualizado test_reward_admin_handlers.py) pasan post-F4 (con get_service, delegates, puros, __exit__, nuevos pure tests; textos/calls/alerts/params idénticos).
- Re-runs de golds (reward unit + handler/pure + cross filtrado) pasan sin regressions atribuibles.
- Ruff clean en los archivos modificados.
- Verificaciones de reglas:
  - grep cross activo == 0
  - LOCs <=50 via inspect
  - Logging formato presente en key paths
  - 1 service + delegates + puros + get_service context + no biz logic
  - GSD pre every (counts 5-10+/fase target; wc tracked)
- GSD log completo con pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en futuro" (reward admin test or pure class; reward unit for delegates; cross -k reward|admin_missions|TestRewardAdmin; bot smoke; ruff+greps+LOC) + nota "Item 2/34 closed. Second of new pool of 4. Previous pool of 4 closed with tests passing per user. Ready for arch-enforcer + test-guardian + documentador + siguiente item del pool" + pool phrase.
- Self-check explícito "Self-Check: PASSED".
- Comportamiento de usuario final idéntico (wizards, confirms, lists, details, package subflow, alerts, navegación muestran mismos textos/emojis/botones/cbs; puros no cambian el contrato observable).
- Safe point final documentado; item listo para guardians + siguiente del pool.

**Gates por fase (ver secciones de fases para detalles; siempre GSD pre antes):**
- Pre-edit / pre-gate / pre-verif / pre-ruff / pre-pytest / pre-grep / pre-smoke / pre-final: append al log.
- Post-edit: ruff + targeted pytest (cuando aplique) + smoke + grep/LOC checks + GSD entry.
- Avanzar solo si gate verde (o documentar desviación menor en log).
- F5: re-runs obligatorios + broader smoke filtrado + self-check + pool phrase + handoff.

**Comandos concretos sugeridos (copiar al pie de la letra en ejecución; usar run_terminal_command):**
```
# GSD (siempre pre)
echo "=== $(date -Iseconds) | PHASE N | GSD pre-... <file> (<motivo>) - <desc + refs DoD + patrones copiados al pie de la letra de item7/8/9 PLANs + gsd logs + pool phrase>" >> .planning/quick/gsd-reward-admin-wizard.log
wc -l .planning/quick/gsd-reward-admin-wizard.log

# Ruff
./venv/bin/python -m ruff check handlers/reward_admin_handlers.py services/reward_service.py tests/handlers/test_reward_admin_handlers.py --fix || true
./venv/bin/python -m ruff format --check handlers/reward_admin_handlers.py services/reward_service.py tests/handlers/test_reward_admin_handlers.py || true

# Pytest targeted (siempre con estos flags)
./venv/bin/python -m pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "reward or get_all_rewards or get_reward or create_reward"
./venv/bin/python -m pytest tests/handlers/test_reward_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts=" || true
./venv/bin/python -m pytest -k "reward or admin_missions or TestRewardAdmin or deliver or TestCross or atomicity" -q --tb=line -p no:cov --override-ini="addopts="

# Grep rules + 1svc
grep -n "PackageService\|VIPService" handlers/reward_admin_handlers.py | grep -v "#\|NOTE\|comment" || true
grep -n "get_service(RewardService)\|from services import get_service\|from services.reward_service import RewardService" handlers/reward_admin_handlers.py
grep -n "def get_available_packages_for_rewards\|def get_all_tariffs\|def get_tariff\|def create_package_for_reward_wizard" services/reward_service.py
grep -n "build_reward_confirm_text_and_keyboard\|build_package_selection_text_and_buttons\|build_tariff_selection_buttons\|build_pkg_confirmation_text_and_keyboard\|compute_reward_type_text\|build_reward_list_entry_and_button\|build_reward_detail_text_and_keyboard\|build_reward_delete_confirm_keyboard" handlers/reward_admin_handlers.py

# LOC (inspect gold)
./venv/bin/python -c '
import inspect
from handlers.reward_admin_handlers import show_package_selection, show_tariff_selection, show_reward_confirmation, show_pkg_confirmation_from_reward, confirm_create_pkg_from_reward, confirm_create_reward, list_rewards, reward_admin_detail, delete_reward_confirm
for name, fn in [("show_package_selection", show_package_selection), ("show_tariff_selection", show_tariff_selection), ("show_reward_confirmation", show_reward_confirmation), ("show_pkg_confirmation_from_reward", show_pkg_confirmation_from_reward), ("confirm_create_pkg_from_reward", confirm_create_pkg_from_reward), ("confirm_create_reward", confirm_create_reward), ("list_rewards", list_rewards), ("reward_admin_detail", reward_admin_detail), ("delete_reward_confirm", delete_reward_confirm)]:
    try:
        src = inspect.getsourcelines(fn)[0]
        print(f"{name} LOC: {len(src)}")
    except Exception as e:
        print(name, "error:", e)
'

# Smoke import + delegates + puros
./venv/bin/python -c "
from handlers.reward_admin_handlers import (
    build_reward_confirm_text_and_keyboard,
    build_package_selection_text_and_buttons,
    build_tariff_selection_buttons,
    build_pkg_confirmation_text_and_keyboard,
    compute_reward_type_text,
    build_reward_list_entry_and_button,
    build_reward_detail_text_and_keyboard,
    build_reward_delete_confirm_keyboard,
)
from services.reward_service import RewardService
print('imports + puros ok')
from unittest.mock import MagicMock
from models.models import Package, Tariff
# exercise puros with minimal data
print('puros callable ok')
"

# Bot smoke (router registration)
./venv/bin/python -c "
import bot
print('bot import + routers (incl reward_admin) ok')
"

# Combined critical re-run (F5)
./venv/bin/python -m pytest -k "reward or admin_missions or TestRewardAdmin or TestRewardAdminPureHelpers or deliver or TestCrossServiceAtomicity or atomicity" -q --tb=line -p no:cov --override-ini="addopts="
```

---

## Instrucciones para el gsd-executor

Este PLAN.md ES tu prompt de ejecución. Síguelo al pie de la letra, sin scope creep. El trabajo es para UNA persona (tú) + disciplina GSD total. El flujo debe continuar automáticamente con gsd-executor para este item (y luego los siguientes del pool de 4).

**CONFIRMACIÓN OBLIGATORIA (incluir en tu output final y en el self-check del log):** Este es el segundo de un nuevo pool de 4 (Item 2/34, reward-admin-wizard). El pool anterior de 4 quedó cerrado con tests pasando: ver HARDENING_ROADMAP + pool33 close artifacts + Item 1/34 (remaining user flows) SUMMARY/self-check + pool phrase verbatim. "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

1. **GSD discipline (non-negotiable, como en todas las phases exitosas 25/26/27 + item7/8/9 logs):**
   - ANTES de **cualquier** modificación (search_replace/write/edit en fuentes o log o SUMMARY), antes de ruff, pytest, grep de verif, smoke, o resumen: append al log.
   - Log: `.planning/quick/gsd-reward-admin-wizard.log`.
   - Crea/append al archivo si necesario (planner hará INIT + pre-write; wc tracked; primer entry de executor puede confirmar + wc).
   - Formato de entry (copia estilo **al pie de la letra** de gsd-mission-admin-long-funcs.log / gsd-store-admin-long-funcs.log / gsd-reward-handlers-1service-loc.log):
     ```
     === 2026-06-26Txx:xx:xx+00:00 | PHASE 3 | GSD pre-edit handlers/reward_admin_handlers.py (F3 extract pure helpers + ensure 1svc) - Agregar build_reward_confirm_text_and_keyboard + build_package_selection... + ... (puros, verb+context+result); slim long flows a <=50; mantener with get_service(RewardService) + delegates; refs DoD F3 + copy snippets from item7/8/9 PLAN F2/F3 + gsd logs + UI pins exact; read pre done; patrones de item7/8/9.
     ```
     Luego ejecuta el comando de edit/tool.
   - También pre-gate (pre-pytest, pre-ruff, pre-grep "PackageService|VIPService|get_service", pre-inspect LOC, pre-final-self-check, pre-SUMMARY si produces).
   - Cuenta las entradas; apunta a varias por fase (5-10+ totales por fase como precedentes). Al final del Item el log debe tener el self-check completo + pool phrase + BATCH/POOL note + handoff.
   - Usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE N | ..." >> .planning/quick/gsd-reward-admin-wizard.log` (o printf). Nunca edites sin pre-log. wc -l después de appends clave.

2. **Orden estricto:** Ejecuta Fase 1 → gates → Fase 2 → gates → Fase 3 → gates → Fase 4 → gates → Fase 5 (re-runs + verif final + self-check + POOL phrase + handoff). **No saltes fases ni hagas "todo de una".** Marca DoD mentalmente o en el log al completar cada checklist. Al final de cada fase documenta "F<N> safe point" + "F<N> COMPLETE" en log (como precedentes).

3. **Herramientas y comandos concretos (usa run_terminal_command para estos; copia los de sección 5 + precedents):**
   - GSD logs + wc: `echo "..." >> log; wc -l log`
   - Mkdir (si planner no lo hizo completamente): `mkdir -p .planning/phases/34-reward-admin-wizard`
   - Ruff: `./venv/bin/python -m ruff check <file> --fix`; `./venv/bin/python -m ruff format --check <file>` (apply si "would reformat" como chore 0 logic per precedent).
   - Pytest targeted (siempre con estos flags para exit limpio): `./venv/bin/python -m pytest <path or -k "expr"> -q --tb=line -p no:cov --override-ini="addopts="`.
   - Grep de reglas: `grep -n "PackageService\|VIPService" handlers/reward_admin_handlers.py` (0 active); `grep -n "get_service(RewardService)" ...`; `grep -n "def get_available...|def get_all_tariffs|def get_tariff|def create_package_for_reward_wizard" services/reward_service.py`; `grep -n "build_reward_confirm...|..." handlers/reward_admin_handlers.py`.
   - LOC (siempre inspect): `./venv/bin/python -c 'import inspect; from handlers.reward_admin_handlers import ...; src=inspect.getsourcelines(fn)[0]; print("LOC:", len(src))'`
   - Smokes: `./venv/bin/python -c "from handlers... import ...; from services.reward_service import RewardService; ..."` (delegates + puros); bot `python -c "import bot; print('ok')"`.
   - Evita sleeps; usa comandos directos.
   - Al final: re-ejecuta los combinados + broader smoke filtrado + self-check en log + (opt) write de SUMMARY.

4. **Patrones a copiar (no reinventar; **al pie de la letra** de golds):**
   - Patrón get_service + with + mock en tests + closes __exit__: copia de tests de mission/store admin (item9/8) + item7 (get_service patch, mock_instance + __enter__, delegate mocks, closes to __exit__, calls asserts on primary svc only, docstrings "ported to 1-service... Arch-enforcer note addressed").
   - Extracción de helper puro para LOC + UI idéntica: copia espíritu + snippets de F3 de item7/8/9 (insert pure build_... near section; replace inline with call; docstring "Función pura..."; inspect LOC post; test refresh path green; trim docstring si 51 por boilerplate + comentario "extracted for LOC rule (Item X)").
   - Logging: "módulo | acción | user_id=... | resultado=..." (copiar de item7/8/9 F2/F3).
   - 1-line / min support + delegate comment: de item7/8/9 F1/F2 (pura + delegate 1-line + "Backward-compatible delegate added for Item X (arch-enforcer...)").
   - Thin delegates para cross en admin wizard: copia exacta de item9 (get_all_rewards_for_mission_wizard / get_reward_for...) y item8 (get_available_packages_for_store) + arch comment + "Precedent itemX".
   - GSD entries detalladas: "pre-xxx <file> (F<N> <motivo>) - <desc + refs DoD + patrones copiados al pie de la letra de item7/8/9 PLANs + gsd logs + UI pins>"; wc; style de item9 (79+), item8 (800+), item7 (40+).
   - Safe points + self-check al final del log: estructura de precedentes (lista fases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0, 1svc+delegates+puros, LOC<=50, logging, pure helpers tests, no prod chg)/desviaciones/tests críticos/"Item closed. Ready for ... + arch-enforcer + test-guardian + siguiente item del pool") + pool phrase.
   - Precedentes PLAN/GSD + handoff + pool/batch: 25/26/27 PLANs + SUMMARIES + gsd logs (1svc + puros + ports + LOC + self-check + pool phrase + "Nth of new pool of 4" + "previous pool closed with tests passing per user"); HARDENING_ROADMAP sec5 + pool33 close.
   - VOZ/estilo: handlers hablan vía textos ya existentes (Lucien voice preservado idéntico); no cambiar mensajes de usuario.
   - 3 sistemas críticos: siempre en mente (gamif/missions/rewards como el dominio aquí; narrative cross via events; channel/VIP); este item es admin config (read+mutate) orthogonal a credit/deliver/claim/progress; re-runs de cross protegen.
   - Commands: exact from PLAN sec5 + "Instrucciones" + precedentes.
   - Test class for pure helpers: exact pattern from item7/8/9 F5 (class Test*PureHelpers with 8-12+ tests; import inside test funcs per file convention; no service mocks for pure; placed after last class; asserts exact strings/emojis/cbs/rows from original handler logic + "1:1").
   - 0 export pure en __init__: confirmado (import directo del módulo es suficiente).
   - Any differing: none; registered in GSD + self-check (none).

5. **Decisiones (sección 4 del PLAN):** Al inicio de la fase relevante (primer GSD entry de la fase), registra qué decidiste para "nombre de helper", si trimmaste docstring para LOC, cómo manejaste logging, etc. Si difieres del "preferido", explica brevemente (mantén espíritu tight + gold + 0 behavior + UI idéntica).

6. **Gates y re-runs:**
   - Corre los targeted pytest con los flags exactos de sección 5 ( -p no:cov --override-ini="addopts=" ).
   - Si un unrelated fail preexistente aparece (ej. alembic_heads, daily concurrent UNIQUE, cross daily !success pre patch en priors, N806, warnings), documéntalo en log pero **no lo cuentes como regression del Item** (precedente "Riesgo: baseline shows pre-existing unrelated fails ... document; do not count as regression").
   - Re-run de reward unit + handler/pure + cross filtrado es obligatorio en F5 (y spot en F1/F3/F4).
   - Siempre GSD pre- antes del pytest/ruff/grep grande.
   - Al final F5: re-ejecuta los combinados + broader smoke filtrado + self-check + pool phrase + handoff explícito.

7. **Alcance (recuerda siempre):** Solo edita los archivos listados en "Archivos que se modificarán" + el log GSD + (este PLAN ya está) + opcional SUMMARY.md al final. Si sientes la tentación de "limpiar más handlers", "tocar package/vip para parity", "agregar tests fuera del reward_admin test file", "editar CLAUDEs o decisions", "cambiar behavior de deliver/claim", detente: scope tight para esta entrega (recomendado por precedentes + "second of new pool of 4" + "0 otros handlers" + "0 changes in reward CRUD/deliver" + "0 atomicity"). El analyzer + user prompt + precedents recomiendan empezar tight aquí.

8. **Al final del Item (F5):**
   - Completa el self-check en el log (lista de fases, DoD cumplidos, archivos modificados, tests que pasaron, reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0, 1svc+delegates+puros, LOC<=50 via inspect, logging, pure helpers tests, no prod chg), desviaciones (si las hubo; ej. ruff hygiene como chore 0 logic per precedents), tests críticos para futuro (lista explícita), "Item 2/34 closed. Second of new pool of 4. Previous pool of 4 closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en reward_admin_handlers: exactly 1 service + <=50L + no direct Package/VIP + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + documentador (update ROADMAP + learnings + agent-memory report + MEMORY pointer) + gsd-executor del siguiente item del pool de 4" + pool phrase verbatim).
   - (Opcional pero recomendado) Produce `.planning/phases/34-reward-admin-wizard/SUMMARY.md` con executive + refs al log + comandos de re-verificación (sigue estructura de 27/26/25/24).
   - Confirma en log: "Self-Check: PASSED".
   - El siguiente agente (gsd-executor next item o arch-enforcer/test-guardian/documentador) usará el log + este PLAN + los cambios como fuente de verdad.

9. **Si algo no está claro o difiere del "reporte del impact-analyzer" o user prompt:** El prompt del usuario + este PLAN (basado en discovery + precedentes 25/26/27 + HARDENING_ROADMAP sec5 + pool phrase + código actual + precedents PLANs) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad real de nombre/firma/contrato (e.g. nombre exacto del helper); de lo contrario, elige conservadoramente siguiendo precedentes (item7/8/9 ports + helper extract + LOC inspect + self-check + pool phrase, delegates thin + arch comment, UI 1:1, get_service context + __enter__/__exit__ mocks, real pure via attrs, docstrings "ported...", 1-line/min support + delegate comment, inspect LOC, etc.) y registra la elección en GSD.

**¡Ejecuta con disciplina total. Cierra el Item de forma limpia, segura, medible y con trazabilidad GSD completa. La modernización de los reward admin handlers (1 service Reward-only + delegates para cross + pure helpers para <=50L + tests) queda hecha sin impacto en los 3 sistemas críticos ni en los contratos de CRUD/deliver/claim/atomicity. UI idéntica. Listo para arch-enforcer + test-guardian + documentador + siguiente item del pool de 4 (flujo continúa automáticamente).**

---

**Fin del PLAN para 34-reward-admin-wizard (Item 2/34, second of new pool of 4).**

Referencias rápidas para el executor (actualizar con líneas reales durante ejecución si cambian):
- HARDENING_ROADMAP.md (sec5 Proposed Next #2, pool phrase, Item7/8/9 patterns, metrics, 3 crit).
- Gold precedent for admin long-funcs + 1svc + delegates + puros + ports + Test*PureHelpers + LOC + self-check + pool phrase: 26-store-admin-long-funcs/PLAN.md + gsd + SUMMARY; 27-mission-admin-long-funcs/PLAN.md + gsd + SUMMARY; 25-reward-handlers-1service-loc/PLAN.md + gsd + SUMMARY.
- Delegate pattern (thin + arch comment + "Precedent itemX"): item8 (get_available_packages_for_store), item9 (get_all_rewards_for_mission_wizard / get_reward_for_mission_wizard), item10 (locals).
- Pure extract + UI 1:1 + inspect + import-inside tests: item7/8/9 F3/F4/F5 + Test*PureHelpers classes.
- get_service: services/__init__.py (context manager).
- Current state (pre): handlers/reward_admin_handlers.py (multi get_service + bare VIP + long show/confirm flows); reward_service.py (no cross delegates for pkgs/tariffs yet; has get_reward_emoji pure + delegate pattern to copy); package_service.get_available_packages_for_rewards exists; vip_service.get_all_tariffs/get_tariff exist; no dedicated test_reward_admin_handlers.py (create in F4).
- Pool phrase (verbatim in all artifacts + self-check + handoff): "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."
- Handoff final: "Item 2/34 closed. Second of new pool of 4. Ready for arch-enforcer re-scan (enfocado en reward_admin_handlers: exactly 1 service + <=50L + no direct Package/VIP + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + documentador (ROADMAP + learnings + agent-memory + MEMORY) + gsd-executor del siguiente item del pool de 4."
- Reglas + contexto: CLAUDE.md (root + handlers + services + models), rules.md, architecture.md, decisions.md (hardener adoption), AGENTS.md, services/missions/CLAUDE.md, handlers/CLAUDE.md (1svc + puros pattern from Items 7-9), models/CLAUDE.md.
- Comandos + patrones: sección 5 + "Instrucciones" arriba + item7/8/9 gsd entries exactas.

Listo para gsd-executor. Ejecuta F1 → ... → F5 con GSD pre en cada paso + self-check PASSED + pool phrase + handoff al final. Handoff explícito a arch + testg + documentador + Item 3.

**Hecho con 💋 para Diana (Señorita Kinky) — gsd-planner subagent (Item 2/34, second of new pool of 4, post pool 33 + Item 1/34 close).**
