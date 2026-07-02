"""
CallbackData definitions - Centralized for Lucien Bot.

Este archivo centraliza todas las definiciones de CallbackData para evitar
el parsing frágil de strings como: int(callback.data.replace("select_tariff_", ""))
"""

from aiogram.filters.callback_data import CallbackData

# ==================== GAMIFICATION ====================


class ReactionCallback(CallbackData, prefix="react"):
    """Reacciones a mensajes broadcast: react:broadcast_id:emoji_id"""

    broadcast_id: int
    emoji_id: int


class EditEmojiCallback(CallbackData, prefix="edit_emoji"):
    """Editar emoji existente"""

    emoji_id: int


class ToggleEmojiCallback(CallbackData, prefix="toggle_emoji"):
    """Activar/desactivar emoji"""

    emoji_id: int


class ChangeEmojiValueCallback(CallbackData, prefix="change_emoji_value"):
    """Cambiar valor de emoji"""

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


class ToggleGiftCallback(CallbackData, prefix="toggle_gift"):
    """Marcar/desmarcar token como regalo"""

    token_id: int
    is_gift: bool = False


class VipPromoDetailCallback(CallbackData, prefix="vip_promo_detail"):
    """Detalle de promoción VIP exclusiva"""

    promo_id: int


class VipPromoInterestCallback(CallbackData, prefix="vip_promo_interest"):
    """Expresar interés en promoción VIP"""

    promo_id: int


class ForwardActionCallback(CallbackData, prefix="fwd_action"):
    """Acción tras reenvío admin: activar VIP u otorgar besitos."""

    action: str  # "vip" | "besitos"


class ForwardConfirmCallback(CallbackData, prefix="fwd_confirm"):
    """Confirmar grant tras reenvío admin."""

    action: str  # "vip" | "besitos"


class ForwardCancelCallback(CallbackData, prefix="fwd_cancel"):
    """Cancelar flujo forward admin."""

    action: str = "cancel"


class SubscriberListCallback(CallbackData, prefix="sub_list"):
    """Lista paginada de suscriptores activos."""

    channel_id: int = 0  # 0 = menú VIP global (sin filtro canal)
    page: int = 0


class SubscriberProfileCallback(CallbackData, prefix="sub_prof"):
    """Perfil admin de un suscriptor."""

    subscription_id: int
    channel_id: int = 0
    page: int = 0


class SubscriberActionCallback(CallbackData, prefix="sub_act"):
    """Iniciar acción admin sobre suscriptor."""

    action: str  # "extend" | "grant_besitos" | "debit_besitos" | "kick"
    subscription_id: int
    channel_id: int = 0
    page: int = 0


class SubscriberExtendTariffCallback(CallbackData, prefix="sub_ext_tar"):
    """Seleccionar tarifa para extender VIP."""

    subscription_id: int
    tariff_id: int
    channel_id: int = 0
    page: int = 0


class SubscriberConfirmCallback(CallbackData, prefix="sub_confirm"):
    """Confirmar acción (extend | grant_besitos | debit_besitos | kick)."""

    action: str
    subscription_id: int
    channel_id: int = 0
    page: int = 0


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


class RestockProductCallback(CallbackData, prefix="restock_prod"):
    """Reabastecer producto"""

    product_id: int


class SelectPkgProductCallback(CallbackData, prefix="sel_pkg_prod"):
    """Seleccionar paquete para producto"""

    product_id: int


class ProductAdminDetailCallback(CallbackData, prefix="prod_admin_detail"):
    """Detalle de producto (admin)"""

    product_id: int
    tier_id: int = 0


class AdminStoreTierCallback(CallbackData, prefix="admin_store_tier"):
    """Navegación admin de productos por tier (0 = sin nivel)."""

    tier_id: int


class ConfigStockAlertCallback(CallbackData, prefix="config_stock_alert"):
    """Configurar alerta de stock"""

    product_id: int


class ToggleProductCallback(CallbackData, prefix="toggle_prod"):
    """Activar/desactivar producto"""

    product_id: int


class DeleteProductCallback(CallbackData, prefix="del_prod"):
    """Eliminar producto"""

    product_id: int
    confirmed: bool = False


class EditProductCallback(CallbackData, prefix="edit_prod"):
    """Abrir menú de edición de producto"""

    product_id: int


class EditProductFieldCallback(CallbackData, prefix="edit_prod_field"):
    """Editar un campo específico del producto"""

    product_id: int
    field: str  # name | description | package | price | stock | tariff | story_node


class SelectPkgEditProductCallback(CallbackData, prefix="sel_pkg_edit"):
    """Seleccionar paquete al editar producto"""

    product_id: int
    package_id: int


class SelectTariffStoreWizardCallback(CallbackData, prefix="wiz_store_tariff"):
    """Seleccionar tarifa VIP en wizard crear producto tienda."""

    tariff_id: int


class SelectStoryNodeStoreWizardCallback(CallbackData, prefix="wiz_store_story"):
    """Seleccionar nodo narrativo en wizard crear producto tienda."""

    story_node_id: int


class SelectTariffEditProductCallback(CallbackData, prefix="sel_tariff_edit"):
    """Seleccionar tarifa al editar producto VIP_GRANT."""

    product_id: int
    tariff_id: int


class SelectTierEditProductCallback(CallbackData, prefix="sel_tier_edit"):
    """Seleccionar tier/nivel al editar producto."""

    product_id: int
    tier_id: int


class SelectStoryNodeEditProductCallback(CallbackData, prefix="sel_story_edit"):
    """Seleccionar nodo al editar producto STORY_UNLOCK."""

    product_id: int
    story_node_id: int


class CreatePkgForProductCallback(CallbackData, prefix="create_pkg_prod"):
    """Crear nuevo paquete desde selección de paquete en flujo de producto"""

    source: str  # "wizard" (creación) o "edit" (edición)
    product_id: int = 0  # solo usado en source="edit"


class CancelPackageWizardCallback(CallbackData, prefix="cancel_pkg_wiz"):
    """Cancelar wizard de paquete (namespaced para no colisionar con cancel global)"""


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


class ConfigMessagesCallback(CallbackData, prefix="config_msgs"):
    """Menú configuración de mensajes del canal"""

    channel_id: int  # DB PK


class ConfigMessageTypeCallback(CallbackData, prefix="config_msg_type"):
    """Selección de tipo de mensaje a editar"""

    channel_id: int
    msg_type: str  # "approval" | "welcome"


class ViewMessagesCallback(CallbackData, prefix="view_msgs"):
    """Ver mensajes actuales del canal"""

    channel_id: int


class RestoreMessagesCallback(CallbackData, prefix="restore_msgs"):
    """Restaurar mensajes a default Lucien"""

    channel_id: int
    msg_type: str  # "approval" | "welcome" | "all"


class ApproveOneCallback(CallbackData, prefix="approve_one"):
    """Aprobar solicitud individual"""

    request_id: int
    channel_id: int  # DB PK (navegación)
    page: int = 0


class RejectOneCallback(CallbackData, prefix="reject_one"):
    """Rechazar solicitud individual (muestra confirmación)"""

    request_id: int
    channel_id: int
    page: int = 0


class ConfirmRejectCallback(CallbackData, prefix="confirm_reject"):
    """Confirmar rechazo de solicitud"""

    request_id: int
    channel_id: int
    page: int = 0


class PendingPageCallback(CallbackData, prefix="pending_page"):
    """Paginación de solicitudes pendientes"""

    channel_id: int
    page: int


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


# ==================== STORY ADMIN ====================


class StoryNodeTypeCallback(CallbackData, prefix="story_node_type"):
    """Selección de tipo de nodo"""

    node_type: str  # NodeType enum value


class StoryArchetypeReqCallback(CallbackData, prefix="story_archetype_req"):
    """Selección de requisito de arquetipo"""

    archetype: str  # ArchetypeType enum value or "none"


class StoryChoicePointsCallback(CallbackData, prefix="story_choice_pts"):
    """Selección de puntos de arquetipo para opción"""

    archetype: str  # ArchetypeType enum value or "none"


class StoryNewArchetypeCallback(CallbackData, prefix="story_new_archetype"):
    """Crear nuevo arquetipo"""

    archetype: str  # ArchetypeType enum value


class StoryArchetypeEditCallback(CallbackData, prefix="story_arch_edit"):
    """Editar arquetipo existente"""

    archetype: str  # ArchetypeType enum value


class StoryChoiceCallback(CallbackData, prefix="story_choice"):
    """Seleccionar opción de historia"""

    choice_id: int


class ContinueStoryCallback(CallbackData, prefix="story_continue"):
    """Continuar a nodo específico"""

    node_id: int


class QuizAnswerCallback(CallbackData, prefix="quiz_answer"):
    """Respuesta a pregunta de cuestionario"""

    answer_idx: int


class ArchetypeSelectCallback(CallbackData, prefix="archetype_select"):
    """Seleccionar arquetipo"""

    archetype: str


class StoryNodeListPageCallback(CallbackData, prefix="story_node_list"):
    """Paginación de listado de nodos admin"""

    page: int = 0


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


class StoryAchievementNodeCallback(CallbackData, prefix="story_ach_node"):
    """Nodo requerido para logro (0 = ninguno)"""

    node_id: int


class StoryChoiceNextCallback(CallbackData, prefix="story_choice_next"):
    """Seleccionar siguiente nodo para opción"""

    node_id: int


class ArchetypeDetailCallback(CallbackData, prefix="archetype_detail"):
    """Detalle de arquetipo"""

    archetype: str


# ==================== REWARD ====================


class RewardTypeCallback(CallbackData, prefix="reward_type"):
    """Selección de tipo de recompensa"""

    reward_type: str  # RewardType enum value: "besitos", "package", "vip_access"


class RewardSelectPkgCallback(CallbackData, prefix="reward_sel_pkg"):
    """Seleccionar paquete para recompensa"""

    pkg_id: int


class RewardAdminDetailCallback(CallbackData, prefix="reward_admin_detail"):
    """Detalle de recompensa (admin)"""

    reward_id: int


class RewardToggleCallback(CallbackData, prefix="reward_toggle"):
    """Activar/desactivar recompensa"""

    reward_id: int


class RewardDeleteCallback(CallbackData, prefix="reward_del"):
    """Eliminar recompensa"""

    reward_id: int
    confirmed: bool = False


# ==================== NURTURE / LIFECYCLE (admin config for sequences + steps) ====================


class NurtureSequenceListCallback(CallbackData, prefix="nurture_list"):
    """Lista de secuencias nurture (active/all)"""

    list_type: str = "active"


class NurtureSequenceDetailCallback(CallbackData, prefix="nurture_detail"):
    """Detalle de secuencia nurture"""

    sequence_id: int


class NurtureToggleSequenceCallback(CallbackData, prefix="nurture_toggle_seq"):
    """Activar/desactivar secuencia"""

    sequence_id: int


class NurtureStepSelectPackageCallback(CallbackData, prefix="nurture_sel_pkg"):
    """Seleccionar paquete para un step de nurture (wired in wizard pick flow)"""

    sequence_id: int
    temp_step_order: int  # orden temporal durante wizard
    package_id: int = 0  # 0 means no-pkg / fallback choice; >0 means selected pkg id


class NurtureStepDetailCallback(CallbackData, prefix="nurture_step_detail"):
    """Detalle / editar step"""

    step_id: int


class NurtureToggleStepCallback(CallbackData, prefix="nurture_toggle_step"):
    """Activar/desactivar step"""

    step_id: int


class NurtureTestSendCallback(CallbackData, prefix="nurture_test_send"):
    """Enviar entrega de test (usa admin tg + pkg)"""

    package_id: int


# ==================== CATEGORY ====================


class CategoryAdminDetailCallback(CallbackData, prefix="cat_adm_detail"):
    """Detalle de categoría (admin)"""

    category_id: int


class CategoryAdminToggleCallback(CallbackData, prefix="cat_adm_toggle"):
    """Activar/desactivar categoría"""

    category_id: int


class CategoryAdminDeleteCallback(CallbackData, prefix="cat_adm_delete"):
    """Eliminar categoría"""

    category_id: int


class CategoryAdminConfirmDeleteCallback(CallbackData, prefix="cat_adm_confirm_del"):
    """Confirmar eliminación de categoría"""

    category_id: int


class CategoryAssignCallback(CallbackData, prefix="cat_assign"):
    """Seleccionar categoría para asignar paquete"""

    category_id: int


class PackageAssignCallback(CallbackData, prefix="pkg_assign"):
    """Seleccionar paquete para asignar"""

    package_id: int


# ==================== BROADCAST ====================


class BroadcastChannelCallback(CallbackData, prefix="bc_channel"):
    """Selección de canal para broadcast"""

    channel_id: int


class ToggleReactionCallback(CallbackData, prefix="bc_reaction"):
    """Toggle selección de emoji en broadcast"""

    emoji_id: int


class BroadcastProtectCallback(CallbackData, prefix="bc_protect"):
    """Protección del mensaje broadcast"""

    action: str  # "yes" | "no"


class ToggleExtraButtonCallback(CallbackData, prefix="bc_extra"):
    """Toggle selección de botón extra (single choice: 0 = ninguno)"""

    button_id: int  # 0 means "ninguno"


# ==================== BROADCAST BUTTONS ADMIN (gestión del catálogo "definir primero") ====================


class EditButtonCallback(CallbackData, prefix="edit_btn"):
    """Editar un botón de enlace existente (admin wizard)"""

    button_id: int


class ToggleButtonCallback(CallbackData, prefix="toggle_btn"):
    """Activar o desactivar un botón de enlace (admin)"""

    button_id: int


class DeleteButtonCallback(CallbackData, prefix="del_btn"):
    """Eliminar botón de enlace (requiere confirmación)"""

    button_id: int
    confirmed: bool = False


class ChangeButtonLabelCallback(CallbackData, prefix="ch_btn_label"):
    """Iniciar cambio de label de un botón (admin wizard)"""
    button_id: int


class ChangeButtonUrlCallback(CallbackData, prefix="ch_btn_url"):
    """Iniciar cambio de url de un botón (admin wizard)"""
    button_id: int


class ChangeButtonDescCallback(CallbackData, prefix="ch_btn_desc"):
    """Iniciar cambio de descripción de un botón (admin wizard)"""
    button_id: int


# ==================== ANONYMOUS MESSAGE ====================


class AnonUnreadCallback(CallbackData, prefix="anon_unread"):
    """Mensajes no leídos"""

    pass


class AnonAllCallback(CallbackData, prefix="anon_all"):
    """Todos los mensajes"""

    pass


class AnonViewCallback(CallbackData, prefix="anon_view"):
    """Ver mensaje anónimo"""

    message_id: int


class AnonReplyCallback(CallbackData, prefix="anon_reply"):
    """Responder a mensaje anónimo"""

    message_id: int


class AnonRevealCallback(CallbackData, prefix="anon_reveal"):
    """Revelar remitente de mensaje anónimo"""

    message_id: int


class AnonDeleteCallback(CallbackData, prefix="anon_delete"):
    """Eliminar mensaje anónimo"""

    message_id: int


# ==================== MISSION ADMIN ====================


class MissionTypeSelectCallback(CallbackData, prefix="mission_type_sel"):
    """Selección de tipo de misión"""

    mission_type: str  # MissionType enum value


class MissionFreqSelectCallback(CallbackData, prefix="mission_freq_sel"):
    """Selección de frecuencia de misión"""

    frequency: str  # MissionFrequency enum value


class MissionDetailCallback(CallbackData, prefix="mission_detail"):
    """Detalle de misión (admin)"""

    mission_id: int


class MissionToggleCallback(CallbackData, prefix="toggle_mission"):
    """Activar/desactivar misión"""

    mission_id: int


class MissionDeleteCallback(CallbackData, prefix="delete_mission"):
    """Eliminar misión"""

    mission_id: int
    confirmed: bool = False


class MissionStatsCallback(CallbackData, prefix="mission_stats"):
    """Estadísticas de misión"""

    mission_id: int


class SelectRewardMissionCallback(CallbackData, prefix="select_reward_mission"):
    """Seleccionar recompensa para misión"""

    reward_id: int


class ConfirmCreateMissionCallback(CallbackData, prefix="confirm_create_mission"):
    """Confirmar creación de misión"""

    pass


# ==================== TRIVIA CONFIG ====================


class TriviaConfigFieldCallback(CallbackData, prefix="trivia_cfg_field"):
    """Selección de campo de configuración de trivia"""

    field_key: str  # "dice" | "trivia" | "trivia_vip" | "trivia_simple"


class TriviaCategoryActivateCallback(CallbackData, prefix="trivia_cat_activate"):
    """Activar categoría de trivia"""

    category_id: str


# ==================== MISSION USER ====================


class MissionUserDetailCallback(CallbackData, prefix="mission_user_detail"):
    """Detalle de misión (usuario)"""

    mission_id: int


# ==================== REWARD USER ====================


class RewardUserDetailCallback(CallbackData, prefix="reward_user_detail"):
    """Detalle de recompensa (usuario)"""

    mission_id: int


class TriviaStreakDetailCallback(CallbackData, prefix="streak_detail"):
    """Detalle de promoción por racha"""

    promo_id: int


class TriviaStreakToggleCallback(CallbackData, prefix="streak_toggle"):
    """Activar/desactivar promoción por racha"""

    promo_id: int


class TriviaStreakDeleteCallback(CallbackData, prefix="streak_delete"):
    """Eliminar promoción por racha"""

    promo_id: int


class TriviaStreakConfirmDeleteCallback(CallbackData, prefix="streak_confirm_del"):
    """Confirmar eliminación de promoción por racha"""

    promo_id: int


class TriviaStreakRedemptionsCallback(CallbackData, prefix="streak_redemptions"):
    """Ver canjes de promoción por racha"""

    promo_id: int


class TriviaStreakCategoryCallback(CallbackData, prefix="streak_promo_cat"):
    """Selección de categoría para promoción por racha"""

    category: str  # "none" o ID numérico


class TriviaStreakGoalTypeCallback(CallbackData, prefix="streak_promo_gt"):
    """Selección de tipo de juego para promoción por racha"""

    goal_type: str  # "general" | "simple" | "vip" | "done"


# ==================== GAME ====================


class TriviaAnswerCallback(CallbackData, prefix="trivia_answer"):
    """Respuesta de trivia"""

    answer_idx: int
    question_idx: int


class TriviaVipAnswerCallback(CallbackData, prefix="trivia_vip_answer"):
    """Respuesta de trivia VIP"""

    answer_idx: int
    question_idx: int


class TriviaSimpleAnswerCallback(CallbackData, prefix="trivia_simple_answer"):
    """Respuesta de trivia especial"""

    answer_idx: int
    question_idx: int


class StreakProtectAcceptCallback(CallbackData, prefix="streak_protect_accept"):
    """Aceptar proteccion de racha pagando besitos."""

    streak: int
    game_type: str


class StreakProtectDeclineCallback(CallbackData, prefix="streak_protect_decline"):
    """Rechazar proteccion de racha (pierde streak y codigos)."""

    streak: int
    game_type: str


class StreakRetireCallback(CallbackData, prefix="streak_retire"):
    """Retirarse del modo arriesgo conservando codigos actuales."""

    pass


class StreakContinueCallback(CallbackData, prefix="streak_continue"):
    """Continuar en modo arriesgo por el siguiente nivel."""

    pass


# ==================== BACKPACK ====================


class BackpackRewardsPageCallback(CallbackData, prefix="backpack_rewards_page"):
    """Paginación de recompensas"""

    page: int


class BackpackPurchasesPageCallback(CallbackData, prefix="backpack_purchases_page"):
    """Paginación de compras"""

    page: int


class BackpackRewardDetailCallback(CallbackData, prefix="backpack_reward"):
    """Detalle de recompensa"""

    history_id: int


class BackpackPurchaseDetailCallback(CallbackData, prefix="backpack_purchase"):
    """Detalle de compra"""

    order_id: int
    product_id: int


class BackpackDeliverCallback(CallbackData, prefix="backpack_deliver"):
    """Entregar contenido de paquete"""

    package_id: int


class BackpackFulfillmentRetryCallback(CallbackData, prefix="bp_fulfill_retry"):
    """Reintentar entrega de fulfillment PACKAGE."""

    fulfillment_id: int


class BackpackActivateVipCallback(CallbackData, prefix="bp_activate_vip"):
    """Activar VIP desde token de fulfillment."""

    fulfillment_id: int


class BackpackReadChapterCallback(CallbackData, prefix="bp_read_chapter"):
    """Leer capítulo desbloqueado por fulfillment STORY_UNLOCK."""

    fulfillment_id: int


class BackpackViewWaitlistCallback(CallbackData, prefix="bp_view_waitlist"):
    """Ver posición en lista de espera."""

    fulfillment_id: int


class BackpackSubmitInputCallback(CallbackData, prefix="bp_submit_input"):
    """Inicia FSM para enviar input pendiente desde mochila."""

    fulfillment_id: int


class StoreTierCallback(CallbackData, prefix="store_tier"):
    """Navegación catálogo por tier."""

    tier_id: int


class FulfillmentAdminQueueCallback(CallbackData, prefix="fulfill_admin_q"):
    """Filtro cola admin fulfillment."""

    status: str = "all"


class FulfillmentAdminItemCallback(CallbackData, prefix="fulfill_admin_item"):
    """Detalle item cola admin."""

    fulfillment_id: int
    filter_status: str = "pending"


class FulfillmentAdminMarkCallback(CallbackData, prefix="fulfill_admin_mark"):
    """Marcar fulfillment cumplido."""

    fulfillment_id: int


class FulfillmentAdminDeliverCallback(CallbackData, prefix="fulfill_admin_deliver"):
    """Entregar paquete desde cola admin."""

    fulfillment_id: int
    package_id: int
