"""
🎩 Lucien Bot - Guardián de los Secretos de Diana

Bot de Telegram para gestión de canales Free y VIP.
"""

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from redis.asyncio import Redis

from config.settings import bot_config
from handlers import (
    admin_router,
    # Phase 9 - Analytics
    analytics_router,
    anonymous_message_admin_router,
    # Phase 15 - Mochila
    backpack_router,
    broadcast_router,
    # Phase 12 - Categorías de Tienda
    category_admin_handlers,
    channel_router,
    common_router,
    free_channel_router,
    # Phase 14 - Minijuegos
    game_user_router,
    gamification_admin_router,
    # Fase 1 - Gamificacion
    gamification_user_router,
    mission_admin_router,
    # Fase 3 - Misiones y Recompensas
    mission_user_router,
    # Nurture admin config
    nurture_admin_router,
    # Fase 2 - Paquetes
    package_router,
    promotion_admin_router,
    # Fase 5 - Promociones
    promotion_user_router,
    reward_admin_router,
    reward_user_router,
    store_admin_router,
    # Fase 4 - Tienda
    store_user_router,
    story_admin_router,
    # Fase 6 - Narrativa
    story_user_router,
    # Phase 16 - Trivias Especiales
    trivia_admin_router,
    # Configuracion de Trivias
    trivia_config_admin_router,
    # Phase 17 - Promociones por Racha
    trivia_streak_admin_router,
    vip_router,
    # Phase 12 - Mensajes Anónimos VIP
    vip_user_router,
)

# Health/observability (Item 11 spike) - optional endpoint starter (aiohttp + HEALTH_ENABLED)
from health_server import start_health_http_server, stop_health_http_server
from middlewares.error_handler import ErrorHandlerMiddleware
from middlewares.idempotency import IdempotencyMiddleware
from middlewares.rate_limiter import ThrottlingMiddleware
from models.database import init_db
from services.broadcast_service import on_besitos_awarded_broadcast_reaction_observer

# InternalEventBus (PoC Item 1) + first listener (narrative domain)
from services.event_bus import EVENT_BESITOS_AWARDED, EVENT_VIP_ACTIVATED, get_event_bus
from services.game_service import on_besitos_awarded_game_award_observer
from services.nurture_service import on_vip_activated
from services.reward_service import on_besitos_awarded_rewards_observer
from services.scheduler_service import get_scheduler
from services.store_service import on_besitos_awarded_store_observer
from services.story_service import on_besitos_awarded_from_gamification
from services.vip_service import VIPService

# Bot start time (Item 11 / observability-health). Captured as early as possible in the
# process entrypoint so health checks can report real uptime instead of always "degraded".
# Lazy-imported by health_service.check_bot_runtime (avoids circular import with health_server wiring).
_BOT_START_TIME: datetime | None = None

# Configurar logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("lucien_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def create_storage():
    """
    Create FSM storage based on environment.

    Uses RedisStorage when REDIS_URL is set (production/Redis available).
    Falls back to MemoryStorage for local dev without Redis.
    """
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            redis_client = Redis.from_url(redis_url)
            storage = RedisStorage(
                redis=redis_client,
                key_builder=DefaultKeyBuilder(with_bot_id=True),
                state_ttl=timedelta(days=1),
                data_ttl=timedelta(days=1),
            )
            logger.info("FSM storage: RedisStorage (state will persist across restarts)")
            return storage
        except Exception as e:
            logger.warning(f"Redis connection failed ({e}) -- falling back to MemoryStorage")
    else:
        logger.warning(
            "REDIS_URL not set -- FSM state will not persist across restarts (using MemoryStorage)"
        )
    return MemoryStorage()


async def check_expired_subscriptions_on_startup(bot: Bot):
    """
    Verifica y procesa suscripciones expiradas al iniciar el bot.
    Esto maneja casos donde el bot estuvo offline y no procesó expiraciones.
    """
    logger.info("Verificando suscripciones expiradas...")
    vip_service = VIPService()

    try:
        expired_subscriptions = vip_service.get_expired_subscriptions()

        if not expired_subscriptions:
            logger.info("No hay suscripciones expiradas pendientes")
            return

        logger.info(f"Encontradas {len(expired_subscriptions)} suscripciones expiradas")

        for subscription in expired_subscriptions:
            try:
                # Verificar si el usuario tiene otra suscripción activa antes de expulsar
                if vip_service.has_other_active_subscription(subscription.user_id, subscription.id):
                    vip_service.expire_subscription(subscription.id)
                    logger.info(
                        f"Suscripción {subscription.id} expirada pero usuario tiene otra activa: "
                        f"user_id={subscription.user_id}"
                    )
                    continue

                # Desactivar la suscripción
                vip_service.expire_subscription(subscription.id)

                # Limpiar estado VIP del usuario (consistente con _process_expired_subscriptions)
                user = subscription.user
                if user and user.vip_entry_status is not None:
                    vip_service.clear_vip_entry_state(user.telegram_id)
                    logger.info(f"VIP entry state cleared on startup: user_id={user.telegram_id}")

                # Obtener información del usuario
                channel = subscription.channel

                if user and channel:
                    # Intentar remover al usuario del canal VIP
                    try:
                        await bot.ban_chat_member(
                            chat_id=channel.channel_id, user_id=user.telegram_id
                        )
                        # Desbanear inmediatamente para permitir que vuelva con un nuevo token
                        await bot.unban_chat_member(
                            chat_id=channel.channel_id, user_id=user.telegram_id
                        )
                        logger.info(
                            f"Usuario {user.telegram_id} removido del canal VIP {channel.channel_id}"
                        )
                    except Exception as e:
                        logger.error(f"Error removiendo usuario {user.telegram_id} del canal: {e}")

            except Exception as e:
                logger.error(f"Error procesando suscripción expirada {subscription.id}: {e}")

        logger.info("Procesamiento de suscripciones expiradas completado")

    except Exception as e:
        logger.error(f"Error verificando suscripciones expiradas: {e}")
    finally:
        vip_service.close()


async def on_startup(bot: Bot):
    """Acciones al iniciar el bot"""
    logger.info("Iniciando Lucien Bot...")

    # Inicializar base de datos
    init_db()
    logger.info("Base de datos inicializada")

    # Verificar suscripciones expiradas (maneja casos donde bot estuvo offline)
    await check_expired_subscriptions_on_startup(bot)

    # Iniciar scheduler
    scheduler = get_scheduler(bot)
    await scheduler.start()
    logger.info("Scheduler iniciado")

    # Cross-domain listeners (explicit, central, no import side-effects).
    # Fase 3 of eventbus-poc + Item 5 + Item 6 + Item 10 store: narrative + rewards + broadcast + game + store domains.
    get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_from_gamification)
    get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_rewards_observer)
    get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_broadcast_reaction_observer)
    get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_game_award_observer)
    get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_store_observer)
    # Nurture / lifecycle: VIP activation triggers per-user sequence enrollment + scheduling (no batch)
    get_event_bus().register(EVENT_VIP_ACTIVATED, on_vip_activated)
    logger.info(
        "Event listeners registrados (besitos_awarded -> narrative, rewards, broadcast, game, store; vip_activated -> nurture)"
    )

    # Health/observability (Item 11 spike)
    # Start optional /health JSON endpoint on separate port (non-blocking, fire-and-forget).
    # Requires HEALTH_ENABLED=1 and aiohttp installed; otherwise logs and skips gracefully.
    # 0 breakage to aiogram polling or critical listeners/scheduler.
    try:
        if os.getenv("HEALTH_ENABLED") == "1":
            port = int(os.getenv("HEALTH_PORT", "8080"))
            asyncio.create_task(start_health_http_server(port=port))
            logger.info(
                f"health_service | startup_endpoint | user_id=0 | result=starting port={port}"
            )
        logger.info("health_service | startup_checks_available | user_id=0 | result=ready")
    except Exception as e:
        logger.warning(f"health_service | startup_endpoint | user_id=0 | result=error {e}")

    # Notificar a administradores
    for admin_id in bot_config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text="🎩 <b>Lucien:</b>\n\n"
                "<i>El guardián de los secretos ha despertado...</i>\n\n"
                "✅ <b>Bot iniciado correctamente.</b>",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(f"No se pudo notificar al admin {admin_id}: {e}")

    logger.info("Lucien Bot iniciado correctamente")


async def on_shutdown(bot: Bot):
    """Acciones al detener el bot"""
    logger.info("Deteniendo Lucien Bot...")

    # Detener scheduler
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.stop()

    # Health endpoint stop (Item 11, if was started)
    try:
        await stop_health_http_server()
    except Exception as e:
        logger.warning(f"health_service | shutdown_endpoint | user_id=0 | result=error {e}")

    # Notificar a administradores
    for admin_id in bot_config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text="🎩 <b>Lucien:</b>\n\n"
                "<i>El guardián descansa...</i>\n\n"
                "⏹ <b>Bot detenido.</b>",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(f"No se pudo notificar al admin {admin_id}: {e}")

    logger.info("Lucien Bot detenido")


async def main():
    """Función principal"""
    # Validar configuración
    if not bot_config.TOKEN:
        logger.error("BOT_TOKEN no configurado. Cree un archivo .env con BOT_TOKEN=your_token")
        sys.exit(1)

    if not bot_config.ADMIN_IDS:
        logger.warning("ADMIN_IDS no configurado. El panel de administración no estará disponible.")

    # Crear bot y dispatcher
    bot = Bot(token=bot_config.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = create_storage()
    dp = Dispatcher(storage=storage)

    # Middlewares registration order (gsd-mw-hardening plan, section 4 + 8):
    # ErrorHandler as *outer* (catches exceptions from all inner mws + handlers)
    # IdempotencyMiddleware for callback_query only (central dedup of TG CB retries)
    # ThrottlingMiddleware for callback_query (after idemp so duplicate retries do not consume rate quota)
    # ThrottlingMiddleware for messages
    # This order: Error outer → Idempotency (cb) → Throttling (cb); Throttling (messages)
    dp.message.outer_middleware(ErrorHandlerMiddleware())
    dp.callback_query.outer_middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(IdempotencyMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.message.middleware(ThrottlingMiddleware())

    # Registrar routers
    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(channel_router)
    dp.include_router(vip_router)
    dp.include_router(free_channel_router)
    # Fase 1 - Gamificacion
    dp.include_router(gamification_user_router)
    dp.include_router(gamification_admin_router)
    dp.include_router(broadcast_router)
    # Fase 2 - Paquetes
    dp.include_router(package_router)
    # Nurture / Lifecycle (admin config only)
    dp.include_router(nurture_admin_router)
    # Fase 3 - Misiones y Recompensas
    dp.include_router(mission_user_router)
    dp.include_router(mission_admin_router)
    dp.include_router(reward_admin_router)
    dp.include_router(reward_user_router)
    # Fase 4 - Tienda
    dp.include_router(store_user_router)
    dp.include_router(store_admin_router)
    # Fase 5 - Promociones
    dp.include_router(promotion_user_router)
    dp.include_router(promotion_admin_router)
    # Fase 6 - Narrativa
    dp.include_router(story_user_router)
    dp.include_router(story_admin_router)
    # Phase 9 - Analytics
    dp.include_router(analytics_router)
    # Phase 12 - Mensajes Anónimos VIP
    dp.include_router(vip_user_router)
    dp.include_router(anonymous_message_admin_router)
    # Phase 12 - Categorías de Tienda
    dp.include_router(category_admin_handlers.router)
    # Phase 14 - Minijuegos
    dp.include_router(game_user_router)
    # Phase 15 - Mochila
    dp.include_router(backpack_router)
    # Phase 16 - Trivias Especiales
    dp.include_router(trivia_admin_router)
    # Phase 17 - Promociones por Racha
    dp.include_router(trivia_streak_admin_router)
    # Configuracion de Trivias
    dp.include_router(trivia_config_admin_router)

    # Configurar eventos de startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Iniciar polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error en polling: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        # Capture start time as early as possible (before asyncio.run / polling) for health/runtime checks.
        # This makes check_bot_runtime return "ok" with real uptime (instead of the previous always-degraded path).
        _BOT_START_TIME = datetime.now(UTC)
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
