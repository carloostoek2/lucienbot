# Fase 15 - Mochila
from .backpack_service import BackpackService

# Fase 1 - Gamificacion
from .besito_service import BesitoService
from .broadcast_service import BroadcastService
from .channel_service import ChannelService
from .daily_gift_service import DailyGiftService

# Internal EventBus (PoC Item 1)
from .event_bus import EVENT_BESITOS_AWARDED, EVENT_VIP_ACTIVATED, InternalEventBus, get_event_bus
from .game_service import GameService

# Item 11 - Observability / Health (read-only best-effort; follows Analytics pattern)
from .health_service import HealthService

# Fase 3 - Misiones y Recompensas
from .mission_service import MissionService

# Nurture / User Content Lifecycle (post-VIP configurable sequences)
from .nurture_service import NurtureService

# Fase 2 - Paquetes
from .package_service import PackageService
from .reward_service import RewardService
from .scheduler_service import SchedulerService

# Fase 4 - Tienda
from .store_service import StoreService

# Phase 17 - Promociones por Racha
from .streak_promotion_service import StreakPromotionService

# Configuracion de Trivias
from .trivia_config_service import TriviaConfigService

# Fase 16 - Trivias Especiales
from .trivia_service import TriviaCategoryService
from .user_service import UserService
from .vip_service import VIPService

__all__ = [
    "ChannelService",
    "VIPService",
    "UserService",
    "SchedulerService",
    # Item 11 - Observability / Health (enables with get_service(HealthService) as h:)
    "HealthService",
    # Fase 1 - Gamificacion
    "BesitoService",
    "BroadcastService",
    "DailyGiftService",
    "GameService",
    # Fase 2 - Paquetes
    "PackageService",
    # Fase 3 - Misiones y Recompensas
    "MissionService",
    "RewardService",
    # Fase 4 - Tienda
    "StoreService",
    # Fase 15 - Mochila
    "BackpackService",
    # Fase 16 - Trivias Especiales
    "TriviaCategoryService",
    # Phase 17 - Promociones por Racha
    "StreakPromotionService",
    # Nurture / User Content Lifecycle
    "NurtureService",
    # Configuracion de Trivias
    "TriviaConfigService",
    "get_service",
    # Internal EventBus (PoC Item 1 - besitos_awarded first use case)
    "InternalEventBus",
    "get_event_bus",
    "EVENT_BESITOS_AWARDED",
    "EVENT_VIP_ACTIVATED",
]


def get_service(service_class, db=None):
    """
    Crea un service con context manager para manejo automático de sesiones.

    Uso:
        from services import get_service, VIPService

        with get_service(VIPService) as vip_service:
            vip_service.get_vip_channel()

    O para pasar sesión existente:
        with get_service(VIPService, db=session) as vip_service:
            ...
    """
    return _ServiceContext(service_class, db)


class _ServiceContext:
    """Context manager para services con manejo automático de sesiones."""

    def __init__(self, service_class, db=None):
        self._service_class = service_class
        self._db = db
        self._service = None

    def __enter__(self):
        self._service = self._service_class(self._db)
        return self._service

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._service and hasattr(self._service, "close"):
            self._service.close()
        return False
