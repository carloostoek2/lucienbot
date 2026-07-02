"""
🎩 Teclados Inline - Lucien Bot

Teclados personalizados con la estética elegante de Diana.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callback_data import (
    AnonViewCallback,
    ApproveAllCallback,
    ChannelDetailCallback,
    ConfigInviteCallback,
    ConfigMessagesCallback,
    ConfigWaitCallback,
    CopyTokenCallback,
    DeleteChannelCallback,
    PendingReqCallback,
    SelectTariffCallback,
    StreakContinueCallback,
    StreakProtectAcceptCallback,
    StreakProtectDeclineCallback,
    StreakRetireCallback,
    SubscriberActionCallback,
    SubscriberConfirmCallback,
    SubscriberExtendTariffCallback,
    SubscriberListCallback,
    SubscriberProfileCallback,
    ToggleGiftCallback,
    TriviaAnswerCallback,
    TriviaSimpleAnswerCallback,
    TriviaVipAnswerCallback,
    WaitTimeCallback,
)
from models.models import Tariff
from utils.lucien_voice import LucienVoice


def main_menu_keyboard(is_vip: bool = False) -> InlineKeyboardMarkup:
    """Menú principal de usuario con gamificación"""
    buttons = []

    # Solo VIP: El Diván
    if is_vip:
        buttons.append([InlineKeyboardButton(text="💎 El Diván", callback_data="vip_area")])

    # Ofertas especiales - arriba de todo
    buttons.append([InlineKeyboardButton(text="✨ Ofertas especiales", callback_data="offers")])

    # Minijuegos - Mochila (misma fila)
    buttons.append(
        [
            InlineKeyboardButton(text="🎮 Minijuegos", callback_data="game_menu"),
            InlineKeyboardButton(text="📦 Mochila", callback_data="backpack_menu"),
        ]
    )

    # Mi saldo - Regalo diario (misma fila)
    buttons.append(
        [
            InlineKeyboardButton(text="💋 Mi saldo de besitos", callback_data="my_balance"),
            InlineKeyboardButton(text="🎁 Regalo diario", callback_data="daily_gift"),
        ]
    )

    # Tienda (solo)
    buttons.append(
        [InlineKeyboardButton(text=LucienVoice.main_menu_shop_button(), callback_data="shop")]
    )

    # Misiones - Recompensas (misma fila)
    buttons.append(
        [
            InlineKeyboardButton(text="🎯 Misiones", callback_data="my_missions"),
            InlineKeyboardButton(text="🎁 Recompensas", callback_data="rewards_list"),
        ]
    )

    # Fragmentos de la historia
    buttons.append(
        [InlineKeyboardButton(text="📖 Fragmentos de la historia", callback_data="narrative")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Menú principal de administrador"""
    buttons = [
        [
            InlineKeyboardButton(
                text="🏛️ Gestionar dominios (canales)", callback_data="admin_channels"
            )
        ],
        [InlineKeyboardButton(text="🎯 Trivias", callback_data="admin_trivia")],
        [InlineKeyboardButton(text="👑 El Diván de Diana (VIP)", callback_data="admin_vip")],
        [
            InlineKeyboardButton(
                text="💌 Susurros del círculo (Mensajes anónimos)",
                callback_data="admin_anonymous_messages",
            )
        ],
        [
            InlineKeyboardButton(
                text="🎮 Las recompensas que cultivan devoción", callback_data="admin_gamification"
            )
        ],
        [InlineKeyboardButton(text="✨ Promociones comerciales", callback_data="admin_promotions")],
        [InlineKeyboardButton(text="📖 Los hilos de la historia", callback_data="admin_narrative")],
        [
            InlineKeyboardButton(
                text="👥 Los visitantes bajo observación", callback_data="admin_users"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Los patrones que revelan deseos", callback_data="admin_analytics"
            )
        ],
        [InlineKeyboardButton(text="🛡️ Pulso del reino / Salud", callback_data="admin_health")],
        [InlineKeyboardButton(text="⚙️ Calibración del reino", callback_data="admin_settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trivia_admin_keyboard() -> InlineKeyboardMarkup:
    """Menú de administración de Trivias"""
    buttons = [
        [
            InlineKeyboardButton(
                text="🎯 Mazos de preguntas", callback_data="admin_trivia_categories"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆 Promos por rachas", callback_data="admin_streak_promotions"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Configuración de trivias", callback_data="admin_trivia_config"
            )
        ],
        [InlineKeyboardButton(text="🔙 Panel de administración", callback_data="back_to_admin")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_management_keyboard() -> InlineKeyboardMarkup:
    """Menú de gestión de canales"""
    buttons = [
        [InlineKeyboardButton(text="➕ Agregar nuevo dominio", callback_data="add_channel")],
        [InlineKeyboardButton(text="📋 Ver dominios registrados", callback_data="list_channels")],
        [InlineKeyboardButton(text="🔙 Volver al sanctum", callback_data="back_to_admin")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_type_keyboard() -> InlineKeyboardMarkup:
    """Selección de tipo de canal"""
    from keyboards.callback_data import ChannelTypeCallback

    buttons = [
        [
            InlineKeyboardButton(
                text="🚪 Vestíbulo (Free)", callback_data=ChannelTypeCallback(action="free").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="👑 El Diván (VIP)", callback_data=ChannelTypeCallback(action="vip").pack()
            )
        ],
        [InlineKeyboardButton(text="🔙 Cancelar", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_actions_keyboard(channel_id: int, channel_type: str) -> InlineKeyboardMarkup:
    """Acciones disponibles para un canal"""
    buttons = []

    if channel_type == "free":
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="⏱️ Configurar tiempo de espera",
                        callback_data=ConfigWaitCallback(channel_id=channel_id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔗 Configurar enlace de invitación",
                        callback_data=ConfigInviteCallback(channel_id=channel_id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📨 Configurar mensajes",
                        callback_data=ConfigMessagesCallback(channel_id=channel_id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👥 Ver solicitudes pendientes",
                        callback_data=PendingReqCallback(channel_id=channel_id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ Aprobar todas las pendientes",
                        callback_data=ApproveAllCallback(channel_id=channel_id).pack(),
                    )
                ],
            ]
        )
    else:  # VIP
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="💎 Gestionar tarifas", callback_data=f"manage_tariffs_{channel_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔑 Generar token de acceso",
                        callback_data=f"generate_token_{channel_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Ver suscriptores activos",
                        callback_data=SubscriberListCallback(channel_id=channel_id, page=0).pack(),
                    )
                ],
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🗑️ Eliminar dominio",
                callback_data=DeleteChannelCallback(channel_id=channel_id).pack(),
            )
        ]
    )
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="list_channels")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tariffs_keyboard(tariffs: list[Tariff], for_selection: bool = False) -> InlineKeyboardMarkup:
    """Teclado con lista de tarifas"""
    buttons = []

    for tariff in tariffs:
        if not tariff.is_active and for_selection:
            continue

        status = "✅" if tariff.is_active else "❌"
        text = f"{status} {tariff.name} - {tariff.duration_days}d - {tariff.price}"

        if for_selection:
            callback = SelectTariffCallback(tariff_id=tariff.id).pack()
        else:
            callback = f"edit_tariff_{tariff.id}"

        buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])

    if not for_selection:
        buttons.append(
            [InlineKeyboardButton(text="➕ Crear nueva tarifa", callback_data="create_tariff")]
        )

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_vip")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def wait_time_keyboard() -> InlineKeyboardMarkup:
    """Opciones de tiempo de espera"""
    buttons = [
        [
            InlineKeyboardButton(text="2 min", callback_data=WaitTimeCallback(minutes="2").pack()),
            InlineKeyboardButton(text="3 min", callback_data=WaitTimeCallback(minutes="3").pack()),
            InlineKeyboardButton(text="5 min", callback_data=WaitTimeCallback(minutes="5").pack()),
        ],
        [
            InlineKeyboardButton(
                text="10 min", callback_data=WaitTimeCallback(minutes="10").pack()
            ),
            InlineKeyboardButton(
                text="15 min", callback_data=WaitTimeCallback(minutes="15").pack()
            ),
            InlineKeyboardButton(
                text="30 min", callback_data=WaitTimeCallback(minutes="30").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="⌨️ Personalizado", callback_data=WaitTimeCallback(minutes="custom").pack()
            )
        ],
        [InlineKeyboardButton(text="🔙 Cancelar", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirmation_keyboard(
    confirm_callback: str, cancel_callback: str = "cancel"
) -> InlineKeyboardMarkup:
    """Teclado de confirmación Sí/No"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Confirmar", callback_data=confirm_callback),
            InlineKeyboardButton(text="❌ Cancelar", callback_data=cancel_callback),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_keyboard(back_callback: str = "back_to_admin") -> InlineKeyboardMarkup:
    """Teclado con botón de volver"""
    buttons = [[InlineKeyboardButton(text="🔙 Volver", callback_data=back_callback)]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_keyboard(callback_data: str = "cancel") -> InlineKeyboardMarkup:
    """Teclado con botón de cancelar"""
    buttons = [[InlineKeyboardButton(text="❌ Cancelar", callback_data=callback_data)]]
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
    buttons = [[InlineKeyboardButton(text=text, callback_data=callback)]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def forward_action_keyboard() -> InlineKeyboardMarkup:
    """Menú de acción tras reenvío admin: VIP o besitos."""
    from keyboards.callback_data import ForwardActionCallback, ForwardCancelCallback

    buttons = [
        [
            InlineKeyboardButton(
                text="👑 Activar VIP",
                callback_data=ForwardActionCallback(action="vip").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="💋 Otorgar besitos",
                callback_data=ForwardActionCallback(action="besitos").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Cancelar",
                callback_data=ForwardCancelCallback().pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def forward_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Confirmación Sí/No para grant forward admin (action: vip | besitos)."""
    from keyboards.callback_data import ForwardCancelCallback, ForwardConfirmCallback

    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Confirmar",
                callback_data=ForwardConfirmCallback(action=action).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Cancelar",
                callback_data=ForwardCancelCallback().pack(),
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def forward_cancel_keyboard() -> InlineKeyboardMarkup:
    """Solo cancelar en flujo forward admin."""
    from keyboards.callback_data import ForwardCancelCallback

    buttons = [
        [InlineKeyboardButton(text="❌ Cancelar", callback_data=ForwardCancelCallback().pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscriber_list_keyboard(
    subs: list, channel_id: int, page: int, total_count: int, page_size: int = 8
) -> InlineKeyboardMarkup:
    """Teclado paginado de suscriptores activos (filas clicables → perfil)."""
    import math

    buttons: list[list[InlineKeyboardButton]] = []
    for sub in subs:
        user = getattr(sub, "user", None)
        if user and user.username:
            label = f"@{user.username}"
        elif user and user.first_name:
            label = user.first_name
        else:
            label = f"ID {sub.user_id}"
        expiry = sub.end_date.strftime("%d/%m") if sub.end_date else "?"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"👤 {label[:18]} — {expiry}",
                    callback_data=SubscriberProfileCallback(
                        subscription_id=sub.id, channel_id=channel_id, page=page
                    ).pack(),
                )
            ]
        )
    total_pages = max(1, math.ceil(total_count / page_size))
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="◀️ Anterior",
                callback_data=SubscriberListCallback(channel_id=channel_id, page=page - 1).pack(),
            )
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text="Siguiente ▶️",
                callback_data=SubscriberListCallback(channel_id=channel_id, page=page + 1).pack(),
            )
        )
    if nav:
        buttons.append(nav)
    back_cb = (
        ChannelDetailCallback(channel_id=channel_id).pack()
        if channel_id
        else "admin_vip"
    )
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscriber_profile_keyboard(
    subscription_id: int, channel_id: int = 0, page: int = 0
) -> InlineKeyboardMarkup:
    """Acciones admin sobre un suscriptor + volver a lista."""
    ctx = {"subscription_id": subscription_id, "channel_id": channel_id, "page": page}
    buttons = [
        [
            InlineKeyboardButton(
                text="⏳ Extender VIP",
                callback_data=SubscriberActionCallback(action="extend", **ctx).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="💋 Otorgar besitos",
                callback_data=SubscriberActionCallback(action="grant_besitos", **ctx).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="💸 Debitar besitos",
                callback_data=SubscriberActionCallback(action="debit_besitos", **ctx).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🚪 Expulsar",
                callback_data=SubscriberActionCallback(action="kick", **ctx).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Volver a lista",
                callback_data=SubscriberListCallback(channel_id=channel_id, page=page).pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscriber_extend_tariffs_keyboard(
    tariffs: list, subscription_id: int, channel_id: int = 0, page: int = 0
) -> InlineKeyboardMarkup:
    """Tarifas activas para extender VIP."""
    buttons: list[list[InlineKeyboardButton]] = []
    for tariff in tariffs:
        if not tariff.is_active:
            continue
        text = f"{tariff.name} — {tariff.duration_days}d"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=SubscriberExtendTariffCallback(
                        subscription_id=subscription_id,
                        tariff_id=tariff.id,
                        channel_id=channel_id,
                        page=page,
                    ).pack(),
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Volver al perfil",
                callback_data=SubscriberProfileCallback(
                    subscription_id=subscription_id, channel_id=channel_id, page=page
                ).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscriber_confirm_keyboard(
    action: str, subscription_id: int, channel_id: int = 0, page: int = 0
) -> InlineKeyboardMarkup:
    """Confirmar o cancelar acción admin sobre suscriptor."""
    ctx = {
        "action": action,
        "subscription_id": subscription_id,
        "channel_id": channel_id,
        "page": page,
    }
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Confirmar",
                callback_data=SubscriberConfirmCallback(**ctx).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Cancelar",
                callback_data=SubscriberProfileCallback(
                    subscription_id=subscription_id, channel_id=channel_id, page=page
                ).pack(),
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vip_management_keyboard() -> InlineKeyboardMarkup:
    """Menú de gestión VIP"""
    buttons = [
        [InlineKeyboardButton(text="💰 Gestionar tarifas", callback_data="manage_tariffs")],
        [InlineKeyboardButton(text="🔑 Generar token de acceso", callback_data="generate_token")],
        [InlineKeyboardButton(text="📋 Ver tokens generados", callback_data="list_tokens")],
        [
            InlineKeyboardButton(
                text="👥 Ver suscriptores activos",
                callback_data=SubscriberListCallback(channel_id=0, page=0).pack(),
            )
        ],
        [InlineKeyboardButton(text="🔙 Volver al sanctum", callback_data="back_to_admin")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def token_actions_keyboard(token_id: int, is_gift: bool = False) -> InlineKeyboardMarkup:
    """Acciones para un token específico"""
    gift_label = "🎁 Quitar marca de regalo" if is_gift else "🎁 Convertir en regalo"
    buttons = [
        [
            InlineKeyboardButton(
                text="📋 Copiar enlace", callback_data=CopyTokenCallback(token_id=token_id).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=gift_label,
                callback_data=ToggleGiftCallback(token_id=token_id, is_gift=not is_gift).pack(),
            )
        ],
        [InlineKeyboardButton(text="🗑️ Revocar token", callback_data=f"revoke_token_{token_id}")],
        [
            InlineKeyboardButton(
                text="🔄 Generar otro token", callback_data="generate_another_token"
            )
        ],
        [InlineKeyboardButton(text="🔙 Volver a tokens", callback_data="list_tokens")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== RITUALES DE ENTRADA (PHASE 10) ====================


def social_links_keyboard() -> InlineKeyboardMarkup:
    """Teclado con enlaces a redes sociales de Diana"""
    buttons = [
        [
            InlineKeyboardButton(text="Instagram", url="https://www.instagram.com/srta.kinky"),
            InlineKeyboardButton(text="TikTok", url="https://www.tiktok.com/@srtakinky"),
            InlineKeyboardButton(text="X", url="https://x.com/srtakinky"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vip_access_keyboard() -> InlineKeyboardMarkup:
    """Botón Volver al menú para acceso VIP directo"""
    buttons = [[InlineKeyboardButton(text="🔙 Volver al menú", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def returning_user_keyboard() -> InlineKeyboardMarkup:
    """Teclado para usuarios que ya estaban en el canal antes del bot"""
    buttons = [[InlineKeyboardButton(text="🔍 Explorar", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_anonymous_notification_keyboard(message_id: int) -> InlineKeyboardMarkup:
    """Teclado para notificación de mensaje anónimo a administradores"""
    buttons = [
        [
            InlineKeyboardButton(
                text="📨 Ver mensaje", callback_data=AnonViewCallback(message_id=message_id).pack()
            )
        ],
        [InlineKeyboardButton(text="🔙 Cerrar", callback_data="back_to_admin")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== MINIJUEGOS (PHASE 14) ====================


def game_menu_keyboard(is_vip: bool = False, special_button: tuple = None) -> InlineKeyboardMarkup:
    """Menú de selección de juegos. Si special_button = (label, callback), anade boton extra."""
    buttons = [
        [InlineKeyboardButton(text="🎲 Dados", callback_data="game_dice")],
    ]
    if special_button:
        label, cb_data = special_button
        buttons.append([InlineKeyboardButton(text=label, callback_data=cb_data)])
    buttons.append(
        [InlineKeyboardButton(text="❓ Trivia", callback_data="game_trivia")]
    )
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dice_play_keyboard() -> InlineKeyboardMarkup:
    """Botón para jugar dados"""
    buttons = [
        [InlineKeyboardButton(text="🎲 Invocar el destino", callback_data="dice_play")],
        [InlineKeyboardButton(text="🔙 Menú de juegos", callback_data="game_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trivia_keyboard(
    question: dict, question_idx: int, back_callback: str = "game_menu"
) -> InlineKeyboardMarkup:
    """Teclado con opciones de trivia A, B, C"""
    buttons = []
    for idx, opt_text in enumerate(question["opts"]):
        buttons.append(
            [
                InlineKeyboardButton(
                    text=opt_text,
                    callback_data=TriviaAnswerCallback(
                        answer_idx=idx, question_idx=question_idx
                    ).pack(),
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 Volver a minijuegos", callback_data=back_callback)]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trivia_vip_keyboard(
    question: dict, question_idx: int, back_callback: str = "vip_area"
) -> InlineKeyboardMarkup:
    """Teclado con opciones de trivia VIP (soporta 4 opciones A, B, C, D)"""
    buttons = []
    for idx, opt_text in enumerate(question["opts"]):
        buttons.append(
            [
                InlineKeyboardButton(
                    text=opt_text,
                    callback_data=TriviaVipAnswerCallback(
                        answer_idx=idx, question_idx=question_idx
                    ).pack(),
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 Volver a El Diván", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trivia_vip_result_keyboard(back_callback: str = "vip_area") -> InlineKeyboardMarkup:
    """Teclado para resultado de trivia VIP con opción de reintentar"""
    buttons = [
        [InlineKeyboardButton(text="🔄 Intentarlo de nuevo", callback_data="game_trivia_vip")],
        [InlineKeyboardButton(text="🔙 Volver a El Diván", callback_data=back_callback)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trivia_simple_keyboard(question: dict, question_idx: int) -> InlineKeyboardMarkup:
    """Teclado con opciones de trivia especial."""
    buttons = []
    for idx, opt_text in enumerate(question["opts"]):
        buttons.append(
            [
                InlineKeyboardButton(
                    text=opt_text,
                    callback_data=TriviaSimpleAnswerCallback(
                        answer_idx=idx, question_idx=question_idx
                    ).pack(),
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 Volver a minijuegos", callback_data="game_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trivia_simple_result_keyboard() -> InlineKeyboardMarkup:
    """Teclado para resultado de trivia especial."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🔄 Otra pregunta especial", callback_data="game_trivia_simple"
            )
        ],
        [InlineKeyboardButton(text="🔙 Volver a minijuegos", callback_data="game_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== PHASE 18: PROTECCION DE RACHA ====================


def protection_keyboard(protection_cost: int, streak: int, game_type: str) -> InlineKeyboardMarkup:
    """Teclado para decision de proteccion de racha."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"Proteger (-{protection_cost} besitos)",
                callback_data=StreakProtectAcceptCallback(
                    streak=streak, game_type=game_type
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="No proteger",
                callback_data=StreakProtectDeclineCallback(
                    streak=streak, game_type=game_type
                ).pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def risk_mode_keyboard() -> InlineKeyboardMarkup:
    """Teclado para modo arriesgo: continuar o retirarse."""
    buttons = [
        [InlineKeyboardButton(text="Continuar", callback_data=StreakContinueCallback().pack())],
        [
            InlineKeyboardButton(
                text="Retirarse y conservar codigos", callback_data=StreakRetireCallback().pack()
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== REACCIONES BROADCAST ====================


def reactions_keyboard_with_counts(
    broadcast_id: int, emojis: list[tuple[int, str]], emoji_counts: dict[int, int]
) -> InlineKeyboardMarkup:
    """Genera teclado de reacciones con conteos para un broadcast.

    Args:
        broadcast_id: ID del broadcast
        emojis: Lista de (emoji_id, emoji_char)
        emoji_counts: Diccionario {emoji_id: conteo}
    """
    from keyboards.callback_data import ReactionCallback

    buttons = []
    for emoji_id, emoji_char in emojis:
        count = emoji_counts.get(emoji_id, 0)
        # Mostrar el emoji con el conteo (o solo el emoji si no hay conteo)
        text = f"{emoji_char} {count}" if count > 0 else emoji_char
        buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=ReactionCallback(broadcast_id=broadcast_id, emoji_id=emoji_id).pack(),
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons])  # Una sola fila


# ==================== PROMOTIONS ====================


def promotion_admin_keyboard() -> InlineKeyboardMarkup:
    """Menú de administración de promociones"""
    buttons = [
        [
            InlineKeyboardButton(
                text="➕ Forjar nueva experiencia", callback_data="create_promotion"
            )
        ],
        [InlineKeyboardButton(text="📋 Ver el Gabinete", callback_data="list_promotions")],
        [
            InlineKeyboardButton(
                text="🔔 Expresiones pendientes", callback_data="promo_pending_interests"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚫 Visitantes restringidos", callback_data="promo_blocked_users"
            )
        ],
        [InlineKeyboardButton(text="📊 Observar el pulso", callback_data="promo_stats")],
        [InlineKeyboardButton(text="🔙 Volver al sanctum", callback_data="admin_gamification")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promotions_list_keyboard(promotions: list, show_active: bool = True) -> InlineKeyboardMarkup:
    """Lista de promociones con botones"""
    from keyboards.callback_data import PromoDetailCallback

    buttons = []
    for promo in promotions:
        status = "✅" if promo.is_active else "❌"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {promo.name[:30]}",
                    callback_data=PromoDetailCallback(promo_id=promo.id).pack(),
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promotion_detail_keyboard(promo_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Teclado de detalle de promoción"""
    from keyboards.callback_data import (
        PromoDeleteCallback,
        PromoInterestsCallback,
        TogglePromoCallback,
    )

    buttons = [
        [
            InlineKeyboardButton(
                text=f"{'Desactivar' if is_active else 'Activar'}",
                callback_data=TogglePromoCallback(promo_id=promo_id, enabled=not is_active).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Ver expresiones de interes",
                callback_data=PromoInterestsCallback(promo_id=promo_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Eliminar",
                callback_data=PromoDeleteCallback(promo_id=promo_id, confirmed=False).pack(),
            )
        ],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="list_promotions")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promotion_confirm_delete_keyboard(promo_id: int) -> InlineKeyboardMarkup:
    """Confirmación de eliminación de promoción"""
    from keyboards.callback_data import PromoDeleteCallback, PromoDetailCallback

    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Si, eliminar",
                callback_data=PromoDeleteCallback(promo_id=promo_id, confirmed=True).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Cancelar", callback_data=PromoDetailCallback(promo_id=promo_id).pack()
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promotion_source_keyboard() -> InlineKeyboardMarkup:
    """Selección de fuente de contenido"""
    buttons = [
        [
            InlineKeyboardButton(
                text="📦 Seleccionar coleccion existente", callback_data="promo_select_package"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Definir archivos manualmente", callback_data="promo_manual_files"
            )
        ],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def packages_for_promotion_keyboard(packages: list) -> InlineKeyboardMarkup:
    """Lista de paquetes para crear promoción"""
    from keyboards.callback_data import SelectPkgPromoCallback

    buttons = []
    for pkg in packages:
        if pkg.is_active:
            file_count = pkg.file_count
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{pkg.name} ({file_count} archivos)",
                        callback_data=SelectPkgPromoCallback(pkg_id=pkg.id).pack(),
                    )
                ]
            )
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promotion_dates_keyboard() -> InlineKeyboardMarkup:
    """Teclado para fechas de vigencia"""
    buttons = [
        [InlineKeyboardButton(text="📅 Sin fechas", callback_data="promo_no_dates")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promotion_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Confirmación de crear promoción"""
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Forjar experiencia", callback_data="confirm_create_promotion"
            )
        ],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def interest_detail_keyboard(
    interest_id: int, user_id: int, is_pending: bool = True
) -> InlineKeyboardMarkup:
    """Teclado de detalle de interés"""
    from keyboards.callback_data import BlockInterestCallback, MarkAttendedCallback

    buttons = []
    if is_pending:
        user_link = f"tg://user?id={user_id}"
        buttons.extend(
            [
                [InlineKeyboardButton(text="💬 Contactar al visitante", url=user_link)],
                [
                    InlineKeyboardButton(
                        text="✅ Marcar como atendido",
                        callback_data=MarkAttendedCallback(interest_id=interest_id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🚫 Restringir visitante",
                        callback_data=BlockInterestCallback(
                            user_id=user_id, confirmed=False
                        ).pack(),
                    )
                ],
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 Volver", callback_data="promo_pending_interests")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def blocked_users_keyboard(blocked_users: list) -> InlineKeyboardMarkup:
    """Lista de usuarios bloqueados"""
    from keyboards.callback_data import BlockedUserDetailCallback

    buttons = []
    for user in blocked_users:
        user_display = user.username or user.first_name or f"Visitante {user.user_id}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{user_display[:25]}",
                    callback_data=BlockedUserDetailCallback(user_id=user.user_id).pack(),
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def block_user_confirm_keyboard(user_id: int, interest_id: int = None) -> InlineKeyboardMarkup:
    """Confirmar bloqueo de usuario"""
    from keyboards.callback_data import InterestDetailCallback

    buttons = [
        [InlineKeyboardButton(text="✅ Si, restringir", callback_data="confirm_block_user")],
        [
            InlineKeyboardButton(
                text="❌ Cancelar",
                callback_data=InterestDetailCallback(interest_id=interest_id).pack()
                if interest_id
                else "promo_blocked_users",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_offers_keyboard(promotions: list, is_blocked: bool = False) -> InlineKeyboardMarkup:
    """Catálogo de ofertas para usuario"""
    from keyboards.callback_data import ViewOfferCallback

    buttons = []
    for promo in promotions:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"👁️ Examinar: {promo.name[:25]}",
                    callback_data=ViewOfferCallback(promo_id=promo.id).pack(),
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="offers")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def offer_detail_keyboard(
    promo_id: int, has_interest: bool, is_blocked: bool
) -> InlineKeyboardMarkup:
    """Detalle de oferta para usuario"""
    from keyboards.callback_data import OfferInterestCallback

    buttons = []
    if has_interest:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📜 Ver sus expresiones de interes", callback_data="my_offers_history"
                )
            ]
        )
    elif not is_blocked:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="💕 Me interesa",
                    callback_data=OfferInterestCallback(promo_id=promo_id).pack(),
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 Volver al Gabinete", callback_data="offers_catalog")]
    )
    buttons.append([InlineKeyboardButton(text="🏠 Menu principal", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
