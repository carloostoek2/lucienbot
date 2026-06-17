"""
Servicio de Misiones - Lucien Bot

Gestiona la creacion, progreso y completacion de misiones.
"""

import html
import logging
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config.settings import bot_config
from models.database import SessionLocal
from models.models import (
    DailyGiftClaim,
    Mission,
    MissionFrequency,
    MissionType,
    Reward,
    RewardType,
    UserMissionProgress,
)
from services.reward_service import RewardService
from utils.bot_runtime import resolve_delivery_bot
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)


class MissionDeliveryResult(str, Enum):
    """Resultado de intento de entrega automática de recompensa de misión."""

    NEWLY_DELIVERED = "newly_delivered"
    ALREADY_DELIVERED = "already_delivered"
    COOLDOWN = "cooldown"
    NO_BOT = "no_bot"
    FAILED = "failed"


def _prepare_recurring_cycle_reset(
    progress: UserMissionProgress, mission: Mission
) -> datetime | None:
    """Captura completed_at previo y reinicia progreso RECURRING. Retorna previous_completed_at."""
    previous_completed_at = progress.completed_at
    progress.current_value = 0
    progress.is_completed = False
    progress.completed_at = None
    progress.last_reference_id = None
    return previous_completed_at


def _apply_progress_increment(
    progress: UserMissionProgress,
    mission: Mission,
    amount: int,
    reference_id: int | None,
) -> tuple[datetime | None, bool]:
    """Incrementa progreso; retorna (previous_completed_at, newly_completed)."""
    if reference_id is not None and progress.last_reference_id == reference_id:
        logger.debug(f"Mision {mission.id}: duplicado skipeado ref={reference_id}")
        return None, False

    progress.current_value += amount
    if reference_id is not None:
        progress.last_reference_id = reference_id

    previous_completed_at = progress.completed_at
    if progress.current_value >= mission.target_value:
        progress.is_completed = True
        progress.completed_at = datetime.now(UTC)
        return previous_completed_at, True
    return previous_completed_at, False


def _recurring_cooldown_blocks(
    mission: Mission,
    previous_completed_at: datetime | None,
    progress: UserMissionProgress,
) -> bool:
    """True si RECURRING está en cooldown y no debe entregarse aún."""
    cooldown_ref = previous_completed_at or progress.last_updated
    if (
        mission.frequency != MissionFrequency.RECURRING
        or not mission.cooldown_hours
        or not cooldown_ref
    ):
        return False
    ref = cooldown_ref if cooldown_ref.tzinfo else cooldown_ref.replace(tzinfo=UTC)
    hours_since = (datetime.now(UTC) - ref).total_seconds() / 3600
    return hours_since < mission.cooldown_hours


async def _send_mission_celebration_message(
    bot, user_id: int, mission: Mission, reward: Reward, db: Session
) -> None:
    """Mensaje de celebración de Lucien tras entrega exitosa (no duplica contenido)."""
    safe_mission = html.escape(mission.name)
    if reward.reward_type == RewardType.BESITOS:
        from services.besito_service import BesitoService

        balance = BesitoService(db=db).get_balance(user_id)
        text = LucienVoice.mission_reward_besitos_delivered(
            safe_mission, reward.besito_amount, balance
        )
    elif reward.reward_type == RewardType.PACKAGE:
        text = LucienVoice.mission_reward_package_delivered(
            safe_mission, html.escape(reward.name)
        )
    elif reward.reward_type == RewardType.VIP_ACCESS:
        tariff_name = html.escape(reward.name)
        if reward.tariff_id:
            from services.vip_service import VIPService

            tariff = VIPService(db=db).get_tariff(reward.tariff_id)
            if tariff:
                tariff_name = html.escape(tariff.name)
        text = LucienVoice.mission_reward_vip_delivered(safe_mission, tariff_name)
    else:
        return
    await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")


def calculate_daily_gift_streak_from_dates(claim_dates: set[date], today: date) -> int:
    """Función pura: días consecutivos de reclamo terminando en ``today``."""
    if today not in claim_dates:
        return 0
    streak = 0
    cursor = today
    while cursor in claim_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


class MissionService:
    """Servicio para gestion de misiones"""

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Obtiene la sesión de base de datos activa."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    # ==================== CREACION DE MISIONES ====================

    def create_mission(
        self,
        name: str,
        description: str,
        mission_type: MissionType,
        target_value: int,
        reward_id: int = None,
        frequency: MissionFrequency = MissionFrequency.ONE_TIME,
        start_date: datetime = None,
        end_date: datetime = None,
        created_by: int = None,
    ) -> Mission:
        """Crea una nueva mision"""
        db = self._get_db()
        mission = Mission(
            name=name,
            description=description,
            mission_type=mission_type,
            target_value=target_value,
            reward_id=reward_id,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by,
            is_active=True,
        )
        db.add(mission)
        db.commit()
        db.refresh(mission)
        logger.info(f"Mision creada: {name} (ID: {mission.id})")
        return mission

    # ==================== CONSULTAS ====================

    def get_mission(self, mission_id: int) -> Mission | None:
        """Obtiene una mision por ID"""
        db = self._get_db()
        return db.query(Mission).filter(Mission.id == mission_id).first()

    def get_all_missions(self, active_only: bool = True) -> list[Mission]:
        """Obtiene todas las misiones"""
        db = self._get_db()
        query = db.query(Mission)
        if active_only:
            query = query.filter(Mission.is_active)
        return query.order_by(desc(Mission.created_at)).all()

    def get_available_missions(self) -> list[Mission]:
        """Obtiene misiones disponibles actualmente"""
        db = self._get_db()
        now = datetime.now(UTC)
        return (
            db.query(Mission)
            .filter(
                Mission.is_active,
                (Mission.start_date == None) | (Mission.start_date <= now),  # noqa: E711
                (Mission.end_date == None) | (Mission.end_date >= now),  # noqa: E711
            )
            .order_by(desc(Mission.created_at))
            .all()
        )

    def get_missions_by_type(self, mission_type: MissionType) -> list[Mission]:
        """Obtiene misiones por tipo"""
        db = self._get_db()
        return (
            db.query(Mission).filter(Mission.mission_type == mission_type, Mission.is_active).all()
        )

    # ==================== PROGRESO DE USUARIO ====================

    def get_or_create_progress(self, user_id: int, mission_id: int) -> UserMissionProgress:
        """Obtiene o crea el progreso de un usuario en una mision"""
        db = self._get_db()
        mission = self.get_mission(mission_id)
        if not mission:
            raise ValueError("Mision no encontrada")

        progress = (
            db.query(UserMissionProgress)
            .filter(
                UserMissionProgress.user_id == user_id, UserMissionProgress.mission_id == mission_id
            )
            .first()
        )

        if not progress:
            progress = UserMissionProgress(
                user_id=user_id,
                mission_id=mission_id,
                target_value=mission.target_value,
                current_value=0,
                is_completed=False,
            )
            db.add(progress)
            db.commit()
            db.refresh(progress)
            logger.info(f"Progreso creado: user={user_id}, mission={mission_id}")

        return progress

    def _get_or_create_progress_locked(
        self, user_id: int, mission_id: int
    ) -> UserMissionProgress:
        """Obtiene o crea progreso con lock de fila para actualizaciones concurrentes."""
        db = self._get_db()
        mission = self.get_mission(mission_id)
        if not mission:
            raise ValueError("Mision no encontrada")

        progress = (
            db.query(UserMissionProgress)
            .filter(
                UserMissionProgress.user_id == user_id,
                UserMissionProgress.mission_id == mission_id,
            )
            .with_for_update()
            .first()
        )
        if progress:
            return progress

        progress = UserMissionProgress(
            user_id=user_id,
            mission_id=mission_id,
            target_value=mission.target_value,
            current_value=0,
            is_completed=False,
        )
        db.add(progress)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            progress = (
                db.query(UserMissionProgress)
                .filter(
                    UserMissionProgress.user_id == user_id,
                    UserMissionProgress.mission_id == mission_id,
                )
                .with_for_update()
                .first()
            )
            if not progress:
                raise
        return progress

    def calculate_user_daily_gift_streak(self, user_id: int) -> int:
        """Calcula la racha actual de regalo diario (días consecutivos hasta hoy)."""
        db = self._get_db()
        tz = ZoneInfo(bot_config.TIMEZONE)
        today = datetime.now(tz).date()
        claims = (
            db.query(DailyGiftClaim)
            .filter(DailyGiftClaim.user_id == user_id)
            .order_by(desc(DailyGiftClaim.claimed_at))
            .limit(400)
            .all()
        )
        claim_dates = {
            c.claimed_at.astimezone(tz).date()
            if c.claimed_at.tzinfo
            else c.claimed_at.replace(tzinfo=UTC).astimezone(tz).date()
            for c in claims
        }
        return calculate_daily_gift_streak_from_dates(claim_dates, today)

    def get_user_progress(self, user_id: int, mission_id: int) -> UserMissionProgress | None:
        """Obtiene el progreso de un usuario en una mision"""
        db = self._get_db()
        return (
            db.query(UserMissionProgress)
            .filter(
                UserMissionProgress.user_id == user_id, UserMissionProgress.mission_id == mission_id
            )
            .first()
        )

    def get_user_all_progress(self, user_id: int) -> list[UserMissionProgress]:
        """Obtiene todo el progreso de un usuario"""
        db = self._get_db()
        return (
            db.query(UserMissionProgress)
            .filter(UserMissionProgress.user_id == user_id)
            .order_by(desc(UserMissionProgress.last_updated))
            .all()
        )

    async def get_user_active_missions(self, user_id: int, bot=None) -> list[dict]:
        """Obtiene las misiones activas de un usuario con su progreso."""
        if bot is not None:
            await self._catch_up_pending_rewards(user_id, bot)
        available_missions = self.get_available_missions()
        result = []

        for mission in available_missions:
            progress = self.get_user_progress(user_id, mission.id)

            if (
                progress
                and progress.is_completed
                and mission.frequency == MissionFrequency.ONE_TIME
            ):
                continue  # Mision completada y no recurrente

            if not progress:
                progress = self.get_or_create_progress(user_id, mission.id)

            result.append(
                {
                    "mission": mission,
                    "progress": progress,
                    "percentage": min(
                        100, int((progress.current_value / mission.target_value) * 100)
                    ),
                }
            )

        return result

    async def get_available_rewards_for_user(self, user_id: int, bot=None) -> list[dict]:
        """Recompensas disponibles con misión, progreso y estado de entrega."""
        if bot is not None:
            await self._catch_up_pending_rewards(user_id, bot)
        db = self._get_db()
        available_missions = self.get_available_missions()
        result = []
        reward_service = RewardService(db)

        for mission in available_missions:
            if not mission.reward_id:
                continue

            progress = self.get_user_progress(user_id, mission.id)
            if (
                progress
                and progress.is_completed
                and mission.frequency == MissionFrequency.ONE_TIME
            ):
                continue

            reward = reward_service.get_reward(mission.reward_id)
            if reward and reward.is_active:
                delivered = self._is_reward_delivered_for_progress(
                    reward_service, user_id, mission, progress
                )
                result.append(
                    {
                        "mission": mission,
                        "reward": reward,
                        "progress": progress,
                        "reward_delivered": delivered,
                    }
                )

        return result

    def _is_reward_delivered_for_progress(
        self,
        reward_service: RewardService,
        user_id: int,
        mission: Mission,
        progress: UserMissionProgress | None,
    ) -> bool:
        """True si el ciclo actual ya tiene historial de entrega."""
        if not progress or not progress.is_completed:
            return False
        return reward_service.has_mission_reward_been_delivered(
            user_id,
            mission.id,
            since_completed_at=progress.completed_at,
            frequency=mission.frequency,
        )

    async def _catch_up_pending_rewards(self, user_id: int, bot) -> None:
        """Best-effort: reintenta entregas pendientes sin bloquear UX."""
        try:
            await self.deliver_pending_rewards(user_id, bot=bot)
        except Exception as exc:
            logger.warning(
                f"mission_service | catch_up_pending | user_id={user_id} | error={exc}"
            )

    # Support added for mission_admin_handlers 1-service + pure extract (item9).
    # Arch-enforcer long-funcs note addressed. Precedent item7 (reward) + item8 (store-admin).

    def get_all_rewards_for_mission_wizard(self) -> list["Reward"]:
        """Thin delegate to RewardService.get_all_rewards(active_only=True).
        Added for item9: enables mission_admin_handlers reward select steps (select_frequency, select_reward_for_mission) to call exactly 1 service (MissionService) per handlers/CLAUDE + arch rules.
        Not core CRUD. 0 behavior change. Precedent item8 get_available_packages_for_store.
        """
        # Spawn internal (mission_service already does RewardService(db) in get_available_rewards_for_user + deliver paths; keep pattern, no new held).
        reward_service = RewardService(db=self._get_db())
        return reward_service.get_all_rewards(active_only=True)

    def get_reward_for_mission_wizard(self, reward_id: int) -> "Reward | None":
        """Thin delegate to RewardService.get_reward(reward_id).
        Added for item9: enables mission_admin_handlers select_reward_for_mission summary to call exactly 1 service (MissionService) per handlers/CLAUDE + arch rules.
        Not core CRUD. 0 behavior change. Precedent item8 get_available_packages_for_store.
        """
        reward_service = RewardService(db=self._get_db())
        return reward_service.get_reward(reward_id)

    # ==================== ACTUALIZACION DE PROGRESO ====================

    def increment_progress(
        self, user_id: int, mission_type: MissionType, amount: int = 1, reference_id: int = None
    ) -> list[UserMissionProgress]:
        """
        Incrementa el progreso del usuario en todas las misiones del tipo especificado.
        Retorna las misiones completadas.

        Args:
            user_id: ID del usuario
            mission_type: Tipo de misión
            amount: Cantidad a incrementar
            reference_id: ID de referencia (broadcast_id) para evitar duplicados
        """
        db = self._get_db()
        missions = self.get_missions_by_type(mission_type)
        completed = []

        for mission in missions:
            if not mission.is_available:
                continue

            progress = self._get_or_create_progress_locked(user_id, mission.id)

            if progress.is_completed and mission.frequency == MissionFrequency.ONE_TIME:
                continue

            if progress.is_completed and mission.frequency == MissionFrequency.RECURRING:
                progress.current_value = 0
                progress.is_completed = False
                progress.completed_at = None
                progress.last_reference_id = None

            if reference_id is not None and progress.last_reference_id == reference_id:
                logger.debug(f"Mision {mission.id}: duplicado skipeado ref={reference_id}")
                continue

            progress.current_value += amount
            if reference_id is not None:
                progress.last_reference_id = reference_id

            if progress.current_value >= mission.target_value:
                progress.is_completed = True
                progress.completed_at = datetime.now(UTC)
                completed.append(progress)
                logger.info(f"Mision completada: user={user_id}, mission={mission.id}")

            db.commit()

        return completed

    async def increment_progress_and_deliver(
        self,
        user_id: int,
        mission_type: MissionType,
        amount: int = 1,
        bot=None,
        reference_id: int = None,
    ) -> list[UserMissionProgress]:
        """Incrementa el progreso y entrega recompensas automaticamente."""
        db = self._get_db()
        completed = []
        for mission in self.get_missions_by_type(mission_type):
            progress = await self._increment_one_mission_and_deliver(
                db, user_id, mission, amount, bot, reference_id
            )
            if progress:
                completed.append(progress)
        return completed

    async def _increment_one_mission_and_deliver(
        self,
        db: Session,
        user_id: int,
        mission: Mission,
        amount: int,
        bot,
        reference_id: int | None,
    ) -> UserMissionProgress | None:
        """Incrementa una misión y entrega recompensa si aplica."""
        if not mission.is_available:
            return None

        progress = self._get_or_create_progress_locked(user_id, mission.id)
        if progress.is_completed and mission.frequency == MissionFrequency.ONE_TIME:
            return None

        if reference_id is not None and progress.last_reference_id == reference_id:
            logger.debug(f"Mision {mission.id}: duplicado skipeado ref={reference_id}")
            return None

        previous_completed_at = None
        if progress.is_completed and mission.frequency == MissionFrequency.RECURRING:
            previous_completed_at = _prepare_recurring_cycle_reset(progress, mission)

        prev_at, newly_completed = _apply_progress_increment(
            progress, mission, amount, reference_id
        )
        if previous_completed_at is None:
            previous_completed_at = prev_at

        if newly_completed:
            logger.info(f"Mision completada: user={user_id}, mission={mission.id}")

        db.commit()

        if newly_completed and mission.reward_id:
            await self._deliver_mission_reward_if_allowed(
                db, user_id, mission, previous_completed_at, progress, bot=bot
            )
        return progress if newly_completed else None

    async def _send_celebration_if_delivered(
        self, delivery_bot, user_id: int, mission: Mission, reward_service: RewardService, db: Session
    ) -> None:
        """Best-effort: mensaje de celebración tras entrega exitosa."""
        reward = reward_service.get_reward(mission.reward_id)
        if not reward:
            return
        try:
            await _send_mission_celebration_message(delivery_bot, user_id, mission, reward, db)
        except Exception as exc:
            logger.warning(
                f"mission_service | celebration_msg | user_id={user_id} | "
                f"mission_id={mission.id} | error={exc}"
            )

    def _log_delivery_attempt(
        self, user_id: int, mission: Mission, result: MissionDeliveryResult
    ) -> None:
        logger.info(
            f"mission_service | auto_deliver | user_id={user_id} | "
            f"mission_id={mission.id} | reward_id={mission.reward_id} | result={result.value}"
        )

    def _mission_reward_prechecks(
        self,
        user_id: int,
        mission: Mission,
        previous_completed_at: datetime | None,
        progress: UserMissionProgress,
        reward_service: RewardService,
        *,
        skip_cooldown: bool,
    ) -> MissionDeliveryResult | None:
        """Valida cooldown e idempotencia antes de claim. None si puede continuar."""
        if not skip_cooldown and _recurring_cooldown_blocks(
            mission, previous_completed_at, progress
        ):
            self._log_delivery_attempt(user_id, mission, MissionDeliveryResult.COOLDOWN)
            return MissionDeliveryResult.COOLDOWN
        if reward_service.has_mission_reward_been_delivered(
            user_id,
            mission.id,
            since_completed_at=progress.completed_at,
            frequency=mission.frequency,
        ):
            self._log_delivery_attempt(user_id, mission, MissionDeliveryResult.ALREADY_DELIVERED)
            return MissionDeliveryResult.ALREADY_DELIVERED
        return None

    async def _execute_mission_reward_delivery(
        self,
        db: Session,
        delivery_bot,
        user_id: int,
        mission: Mission,
        progress: UserMissionProgress,
        reward_service: RewardService,
    ) -> MissionDeliveryResult:
        """Claim atómico + deliver_reward + celebración."""
        claimed = reward_service.try_claim_mission_delivery(
            user_id,
            mission.id,
            mission.reward_id,
            since_completed_at=progress.completed_at,
            frequency=mission.frequency,
        )
        if not claimed:
            self._log_delivery_attempt(user_id, mission, MissionDeliveryResult.ALREADY_DELIVERED)
            return MissionDeliveryResult.ALREADY_DELIVERED

        success, _message = await reward_service.deliver_reward(
            bot=delivery_bot,
            user_id=user_id,
            reward_id=mission.reward_id,
            mission_id=mission.id,
            history_claimed=True,
            since_completed_at=progress.completed_at,
            frequency=mission.frequency,
        )
        if not success:
            reward = reward_service.get_reward(mission.reward_id)
            if reward and reward.reward_type != RewardType.VIP_ACCESS:
                reward_service.release_mission_delivery_claim(
                    user_id, mission.id, mission.reward_id
                )
            self._log_delivery_attempt(user_id, mission, MissionDeliveryResult.FAILED)
            return MissionDeliveryResult.FAILED

        # Saltar celebración si la entrega fue un fallo permanente (chat no existe o bot bloqueado)
        if not _message.startswith("permanent:"):
            await self._send_celebration_if_delivered(
                delivery_bot, user_id, mission, reward_service, db
            )
        self._log_delivery_attempt(user_id, mission, MissionDeliveryResult.NEWLY_DELIVERED)
        return MissionDeliveryResult.NEWLY_DELIVERED

    async def _deliver_mission_reward_if_allowed(
        self,
        db: Session,
        user_id: int,
        mission: Mission,
        previous_completed_at: datetime | None,
        progress: UserMissionProgress,
        bot=None,
        *,
        skip_cooldown: bool = False,
    ) -> MissionDeliveryResult:
        """Entrega recompensa post-commit con claim atómico e idempotencia."""
        delivery_bot = resolve_delivery_bot(bot)
        if delivery_bot is None:
            self._log_delivery_attempt(user_id, mission, MissionDeliveryResult.NO_BOT)
            return MissionDeliveryResult.NO_BOT

        reward_service = RewardService(db)
        blocked = self._mission_reward_prechecks(
            user_id, mission, previous_completed_at, progress, reward_service,
            skip_cooldown=skip_cooldown,
        )
        if blocked is not None:
            return blocked

        return await self._execute_mission_reward_delivery(
            db, delivery_bot, user_id, mission, progress, reward_service
        )

    async def apply_daily_gift_mission_updates(self, user_id: int, bot=None) -> int:
        """Actualiza misiones DAILY_GIFT_* tras un reclamo exitoso. Retorna completadas."""
        db = self._get_db()
        streak = self.calculate_user_daily_gift_streak(user_id)
        last_claim = (
            db.query(DailyGiftClaim)
            .filter(DailyGiftClaim.user_id == user_id)
            .order_by(desc(DailyGiftClaim.claimed_at))
            .first()
        )
        claim_ref = last_claim.id if last_claim else None
        completed_count = 0

        for mission in self.get_missions_by_type(MissionType.DAILY_GIFT_STREAK):
            if not mission.is_available:
                continue
            progress = self.set_progress(user_id, mission.id, streak)
            if progress and progress.is_completed:
                completed_count += 1
                if mission.reward_id:
                    await self._deliver_mission_reward_if_allowed(
                        db,
                        user_id,
                        mission,
                        progress.completed_at,
                        progress,
                        bot=bot,
                    )

        total_done = await self.increment_progress_and_deliver(
            user_id,
            MissionType.DAILY_GIFT_TOTAL,
            amount=1,
            bot=bot,
            reference_id=claim_ref,
        )
        return completed_count + len(total_done)

    async def apply_vip_active_mission_updates(self, user_id: int, bot=None) -> int:
        """Completa misiones VIP_ACTIVE y entrega recompensas al activar VIP."""
        db = self._get_db()
        completed = 0
        for mission in self.get_missions_by_type(MissionType.VIP_ACTIVE):
            if not mission.is_available:
                continue
            progress = self.set_progress(user_id, mission.id, mission.target_value)
            if progress and progress.is_completed:
                completed += 1
                logger.info(f"Mision VIP completada: user={user_id}, mission={mission.id}")
                if mission.reward_id:
                    await self._deliver_mission_reward_if_allowed(
                        db,
                        user_id,
                        mission,
                        progress.completed_at,
                        progress,
                        bot=bot,
                    )
        return completed

    def get_users_with_pending_reward_deliveries(self) -> list[int]:
        """Usuarios con misiones completadas sin entrega del ciclo actual."""
        db = self._get_db()
        reward_service = RewardService(db)
        user_ids: set[int] = set()
        rows = (
            db.query(UserMissionProgress)
            .filter(UserMissionProgress.is_completed.is_(True))
            .all()
        )
        for progress in rows:
            mission = self.get_mission(progress.mission_id)
            if not mission or not mission.reward_id or not mission.is_active:
                continue
            reward = reward_service.get_reward(mission.reward_id)
            if not reward or not reward.is_active:
                continue
            if self._is_reward_delivered_for_progress(
                reward_service, progress.user_id, mission, progress
            ):
                continue
            user_ids.add(progress.user_id)
        return sorted(user_ids)

    def _is_pending_delivery_candidate(
        self, mission: Mission | None, reward_service: RewardService, reward_id: int
    ) -> bool:
        """True si misión/recompensa activas y elegibles para catch-up."""
        if not mission or not mission.reward_id or not mission.is_active:
            return False
        reward = reward_service.get_reward(reward_id)
        return reward is not None and reward.is_active

    async def deliver_pending_rewards(self, user_id: int, bot=None) -> int:
        """Reintenta entregas pendientes. Retorna cantidad recién entregada (no ya-entregadas)."""
        db = self._get_db()
        reward_service = RewardService(db)
        delivered = 0
        for progress in self.get_user_all_progress(user_id):
            if not progress.is_completed:
                continue
            mission = self.get_mission(progress.mission_id)
            if not self._is_pending_delivery_candidate(
                mission, reward_service, mission.reward_id if mission else None
            ):
                continue
            if self._is_reward_delivered_for_progress(
                reward_service, user_id, mission, progress
            ):
                continue
            result = await self._deliver_mission_reward_if_allowed(
                db,
                user_id,
                mission,
                None,
                progress,
                bot=bot,
                skip_cooldown=True,
            )
            if result == MissionDeliveryResult.NEWLY_DELIVERED:
                delivered += 1
        return delivered

    async def deliver_pending_rewards_for_mission(
        self, user_id: int, mission_id: int, bot=None
    ) -> bool:
        """Catch-up de una misión completada sin entrega (API interna; ver CLAUDE.md)."""
        db = self._get_db()
        progress = self.get_user_progress(user_id, mission_id)
        mission = self.get_mission(mission_id)
        if not progress or not mission or not progress.is_completed:
            return False
        result = await self._deliver_mission_reward_if_allowed(
            db,
            user_id,
            mission,
            None,
            progress,
            bot=bot,
            skip_cooldown=True,
        )
        return result == MissionDeliveryResult.NEWLY_DELIVERED

    def is_mission_reward_delivered(self, user_id: int, mission_id: int) -> bool:
        """Estado de entrega del ciclo actual para UI."""
        mission = self.get_mission(mission_id)
        progress = self.get_user_progress(user_id, mission_id)
        if not mission:
            return False
        return self._is_reward_delivered_for_progress(
            RewardService(self._get_db()), user_id, mission, progress
        )

    def set_progress(self, user_id: int, mission_id: int, value: int) -> UserMissionProgress | None:
        """Establece progreso; preserva completed_at si ya completada (idempotencia RECURRING)."""
        db = self._get_db()
        mission = self.get_mission(mission_id)
        if not mission:
            return None

        progress = self.get_or_create_progress(user_id, mission_id)
        progress.current_value = value

        if progress.current_value >= mission.target_value:
            if not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = datetime.now(UTC)
        else:
            progress.is_completed = False
            progress.completed_at = None

        db.commit()
        return progress

    # ==================== ACTUALIZACION Y ELIMINACION ====================

    def update_mission(self, mission_id: int, **kwargs) -> bool:
        """Actualiza una mision"""
        db = self._get_db()
        mission = self.get_mission(mission_id)
        if not mission:
            return False

        allowed_fields = [
            "name",
            "description",
            "target_value",
            "reward_id",
            "frequency",
            "start_date",
            "end_date",
            "is_active",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(mission, field):
                setattr(mission, field, value)

        db.commit()
        logger.info(f"Mision {mission_id} actualizada")
        return True

    def delete_mission(self, mission_id: int) -> bool:
        """Elimina una misión de la base de datos (soft delete)"""
        mission = self.get_mission(mission_id)
        if not mission:
            logger.warning(f"Misión {mission_id} no encontrada para eliminar")
            return False

        db = self._get_db()
        mission.is_active = False
        db.commit()
        logger.info(f"Misión {mission_id} desactivada (soft delete)")
        return True

    # ==================== ESTADISTICAS ====================

    def get_mission_stats(self, mission_id: int) -> dict:
        """Obtiene estadisticas de una mision"""
        db = self._get_db()
        mission = self.get_mission(mission_id)
        if not mission:
            return {}

        progress_list = (
            db.query(UserMissionProgress).filter(UserMissionProgress.mission_id == mission_id).all()
        )

        total_users = len(progress_list)
        completed = sum(1 for p in progress_list if p.is_completed)
        in_progress = total_users - completed

        return {
            "mission_name": mission.name,
            "total_users": total_users,
            "completed": completed,
            "in_progress": in_progress,
            "completion_rate": round((completed / total_users * 100), 2) if total_users > 0 else 0,
        }


async def _run_mission_increment_on_session(
    mission_db: Session,
    user_id: int,
    mission_type: MissionType,
    *,
    amount: int,
    bot,
    reference_id: int | None,
) -> int:
    """Ejecuta increment_progress_and_deliver en la sesión indicada."""
    mission_service = MissionService(mission_db)
    try:
        completed = await mission_service.increment_progress_and_deliver(
            user_id,
            mission_type,
            amount=amount,
            bot=bot,
            reference_id=reference_id,
        )
        return len(completed)
    finally:
        mission_service.close()


async def run_mission_side_effects_isolated(
    user_id: int,
    mission_type: MissionType,
    *,
    amount: int = 1,
    bot=None,
    reference_id: int | None = None,
    db: Session | None = None,
    max_attempts: int = 2,
) -> int:
    """
    Procesa misiones con reintento (best-effort).
    Usa ``db`` del caller si se provee; si falla, reintenta con sesión aislada.
    """
    sessions: list[tuple[Session, bool]] = []
    if db is not None:
        sessions.append((db, False))
    isolated_attempts = max_attempts if db is None else max(1, max_attempts - 1)
    for _ in range(isolated_attempts):
        sessions.append((SessionLocal(), True))

    completed_count = 0
    for attempt, (mission_db, owns) in enumerate(sessions[:max_attempts], start=1):
        try:
            completed_count = await _run_mission_increment_on_session(
                mission_db,
                user_id,
                mission_type,
                amount=amount,
                bot=bot,
                reference_id=reference_id,
            )
            logger.info(
                f"mission_service | run_mission_side_effects | user_id={user_id} | "
                f"type={mission_type.value} | completed={completed_count} | attempt={attempt}"
            )
            break
        except Exception as exc:
            mission_db.rollback()
            logger.warning(
                f"mission_service | run_mission_side_effects_failed | user_id={user_id} | "
                f"type={mission_type.value} | attempt={attempt} | error={exc}"
            )
        finally:
            if owns:
                mission_db.close()
    return completed_count


async def run_daily_gift_mission_side_effects(user_id: int, bot=None) -> int:
    """Best-effort: misiones de regalo diario en sesión aislada."""
    mission_db = SessionLocal()
    mission_service = MissionService(mission_db)
    try:
        return await mission_service.apply_daily_gift_mission_updates(user_id, bot=bot)
    except Exception as exc:
        mission_db.rollback()
        logger.warning(
            f"mission_service | daily_gift_missions_failed | user_id={user_id} | error={exc}"
        )
        return 0
    finally:
        mission_service.close()
        mission_db.close()


async def run_vip_mission_side_effects(
    user_id: int, bot=None, db: Session | None = None
) -> int:
    """Best-effort: misiones VIP_ACTIVE con entrega automática."""
    owns_db = db is None
    mission_db = db or SessionLocal()
    mission_service = MissionService(mission_db)
    try:
        return await mission_service.apply_vip_active_mission_updates(user_id, bot=bot)
    except Exception as exc:
        mission_db.rollback()
        logger.warning(
            f"mission_service | vip_missions_failed | user_id={user_id} | error={exc}"
        )
        return 0
    finally:
        mission_service.close()
        if owns_db:
            mission_db.close()
