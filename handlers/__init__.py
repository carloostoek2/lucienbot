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
# Fase 4 - Tienda
from .store_user_handlers import router as store_user_router
from .store_admin_handlers import router as store_admin_router

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
    # Fase 4 - Tienda
    'store_user_router',
    'store_admin_router'
]
