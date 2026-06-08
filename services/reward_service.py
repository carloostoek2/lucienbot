"""
Servicio de Recompensas - Lucien Bot

Gestiona la creacion y entrega de recompensas.
"""

import logging

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import Reward, RewardType, TransactionSource, UserRewardHistory
from services.besito_service import BesitoService
from services.package_service import PackageService
from services.vip_service import VIPService
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)


def get_reward_emoji(reward: Reward) -> tuple[str, str]:
    """Retorna (emoji, description) según tipo de recompensa. Función pura (sin estado ni side-effects)."""
    if reward.reward_type == RewardType.BESITOS:
        return "💋", f"{reward.besito_amount} besitos"
    elif reward.reward_type == RewardType.PACKAGE:
        return "📦", f"Paquete exclusivo: {reward.name}"
    elif reward.reward_type == RewardType.VIP_ACCESS:
        return "👑", f"Acceso VIP: {reward.name}"
    return "🎁", ""


class RewardService:
    """Servicio para gestion de recompensas"""

    def __init__(self, db: Session = None):
        self._owns_session = db is None
        self.db = db or SessionLocal()
        # Held direct BesitoService composition removed (Item 5 / reduce via EventBus pattern).
        # BESITOS reward delivery now uses local on-demand BesitoService(db=self.db) *only*
        # inside _deliver_besitos (preserves atomicity: credit's internal commit + MISSION tx source
        # + log_reward_delivery + return msg all unchanged; best-effort schedule_emit still fires).
        # Package + VIP remain held (scope: other composers untouched for now).
        self.package_service = PackageService(self.db)
        self.vip_service = VIPService(self.db)

    # ==================== CREACION DE RECOMPENSAS ====================

    def create_reward_besitos(
        self, name: str, description: str, besito_amount: int, created_by: int = None
    ) -> Reward:
        """Crea una recompensa de tipo besitos"""
        reward = Reward(
            name=name,
            description=description,
            reward_type=RewardType.BESITOS,
            besito_amount=besito_amount,
            created_by=created_by,
            is_active=True,
        )
        self.db.add(reward)
        self.db.commit()
        self.db.refresh(reward)
        logger.info(f"Recompensa de besitos creada: {name} ({besito_amount} besitos)")
        return reward

    def create_reward_package(
        self, name: str, description: str, package_id: int, created_by: int = None
    ) -> Reward:
        """Crea una recompensa de tipo paquete"""
        reward = Reward(
            name=name,
            description=description,
            reward_type=RewardType.PACKAGE,
            package_id=package_id,
            created_by=created_by,
            is_active=True,
        )
        self.db.add(reward)
        self.db.commit()
        self.db.refresh(reward)
        logger.info(f"Recompensa de paquete creada: {name} (package_id={package_id})")
        return reward

    def create_reward_vip(
        self, name: str, description: str, tariff_id: int, created_by: int = None
    ) -> Reward:
        """Crea una recompensa de tipo acceso VIP"""
        reward = Reward(
            name=name,
            description=description,
            reward_type=RewardType.VIP_ACCESS,
            tariff_id=tariff_id,
            created_by=created_by,
            is_active=True,
        )
        self.db.add(reward)
        self.db.commit()
        self.db.refresh(reward)
        logger.info(f"Recompensa VIP creada: {name} (tariff_id={tariff_id})")
        return reward

    # ==================== CONSULTAS ====================

    def get_reward(self, reward_id: int) -> Reward | None:
        """Obtiene una recompensa por ID"""
        return self.db.query(Reward).filter(Reward.id == reward_id).first()

    def get_all_rewards(self, active_only: bool = True) -> list[Reward]:
        """Obtiene todas las recompensas"""
        query = self.db.query(Reward)
        if active_only:
            query = query.filter(Reward.is_active)
        return query.order_by(desc(Reward.created_at)).all()

    def get_rewards_by_type(self, reward_type: RewardType) -> list[Reward]:
        """Obtiene recompensas por tipo"""
        return (
            self.db.query(Reward).filter(Reward.reward_type == reward_type, Reward.is_active).all()
        )

    # ==================== UI HELPERS ====================

    # Backward-compatible delegate added for Item 2 (arch-enforcer 1-service rule for reward handlers).
    def get_reward_emoji(self, reward: Reward) -> tuple[str, str]:
        """Retorna (emoji, description) según tipo de recompensa. Delegate a la función pura top-level para mantener compatibilidad."""
        return get_reward_emoji(reward)

    # ==================== ACTUALIZACION Y ELIMINACION ====================

    def update_reward(self, reward_id: int, **kwargs) -> bool:
        """Actualiza una recompensa"""
        reward = self.get_reward(reward_id)
        if not reward:
            return False

        allowed_fields = [
            "name",
            "description",
            "besito_amount",
            "package_id",
            "tariff_id",
            "is_active",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(reward, field):
                setattr(reward, field, value)

        self.db.commit()
        logger.info(f"Recompensa {reward_id} actualizada")
        return True

    def delete_reward(self, reward_id: int) -> bool:
        """Elimina una recompensa de la base de datos (soft delete)"""
        reward = self.get_reward(reward_id)
        if not reward:
            logger.warning(f"Recompensa {reward_id} no encontrada para eliminar")
            return False

        reward.is_active = False
        self.db.commit()
        logger.info(f"Recompensa {reward_id} desactivada (soft delete)")
        return True

    # ==================== ENTREGA DE RECOMPENSAS ====================

    async def deliver_reward(
        self, bot, user_id: int, reward_id: int, mission_id: int = None
    ) -> tuple[bool, str]:
        """
        Entrega una recompensa a un usuario.

        Args:
            bot: Instancia del bot
            user_id: ID del usuario
            reward_id: ID de la recompensa
            mission_id: ID de la mision (opcional, para historial)

        Returns:
            Tuple (exito, mensaje)
        """
        reward = self.get_reward(reward_id)
        if not reward:
            return False, "Recompensa no encontrada"

        if not reward.is_active:
            return False, "Recompensa inactiva"

        try:
            if reward.reward_type == RewardType.BESITOS:
                success, message = await self._deliver_besitos(user_id, reward)
                if success:
                    self.log_reward_delivery(user_id, reward_id, mission_id)
                return success, message

            elif reward.reward_type == RewardType.PACKAGE:
                success, message = await self._deliver_package(bot, user_id, reward)
                if success:
                    self.log_reward_delivery(user_id, reward_id, mission_id)
                return success, message

            elif reward.reward_type == RewardType.VIP_ACCESS:
                success, message = await self._deliver_vip_access(bot, user_id, reward)
                if success:
                    self.log_reward_delivery(user_id, reward_id, mission_id)
                return success, message

            else:
                return False, "Tipo de recompensa no soportado"

        except Exception as e:
            logger.error(f"Error entregando recompensa {reward_id}: {e}")
            return False, f"Error al entregar recompensa: {str(e)}"

    async def _deliver_besitos(self, user_id: int, reward: Reward) -> tuple[bool, str]:
        """Entrega recompensa de besitos (local BesitoService on-demand with shared db for atomicity)."""
        besito_service = BesitoService(
            db=self.db
        )  # local, on-demand; owns=False (db shared); credit commits internally as before
        success = besito_service.credit_besitos(
            user_id=user_id,
            amount=reward.besito_amount,
            source=TransactionSource.MISSION,
            description=f"Recompensa: {reward.name}",
            reference_id=reward.id,
        )

        if success:
            balance = besito_service.get_balance(user_id)
            return True, f"Has recibido {reward.besito_amount} besitos! Tu saldo es: {balance}"
        else:
            return False, "Error al acreditar besitos"

    async def _deliver_package(self, bot, user_id: int, reward: Reward) -> tuple[bool, str]:
        """Entrega recompensa de paquete"""
        if not reward.package_id:
            return False, "Paquete no configurado"

        # Verificar disponibilidad
        package = self.package_service.get_package(reward.package_id)
        if not package:
            return False, "Paquete no encontrado"

        if not package.is_available_for_reward:
            return False, "Paquete no disponible para recompensas"

        # Decrementar stock y entregar
        if not package.decrement_reward_stock():
            return False, "Stock de recompensas agotado"

        self.db.commit()

        # Enviar paquete
        success, message = await self.package_service.deliver_package_to_user(
            bot=bot, user_id=user_id, package_id=reward.package_id
        )

        return success, message if success else "Error al enviar paquete"

    async def _deliver_vip_access(self, bot, user_id: int, reward: Reward) -> tuple[bool, str]:
        """Entrega recompensa de acceso VIP"""
        if not reward.tariff_id:
            return False, "Tarifa VIP no configurada"

        tariff = self.vip_service.get_tariff(reward.tariff_id)
        if not tariff:
            return False, "Tarifa no encontrada"

        # Generar token VIP
        token = self.vip_service.generate_token(reward.tariff_id)

        # Obtener info del bot para construir URL
        bot_info = await bot.get_me()
        token_url = f"https://t.me/{bot_info.username}?start={token.token_code}"

        # Enviar mensaje al usuario
        await bot.send_message(
            chat_id=user_id,
            text=f"""🎩 Lucien:

Diana te ha concedido acceso a El Diván...

👑 Recompensa VIP Activada

📋 Tarifa: {tariff.name}
⏱ Duracion: {tariff.duration_days} dias

🔗 Tu enlace de acceso:
{token_url}

Haz clic para activar tu membresia VIP.""",
        )

        return True, LucienVoice.reward_vip_received(tariff.name, tariff.duration_days)

    # ==================== HISTORIAL ====================

    def log_reward_delivery(
        self, user_id: int, reward_id: int, mission_id: int = None, details: str = None
    ):
        """Registra la entrega de una recompensa"""
        history = UserRewardHistory(
            user_id=user_id, reward_id=reward_id, mission_id=mission_id, details=details
        )
        self.db.add(history)
        self.db.commit()

    def get_user_reward_history(self, user_id: int, limit: int = 20) -> list[UserRewardHistory]:
        """Obtiene el historial de recompensas de un usuario"""
        return (
            self.db.query(UserRewardHistory)
            .filter(UserRewardHistory.user_id == user_id)
            .order_by(desc(UserRewardHistory.delivered_at))
            .limit(limit)
            .all()
        )

    # ==================== ESTADISTICAS ====================

    def get_reward_stats(self, reward_id: int) -> dict:
        """Obtiene estadisticas de una recompensa"""
        reward = self.get_reward(reward_id)
        if not reward:
            return {}

        deliveries = (
            self.db.query(UserRewardHistory)
            .filter(UserRewardHistory.reward_id == reward_id)
            .count()
        )

        return {
            "reward_name": reward.name,
            "type": reward.reward_type.value,
            "total_deliveries": deliveries,
        }

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None
        # Cerrar subs (inofensivo: ellos tienen owns=False cuando db compartido)
        for sub in (
            getattr(self, "besito_service", None),
            getattr(self, "package_service", None),
            getattr(self, "vip_service", None),
        ):
            if sub and hasattr(sub, "close"):
                sub.close()


# =============================================================================
# Cross-domain event listeners (registered explicitly from bot.py on startup).
# The listener lives here (rewards domain ownership). It is a plain async callable
# receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
# (to avoid any re-entrancy with deliver paths or future extensions; delivery contracts
# and partial-failure behavior are authoritative in the credit + log_reward_delivery flow).
# This is observational only (best effort; errors swallowed by bus).
# =============================================================================


async def on_besitos_awarded_rewards_observer(payload: dict) -> None:
    """
    Rewards-domain listener for "besitos_awarded" events (emitted by BesitoService.credit_besitos
    post-commit, including from MISSION reward deliveries in _deliver_besitos).

    DESIRED CONTRACT (copy of narrative precedent): log reception with full context (user_id/amount/source/ref);
    purely observational + wiring proof for this domain. MUST NOT credit, debit, or mutate besitos state here.
    Future extensions (e.g. stats, hints tied to awards) belong in this module and should use
    get_service(RewardService) or direct models if a fresh DB session is required.
    """
    uid = payload.get("user_id")
    amt = payload.get("amount")
    src = payload.get("source")
    ref = payload.get("reference_id")
    logger.info(
        f"rewards | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"
    )
    # No side effects that mutate besitos here (best effort, non-authoritative; 0 impact on deliver_reward contracts).
