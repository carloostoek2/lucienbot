"""Recordatorio a usuarios Free inactivos (informe #6). Feature flag apagado por defecto.

Reglas:
- Destinatarios: hicieron /start (``bot_started_at``), no bloquearon al bot, activos, no
  admin y sin VIP vigente. Los creados solo por join-request no tienen ``bot_started_at``.
- Solo usuarios con actividad REAL (no reacciones del canal) en o después de la
  activación del flag: ``last_activity_at IS NOT NULL AND last_activity_at >= activado_en``.
  La activación se guarda UNA vez en ``feature_activations`` la primera vez que el flag
  corre encendido y nunca se recalcula. Los inactivos históricos (última actividad antes
  de la activación, o NULL) NUNCA reciben nada, ningún día: no hay "ola" del día 3.
- Inactividad = ahora - last_activity_at. A los 3 días se manda uno. No se repite hasta que el usuario vuelva (actividad posterior
  al recordatorio) y vuelva a pasar 3 días inactivo; además máximo 1 cada 7 días.
- Solo de 10:00 a 21:00 America/Mexico_City (se revalida antes de cada envío).
- Lotes de ``BATCH_SIZE`` con pausa entre envíos; claim por fila (UPDATE condicional)
  antes de enviar, así dos instancias no mandan dos veces.
- Si el usuario bloqueó al bot: se marca ``bot_blocked_at`` y no se reintenta.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config.settings import bot_config
from models.models import FeatureActivation, Subscription, User, UserRole

logger = logging.getLogger(__name__)

FEATURE_KEY = "free_inactivity_reminder"
INACTIVITY = timedelta(days=3)
MIN_INTERVAL = timedelta(days=7)
SEND_HOUR_START = 10  # incluido
SEND_HOUR_END = 21  # excluido
BATCH_SIZE = 200
SEND_PAUSE_SECONDS = 0.05  # ~20 msg/s
ACTIVITY_THROTTLE = timedelta(minutes=15)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def is_enabled() -> bool:
    return bool(getattr(bot_config, "FEATURE_FREE_INACTIVITY_REMINDER", False))


def in_send_window(now: datetime) -> bool:
    local = _utc(now).astimezone(ZoneInfo(bot_config.TIMEZONE))
    return SEND_HOUR_START <= local.hour < SEND_HOUR_END


# ==================== Actividad (llamado desde ActivityMiddleware) ====================


def touch_activity(db: Session, telegram_id: int, now: datetime | None = None) -> bool:
    """Marca actividad con throttle (1 escritura cada 15 min). Un solo UPDATE."""
    now = _utc(now) or datetime.now(UTC)
    result = db.execute(
        update(User)
        .where(
            User.telegram_id == telegram_id,
            or_(User.last_activity_at.is_(None), User.last_activity_at < now - ACTIVITY_THROTTLE),
        )
        .values(last_activity_at=now)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def mark_started(db: Session, telegram_id: int, now: datetime | None = None) -> None:
    """/start: fija bot_started_at si falta (nunca lo pisa) y limpia bot_blocked_at
    (si escribió /start, desbloqueó al bot). También cuenta como actividad."""
    now = _utc(now) or datetime.now(UTC)
    db.execute(
        update(User)
        .where(User.telegram_id == telegram_id, User.bot_started_at.is_(None))
        .values(bot_started_at=now)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        update(User)
        .where(User.telegram_id == telegram_id, User.bot_blocked_at.is_not(None))
        .values(bot_blocked_at=None)
        .execution_options(synchronize_session=False)
    )
    db.execute(update(User).where(User.telegram_id == telegram_id).values(last_activity_at=now))
    db.commit()


# ==================== Activación del flag ====================


def ensure_activation(db: Session, now: datetime | None = None) -> datetime:
    """Devuelve el momento de la PRIMERA activación; lo guarda si no existe."""
    row = db.get(FeatureActivation, FEATURE_KEY)
    if row is not None:
        return _utc(row.activated_at)
    activated_at = _utc(now) or datetime.now(UTC)
    try:
        with db.begin_nested():
            db.add(FeatureActivation(key=FEATURE_KEY, activated_at=activated_at))
        db.commit()
        logger.info(
            f"inactivity_reminder | ensure_activation | activated_at={activated_at.isoformat()}"
        )
    except IntegrityError:
        db.rollback()  # otra instancia la creó primero
    row = db.get(FeatureActivation, FEATURE_KEY)
    return _utc(row.activated_at)


# ==================== Selección y claim ====================


def _admin_ids() -> list[int]:
    return list(getattr(bot_config, "ADMIN_IDS", []) or [])


def find_candidates(db: Session, now: datetime, activated_at: datetime, limit: int) -> list[User]:
    now = _utc(now)
    cutoff = now - INACTIVITY
    activated_at = _utc(activated_at)
    has_active_vip = exists().where(
        Subscription.user_id == User.telegram_id,
        Subscription.is_active.is_(True),
        Subscription.end_date > now,
    )
    query = (
        select(User)
        .where(
            User.bot_started_at.is_not(None),
            User.bot_blocked_at.is_(None),
            User.is_active.is_(True),
            User.role != UserRole.ADMIN,
            ~has_active_vip,
            # Actividad real posterior a la activación (excluye inactivos históricos)
            # y 3 días sin actividad desde entonces.
            User.last_activity_at.is_not(None),
            User.last_activity_at >= activated_at,
            User.last_activity_at <= cutoff,
            or_(
                User.last_inactivity_reminder_at.is_(None),
                and_(
                    User.last_inactivity_reminder_at <= now - MIN_INTERVAL,
                    User.last_activity_at > User.last_inactivity_reminder_at,
                ),
            ),
        )
        .order_by(User.id)
        .limit(limit)
    )
    admins = _admin_ids()
    if admins:
        query = query.where(User.telegram_id.not_in(admins))
    return list(db.execute(query).scalars())


def claim(db: Session, user_id: int, previous: datetime | None, now: datetime) -> bool:
    """Compare-and-set sobre last_inactivity_reminder_at: solo una instancia gana.

    ``previous`` es el valor leído al seleccionar al candidato.
    """
    condition = (
        User.last_inactivity_reminder_at.is_(None)
        if previous is None
        else User.last_inactivity_reminder_at == previous
    )
    result = db.execute(
        update(User)
        .where(User.id == user_id, condition)
        .values(last_inactivity_reminder_at=_utc(now))
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def _release_claim(db: Session, user_id: int, previous: datetime | None) -> None:
    db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_inactivity_reminder_at=previous)
        .execution_options(synchronize_session=False)
    )
    db.commit()


def _mark_blocked(db: Session, user_id: int, now: datetime) -> None:
    db.execute(
        update(User)
        .where(User.id == user_id)
        .values(bot_blocked_at=_utc(now))
        .execution_options(synchronize_session=False)
    )
    db.commit()


def _message_for(previous_reminder: datetime | None, gift_amount: int) -> str:
    from utils.lucien_voice import LucienVoice

    if previous_reminder is None and gift_amount > 0:
        return LucienVoice.free_inactivity_reminder(gift_amount)
    return LucienVoice.free_inactivity_reminder_alt()


async def run_inactivity_reminders(
    db: Session,
    bot,
    now: datetime | None = None,
    *,
    batch_size: int = BATCH_SIZE,
    pause_seconds: float = SEND_PAUSE_SECONDS,
    clock=None,
) -> dict:
    """Una corrida del job. ``clock()`` (tests) da la hora antes de cada envío."""
    stats = {"sent": 0, "blocked": 0, "skipped": 0, "errors": 0}
    if not is_enabled():
        return {**stats, "reason": "disabled"}
    now = _utc(now) or datetime.now(UTC)
    activated_at = ensure_activation(db, now)
    if not in_send_window(now):
        return {**stats, "reason": "outside_window"}

    from services.daily_gift_service import DailyGiftService

    gift_amount = DailyGiftService(db).get_gift_amount()
    clock = clock or (lambda: datetime.now(UTC))
    for user in find_candidates(db, now, activated_at, batch_size):
        send_now = _utc(clock())
        if not in_send_window(send_now):
            stats["reason"] = "window_closed"
            break
        previous = user.last_inactivity_reminder_at
        if not claim(db, user.id, previous, send_now):
            stats["skipped"] += 1
            continue
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=_message_for(previous, gift_amount),
                parse_mode="HTML",
            )
            stats["sent"] += 1
        except TelegramForbiddenError:
            _mark_blocked(db, user.id, send_now)
            stats["blocked"] += 1
        except TelegramRetryAfter as exc:
            # No se envió: se libera el claim y se corta el lote (la próxima corrida sigue).
            _release_claim(db, user.id, previous)
            logger.warning(f"inactivity_reminder | retry_after={exc.retry_after}s | stop_batch")
            stats["reason"] = "retry_after"
            break
        except Exception as exc:  # noqa: BLE001
            # Estado desconocido (puede haberse entregado): se deja el claim (no se repite).
            stats["errors"] += 1
            logger.error(
                f"inactivity_reminder | send_error | user_id={user.telegram_id} | error={exc}"
            )
        if pause_seconds:
            await asyncio.sleep(pause_seconds)
    logger.info(f"inactivity_reminder | run | {stats}")
    return stats
