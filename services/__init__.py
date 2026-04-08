from .channel_service import ChannelService
from .vip_service import VIPService
from .user_service import UserService
from .scheduler_service import SchedulerService
# Fase 1 - Gamificacion
from .besito_service import BesitoService
from .broadcast_service import BroadcastService
from .daily_gift_service import DailyGiftService
from .game_service import GameService
# Fase 2 - Paquetes
from .package_service import PackageService
# Fase 3 - Misiones y Recompensas
from .mission_service import MissionService
from .reward_service import RewardService
# Fase 4 - Tienda
from .store_service import StoreService

__all__ = [
    'ChannelService', 'VIPService', 'UserService', 'SchedulerService',
    # Fase 1 - Gamificacion
    'BesitoService', 'BroadcastService', 'DailyGiftService', 'GameService',
    # Fase 2 - Paquetes
    'PackageService',
    # Fase 3 - Misiones y Recompensas
    'MissionService', 'RewardService',
    # Fase 4 - Tienda
    'StoreService',
    'get_service'
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
        if self._service and hasattr(self._service, 'close'):
            self._service.close()
        return False
