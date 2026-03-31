"""
Servicio Scheduler - Lucien Bot

Gestiona los temporizadores para aprobaciones automáticas y recordatorios.
Usa APScheduler con SQLAlchemyJobStore para persistencia de jobs.
"""
from datetime import datetime
from aiogram import Bot
from models.database import SessionLocal
from models.models import ChannelType
from services.backup_service import BackupService
from services.channel_service import ChannelService
from services.vip_service import VIPService
from services.user_service import UserService
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    """Servicio de tareas programadas usando APScheduler."""

    def __init__(self, bot: Bot):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        from apscheduler.executors.asyncio import AsyncIOExecutor
        from config.settings import bot_config

        self.bot = bot
        self.running = False
        self._scheduler = None

        # Configure job stores (using existing database as job store)
        jobstores = {
            "default": SQLAlchemyJobStore(url=bot_config.DATABASE_URL)
        }
        executors = {
            "default": AsyncIOExecutor()
        }
        job_defaults = {
            "coalesce": True,
            "max_instances": 1,
            "replace_existing": True,
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=bot_config.TIMEZONE,
        )

    async def start(self):
        """Inicia el scheduler registrando jobs y arrancando."""
        if self.running:
            return

        # Register jobs with cron schedules
        self._scheduler.add_job(
            self._process_pending_requests,
            trigger="cron",
            hour=9, minute=0,
            id="approve_join_requests",
            name="Approve pending join requests",
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._process_expiring_subscriptions,
            trigger="cron",
            hour=8, minute=0,
            id="expiry_reminders",
            name="Send VIP expiry reminders",
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._process_expired_subscriptions,
            trigger="cron",
            hour=0, minute=5,
            id="expire_subscriptions",
            name="Process expired VIP subscriptions",
            replace_existing=True,
        )
        # Backup job: runs daily at 3 AM
        self._scheduler.add_job(
            self._run_backup_job,
            trigger="cron",
            hour=3, minute=0,
            id="daily_backup",
            name="Daily database backup",
            replace_existing=True,
        )

        self._scheduler.start()
        self.running = True
        logger.info("Scheduler started (APScheduler + SQLAlchemyJobStore)")

    async def stop(self):
        """Detiene el scheduler."""
        if not self.running:
            return
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self.running = False
        logger.info("Scheduler stopped")

    async def _run_backup_job(self):
        """Ejecuta backup de base de datos."""
        try:
            backup_service = BackupService()
            result = await backup_service.daily_backup()
            if result:
                logger.info(f"Backup completed: {result}")
            else:
                logger.warning("Backup failed -- check logs")
        except Exception as e:
            logger.error(f"Error running backup: {e}")

    async def _process_pending_requests(self):
        """Procesa solicitudes pendientes listas para aprobar"""
        db = SessionLocal()
        try:
            channel_service = ChannelService(db)
            ready_requests = channel_service.get_ready_to_approve()

            for request in ready_requests:
                try:
                    channel = request.channel
                    if not channel or not channel.is_active:
                        continue

                    # Aprobar solicitud en Telegram
                    await self.bot.approve_chat_join_request(
                        chat_id=channel.channel_id,
                        user_id=request.user_id
                    )

                    # Actualizar estado en BD
                    request.status = "approved"
                    request.approved_at = datetime.utcnow()
                    db.commit()

                    # Notificar al usuario
                    await self.bot.send_message(
                        chat_id=request.user_id,
                        text=LucienVoice.free_access_approved(channel.channel_name),
                        parse_mode="HTML"
                    )

                    logger.info(f"Solicitud aprobada: user={request.user_id}, channel={channel.channel_id}")

                except Exception as e:
                    logger.error(f"Error aprobando solicitud {request.id}: {e}")
                    db.rollback()

        finally:
            db.close()

    async def _process_expiring_subscriptions(self):
        """Envía recordatorios de suscripciones por vencer"""
        db = SessionLocal()
        try:
            vip_service = VIPService(db)
            expiring = vip_service.get_expiring_subscriptions(hours=24)

            for subscription in expiring:
                try:
                    # Enviar recordatorio
                    await self.bot.send_message(
                        chat_id=subscription.user_id,
                        text=LucienVoice.vip_renewal_reminder(subscription.end_date),
                        parse_mode="HTML"
                    )

                    # Marcar como recordatorio enviado
                    subscription.reminder_sent = True
                    db.commit()

                    logger.info(f"Recordatorio enviado: subscription={subscription.id}")

                except Exception as e:
                    logger.error(f"Error enviando recordatorio {subscription.id}: {e}")
                    db.rollback()

        finally:
            db.close()

    async def _process_expired_subscriptions(self):
        """Procesa suscripciones vencidas"""
        db = SessionLocal()
        try:
            vip_service = VIPService(db)
            expired = vip_service.get_expired_subscriptions()

            for subscription in expired:
                try:
                    channel = subscription.channel
                    if not channel or not channel.is_active:
                        continue

                    # Expulsar usuario del canal VIP
                    await self.bot.ban_chat_member(
                        chat_id=channel.channel_id,
                        user_id=subscription.user_id
                    )

                    # Desbanear para permitir reingreso futuro
                    await self.bot.unban_chat_member(
                        chat_id=channel.channel_id,
                        user_id=subscription.user_id
                    )

                    # Desactivar suscripción
                    subscription.is_active = False
                    db.commit()

                    # Notificar al usuario
                    await self.bot.send_message(
                        chat_id=subscription.user_id,
                        text=LucienVoice.vip_expired(),
                        parse_mode="HTML"
                    )

                    logger.info(f"Suscripción expirada: subscription={subscription.id}")

                except Exception as e:
                    logger.error(f"Error expirando suscripción {subscription.id}: {e}")
                    db.rollback()

        finally:
            db.close()


# Instancia global del scheduler
_scheduler_instance: SchedulerService = None


def get_scheduler(bot: Bot = None) -> SchedulerService:
    """Obtiene o crea la instancia del scheduler"""
    global _scheduler_instance
    if _scheduler_instance is None and bot is not None:
        _scheduler_instance = SchedulerService(bot)
    return _scheduler_instance
