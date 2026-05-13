"""
Handlers de Gamificación para Usuarios - Lucien Bot

Handlers para funcionalidades de gamificación accesibles por usuarios.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from services.besito_service import BesitoService
from services.daily_gift_service import DailyGiftService
from services.broadcast_service import BroadcastService
from keyboards.inline_keyboards import back_keyboard, main_menu_keyboard, reactions_keyboard_with_counts
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()

# Deduplication set for reaction callbacks (prevents duplicate processing from Telegram retries)
_reaction_callbacks_being_processed = set()


# ==================== CONSULTAR SALDO ====================

@router.callback_query(F.data == "my_balance")
async def show_balance(callback: CallbackQuery):
    """Muestra el saldo de besitos del usuario"""
    user_id = callback.from_user.id

    besito_service = BesitoService()
    try:
        stats = besito_service.get_balance_with_stats(user_id)
    finally:
        besito_service.close()
    
    text = f"""🎩 <b>Lucien:</b>

<i>Permíteme consultar los fragmentos de atención que ha acumulado...</i>

💋 <b>Tu saldo de besitos:</b> {stats['balance']}

📊 <b>Estadísticas:</b>
   • Total acumulado: {stats['total_earned']}
   • Total gastado: {stats['total_spent']}

<i>Diana aprecia cada momento de su atención...</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("back_to_main"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "transaction_history")
async def show_transaction_history(callback: CallbackQuery):
    """Muestra el historial de transacciones"""
    user_id = callback.from_user.id

    besito_service = BesitoService()
    try:
        transactions = besito_service.get_transaction_history(user_id, limit=10)
    finally:
        besito_service.close()
    
    if not transactions:
        text = f"""🎩 <b>Lucien:</b>

<i>Aún no hay movimientos registrados en su cuenta...</i>

💋 <b>Tu historial está vacío.</b>

<i>Interactúe más con el reino para acumular besitos.</i>"""
    else:
        text = f"""🎩 <b>Lucien:</b>

<i>Los movimientos de su moneda especial...</i>

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
                "TRIVIA": "Trivia"
            }.get(tx.source.value, tx.source.value)
            
            text += f"{emoji} <b>{'+' if tx.amount > 0 else ''}{tx.amount}</b> - {source_name}\n"
            text += f"   <i>{date_str}</i>\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("my_balance"),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== REGALO DIARIO ====================

@router.callback_query(F.data == "daily_gift")
async def daily_gift_menu(callback: CallbackQuery):
    """Menú del regalo diario"""
    user_id = callback.from_user.id

    gift_service = DailyGiftService()
    try:
        can_claim, time_remaining, message = gift_service.can_claim(user_id)
    finally:
        gift_service.close()
    
    if can_claim:
        amount = gift_service.get_gift_amount()
        text = f"""🎩 <b>Lucien:</b>

<i>Diana tiene un obsequio especial para usted hoy...</i>

🎁 <b>Regalo Diario Disponible</b>

💋 <b>Cantidad:</b> {amount} besitos

<i>¿Desea reclamar su regalo?</i>"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Reclamar regalo", callback_data="claim_gift")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")]
        ])
    else:
        text = f"""🎩 <b>Lucien:</b>

<i>La generosidad de Diana tiene sus tiempos...</i>

⏳ <b>Regalo Diario</b>

{message}

<i>Vuelva más tarde para recibir su próximo obsequio.</i>"""
        
        keyboard = back_keyboard("back_to_main")
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "claim_gift")
async def claim_daily_gift(callback: CallbackQuery):
    """Procesa el reclamo del regalo diario"""
    user_id = callback.from_user.id

    gift_service = DailyGiftService()
    try:
        success, amount, message = gift_service.claim_gift(user_id)
    finally:
        gift_service.close()
    
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
        text,
        reply_markup=back_keyboard("back_to_main"),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== REACCIONES A BROADCAST ====================

from keyboards.callback_data import ReactionCallback

@router.callback_query(ReactionCallback.filter())
async def handle_reaction(callback: CallbackQuery, callback_data: ReactionCallback):
    """Maneja las reacciones a mensajes de broadcast y actualiza conteos"""
    user = callback.from_user

    # Datos extraídos type-safe del CallbackData
    broadcast_id = callback_data.broadcast_id
    emoji_id = callback_data.emoji_id

    # Deduplication key para prevenir procesamiento duplicado
    dedup_key = f"{user.id}:{broadcast_id}:{emoji_id}"

    # Verificar si ya estamos procesando este callback (race condition protection)
    if dedup_key in _reaction_callbacks_being_processed:
        logger.debug(f"Callback duplicado ignorado: {dedup_key}")
        await callback.answer("Procesando tu reacción...", show_alert=False)
        return

    # Marcar como en proceso
    _reaction_callbacks_being_processed.add(dedup_key)

    try:
        broadcast_service = BroadcastService()

        # Registrar reacción con entrega automática de recompensas (verificación y registro atómico)
        reaction = await broadcast_service.check_and_register_reaction(
            broadcast_id=broadcast_id,
            user_id=user.id,
            emoji_id=emoji_id,
            username=user.username,
            bot=callback.bot
        )

        if reaction:
            # reaction ahora es un diccionario, usar los datos directamente
            emoji_char = reaction.get('emoji_char', '💋')
            besitos = reaction.get('besitos_awarded', 0)

            # Obtener el broadcast para actualizar el mensaje
            broadcast = broadcast_service.get_broadcast(broadcast_id)
            if broadcast and broadcast.has_reactions:
                # Obtener TODOS los emojis originales del broadcast
                selected_emoji_ids = broadcast_service.get_selected_emoji_ids(broadcast_id)

                # Obtener conteo actualizado de reacciones
                reactions = broadcast_service.get_reactions_by_broadcast(broadcast_id)

                # Contar reacciones por emoji
                emoji_counts = {}
                for r in reactions:
                    if r.reaction_emoji:
                        emoji_id_val = r.reaction_emoji.id
                        emoji_counts[emoji_id_val] = emoji_counts.get(emoji_id_val, 0) + 1

                # Construir lista de emojis para el keyboard
                emojis = []
                for emoji_id in selected_emoji_ids:
                    emoji_obj = broadcast_service.get_reaction_emoji(emoji_id)
                    if emoji_obj:
                        emojis.append((emoji_id, emoji_obj.emoji))

                # Usar función extractada para reconstruir el teclado
                if emojis:
                    new_markup = reactions_keyboard_with_counts(
                        broadcast_id, emojis, emoji_counts
                    )
                    # Usar método extractado para actualizar mensaje
                    await broadcast_service.update_reaction_message(
                        bot=callback.bot,
                        channel_id=broadcast.channel_id,
                        message_id=broadcast.message_id,
                        new_markup=new_markup
                    )

            # Logging de la reacción recibida
            logger.info(f"Reaction processed: user={user.id}, broadcast={broadcast_id}, emoji={emoji_id}, besitos={besitos}")

            # Solo notificar via callback (sin mensaje privado)
            await callback.answer(f"¡+{besitos} besitos! 💋")
        else:
            await callback.answer("Ya reaccionaste a este mensaje", show_alert=True)

    finally:
        # Siempre remover el dedup key al finalizar
        _reaction_callbacks_being_processed.discard(dedup_key)



