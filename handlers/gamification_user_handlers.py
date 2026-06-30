"""
Handlers de Gamificación para Usuarios - Lucien Bot

Handlers para funcionalidades de gamificación accesibles por usuarios.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callback_data import ReactionCallback
from keyboards.inline_keyboards import (
    back_keyboard,
    reactions_keyboard_with_counts,
)
from services import get_service
from services.besito_service import BesitoService
from services.broadcast_service import BroadcastService
from services.daily_gift_service import DailyGiftService
from utils.admin import is_admin

logger = logging.getLogger(__name__)
router = Router()


# ==================== CONSULTAR SALDO ====================


@router.callback_query(F.data == "my_balance", lambda cb: not is_admin(cb.from_user.id))
async def show_balance(callback: CallbackQuery):
    """Muestra el saldo de besitos del usuario"""
    user_id = callback.from_user.id

    with get_service(BesitoService) as besito_service:
        stats = besito_service.get_balance_with_stats(user_id)

    text = f"""🎩 <b>Lucien:</b>

<i>Permíteme consultar los fragmentos de atención que ha acumulado...</i>

💋 <b>Tu saldo de besitos:</b> {stats["balance"]}

📊 <b>Estadísticas:</b>
   • Total acumulado: {stats["total_earned"]}
   • Total gastado: {stats["total_spent"]}

<i>Diana aprecia cada momento de su atención...</i>"""

    await callback.message.edit_text(
        text, reply_markup=back_keyboard("back_to_main"), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "transaction_history", lambda cb: not is_admin(cb.from_user.id))
async def show_transaction_history(callback: CallbackQuery):
    """Muestra el historial de transacciones"""
    user_id = callback.from_user.id

    with get_service(BesitoService) as besito_service:
        transactions = besito_service.get_transaction_history(user_id, limit=10)

    if not transactions:
        text = """🎩 <b>Lucien:</b>

<i>Aún no hay movimientos registrados en su cuenta...</i>

💋 <b>Tu historial está vacío.</b>

<i>Interactúe más con el reino para acumular besitos.</i>"""
    else:
        text = """🎩 <b>Lucien:</b>

<i>Historial de sus besitos:</i>

📋 <b>Últimas transacciones:</b>

"""
        for tx in transactions:
            emoji = "💚" if tx.amount > 0 else "💔"
            date_str = tx.created_at.strftime("%d/%m %H:%M") if tx.created_at else "?"
            source_name = {
                "reaction": "Reacción",
                "daily_gift": "Regalo diario",
                "mission": "Misión",
                "purchase": "Compra",
                "admin": "Admin",
                "anonymous_message": "Mensaje anónimo",
                "GAME": "Juego",
                "TRIVIA": "Trivia",
            }.get(tx.source.value, tx.source.value)

            text += f"{emoji} <b>{'+' if tx.amount > 0 else ''}{tx.amount}</b> - {source_name}\n"
            text += f"   <i>{date_str}</i>\n\n"

    await callback.message.edit_text(
        text, reply_markup=back_keyboard("my_balance"), parse_mode="HTML"
    )
    await callback.answer()


# ==================== REGALO DIARIO ====================


@router.callback_query(F.data == "daily_gift", lambda cb: not is_admin(cb.from_user.id))
async def daily_gift_menu(callback: CallbackQuery):
    """Menú del regalo diario"""
    user_id = callback.from_user.id

    with get_service(DailyGiftService) as gift_service:
        can_claim, time_remaining, message = gift_service.can_claim(user_id)

        if can_claim:
            amount = gift_service.get_gift_amount()
            text = f"""🎩 <b>Lucien:</b>

<i>Diana tiene un obsequio especial para usted hoy...</i>

🎁 <b>Regalo Diario Disponible</b>

💋 <b>Cantidad:</b> {amount} besitos

<i>¿Desea reclamar su regalo?</i>"""

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🎁 Reclamar regalo", callback_data="claim_gift")],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")],
                ]
            )
        else:
            text = f"""🎩 <b>Lucien:</b>

<i>La generosidad de Diana tiene sus tiempos...</i>

⏳ <b>Regalo Diario</b>

{message}

<i>Vuelva más tarde para recibir su próximo obsequio.</i>"""

            keyboard = back_keyboard("back_to_main")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "claim_gift", lambda cb: not is_admin(cb.from_user.id))
async def claim_daily_gift(callback: CallbackQuery):
    """Procesa el reclamo del regalo diario"""
    user_id = callback.from_user.id

    with get_service(DailyGiftService) as gift_service:
        success, amount, message = await gift_service.claim_gift_with_missions(
            user_id, bot=callback.bot
        )

    if success:
        text = f"""🎩 <b>Lucien:</b>

<i>Diana se complace con su dedicación...</i>

✅ <b>¡Regalo reclamado!</b>

{message}

<i>Mañana habrá más besitos esperándole...</i>"""
    else:
        text = f"""🎩 <b>Lucien:</b>

<i>Hmm... algo ocurrió con su solicitud...</i>

⚠️ {message}"""

    await callback.message.edit_text(
        text, reply_markup=back_keyboard("back_to_main"), parse_mode="HTML"
    )
    await callback.answer()


# ==================== REACCIONES A BROADCAST ====================


def calculate_emoji_counts_from_reactions(reactions: list) -> dict[int, int]:
    """Calcula el mapa de conteos de emojis a partir de reacciones registradas. Función pura."""
    emoji_counts: dict[int, int] = {}
    for r in reactions:
        if r.reaction_emoji:
            emoji_id_val = r.reaction_emoji.id
            emoji_counts[emoji_id_val] = emoji_counts.get(emoji_id_val, 0) + 1
    return emoji_counts


REACTION_FAILURE_MESSAGES = {
    "duplicate": "Ya reaccionaste a este mensaje",
    "invalid_broadcast": "Este mensaje ya no está disponible para reaccionar.",
    "message_mismatch": "Este mensaje ya no está disponible para reaccionar.",
    "no_reactions": "Este mensaje no acepta reacciones.",
    "inactive_emoji": "Esta reacción no está disponible en este mensaje.",
    "emoji_not_allowed": "Esta reacción no está disponible en este mensaje.",
    "invalid_emoji": "Emoji no válido.",
    "credit_failed": "No pudimos registrar tu reacción. Inténtalo de nuevo.",
}


def reaction_failure_message(reason: str) -> str:
    """Mensaje de error para el usuario según el motivo de fallo. Función pura."""
    return REACTION_FAILURE_MESSAGES.get(
        reason, "No pudimos procesar tu reacción. Inténtalo de nuevo."
    )


async def refresh_reaction_markup_counts(
    broadcast_service: BroadcastService,
    bot,
    broadcast,
    broadcast_id: int,
) -> None:
    """Reconstruye y actualiza el teclado de reacciones con conteos (preserva botón extra URL si existe)."""
    selected_emoji_ids = broadcast_service.get_selected_emoji_ids(broadcast_id)
    reactions = broadcast_service.get_reactions_by_broadcast(broadcast_id)
    emoji_counts = calculate_emoji_counts_from_reactions(reactions)
    emojis = []
    for selected_emoji_id in selected_emoji_ids:
        emoji_obj = broadcast_service.get_reaction_emoji(selected_emoji_id)
        if emoji_obj:
            emojis.append((selected_emoji_id, emoji_obj.emoji))

    # Preservar extra button: usar reactions_keyboard_with_counts (estable) para fila de reacciones + fila URL manual si extra.
    # NO modificar reactions_keyboard_with_counts.
    extra_button = None
    extra_id = getattr(broadcast, "extra_button_id", None)
    if isinstance(extra_id, int):
        extra_button = broadcast_service.get_broadcast_button(extra_id)

    if emojis:
        # Fila de reacciones con conteos (estable)
        reaction_markup = reactions_keyboard_with_counts(broadcast_id, emojis, emoji_counts)
        rows = (
            list(reaction_markup.inline_keyboard)
            if reaction_markup and reaction_markup.inline_keyboard
            else []
        )
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        if extra_button:
            rows.append([InlineKeyboardButton(text=extra_button.label, url=extra_button.url)])
        new_markup = InlineKeyboardMarkup(inline_keyboard=rows) if rows else None
    else:
        if extra_button:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

            new_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=extra_button.label, url=extra_button.url)]
                ]
            )
        else:
            new_markup = None

    if new_markup is not None:
        await broadcast_service.update_reaction_message(
            bot=bot,
            channel_id=broadcast.channel_id,
            message_id=broadcast.message_id,
            new_markup=new_markup,
        )


@router.callback_query(ReactionCallback.filter())
async def handle_reaction(callback: CallbackQuery, callback_data: ReactionCallback):
    """Maneja las reacciones a mensajes de broadcast y actualiza conteos"""
    if not callback.message:
        await callback.answer(
            "No pudimos procesar tu reacción. Inténtalo de nuevo.", show_alert=True
        )
        return

    user = callback.from_user
    broadcast_id = callback_data.broadcast_id
    emoji_id = callback_data.emoji_id

    if is_admin(user.id):
        await callback.answer("Los custodios observan con elegancia...")
        return

    with get_service(BroadcastService) as broadcast_service:
        result = await broadcast_service.check_and_register_reaction(
            broadcast_id=broadcast_id,
            user_id=user.id,
            emoji_id=emoji_id,
            username=user.username,
            bot=callback.bot,
            channel_id=callback.message.chat.id,
            message_id=callback.message.message_id,
        )

        if result.get("success"):
            besitos = result.get("besitos_awarded", 0)
            broadcast = broadcast_service.get_broadcast(broadcast_id)
            if broadcast and broadcast.has_reactions:
                await refresh_reaction_markup_counts(
                    broadcast_service, callback.bot, broadcast, broadcast_id
                )
            logger.info(
                f"gamification_user_handlers | handle_reaction | user_id={user.id} | broadcast_id={broadcast_id} | emoji={emoji_id} | besitos={besitos}"
            )
            await callback.answer(f"¡+{besitos} besitos! 💋")
        else:
            reason = result.get("reason", "error")
            logger.info(
                f"gamification_user_handlers | handle_reaction | user_id={user.id} | broadcast_id={broadcast_id} | emoji={emoji_id} | reason={reason}"
            )
            await callback.answer(reaction_failure_message(reason), show_alert=True)
