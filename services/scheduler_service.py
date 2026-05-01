"""
Servicio Scheduler - Lucien Bot

Gestiona los temporizadores para aprobaciones automáticas y recordatorios.
Usa APScheduler con SQLAlchemyJobStore para persistencia de jobs.

Los job handlers son funciones de módulo (no métodos) para evitar errores
de serialización con APScheduler + SQLAlchemyJobStore:
  1. _get_bot() lazily crea el Bot para evitar "cannot pickle SSLContext"
  2. Funciones de módulo (no bound methods) para evitar que APScheduler
     detecte ciclos de serialización en self._scheduler
"""
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from aiogram.types import BotCommandScopeAllPrivateChats
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from models.database import SessionLocal
from models.models import ChannelType
from services.backup_service import BackupService
from services.channel_service import ChannelService
from services.vip_service import VIPService
from services.user_service import UserService
from utils.lucien_voice import LucienVoice
from keyboards.inline_keyboards import social_links_keyboard
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Bot lazily-created para evitar errores de pickling con APScheduler.
# aiogram.Bot contiene SSLContext que no es serializable.
# ─────────────────────────────────────────────────────────────────────────────
_bot_token: str | None = None
_bot_instance: Bot | None = None


def _get_bot() -> Bot:
    """Crea o retorna el bot lazily. Solo se invoca en runtime del job."""
    global _bot_instance, _bot_token
    if _bot_instance is None and _bot_token is not None:
        _bot_instance = Bot(token=_bot_token)
    if _bot_instance is None:
        raise RuntimeError("Bot no inicializado en scheduler")
    return _bot_instance


# ─────────────────────────────────────────────────────────────────────────────
# Job handlers como funciones de módulo (NO métodos de instancia).
# Esto evita que APScheduler intente picklear self._scheduler.
# ─────────────────────────────────────────────────────────────────────────────

async def _run_backup_job():
    """Ejecuta backup de base de datos (llamado por APScheduler)."""
    try:
        backup_service = BackupService()
        result = await backup_service.daily_backup()
        if result:
            logger.info(f"Backup completed: {result}")
        else:
            logger.warning("Backup failed -- check logs")
    except Exception as e:
        logger.error(f"Error running backup: {e}")


async def _send_free_welcome_job(user_id: int, channel_id: int):
    """Envía el mensaje ritual de entrada al canal Free tras 30s de espera.

    Job handler de módulo para evitar errores de serialización con APScheduler.
    """
    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        channel = channel_service.get_channel_by_id(channel_id)

        if not channel or not channel.is_active:
            logger.warning(f"Canal {channel_id} no encontrado o inactivo para welcome job")
            return

        bot = _get_bot()

        await bot.send_message(
            chat_id=user_id,
            text=LucienVoice.free_entry_ritual(channel.channel_name or "Los Kinkys"),
            parse_mode="HTML",
            reply_markup=social_links_keyboard()
        )

        logger.info(f"Mensaje ritual enviado: user={user_id}, channel={channel_id}")

    except Exception as e:
        logger.error(f"Error enviando mensaje ritual a user={user_id}: {e}")
    finally:
        db.close()


async def _process_pending_requests():
    """Procesa solicitudes pendientes listas para aprobar (llamado por APScheduler)."""
    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        ready_requests = channel_service.get_ready_to_approve()
        bot = _get_bot()

        for request in ready_requests:
            try:
                channel = request.channel
                if not channel or not channel.is_active:
                    continue

                await bot.approve_chat_join_request(
                    chat_id=channel.channel_id,
                    user_id=request.user_id
                )

                request.status = "approved"
                request.approved_at = datetime.utcnow()
                db.commit()

                # Enviar mensaje de bienvenida directamente.
                # NOTA: El webhook handle_member_join NO se dispara cuando el bot
                # aprueba via API (el evento tiene from_user=bot, no el usuario).
                # Para aprobaciones manuales por custodio sí funciona el webhook.
                try:
                    message = LucienVoice.free_entry_welcome(channel.channel_name or "Los Kinkys")
                    if channel.invite_link:
                        message += f"\n{channel.invite_link}"
                    await bot.send_message(
                        chat_id=request.user_id,
                        text=message,
                        parse_mode="HTML",
                        reply_markup=social_links_keyboard()
                    )
                    logger.info(f"Mensaje bienvenida enviado a user={request.user_id} tras aprobacion automatica")
                except Exception as e:
                    logger.error(f"Error enviando bienvenida a user={request.user_id}: {e}")

                logger.info(f"Solicitud aprobada: user={request.user_id}, channel={channel.channel_id}")

            except Exception as e:
                logger.error(f"Error aprobando solicitud {request.id}: {e}")
                db.rollback()

    finally:
        db.close()


async def _process_expiring_subscriptions():
    """Envía recordatorios de suscripciones por vencer (llamado por APScheduler)."""
    db = SessionLocal()
    try:
        vip_service = VIPService(db)
        expiring = vip_service.get_expiring_subscriptions(hours=24)
        bot = _get_bot()

        for subscription in expiring:
            try:
                await bot.send_message(
                    chat_id=subscription.user_id,
                    text=LucienVoice.vip_renewal_reminder(subscription.end_date),
                    parse_mode="HTML"
                )

                subscription.reminder_sent = True
                db.commit()

                logger.info(f"Recordatorio enviado: subscription={subscription.id}")

            except Exception as e:
                logger.error(f"Error enviando recordatorio {subscription.id}: {e}")
                db.rollback()

    finally:
        db.close()


async def _process_expired_subscriptions():
    """Procesa suscripciones vencidas (llamado por APScheduler)."""
    db = SessionLocal()
    try:
        vip_service = VIPService(db)
        expired = vip_service.get_expired_subscriptions()
        bot = _get_bot()

        for subscription in expired:
            try:
                # ── FIX: Check if user has ANY other active subscription ──
                other_active = db.query(Subscription).filter(
                    Subscription.user_id == subscription.user_id,
                    Subscription.id != subscription.id,
                    Subscription.is_active == True,
                    Subscription.end_date > datetime.utcnow()
                ).first()

                if other_active:
                    # User has other active subscription - skip expulsion
                    subscription.is_active = False
                    db.commit()
                    logger.info(f"[Scheduler] User has other active sub, skipping expulsion: user_id={subscription.user_id}, expired_sub_id={subscription.id}")
                    continue

                channel = subscription.channel
                if not channel or not channel.is_active:
                    continue

                await bot.ban_chat_member(
                    chat_id=channel.channel_id,
                    user_id=subscription.user_id
                )
                await bot.unban_chat_member(
                    chat_id=channel.channel_id,
                    user_id=subscription.user_id
                )

                subscription.is_active = False
                db.commit()

                await bot.send_message(
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


async def _sync_question_sets():
    """Sincroniza el question set activo basándose en promociones activas.

    Busca la promoción activa más reciente con question_set_id asignado,
    actualiza GameService._active_question_set_path y limpia el caché de
    instancias existentes para forzar recarga.
    """
    from datetime import datetime, timezone
    from models.models import Promotion, PromotionStatus, QuestionSet
    from services.game_service import GameService

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # 0. Prioridad: Verificar si hay un override manual activo
        override_set = db.query(QuestionSet).filter(QuestionSet.is_override == True).first()
        if override_set:
            if GameService._active_question_set_path != override_set.file_path:
                logger.info(f"[Scheduler] Manteniendo override manual: {override_set.name}")
                GameService._active_question_set_path = override_set.file_path
                GameService._active_question_set_vip_path = None
            return

        # 1. Buscar promociones activas con set de preguntas
        promotion = db.query(Promotion).filter(
            Promotion.status == PromotionStatus.ACTIVE,
            Promotion.question_set_id.isnot(None),
            Promotion.is_active == True
        ).order_by(Promotion.start_date.desc().nullslast()).first()

        # 2. Filter to only those currently in their date range (NULL dates = always available)
        active_promotion = None
        if promotion:
            # NULL start_date = immediately available; NULL end_date = never expires
            is_started = promotion.start_date is None or promotion.start_date <= now
            is_not_expired = promotion.end_date is None or promotion.end_date >= now
            if is_started and is_not_expired:
                active_promotion = promotion
            else:
                active_promotion = None

        if active_promotion and active_promotion.question_set_id:
            question_set = db.query(QuestionSet).filter(
                QuestionSet.id == active_promotion.question_set_id
            ).first()

            if question_set:
                new_path = question_set.file_path
                old_path = GameService._active_question_set_path

                if old_path != new_path:
                    logger.info(
                        f"[Scheduler] Activating question set from promotion "
                        f"id={active_promotion.id} '{active_promotion.name}': "
                        f"file_path={new_path}"
                    )
                    GameService._active_question_set_path = new_path
                    GameService._active_question_set_vip_path = None  # VIP uses default

                # Update DB state: this QuestionSet is active, others are not
                db.query(QuestionSet).filter(
                    QuestionSet.id != question_set.id,
                    QuestionSet.is_active == True,
                    QuestionSet.is_override == False
                ).update({QuestionSet.is_active: False})

                if not question_set.is_active:
                    question_set.is_active = True

                db.commit()
                logger.info(f"[Scheduler] QuestionSet id={question_set.id} sincronizado como activo")
            else:
                logger.warning(
                    f"[Scheduler] Promotion id={active_promotion.id} has question_set_id="
                    f"{active_promotion.question_set_id} but QuestionSet not found"
                )
        else:
            # No active promotion - reset to default
            default_path = "docs/preguntas.json"
            if GameService._active_question_set_path != default_path:
                logger.info("[Scheduler] No active promotion, resetting question set to default")
                GameService._active_question_set_path = default_path
                GameService._active_question_set_vip_path = None

    except Exception as e:
        logger.error(f"[Scheduler] Error syncing question sets: {e}")
        db.rollback()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# SchedulerService — solo maneja el ciclo de vida de APScheduler
# ─────────────────────────────────────────────────────────────────────────────

class SchedulerService:
    """Gestiona APScheduler con SQLAlchemyJobStore. No contiene lógica de jobs."""

    def __init__(self, bot: Bot):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        from apscheduler.executors.asyncio import AsyncIOExecutor
        from config.settings import bot_config

        global _bot_token
        _bot_token = bot.token  # Guardar solo el token (string -> picklable)

        self.running = False
        self._scheduler = None

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
        """Registra jobs y arranca el scheduler."""
        if self.running:
            return

        self._scheduler.add_job(
            _process_pending_requests,
            trigger=IntervalTrigger(seconds=30),
            id="approve_join_requests",
            name="Approve pending join requests",
            replace_existing=True,
        )
        self._scheduler.add_job(
            _process_expiring_subscriptions,
            trigger="cron",
            hour=8, minute=0,
            id="expiry_reminders",
            name="Send VIP expiry reminders",
            replace_existing=True,
        )
        self._scheduler.add_job(
            _process_expired_subscriptions,
            trigger="cron",
            hour=0, minute=5,
            id="expire_subscriptions",
            name="Process expired VIP subscriptions",
            replace_existing=True,
        )
        self._scheduler.add_job(
            _run_backup_job,
            trigger="cron",
            hour=3, minute=0,
            id="daily_backup",
            name="Daily database backup",
            replace_existing=True,
        )
        self._scheduler.add_job(
            _sync_question_sets,
            trigger=IntervalTrigger(minutes=1),
            id="sync_question_sets",
            name="Sync active question set from promotions",
            replace_existing=True,
        )

        self._scheduler.start()
        self.running = True
        logger.info("Scheduler started (APScheduler + SQLAlchemyJobStore)")

    def schedule_free_welcome(self, user_id: int, channel_id: int):
        """Programa el mensaje ritual de entrada con 30s de delay.

        Usa DateTrigger para un job one-shot que se ejecuta 30 segundos
        después de la solicitud de unión al canal Free.
        """
        job_id = f"free_welcome_{user_id}_{channel_id}"
        run_date = datetime.now(timezone.utc) + timedelta(seconds=30)
        self._scheduler.add_job(
            _send_free_welcome_job,
            trigger=DateTrigger(run_date=run_date),
            id=job_id,
            replace_existing=True,
            kwargs={"user_id": user_id, "channel_id": channel_id},
        )
        logger.info(f"Scheduled free welcome job: user={user_id}, channel={channel_id}, run_at={run_date}")

    async def stop(self):
        """Detiene el scheduler."""
        if not self.running:
            return
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self.running = False
        logger.info("Scheduler stopped")


# ─────────────────────────────────────────────────────────────────────────────
# Instancia global
# ─────────────────────────────────────────────────────────────────────────────
_scheduler_instance: SchedulerService | None = None


def get_scheduler(bot: Bot | None = None) -> SchedulerService | None:
    """Obtiene o crea la instancia del scheduler."""
    global _scheduler_instance
    if _scheduler_instance is None and bot is not None:
        _scheduler_instance = SchedulerService(bot)
    return _scheduler_instance
