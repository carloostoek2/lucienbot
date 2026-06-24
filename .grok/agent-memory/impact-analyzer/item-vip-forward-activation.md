# Impact Analysis: VIP Forward Activation

**Date:** 2026-06-24  
**Change:** Admin forwards a VIP candidate's message → bot extracts `telegram_id` via `message.forward_origin` → admin confirms identity + tariff → service activates VIP (token redeem + subscription) → bot DMs native invite link to user; on DM failure, admin gets manual deep-link fallback (existing token flow).  
**Analysis only** — no implementación

---

## Executive Summary

This item adds an **admin shortcut** to the current manual VIP onboarding path (`generate_token` → share deep link → user `/start` redeems). The heavy lifting already exists in `VIPService.grant_vip_from_tariff` (token generation + `redeem_token_with_missions` + `create_vip_invite_link`) and in fulfillment/reward paths that DM users with `vip_direct_access` + `vip_access_keyboard`. The new work is **wiring**: FSM in `vip_handlers.py`, a pure forward-origin extractor, one orchestration service method that grants + attempts DM + returns fallback metadata, and LucienVoice strings for the wizard.

**Global risk: MEDIUM-HIGH** — touches critical system **#3 channels-VIP** (pending/approve/subs/grant/revoke) because activation must still flow through `redeem_token` (SELECT FOR UPDATE, extension vs new sub, `EVENT_VIP_ACTIVATED` post-commit). The implementation is low-risk **if** it reuses `grant_vip_from_tariff` without bypassing token/subscription invariants. No scheduler, channel ban, or expire logic should change.

**Sensitive systems protected by design:**
- **channels-VIP:** Subscription created only via existing redeem path; invite link is post-activation delivery (same as store/fulfillment).
- **Gamification atomicity:** Orthogonal; no besito/mission credit in handler.
- **Narrative FSM / EventBus:** `EVENT_VIP_ACTIVATED` already emitted inside `redeem_token`; nurture listener in `bot.py` unchanged.

**Scope validity:** Tight and **single pool item** (~1 item). No DB migration. No changes to `common_handlers` `/start` redeem path (fallback deep link reuses it). Main complexity is Telegram forward privacy (`MessageOriginHiddenUser`) and handler FSM + 1-service-call discipline on the confirm step.

---

## Consumers / Call Sites Map

### Core VIP activation (must reuse, not fork)

| Location | Lines | Role |
|----------|-------|------|
| `services/vip_service.py` | 175–303 | `redeem_token` — FOR UPDATE, extend/new sub, clear entry state, `schedule_emit(EVENT_VIP_ACTIVATED)` |
| `services/vip_service.py` | 305–322 | `redeem_token_with_missions` — VIP_ACTIVE mission side effects |
| `services/vip_service.py` | 456–480 | `create_vip_invite_link` — member_limit=1, 7-day expire |
| `services/vip_service.py` | 482–524 | `grant_vip_from_tariff` — **primary reuse target** for activation + invite generation |
| `services/vip_service.py` | 526–535 | `resend_vip_invite_for_user` — renewal/DM-retry pattern (not primary, but related) |

### Current manual admin token flow (unchanged fallback)

| Location | Lines | Role |
|----------|-------|------|
| `handlers/vip_handlers.py` | 181–252 | `generate_token` — tariff pick → `generate_token` → deep link to admin |
| `handlers/vip_handlers.py` | 342–364 | `copy_token` — admin copies `t.me/bot?start=TOKEN` |
| `handlers/common_handlers.py` | 114–139 | `/start` + `redeem_token_with_missions` + `create_vip_invite_link(allow_fallback=True)` |

### DM delivery precedents (pattern to mirror in new service method)

| Location | Lines | Role |
|----------|-------|------|
| `services/fulfillment_service.py` | 306–319 | `_send_vip_access_dm` — `bot.send_message` + `vip_access_keyboard`, swallow TG errors |
| `services/fulfillment_service.py` | 360–387 | `_dispatch_vip_grant` — partial metadata when invite/DM fails |
| `services/reward_service.py` | 421–479 | `_deliver_vip_access` — grant + DM + partial grant markers |

### EventBus / nurture (downstream of redeem — no edit expected)

| Location | Lines | Role |
|----------|-------|------|
| `services/event_bus.py` | 26 | `EVENT_VIP_ACTIVATED` constant |
| `bot.py` | 223 | `get_event_bus().register(EVENT_VIP_ACTIVATED, on_vip_activated)` |
| `services/nurture_service.py` | 414–438 | `on_vip_activated` — enroll nurture sequence (best-effort) |

### Forward extraction precedent (different origin type)

| Location | Lines | Role |
|----------|-------|------|
| `handlers/channel_handlers.py` | 345–375 | Uses `F.forward_from_chat` + `message.forward_from_chat` for **channel** registration — **not** user forwards; do not copy for VIP user ID |

### Keyboards / callbacks

| Location | Lines | Role |
|----------|-------|------|
| `keyboards/inline_keyboards.py` | 248–273 | `tariffs_keyboard(for_selection=True)` + `SelectTariffCallback` |
| `keyboards/inline_keyboards.py` | 305–315 | `confirmation_keyboard` |
| `keyboards/inline_keyboards.py` | 347–360 | `vip_management_keyboard` — add entry button here |
| `keyboards/callback_data.py` | 68–71 | `SelectTariffCallback(prefix="select_tariff")` — shared with reward wizard; disambiguate via **FSM state** |

### Tests referencing VIP grant/redeem/emit

| File | Coverage |
|------|----------|
| `tests/unit/test_vip_service.py` | redeem emit, invite links, `grant_vip_from_tariff`, partial metadata |
| `tests/integration/test_vip_subscription_lifecycle.py` | scheduler expire + extension model |
| `tests/handlers/test_common_handlers.py` | `/start` redeem + invite |
| `tests/unit/test_fulfillment_service.py` | grant/resend VIP dispatch + DM failure paths |
| `tests/unit/test_reward_service.py` | `grant_vip_from_tariff` / resend mocks |
| `tests/unit/test_event_bus.py` | nurture `on_vip_activated` gold |
| `tests/integration/test_nurture_lifecycle_e2e.py` | VIP activated → nurture |
| `tests/integration/test_invariants.py` | I4 token single-use, I5 VIP access |
| `tests/unit/test_mission_side_effects.py` | VIP mission side effects via redeem |
| `tests/integration/test_callbackdata_vip.py` | `SelectTariffCallback` packing/filter |

**Note:** `forward_origin` / `MessageOriginUser` is **not used anywhere** in app code today (only aiogram types in venv). Greenfield extractor required.

---

## Risks

### Critical

| Risk | Mitigation |
|------|------------|
| Bypass token/subscription model (direct VIP flag or channel add without `redeem_token`) | New service method must call `grant_vip_from_tariff` (or `generate_token` + `redeem_token_with_missions`) only; never write `Subscription` in handler |
| Race on double confirm / double forward | Final confirm is callback → `IdempotencyMiddleware` applies; service `redeem_token` uses `with_for_update`; document that second activation on active user **extends** sub (existing behavior) |
| Wrong user ID extracted | Use `message.forward_origin` with `type == "user"` → `sender_user.id`; reject `MessageOriginHiddenUser`, channel/chat origins; show Lucien error |
| `EVENT_VIP_ACTIVATED` skipped or duplicated | Do not emit from handler; rely on `redeem_token` only (already tested in `TestVIPServiceNurtureEmit`) |

### Medium

| Risk | Mitigation |
|------|------------|
| User blocked bot → DM fails | Mirror `fulfillment_service` partial path: subscription active + return `token_code` / deep link URL in admin message (`LucienVoice.token_generated` or dedicated fallback string) |
| `SelectTariffCallback` handler collision with `TokenStates.selecting_tariff` | New `ForwardActivationStates.selecting_tariff` + separate handler; same callback prefix OK when gated by state (precedent: reward wizard) |
| Handler >1 service call / business logic in handler | Extract `extract_forwarded_user_id` as pure util; final step = **one** `grant_vip_from_admin_forward(bot, user_id, tariff_id)` returning all admin/user messages |
| Renewal vs new subscriber ambiguity | `redeem_token` already extends active sub; admin UI should show "renovación" if `is_user_vip(target_id)` (read-only preview via service `is_user_vip` in confirm step — acceptable as part of single preview call or pure FSM data from prior step) |
| `create_vip_invite_link(allow_fallback=False)` in grant path | Keep fail-closed for auto-DM flow; fallback uses **token deep link**, not static channel link (matches requirement) |

### Low

| Risk | Mitigation |
|------|------------|
| Nurture / mission side effects | Automatic via `redeem_token_with_missions`; no change |
| Scheduler expire/ban | Unaffected if subscription dates correct |
| `common_handlers` `/start` path | Unchanged; fallback deep link still works |
| No `test_vip_handlers.py` today | Add handler unit tests (mock service); gold stays in `test_vip_service` |

---

## Proposed Tight Scope

### 1. Pure helper (new file recommended)

**`utils/telegram_forward.py`** (or `utils/vip_forward.py`):

```python
def extract_forwarded_user_id(message: Message) -> int | None:
    """From MessageOriginUser.sender_user.id; None if hidden/channel/chat/invalid."""
```

- aiogram 3: `message.forward_origin`, not deprecated `forward_from`.
- Handle `MessageOriginHiddenUser` → `None` + admin message "usuario oculto por privacidad".
- Unit-testable without DB.

### 2. Service method (single orchestration entry)

**`VIPService.grant_vip_from_admin_forward(bot, user_id: int, tariff_id: int)`**  
→ `tuple[bool, str, dict]` aligned with `grant_vip_from_tariff` metadata:

1. Call existing `grant_vip_from_tariff(bot, user_id, tariff_id)`.
2. If `ok` and `invite_link`: attempt DM (`vip_direct_access` + `vip_access_keyboard`) — copy pattern from `fulfillment_service._send_vip_access_dm`.
3. Return variants:
   - **Full success:** `(True, admin_success_msg, {..., "dm_sent": True})`
   - **VIP ok, DM failed:** `(False, admin_fallback_with_token_url, {..., "vip_activated": True, "token_code": ..., "dm_sent": False})` — reuse metadata from partial invite failure path
   - **Grant failed:** existing error messages

**Do not** modify `redeem_token` / `grant_vip_from_tariff` semantics in this item unless extracting shared `_send_vip_access_dm` to avoid duplication (optional refactor, out of scope if it widens diff).

### 3. Handler FSM (`vip_handlers.py`)

**New `ForwardActivationStates`:**

| State | Trigger | Action |
|-------|---------|--------|
| `waiting_forwarded_message` | Callback from VIP menu "Activar por reenvío" | Prompt admin to forward user message |
| `confirming_user` | Message with valid `forward_origin` user | Show `@username` / name / `ID`; `confirmation_keyboard` |
| `selecting_tariff` | Confirm user | `tariffs_keyboard(for_selection=True)` |
| `confirming_activation` | `SelectTariffCallback` | Show user + tariff summary; final confirm |
| (clear) | Confirm activation | **One** `grant_vip_from_admin_forward` call; render result to admin |

**Tariff selection UX decision (recommended):**  
**After user identity confirm, before final activation confirm** — reuse existing tariff keyboard (same as "Generar token"). Rationale: renewals and new subs may need different durations; matches admin mental model; no new config.

**Entry:** New button in `vip_management_keyboard()` e.g. `"📨 Activar VIP por reenvío"`.

**Admin guards:** `is_admin` on all callbacks/messages (match `channel_handlers` `_deny_non_admin_message` pattern if FSM open).

### 4. LucienVoice (new strings)

- Forward prompt / user detected preview / confirm activation / success DM sent / fallback manual link / forward invalid / hidden user / no tariffs.

### 5. Callbacks

- Reuse `confirmation_keyboard("confirm_forward_vip", "admin_vip")` string callbacks **or** new `ConfirmForwardVipCallback` if packed data needed (tariff_id + user_id in state is enough — prefer FSM `state.update_data`).

### 6. Explicitly out of scope

- Changing `generate_token` / manual token UI
- `common_handlers` redeem flow
- Store/fulfillment/reward VIP delivery
- Channel scheduler / ban logic
- Auto-detect tariff from forwarded message content
- Support for forwarded messages from channels/groups as VIP candidates

---

## Affected Tests

### New tests (executor should add)

| File | Cases |
|------|-------|
| `tests/unit/test_telegram_forward.py` (or under `test_vip_service`) | `MessageOriginUser` → id; HiddenUser → None; no forward → None |
| `tests/unit/test_vip_service.py` | `grant_vip_from_admin_forward`: DM ok; DM fail → token in metadata; grant fail |
| `tests/handlers/test_vip_forward_handlers.py` (new) | FSM steps mocked service; admin-only; invalid forward |

### Baseline / regression (run before and after)

```bash
# Gold — VIP service core + invite + grant
pytest tests/unit/test_vip_service.py -q --tb=line -p no:cov --override-ini="addopts="

# Gold — subscription lifecycle / scheduler protection
pytest tests/integration/test_vip_subscription_lifecycle.py -q --tb=line -p no:cov --override-ini="addopts="

# Gold — /start redeem + invite (unchanged path)
pytest tests/handlers/test_common_handlers.py -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or token or start"

# Gold — EVENT_VIP_ACTIVATED → nurture
pytest tests/unit/test_event_bus.py tests/integration/test_nurture_lifecycle_e2e.py -q --tb=line -p no:cov --override-ini="addopts=" -k "vip_activated or vip_activated"

# Gold — fulfillment/reward VIP grant contracts (no regression)
pytest tests/unit/test_fulfillment_service.py tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or grant_vip or resend_vip"

# Gold — invariants I4/I5 + mission VIP side effects
pytest tests/integration/test_invariants.py tests/unit/test_mission_side_effects.py -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or token or VIP"

# Callback data — SelectTariffCallback still valid
pytest tests/integration/test_callbackdata_vip.py -q --tb=line -p no:cov --override-ini="addopts="

# New handler tests (post-implementation)
pytest tests/handlers/test_vip_forward_handlers.py -q --tb=line -p no:cov --override-ini="addopts="

# Combined VIP forward slice (CI-friendly)
pytest tests/unit/test_vip_service.py tests/integration/test_vip_subscription_lifecycle.py tests/handlers/test_common_handlers.py tests/unit/test_event_bus.py tests/integration/test_invariants.py -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or token or redeem or grant_vip or invite"
```

---

## Files Map

### Edit

| File | Change |
|------|--------|
| `handlers/vip_handlers.py` | `ForwardActivationStates`, handlers, menu entry callback |
| `services/vip_service.py` | `grant_vip_from_admin_forward` (+ optional thin DM helper) |
| `utils/telegram_forward.py` | **Create** — `extract_forwarded_user_id` pure |
| `utils/lucien_voice.py` | Admin forward-flow copy |
| `keyboards/inline_keyboards.py` | Button in `vip_management_keyboard` |
| `tests/unit/test_vip_service.py` | New method tests |
| `tests/handlers/test_vip_forward_handlers.py` | **Create** — FSM handler tests |
| `tests/unit/test_telegram_forward.py` | **Create** — pure helper tests |
| `services/vip/CLAUDE.md` | Document forward-activation flow (minimal) |

### No touch (unless optional doc)

| File | Reason |
|------|--------|
| `bot.py` | No new EventBus listeners |
| `handlers/common_handlers.py` | `/start` redeem unchanged |
| `services/fulfillment_service.py` | Pattern reference only |
| `services/reward_service.py` | Orthogonal delivery path |
| `services/mission_service.py` | Side effects via existing redeem |
| `handlers/channel_handlers.py` | Different forward type |
| `models/*` | No schema change |
| Scheduler / channel grant jobs | No subscription semantics change |

---

## Pool Partition Recommendation

**1 item** — single cohesive feature:

- Pure helper + 1 service method + vip_handlers FSM + keyboard button + LucienVoice + tests.

Do **not** split token-flow refactor or shared `_send_vip_access_dm` extraction unless executor hits LOC/arch-enforcer pressure; that would be a separate hardening item.

---

## Ready for chain

### Handoff to gsd-planner

- Implement FSM order: **menu → forward → confirm user → select tariff → confirm activate → service once**.
- Reuse `grant_vip_from_tariff`; add `grant_vip_from_admin_forward` for DM + admin fallback only.
- `forward_origin` + `MessageOriginUser.sender_user.id`; reject hidden origins.
- Tariff UX: reuse `tariffs_keyboard(for_selection=True)` after user confirm.

### DoD for downstream

| Agent | Verify |
|-------|--------|
| **gsd-planner** | Scope matches 1 item; no redeem/scheduler edits |
| **gsd-executor** | Handler final step = 1 service call; admin `is_admin` everywhere |
| **arch-enforcer** | No DB in handlers; funcs ≤50 LOC (split pure builders if needed); channels-VIP invariants preserved |
| **test-guardian** | Run gold commands above + new tests; `EVENT_VIP_ACTIVATED` still single emit from redeem |
| **documentador** | Update `services/vip/CLAUDE.md` flow diagram |

---

*Report generated by impact-analyzer agent. Evidence: grep/read of `vip_service.py`, `vip_handlers.py`, `common_handlers.py`, `fulfillment_service.py`, `channel_handlers.py`, `bot.py`, keyboards, `test_vip_service.py`, `test_vip_subscription_lifecycle.py`, aiogram `MessageOriginUser` type.*