# Impact Analysis: Item 1 — Lucien emisor (Part A, A1-A5)

**Date:** 2026-08-15
**Change:** Persistir `business_connection` de la dueña en Lucien, emitir `EVENT_VIP_KICKED` desde los 3 puntos de expulsión y notificar al chat de coordinación vía `LinkNotifier` (flag `FEATURE_LINK_ENABLED`, default off).
**Repo:** `/home/ubuntu/repos/lucienbot`
**Analysis only** — no implementación.

## Executive Summary

Cambio de alcance medio en Lucien, de cero superficie business hoy (verificado: no existe `EVENT_VIP_KICKED`, `link_notifier`, handler `business_connection`, `LINK_CHAT_ID` ni `FEATURE_LINK_ENABLED` en el repo). El cambio agrega una tabla nueva (`business_connections`), un handler aiogram `business_connection`, un listener best-effort (`LinkNotifier`) y 3 emisiones `schedule_emit` post-ban (admin_revoke, scheduler expiry, startup cleanup). Riesgo global MEDIO-BAJO: todos los sistemas sensibles (gamificación, narrativa, channels-VIP, atomicidad/EventBus/get_service) quedan intactos con flag OFF y con flag ON el emisor es best-effort puro (nunca rompe el flujo de expulsión).

Se confirman 3 correcciones críticas al plan contra el código real: (1) `Channel` NO tiene `.name` — el campo es `channel.channel_name` (models.py:91); (2) el handler A1 que "upserta via `SessionLocal`" violaría la regla no-negociable "handlers NO acceden a DB" (cero precedente en `handlers/`; todos los handlers llaman 1 service) — debe delegar a un service; (3) orden en `on_startup`: el tercer hook (startup cleanup) correría ANTES de registrar el listener `EVENT_VIP_KICKED` y ANTES de que `_bot_token` exista, por lo que el aviso se perdería en silencio — hay que registrar el listener al tope de `on_startup` y darle al notifier un bot lazy propio e independiente del scheduler.

El head de alembic es `20260629_user_chat_id` (confirmado con `alembic heads`), aiogram 3.24.0 (soporta `router.business_connection()`), y el layout de tests unitarios es `tests/unit/` (el path `tests/test_link_notifier.py` del plan está mal: debe ser `tests/unit/test_link_notifier.py`).

## Consumers / Call Sites Map

| Función / símbolo | Archivo:Línea | Consumers (quién llama) | Depende de |
|---|---|---|---|
| `check_expired_subscriptions_on_startup(bot)` | bot.py:141 | `on_startup` bot.py:213 | `VIPService.get_expired_subscriptions`, `has_other_active_subscription`, `expire_subscription`, `clear_vip_entry_state`, `bot.ban_chat_member` L184-186 |
| `on_startup(bot)` | bot.py:204 | registrado en `dp.startup` bot.py:373 | `init_db`, startup check L213, `get_scheduler` L216, registros EventBus L222-229, `HEALTH_ENABLED` L239 |
| `admin_revoke_subscription(bot, subscription_id, admin_id)` | vip_service.py:1005 | handlers de admin revoke (grep: `vip_subscriber_admin_handlers`, `test_vip_service.py:1126/1138/1266`) | `ban_chat_member` L1048, query `user` L1050, `channel` L1027, `subscription` |
| `_process_expired_subscriptions()` | scheduler_service.py:189 | APScheduler job `expire_subscriptions` L468-475 | `_get_bot()` L195, `get_expired_subscriptions`, `ban_chat_member` L218, query `user` L225 |
| `_get_bot()` | scheduler_service.py:47 | jobs del scheduler (L92, 122, 140, 170, 195, 337) | `_bot_token` seteado SOLO en `SchedulerService.__init__` L425-426 |
| `EVENT_BESITOS_AWARDED` / `EVENT_VIP_ACTIVATED` | event_bus.py:23 / :26 | emisores (besito_service:92-103, vip_service:17,337,649,697,747) y registradores (bot.py:79,222-229) | `InternalEventBus`, `get_event_bus`, `schedule_emit` |
| `get_event_bus()` / `schedule_emit()` | event_bus.py:112 / :124 | vip_service.py:17, bot.py, besito_service.py | singleton `_bus` |
| `on_vip_activated(payload)` | nurture_service.py:414 | `get_event_bus().register(EVENT_VIP_ACTIVATED, ...)` bot.py:229 | `get_service(NurtureService)` |
| `Channel.channel_id` / `Channel.channel_name` | models.py:90 / :91 | todos los flujos de canales/grants/bans | — |
| `User.username` | models.py:65 | perfiles, log de kinks | — |
| `SessionLocal` | models/database.py:33 | services (vip, scheduler, etc.) | `engine` |
| `BotConfig` (dataclass + `os.getenv`) | config/settings.py:11 | `bot.py:307` (TOKEN), `models/database.py:11` | `load_dotenv` |

## Risks (verificados contra código real)

| # | Severidad | Riesgo | Mitigación | Evidencia |
|---|---|---|---|---|
| R1 | CRITICAL | **Tercer hook (startup) no emitiría**: (a) `check_expired_subscriptions_on_startup` corre en L213 ANTES del registro de listeners (L222-229); (b) `_bot_token` se setea en `get_scheduler(bot)` L216, después de L213 → si el notifier reusa `_get_bot()` del scheduler, `RuntimeError` al primer ban de startup y el aviso se pierde (best-effort lo traga). | Registrar `EVENT_VIP_KICKED` al TOPE de `on_startup` (después de `init_db` L210, antes de L213). `LinkNotifier` debe tener su PROPIO bot lazy a partir de `bot_config.TOKEN`/`BOT_TOKEN` (espejo del patrón `_bot_token` de scheduler pero self-contained). | bot.py:213 vs L222-229; scheduler_service.py:425-426 vs L47-54 |
| R2 | CRITICAL | **A1 handler con `SessionLocal` viola regla no-negociable** ("handlers llaman exactamente 1 service", "PROHIBIDO acceso a DB fuera de models"). Cero handlers tocan DB hoy (grep `SessionLocal|db.query|get_db` en `handlers/` = 0 resultados). arch-enforcer marcaría FAIL. | El handler `@router.business_connection()` delega el upsert a UN service (p. ej. `LinkNotifier.upsert_business_connection(...)` como classmethod, o un `BusinessConnectionService` fino). Handler = extraer campos + 1 llamada + log `business_connection_enabled/disabled`. | reglas CLAUDE.md/rules.md; `handlers/__init__.py` (nada de DB) |
| R3 | MEDIUM | **`channel.name` no existe** → payload perdería `channel_name`. El plan ya pedía verificar; la verificación da: campo = `channel.channel_name` (models.py:91, nullable). | Usar `channel.channel_name` en los 3 hooks. Incluir siempre (es nullable, el contrato lo permite opcional). | models/models.py:91 |
| R4 | MEDIUM | **Path de test A5 mal**: `tests/test_link_notifier.py` no sigue el layout (unitarios van en `tests/unit/` con `__init__.py`). | Crear `tests/unit/test_link_notifier.py`; correr con flags hardener `-p no:cov --override-ini="addopts="` (el addopts default incluye `--cov-fail-under=70` que rompería el run aislado). | `tests/unit/` layout; pyproject.toml addopts |
| R5 | MEDIUM | **Regresión en golds de `test_vip_service.py`** si los tests de `admin_revoke` patchean `schedule_emit` y ahora el branch "kicked" emite un 2º evento. Verificado: `test_admin_revoke_bans_without_immediate_unban` (L1133) usa `AsyncMock()` y NO patcha `schedule_emit`; el emit nuevo no tiene listener → no-op → `bot.send_message.assert_called_once()` (L1148) no se rompe. `deactivated_only`/`channel_inactive`/`not_found` NO emiten (regla A3) → sus tests (`assert_not_called`) intactos. | Correr `test_vip_service.py` completo. Si algún gold llegara a patchear `schedule_emit` a futuro, filtrar por evento. | test_vip_service.py L1126-1149, L1259-1274 |
| R6 | LOW | **`test_alembic_heads.py` (integration)** valida 1 solo head + history sin gaps. La migración nueva (`20260815_business_connections`, `down_revision="20260629_user_chat_id"`) mantiene 1 head → no rompe. `current_revision_matches_head` es warn-only si no hay DB. | Correr `tests/integration/test_alembic_heads.py` tras crear la migración. | `alembic heads` = `20260629_user_chat_id (head)` |
| R7 | LOW | **Export de `EVENT_VIP_KICKED` incompleto**: bot.py:79 y services/__init__.py:11/77 importan los 2 eventos actuales; `vip_service.py:17` importa `EVENT_VIP_ACTIVATED, get_event_bus, schedule_emit`. Si no se agrega el nuevo a los 3 sitios + `__all__`, falla la importación o el registro. | A2 debe tocar: `event_bus.py` (const), `services/__init__.py` (import + `__all__`), `bot.py:79` (import), `vip_service.py:17` (import), `scheduler_service.py` (import nuevo). | event_bus.py:23-26; services/__init__.py:11,77-78 |
| R8 | LOW | **Flag OFF = comportamiento idéntico**: si `enabled=False` o `chat_id=None` el notifier hace early-return antes de tocar DB o Telegram. Con `LINK_CHAT_ID` unset → `int(os.getenv("LINK_CHAT_ID", "0")) or None` → `None` → no-op. | A4 lee `os.getenv("FEATURE_LINK_ENABLED") == "1"` (precedente `HEALTH_ENABLED` bot.py:239) y `int(os.getenv("LINK_CHAT_ID", "0"))`. Verificación A4: flag unset → 0 cambios de comportamiento. | bot.py:239; config/settings.py |
| R9 | LOW | **Concurrencia en upsert del handler** (dos updates `business_connection` simultáneos). Es idempotente por PK (insert-or-update), sin carrera destructiva. | Upsert por PK con `merge()`/`query.get()`; transacción corta vía el service. | — |
| R10 | INFO | **`username` con "@"**: `User.username` guarda el handle SIN "@"; el contrato REQ-LNK-03 muestra `"@user"`. Decidir y documentar (prefijo "@" al construir el payload, o raw). | Consistente entre A2 y B2 (Diana). | SPEC REQ-LNK-03 |

## Affected Tests

**Nuevos (A5):**
- `tests/unit/test_link_notifier.py` — 4 asserts del plan: disabled → no send; enabled → texto `[LINK]` + campos JSON; `send_message` raise → swallow (no propaga); `event_id` uuid4 fresco por evento.

**Comandos exactos (flags hardener, evitan el gate de coverage del addopts default):**
```bash
cd /home/ubuntu/repos/lucienbot
# A5 nuevo test
python3 -m pytest tests/unit/test_link_notifier.py -q --tb=line -p no:cov --override-ini="addopts=" -v --no-header
# Regresión golds/unitarios directos
python3 -m pytest tests/unit/test_vip_service.py tests/unit/test_scheduler.py tests/unit/test_event_bus.py -q --tb=line -p no:cov --override-ini="addopts="
# Migración nueva (un solo head) + flujos VIP de integración
python3 -m pytest tests/integration/test_alembic_heads.py -q --tb=line -p no:cov --override-ini="addopts="
python3 -m pytest tests/integration/test_vip_flows.py tests/integration/test_vip_subscription_lifecycle.py -q --tb=line -p no:cov --override-ini="addopts="
# Smoke tier unit completo (regresiones indirectas)
python3 -m pytest tests/unit/ -q --tb=line -p no:cov --override-ini="addopts="
```

**Tests existentes que pueden regresar:**
- `tests/unit/test_vip_service.py` — `admin_revoke_*` (kicked/deactivated_only/channel_inactive) + golds de `schedule_emit` de redeem (L467/485/1223). Riesgo bajo (verificado R5).
- `tests/unit/test_scheduler.py` — cubre registro de jobs, no `_process_expired_subscriptions` (grep = 0 tests directos del branch de ban). Riesgo bajo.
- `tests/unit/test_event_bus.py` — usa `_reset_event_bus_for_tests` + instancias frescas; agregar la constante no rompe.
- `tests/integration/test_alembic_heads.py` — valida el nuevo single head.
- `tests/integration/test_vip_flows.py` / `test_vip_subscription_lifecycle.py` — ejercitan `get_expired_subscriptions`/unban, no admin_revoke; riesgo bajo.
- `tests/handlers/test_vip_subscriber_admin_handlers.py` — toca admin revoke (candidato a revisar si cambia la firma; la emisión post-commit no la cambia).

## Files Map

- **Edit (producción):**
  - `models/models.py` — modelo `BusinessConnection` (estilo `Column`, `func.now()`), espejo de Diana: `business_connection_id` String/Text PK, `user_id` BigInteger, `user_chat_id` BigInteger nullable, `is_enabled` Boolean, `created_at` DateTime(tz) server_default now.
  - `models/__init__.py` — exportar `BusinessConnection` en imports + `__all__` (no estaba en el plan; necesario para coherencia del paquete y metadata).
  - `alembic/versions/20260815_business_connections.py` — `revision="20260815_business_connections"`, `down_revision="20260629_user_chat_id"`, `op.create_table` / `op.drop_table`. Estilo de `20260629_add_pending_request_user_chat_id.py` (mismo rev slug legible).
  - `handlers/business_connection_handlers.py` (CREATE) — `Router()`, `@router.business_connection()`, delega upsert a 1 service, log `business_connection_enabled/disabled`.
  - `handlers/__init__.py` — import + `__all__` del nuevo router.
  - `bot.py` — import del router (bloque L21-68), `dp.include_router(...)` (junto a L325-370); import `EVENT_VIP_KICKED` (L79); registro `get_event_bus().register(EVENT_VIP_KICKED, on_vip_kicked)` al TOPE de `on_startup` (ANTES de L213); emit en el branch de ban de `check_expired_subscriptions_on_startup` (L184-186, dentro de `if user and channel:`).
  - `services/event_bus.py` — `EVENT_VIP_KICKED: str = "vip_kicked"` (junto a L26).
  - `services/link_notifier.py` (CREATE) — `LinkNotifier` + adapter module-level `on_vip_kicked(payload)`; bot lazy PROPIO (no reusar `_bot_token` del scheduler); best-effort try/except; logging `link_notifier | ... | user_id= | resultado=`.
  - `services/vip_service.py` — import `EVENT_VIP_KICKED` (L17); emit post-DM en branch "kicked" (L1055-1059, antes del return L1064): `schedule_emit(get_event_bus().emit(EVENT_VIP_KICKED, {...}))` con `reason="admin_revoke"`, `user_id=subscription.user_id`, `username=user.username`, `channel_id=channel.channel_id`, `channel_name=channel.channel_name`.
  - `services/scheduler_service.py` — import del bus; emit tras L231 (branch único de ban L218), `reason="expired"`, user L225, channel L199.
  - `services/__init__.py` — export `EVENT_VIP_KICKED`.
  - `.env.example` — documentar `FEATURE_LINK_ENABLED` y `LINK_CHAT_ID`.
- **No touch (ajenos al ítem, cambios sin commitear):** `CLAUDE.md`, `tests/handlers/test_broadcast_handlers.py`, `.planning/HARDENING_ROADMAP.md`, `.claude/agents/documentador.md`, `.planning/quick/20260706-reaction-ecosystem-week3-tight/` (untracked), `.critical_tests_stats.json`.

## Ready for chain

Handoff a gsd-planner con scope tight (A1-A5), las 3 correcciones R1/R2/R3 resueltas, y el test list de arriba. Contrato de seguridad: flag OFF = cero comportamiento nuevo; los 3 hooks emiten SOLO en ban real (no `deactivated_only`/`channel_inactive`/`not_found`); notifier best-effort "MUST NOT break kick flow"; handlers 1 service, funciones ≤50 líneas, logging `módulo | acción | user_id | resultado`, sin voseo en textos nuevos.
