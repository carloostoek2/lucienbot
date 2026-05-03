"""
🎩 Lucien Bot - Guardián de los Secretos de Diana

Bot de Telegram para gestión de canales Free y VIP.
"""
import asyncio
import logging
import os
import sys
from datetime import timedelta
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from redis.asyncio import Redis

from config.settings import bot_config
from models.database import init_db
from services.scheduler_service import get_scheduler
from handlers import (
    common_router,
    admin_router,
    channel_router,
    vip_router,
    free_channel_router,
    # Fase 1 - Gamificacion
    gamification_user_router,
    gamification_admin_router,
    broadcast_router,
    # Fase 2 - Paquetes
    package_router,
    # Fase 3 - Misiones y Recompensas
    mission_user_router,
    mission_admin_router,
    reward_admin_router,
    reward_user_router,
    # Fase 4 - Tienda
    store_user_router,
    store_admin_router,
    # Fase 5 - Promociones
    promotion_user_router,
    promotion_admin_router,
    # Fase 6 - Narrativa
    story_user_router,
    story_admin_router,
    # Phase 9 - Analytics
    analytics_router,
    # Phase 12 - Mensajes Anónimos VIP
    vip_user_router,
    anonymous_message_admin_router,
    # Phase 12 - Categorías de Tienda
    category_admin_handlers,
    # Phase 14 - Minijuegos
    game_user_router,
    # Phase 16 - Trivia Discount
    trivia_discount_admin_router,
    # Phase 17 - Question Sets
    question_set_admin_router,
    # Phase 15 - Mochila
    backpack_router,
)

from handlers.rate_limit_middleware import ThrottlingMiddleware
from handlers.chat_action_middleware import ChatActionMiddleware

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('lucien_bot.log', encoding='utf-8')
    ]
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
        logger.warning("REDIS_URL not set -- FSM state will not persist across restarts (using MemoryStorage)")
    return MemoryStorage()


from services.vip_service import VIPService


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
                # Desactivar la suscripción
                vip_service.expire_subscription(subscription.id)

                # Obtener información del usuario
                user = subscription.user
                channel = subscription.channel

                if user and channel:
                    # Intentar remover al usuario del canal VIP
                    try:
                        await bot.ban_chat_member(
                            chat_id=channel.channel_id,
                            user_id=user.telegram_id
                        )
                        # Desbanear inmediatamente para permitir que vuelva con un nuevo token
                        await bot.unban_chat_member(
                            chat_id=channel.channel_id,
                            user_id=user.telegram_id
                        )
                        logger.info(f"Usuario {user.telegram_id} removido del canal VIP {channel.channel_id}")
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
    
    # Notificar a administradores
    for admin_id in bot_config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text="🎩 <b>Lucien:</b>\n\n"
                     "<i>El guardián de los secretos ha despertado...</i>\n\n"
                     "✅ <b>Bot iniciado correctamente.</b>",
                parse_mode=ParseMode.HTML
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
    
    # Notificar a administradores
    for admin_id in bot_config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text="🎩 <b>Lucien:</b>\n\n"
                     "<i>El guardián descansa...</i>\n\n"
                     "⏹ <b>Bot detenido.</b>",
                parse_mode=ParseMode.HTML
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

    # Middlewares globales - indication de "escribiendo..." mientras se procesa
    dp.message.middleware(ChatActionMiddleware())
    dp.callback_query.middleware(ChatActionMiddleware())

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
    # Phase 16 - Trivia Discount
    dp.include_router(trivia_discount_admin_router)
    # Phase 17 - Question Sets
    dp.include_router(question_set_admin_router)
    # Phase 15 - Mochila
    dp.include_router(backpack_router)

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
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
