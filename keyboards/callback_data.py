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


# ==================== CHANNEL ====================

class ChannelTypeCallback(CallbackData, prefix="channel_type"):
    """Selección de tipo de canal"""
    action: str


class ChannelDetailCallback(CallbackData, prefix="channel_detail"):
    """Detalle de canal"""
    channel_id: int


class ConfigWaitCallback(CallbackData, prefix="config_wait"):
    """Configurar tiempo de espera"""
    channel_id: int


class WaitTimeCallback(CallbackData, prefix="wait"):
    """Selección de tiempo de espera"""
    minutes: str


class ConfigInviteCallback(CallbackData, prefix="config_invite"):
    """Configurar enlace de invitación"""
    channel_id: int


class PendingReqCallback(CallbackData, prefix="pending_req"):
    """Ver solicitudes pendientes"""
    channel_id: int


class ApproveAllCallback(CallbackData, prefix="approve_all"):
    """Aprobar todas las solicitudes"""
    channel_id: int


class DeleteChannelCallback(CallbackData, prefix="delete_channel"):
    """Confirmar eliminación de canal"""
    channel_id: int


class ConfirmDeleteChannelCallback(CallbackData, prefix="confirm_delete_channel"):
    """Eliminar canal confirmado"""
    channel_id: int


# ==================== PACKAGE ====================

class PackageListCallback(CallbackData, prefix="pkg_list"):
    """Navigación de lista de paquetes"""
    list_type: str = "active"  # "active" | "all"


class PackageDetailCallback(CallbackData, prefix="pkg_detail"):
    """Detalle de paquete"""
    package_id: int


class TogglePackageCallback(CallbackData, prefix="toggle_pkg"):
    """Activar/desactivar paquete"""
    package_id: int


class DeletePackageCallback(CallbackData, prefix="del_pkg"):
    """Eliminar paquete"""
    package_id: int
    confirmed: bool = False


class ViewPackageFilesCallback(CallbackData, prefix="view_pkg_files"):
    """Ver archivos de paquete"""
    package_id: int


class DeletePackageFilesCallback(CallbackData, prefix="del_pkg_files"):
    """Iniciar eliminación de archivos de paquete"""
    package_id: int


class SendPackageSelectCallback(CallbackData, prefix="send_pkg"):
    """Selección de paquete para enviar"""
    package_id: int


class UpdatePackageSelectCallback(CallbackData, prefix="upd_pkg"):
    """Selección de paquete para actualizar"""
    package_id: int


class DeleteFilePkgCallback(CallbackData, prefix="delfile_pkg"):
    """Selección de paquete para eliminar archivos"""
    package_id: int


class ConfirmDeleteFileCallback(CallbackData, prefix="confirm_delfile"):
    """Confirmar eliminación de archivo"""
    file_id: int


class ExecuteDeleteFileCallback(CallbackData, prefix="exec_delfile"):
    """Ejecutar eliminación de archivo"""
    file_id: int


class ContinueDeleteFilesCallback(CallbackData, prefix="cont_delfile"):
    """Continuar eliminación de archivos"""
    package_id: int


class FinishDeleteFilesCallback(CallbackData, prefix="finish_delfile"):
    """Finalizar eliminación de archivos"""
    package_id: int


# ==================== STORY ====================

class StoryNodeDetailCallback(CallbackData, prefix="story_node_detail"):
    """Detalle de nodo de historia"""
    node_id: int


class StoryNodeToggleCallback(CallbackData, prefix="story_node_toggle"):
    """Activar/desactivar nodo"""
    node_id: int


class StoryNodeDeleteCallback(CallbackData, prefix="story_node_delete"):
    """Eliminar nodo"""
    node_id: int
    confirmed: bool = False


class StoryAddChoicesCallback(CallbackData, prefix="story_add_choices"):
    """Agregar opciones a nodo"""
    node_id: int


class StoryChoiceNextCallback(CallbackData, prefix="story_choice_next"):
    """Seleccionar siguiente nodo para opción"""
    node_id: int


class ArchetypeDetailCallback(CallbackData, prefix="archetype_detail"):
    """Detalle de arquetipo"""
    archetype: str