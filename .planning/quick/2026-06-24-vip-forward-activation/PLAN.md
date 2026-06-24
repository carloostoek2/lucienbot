# PLAN: VIP Forward Activation (admin activates/renews by forwarding candidate message)

**Item:** vip-forward-activation  
**Pool:** VIP-Forward-Activation (1/1 item)  
**Effort:** 5  
**Type:** auto (new feature, hardener-agile tight scope)  
**Date:** 2026-06-24  

---

## Objective

Add admin forward-VIP-activation flow so that admins can identify candidate by forwarding their TG message to the bot, confirm with tariff choice, grant via existing token/redeem (grant_vip_from_tariff), push direct native invite to user, fallback notify admin on contact failure. Manual deep-link flow untouched. Follow all rules.

**In scope (tight):**
- Message handler in vip_handlers.py to detect admin-forwarded user message (support forward_from + forward_origin MessageOriginUser).
- Pure helper functions (verb+context+result, "Función pura...", import-inside) for extract candidate ID/display to keep handler LOC <=50.
- FSM states (dedicated VIPForwardActivationStates) + reuse of tariffs_keyboard(for_selection=True), SelectTariffCallback, confirmation_keyboard for tariff choice + approve.
- Confirm handler does EXACTLY 1 service call (prefer with get_service(VIPService) as svc) to grant_vip_from_tariff; then direct bot.send_message to candidate using returned vip_direct_access msg + vip_access_keyboard; catch blocked send using "bot was blocked by the user" pattern; on fail notify the forwarding admin with manual deep-link info.
- Logging strict f"{__name__} | <accion> | user_id=... | resultado=..."
- Reuse: grant_vip_from_tariff, create_vip_invite_link (internal), tariffs_keyboard, confirmation_keyboard, SelectTariffCallback, vip_direct_access, is_admin, blocked pattern from channel_grant.
- 0 change to manual token/redeem path, 0 mutation to atomic redeem / EVENT_VIP_ACTIVATED contract, 0 impact to gamif/narrative/channels-VIP atomicity.

**Out of scope (locked):**
- NO changes to services/vip_service.py (reuse only), models, bot.py router, keyboards/callback_data, common_handlers (manual flow), reward/fulfillment.
- NO new tariffs UI or tariff selection outside forward flow.
- NO behavior change to existing token gen / redeem / invite creation paths.
- NO new admin menu entry for "forward activate" (detection on forwarded msg from admin is sufficient).
- No direct DB, no multi-svc in handler, no >50 LOC funcs.

**Decision (state):** Use dedicated VIPForwardActivationStates (selecting_tariff, confirming) to keep TokenStates pure for token generation flow. Store target_user_id + tariff_id + display in FSM data. Branching only in forward-specific callbacks.

---

## Context (@refs)

**Mandatory reads (do before ANY edit/gate):**
- `@.planning/quick/2026-06-24-vip-forward-activation-intake.md` (official scope)
- `@.grok/agent-memory/impact-analyzer/vip-forward-activation.md` (source of truth for consumers, risks, affected tests, files map)
- `@CLAUDE.md` (root) — hardener workflow, 6-agent seq + documentador, pool phrase, 3 crit systems (protect channels-VIP + atomicity/EventBus/get_service), exactly 1 svc/handler, <=50 LOC, naming, logging
- `@AGENTS.md` + `@architecture.md` + `@rules.md`
- `@handlers/CLAUDE.md` — 1-service via get_service, hardener pure helpers precedent (Items 7-9/25-27), no biz logic, logging, ports in tests
- `@services/CLAUDE.md` — get_service contract + example, VIPService in table
- `@services/vip/CLAUDE.md` — "siempre via token", no agregar/quitar VIP directo, grant via redeem
- Precedents (copy AL PIE DE LA LETRA):
  - `services/reward_service.py:465` grant_vip_from_tariff usage + _deliver_vip partial handling + _send + _mark + try/exc send
  - `services/channel_grant.py:112` blocked send handling: `if "bot was blocked by the user" in str(e):`
  - `handlers/vip_handlers.py` (current): direct+finally (but prefer get_service for new), FSM TokenStates.selecting_tariff + SelectTariff, tariffs_keyboard(for_selection=True), confirmation_keyboard usage, logging f"{__name__} | ... | user_id=... ", is_admin guards (lambda + explicit), generate flow
  - `services/vip_service.py:482` grant_vip_from_tariff + redeem_token_with_missions + create_vip_invite_link(allow_fallback=False) + partial meta + return (ok, LucienVoice.vip_direct_access(invite), meta)
  - Pure helpers precedent (broadcast_handlers etc): import inside, docstring "Función pura (sin estado ni side-effects).", verb+ctx+res
  - Gold atomic: redeem FOR UPDATE + post EVENT best effort "MUST NOT mutate" in observers
- Recent hardener gsd logs style (if present in .planning/quick): GSD pre timestamp | PHASE | desc + refs DoD + copied patterns (use bat)
- `keyboards/inline_keyboards.py` + `keyboards/callback_data.py`: tariffs_keyboard, confirmation, SelectTariffCallback, vip_access_keyboard
- `utils/lucien_voice.py`: vip_direct_access
- `services/__init__.py`: get_service impl + VIPService export
- Test golds from impact + root: vip/redeem/grant/atomicity/invariants

**Key code to copy verbatim (patterns):**
- grant call + partial + send try/exc + blocked if: from reward_service _deliver_vip_access and channel_grant _send_welcome_after_grant
- tariff select + confirm flow + logging + is_admin + finally close precedent (but convert new to get_service): vip_handlers generate_token_start / generate_token / confirm paths
- Pure extract for candidate: follow build_* style with internal import
- Logging: f"{__name__} | activar_vip_por_reenvio | user_id={admin} | forwarded_user_id=... | resultado=..."
- Voice reuse: LucienVoice.vip_direct_access(invite_link)
- FSM state management + clear on end + answer()

**Gold tests that must stay green (0 attributable regressions):**
- `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or redeem or grant_vip or TestVIPServiceInviteLinks or subscription or atomicity or invariants"`
- Broader: `-k "cross_service_atomicity or reaction or daily_gift or TestCrossServiceAtomicity"`
- Specific: tests/unit/test_vip_service.py (grant, redeem, partial, invite member_limit=1), tests/unit/test_reward_service.py (VIP deliver), integration test_vip_* , test_invariants.py (I4/I5), handler tests, bot import smoke
- Re-runs of key VIP golds after changes (exact cmds below)
- Arch: 0 crit (grep 1 svc in forward paths, LOC via inspect, logging exact, is_admin, no bare Reward etc, 3 crit orthogonal protected)
- No tests for manual deep-link paths broken

**Pre-flight commands (run before touching code):**
See "Test Commands" + "Instrucciones para gsd-executor"

---

## Constraints (NON-NEGOTIABLE)

1. **0 behavior / 0 atomicity change to manual token flow + redeem_token:** Always use grant_vip_from_tariff (which does generate + redeem_with_missions + create_invite). NEVER bypass redeem. EVENT_VIP_ACTIVATED remains post-commit best-effort from inside redeem only. "siempre via token".
2. **Handler rule:** EXACTLY 1 service call per action handler (use `with get_service(VIPService) as svc:` in the grant/activate one; document if direct+finally used). No biz logic (extract puros for candidate extract/display/UI build if needed to <=50 LOC). 1:1 UI reuse where applicable.
3. **LOC + naming + logging:** Every function <=50 lines (verified post-edit with python -c "import inspect; print(inspect.getsourcelines(fn))"). Name: verbo + contexto + resultado. Logging: f"{__name__} | <accion> | user_id=... | resultado=..." on every important action.
4. **Protect 3 critical:** gamif (no touch), narrative (no), channels-VIP (grant only via token path + subs; invite 1-use; no mutation on pending/approve/expire).
5. **Reuse exact:** grant_vip_from_tariff(bot, target_id, tariff_id) -> (ok, msg, meta); create_vip_invite (internal); tariffs_keyboard(..., for_selection=True); SelectTariffCallback; confirmation_keyboard; is_admin; blocked detection pattern; vip_direct_access + vip_access_keyboard for direct send.
6. **Forward detection:** support message.forward_from (legacy) AND message.forward_origin (aiogram3 MessageOriginUser). No crash on hidden users.
7. **Auth + safety:** is_admin on message + all CBs. Validate candidate ID extracted. No hardcode. Fallback on send fail notifies the *forwarding admin* (not candidate).
8. **get_service preference:** Prefer modern `with get_service(VIPService) as ...` for new code (per handlers/CLAUDE + services). If direct needed document why; use finally close like current vip precedent but mark as transitional.
9. **Scope:** Only forward detect + tariff select/confirm + grant + direct send + fallback notify. No docs changes outside PLAN, no ROADMAP unless documentador later.
10. **GSD discipline:** Executor MUST log GSD pre (timestamp | PHASE | ...) BEFORE every edit/gate/ruff/test/write. Copy patterns al pie. Self-check PASSED at end. Use exact test cmds.
11. **Effort 5:** Review will be brutal on contracts, 1-svc, atomic, LOC, logging, no-reg to golds.

---

## Tasks

### Task 1: Add pure extract helpers + FSM states + forward message detection handler in vip_handlers.py

**type:** auto  
**Objective:** Implement detection of admin-forwarded candidate user message (using forward_from | forward_origin), extract ID/display via pure helper, fetch tariffs via exactly 1 svc (get_service or direct+close), display tariffs_keyboard + set forward-specific state + data (target_user_id, display). Logging + is_admin guard. Keep func <=50 LOC.  
**Files:**  
- handlers/vip_handlers.py (only)  

**Actions (exact, copy patterns):**
1. At top (after other imports): add `from aiogram.types import MessageOriginUser` (or lazy), `from services import get_service, VIPService`, `from keyboards.inline_keyboards import ... , vip_access_keyboard` (if not), keep existing.
2. Add new states class after TokenStates:
   ```python
   class VIPForwardActivationStates(StatesGroup):
       selecting_tariff = State()
       confirming = State()
   ```
3. Add pure helpers (before router or after states; copy style from broadcast_handlers + Item7-9 puros):
   ```python
   def extract_forwarded_candidate(message: Message) -> tuple[int | None, str]:
       """Extrae ID y nombre/display del usuario original reenviado para activación VIP. Función pura (sin estado ni side-effects)."""
       from aiogram.types import MessageOriginUser
       if message.forward_from:
           u = message.forward_from
           display = u.full_name or (f"@{u.username}" if getattr(u, "username", None) else str(u.id))
           return u.id, display
       if message.forward_origin and isinstance(message.forward_origin, MessageOriginUser):
           u = message.forward_origin.sender_user
           display = u.full_name or (f"@{u.username}" if getattr(u, "username", None) else str(u.id))
           return u.id, display
       return None, "desconocido"
   ```
   (Keep short; add 1-2 more pure if build_confirm_text needed for <=50.)
4. Add message handler (after other vip msg handlers; use lambda for admin + forward filter):
   ```python
   @router.message(lambda msg: bool(getattr(msg, "forward_from", None) or getattr(msg, "forward_origin", None)) and is_admin(msg.from_user.id))
   async def process_forwarded_vip_candidate(message: Message, state: FSMContext):
       """Procesa reenvío de mensaje de candidato VIP por admin. Extrae + 1 svc para listar tarifas + set state."""
       # pure extract
       candidate_id, display = extract_forwarded_candidate(message)
       if not candidate_id:
           await message.answer("🎩 <b>Lucien:</b>\n\n<i>No pude identificar al visitante del reenvío...</i>", parse_mode="HTML")
           return
       admin_id = message.from_user.id
       logger.info(f"{__name__} | detectar_candidato_vip_reenviado | user_id={admin_id} | forwarded_user_id={candidate_id} | display={display}")
       # 1 service call (prefer get_service)
       tariffs = []
       with get_service(VIPService) as vip_service:  # or direct + finally per current precedent (doc)
           tariffs = vip_service.get_all_tariffs(active_only=True)
       if not tariffs:
           await message.answer(..., reply_markup=...)
           return
       await message.answer(
           f"🎩 <b>Lucien:</b>\n\n<i>Reenvío detectado de {display} (ID {candidate_id}). Seleccione tarifa para activar/renovar VIP...</i>",
           reply_markup=tariffs_keyboard(tariffs, for_selection=True),
           parse_mode="HTML",
       )
       await state.set_state(VIPForwardActivationStates.selecting_tariff)
       await state.update_data(forward_target_user_id=candidate_id, forward_target_display=display)
   ```
5. Guard that this does not interfere with other states (use if state not set or always allow as detection).

**Verification (run after edit, log GSD pre before):**
- `python -c "
import inspect, handlers.vip_handlers as m
print('extract len:', len(inspect.getsourcelines(m.extract_forwarded_candidate)[0]))
print('process len:', len(inspect.getsourcelines(m.process_forwarded_vip_candidate)[0]) if hasattr(m,'process_forwarded_vip_candidate') else 'N/A')
print('get_service import OK' if 'get_service' in open('handlers/vip_handlers.py').read() else 'check')
"`
- `rg -n 'with get_service\(VIPService\)' handlers/vip_handlers.py || echo 'get_service used or documented'`
- `rg -n 'def (extract_forwarded|process_forwarded_vip)' handlers/vip_handlers.py`
- `rg -F '{__name__} | ' handlers/vip_handlers.py | head -3`
- wc -l func <=50 + is_admin + 1 svc in detection path
- ruff check/format on file
- No change to existing token select handler yet

**GSD pre-log (verbatim format before any edit/gate):**
Append to `.planning/quick/gsd-vip-forward-activation.log` :
`$(date -u +%Y-%m-%dT%H:%M:%S+00:00) | PHASE 1 | GSD pre-T1-detection - before edit vip_handlers.py; DoD: pure extract + states + msg handler w/ 1 get_service + logging + <=50 + is_admin; copy: extract style from broadcast puros + forward channel precedent + vip msg handler + get_service from analytics; refs: impact map, intake, handlers/CLAUDE pure+1svc, vip_service grant no touch`

---

### Task 2: Implement tariff select transition + confirmation for forward activation (state machine)

**type:** auto  
**Objective:** On SelectTariffCallback while in VIPForwardActivationStates.selecting_tariff: store tariff, build confirm prompt (reuse or pure build), show confirmation_keyboard("confirm_vip_forward_activation", "cancel"), set confirming state. 0 svc calls in this transition (pure UI). Reuse SelectTariff filter + is_admin. Keep <=50.  
**Files:** handlers/vip_handlers.py  

**Actions (exact):**
1. Add the select tariff handler for forward (after generate_token or parallel):
   ```python
   @router.callback_query(VIPForwardActivationStates.selecting_tariff, SelectTariffCallback.filter(), lambda cb: is_admin(cb.from_user.id))
   async def select_tariff_for_forward_vip(callback: CallbackQuery, state: FSMContext, callback_data: SelectTariffCallback):
       """Selecciona tarifa para forward activation; transiciona a confirm (0 svc)."""
       tariff_id = callback_data.tariff_id
       data = await state.get_data()
       target_id = data.get("forward_target_user_id")
       display = data.get("forward_target_display", str(target_id))
       admin_id = callback.from_user.id
       logger.info(f"{__name__} | seleccionar_tarifa_vip_forward | user_id={admin_id} | tariff_id={tariff_id} | target_user_id={target_id}")
       # fetch tariff name (but since 0 svc here; use previous or minimal - or 1 read ok? keep pure if possible; current pattern allows in select)
       # For strict: can avoid svc by passing name in cb data later, but reuse existing SelectTariff; for now use inline or 1 read if needed but prefer avoid
       await callback.message.edit_text(
           f"🎩 <b>Lucien:</b>\n\n<i>¿Activar/renovar VIP con esta tarifa para {display} (ID {target_id})?</i>\n\nConfirme para proceder vía token interno.",
           reply_markup=confirmation_keyboard("confirm_vip_forward_activation", "cancel_vip_activation"),
           parse_mode="HTML",
       )
       await state.update_data(selected_tariff_id=tariff_id)
       await state.set_state(VIPForwardActivationStates.confirming)
       await callback.answer()
   ```
   (If tariff name fetch needed, use a 2nd svc read? Avoid: fetch name in prior or use tariff_id only. Precedent allows; but to obey 1-per-action, tariff name can be displayed without fetch by storing at select time if we fetch tariffs earlier.)
2. Add cancel handler if needed (simple clear state + back to vip mgmt).
3. Keep existing TokenStates.selecting_tariff untouched.

**Verification:**
- Grep for new state + confirm_keyboard usage
- Inspect LOC of new func <=50
- Grep logging format in new path
- Manual: forward flow reaches confirm without calling grant yet
- ruff + no regression to token gen path (run token tests later)

**GSD pre-log:** `... | PHASE 2 | GSD pre-T2-select-confirm - refs DoD pure UI + no svc here + copy confirmation from tariff create + select filter from generate_token; before any search_replace`

---

### Task 3: Implement confirm + grant (exactly 1 svc) + direct send + blocked fallback notify in vip_handlers

**type:** auto  
**Objective:** On confirm CB in confirming state: EXACTLY 1 svc call to grant_vip_from_tariff using stored target + tariff; if ok attempt bot.send_message to target (with vip_access_keyboard); catch blocked using channel_grant pattern + notify forwarding admin with manual token deep link; handle partial/!ok; clear state; logging; use get_service. Reuse voice.  
**Files:** handlers/vip_handlers.py  

**Actions (exact):**
1. Add the confirm handler (the critical 1-svc one):
   ```python
   @router.callback_query(VIPForwardActivationStates.confirming, F.data == "confirm_vip_forward_activation", lambda cb: is_admin(cb.from_user.id))
   async def confirm_forward_vip_activation(callback: CallbackQuery, state: FSMContext):
       """Confirma y ejecuta grant (EXACTLY 1 service call) + push directo o fallback notify admin."""
       data = await state.get_data()
       target_user_id = data.get("forward_target_user_id")
       tariff_id = data.get("selected_tariff_id")
       admin_id = callback.from_user.id
       logger.info(f"{__name__} | activar_vip_forward_confirm | user_id={admin_id} | target_user_id={target_user_id} | tariff_id={tariff_id}")
       if not target_user_id or not tariff_id:
           await callback.answer("Datos incompletos", show_alert=True)
           await state.clear()
           return
       ok, access_msg, meta = False, "", {}
       with get_service(VIPService) as vip_service:  # EXACTLY 1 service call; prefer get_service
           ok, access_msg, meta = await vip_service.grant_vip_from_tariff(callback.bot, target_user_id, tariff_id)
       if ok:
           sent = False
           try:
               await callback.bot.send_message(
                   chat_id=target_user_id,
                   text=access_msg,
                   reply_markup=vip_access_keyboard(),
                   parse_mode="HTML",
               )
               sent = True
               logger.info(f"{__name__} | notificar_directo_vip_forward | user_id={admin_id} | target={target_user_id} | resultado=enviado")
           except Exception as e:
               if "bot was blocked by the user" in str(e):
                   logger.warning(f"{__name__} | notificar_directo_vip_forward_bloqueado | user_id={admin_id} | target={target_user_id}")
               else:
                   logger.error(f"{__name__} | notificar_directo_vip_forward_error | user_id={admin_id} | target={target_user_id} | error={e}")
               # fallback notify to admin
               token_code = meta.get("token_code")
               deep_link = f"https://t.me/{(await callback.bot.get_me()).username}?start={token_code}" if token_code else "contacta a Lucien para link"
               await callback.message.answer(
                   f"🎩 <b>Lucien:</b>\n\n<i>Activación completada para el visitante, pero no pude notificarle directamente (posible bloqueo).</i>\n\nProporcione enlace manual: <code>{deep_link}</code>",
                   parse_mode="HTML",
               )
           if sent:
               await callback.message.edit_text(
                   "🎩 <b>Lucien:</b>\n\n<i>Activación VIP forward completada. Acceso directo enviado al candidato.</i>",
                   reply_markup=vip_management_keyboard(),
                   parse_mode="HTML",
               )
       else:
           # handle !ok (partial or fail) - show msg to admin; use meta if activated
           await callback.message.edit_text(
               f"🎩 <b>Lucien:</b>\n\n<i>{access_msg}</i>",
               reply_markup=vip_management_keyboard(),
               parse_mode="HTML",
           )
       await state.clear()
       await callback.answer()
   ```
2. Add simple cancel if not present:
   @router.callback_query(..., F.data == "cancel_vip_activation" ...)
       await state.clear()
       ...
3. Ensure imports for F, etc. already there. Use callback.bot for send/get_me.

**Verification (GSD pre before every):**
- `grep -n 'with get_service(VIPService)' handlers/vip_handlers.py` → exactly one in this path (confirm handler)
- `wc -l` + `python -c 'import inspect; ... getsourcelines(confirm...)'` → <=50
- `rg -n 'bot was blocked by the user' handlers/vip_handlers.py`
- `rg -F 'activar_vip_forward_confirm' handlers/vip_handlers.py`
- `rg -F '{__name__} | ' handlers/vip_handlers.py | grep -E 'forward|bloqueado'`
- Full handler file ruff + targeted pytest (no change to token paths)
- Manual simulation: no mutation to redeem (use existing tests)
- 0 bare svc other than the one

**GSD pre-log:** `... | PHASE 3 | GSD pre-T3-grant-send-fallback - before edit confirm handler; copy AL PIE: grant usage from reward:465 + partial meta, blocked-if exact from channel_grant:112, logging + is_admin from vip, get_service, send+keyboard from _send_vip in reward, voice; DoD: exactly 1 svc, <=50, fallback notify admin, redeem contract untouched; refs impact risks, intake, handlers/CLAUDE, vip/CLAUDE`

---

### Task 4 (max 4; optional tight): Verify rules + re-run gold tests + self-check (no new code unless gaps)

**type:** checkpoint  
**Objective:** Post-code: run exact test cmds, ruff, inspect LOC/logging/1svc/grep is_admin/get_service, self-check PASSED + append to log + optional SUMMARY.  
**Files:** (verification only; gsd log + PLAN already)  

**Verification (required):**
- Run full "Test commands" below, capture that VIP golds + atomic + cross re-runs green (0 attributable reg)
- `python -c 'import inspect; from handlers.vip_handlers import *; ... assert all <=50'`
- Grep rules: 0 other svc bare in forward handlers, 1 get_service in activation, logging exact format, verb names, is_admin on all new, pure docstrings
- Self-check in log: "Self-Check: PASSED" + pool note if applicable + handoff
- File existence checks

**GSD pre-log:** Before test/ruff/inspect: timestamp | PHASE 4 | GSD pre-verif ...

---

## Instrucciones para gsd-executor (critical - put verbatim in PLAN)

- Lee PLAN completo antes de editar.
- ANTES de CADA edit/gate/ruff/test: log GSD pre en `.planning/quick/gsd-vip-forward-activation.log` (formato: timestamp | PHASE X | desc + refs DoD + patrones copiados)
- Copia patrones AL PIE DE LA LETRA: grant call from reward, blocked if-str from channel_grant _send_welcome, handler logging from vip_handlers, pure helpers precedent from hardener (Item9 mission etc), redeem contract tests.
- Usa with get_service si encaja; si no, VIPService() + finally close como en vip_handlers actuales (pero documentar).
- Self-check PASSED al final del log + SUMMARY.
- Respeta voice Lucien, 3 crit (canales-VIP atomic protected), "siempre via token".
- No toques redeem logic.
- After code, run exact test cmds from below.

---

## Test commands (exact)

From impact and project gold:
```
pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or redeem or grant_vip or TestVIPServiceInviteLinks or subscription or atomicity or invariants" 
```
Also broader:
```
pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "cross_service_atomicity or reaction or daily_gift or TestCrossServiceAtomicity"
```
Include re-runs of key VIP golds (after each task + final):
- Re-run full VIP unit: `pytest tests/unit/test_vip_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "grant or redeem or invite"`
- Handler related if exist + common redeem path (ensure untouched): `-k "vip or TestVIP or redeem"`
- Bot smoke + import: `python -c "import handlers.vip_handlers; print('import ok')"`
- Ruff: `ruff check handlers/vip_handlers.py && ruff format --check handlers/vip_handlers.py`
- LOC + rules: use python inspect + rg as in verifs
- Re-run atomic/invariants protecting redeem: targeted from cross + invariants

Executor must capture outputs, ensure 0 regressions attributable to forward flow.

---

## Risks + Mitigation

**Critical (channels-VIP + redeem atomicity) - from impact-analyzer:**
- **Redeem atomicity (FOR UPDATE, extension, EVENT):** MUST call grant_vip_from_tariff (wraps redeem_token_with_missions). Risk if bypass: dupe sub, missed EVENT (nurture), broken single-active. Mitigation: reuse grant exactly; no direct redeem; tests cover (will re-run golds + atomic).
- **Invite 1-use + creation fail:** grant uses allow_fallback=False. Returns partial (vip_activated=True, invite=None). Mitigation: follow meta; fallback notify uses token_code if present; admin can still provide manual.
- **Send failure (blocked):** Direct send to candidate independent of grant. Precedent exact: `if "bot was blocked by the user" in str(e):` warning no rollback. Mitigation: catch, log, notify *forwarding admin* (the one who did forward) with deep link/token for manual handoff. No rollback of grant (desired, as in reward partials).
- **Tariff selection / confirm:** Reuse tariffs_keyboard + SelectTariff + confirmation. Risk wrong duration: use existing select flow.
- **Auth / spam:** is_admin guard on message handler + all CBs (lambda + explicit). Validate extracted forward user_id present. No self-forward special case needed beyond display.

**Medium:**
- FSM state pollution / dual use of select: dedicated VIPForwardActivationStates (not reuse TokenStates) to protect existing token gen.
- Handler rule violation: enforced by pure extract + get_service + exactly 1 call in grant confirm handler. No biz in handler (state + send only).
- Direct vs get_service: using get_service for new forward path (modern, per handlers/CLAUDE precedent for recent items).
- Logging/voice: strict format + reuse vip_direct_access; inline Lucien for admin UI consistent with existing vip_handlers.
- Extension/renew: grant already handles (redeem extend logic); forward works for both.
- Nurture/EventBus: activation emits as side effect of redeem; observer best-effort ("MUST NOT mutate").
- No impact on gamif/narrative: confirmed by impact.

**Low:**
- Multi channel VIP: handled internal to redeem.
- ID duality: TG ids from forward_from are BigInt, correct as used elsewhere.
- Rate/Idemp: global middlewares cover CBs and msgs.
- Hidden forward users: return None, error gracefully (no ID leak).

**No impact areas:** gamification atomic, narrative, free channels, besito, store non-VIP products. Manual deep link /start=token + common_handlers redeem 100% untouched.

---

## Success Criteria

- [ ] PLAN.md produced at exact path, scope tight per intake+impact+constraints.
- [ ] 2-4 tasks with DoD, exact files, verifs (incl. wc/rg for LOC<=50, 1-svc grep, logging, is_admin).
- [ ] GSD pre logs appended before every executor step (planner started one).
- [ ] Code uses grant_vip_from_tariff exclusively for activation (no redeem direct).
- [ ] Handler(s) exactly 1 service (get_service preferred), <=50 LOC (inspect), verb+ctx+res names, strict logging.
- [ ] Forward detect supports forward_from + forward_origin; pure helper(s) with import-inside + docstring.
- [ ] Direct send to candidate on success; blocked fallback notifies *admin* with manual deep link (copy pattern).
- [ ] All gold tests + re-runs pass 0 attributable regressions (VIP golds, atomicity, cross, invariants).
- [ ] Arch rules: 0 critical (1 svc, no DB, domains, logging, 3 crit protected incl channels-VIP atomic + EventBus contract).
- [ ] Self-check PASSED in log + handoff ready for arch-enforcer then test-guardian.
- [ ] Manual deep-link flow + redeem atomic/EVENT untouched + "siempre via token".
- [ ] Handoff: ready for gsd-executor (full copy of precedents + GSD discipline).

After writing PLAN, verify file exists, show summary of tasks, handoff ready for executor.

---

**Handoff note for executor + later agents:** This is new feature under hardener-agile + effort5. Tight scope. Follow verbatim. After executor self-check + tests green: ready for arch-enforcer (0 crit target) + test-guardian ("suite protege adecuadamente") + re-runs + (later documentador if pool). Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

Use tools to verify this PLAN after creation.
