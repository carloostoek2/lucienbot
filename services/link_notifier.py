"""
LinkNotifier - Fase 6 link (emisor).

Persiste la business_connection de la dueña y envía el aviso [LINK] al chat de
coordinación. Best-effort: nunca rompe el flujo de expulsión. Flag OFF = no-op.
Bot lazy PROPIO (bot_config.TOKEN) — NO reusa el _get_bot del scheduler, que
depende de _bot_token seteado después del startup check (corrección R1).
"""
import json
import logging
import uuid

from aiogram import Bot

from config.settings import bot_config
from models.database import SessionLocal, get_db_session
from models.models import BusinessConnection

logger = logging.getLogger(__name__)


def _fetch_enabled_business_connection_id(db) -> str | None:
    """Return the most recent enabled business_connection_id, or None."""
    row = (
        db.query(BusinessConnection)
        .filter(BusinessConnection.is_enabled.is_(True))
        .order_by(BusinessConnection.created_at.desc())
        .first()
    )
    return row.business_connection_id if row else None


class LinkNotifier:
    def __init__(self, bot: Bot, chat_id: int | None, enabled: bool) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._enabled = enabled

    @staticmethod
    def upsert_business_connection(bc) -> None:
        """Persist the owner's business connection (idempotent upsert by PK)."""
        with get_db_session() as db:
            row = db.get(BusinessConnection, bc.id)
            if row is None:
                db.add(
                    BusinessConnection(
                        business_connection_id=bc.id,
                        user_id=bc.user.id,
                        user_chat_id=bc.user_chat_id,
                        is_enabled=bc.is_enabled,
                    )
                )
            else:
                row.user_id = bc.user.id
                row.user_chat_id = bc.user_chat_id
                row.is_enabled = bc.is_enabled
        logger.info(
            f"link_notifier | upsert_business_connection | user_id={bc.user.id} | "
            f"result={'enabled' if bc.is_enabled else 'disabled'}"
        )

    async def notify_vip_kicked(self, payload: dict) -> None:
        """Best-effort [LINK] notification. Never raises; never blocks the kick flow."""
        if not self._enabled or self._chat_id is None:
            return
        try:
            db = SessionLocal()
            try:
                bc_id = _fetch_enabled_business_connection_id(db)
            finally:
                db.close()
            if not bc_id:
                logger.info(
                    f"link_notifier | notify_vip_kicked | user_id={payload.get('user_id')} | "
                    "result=no_business_connection"
                )
                return
            raw_username = payload.get("username")
            body = {
                "v": 1,
                "event": "vip_kicked",
                "event_id": str(uuid.uuid4()),
                "user_id": payload.get("user_id"),
                "username": f"@{raw_username}" if raw_username else None,
                "channel_id": payload.get("channel_id"),
                "channel_name": payload.get("channel_name"),
                "reason": payload.get("reason"),
                "ts": payload.get("ts"),
            }
            text = "[LINK] " + json.dumps(body, ensure_ascii=False, separators=(",", ":"))
            await self._bot.send_message(
                chat_id=self._chat_id, business_connection_id=bc_id, text=text
            )
            logger.info(
                f"link_notifier | notify_vip_kicked | user_id={payload.get('user_id')} | "
                f"event_id={body['event_id']} | result=sent"
            )
        except Exception as exc:
            logger.warning(
                f"link_notifier | notify_vip_kicked | user_id={payload.get('user_id')} | "
                f"error={exc} | result=swallowed_best_effort"
            )


_bot_instance: Bot | None = None
_notifier: LinkNotifier | None = None


def _get_bot() -> Bot:
    """Self-contained lazy bot from bot_config.TOKEN (not scheduler._bot_token)."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(token=bot_config.TOKEN)
    return _bot_instance


def _get_link_notifier() -> LinkNotifier:
    """Return the module singleton notifier (reads config once)."""
    global _notifier
    if _notifier is None:
        _notifier = LinkNotifier(
            bot=_get_bot(),
            chat_id=bot_config.LINK_CHAT_ID or None,
            enabled=bot_config.FEATURE_LINK_ENABLED,
        )
    return _notifier


async def on_vip_kicked(payload: dict) -> None:
    """Event bus listener adapter (registered in bot.py). Best-effort, never raises."""
    try:
        await _get_link_notifier().notify_vip_kicked(payload)
    except Exception as exc:
        logger.warning(
            f"link_notifier | on_vip_kicked | user_id={payload.get('user_id')} | "
            f"error={exc} | result=swallowed_best_effort"
        )
