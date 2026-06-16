# Missions Domain

Tareas configurables por admin con recompensas automáticas al completarse.

## Services
- `mission_service.py` — Misiones y progreso
- `reward_service.py` — Recompensas y entrega

## Handlers
- `mission_user_handlers.py` — Usuario: ver misiones, reclamar recompensa
- `mission_admin_handlers.py` — Admin: crear/editar/listar misiones
- `reward_admin_handlers.py` — Admin: crear recompensas (besitos/paquete/VIP)

## Modelos clave
- `Mission` — Definición: nombre, tipo, target, reward_id. Tipos: REACTION_COUNT, DAILY_GIFT_STREAK, DAILY_GIFT_TOTAL, STORE_PURCHASE, VIP_ACTIVE
- `UserMissionProgress` — Progreso por usuario/misión. NO "MissionProgress"
- `Reward` — Recompensa: besitos, paquete o acceso VIP. Tipos: BESITOS, PACKAGE, VIP_ACCESS
- `UserRewardHistory` — Log de entregas

## MissionService API
```python
# Misiones
create_mission(name, description, mission_type, target_value, reward_id,
              frequency) -> Mission  # frequency: ONE_TIME o RECURRING
get_mission(mission_id) -> Mission
get_all_missions(active_only=True) -> list[Mission]
get_available_missions() -> list[Mission]  # Disponibles para el usuario
update_mission(mission_id, **kwargs) -> bool
delete_mission(mission_id) -> bool

# Progreso
get_or_create_progress(user_id, mission_id) -> UserMissionProgress
get_user_progress(user_id, mission_id) -> UserMissionProgress
get_user_all_progress(user_id) -> list[UserMissionProgress]
get_user_active_missions(user_id, bot=None) -> list[dict]  # catch-up si bot
get_available_rewards_for_user(user_id, bot=None) -> list[dict]
increment_progress(user_id, mission_type, amount=1, reference_id=None) -> list[UserMissionProgress]
increment_progress_and_deliver(user_id, mission_type, amount=1, bot=None, reference_id=None) -> list
set_progress(user_id, mission_id, value) -> UserMissionProgress  # preserva completed_at si ya completada

# Entrega automática y catch-up
deliver_pending_rewards(user_id, bot=None) -> int  # solo NEWLY_DELIVERED
deliver_pending_rewards_for_mission(user_id, mission_id, bot=None) -> bool
get_users_with_pending_reward_deliveries() -> list[int]  # scheduler scan
is_mission_reward_delivered(user_id, mission_id) -> bool
apply_daily_gift_mission_updates(user_id, bot=None) -> int
apply_vip_active_mission_updates(user_id, bot=None) -> int
```

## RewardService API
```python
# Creación por tipo
create_reward_besitos(name, description, besito_amount) -> Reward
create_reward_package(name, description, package_id) -> Reward
create_reward_vip(name, description, tariff_id) -> Reward

# CRUD
get_reward(reward_id) -> Reward
get_all_rewards(active_only=True) -> list[Reward]
get_rewards_by_type(reward_type) -> list[Reward]
update_reward(reward_id, **kwargs) -> bool
delete_reward(reward_id) -> bool

# Entrega (async; BesitoService / PackageService / VIPService internos)
deliver_reward(bot, user_id, reward_id, mission_id=None, *, history_claimed=False) -> tuple[bool, str]
try_claim_mission_delivery(user_id, mission_id, reward_id, *, since_completed_at, frequency) -> bool
release_mission_delivery_claim(user_id, mission_id, reward_id) -> None
has_mission_reward_been_delivered(user_id, mission_id, *, since_completed_at=None, frequency) -> bool

# Historial y stats
log_reward_delivery(user_id, reward_id, mission_id, details) -> None
get_user_reward_history(user_id, limit=20) -> list[UserRewardHistory]
get_reward_stats(reward_id) -> dict
```

## Flujo de Misión

```
Admin crea Mission + Reward asociada
    → Admin configura tipo, target, reward
Disparador (reacción, regalo diario, tienda, VIP, etc.)
    → MissionService.increment_progress_and_deliver() o set_progress() + pipeline
    → Si current_value >= target_value → is_completed = True (commit primero)
    → _deliver_mission_reward_if_allowed (automático, todos los MissionType)
        → resolve_delivery_bot (handler o scheduler lazy)
        → idempotencia UserRewardHistory (ONE_TIME / RECURRING por completed_at)
        → RewardService.deliver_reward()
        → Mensaje celebración LucienVoice (besitos / paquete / VIP)
Catch-up si falló o sin bot
    → deliver_pending_rewards en menús (/start, my_missions, rewards_list)
    → deliver_pending_rewards_for_mission en reward_detail y mission_detail (por misión)
    → Job scheduler cada 30 min (pending_mission_rewards)
    → claim_mission_reward: callback-only safety net (no teclado; batch deliver_pending_rewards)
```

## Entrega atómica e idempotencia

- `RewardService.try_claim_mission_delivery()` — `FOR UPDATE` + claim en `UserRewardHistory` antes de side-effects
- Claim fresco `__delivery_claim__` (<60s) bloquea invocaciones concurrentes; stale (>=60s) es resumible
- Estados VIP `token:`/`sent:` son resumibles; `sent:` reutiliza token sin reenviar mensaje
- Filas finalizadas (`details=None`) permiten nuevo claim en ciclos RECURRING
- Claims pendientes no cuentan como entregadas hasta `_finalize_delivery_claim`
- Besitos: idempotente por ciclo vía transacción MISSION + `reference_id=claim.id` (misión) o `reward.id` (directo)
- RECURRING multi-ciclo: cada ciclo acredita besitos de nuevo (claim nuevo → reference_id distinto)
- VIP: reutiliza token; `sent:token:CODE` parseado antes de generar token nuevo
- Paquete: no decrementa stock si historial finalizado del ciclo ya existe
- `deliver_pending_rewards` retorna solo `NEWLY_DELIVERED`; filtra misión/recompensa inactivas
- Catch-up (`deliver_pending_rewards*`): `skip_cooldown=True` — entrega ciclos pendientes sin esperar cooldown
- Flujo automático (`increment_progress_and_deliver`): respeta cooldown vía `previous_completed_at`
- `increment_progress_and_deliver` captura `previous_completed_at` ANTES del reset RECURRING
- `set_progress` preserva `completed_at` si ya estaba completada (RECURRING diario)

## Handlers — claim_mission_reward (safety net)

- Callback `claim_mission_reward` registrado pero **sin botón en teclados** (aceptable)
- Uso: red de seguridad manual/debug; flujo normal es auto-entrega + catch-up en menús
- Invoca `MissionService.deliver_pending_rewards(user_id, bot)` con alertas LucienVoice

## Reglas de Negocio
- Missions de tipo RECURRING se reinician tras completar (progreso se resetea)
- `deliver_reward()` es idempotente en la lógica de entrega
- Si la recompensa es de tipo PACKAGE: stock del paquete se decrementa (reward_stock)
- `increment_progress()` es el mecanismo preferido para incrementar — itera todas las missions activas del tipo dado

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Usar `increment_progress()` con `mission_type` para auto-incrementar todas las missions del mismo tipo
4. Para entregar recompensa: siempre usar `RewardService.deliver_reward()`, no llamar servicios internos directamente

## Cross-domain notifications (EventBus) (Item 5 / reduce via EventBus)

- RewardService held direct BesitoService composition for BESITOS rewards reduced (only this delivery composer touched per tight scope; Package + VIP remain held; other composers like broadcast/game/daily untouched).
- BESITOS delivery now uses local on-demand `BesitoService(db=self.db)` *only* inside `_deliver_besitos` (preserves 100% atomicity of the MISSION credit tx + log_reward_delivery + return msg; credit does its internal commit as before; best-effort schedule_emit still fires post-commit).
- Added rewards-domain observational listener `on_besitos_awarded_rewards_observer` at module bottom (copy of story_service.py:670-694 "Cross-domain event listeners" block + structure + "MUST NOT call back into credit/debit besitos" + "best effort, non-authoritative" + "DESIRED CONTRACT" + log "rewards | besitos_awarded_received | user_id=..."; purely observational, 0 mutation, 0 re-entrancy risk with deliver paths; 0 impact on deliver_reward contracts or partial failure behavior protected by gold test_cross_service_atomicity).
- Central explicit registration in bot.py on_startup (after scheduler, after the narrative listener; import + register call + extended logger.info "... (besitos_awarded -> narrative, rewards)"; comment updated "Fase 3 of eventbus-poc + Item 5: narrative + rewards domains").
- 0 behavior change (deliver_reward BESITOS returns identical success/msg/balance, TransactionSource.MISSION + reference_id=reward.id, UserRewardHistory, Lucien strings); 0 atomicity impact (re-runs of cross_service_atomicity happy + "credit survives deliver False" variants + patch schedule_emit all green in F2/F4); 0 other composers touched.
- Refs: services/event_bus.py (DESIRED CONTRACT + schedule_emit + gather return_exceptions), decisions.md (new entry post Item 1), .planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md + gsd-reward-besito-eventbus.log (GSD pre every, phases F1-F5, self-check PASSED), test_cross_service_atomicity.py (gold for atomicity/partial/best-effort).
- See also services/gamification/CLAUDE.md and services/narrative/CLAUDE.md for sibling cross-domain notes from Item 1.

- Item 6 continuation (remaining core high-volume composers: broadcast/game/daily): BroadcastService + GameService held reduced (locals inside reaction credits + play_* win/streak credits); DailyGiftService uses local inside claim_gift (prop kept for guards); 1-2 obs listeners added for broadcast reactions + game awards (high-value for streaks/promo per 3 critical systems; "MUST NOT credit" + best effort + domain logs; central reg in bot extended to 4). 0 other services (store/mission etc out per tight); 0 behavior/0 atomicity (golds re-runs: atomicity full + reaction chains + daily atomic + game play + besito emit + story inverse all green; patch schedule_emit verifies emit from locals; "credit survives" + post-credit best effort hold). 1-line test fixes only (w/ daily hasattr precedent + comments). Docs: broadcast/CLAUDE new section, gamif/CLAUDE append, this, decisions Item6 + BATCH "4 items completed in tirón". Refs: .planning/phases/24-remaining-besito-compositions/PLAN.md + gsd-remaining-besito-compositions.log (full GSD + self-check PASSED + handoff to arch-enforcer/test-guardian), 23-PLAN (gold), atomicity gold + reaction_mission_flow (strict + patch + TestSession + N806 + 777 + try/finally).

- Item 10 continuation (remaining store purchase composer; second of new pool of 4, auto after Item 9 closed full 6-step + "suite protege adecuadamente" + tests green + documentador updated ROADMAP): StoreService held reduced (locals on-demand BesitoService(db=self.db) *only* inside balance/debit sites for atomic PURCHASE debits + history + source=PURCHASE in complete_order/direct_purchase/create_order; high-value obs listener on_besitos_awarded_store_observer "MUST NOT credit/debit/mutate" + "store | besitos_awarded_received" + DESIRED + central reg + Item 10; 0 other services/files touched per tight (0 store_user already get_service; 0 package/reward delivery); 0 behavior/0 atomicity (golds re-runs cross full w/ patch schedule_emit + strict + DESIRED + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession/file + 777 + gather + N806 tol w/doc protect). Refs: .planning/phases/28-remaining-besito-store/PLAN.md + impact10 + gsd-remaining-besito-store.log, 23/24 precedents + atomicity gold, 25/26/27 pool phrase + "Nth of new pool of 4" + self-check + handoff.
