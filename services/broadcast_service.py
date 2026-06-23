"""
Servicio de Broadcasting - Lucien Bot

Gestiona el envío de mensajes a canales con sistema de reacciones.
"""

import logging

from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.database import SessionLocal
from models.models import (
    BroadcastButton,
    BroadcastMessage,
    BroadcastReaction,
    MissionType,
    ReactionEmoji,
    TransactionSource,
)
from services.besito_service import BesitoService
from services.mission_service import MissionService, run_mission_side_effects_isolated

logger = logging.getLogger(__name__)


class BroadcastService:
    """Servicio para gestión de broadcasting con reacciones"""

    def __init__(self, db: Session = None):
        self._owns_session = db is None
        self.db = db or SessionLocal()
        # Held direct BesitoService composition removed (Item 6 / remaining composers unification).
        # REACTION credits now use local on-demand BesitoService(db=self.db) *only*
        # inside register_reaction / check_and_register_reaction (preserves atomicity:
        # credit's internal commit + REACTION tx + mission best-effort + return dict all unchanged;
        # best-effort schedule_emit still fires post-credit commit).
        # Other composers (game/daily) handled in their phases; scope tight per Item 6.
        # (No other held subs in this service's __init__.)

    # ==================== CONFIGURACIÓN DE EMOJIS ====================

    def create_reaction_emoji(
        self, emoji: str, name: str = None, besito_value: int = 1
    ) -> ReactionEmoji:
        """Crea un nuevo emoji de reacción"""
        reaction = ReactionEmoji(
            emoji=emoji, name=name or emoji, besito_value=besito_value, is_active=True
        )
        self.db.add(reaction)
        self.db.commit()
        self.db.refresh(reaction)
        logger.info(f"Emoji de reacción creado: {emoji} = {besito_value} besitos")
        return reaction

    def get_reaction_emoji(self, emoji_id: int) -> ReactionEmoji | None:
        """Obtiene un emoji por ID"""
        return self.db.query(ReactionEmoji).filter(ReactionEmoji.id == emoji_id).first()

    def get_reaction_emoji_by_emoji(self, emoji: str) -> ReactionEmoji | None:
        """Obtiene un emoji por su caracter"""
        return (
            self.db.query(ReactionEmoji)
            .filter(ReactionEmoji.emoji == emoji, ReactionEmoji.is_active)
            .first()
        )

    def get_all_emojis(self, active_only: bool = True) -> list[ReactionEmoji]:
        """Obtiene todos los emojis configurados"""
        query = self.db.query(ReactionEmoji)
        if active_only:
            query = query.filter(ReactionEmoji.is_active)
        return query.all()

    def update_emoji_value(self, emoji_id: int, besito_value: int) -> bool:
        """Actualiza el valor de besitos de un emoji"""
        emoji = self.get_reaction_emoji(emoji_id)
        if emoji:
            emoji.besito_value = besito_value
            self.db.commit()
            return True
        return False

    def toggle_emoji(self, emoji_id: int) -> bool:
        """Activa/desactiva un emoji"""
        emoji = self.get_reaction_emoji(emoji_id)
        if emoji:
            emoji.is_active = not emoji.is_active
            self.db.commit()
            return True
        return False

    def delete_emoji(self, emoji_id: int) -> bool:
        """Elimina un emoji"""
        emoji = self.get_reaction_emoji(emoji_id)
        if emoji:
            self.db.delete(emoji)
            self.db.commit()
            return True
        return False

    # ==================== BOTONES DE ENLACE EXTRA ====================

    def create_broadcast_button(
        self, label: str, url: str, description: str = None
    ) -> BroadcastButton:
        """Crea un nuevo botón de enlace extra.

        Validation is loose per ITEM1 decision (Telegram link intent documented;
        enforcement + tests deferred to ITEM2 integration). No strict checks here.
        """
        button = BroadcastButton(label=label, url=url, description=description, is_active=True)
        self.db.add(button)
        self.db.commit()
        self.db.refresh(button)
        logger.info(
            f"broadcast_service | create_broadcast_button | label={label} | url={url} | id={button.id}"
        )
        return button

    def get_broadcast_button(self, button_id: int) -> BroadcastButton | None:
        """Obtiene un botón por ID"""
        return self.db.query(BroadcastButton).filter(BroadcastButton.id == button_id).first()

    def get_all_buttons(self, active_only: bool = True) -> list[BroadcastButton]:
        """Obtiene todos los botones de enlace"""
        query = self.db.query(BroadcastButton)
        if active_only:
            query = query.filter(BroadcastButton.is_active)
        return query.all()

    def toggle_broadcast_button(self, button_id: int) -> bool:
        """Activa/desactiva un botón de enlace"""
        button = self.get_broadcast_button(button_id)
        if button:
            button.is_active = not button.is_active
            self.db.commit()
            return True
        return False

    def update_broadcast_button(
        self, button_id: int, label: str = None, url: str = None, description: str = None
    ) -> bool:
        """Actualiza campos provistos de un botón (parcial).

        If no non-None fields provided, this is a no-op (no columns mutated)
        but we still commit (harmless) and return True because the row was found.
        This matches the simple "if found: mutate; commit; return True" pattern
        used by update_emoji_value / siblings (no early-exit complexity).
        """
        button = self.get_broadcast_button(button_id)
        if not button:
            return False
        if label is not None:
            button.label = label
        if url is not None:
            button.url = url
        if description is not None:
            button.description = description
        self.db.commit()  # commit even on no-op to keep pattern consistent
        return True

    def delete_broadcast_button(self, button_id: int) -> bool:
        """Elimina un botón de enlace"""
        button = self.get_broadcast_button(button_id)
        if button:
            self.db.delete(button)
            self.db.commit()
            return True
        return False

    # ==================== MENSAJES DE BROADCAST ====================

    def create_broadcast_message(
        self,
        message_id: int,
        channel_id: int,
        admin_id: int,
        text: str = None,
        has_attachment: bool = False,
        attachment_type: str = None,
        attachment_file_id: str = None,
        has_reactions: bool = False,
        is_protected: bool = False,
        selected_emoji_ids: str = None,
        extra_button_id: int = None,
    ) -> BroadcastMessage:
        """Registra un mensaje de broadcast en la base de datos (acepta extra_button_id opcional)."""
        broadcast = BroadcastMessage(
            message_id=message_id,
            channel_id=channel_id,
            admin_id=admin_id,
            text=text,
            has_attachment=has_attachment,
            attachment_type=attachment_type,
            attachment_file_id=attachment_file_id,
            has_reactions=has_reactions,
            is_protected=is_protected,
            selected_emoji_ids=selected_emoji_ids,
            extra_button_id=extra_button_id,
        )
        self.db.add(broadcast)
        self.db.commit()
        self.db.refresh(broadcast)
        logger.info(f"Mensaje de broadcast registrado: {broadcast.id}")
        return broadcast

    def get_broadcast(self, broadcast_id: int) -> BroadcastMessage | None:
        """Obtiene un mensaje de broadcast por ID"""
        return self.db.query(BroadcastMessage).filter(BroadcastMessage.id == broadcast_id).first()

    def update_broadcast_message_id(self, broadcast_id: int, message_id: int) -> bool:
        """Actualiza el message_id de Telegram tras el envío al canal."""
        broadcast = self.get_broadcast(broadcast_id)
        if not broadcast:
            return False
        broadcast.message_id = message_id
        self.db.commit()
        return True

    def delete_broadcast(self, broadcast_id: int) -> bool:
        """Elimina un broadcast huérfano (p. ej. fallo de envío a Telegram)."""
        broadcast = self.get_broadcast(broadcast_id)
        if not broadcast:
            return False
        self.db.delete(broadcast)
        self.db.commit()
        logger.info(f"broadcast_service | delete_broadcast | broadcast_id={broadcast_id} | ok")
        return True

    @staticmethod
    def _reaction_failure(reason: str) -> dict:
        return {"success": False, "reason": reason}

    def get_selected_emoji_ids(self, broadcast_id: int) -> list[int]:
        """Obtiene la lista de IDs de emojis seleccionados para un broadcast"""
        broadcast = self.get_broadcast(broadcast_id)
        if not broadcast or not broadcast.selected_emoji_ids:
            return []
        try:
            return [int(eid) for eid in broadcast.selected_emoji_ids.split(",") if eid]
        except (ValueError, AttributeError):
            return []

    def get_broadcast_by_message_id(
        self, message_id: int, channel_id: int
    ) -> BroadcastMessage | None:
        """Obtiene un broadcast por ID de mensaje de Telegram y canal"""
        return (
            self.db.query(BroadcastMessage)
            .filter(
                BroadcastMessage.message_id == message_id, BroadcastMessage.channel_id == channel_id
            )
            .first()
        )

    def get_recent_broadcasts(
        self, channel_id: int = None, limit: int = 20
    ) -> list[BroadcastMessage]:
        """Obtiene mensajes de broadcast recientes"""
        query = self.db.query(BroadcastMessage)
        if channel_id:
            query = query.filter(BroadcastMessage.channel_id == channel_id)
        return query.order_by(desc(BroadcastMessage.created_at)).limit(limit).all()

    # ==================== REACCIONES ====================

    def has_user_reacted(self, broadcast_id: int, user_id: int) -> bool:
        """Verifica si un usuario ya reaccionó a un mensaje"""
        reaction = (
            self.db.query(BroadcastReaction)
            .filter(
                BroadcastReaction.broadcast_id == broadcast_id, BroadcastReaction.user_id == user_id
            )
            .first()
        )
        return reaction is not None

    def register_reaction(
        self, broadcast_id: int, user_id: int, emoji_id: int, username: str = None
    ) -> BroadcastReaction | None:
        """
        DEPRECATED: Use check_and_register_reaction instead.

        Legacy sync path kept for existing tests. Does not deliver mission rewards
        via bot and duplicates mission logic differently than the production async
        path. New code must call check_and_register_reaction.

        Registra una reacción y otorga besitos al usuario.
        Retorna None si el usuario ya reaccionó.
        """
        # Verificar si ya reaccionó (con lock para evitar race conditions)
        existing = (
            self.db.query(BroadcastReaction)
            .filter(
                BroadcastReaction.broadcast_id == broadcast_id, BroadcastReaction.user_id == user_id
            )
            .with_for_update()
            .first()
        )
        if existing:
            logger.info(f"Usuario {user_id} ya reaccionó al broadcast {broadcast_id}")
            return None

        # Obtener el emoji y su valor
        emoji = self.get_reaction_emoji(emoji_id)
        if not emoji:
            logger.error(f"Emoji {emoji_id} no encontrado")
            return None

        besito_value = emoji.besito_value

        try:
            # Crear la reacción
            reaction = BroadcastReaction(
                broadcast_id=broadcast_id,
                user_id=user_id,
                username=username,
                reaction_emoji_id=emoji_id,
                besitos_awarded=besito_value,
            )
            self.db.add(reaction)

            # Acreditar besitos al usuario
            description = f"Reacción con {emoji.emoji}"
            besito_service = BesitoService(
                db=self.db
            )  # local, on-demand; owns=False (db shared); credit commits internally as before + schedule_emit best-effort
            credited = besito_service.credit_besitos(
                user_id=user_id,
                amount=besito_value,
                source=TransactionSource.REACTION,
                description=description,
                reference_id=broadcast_id,
            )
            if not credited:
                self.db.rollback()
                logger.error(
                    f"broadcast_service | register_reaction | user_id={user_id} | broadcast_id={broadcast_id} | credit_failed"
                )
                return None

            self.db.commit()
            self.db.refresh(reaction)

            # Incrementar progreso de misiones REACTION_COUNT
            mission_service = MissionService(self.db)
            completed_missions = mission_service.increment_progress(
                user_id, MissionType.REACTION_COUNT, amount=1
            )

            logger.info(
                f"Reacción registrada: user={user_id}, broadcast={broadcast_id}, besitos={besito_value}, misiones_completadas={len(completed_missions)}"
            )
            return reaction

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registrando reacción: {e}")
            return None

    async def check_and_register_reaction(
        self,
        broadcast_id: int,
        user_id: int,
        emoji_id: int,
        username: str = None,
        bot=None,
        channel_id: int = None,
        message_id: int = None,
    ) -> dict:
        """
        Verifica y registra una reacción en una sola transacción atómica.
        Entrega recompensas de misiones automáticamente.

        Retorna dict con ``success`` True y datos de la reacción, o
        ``success`` False con ``reason`` (duplicate, invalid_broadcast, etc.).

        IMPORTANTE: Construye el dict de retorno ANTES del segundo commit
        para evitar el bug 'DetachedInstanceError' que existe en main.
        """
        db = self.db

        broadcast = self.get_broadcast(broadcast_id)
        if not broadcast:
            logger.warning(
                f"broadcast_service | check_and_register_reaction | user_id={user_id} | broadcast_id={broadcast_id} | invalid_broadcast"
            )
            return self._reaction_failure("invalid_broadcast")
        if not broadcast.has_reactions:
            return self._reaction_failure("no_reactions")
        if channel_id is not None and broadcast.channel_id != channel_id:
            return self._reaction_failure("message_mismatch")
        if message_id is not None and broadcast.message_id != message_id:
            return self._reaction_failure("message_mismatch")

        emoji = self.get_reaction_emoji(emoji_id)
        if not emoji:
            logger.error(f"Emoji {emoji_id} no encontrado")
            return self._reaction_failure("invalid_emoji")
        if not emoji.is_active:
            return self._reaction_failure("inactive_emoji")

        selected_emoji_ids = self.get_selected_emoji_ids(broadcast_id)
        if emoji_id not in selected_emoji_ids:
            return self._reaction_failure("emoji_not_allowed")

        # Defensa en profundidad: chequeo explícito antes del INSERT (UC sigue siendo la protección final para races).
        if self.has_user_reacted(broadcast_id, user_id):
            logger.info(
                f"broadcast_service | check_and_register_reaction | user_id={user_id} | broadcast_id={broadcast_id} | duplicate (pre-check)"
            )
            return self._reaction_failure("duplicate")

        besito_value = emoji.besito_value

        try:
            # Crear la reacción - el UniqueConstraint en BD evitará duplicados (fallback para concurrencia)
            reaction = BroadcastReaction(
                broadcast_id=broadcast_id,
                user_id=user_id,
                username=username,
                reaction_emoji_id=emoji_id,
                besitos_awarded=besito_value,
            )
            db.add(reaction)
            db.flush()  # Forzar el INSERT para capturar IntegrityError

            # Acreditar besitos al usuario (dentro de la misma transacción)
            description = f"Reacción con {emoji.emoji}"
            besito_service = BesitoService(
                db=self.db
            )  # local, on-demand; owns=False (db shared); credit commits internally as before + schedule_emit best-effort
            credited = besito_service.credit_besitos(
                user_id=user_id,
                amount=besito_value,
                source=TransactionSource.REACTION,
                description=description,
                reference_id=broadcast_id,
            )
            if not credited:
                db.rollback()
                logger.error(
                    f"broadcast_service | check_and_register_reaction | user_id={user_id} | broadcast_id={broadcast_id} | credit_failed"
                )
                return self._reaction_failure("credit_failed")

            # Commit de la transacción principal
            db.commit()

            logger.info(
                f"Reacción registrada: user={user_id}, broadcast={broadcast_id}, besitos={besito_value}"
            )

            # GUARDAR el ID de la reacción ANTES de procesar misiones
            # para evitarDetachedInstanceError después del segundo commit
            reaction_id = reaction.id
            emoji_char = emoji.emoji

            # Misiones: sesión DB aislada + reintento (best-effort; no invalida la reacción)
            completed_count = await run_mission_side_effects_isolated(
                user_id,
                MissionType.REACTION_COUNT,
                amount=1,
                bot=bot,
                reference_id=broadcast_id,
                db=db,
            )
            if completed_count:
                logger.info(
                    f"Misiones completadas por reacción: user={user_id}, broadcast={broadcast_id}, count={completed_count}"
                )

            # Retornar diccionario con datos GUARDADOS (no acceder al objeto reaction)
            return {
                "success": True,
                "id": reaction_id,
                "broadcast_id": broadcast_id,
                "user_id": user_id,
                "besitos_awarded": besito_value,
                "emoji_id": emoji_id,
                "emoji_char": emoji_char,
            }

        except IntegrityError as exc:
            db.rollback()
            err_text = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
            err_lower = err_text.lower()
            is_duplicate = (
                "uq_broadcast_user_reaction" in err_text
                or "unique constraint failed" in err_lower  # SQLite common message
                or (
                    "unique" in err_lower
                    and "broadcast_reactions" in err_lower
                    and "user_id" in err_lower
                )
            )
            if is_duplicate:
                logger.info(
                    f"broadcast_service | check_and_register_reaction | user_id={user_id} | broadcast_id={broadcast_id} | duplicate"
                )
                return self._reaction_failure("duplicate")
            if "foreign key" in err_lower:
                logger.warning(
                    f"broadcast_service | check_and_register_reaction | user_id={user_id} | broadcast_id={broadcast_id} | invalid_broadcast_fk"
                )
                return self._reaction_failure("invalid_broadcast")
            logger.error(
                f"broadcast_service | check_and_register_reaction | user_id={user_id} | integrity_error={exc}"
            )
            return self._reaction_failure("error")
        except Exception as e:
            db.rollback()
            logger.error(
                f"broadcast_service | check_and_register_reaction | user_id={user_id} | error={e}"
            )
            return self._reaction_failure("error")

    def get_reactions_by_broadcast(self, broadcast_id: int) -> list[BroadcastReaction]:
        """Obtiene todas las reacciones de un mensaje"""
        return (
            self.db.query(BroadcastReaction)
            .options(joinedload(BroadcastReaction.reaction_emoji))
            .filter(BroadcastReaction.broadcast_id == broadcast_id)
            .all()
        )

    def get_reaction_count(self, broadcast_id: int) -> int:
        """Obtiene el número de reacciones de un mensaje"""
        return (
            self.db.query(BroadcastReaction)
            .filter(BroadcastReaction.broadcast_id == broadcast_id)
            .count()
        )

    def get_user_reactions(self, user_id: int, limit: int = 20) -> list[BroadcastReaction]:
        """Obtiene las reacciones de un usuario"""
        return (
            self.db.query(BroadcastReaction)
            .filter(BroadcastReaction.user_id == user_id)
            .order_by(desc(BroadcastReaction.created_at))
            .limit(limit)
            .all()
        )

    # ==================== ESTADÍSTICAS ====================

    def get_broadcast_stats(self, broadcast_id: int) -> dict:
        """Obtiene estadísticas de un mensaje de broadcast"""
        broadcast = self.get_broadcast(broadcast_id)
        if not broadcast:
            return {}

        reactions = self.get_reactions_by_broadcast(broadcast_id)
        total_besitos = sum(r.besitos_awarded for r in reactions)

        # Contar por emoji
        emoji_counts = {}
        for r in reactions:
            emoji_char = r.reaction_emoji.emoji if r.reaction_emoji else "?"
            emoji_counts[emoji_char] = emoji_counts.get(emoji_char, 0) + 1

        return {
            "total_reactions": len(reactions),
            "total_besitos_awarded": total_besitos,
            "emoji_breakdown": emoji_counts,
            "unique_users": len({r.user_id for r in reactions}),
        }

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None
        # Cerrar subs (inofensivo: ellos tienen owns=False cuando db compartido)
        for sub in (getattr(self, "besito_service", None),):
            if sub and hasattr(sub, "close"):
                sub.close()

    async def update_reaction_message(
        self, bot, channel_id: int, message_id: int, new_markup: InlineKeyboardMarkup
    ) -> bool:
        """Actualiza el markup de un mensaje de broadcast con los nuevos conteos."""
        try:
            await bot.edit_message_reply_markup(
                chat_id=channel_id, message_id=message_id, reply_markup=new_markup
            )
            return True
        except Exception as e:
            if "message is not modified" in str(e).lower():
                return True
            logger.warning(
                f"broadcast_service | update_reaction_message | channel_id={channel_id} | message_id={message_id} | error={e}"
            )
            return False


# =============================================================================
# Cross-domain event listeners (registered explicitly from bot.py on startup).
# The listener lives here (broadcast domain ownership). It is a plain async callable
# receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
# (to avoid any re-entrancy with reaction credit paths or future extensions; reaction
# credit contracts and partial-failure behavior are authoritative in the credit + mission
# best-effort flow inside check_and_register_reaction).
# This is observational only (best effort; errors swallowed by bus).
# =============================================================================


async def on_besitos_awarded_broadcast_reaction_observer(payload: dict) -> None:
    """
    Broadcast-domain listener for "besitos_awarded" events (emitted by BesitoService.credit_besitos
    post-commit, including from REACTION credits in check_and_register_reaction).

    DESIRED CONTRACT (copy of narrative precedent + Reward Item5): log reception with full context
    (user_id/amount/source/ref); purely observational + wiring proof for this domain.
    MUST NOT credit, debit, or mutate besitos state here.
    Future extensions (e.g. streak/promo hooks on reaction awards) belong in this module and should use
    get_service(BroadcastService) or direct models if a fresh DB session is required.
    """
    uid = payload.get("user_id")
    amt = payload.get("amount")
    src = payload.get("source")
    ref = payload.get("reference_id")
    logger.info(
        f"broadcast | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"
    )
    # No side effects that mutate besitos here (best effort, non-authoritative; 0 impact on reaction credit contracts / atomicity gold).
