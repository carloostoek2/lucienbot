"""
CallbackData definitions - Centralized for Lucien Bot.

Este archivo centraliza todas las definiciones de CallbackData para evitar
el parsing frágil de strings como: int(callback.data.replace("select_tariff_", ""))
"""
from aiogram.filters.callback_data import CallbackData


# ==================== GAMIFICATION ====================

class ReactionCallback(CallbackData, prefix="react"):
    """Reacciones a mensajes broadcast: react_{broadcast_id}_{emoji_id}"""
    broadcast_id: int
    emoji_id: int


class BalanceCallback(CallbackData, prefix="bal"):
    """Consulta de saldo de besitos"""
    action: str = "view"


class HistoryCallback(CallbackData, prefix="hist"):
    """Historial de transacciones"""
    action: str = "view"


class DailyGiftCallback(CallbackData, prefix="gift"):
    """Menú y reclamo de regalo diario"""
    action: str = "menu"  # "menu" | "claim"


# ==================== BACK NAVIGATION ====================

class BackCallback(CallbackData, prefix="back"):
    """Navegación de vuelta"""
    dest: str = "main"  # "main" | "admin" | "balance"


# ==================== VIP ====================

class SelectTariffCallback(CallbackData, prefix="select_tariff"):
    """Selección de tarifa VIP"""
    tariff_id: int


class CopyTokenCallback(CallbackData, prefix="copy_token"):
    """Copiar token de acceso"""
    token_id: int


# ==================== STORE ====================

class ProductDetailCallback(CallbackData, prefix="product_detail"):
    """Detalle de producto"""
    product_id: int


class DirectBuyCallback(CallbackData, prefix="direct_buy"):
    """Compra directa de producto"""
    product_id: int


class ConfirmDirectBuyCallback(CallbackData, prefix="confirm_direct_buy"):
    """Confirmar compra directa"""
    product_id: int


class StoreCategoryCallback(CallbackData, prefix="store_category"):
    """Categoría de tienda"""
    category_id: int


class ProductPreviewCallback(CallbackData, prefix="product_preview"):
    """Preview de producto"""
    product_id: int


# ==================== PROMOTIONS ====================

class SelectPkgPromoCallback(CallbackData, prefix="promo_select_pkg"):
    """Selección de paquete para promoción"""
    pkg_id: int


class PromoDetailCallback(CallbackData, prefix="promo_detail"):
    """Detalle de promoción"""
    promo_id: int


class TogglePromoCallback(CallbackData, prefix="toggle_promo"):
    """Activar/desactivar promoción"""
    promo_id: int
    enabled: bool = True


class PromoDeleteCallback(CallbackData, prefix="promo_del"):
    """Eliminar promoción"""
    promo_id: int
    confirmed: bool = False


class InterestDetailCallback(CallbackData, prefix="interest_detail"):
    """Detalle de expresión de interés"""
    interest_id: int


class MarkAttendedCallback(CallbackData, prefix="adm_attended"):
    """Marcar interés como atendido (admin)"""
    interest_id: int


class BlockInterestCallback(CallbackData, prefix="block_int"):
    """Bloquear usuario por interés"""
    user_id: int
    confirmed: bool = False


class PromoInterestsCallback(CallbackData, prefix="promo_interests"):
    """Ver intereses de promoción"""
    promo_id: int


class BlockedUserDetailCallback(CallbackData, prefix="blocked_user_detail"):
    """Detalle de usuario bloqueado"""
    user_id: int


class UnblockUserCallback(CallbackData, prefix="unblock_user"):
    """Desbloquear usuario"""
    user_id: int


class ViewOfferCallback(CallbackData, prefix="view_offer"):
    """Ver detalle de oferta usuario"""
    promo_id: int


class OfferInterestCallback(CallbackData, prefix="offer_interest"):
    """Expresar interés en oferta"""
    promo_id: int