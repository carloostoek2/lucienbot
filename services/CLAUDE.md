# Services

Lógica de negocio por dominio. Un service = un dominio (no fragmentar).

## Servicios Disponibles

<!-- AUTO:SERVICES -->
| Service | Dominio | Archivo | Métodos |
|---------|---------|---------|--------|
| `ChannelService` | Channels | `channel_service.py` | close, create_channel, get_channel_by_id, get_channel_by_db_id, get_all_channels, +13 más |
| `VIPService` | VIP | `vip_service.py` | close, create_tariff, get_tariff, get_all_tariffs, update_tariff, +18 más |
| `UserService` | Users | `user_service.py` | create_user, get_user, get_or_create_user, get_all_users, get_admins, +4 más |
| `SchedulerService` | System | `scheduler_service.py` | start, stop |
| `HealthService` | System/Observability | `health_service.py` | check_db_connectivity, check_bot_runtime, check_channels_status, check_scheduler_jobs, check_event_bus_listeners, check_critical_services_sanity, check_backup_status, get_overall_status, close, _get_db |
| `BesitoService` | Gamificación | `besito_service.py` | close, get_or_create_balance, get_balance, get_balance_with_stats, credit_besitos, +6 más |
| `BroadcastService` | Broadcast | `broadcast_service.py` | create_reaction_emoji, get_reaction_emoji, get_reaction_emoji_by_emoji, get_all_emojis, update_emoji_value, +12 más |
| `DailyGiftService` | Gamificación | `daily_gift_service.py` | get_config, update_config, is_active, get_gift_amount, get_last_claim, +5 más |
| `GameService` | Gamificación (Minijuegos) | `game_service.py` | play_dice_game, get_menu_data, get_dice_entry_data, play_trivia_game, etc. User messages directos (reglas claras, feedback simple) desde tono 2026. |
| `PackageService` | Store | `package_service.py` | create_package, add_file_to_package, get_package, get_all_packages, get_available_packages_for_store, +11 más |
| `MissionService` | Missions | `mission_service.py` | close, create_mission, get_mission, get_all_missions, get_available_missions, +10 más |
| `RewardService` | Missions | `reward_service.py` | create_reward_besitos, create_reward_package, create_reward_vip, get_reward, get_all_rewards, +7 más |
| `StoreService` | Store | `store_service.py` | close, create_product, get_product, get_all_products, get_available_products, +15 más. User-facing: copy directo en tienda (Tienda de Lucien, productos, besitos) desde 2026. |
| `AnonymousMessageService` | VIP | `anonymous_message_service.py` | send_message, get_message, get_all_messages, get_unread_messages, mark_as_read, reply_to_message, get_sender_info, delete_message |



## Reglas de Services

- Un service es dueño de su dominio
- Centraliza toda la lógica del dominio
- **PROHIBIDO**: lógica duplicada en múltiples services
- **PROHIBIDO**: acceso a DB directo (usar models)
- Funciones máximo 50 líneas
- Logging en cada acción importante

## Acceso a DB

Los services NO acceden a DB directamente. Usan models:

`from models import User, BesitoTransaction

# Correcto
user = await session.get(User, user_id)
# Incorrecto
await session.execute(text("SELECT * FROM users"))`

## Cross-cutting: Internal EventBus (PoC Item 1)
- `services/event_bus.py` provee `InternalEventBus` + `get_event_bus()` + `EVENT_BESITOS_AWARDED` + `schedule_emit` (para emitir desde paths sync como credit_besitos).
- Patrón: async gather con return_exceptions=True (errores de listeners se loguean por listener y no propagan).
- Primer caso de uso: `credit_besitos` (post commit) emite "besitos_awarded"; narrative es primer listener (ver sus CLAUDEs).
- Registro explícito en bot.py (no side effects en imports de dominios).
- Exportado en este __init__ para conveniencia de listeners y tests.
- Conservador y removable: el bus es infraestructura liviana; no inyección en esta iteración.

## Observability (Item 11)
HealthService (Item 11): read-only/best-effort system status for Custodios/ops/platform (DB ping/latency, bot runtime, channels free/VIP/pending/ready, scheduler jobs, EventBus listener counts (besitos_awarded focus), critical sanity (besitos neg balances + recent tx vol, VIP active/expiring, narrative progress/achievements), backup last age). Follows AnalyticsService pattern al pie de la letra (__init__ db=None, _owns_session, _get_db, close, direct model counts for speed, no mutation). Admin-only via is_admin() + with get_service(HealthService) as h: exactly 1 call in handlers (analytics_handlers.py extended for /health Command + cb "admin_health"; menu btn "🛡️ Pulso del reino" after analytics). Logging "health_service | <action> | user_id=0 | status=... latency=..." (or admin_id for bot). Best-effort + short timeouts + try/except; never blocks main loop or tx. 0 mutation/0 impact on 3 crit (gamif credits/reactions/daily/missions, narrative progress/archetypes/FSM/quiz, channel pending/approve/expire/bans/subs, VIP grant/revoke) or atomicity/EventBus/get_service contracts (observes only, "MUST NOT mutate"). Optional /health JSON endpoint (aiohttp if avail + HEALTH_ENABLED=1 + separate port; non-blocking task in bot.py on_startup after scheduler/listeners; graceful skip if no dep/flag; handler uses get_service(HealthService)). Terminal: python -m scripts.health_check [--json] [--verbose] (standalone, same service, exit codes, user_id=0 logs). See decisions Item 11 + impact item11 + PLAN 29-observability-health + gsd-observability-health.log. Documentador updated ROADMAP at tirón close.

**Hardener pattern for new observability / cross-cutting services (Item 11 precedent):** Introduced via full 6-agent sequence (impact-analyzer explicit 0-risk to 3 crit + atomicity contracts; gsd-planner 5-6 phases + copy Analytics al pie + GSD pre; executor self-check PASSED 80+; arch-enforcer PASS WITH NOTES 0 crit; test-guardian "suite protege adecuadamente" + golds re-runs + broader; explicit documentador launch at F6 for ROADMAP/docs). HealthService: read-only/best-effort, __init__ db=None + _owns + _get_db + close + direct counts (no mutation), <50 LOC/func, verb+ctx+res, logging "health_service | <action> | user_id=0 | ...", exactly 1 call in handlers via get_service + is_admin. Endpoint/terminal/admin view non-blocking, graceful skip. 0 behavior/0 atomicity/0 impact on gamif/narrative/channel-VIP contracts. See 29-*-SUMMARY.md + root CLAUDE Hardener Workflow section + claude-md-sync agent for future CLAUDE reality syncs. Pattern generalizable for future read-only system services.

Item 4/34 extended hygiene (structured logging to rate/idemp + besito sample + /health verify + handlers/CLAUDE sync + decisions entry); see 34-PLAN + gsd-34-observability-health-docs.log + pool phrase. 0 impact.
