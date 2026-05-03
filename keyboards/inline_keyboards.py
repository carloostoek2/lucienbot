"""
🎩 Teclados Inline - Lucien Bot

Teclados personalizados con la estética elegante de Diana.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional
from models.models import Channel, Tariff


def main_menu_keyboard(is_vip: bool = False, active_promo: dict = None) -> InlineKeyboardMarkup:
    """Menú principal de usuario con gamificación"""
    buttons = []

    # Aviso de promoción activa (si hay)
    if active_promo:
        buttons.append([InlineKeyboardButton(
            text=f"🎯 {active_promo['name']} - ⏱️ {active_promo['remaining_formatted']}",
            callback_data="game_menu"
        )])

    # Solo VIP: El Diván
    if is_vip:
        buttons.append([InlineKeyboardButton(
            text="💎 El Diván",
            callback_data="vip_area"
        )])

    # Ofertas especiales - arriba de todo
    buttons.append([InlineKeyboardButton(
        text="✨ Ofertas especiales",
        callback_data="offers"
    )])

    # Minijuegos - Mochila (misma fila)
    buttons.append([
        InlineKeyboardButton(
            text="🎮 Minijuegos",
            callback_data="game_menu"
        ),
        InlineKeyboardButton(
            text="📦 Mochila",
            callback_data="backpack_menu"
        )
    ])

    # Mi saldo - Regalo diario (misma fila)
    buttons.append([
        InlineKeyboardButton(
            text="💋 Mi saldo de besitos",
            callback_data="my_balance"
        ),
        InlineKeyboardButton(
            text="🎁 Regalo diario",
            callback_data="daily_gift"
        )
    ])

    # Tienda (solo)
    buttons.append([InlineKeyboardButton(
        text="🛍️ Tienda",
        callback_data="shop"
    )])

    # Misiones - Recompensas (misma fila)
    buttons.append([
        InlineKeyboardButton(
            text="🎯 Misiones",
            callback_data="my_missions"
        ),
        InlineKeyboardButton(
            text="🎁 Recompensas",
            callback_data="rewards_list"
        )
    ])

    # Fragmentos de la historia
    buttons.append([InlineKeyboardButton(
        text="📖 Fragmentos de la historia",
        callback_data="narrative"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Menú principal de administrador"""
    buttons = [
        [InlineKeyboardButton(
            text="🏛️ Gestionar dominios (canales)",
            callback_data="admin_channels"
        )],
        [InlineKeyboardButton(
            text="👑 El Diván de Diana (VIP)",
            callback_data="admin_vip"
        )],
        [InlineKeyboardButton(
            text="💌 Susurros del círculo (Mensajes anónimos)",
            callback_data="admin_anonymous_messages"
        )],
        [InlineKeyboardButton(
            text="🎮 Las recompensas que cultivan devoción",
            callback_data="admin_gamification"
        )],
        [InlineKeyboardButton(
            text="🎯 Sets de Preguntas",
            callback_data="admin_question_sets"
        )],
        [InlineKeyboardButton(
            text="✨ Promociones comerciales",
            callback_data="admin_promotions"
        )],
        [InlineKeyboardButton(
            text="📖 Los hilos de la historia",
            callback_data="admin_narrative"
        )],
        [InlineKeyboardButton(
            text="👥 Los visitantes bajo observación",
            callback_data="admin_users"
        )],
        [InlineKeyboardButton(
            text="📊 Los patrones que revelan deseos",
            callback_data="admin_analytics"
        )],
        [InlineKeyboardButton(
            text="⚙️ Calibración del reino",
            callback_data="admin_settings"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_management_keyboard() -> InlineKeyboardMarkup:
    """Menú de gestión de canales"""
    buttons = [
        [InlineKeyboardButton(
            text="➕ Agregar nuevo dominio",
            callback_data="add_channel"
        )],
        [InlineKeyboardButton(
            text="📋 Ver dominios registrados",
            callback_data="list_channels"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver al sanctum",
            callback_data="back_to_admin"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_type_keyboard() -> InlineKeyboardMarkup:
    """Selección de tipo de canal"""
    buttons = [
        [InlineKeyboardButton(
            text="🚪 Vestíbulo (Free)",
            callback_data="channel_type_free"
        )],
        [InlineKeyboardButton(
            text="👑 El Diván (VIP)",
            callback_data="channel_type_vip"
        )],
        [InlineKeyboardButton(
            text="🔙 Cancelar",
            callback_data="cancel"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_actions_keyboard(channel_id: int, channel_type: str) -> InlineKeyboardMarkup:
    """Acciones disponibles para un canal"""
    buttons = []
    
    if channel_type == "free":
        buttons.extend([
            [InlineKeyboardButton(
                text="⏱️ Configurar tiempo de espera",
                callback_data=f"config_wait_{channel_id}"
            )],
            [InlineKeyboardButton(
                text="🔗 Configurar enlace de invitación",
                callback_data=f"config_invite_{channel_id}"
            )],
            [InlineKeyboardButton(
                text="📨 Configurar mensajes",
                callback_data=f"config_messages_{channel_id}"
            )],
            [InlineKeyboardButton(
                text="👥 Ver solicitudes pendientes",
                callback_data=f"pending_req_{channel_id}"
            )],
            [InlineKeyboardButton(
                text="✅ Aprobar todas las pendientes",
                callback_data=f"approve_all_{channel_id}"
            )]
        ])
    else:  # VIP
        buttons.extend([
            [InlineKeyboardButton(
                text="💎 Gestionar tarifas",
                callback_data=f"manage_tariffs_{channel_id}"
            )],
            [InlineKeyboardButton(
                text="🔑 Generar token de acceso",
                callback_data=f"generate_token_{channel_id}"
            )],
            [InlineKeyboardButton(
                text="📋 Ver suscriptores activos",
                callback_data=f"list_subscribers_{channel_id}"
            )]
        ])
    
    buttons.append([InlineKeyboardButton(
        text="🗑️ Eliminar dominio",
        callback_data=f"delete_channel_{channel_id}"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="list_channels"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tariffs_keyboard(tariffs: List[Tariff], for_selection: bool = False) -> InlineKeyboardMarkup:
    """Teclado con lista de tarifas"""
    buttons = []
    
    for tariff in tariffs:
        if not tariff.is_active and for_selection:
            continue
            
        status = "✅" if tariff.is_active else "❌"
        text = f"{status} {tariff.name} - {tariff.duration_days}d - {tariff.price}"
        
        if for_selection:
            callback = f"select_tariff_{tariff.id}"
        else:
            callback = f"edit_tariff_{tariff.id}"
        
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])
    
    if not for_selection:
        buttons.append([InlineKeyboardButton(
            text="➕ Crear nueva tarifa",
            callback_data="create_tariff"
        )])
    
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="admin_vip"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def wait_time_keyboard() -> InlineKeyboardMarkup:
    """Opciones de tiempo de espera"""
    buttons = [
        [
            InlineKeyboardButton(text="2 min", callback_data="wait_2"),
            InlineKeyboardButton(text="3 min", callback_data="wait_3"),
            InlineKeyboardButton(text="5 min", callback_data="wait_5")
        ],
        [
            InlineKeyboardButton(text="10 min", callback_data="wait_10"),
            InlineKeyboardButton(text="15 min", callback_data="wait_15"),
            InlineKeyboardButton(text="30 min", callback_data="wait_30")
        ],
        [InlineKeyboardButton(
            text="⌨️ Personalizado",
            callback_data="wait_custom"
        )],
        [InlineKeyboardButton(
            text="🔙 Cancelar",
            callback_data="cancel"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirmation_keyboard(confirm_callback: str, cancel_callback: str = "cancel") -> InlineKeyboardMarkup:
    """Teclado de confirmación Sí/No"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Confirmar", callback_data=confirm_callback),
            InlineKeyboardButton(text="❌ Cancelar", callback_data=cancel_callback)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_keyboard(back_callback: str = "back_to_admin") -> InlineKeyboardMarkup:
    """Teclado con botón de volver"""
    buttons = [
        [InlineKeyboardButton(text="🔙 Volver", callback_data=back_callback)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Teclado con botón de cancelar"""
    buttons = [
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def broadcast_back_keyboard(current_step: str) -> InlineKeyboardMarkup:
    """Teclado con botón de regresar al paso anterior durante broadcast"""
    back_steps = {
        "waiting_text": ("admin_gamification", "❌ Cancelar"),
        "waiting_attachment": ("attach_no", "🔙 Omitir adjunto"),
        "waiting_attachment_decision": ("waiting_text", "🔙 Volver al texto"),
        "selecting_reactions": ("reaction_no", "🔙 Sin reacciones"),
        "waiting_reaction_decision": ("waiting_attachment_decision", "🔙 Volver"),
        "waiting_protection": ("waiting_reaction_decision", "🔙 Volver"),
        "confirming": ("waiting_protection", "🔙 Volver"),
    }
    
    callback, text = back_steps.get(current_step, ("cancel", "❌ Cancelar"))
    buttons = [
        [InlineKeyboardButton(text=text, callback_data=callback)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vip_management_keyboard() -> InlineKeyboardMarkup:
    """Menú de gestión VIP"""
    buttons = [
        [InlineKeyboardButton(
            text="💰 Gestionar tarifas",
            callback_data="manage_tariffs"
        )],
        [InlineKeyboardButton(
            text="🔑 Generar token de acceso",
            callback_data="generate_token"
        )],
        [InlineKeyboardButton(
            text="📋 Ver tokens generados",
            callback_data="list_tokens"
        )],
        [InlineKeyboardButton(
            text="👥 Ver suscriptores activos",
            callback_data="list_subscribers"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver al sanctum",
            callback_data="back_to_admin"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def token_actions_keyboard(token_id: int) -> InlineKeyboardMarkup:
    """Acciones para un token específico"""
    buttons = [
        [InlineKeyboardButton(
            text="📋 Copiar enlace",
            callback_data=f"copy_token_{token_id}"
        )],
        [InlineKeyboardButton(
            text="🗑️ Revocar token",
            callback_data=f"revoke_token_{token_id}"
        )],
        [InlineKeyboardButton(
            text="🔄 Generar otro token",
            callback_data="generate_another_token"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver a tokens",
            callback_data="list_tokens"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== RITUALES DE ENTRADA (PHASE 10) ====================

def social_links_keyboard() -> InlineKeyboardMarkup:
    """Teclado con enlaces a redes sociales de Diana"""
    buttons = [
        [
            InlineKeyboardButton(text="Instagram", url="https://www.instagram.com/srta.kinky"),
            InlineKeyboardButton(text="TikTok", url="https://www.tiktok.com/@srtakinky"),
            InlineKeyboardButton(text="X", url="https://x.com/srtakinky")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def vip_entry_continue_keyboard() -> InlineKeyboardMarkup:
    """Botón Continuar para Fase 1 del ritual VIP"""
    buttons = [
        [InlineKeyboardButton(text="Continuar", callback_data="vip_entry_continue")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vip_entry_ready_keyboard() -> InlineKeyboardMarkup:
    """Botón Estoy listo para Fase 2 del ritual VIP"""
    buttons = [
        [InlineKeyboardButton(text="Estoy listo", callback_data="vip_entry_ready")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def returning_user_keyboard() -> InlineKeyboardMarkup:
    """Teclado para usuarios que ya estaban en el canal antes del bot"""
    buttons = [
        [InlineKeyboardButton(text="🔍 Explorar", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_anonymous_notification_keyboard(message_id: int) -> InlineKeyboardMarkup:
    """Teclado para notificación de mensaje anónimo a administradores"""
    buttons = [
        [InlineKeyboardButton(
            text="📨 Ver mensaje",
            callback_data=f"anon_view_{message_id}"
        )],
        [InlineKeyboardButton(
            text="🔙 Cerrar",
            callback_data="back_to_admin"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== MINIJUEGOS (PHASE 14) ====================

def game_menu_keyboard(is_vip: bool = False) -> InlineKeyboardMarkup:
    """Menú de selección de juegos"""
    buttons = [
        [InlineKeyboardButton(text="🎲 Lanzar los dados del destino", callback_data="game_dice")],
        [InlineKeyboardButton(text="❓ El examen de Diana", callback_data="game_trivia")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dice_play_keyboard() -> InlineKeyboardMarkup:
    """Botón para jugar dados"""
    buttons = [
        [InlineKeyboardButton(text="🎲 Invocar el destino", callback_data="dice_play")],
        [InlineKeyboardButton(text="🔙 Menú de juegos", callback_data="game_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trivia_keyboard(question: dict, question_idx: int, back_callback: str = "game_menu") -> InlineKeyboardMarkup:
    """Teclado con opciones de trivia A, B, C"""
    buttons = []
    for idx, opt_text in enumerate(question['opts']):
        buttons.append([InlineKeyboardButton(
            text=opt_text,
            callback_data=f"trivia_answer_{idx}_{question_idx}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver al menú de juegos",
        callback_data=back_callback
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trivia_vip_keyboard(question: dict, question_idx: int, back_callback: str = "vip_area") -> InlineKeyboardMarkup:
    """Teclado con opciones de trivia VIP (soporta 4 opciones A, B, C, D)"""
    buttons = []
    for idx, opt_text in enumerate(question['opts']):
        buttons.append([InlineKeyboardButton(
            text=opt_text,
            callback_data=f"trivia_vip_answer_{idx}_{question_idx}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver a El Diván",
        callback_data=back_callback
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trivia_vip_result_keyboard(back_callback: str = "vip_area") -> InlineKeyboardMarkup:
    """Teclado para resultado de trivia VIP con opción de reintentar"""
    buttons = [
        [InlineKeyboardButton(text="🔄 Intentarlo de nuevo", callback_data="game_trivia_vip")],
        [InlineKeyboardButton(text="🔙 Volver a El Diván", callback_data=back_callback)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def discount_claim_keyboard(code: str) -> InlineKeyboardMarkup:
    """Teclado para que el usuario vea y copie su código de descuento"""
    buttons = [
        [InlineKeyboardButton(text="📋 Copiar código", callback_data=f"copy_discount_{code}")],
        [InlineKeyboardButton(text="🔙 Volver al menú", callback_data="game_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
