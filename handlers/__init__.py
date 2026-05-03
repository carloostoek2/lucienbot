from .common_handlers import router as common_router
from .admin_handlers import router as admin_router
from .channel_handlers import router as channel_router
from .vip_handlers import router as vip_router
from .free_channel_handlers import router as free_channel_router
# Fase 1 - Gamificacion
from .gamification_user_handlers import router as gamification_user_router
from .gamification_admin_handlers import router as gamification_admin_router
from .broadcast_handlers import router as broadcast_router
# Fase 2 - Paquetes
from .package_handlers import router as package_router
# Fase 3 - Misiones y Recompensas
from .mission_user_handlers import router as mission_user_router
from .mission_admin_handlers import router as mission_admin_router
from .reward_admin_handlers import router as reward_admin_router
from .reward_user_handlers import router as reward_user_router
# Fase 4 - Tienda
from .store_user_handlers import router as store_user_router
from .store_admin_handlers import router as store_admin_router
# Fase 5 - Promociones
from .promotion_user_handlers import router as promotion_user_router
from .promotion_admin_handlers import router as promotion_admin_router
# Fase 6 - Narrativa
from .story_user_handlers import router as story_user_router
from .story_admin_handlers import router as story_admin_router
# Phase 9 - Analytics
from .analytics_handlers import router as analytics_router
# Phase 12 - Mensajes Anónimos VIP
from .vip_user_handlers import router as vip_user_router
from .anonymous_message_admin_handlers import router as anonymous_message_admin_router
# Phase 14 - Minijuegos
from .game_user_handlers import router as game_user_router
# Phase 16 - Trivia Discount
from .trivia_discount_admin_handlers import router as trivia_discount_admin_router
# Phase 17 - Question Sets
from .question_set_admin_handlers import router as question_set_admin_router
# Phase 15 - Mochila
from .backpack_handler import router as backpack_router

__all__ = [
    'common_router',
    'admin_router',
    'channel_router',
    'vip_router',
    'free_channel_router',
    # Fase 1 - Gamificacion
    'gamification_user_router',
    'gamification_admin_router',
    'broadcast_router',
    # Fase 2 - Paquetes
    'package_router',
    # Fase 3 - Misiones y Recompensas
    'mission_user_router',
    'mission_admin_router',
    'reward_admin_router',
    'reward_user_router',
    # Fase 4 - Tienda
    'store_user_router',
    'store_admin_router',
    # Fase 5 - Promociones
    'promotion_user_router',
    'promotion_admin_router',
    # Fase 6 - Narrativa
    'story_user_router',
    'story_admin_router',
    # Phase 9 - Analytics
    'analytics_router',
    # Phase 12 - Mensajes Anónimos VIP
    'vip_user_router',
    'anonymous_message_admin_router',
    # Phase 14 - Minijuegos
    'game_user_router',
    # Phase 16 - Trivia Discount
    'trivia_discount_admin_router',
    # Phase 17 - Question Sets
    'question_set_admin_router',
    # Phase 15 - Mochila
    'backpack_router'
]
