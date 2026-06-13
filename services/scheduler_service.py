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

import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from keyboards.inline_keyboards import social_links_keyboard
from models.database import SessionLocal
from services.backup_service import BackupService
from services.channel_service import ChannelService
from services.package_service import PackageService
from services.streak_scheduler_bridge import activate_streak_promotion, deactivate_streak_promotion
from services.vip_service import VIPService
from utils.lucien_voice import LucienVoice

# Nurture (loaded inside job to avoid import cycles at module load)
# from models.models import NurtureSequence, NurtureStep, UserNurtureProgress
# from services.nurture_service import NurtureService
# from services.package_service import PackageService

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
            reply_markup=social_links_keyboard(),
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
                    chat_id=channel.channel_id, user_id=request.user_id
                )

                request.status = "approved"
                request.approved_at = datetime.now(UTC)
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
                        reply_markup=social_links_keyboard(),
                    )
                    logger.info(
                        f"Mensaje bienvenida enviado a user={request.user_id} tras aprobacion automatica"
                    )
                except Exception as e:
                    logger.error(f"Error enviando bienvenida a user={request.user_id}: {e}")

                logger.info(
                    f"Solicitud aprobada: user={request.user_id}, channel={channel.channel_id}"
                )

            except TelegramBadRequest as e:
                if "USER_ALREADY_PARTICIPANT" in str(e):
                    request.status = "approved"
                    request.approved_at = datetime.now(UTC)
                    db.commit()
                    logger.info(
                        f"Solicitud {request.id}: user={request.user_id} ya era participante, "
                        f"marcada como aprobada"
                    )
                else:
                    logger.error(f"Error aprobando solicitud {request.id}: {e}")
                    db.rollback()
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
                    parse_mode="HTML",
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
                channel = subscription.channel
                if not channel or not channel.is_active:
                    continue

                # Verificar si el usuario tiene otra suscripción activa en cualquier canal
                other_active = vip_service.has_other_active_subscription(
                    subscription.user_id, subscription.id
                )

                if other_active:
                    # El usuario tiene otra suscripción activa, solo marcar esta como inactiva
                    subscription.is_active = False
                    db.commit()
                    logger.info(
                        f"Suscripción {subscription.id} expirada pero usuario tiene otra activa: user_id={subscription.user_id}"
                    )
                    continue

                # Es la única suscripción del usuario: ban/unban y notificar
                await bot.ban_chat_member(chat_id=channel.channel_id, user_id=subscription.user_id)
                await bot.unban_chat_member(
                    chat_id=channel.channel_id, user_id=subscription.user_id
                )

                subscription.is_active = False

                # Limpiar estado VIP del usuario para evitar inconsistencias
                from models.models import User

                user = db.query(User).filter(User.telegram_id == subscription.user_id).first()
                if user and user.vip_entry_status is not None:
                    user.vip_entry_status = None
                    user.vip_entry_stage = None
                    logger.info(f"VIP entry state cleared: user_id={subscription.user_id}")

                db.commit()

                await bot.send_message(
                    chat_id=subscription.user_id, text=LucienVoice.vip_expired(), parse_mode="HTML"
                )

                logger.info(f"Suscripción expirada (única): subscription={subscription.id}")

            except Exception as e:
                logger.error(f"Error expirando suscripción {subscription.id}: {e}")
                db.rollback()

    finally:
        db.close()


async def _perform_nurture_content_delivery(bot, user_id: int, step, db) -> tuple[bool, str]:
    """Extracted delivery (pkg via delegate or fallback). Reduces _deliver LOC; no direct bot in main job body.
    PII: user_id (telegram) in logs + any job context; same protection as other scheduler jobs (jobstore + logs ACL).
    """
    delivered = False
    result_msg = ""
    if step.package_id:
        pkg_svc = PackageService(db)  # shares
        try:
            success, result_msg = await pkg_svc.deliver_package_to_user(
                bot, user_id, step.package_id
            )
            delivered = success
        finally:
            if hasattr(pkg_svc, "close"):
                pkg_svc.close()
    elif step.fallback_text:
        try:
            # NOTE: per security review, fallback now sent as plain text (no HTML) to prevent injection
            await bot.send_message(chat_id=user_id, text=step.fallback_text)
            delivered = True
            result_msg = "fallback sent"
        except Exception as e:
            logger.error(
                f"nurture_delivery | fallback_error | user_id={user_id} | step_id={step.id} | err={e}"
            )
            delivered = False
    return delivered, result_msg


async def _deliver_nurture_step(user_id: int, step_id: int):
    """
    Entrega un paso de nurture (job one-shot).
    Carga step/seq/progress. Idempotente (ya entregado o inactivo -> noop).
    Delega delivery rico a PackageService.deliver_package_to_user.
    Actualiza progreso post-entrega. Verifica VIP audience cuando corresponde.
    PII/jobstore: user_id/telegram_id in job execution context + logs + progress; inherits full protection of APS SQLAlchemyJobStore (same DB as main app, same backup/ACL policy as free_welcome/streak). Per-step one-shots keep volume low.
    """
    db = SessionLocal()
    try:
        from models.models import NurtureSequence, NurtureStep, UserNurtureProgress
        from services.nurture_service import NurtureService
        from services.vip_service import VIPService

        step = db.query(NurtureStep).filter(NurtureStep.id == step_id).first()
        if not step or not step.is_active:
            logger.info(
                f"nurture_delivery | skip_inactive_step | user_id={user_id} | step_id={step_id}"
            )
            return

        seq = db.query(NurtureSequence).filter(NurtureSequence.id == step.sequence_id).first()
        if not seq or not seq.is_active:
            logger.info(
                f"nurture_delivery | skip_inactive_seq | user_id={user_id} | step_id={step_id}"
            )
            return

        prog = (
            db.query(UserNurtureProgress)
            .filter(
                UserNurtureProgress.user_telegram_id == user_id,
                UserNurtureProgress.sequence_id == seq.id,
            )
            .first()
        )
        if (
            not prog
            or prog.status != "active"
            or (prog.last_step_order_delivered or 0) >= step.step_order
        ):
            logger.info(
                f"nurture_delivery | already_delivered_or_inactive | user_id={user_id} | step_id={step_id} | last={getattr(prog, 'last_step_order_delivered', 0)}"
            )
            return

        # Dignity/granularity: si audience VIP y ya no es VIP, no entregar (pero mantener progreso)
        vip_svc = VIPService(db)
        aud_val = getattr(seq.audience, "value", str(seq.audience)).lower()
        if aud_val == "vip" and not vip_svc.is_user_vip(user_id):
            logger.info(
                f"nurture_delivery | skip_non_vip | user_id={user_id} | seq_id={seq.id} | step_order={step.step_order}"
            )
            # Advance progress on skip so one-shot seq does not get stuck (M6)
            nurture_svc = NurtureService(db)
            nurture_svc.update_progress_last_delivered(user_id, seq.id, step.step_order)
            if hasattr(nurture_svc, "close"):
                nurture_svc.close()
            return

        bot = _get_bot()

        # Gate: claim the step via conditional progress update *before* delivery side-effect (R4 / S2).
        # Only deliver if this job "won" the claim (prevents dupe for co-delayed/ concurrent).
        # Advance happens on claim (or on early skips below). Keeps per-step one-shot semantics.
        nurture_svc = NurtureService(db)
        if not nurture_svc.update_progress_last_delivered(user_id, seq.id, step.step_order):
            logger.info(
                f"nurture_delivery | already_claimed_or_advanced | user_id={user_id} | step_id={step_id}"
            )
            if hasattr(nurture_svc, "close"):
                nurture_svc.close()
            return

        # We claimed it — safe to deliver (no second update needed; claim did the advance + possible completed status)
        delivered, result_msg = await _perform_nurture_content_delivery(bot, user_id, step, db)

        if delivered:
            logger.info(
                f"nurture_delivery | delivered | user_id={user_id} | seq_id={seq.id} | step_id={step_id} | order={step.step_order} | result={result_msg[:50] if result_msg else 'ok'}"
            )
        else:
            logger.warning(
                f"nurture_delivery | delivery_failed | user_id={user_id} | step_id={step_id} | msg={result_msg}"
            )
        if hasattr(nurture_svc, "close"):
            nurture_svc.close()

    except Exception as e:
        logger.error(f"nurture_delivery | error | user_id={user_id} | step_id={step_id} | err={e}")
    finally:
        db.close()


def _cleanup_expired_streak_sessions():
    """Cancela sesiones de racha expiradas que no fueron cerradas por interaccion."""
    import json
    from datetime import datetime

    from models.models import StreakPromotionCode, StreakPromotionCodeStatus, StreakSession

    db = SessionLocal()
    try:
        now = datetime.now(UTC).replace(tzinfo=None)
        expired = (
            db.query(StreakSession)
            .filter(
                StreakSession.expires_at.isnot(None),
                StreakSession.expires_at < now,
            )
            .all()
        )
        cancelled = 0
        for session in expired:
            code_ids = json.loads(session.codes_delivered or "[]")
            for code_id in code_ids:
                code = (
                    db.query(StreakPromotionCode).filter(StreakPromotionCode.id == code_id).first()
                )
                if code and code.status == StreakPromotionCodeStatus.DELIVERED:
                    code.status = StreakPromotionCodeStatus.CANCELLED
                    cancelled += 1
            session.expires_at = now
        if cancelled > 0:
            db.commit()
            logger.info(f"scheduler_service - cleanup_streak_sessions - cancelled:{cancelled}")
    except Exception as e:
        db.rollback()
        logger.error(f"scheduler_service - cleanup_streak_sessions - error:{e}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# SchedulerService — solo maneja el ciclo de vida de APScheduler
# ─────────────────────────────────────────────────────────────────────────────


class SchedulerService:
    """Gestiona APScheduler con SQLAlchemyJobStore. No contiene lógica de jobs."""

    def __init__(self, bot: Bot):
        from apscheduler.executors.asyncio import AsyncIOExecutor
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        from config.settings import bot_config

        global _bot_token
        _bot_token = bot.token  # Guardar solo el token (string -> picklable)

        self.running = False
        self._scheduler = None

        jobstores = {"default": SQLAlchemyJobStore(url=bot_config.DATABASE_URL)}
        executors = {"default": AsyncIOExecutor()}
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
            hour=8,
            minute=0,
            id="expiry_reminders",
            name="Send VIP expiry reminders",
            replace_existing=True,
        )
        self._scheduler.add_job(
            _process_expired_subscriptions,
            trigger="cron",
            hour="0,6,12,18",
            minute=5,
            id="expire_subscriptions",
            name="Process expired VIP subscriptions",
            replace_existing=True,
        )
        self._scheduler.add_job(
            _run_backup_job,
            trigger="cron",
            hour=3,
            minute=0,
            id="daily_backup",
            name="Daily database backup",
            replace_existing=True,
        )
        self._scheduler.add_job(
            _cleanup_expired_streak_sessions,
            IntervalTrigger(minutes=60),
            id="cleanup_streak_sessions",
            replace_existing=True,
            name="Limpieza de sesiones de racha expiradas",
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
        run_date = datetime.now(UTC) + timedelta(seconds=30)
        self._scheduler.add_job(
            _send_free_welcome_job,
            trigger=DateTrigger(run_date=run_date),
            id=job_id,
            replace_existing=True,
            kwargs={"user_id": user_id, "channel_id": channel_id},
        )
        logger.info(
            f"Scheduled free welcome job: user={user_id}, channel={channel_id}, run_at={run_date}"
        )

    def schedule_streak_promotion(self, promo_id: int, start_date=None, end_date=None):
        """Programa jobs de activacion/desactivacion automatica para una promocion por racha.

        Usa DateTrigger para ejecutar en fechas especificas de inicio y fin.
        """
        if start_date:
            self._scheduler.add_job(
                activate_streak_promotion,
                trigger=DateTrigger(run_date=start_date),
                id=f"streak_promo_activate_{promo_id}",
                replace_existing=True,
                kwargs={"promo_id": promo_id},
            )
            logger.info(
                f"Scheduled streak promotion activation: promo_id={promo_id}, at={start_date}"
            )
        if end_date:
            self._scheduler.add_job(
                deactivate_streak_promotion,
                trigger=DateTrigger(run_date=end_date),
                id=f"streak_promo_deactivate_{promo_id}",
                replace_existing=True,
                kwargs={"promo_id": promo_id},
            )
            logger.info(
                f"Scheduled streak promotion deactivation: promo_id={promo_id}, at={end_date}"
            )
        logger.info(
            f"scheduler_service - schedule_streak_promotion - "
            f"promo_id:{promo_id} - start:{start_date} - end:{end_date}"
        )

    def remove_streak_promotion_jobs(self, promo_id: int):
        """Remueve jobs de activacion/desactivacion para una promocion por racha."""
        for job_id in (f"streak_promo_activate_{promo_id}", f"streak_promo_deactivate_{promo_id}"):
            try:
                self._scheduler.remove_job(job_id)
            except Exception as e:
                logger.warning(
                    f"scheduler_service - remove_streak_promotion_jobs - job:{job_id} - error:{e}"
                )
        logger.info(
            f"scheduler_service - remove_streak_promotion_jobs - promo_id:{promo_id} - removed"
        )

    def schedule_nurture_step(self, user_telegram_id: int, step_id: int, run_date: datetime):
        """Programa entrega one-shot de un NurtureStep usando DateTrigger (persistente via jobstore).
        PII: user_telegram_id (tg id) stored in APS jobstore kwargs + logs; protected exactly as free_welcome/streak jobs (same SQLAlchemyJobStore DB, same backups/ACLs). Volume small (admin-configured steps per seq).
        """
        job_id = f"nurture_{user_telegram_id}_{step_id}"
        self._scheduler.add_job(
            _deliver_nurture_step,
            trigger=DateTrigger(run_date=run_date),
            id=job_id,
            replace_existing=True,
            kwargs={"user_id": user_telegram_id, "step_id": step_id},
        )
        logger.info(
            f"scheduler_service | schedule_nurture_step | user_id={user_telegram_id} | step_id={step_id} | run_date={run_date} | result=scheduled"
        )

    def remove_nurture_jobs(self, user_telegram_id: int, step_ids: list[int] | None = None):
        """Remueve jobs nurture programados para un usuario (soporta step_ids=None para todos del user via prefix scan en jobstore)."""
        removed = 0
        if step_ids:
            for sid in step_ids:
                jid = f"nurture_{user_telegram_id}_{sid}"
                try:
                    self._scheduler.remove_job(jid)
                    removed += 1
                except Exception as e:
                    logger.debug(f"scheduler_service | remove_nurture_jobs | job={jid} | err={e}")
        else:
            # full for user: scan current jobs (works for in-memory + persistent ones loaded)
            prefix = f"nurture_{user_telegram_id}_"
            for job in list(self._scheduler.get_jobs()):
                if job.id.startswith(prefix):
                    try:
                        self._scheduler.remove_job(job.id)
                        removed += 1
                    except Exception as e:
                        logger.debug(
                            f"scheduler_service | remove_nurture_jobs | job={job.id} | err={e}"
                        )
        logger.info(
            f"scheduler_service | remove_nurture_jobs | user_id={user_telegram_id} | step_ids={step_ids} | removed={removed} | result=attempted"
        )

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
