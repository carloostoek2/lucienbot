"""
🎩 Lucien Bot - Guardián de los Secretos de Diana

Bot de Telegram para gestión de canales Free y VIP.
"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

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
    reward_admin_router
)

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


async def on_startup(bot: Bot):
    """Acciones al iniciar el bot"""
    logger.info("Iniciando Lucien Bot...")
    
    # Inicializar base de datos
    init_db()
    logger.info("Base de datos inicializada")
    
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
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
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
