"""
Servicio de Recompensas - Lucien Bot

Gestiona la creacion y entrega de recompensas.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, desc, or_

if TYPE_CHECKING:
    from models.models import Package, Tariff
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from keyboards.inline_keyboards import vip_access_keyboard
from models.database import SessionLocal
from models.models import (
    MissionFrequency,
    Reward,
    RewardType,
    TransactionSource,
    UserMissionProgress,
    UserRewardHistory,
)
from services.besito_service import BesitoService
from services.package_service import PackageService
from services.vip_service import VIPService
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)

_DELIVERY_CLAIM_MARKER = "__delivery_claim__"
_CLAIM_TOKEN_PREFIX = "token:"
_CLAIM_SENT_PREFIX = "sent:"
_DELIVERY_CLAIM_TTL_SECONDS = 60


def _finalized_delivery_clause():
    """Excluye claims pendientes del chequeo de idempotencia."""
    return or_(
        UserRewardHistory.details.is_(None),
        and_(
            UserRewardHistory.details != _DELIVERY_CLAIM_MARKER,
            ~UserRewardHistory.details.like(f"{_CLAIM_TOKEN_PREFIX}%"),
            ~UserRewardHistory.details.like(f"{_CLAIM_SENT_PREFIX}%"),
        ),
    )


def _has_prior_vip_grant_attempt(details: str | None) -> bool:
    """True si el claim refleja un intento previo de activación VIP (retry/resend)."""
    if not details:
        return False
    return details.startswith(_CLAIM_TOKEN_PREFIX) or details.startswith(_CLAIM_SENT_PREFIX)


def _is_resumable_delivery_claim(details: str | None) -> bool:
    """True si el claim pendiente puede reanudarse (stale o VIP en vuelo)."""
    if not details:
        return False
    if details == _DELIVERY_CLAIM_MARKER:
        return True
    return details.startswith(_CLAIM_TOKEN_PREFIX) or details.startswith(_CLAIM_SENT_PREFIX)


def _delivery_claim_age_seconds(delivered_at: datetime) -> float:
    """Edad del claim en segundos (timezone-aware)."""
    ref = delivered_at if delivered_at.tzinfo else delivered_at.replace(tzinfo=UTC)
    return (datetime.now(UTC) - ref).total_seconds()


def _is_fresh_delivery_claim(details: str | None, delivered_at: datetime) -> bool:
    """True si __delivery_claim__ aún en vuelo (< TTL); bloquea entregas concurrentes."""
    if details != _DELIVERY_CLAIM_MARKER:
        return False
    return _delivery_claim_age_seconds(delivered_at) < _DELIVERY_CLAIM_TTL_SECONDS


def get_reward_emoji(reward: Reward) -> tuple[str, str]:
    """Retorna (emoji, description) según tipo de recompensa. Función pura (sin estado ni side-effects)."""
    if reward.reward_type == RewardType.BESITOS:
        return "💋", LucienVoice.reward_emoji_besitos(reward.besito_amount)
    elif reward.reward_type == RewardType.PACKAGE:
        return "📦", LucienVoice.reward_emoji_package(reward.name)
    elif reward.reward_type == RewardType.VIP_ACCESS:
        return "👑", LucienVoice.reward_emoji_vip(reward.name)
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

    # Support added for reward_admin_handlers 1-service + pure extract (item34).
    # Arch-enforcer long-funcs + multi-service note addressed. Precedent item7/8/9.
    def get_available_packages_for_rewards(self) -> list[Package]:
        """Thin delegate to PackageService.get_available_packages_for_rewards().
        Added for item34: enables reward_admin_handlers package selection in reward wizard to call exactly 1 service (RewardService) per handlers/CLAUDE + arch rules.
        Not core CRUD. 0 behavior change. Precedent item8/9.
        """
        from services.package_service import PackageService

        return PackageService(db=self._get_db()).get_available_packages_for_rewards()

    def get_all_tariffs(self, active_only: bool = True) -> list[Tariff]:
        """Thin delegate to VIPService.get_all_tariffs(active_only).
        Added for item34: enables reward_admin_handlers tariff selection for VIP rewards to call exactly 1 service (RewardService).
        Not core CRUD. 0 behavior change. Precedent item8/9.
        """
        from services.vip_service import VIPService

        return VIPService(db=self._get_db()).get_all_tariffs(active_only=active_only)

    def get_tariff(self, tariff_id: int) -> Tariff | None:
        """Thin delegate to VIPService.get_tariff(tariff_id).
        Added for item34: enables reward_admin_handlers tariff lookup in confirm/display.
        Not core CRUD. 0 behavior change. Precedent item8/9.
        """
        from services.vip_service import VIPService

        return VIPService(db=self._get_db()).get_tariff(tariff_id)

    def get_package(self, package_id: int) -> Package | None:
        """Thin delegate to PackageService.get_package(package_id).
        Added for item34: enables reward_admin_handlers confirm display to enrich package name without direct PackageService.
        Not core CRUD. 0 behavior change. Precedent item8/9.
        """
        from services.package_service import PackageService
        return PackageService(db=self._get_db()).get_package(package_id)

    def create_package_for_reward_wizard(
        self,
        name: str,
        description: str,
        store_stock: int,
        reward_stock: int,
        files: list[dict],
        created_by: int,
    ) -> Package:
        """Thin orchestration: create package (store_stock=-2) + add files for reward wizard.
        Added for item34: enables reward_admin_handlers package creation sub-wizard to call exactly 1 service (RewardService).
        Not core reward CRUD. 0 behavior change. Precedent pattern for cross in admin wizards.
        """
        from services.package_service import PackageService

        ps = PackageService(db=self._get_db())
        pkg = ps.create_package(
            name=name,
            description=description,
            store_stock=store_stock,
            reward_stock=reward_stock,
            created_by=created_by,
        )
        for i, f in enumerate(files or []):
            ps.add_file_to_package(
                package_id=pkg.id,
                file_id=f["file_id"],
                file_type=f["file_type"],
                file_name=f.get("file_name"),
                order_index=i,
            )
        return pkg

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
        self,
        bot,
        user_id: int,
        reward_id: int,
        mission_id: int = None,
        *,
        history_claimed: bool = False,
        since_completed_at: datetime | None = None,
        frequency: MissionFrequency = MissionFrequency.ONE_TIME,
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
            return False, LucienVoice.reward_not_found()

        if not reward.is_active:
            return False, LucienVoice.reward_inactive()

        try:
            if reward.reward_type == RewardType.BESITOS:
                success, message = await self._deliver_besitos(
                    user_id, reward, mission_id=mission_id
                )
            elif reward.reward_type == RewardType.PACKAGE:
                success, message = await self._deliver_package(
                    bot,
                    user_id,
                    reward,
                    mission_id=mission_id,
                    since_completed_at=since_completed_at,
                    frequency=frequency,
                )
            elif reward.reward_type == RewardType.VIP_ACCESS:
                success, message = await self._deliver_vip_access(
                    bot, user_id, reward, mission_id=mission_id
                )
            else:
                return False, LucienVoice.reward_type_unsupported()

            if success and not history_claimed:
                self.log_reward_delivery(user_id, reward_id, mission_id)
            elif success and history_claimed:
                self._finalize_delivery_claim(user_id, mission_id, reward_id)
            return success, message

        except Exception as e:
            logger.error(f"Error entregando recompensa {reward_id}: {e}")
            return False, LucienVoice.reward_delivery_error()

    def _besitos_credit_reference_id(
        self, user_id: int, reward_id: int, mission_id: int | None
    ) -> int:
        """reference_id del crédito: claim.id por ciclo de misión, reward.id fuera de misión."""
        if mission_id:
            claim = self._get_mission_delivery_claim(user_id, mission_id, reward_id)
            if claim:
                return claim.id
        return reward_id

    def _has_mission_besitos_credit(
        self,
        user_id: int,
        reward_id: int,
        *,
        mission_id: int | None = None,
    ) -> bool:
        """True si ya existe crédito MISSION para este ciclo/claim (evita doble acreditación)."""
        from models.models import BesitoTransaction

        ref_id = self._besitos_credit_reference_id(user_id, reward_id, mission_id)
        return (
            self.db.query(BesitoTransaction)
            .filter(
                BesitoTransaction.user_id == user_id,
                BesitoTransaction.source == TransactionSource.MISSION,
                BesitoTransaction.reference_id == ref_id,
            )
            .first()
            is not None
        )

    async def _deliver_besitos(
        self,
        user_id: int,
        reward: Reward,
        *,
        mission_id: int | None = None,
    ) -> tuple[bool, str]:
        """Entrega recompensa de besitos (local BesitoService on-demand with shared db for atomicity)."""
        besito_service = BesitoService(db=self.db)
        if self._has_mission_besitos_credit(user_id, reward.id, mission_id=mission_id):
            balance = besito_service.get_balance(user_id)
            return True, LucienVoice.reward_besitos_received(reward.besito_amount, balance)

        ref_id = self._besitos_credit_reference_id(user_id, reward.id, mission_id)
        success = besito_service.credit_besitos(
            user_id=user_id,
            amount=reward.besito_amount,
            source=TransactionSource.MISSION,
            description=f"Recompensa: {reward.name}",
            reference_id=ref_id,
        )
        if success:
            balance = besito_service.get_balance(user_id)
            return True, LucienVoice.reward_besitos_received(reward.besito_amount, balance)
        return False, LucienVoice.reward_besitos_failed()

    async def _deliver_package(
        self,
        bot,
        user_id: int,
        reward: Reward,
        *,
        mission_id: int | None = None,
        since_completed_at: datetime | None = None,
        frequency: MissionFrequency = MissionFrequency.ONE_TIME,
    ) -> tuple[bool, str]:
        """Entrega recompensa de paquete"""
        if not reward.package_id:
            return False, LucienVoice.reward_package_not_configured()

        if mission_id and self.has_mission_reward_been_delivered(
            user_id,
            mission_id,
            since_completed_at=since_completed_at,
            frequency=frequency,
        ):
            package = self.package_service.get_package(reward.package_id)
            name = package.name if package else reward.name
            return True, LucienVoice.reward_emoji_package(name)[1]

        # Verificar disponibilidad
        package = self.package_service.get_package(reward.package_id)
        if not package:
            return False, LucienVoice.reward_package_not_found()

        if not package.is_available_for_reward:
            return False, LucienVoice.reward_package_unavailable()

        if not package.decrement_reward_stock():
            return False, LucienVoice.reward_stock_depleted()

        success, message = await self.package_service.deliver_package_to_user(
            bot=bot,
            user_id=user_id,
            package_id=reward.package_id,
            delivery_source="reward",
        )
        if not success:
            # Fallo permanente: el usuario nunca podrá recibir este paquete
            if message.startswith("permanent:"):
                logger.warning(
                    f"reward_service | _deliver_package | permanent_failure | "
                    f"user_id={user_id} | package_id={reward.package_id} | reason={message}"
                )
                if mission_id:
                    self._finalize_delivery_claim(user_id, mission_id, reward.id)
                self.db.commit()
                return True, message

            if package.reward_stock >= 0:
                package.reward_stock += 1
            self.db.commit()
            return False, LucienVoice.reward_package_delivery_failed()

        self.db.commit()
        return success, message

    async def _mark_vip_partial_grant(
        self, claim: UserRewardHistory | None, metadata: dict
    ) -> None:
        """Persist token: marker so retry resends instead of re-granting."""
        if not claim:
            return
        token_id = metadata.get("token_id")
        if token_id is not None:
            claim.details = f"{_CLAIM_TOKEN_PREFIX}{token_id}"
            self.db.commit()

    async def _mark_vip_delivery_sent(
        self, claim: UserRewardHistory | None, metadata: dict
    ) -> None:
        if not claim:
            return
        token_id = metadata.get("token_id")
        claim.details = f"{_CLAIM_SENT_PREFIX}vip_activated:{token_id}"
        self.db.commit()

    async def _send_vip_access_message(self, bot, user_id: int, message: str) -> None:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=vip_access_keyboard(),
            parse_mode="HTML",
        )

    async def _deliver_vip_access(
        self, bot, user_id: int, reward: Reward, *, mission_id: int | None = None
    ) -> tuple[bool, str]:
        """Entrega recompensa de acceso VIP con activación inmediata."""
        if not reward.tariff_id:
            return False, LucienVoice.reward_vip_not_configured()

        tariff = self.vip_service.get_tariff(reward.tariff_id)
        if not tariff:
            return False, LucienVoice.reward_tariff_not_found()

        claim = (
            self._get_mission_delivery_claim(user_id, mission_id, reward.id) if mission_id else None
        )
        already_sent = claim and claim.details and claim.details.startswith(_CLAIM_SENT_PREFIX)
        received_msg = LucienVoice.reward_vip_received(tariff.name, tariff.duration_days)

        if already_sent and self.vip_service.is_user_vip(user_id):
            return True, received_msg

        prior_grant = claim and _has_prior_vip_grant_attempt(claim.details)
        if prior_grant and self.vip_service.is_user_vip(user_id):
            ok, msg, _invite = await self.vip_service.resend_vip_invite_for_user(bot, user_id)
            if not ok:
                return False, msg
            try:
                await self._send_vip_access_message(bot, user_id, msg)
            except Exception as exc:
                logger.error(
                    f"reward_service | _deliver_vip_access | send_failed | "
                    f"user_id={user_id} | error={exc}"
                )
                return False, LucienVoice.reward_delivery_error()
            await self._mark_vip_delivery_sent(claim, {"token_id": "resend"})
            return True, received_msg

        ok, msg, metadata = await self.vip_service.grant_vip_from_tariff(
            bot, user_id, reward.tariff_id
        )
        if not ok:
            if metadata.get("vip_activated"):
                await self._mark_vip_partial_grant(claim, metadata)
            return False, msg
        try:
            await self._send_vip_access_message(bot, user_id, msg)
        except Exception as exc:
            logger.error(
                f"reward_service | _deliver_vip_access | send_failed | "
                f"user_id={user_id} | error={exc}"
            )
            await self._mark_vip_partial_grant(claim, metadata)
            return False, LucienVoice.reward_delivery_error()
        await self._mark_vip_delivery_sent(claim, metadata)
        return True, received_msg

    # ==================== HISTORIAL ====================

    def _get_mission_delivery_claim(
        self, user_id: int, mission_id: int, reward_id: int
    ) -> UserRewardHistory | None:
        return (
            self.db.query(UserRewardHistory)
            .filter(
                UserRewardHistory.user_id == user_id,
                UserRewardHistory.mission_id == mission_id,
                UserRewardHistory.reward_id == reward_id,
            )
            .order_by(desc(UserRewardHistory.delivered_at))
            .first()
        )

    def try_claim_mission_delivery(
        self,
        user_id: int,
        mission_id: int,
        reward_id: int,
        *,
        since_completed_at: datetime | None,
        frequency: MissionFrequency,
    ) -> bool:
        """Reserva atómicamente el slot de entrega antes de side-effects."""
        progress = (
            self.db.query(UserMissionProgress)
            .filter(
                UserMissionProgress.user_id == user_id,
                UserMissionProgress.mission_id == mission_id,
            )
            .with_for_update()
            .first()
        )
        if not progress or not progress.is_completed:
            return False
        cycle_at = since_completed_at or progress.completed_at
        if self.has_mission_reward_been_delivered(
            user_id,
            mission_id,
            since_completed_at=cycle_at,
            frequency=frequency,
        ):
            return False
        existing = self._get_mission_delivery_claim(user_id, mission_id, reward_id)
        if existing and _is_resumable_delivery_claim(existing.details):
            if _is_fresh_delivery_claim(existing.details, existing.delivered_at):
                return False
            return True
        self.db.add(
            UserRewardHistory(
                user_id=user_id,
                reward_id=reward_id,
                mission_id=mission_id,
                details=_DELIVERY_CLAIM_MARKER,
            )
        )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return False
        return True

    def release_mission_delivery_claim(self, user_id: int, mission_id: int, reward_id: int) -> None:
        """Libera claim pendiente tras fallo. No borra si besitos ya fueron acreditados."""
        claim = self._get_mission_delivery_claim(user_id, mission_id, reward_id)
        if not claim or claim.details != _DELIVERY_CLAIM_MARKER:
            return
        if self._has_mission_besitos_credit(user_id, reward_id, mission_id=mission_id):
            self._finalize_delivery_claim(user_id, mission_id, reward_id)
            return
        self.db.delete(claim)
        self.db.commit()

    def _finalize_delivery_claim(
        self, user_id: int, mission_id: int | None, reward_id: int
    ) -> None:
        """Marca claim como entrega finalizada."""
        if not mission_id:
            return
        claim = self._get_mission_delivery_claim(user_id, mission_id, reward_id)
        if claim:
            claim.details = None
            self.db.commit()

    def has_mission_reward_been_delivered(
        self,
        user_id: int,
        mission_id: int,
        *,
        since_completed_at: datetime | None = None,
        frequency: MissionFrequency = MissionFrequency.ONE_TIME,
    ) -> bool:
        """Idempotencia: ONE_TIME si hay historial; RECURRING por ciclo (completed_at)."""
        query = self.db.query(UserRewardHistory).filter(
            UserRewardHistory.user_id == user_id,
            UserRewardHistory.mission_id == mission_id,
            _finalized_delivery_clause(),
        )
        if frequency == MissionFrequency.RECURRING and since_completed_at is not None:
            ref = (
                since_completed_at
                if since_completed_at.tzinfo
                else since_completed_at.replace(tzinfo=UTC)
            )
            return query.filter(UserRewardHistory.delivered_at >= ref).first() is not None
        return query.first() is not None

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
