"""
VIP activation admin notifier (Item 30).

Observational EventBus listeners that DM each Custodio (bot_config.ADMIN_IDS) the
outcome of VIP token activation: success (reuses EVENT_VIP_ACTIVATED) and failure
(new EVENT_VIP_ACTIVATION_FAILED). Best-effort: NEVER mutates VIP state and NEVER
re-enters redeem_token. Follows the proven patterns:
- listener -> nurture_service.on_vip_activated (lazy get_service, try/except,
  log handled/swallowed_best_effort);
- DM loop -> store_service._notify_admins_of_purchase (per-admin try/except);
- lazy bot -> link_notifier._get_bot (self-contained, bot_config.TOKEN).

User-facing text is delegated to LucienVoice (canonical location per the
no-hardcoded-Spanish-in-services audit). Logging convention:
"vip_notifier | <accion> | user_id=<...> | resultado".
"""

import logging

from aiogram import Bot

from config.settings import bot_config
from models.models import Subscription, User
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)


_bot_instance: Bot | None = None


def _get_bot() -> Bot:
    """Return a lazy self-contained bot from bot_config.TOKEN (link_notifier pattern)."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(token=bot_config.TOKEN)
    return _bot_instance


async def _notify_admins(bot: Bot, text: str) -> None:
    """DM each Custodio (ADMIN_IDS) the given text. Best-effort; per-admin try/except."""
    if not bot_config.ADMIN_IDS:
        logger.debug("vip_notifier | notify_skipped | reason=no_admin_ids | result=skip")
        return
    for admin_id in bot_config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
            logger.info(f"vip_notifier | notify_sent | admin_id={admin_id} | result=ok")
        except Exception as exc:
            logger.error(
                f"vip_notifier | notify_error | admin_id={admin_id} | error={exc} | result=error"
            )


def build_activation_success_text(
    user_id: int,
    username: str | None,
    first_name: str | None,
    tariff_name: str | None,
    duration_days: int | None,
) -> str:
    """Pure helper: normalize identity/tariff (None -> 'N/A') and delegate to LucienVoice."""
    uname = f"@{username}" if username else "N/A"
    name = first_name or "N/A"
    tname = tariff_name or "N/A"
    dur = str(duration_days) if duration_days is not None else "N/A"
    return LucienVoice.vip_activation_admin_success(
        username=uname,
        first_name=name,
        user_id=user_id,
        tariff_name=tname,
        duration_days=dur,
    )


def build_activation_failure_text(
    user_id: int,
    username: str | None,
    first_name: str | None,
    reason: str,
    token_code: str | None = None,
) -> str:
    """Pure helper: normalize identity (None -> 'N/A') and delegate failure text to LucienVoice."""
    uname = f"@{username}" if username else "N/A"
    name = first_name or "N/A"
    return LucienVoice.vip_activation_admin_failure(
        username=uname,
        first_name=name,
        user_id=user_id,
        reason=reason,
        token_code=token_code,
    )


async def on_vip_activated_admin_notify(payload: dict) -> None:
    """Listener for EVENT_VIP_ACTIVATED: DM each Custodio with user + tariff + duration."""
    user_id = payload.get("user_id") if isinstance(payload, dict) else None
    subscription_id = payload.get("subscription_id") if isinstance(payload, dict) else None
    if not user_id or not subscription_id:
        logger.debug(
            f"vip_notifier | on_vip_activated_admin_notify | user_id={user_id} | "
            "result=missing_ids"
        )
        return
    try:
        from services import get_service, VIPService  # lazy (anti-circular import)

        with get_service(VIPService) as svc:
            db = svc._get_db()
            subscription = (
                db.query(Subscription).filter(Subscription.id == int(subscription_id)).first()
            )
            if not subscription:
                logger.warning(
                    f"vip_notifier | on_vip_activated_admin_notify | user_id={user_id} | "
                    "result=subscription_not_found"
                )
                return
            tariff = subscription.tariff
            if tariff is None and subscription.token is not None:
                tariff = subscription.token.tariff
            tariff_name = tariff.name if tariff else None
            duration_days = tariff.duration_days if tariff else None
            user = db.query(User).filter(User.telegram_id == int(user_id)).first()
            username = user.username if user else None
            first_name = user.first_name if user else None
            text = build_activation_success_text(
                int(user_id), username, first_name, tariff_name, duration_days
            )
        await _notify_admins(_get_bot(), text)
        logger.info(
            f"vip_notifier | on_vip_activated_admin_notify | user_id={user_id} | "
            f"subscription_id={subscription_id} | result=handled"
        )
    except Exception as exc:
        logger.warning(
            f"vip_notifier | on_vip_activated_admin_notify | user_id={user_id} | "
            f"error={exc} | result=swallowed_best_effort"
        )


async def notify_reintegration_attempt(
    user_id: int,
    username: str | None,
    first_name: str | None,
    ok: bool,
    meta: dict | None,
) -> None:
    """Avisa a Custodios el resultado de /start reintegrar. Best-effort, no muta VIP."""
    display = first_name or (f"@{username}" if username else f"ID:{user_id}")
    if username and first_name:
        display = f"{first_name} (@{username})"
    reason = (meta or {}).get("reason")
    try:
        if ok:
            text = LucienVoice.vip_reintegration_admin_ok(
                display=display,
                user_id=user_id,
                expiry=(meta or {}).get("expiry", "—"),
                days_remaining=int((meta or {}).get("days_remaining") or 0),
                invite_link=(meta or {}).get("invite_link") or "",
            )
        elif reason == "invite_failed" or reason == "no_channel":
            text = LucienVoice.vip_reintegration_admin_invite_failed(display, user_id)
        else:
            text = LucienVoice.vip_reintegration_admin_denied(display, user_id)
        await _notify_admins(_get_bot(), text)
        logger.info(
            f"vip_notifier | notify_reintegration_attempt | user_id={user_id} | "
            f"ok={ok} | reason={reason} | result=handled"
        )
    except Exception as exc:
        logger.warning(
            f"vip_notifier | notify_reintegration_attempt | user_id={user_id} | "
            f"error={exc} | result=swallowed_best_effort"
        )


async def on_vip_activation_failed_admin_notify(payload: dict) -> None:
    """Listener for EVENT_VIP_ACTIVATION_FAILED: DM each Custodio with the failure reason."""
    user_id = payload.get("user_id") if isinstance(payload, dict) else None
    reason = payload.get("reason") if isinstance(payload, dict) else None
    if not user_id or not reason:
        logger.debug(
            f"vip_notifier | on_vip_activation_failed_admin_notify | user_id={user_id} | "
            "result=missing_ids"
        )
        return
    try:
        from services import get_service, VIPService  # lazy (anti-circular import)

        with get_service(VIPService) as svc:
            db = svc._get_db()
            user = db.query(User).filter(User.telegram_id == int(user_id)).first()
            username = user.username if user else None
            first_name = user.first_name if user else None
        token_code = payload.get("token_code") if isinstance(payload, dict) else None
        text = build_activation_failure_text(
            int(user_id), username, first_name, reason, token_code
        )
        await _notify_admins(_get_bot(), text)
        logger.info(
            f"vip_notifier | on_vip_activation_failed_admin_notify | user_id={user_id} | "
            f"reason={reason} | result=handled"
        )
    except Exception as exc:
        logger.warning(
            f"vip_notifier | on_vip_activation_failed_admin_notify | user_id={user_id} | "
            f"error={exc} | result=swallowed_best_effort"
        )
