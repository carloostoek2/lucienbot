"""
Servicio de Minijuegos - Lucien Bot

Gestiona los minijuegos de dados y trivia con límites diarios.
"""

import json
import logging
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import GameRecord, TransactionSource
from services.besito_service import BesitoService
from services.user_service import UserService
from services.vip_service import VIPService

logger = logging.getLogger(__name__)


class GameService:
    """Servicio para minijuegos de dados y trivia"""

    # Constantes de límites diarios
    DAILY_DICE_LIMIT_FREE = 10
    DAILY_DICE_LIMIT_VIP = 20
    DAILY_TRIVIA_LIMIT_FREE = 5
    DAILY_TRIVIA_LIMIT_VIP = 10

    # Recompensas por victoria
    DICE_WIN_BESITOS = 1
    TRIVIA_WIN_BESITOS = 1
    TRIVIA_VIP_WIN_BESITOS = 2

    # Límites trivia VIP
    DAILY_TRIVIA_VIP_LIMIT = 5

    # Limites trivia simple (Phase 16)
    DAILY_TRIVIA_SIMPLE_LIMIT_FREE = 5
    DAILY_TRIVIA_SIMPLE_LIMIT_VIP = 10

    # Recompensas trivia simple (estandarizadas al mismo esquema 1/2)
    TRIVIA_SIMPLE_WIN_BESITOS = 1
    TRIVIA_SIMPLE_VIP_WIN_BESITOS = 2

    # Hitos de racha (D-09): {streak: bonus_base}
    STREAK_MILESTONES = {3: 2, 5: 5, 7: 10, 10: 20}

    # Límites de besitos ganados en trivia (earning caps, distintos de límites de jugadas)
    TRIVIA_BESITOS_DAILY_FREE = 10
    TRIVIA_BESITOS_DAILY_VIP = 15
    TRIVIA_BESITOS_WEEKLY_FREE = 30
    TRIVIA_BESITOS_WEEKLY_VIP = 40

    # ==================== TEMPLATES DE COPY ====================

    MENU_TEMPLATES = {
        "title": [
            "🎮 Minijuegos",
        ],
        "subtitle": [
            "Juegue y gane besitos. Límite diario por juego.",
        ],
        "dice_description": [
            "🎲 Dados: gane 1 besito con pares o dobles.",
        ],
        "trivia_description": [
            "❓ Trivia: responda correctamente y gane besitos.",
        ],
        "trivia_vip_description": [
            "🎩 Trivia VIP: más besitos por respuesta correcta.",
        ],
        "footer": [
            "Oportunidades restantes hoy:",
        ],
    }

    DICE_TEMPLATES = {
        "entry_title": [
            "🎲 Dados",
        ],
        "entry_intro": [
            "Lance dos dados. Gane besitos si obtiene pares o dobles.",
        ],
        "rules": [
            "• Ambos dados pares: +1 besito\n• Dados iguales (dobles): +1 besito",
        ],
        "win_doubles": [
            "¡Dobles! +1 besito.",
        ],
        "win_pairs": [
            "¡Pares! +1 besito.",
        ],
        "near_miss_consecutive": [
            "{dice1} y {dice2}. Casi, pero no ganó.",
        ],
        "near_miss_seven": [
            "Suma 7. No ganó esta vez.",
        ],
        "loss": [
            "{dice1} y {dice2}. No ganó.",
        ],
        "limit_reached": [
            "Usó todos los intentos de dados de hoy. Vuelva mañana.",
        ],
    }

    TRIVIA_TEMPLATES = {
        "entry_title": [
            "❓ Trivia",
        ],
        "entry_intro": [
            "Responda correctamente para ganar 1 besito.",
        ],
        "counter": [
            "Intentos restantes: {remaining} de {limit}",
        ],
        "correct": [
            "🎩 <b>Lucien:</b>\n¡Correcto! +1 besito.",
        ],
        "incorrect": [
            "🎩 <b>Lucien:</b>\nIncorrecto.\nLa respuesta era: <b>{correct_answer}</b>",
        ],
        "streak_messages": {
            2: ["Racha: 2"],
            3: ["Racha: 3"],
            5: ["Racha: 5"],
            7: ["Racha: 7"],
            10: ["Racha: 10"],
        },
        "limit_reached": [
            "Usó todos los intentos de trivia de hoy. Vuelva mañana.",
        ],
        "cap_warning": [
            "⚠️ Puede ganar {remaining} besitos más en trivia hoy.",
        ],
        "cap_exhausted": [
            "⏸️ Alcanzó el tope de besitos de trivia por hoy. Puede seguir jugando, las recompensas se renuevan mañana.",
        ],
    }

    TRIVIA_VIP_TEMPLATES = {
        "entry_title": [
            "🎩 Trivia VIP",
        ],
        "entry_intro": [
            "Responda correctamente. +2 besitos por acierto.",
        ],
        "counter": [
            "Intentos VIP restantes: {remaining} de {limit}",
        ],
        "correct": [
            "🎩 <b>Lucien:</b>\n¡Correcto! +2 besitos.",
        ],
        "incorrect": [
            "🎩 <b>Lucien:</b>\nIncorrecto.\nLa respuesta era: <b>{correct_answer}</b>",
        ],
        "streak_messages": {
            2: ["Racha VIP: 2"],
            3: ["Racha VIP: 3"],
            5: ["Racha VIP: 5"],
            7: ["Racha VIP: 7"],
            10: ["Racha VIP: 10"],
        },
        "limit_reached": [
            "Usó todos los intentos VIP de trivia de hoy. Vuelva mañana.",
        ],
        "cap_warning": [
            "⚠️ Puede ganar {remaining} besitos VIP más en trivia hoy.",
        ],
        "cap_exhausted": [
            "⏸️ Tope de besitos VIP alcanzado por hoy. Puede seguir jugando; recompensas se renuevan mañana.",
        ],
    }

    TRIVIA_SIMPLE_TEMPLATES = {
        "entry_title": [
            "🎭 Trivia especial",
        ],
        "entry_intro": [
            "Preguntas de la categoría actual. Gane besitos por aciertos.",
        ],
        "counter": [
            "Intentos restantes: {remaining} de {limit}",
        ],
        "correct": [
            "🎩 <b>Lucien:</b>\n¡Correcto! +1 besito.",
        ],
        "incorrect": [
            "🎩 <b>Lucien:</b>\nIncorrecto.\nLa respuesta era: <b>{correct_answer}</b>",
        ],
        "streak_messages": {
            2: ["Racha: 2"],
            3: ["Racha: 3"],
            5: ["Racha: 5"],
            7: ["Racha: 7"],
            10: ["Racha: 10"],
        },
        "limit_reached": [
            "Usó todos los intentos de trivia especial de hoy. Vuelva mañana.",
        ],
        "deck_exhausted": [
            "Ya respondió todas las preguntas de esta categoría hoy. Vuelva mañana.",
        ],
        "cap_warning": [
            "⚠️ Puede ganar {remaining} besitos más en trivia especial hoy.",
        ],
        "cap_exhausted": [
            "⏸️ Tope de besitos de trivia especial alcanzado por hoy. Puede seguir jugando; recompensas mañana.",
        ],
    }

    def __init__(self, db: Session = None):
        self._owns_session = db is None
        self.db = db or SessionLocal()
        # Held direct BesitoService composition removed (Item 6 / remaining composers unification).
        # GAME/TRIVIA credits now use local on-demand BesitoService(db=self.db) *only*
        # inside play_dice_game / play_trivia_game / play_vip_trivia_game / play_simple_trivia_game
        # (preserves atomicity: credit's internal commit + GAME/TRIVIA record + streak/promo best-effort + return dict all unchanged;
        # best-effort schedule_emit still fires post-credit commit).
        # The has_sufficient local at _build_streak_failure_state (~953) remains (consistent style for non-credit check).
        # Other composers (broadcast/daily) handled in their phases; scope tight per Item 6.
        self._user_service = UserService(self.db)
        self._vip_service = VIPService(self.db)
        self._questions = None
        self._vip_questions = None
        self._simple_questions = {}  # {category_id: [questions]}

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None
        # Cerrar subs (inofensivo: ellos tienen owns=False cuando db compartido)
        for sub in (
            getattr(self, "besito_service", None),
            getattr(self, "_user_service", None),
            getattr(self, "_vip_service", None),
        ):
            if sub and hasattr(sub, "close"):
                sub.close()

    # ==================== TEMPLATE HELPERS ====================

    def _select_template(self, template_list: list) -> str:
        """Selecciona una variación aleatoria de template"""
        selected = random.choice(template_list)
        logger.debug(
            f"game_service - _select_template - selected from {len(template_list)} variations"
        )
        return selected

    def _is_near_miss(self, dice1: int, dice2: int) -> dict:
        """
        Detecta 'casi victorias' en dados.
        Returns: {is_near_miss, type, description}
        """
        # No es near miss si es victoria
        if dice1 == dice2 or (dice1 % 2 == 0 and dice2 % 2 == 0):
            return {"is_near_miss": False, "type": None, "description": None}

        # Dados consecutivos (3-4, 5-6, etc.)
        if abs(dice1 - dice2) == 1:
            template = self._select_template(self.DICE_TEMPLATES["near_miss_consecutive"])
            return {
                "is_near_miss": True,
                "type": "consecutive",
                "description": template.format(dice1=dice1, dice2=dice2),
            }

        # Suma 7
        if dice1 + dice2 == 7:
            template = self._select_template(self.DICE_TEMPLATES["near_miss_seven"])
            return {
                "is_near_miss": True,
                "type": "seven",
                "description": template.format(dice1=dice1, dice2=dice2),
            }

        return {"is_near_miss": False, "type": None, "description": None}

    def _get_today_trivia_records(self, user_id: int) -> list:
        """Obtiene registros de trivia de hoy ordenados por tiempo DESC"""
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        records = (
            self.db.query(GameRecord)
            .filter(
                GameRecord.user_id == user_id,
                GameRecord.game_type == "trivia",
                GameRecord.played_at >= today,
            )
            .order_by(GameRecord.played_at.desc())
            .all()
        )
        return records

    def _get_trivia_streak(self, user_id: int) -> int:
        """Calcula racha actual de victorias en trivia (solo hoy).
        Soporta payout==0 en respuestas correctas por tope de besitos (usa .correct si existe).
        """
        records = self._get_today_trivia_records(user_id)
        streak = 0
        for record in records:
            is_win = getattr(record, "correct", None)
            if is_win is True or (is_win is None and record.payout > 0):
                streak += 1
            else:
                break
        return streak

    def _get_streak_message(self, streak: int) -> str | None:
        """Obtiene mensaje de racha según nivel alcanzado"""
        if streak < 2:
            return None

        # Determinar nivel de racha
        if streak >= 10:
            level = 10
        elif streak >= 7:
            level = 7
        elif streak >= 5:
            level = 5
        elif streak >= 3:
            level = 3
        else:
            level = 2

        templates = self.TRIVIA_TEMPLATES["streak_messages"].get(level, ["¡Racha de {streak}!"])
        return self._select_template(templates).format(streak=streak)

    def _build_dice_message(self, parts: dict) -> str:
        """Construye mensaje final de dados desde partes"""
        lines = [parts["header"], "", parts["dice_display"], "", parts["result_text"]]
        if parts.get("reward_text"):
            lines.extend(["", parts["reward_text"]])
        if parts.get("encouragement"):
            lines.extend(["", parts["encouragement"]])
        return "\n".join(lines)

    def _build_trivia_message(self, parts: dict) -> str:
        """Construye mensaje final de trivia desde partes"""
        lines = [parts["header"]]
        if parts.get("reward_text"):
            lines.extend(["", parts["reward_text"]])
        if parts.get("streak_text"):
            lines.extend(["", parts["streak_text"]])
        if parts.get("promo_code_line"):
            lines.extend(["", parts["promo_code_line"]])
        if parts.get("cap_message"):
            lines.extend(["", parts["cap_message"]])
        if parts.get("encouragement"):
            lines.extend(["", parts["encouragement"]])
        return "\n".join(lines)

    def _build_cap_message(self, remaining_before: int, remaining_after: int, templates: dict) -> str | None:
        """Construye mensaje de aviso de limite de besitos (caps)."""
        if remaining_before <= 0:
            return self._select_template(templates["cap_exhausted"])
        if remaining_after <= 0:
            return self._select_template(templates["cap_exhausted"])
        if 0 < remaining_after <= 3:
            return self._select_template(templates["cap_warning"]).format(remaining=remaining_after)
        return None

    # ==================== VIP DETECTION ====================

    def is_user_vip(self, user_id: int) -> bool:
        """Verifica si usuario es VIP"""
        return self._vip_service.is_user_vip(user_id)

    def get_daily_limits(self, user_id: int) -> dict:
        """Obtiene límites diarios según tipo de usuario y configuración en BD"""
        is_vip = self.is_user_vip(user_id)
        try:
            from services.trivia_config_service import TriviaConfigService

            config_svc = TriviaConfigService(self.db)
            config = config_svc.get_config()
        except Exception:
            config = {}

        return {
            "dice_limit": config.get(
                "dice_limit_vip" if is_vip else "dice_limit_free",
                self.DAILY_DICE_LIMIT_VIP if is_vip else self.DAILY_DICE_LIMIT_FREE,
            ),
            "trivia_limit": config.get(
                "trivia_limit_vip" if is_vip else "trivia_limit_free",
                self.DAILY_TRIVIA_LIMIT_VIP if is_vip else self.DAILY_TRIVIA_LIMIT_FREE,
            ),
            "trivia_vip_limit": config.get("trivia_vip_limit", self.DAILY_TRIVIA_VIP_LIMIT),
            "trivia_simple_limit": config.get(
                "trivia_simple_limit_vip" if is_vip else "trivia_simple_limit_free",
                self.DAILY_TRIVIA_SIMPLE_LIMIT_VIP
                if is_vip
                else self.DAILY_TRIVIA_SIMPLE_LIMIT_FREE,
            ),
        }

    def get_menu_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para el menú de juegos"""
        limits = self.get_daily_limits(user_id)
        dice_played = self.get_today_play_count(user_id, "dice")
        trivia_played = self.get_today_play_count(user_id, "trivia")

        remaining_dice = max(0, limits["dice_limit"] - dice_played)
        remaining_trivia = max(0, limits["trivia_limit"] - trivia_played)

        logger.info(
            f"game_service - get_menu_data - {user_id} - dice:{remaining_dice}/{limits['dice_limit']}, trivia:{remaining_trivia}/{limits['trivia_limit']}"
        )

        return {
            "title": self._select_template(self.MENU_TEMPLATES["title"]),
            "subtitle": self._select_template(self.MENU_TEMPLATES["subtitle"]),
            "dice_description": self._select_template(self.MENU_TEMPLATES["dice_description"]),
            "trivia_description": self._select_template(self.MENU_TEMPLATES["trivia_description"]),
            "footer": self._select_template(self.MENU_TEMPLATES["footer"]),
            "remaining_dice": remaining_dice,
            "remaining_trivia": remaining_trivia,
            "limit_dice": limits["dice_limit"],
            "limit_trivia": limits["trivia_limit"],
            "is_vip": self.is_user_vip(user_id),
        }

    # ==================== CONTEO DIARIO ====================

    def get_today_play_count(self, user_id: int, game_type: str) -> int:
        """Obtiene jugadas de hoy para un tipo de juego"""
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(GameRecord)
            .filter(
                GameRecord.user_id == user_id,
                GameRecord.game_type == game_type,
                GameRecord.played_at >= today,
            )
            .count()
        )

    def can_play(self, user_id: int, game_type: str) -> tuple[bool, int, int, str]:
        """
        Verifica si usuario puede jugar según límites diarios.
        Returns: (puede_jugar, jugadas_hoy, limite, mensaje)
        """
        limits = self.get_daily_limits(user_id)
        if game_type == "dice":
            limit = limits["dice_limit"]
        elif game_type == "trivia_simple":
            limit = limits["trivia_simple_limit"]
        else:
            limit = limits["trivia_limit"]
        played = self.get_today_play_count(user_id, game_type)

        if played >= limit:
            is_vip = self.is_user_vip(user_id)
            if is_vip:
                return False, played, limit, "Ha alcanzado su límite diario de jugadas. Vuelva mañana."
            else:
                return (
                    False,
                    played,
                    limit,
                    (
                        "Ha alcanzado su límite diario de jugadas. Vuelva mañana.\n"
                        "Los miembros VIP tienen más jugadas diarias."
                    ),
                )
        return True, played, limit, None

    # ==================== BESITOS EARNING CAPS (TRIVIA) ====================

    TRIVIA_GAME_TYPES = ("trivia", "trivia_vip", "trivia_simple")

    def _get_trivia_besitos_earned_since(self, user_id: int, since: datetime) -> int:
        """Suma payout de todos los tipos de trivia desde 'since' (usado para caps)."""
        total = (
            self.db.query(func.sum(GameRecord.payout))
            .filter(
                GameRecord.user_id == user_id,
                GameRecord.game_type.in_(self.TRIVIA_GAME_TYPES),
                GameRecord.played_at >= since,
            )
            .scalar()
        )
        return int(total or 0)

    def get_trivia_besitos_earned_today(self, user_id: int) -> int:
        """Besitos totales ganados hoy en cualquier variante de trivia."""
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return self._get_trivia_besitos_earned_since(user_id, today)

    def get_trivia_besitos_earned_week(self, user_id: int) -> int:
        """Besitos totales ganados en ventana rolling de 7 días (semanal)."""
        week_ago = datetime.now(UTC) - timedelta(days=7)
        return self._get_trivia_besitos_earned_since(user_id, week_ago)

    def get_trivia_besitos_limits(self, user_id: int) -> dict:
        """Devuelve caps + earned + remaining para daily y weekly según VIP."""
        is_vip = self.is_user_vip(user_id)
        try:
            from services.trivia_config_service import TriviaConfigService

            config_svc = TriviaConfigService(self.db)
            config = config_svc.get_config()
        except Exception:
            config = {}

        if is_vip:
            daily_cap = config.get("trivia_besitos_daily_vip", self.TRIVIA_BESITOS_DAILY_VIP)
            weekly_cap = config.get("trivia_besitos_weekly_vip", self.TRIVIA_BESITOS_WEEKLY_VIP)
        else:
            daily_cap = config.get("trivia_besitos_daily_free", self.TRIVIA_BESITOS_DAILY_FREE)
            weekly_cap = config.get("trivia_besitos_weekly_free", self.TRIVIA_BESITOS_WEEKLY_FREE)

        earned_daily = self.get_trivia_besitos_earned_today(user_id)
        earned_weekly = self.get_trivia_besitos_earned_week(user_id)

        return {
            "daily_cap": daily_cap,
            "weekly_cap": weekly_cap,
            "earned_daily": earned_daily,
            "earned_weekly": earned_weekly,
            "remaining_daily": max(0, daily_cap - earned_daily),
            "remaining_weekly": max(0, weekly_cap - earned_weekly),
            "is_vip": is_vip,
        }

    def _apply_trivia_besitos_cap(
        self, user_id: int, desired_base: int, desired_bonus: int
    ) -> tuple[int, int]:
        """Aplica los caps daily+weekly y devuelve (awarded_base, awarded_bonus)."""
        limits = self.get_trivia_besitos_limits(user_id)
        total_desired = desired_base + desired_bonus
        allowed = min(
            total_desired,
            limits["remaining_daily"],
            limits["remaining_weekly"],
        )
        awarded_base = min(desired_base, allowed)
        awarded_bonus = min(desired_bonus, max(0, allowed - awarded_base))
        return awarded_base, awarded_bonus

    # ==================== DADOS ====================

    def get_dice_entry_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para la entrada del juego de dados"""
        limits = self.get_daily_limits(user_id)
        played = self.get_today_play_count(user_id, "dice")
        remaining = max(0, limits["dice_limit"] - played)

        logger.info(
            f"game_service - get_dice_entry_data - {user_id} - remaining:{remaining}/{limits['dice_limit']}"
        )

        return {
            "title": self._select_template(self.DICE_TEMPLATES["entry_title"]),
            "intro": self._select_template(self.DICE_TEMPLATES["entry_intro"]),
            "rules": self._select_template(self.DICE_TEMPLATES["rules"]),
            "remaining": remaining,
            "limit": limits["dice_limit"],
            "is_vip": self.is_user_vip(user_id),
        }

    def roll_dice(self) -> tuple[int, int]:
        """Lanza dos dados (1-6)"""
        return random.randint(1, 6), random.randint(1, 6)

    def check_dice_win(self, dice1: int, dice2: int) -> str:
        """
        Verifica victoria: pares (ambos pares) o dobles (iguales).
        Returns: 'pairs', 'doubles', o 'none'
        """
        if dice1 == dice2:
            return "doubles"
        if dice1 % 2 == 0 and dice2 % 2 == 0:
            return "pairs"
        return "none"

    def play_dice_game(self, user_id: int) -> dict[str, Any]:
        """
        Procesa una partida de dados con near-miss detection.
        Returns: {dice1, dice2, sum, won, win_type, is_near_miss, near_miss_type,
                 besitos, remaining_after, message_parts, limit_reached, message}
        """
        # 1. Verificar límites
        can_play, played, limit, limit_msg = self.can_play(user_id, "dice")
        if not can_play:
            limit_template = self._select_template(self.DICE_TEMPLATES["limit_reached"])
            return {
                "dice1": None,
                "dice2": None,
                "sum": 0,
                "won": False,
                "win_type": None,
                "is_near_miss": False,
                "near_miss_type": None,
                "besitos": 0,
                "remaining_after": 0,
                "message_parts": {},
                "limit_reached": True,
                "message": limit_template + "\n\n" + limit_msg,
            }

        # 2. Lanzar dados
        dice1, dice2 = self.roll_dice()
        dice_sum = dice1 + dice2

        # 3. Verificar victoria
        win_type = self.check_dice_win(dice1, dice2)
        won = win_type != "none"

        # 4. Verificar near-miss (solo si no ganó)
        near_miss = {"is_near_miss": False, "type": None, "description": None}
        if not won:
            near_miss = self._is_near_miss(dice1, dice2)

        # 5. Acreditar besitos si ganó
        besitos = 0
        if won:
            besitos = self.DICE_WIN_BESITOS
            besito_service = BesitoService(
                db=self.db
            )  # local on-demand inside credit site; shared db; credit internal commit + schedule_emit
            besito_service.credit_besitos(
                user_id=user_id,
                amount=besitos,
                source=TransactionSource.GAME,
                description=f"Victoria en dados: {win_type}",
            )

        # 6. Registrar jugada
        record = GameRecord(
            user_id=user_id, game_type="dice", result=f"{dice1}+{dice2}", payout=besitos, correct=False
        )
        self.db.add(record)
        self.db.commit()

        # 7. Calcular oportunidades restantes
        remaining_after = max(0, limit - (played + 1))

        # 8. Construir partes del mensaje
        message_parts = self._build_dice_message_parts(
            dice1, dice2, won, win_type, near_miss, besitos, remaining_after
        )

        # 9. Construir mensaje final
        message = self._build_dice_message(message_parts)

        logger.info(
            f"game_service - play_dice_game - {user_id} - dice:{dice1}+{dice2}, won:{won}, near_miss:{near_miss['is_near_miss']}"
        )

        return {
            "dice1": dice1,
            "dice2": dice2,
            "sum": dice_sum,
            "won": won,
            "win_type": win_type if won else None,
            "is_near_miss": near_miss["is_near_miss"],
            "near_miss_type": near_miss["type"],
            "besitos": besitos,
            "remaining_after": remaining_after,
            "message_parts": message_parts,
            "limit_reached": False,
            "message": message,
        }

    def _build_dice_message_parts(
        self,
        dice1: int,
        dice2: int,
        won: bool,
        win_type: str,
        near_miss: dict,
        besitos: int,
        remaining: int,
    ) -> dict:
        """Construye las partes del mensaje de dados"""
        # Header con resultado visual y tipo de victoria si aplica
        if won:
            if win_type == "doubles":
                header = f"<b>¡DOBLES!</b>\n\n🎲 {dice1}  |  {dice2} 🎲"
            else:
                header = f"<b>¡PARES!</b>\n\n🎲 {dice1}  |  {dice2} 🎲"
        else:
            header = f"🎲 {dice1}  |  {dice2} 🎲"

        # Sin display de suma (eliminado)
        dice_display = ""

        # Texto de resultado según tipo (sin mostrar suma)
        if won:
            result_text = self._select_template(
                self.DICE_TEMPLATES["win_doubles"]
                if win_type == "doubles"
                else self.DICE_TEMPLATES["win_pairs"]
            )
        elif near_miss["is_near_miss"]:
            result_text = near_miss["description"]
        else:
            result_text = self._select_template(self.DICE_TEMPLATES["loss"]).format(
                dice1=dice1, dice2=dice2
            )

        # Texto de recompensa
        reward_text = None
        if won:
            reward_text = f"+{besitos} besito{'s' if besitos > 1 else ''} 💋"

        # Mensaje de ánimo/oportunidades restantes
        encouragement = None
        if remaining > 0:
            encouragement = f"Oportunidades restantes: {remaining}"
        else:
            encouragement = "No le quedan jugadas de dados por hoy. Vuelva mañana."

        return {
            "header": header,
            "dice_display": dice_display,
            "result_text": result_text,
            "reward_text": reward_text,
            "encouragement": encouragement,
        }

    # ==================== TRIVIA ====================

    def get_trivia_entry_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para la entrada de trivia"""
        limits = self.get_daily_limits(user_id)
        played = self.get_today_play_count(user_id, "trivia")
        remaining = max(0, limits["trivia_limit"] - played)
        streak = self._get_trivia_streak(user_id)

        can_play = remaining > 0
        limit_message = None
        if not can_play:
            limit_message = self._select_template(self.TRIVIA_TEMPLATES["limit_reached"])
            is_vip = self.is_user_vip(user_id)
            if not is_vip:
                limit_message += "\n\nLos miembros VIP tienen más preguntas diarias."

        logger.info(
            f"game_service - get_trivia_entry_data - {user_id} - remaining:{remaining}, streak:{streak}"
        )

        return {
            "title": self._select_template(self.TRIVIA_TEMPLATES["entry_title"]),
            "intro": self._select_template(self.TRIVIA_TEMPLATES["entry_intro"]),
            "counter_template": self._select_template(self.TRIVIA_TEMPLATES["counter"]),
            "remaining": remaining,
            "limit": limits["trivia_limit"],
            "current_streak": streak,
            "is_vip": self.is_user_vip(user_id),
            "can_play": can_play,
            "limit_message": limit_message,
        }

    def load_trivia_questions(self) -> list:
        """Carga preguntas de docs/preguntas.json"""
        if self._questions is not None:
            return self._questions

        questions_path = Path("docs/preguntas.json")
        if not questions_path.exists():
            logger.warning("Questions file not found: docs/preguntas.json")
            return []

        try:
            with open(questions_path, encoding="utf-8") as f:
                data = json.load(f)
                self._questions = data if isinstance(data, list) else data.get("questions", [])
        except Exception as e:
            logger.error(f"Error loading trivia questions: {e}")
            self._questions = []

        return self._questions

    def get_random_question(self) -> tuple[dict | None, int]:
        """Retorna pregunta aleatoria con índice"""
        questions = self.load_trivia_questions()
        if not questions:
            return None, -1

        idx = random.randint(0, len(questions) - 1)
        return questions[idx], idx

    def get_question_by_index(self, index: int) -> dict | None:
        """Retorna pregunta por índice"""
        questions = self.load_trivia_questions()
        if 0 <= index < len(questions):
            return questions[index]
        return None

    def check_trivia_answer(self, question: dict, answer_idx: int) -> bool:
        """Verifica si respuesta es correcta"""
        if not question:
            return False
        return question.get("answer") == answer_idx

    def play_trivia(self, user_id: int, question_idx: int, answer_idx: int) -> dict[str, Any]:
        """
        Procesa respuesta de trivia con sistema de rachas.
        Returns: {correct, besitos, previous_streak, new_streak, streak_message,
                 message, message_parts, remaining_after, limit_reached}
        """
        # 1. Verificar límites
        can_play, played, limit, limit_msg = self.can_play(user_id, "trivia")
        if not can_play:
            limit_template = self._select_template(self.TRIVIA_TEMPLATES["limit_reached"])
            full_message = limit_template + "\n\n" + limit_msg
            return {
                "correct": False,
                "besitos": 0,
                "previous_streak": 0,
                "new_streak": 0,
                "streak_message": None,
                "message": full_message,
                "message_parts": {},
                "remaining_after": 0,
                "limit_reached": True,
            }

        # 2. Obtener pregunta
        question = self.get_question_by_index(question_idx)
        if not question:
            return {
                "correct": False,
                "besitos": 0,
                "previous_streak": 0,
                "new_streak": 0,
                "streak_message": None,
                "message": "Pregunta no encontrada.",
                "message_parts": {},
                "remaining_after": max(0, limit - played),
                "limit_reached": False,
            }

        # 3. Obtener racha previa
        previous_streak = self._get_trivia_streak(user_id)

        # 4. Verificar respuesta
        is_correct = self.check_trivia_answer(question, answer_idx)

        # 5. Calcular nueva racha
        new_streak = previous_streak + 1 if is_correct else 0

        # 6. Obtener mensaje de racha si aplica
        streak_message = None
        if is_correct:
            streak_message = self._get_streak_message(new_streak)

        # 7. Calcular recompensa deseada + aplicar caps de besitos ganados
        besitos = 0
        streak_bonus = 0
        cap_message = None
        if is_correct:
            cap_limits = self.get_trivia_besitos_limits(user_id)
            cap_remaining_before = min(
                cap_limits["remaining_daily"], cap_limits["remaining_weekly"]
            )

            desired_base = self.TRIVIA_WIN_BESITOS
            desired_bonus = 0
            if new_streak in self.STREAK_MILESTONES:
                bonus = self.STREAK_MILESTONES[new_streak]
                desired_bonus = bonus * 2 if self.is_user_vip(user_id) else bonus

            awarded_base, awarded_bonus = self._apply_trivia_besitos_cap(
                user_id, desired_base, desired_bonus
            )
            besitos = awarded_base
            streak_bonus = awarded_bonus

            besito_service = BesitoService(
                db=self.db
            )  # local on-demand inside credit site; shared db; credit internal commit + schedule_emit
            if besitos > 0:
                besito_service.credit_besitos(
                    user_id=user_id,
                    amount=besitos,
                    source=TransactionSource.TRIVIA,
                    description=f"Victoria en trivia (racha: {new_streak})",
                )
            if streak_bonus > 0:
                besito_service.credit_besitos(
                    user_id=user_id,
                    amount=streak_bonus,
                    source=TransactionSource.TRIVIA,
                    description=f"Bonus por racha de {new_streak} en trivia",
                )

            cap_remaining_after = max(0, cap_remaining_before - (besitos + streak_bonus))
            cap_message = self._build_cap_message(
                cap_remaining_before, cap_remaining_after, self.TRIVIA_TEMPLATES
            )

        # 8. Registrar jugada (BEFORE claim_for_streak — its commit commits this too)
        record = GameRecord(
            user_id=user_id,
            game_type="trivia",
            result=f"question_{question_idx}",
            payout=besitos + streak_bonus,
            correct=is_correct,
        )
        self.db.add(record)

        # Phase 17: Streak Promotion check
        promo_code_info = None
        if is_correct:
            from services.streak_promotion_service import StreakPromotionService

            promo_service = StreakPromotionService(self.db)
            try:
                promo_code_info = promo_service.claim_for_streak(
                    user_id=user_id,
                    game_type="trivia",
                    streak=new_streak,
                    category_id=None,
                )
            finally:
                promo_service.close()

        # 9. Calcular oportunidades restantes
        remaining_after = max(0, limit - (played + 1))

        # 10. Construir partes del mensaje
        message_parts = self._build_trivia_message_parts(
            is_correct,
            question,
            besitos,
            streak_message,
            remaining_after,
            promo_code=promo_code_info,
            cap_message=cap_message,
        )

        # 11. Construir mensaje final
        message = self._build_trivia_message(message_parts)

        # Phase 18: Build session_state for handler decisions
        session_state = None
        if not is_correct:
            session_state = self._build_streak_failure_state(user_id, previous_streak)
        elif promo_code_info:
            session_state = self._build_streak_claim_state(user_id, promo_code_info)

        logger.info(
            f"game_service - play_trivia - {user_id} - correct:{is_correct}, streak:{new_streak}, bonus:{streak_bonus}"
        )

        # Commit del registro de jugadapara asegurar persistencia
        self.db.commit()

        return {
            "correct": is_correct,
            "besitos": besitos,
            "besitos_total": besitos + streak_bonus,
            "previous_streak": previous_streak,
            "new_streak": new_streak,
            "streak_message": streak_message,
            "streak_bonus": streak_bonus,
            "promo_code": promo_code_info,
            "message": message,
            "message_parts": message_parts,
            "remaining_after": remaining_after,
            "limit_reached": False,
            "session_state": session_state,
        }

    def _build_streak_failure_state(self, user_id: int, streak: int) -> dict | None:
        """Construye session_state cuando el usuario falla una pregunta con sesion activa."""
        from services.streak_promotion_service import StreakPromotionService

        promo_service = StreakPromotionService(self.db)
        try:
            session = promo_service.get_active_session(user_id)
            if not session:
                return None
            if session.protection_used:
                # Already used protection -> cancel all codes, close session
                cancelled = promo_service.cancel_session_codes(session.id)
                promo_service.close_session(user_id, retire=False)
                return {"action": "cancelled", "streak_reset_to": 0, "codes_cancelled": cancelled}
            # Protection available -> check if user can afford
            cost = promo_service.calculate_protection_cost(streak)
            besito_service = BesitoService(self.db)
            can_afford = besito_service.has_sufficient_balance(user_id, cost)
            if can_afford:
                return {
                    "action": "offer_protection",
                    "protection_cost": cost,
                    "streak": streak,
                }
            else:
                # Set timeout
                session.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=2)
                self.db.flush()
                return {
                    "action": "timeout",
                    "expires_at": session.expires_at.isoformat(),
                    "streak": streak,
                }
        finally:
            promo_service.close()

    def _build_streak_claim_state(self, user_id: int, promo_code_info: dict) -> dict | None:
        """Construye session_state cuando el usuario alcanza un tier y reclama codigo."""
        from services.streak_promotion_service import StreakPromotionService

        promo_service = StreakPromotionService(self.db)
        try:
            session = promo_service.get_active_session(user_id)
            if not session:
                return None
            if session.is_in_risk_mode:
                return {"action": "claimed_in_risk", "code": promo_code_info}
            return {
                "action": "offer_retire",
                "code": promo_code_info,
                "session_id": session.id,
            }
        finally:
            promo_service.close()

    def _build_trivia_message_parts(
        self,
        is_correct: bool,
        question: dict,
        besitos: int,
        streak_message: str | None,
        remaining: int,
        promo_code: dict | None = None,
        cap_message: str | None = None,
    ) -> dict:
        """Construye las partes del mensaje de trivia"""
        # Respuesta correcta (para formatear templates)
        letters = ["A", "B", "C", "D"]
        answer_idx = min(question["answer"], len(letters) - 1)
        correct_letter = letters[answer_idx]
        correct_answer_text = f"{correct_letter}) {question['opts'][question['answer']]}"

        # Header según resultado
        if is_correct:
            header = self._select_template(self.TRIVIA_TEMPLATES["correct"])
        else:
            header_template = self._select_template(self.TRIVIA_TEMPLATES["incorrect"])
            header = header_template.format(correct_answer=correct_answer_text)

        # Resultado de la respuesta - simplificado
        result_text = None

        # Respuesta correcta (solo se muestra si se equivocó - ahora ya está en el header)
        correct_answer = None

        # Recompensa
        reward_text = None
        if is_correct and besitos > 0:
            reward_text = f"+{besitos} besitos 💋"

        # Mensaje de racha
        streak_text = streak_message

        # Animo / oportunidades
        encouragement = None
        if remaining > 0:
            encouragement = f"Oportunidades restantes: {remaining}"
        else:
            encouragement = "No le quedan preguntas de trivia por hoy. Vuelva mañana."

        # Phase 17: Promo code line
        promo_code_line = None
        if promo_code and promo_code.get("code"):
            code = promo_code["code"]
            promo_code_line = (
                f"\U0001f39f️ <b>¡Código de descuento ganado!</b>\n"
                f"<i>Su racha le ha otorgado: <code>{code}</code></i>\n"
                f"<i>Lucien guarda registro de este código en su archivo personal.</i>"
            )

        return {
            "header": header,
            "result_text": result_text,
            "correct_answer": correct_answer,
            "reward_text": reward_text,
            "streak_text": streak_text,
            "encouragement": encouragement,
            "promo_code_line": promo_code_line,
            "cap_message": cap_message,
        }

    # ==================== TRIVIA VIP ====================

    def _get_today_vip_trivia_records(self, user_id: int) -> list:
        """Obtiene registros de trivia VIP de hoy ordenados por tiempo DESC"""
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        records = (
            self.db.query(GameRecord)
            .filter(
                GameRecord.user_id == user_id,
                GameRecord.game_type == "trivia_vip",
                GameRecord.played_at >= today,
            )
            .order_by(GameRecord.played_at.desc())
            .all()
        )
        return records

    def _get_vip_trivia_streak(self, user_id: int) -> int:
        """Calcula racha actual de victorias en trivia VIP (solo hoy).
        Soporta payout==0 en respuestas correctas por tope de besitos (usa .correct si existe).
        """
        records = self._get_today_vip_trivia_records(user_id)
        streak = 0
        for record in records:
            is_win = getattr(record, "correct", None)
            if is_win is True or (is_win is None and record.payout > 0):
                streak += 1
            else:
                break
        return streak

    def can_play_vip_trivia(self, user_id: int) -> tuple[bool, int, int, str]:
        """
        Verifica si usuario VIP puede jugar trivia VIP.
        Returns: (puede_jugar, jugadas_hoy, limite, mensaje)
        """
        if not self.is_user_vip(user_id):
            return (
                False,
                0,
                self.DAILY_TRIVIA_VIP_LIMIT,
                "Esta trivia es exclusiva para miembros VIP.",
            )

        played = len(self._get_today_vip_trivia_records(user_id))
        limit = self.DAILY_TRIVIA_VIP_LIMIT

        if played >= limit:
            return (
                False,
                played,
                limit,
                self._select_template(self.TRIVIA_VIP_TEMPLATES["limit_reached"]),
            )

        return True, played, limit, None

    def load_trivia_vip_questions(self) -> list:
        """Carga preguntas VIP de docs/preguntas_vip.json"""
        if self._vip_questions is not None:
            return self._vip_questions

        questions_path = Path("docs/preguntas_vip.json")
        if not questions_path.exists():
            logger.warning("VIP Questions file not found: docs/preguntas_vip.json")
            return []

        try:
            with open(questions_path, encoding="utf-8") as f:
                data = json.load(f)
                self._vip_questions = data if isinstance(data, list) else data.get("questions", [])
        except Exception as e:
            logger.error(f"Error loading VIP trivia questions: {e}")
            self._vip_questions = []

        return self._vip_questions

    def get_random_vip_question(self) -> tuple[dict | None, int]:
        """Retorna pregunta VIP aleatoria con índice"""
        questions = self.load_trivia_vip_questions()
        if not questions:
            return None, -1

        idx = random.randint(0, len(questions) - 1)
        return questions[idx], idx

    def get_vip_question_by_index(self, index: int) -> dict | None:
        """Retorna pregunta VIP por índice"""
        questions = self.load_trivia_vip_questions()
        if 0 <= index < len(questions):
            return questions[index]
        return None

    def check_trivia_vip_answer(self, question: dict, answer_idx: int) -> bool:
        """Verifica si respuesta VIP es correcta"""
        if not question:
            return False
        return question.get("answer") == answer_idx

    def get_trivia_vip_entry_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para la entrada de trivia VIP"""
        limits = self.get_daily_limits(user_id)
        played = len(self._get_today_vip_trivia_records(user_id))
        remaining = max(0, limits["trivia_vip_limit"] - played)
        streak = self._get_vip_trivia_streak(user_id)

        can_play = remaining > 0
        is_vip = self.is_user_vip(user_id)
        limit_message = None

        if not is_vip:
            limit_message = "Esta trivia es exclusiva para miembros VIP."
            can_play = False
        elif not can_play:
            limit_message = self._select_template(self.TRIVIA_VIP_TEMPLATES["limit_reached"])

        logger.info(
            f"game_service - get_trivia_vip_entry_data - {user_id} - remaining:{remaining}, streak:{streak}, is_vip:{is_vip}"
        )

        return {
            "title": self._select_template(self.TRIVIA_VIP_TEMPLATES["entry_title"]),
            "intro": self._select_template(self.TRIVIA_VIP_TEMPLATES["entry_intro"]),
            "counter_template": self._select_template(self.TRIVIA_VIP_TEMPLATES["counter"]),
            "remaining": remaining,
            "limit": limits["trivia_vip_limit"],
            "current_streak": streak,
            "is_vip": is_vip,
            "can_play": can_play,
            "limit_message": limit_message,
        }

    def play_trivia_vip(self, user_id: int, question_idx: int, answer_idx: int) -> dict[str, Any]:
        """
        Procesa respuesta de trivia VIP con sistema de rachas y recompensa VIP.
        Returns: {correct, besitos, previous_streak, new_streak, streak_message,
                 message, message_parts, remaining_after, limit_reached}
        """
        # 1. Verificar si es VIP y límites
        can_play, played, limit, limit_msg = self.can_play_vip_trivia(user_id)
        if not can_play:
            return {
                "correct": False,
                "besitos": 0,
                "previous_streak": 0,
                "new_streak": 0,
                "streak_message": None,
                "message": limit_msg,
                "message_parts": {},
                "remaining_after": 0,
                "limit_reached": True,
            }

        # 2. Obtener pregunta
        question = self.get_vip_question_by_index(question_idx)
        if not question:
            return {
                "correct": False,
                "besitos": 0,
                "previous_streak": 0,
                "new_streak": 0,
                "streak_message": None,
                "message": "Pregunta no encontrada.",
                "message_parts": {},
                "remaining_after": max(0, limit - played),
                "limit_reached": False,
            }

        # 3. Obtener racha previa
        previous_streak = self._get_vip_trivia_streak(user_id)

        # 4. Verificar respuesta
        is_correct = self.check_trivia_vip_answer(question, answer_idx)

        # 5. Calcular nueva racha
        new_streak = previous_streak + 1 if is_correct else 0

        # 6. Obtener mensaje de racha si aplica
        streak_message = None
        if is_correct:
            streak_message = self._get_streak_message(new_streak)

        # 7. Calcular recompensa deseada + aplicar caps de besitos ganados
        besitos = 0
        streak_bonus = 0
        cap_message = None
        if is_correct:
            cap_limits = self.get_trivia_besitos_limits(user_id)
            cap_remaining_before = min(
                cap_limits["remaining_daily"], cap_limits["remaining_weekly"]
            )

            desired_base = self.TRIVIA_VIP_WIN_BESITOS
            desired_bonus = 0
            if new_streak in self.STREAK_MILESTONES:
                bonus = self.STREAK_MILESTONES[new_streak]
                desired_bonus = bonus * 2 if self.is_user_vip(user_id) else bonus

            awarded_base, awarded_bonus = self._apply_trivia_besitos_cap(
                user_id, desired_base, desired_bonus
            )
            besitos = awarded_base
            streak_bonus = awarded_bonus

            besito_service = BesitoService(
                db=self.db
            )  # local on-demand inside credit site; shared db; credit internal commit + schedule_emit
            if besitos > 0:
                besito_service.credit_besitos(
                    user_id=user_id,
                    amount=besitos,
                    source=TransactionSource.TRIVIA,
                    description=f"Victoria en trivia VIP (racha: {new_streak})",
                )
            if streak_bonus > 0:
                besito_service.credit_besitos(
                    user_id=user_id,
                    amount=streak_bonus,
                    source=TransactionSource.TRIVIA,
                    description=f"Bonus por racha de {new_streak} en trivia VIP",
                )

            cap_remaining_after = max(0, cap_remaining_before - (besitos + streak_bonus))
            cap_message = self._build_cap_message(
                cap_remaining_before, cap_remaining_after, self.TRIVIA_VIP_TEMPLATES
            )

        # 8. Registrar jugada (BEFORE claim_for_streak — its commit commits this too)
        record = GameRecord(
            user_id=user_id,
            game_type="trivia_vip",
            result=f"vip_question_{question_idx}",
            payout=besitos + streak_bonus,
            correct=is_correct,
        )
        self.db.add(record)

        # Phase 17: Streak Promotion check
        promo_code_info = None
        if is_correct:
            from services.streak_promotion_service import StreakPromotionService

            promo_service = StreakPromotionService(self.db)
            try:
                promo_code_info = promo_service.claim_for_streak(
                    user_id=user_id,
                    game_type="trivia_vip",
                    streak=new_streak,
                    category_id=None,
                )
            finally:
                promo_service.close()

        # 9. Calcular oportunidades restantes
        remaining_after = max(0, limit - (played + 1))

        # 10. Construir partes del mensaje
        message_parts = self._build_trivia_vip_message_parts(
            is_correct,
            question,
            besitos,
            streak_message,
            remaining_after,
            promo_code=promo_code_info,
            cap_message=cap_message,
        )

        # 11. Construir mensaje final
        message = self._build_trivia_vip_message(message_parts)

        # Phase 18: Build session_state for handler decisions
        session_state = None
        if not is_correct:
            session_state = self._build_streak_failure_state(user_id, previous_streak)
        elif promo_code_info:
            session_state = self._build_streak_claim_state(user_id, promo_code_info)

        logger.info(
            f"game_service - play_trivia_vip - {user_id} - correct:{is_correct}, streak:{new_streak}, besitos:{besitos}, bonus:{streak_bonus}"
        )

        # Commit del registro de jugadapara asegurar persistencia
        self.db.commit()

        return {
            "correct": is_correct,
            "besitos": besitos,
            "besitos_total": besitos + streak_bonus,
            "previous_streak": previous_streak,
            "new_streak": new_streak,
            "streak_message": streak_message,
            "streak_bonus": streak_bonus,
            "promo_code": promo_code_info,
            "message": message,
            "message_parts": message_parts,
            "remaining_after": remaining_after,
            "limit_reached": False,
            "session_state": session_state,
        }

    def _build_trivia_vip_message_parts(
        self,
        is_correct: bool,
        question: dict,
        besitos: int,
        streak_message: str | None,
        remaining: int,
        promo_code: dict | None = None,
        cap_message: str | None = None,
    ) -> dict:
        """Construye las partes del mensaje de trivia VIP"""
        correct_letter = ["A", "B", "C", "D"][question["answer"]]
        correct_answer_text = f"{correct_letter}) {question['opts'][question['answer']]}"

        if is_correct:
            header = self._select_template(self.TRIVIA_VIP_TEMPLATES["correct"])
        else:
            header_template = self._select_template(self.TRIVIA_VIP_TEMPLATES["incorrect"])
            header = header_template.format(correct_answer=correct_answer_text)

        result_text = None
        correct_answer = None

        reward_text = None
        if is_correct and besitos > 0:
            reward_text = f"+{besitos} besitos 💋💋💋💋💋"

        streak_text = streak_message

        encouragement = None
        if remaining > 0:
            encouragement = f"Oportunidades VIP restantes: {remaining}"
        else:
            encouragement = "No le quedan preguntas VIP por hoy. Vuelva mañana."

        # Phase 17: Promo code line
        promo_code_line = None
        if promo_code and promo_code.get("code"):
            code = promo_code["code"]
            promo_code_line = (
                f"\U0001f39f️ <b>¡Código de descuento ganado!</b>\n"
                f"<i>Su racha le ha otorgado: <code>{code}</code></i>\n"
                f"<i>Lucien guarda registro de este código en su archivo personal.</i>"
            )

        return {
            "header": header,
            "result_text": result_text,
            "correct_answer": correct_answer,
            "reward_text": reward_text,
            "streak_text": streak_text,
            "encouragement": encouragement,
            "promo_code_line": promo_code_line,
            "cap_message": cap_message,
        }

    def _build_trivia_vip_message(self, parts: dict) -> str:
        """Construye mensaje final de trivia VIP"""
        lines = [parts["header"]]
        if parts.get("reward_text"):
            lines.extend(["", parts["reward_text"]])
        if parts.get("streak_text"):
            lines.extend(["", parts["streak_text"]])
        if parts.get("promo_code_line"):
            lines.extend(["", parts["promo_code_line"]])
        if parts.get("cap_message"):
            lines.extend(["", parts["cap_message"]])
        if parts.get("encouragement"):
            lines.extend(["", parts["encouragement"]])
        return "\n".join(lines)

    # ==================== TRIVIA ESPECIAL (PHASE 16) ====================

    def _get_today_simple_trivia_records(self, user_id: int) -> list:
        """Obtiene registros de trivia temática de hoy ordenados por tiempo DESC."""
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        records = (
            self.db.query(GameRecord)
            .filter(
                GameRecord.user_id == user_id,
                GameRecord.game_type == "trivia_simple",
                GameRecord.played_at >= today,
            )
            .order_by(GameRecord.played_at.desc())
            .all()
        )
        return records

    def _get_answered_today_indices(self, user_id: int, game_type: str) -> set:
        """Retorna set de indices de preguntas ya respondidas hoy para un game_type."""
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        records = (
            self.db.query(GameRecord)
            .filter(
                GameRecord.user_id == user_id,
                GameRecord.game_type == game_type,
                GameRecord.played_at >= today,
            )
            .all()
        )
        indices = set()
        for rec in records:
            result_str = rec.result or ""
            if result_str.startswith("simple_question_"):
                try:
                    idx = int(result_str.replace("simple_question_", ""))
                    indices.add(idx)
                except ValueError:
                    continue
        return indices

    def load_trivia_simple_questions(self, category_id: str) -> list:
        """Carga preguntas simples desde docs/preguntas_{category_id}.json."""
        if category_id in self._simple_questions:
            return self._simple_questions[category_id]

        questions_path = Path(f"docs/preguntas_{category_id}.json")
        if not questions_path.exists():
            logger.warning(f"trivia simple questions file not found: {questions_path}")
            return []

        try:
            with open(questions_path, encoding="utf-8") as f:
                data = json.load(f)
                questions = data if isinstance(data, list) else data.get("questions", [])
                self._simple_questions[category_id] = questions
        except Exception as e:
            logger.error(f"Error loading trivia simple questions: {e}")
            self._simple_questions[category_id] = []

        return self._simple_questions[category_id]

    def get_random_simple_question(self, user_id: int, category_id: str) -> tuple:
        """Retorna (question_dict, index) de pregunta simple no respondida hoy.
        Returns (None, -1) si no hay preguntas, (None, -2) si todas respondidas."""
        questions = self.load_trivia_simple_questions(category_id)
        if not questions:
            return None, -1

        answered = self._get_answered_today_indices(user_id, "trivia_simple")
        available = [i for i in range(len(questions)) if i not in answered]
        if not available:
            return None, -2

        idx = random.choice(available)
        return questions[idx], idx

    def _get_simple_trivia_streak(self, user_id: int) -> int:
        """Calcula racha actual de victorias en trivia simple (solo hoy).
        Soporta payout==0 en respuestas correctas por tope de besitos (usa .correct si existe).
        """
        records = self._get_today_simple_trivia_records(user_id)
        streak = 0
        for record in records:
            is_win = getattr(record, "correct", None)
            if is_win is True or (is_win is None and record.payout > 0):
                streak += 1
            else:
                break
        return streak

    def get_question_by_simple_index(self, index: int, category_id: str) -> dict | None:
        """Retorna pregunta simple por indice y categoria."""
        questions = self.load_trivia_simple_questions(category_id)
        if 0 <= index < len(questions):
            return questions[index]
        return None

    def _get_simple_streak_message(self, streak: int) -> str | None:
        """Obtiene mensaje de racha actual segun nivel alcanzado."""
        if streak < 2:
            return None
        if streak >= 10:
            level = 10
        elif streak >= 7:
            level = 7
        elif streak >= 5:
            level = 5
        elif streak >= 3:
            level = 3
        else:
            level = 2
        templates = self.TRIVIA_SIMPLE_TEMPLATES["streak_messages"].get(
            level, ["!Racha de {streak}!"]
        )
        return self._select_template(templates).format(streak=streak)

    def get_trivia_simple_entry_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para la entrada de trivia simple."""
        limits = self.get_daily_limits(user_id)
        played = len(self._get_today_simple_trivia_records(user_id))
        remaining = max(0, limits["trivia_simple_limit"] - played)
        streak = self._get_simple_trivia_streak(user_id)

        can_play = remaining > 0
        limit_message = None
        if not can_play:
            limit_message = self._select_template(self.TRIVIA_SIMPLE_TEMPLATES["limit_reached"])

        logger.info(
            f"game_service - get_trivia_simple_entry_data - {user_id} - remaining:{remaining}, streak:{streak}"
        )

        return {
            "title": self._select_template(self.TRIVIA_SIMPLE_TEMPLATES["entry_title"]),
            "intro": self._select_template(self.TRIVIA_SIMPLE_TEMPLATES["entry_intro"]),
            "counter_template": self._select_template(self.TRIVIA_SIMPLE_TEMPLATES["counter"]),
            "remaining": remaining,
            "limit": limits["trivia_simple_limit"],
            "current_streak": streak,
            "is_vip": self.is_user_vip(user_id),
            "can_play": can_play,
            "limit_message": limit_message,
        }

    def play_trivia_simple(
        self, user_id: int, question_idx: int, answer_idx: int, category_id: str
    ) -> dict[str, Any]:
        """
        Procesa respuesta de trivia simple con rachas y bonus.
        Returns: {correct, besitos, streak_bonus, message, ...}
        """
        can_play, played, limit, limit_msg = self.can_play(user_id, "trivia_simple")
        if not can_play:
            limit_template = self._select_template(self.TRIVIA_SIMPLE_TEMPLATES["limit_reached"])
            full_message = limit_template + "\n\n" + limit_msg
            return {
                "correct": False,
                "besitos": 0,
                "streak_bonus": 0,
                "previous_streak": 0,
                "new_streak": 0,
                "streak_message": None,
                "message": full_message,
                "message_parts": {},
                "remaining_after": 0,
                "limit_reached": True,
            }

        question = self.get_question_by_simple_index(question_idx, category_id)
        if not question:
            return {
                "correct": False,
                "besitos": 0,
                "streak_bonus": 0,
                "previous_streak": 0,
                "new_streak": 0,
                "streak_message": None,
                "message": "Pregunta simple no encontrada.",
                "message_parts": {},
                "remaining_after": max(0, limit - played),
                "limit_reached": False,
            }

        previous_streak = self._get_simple_trivia_streak(user_id)
        is_correct = self.check_trivia_answer(question, answer_idx)

        new_streak = previous_streak + 1 if is_correct else 0

        streak_message = None
        if is_correct:
            streak_message = self._get_simple_streak_message(new_streak)

        besitos = 0
        streak_bonus = 0
        cap_message = None
        if is_correct:
            cap_limits = self.get_trivia_besitos_limits(user_id)
            cap_remaining_before = min(
                cap_limits["remaining_daily"], cap_limits["remaining_weekly"]
            )

            desired_base = (
                self.TRIVIA_SIMPLE_VIP_WIN_BESITOS
                if self.is_user_vip(user_id)
                else self.TRIVIA_SIMPLE_WIN_BESITOS
            )
            desired_bonus = 0
            if new_streak in self.STREAK_MILESTONES:
                bonus = self.STREAK_MILESTONES[new_streak]
                desired_bonus = bonus * 2 if self.is_user_vip(user_id) else bonus

            awarded_base, awarded_bonus = self._apply_trivia_besitos_cap(
                user_id, desired_base, desired_bonus
            )
            besitos = awarded_base
            streak_bonus = awarded_bonus

            besito_service = BesitoService(
                db=self.db
            )  # local on-demand inside credit site; shared db; credit internal commit + schedule_emit
            if besitos > 0:
                besito_service.credit_besitos(
                    user_id=user_id,
                    amount=besitos,
                    source=TransactionSource.TRIVIA,
                    description=f"Victoria en trivia simple (racha: {new_streak})",
                )
            if streak_bonus > 0:
                besito_service.credit_besitos(
                    user_id=user_id,
                    amount=streak_bonus,
                    source=TransactionSource.TRIVIA,
                    description=f"Bonus por racha de {new_streak} en trivia simple",
                )

            cap_remaining_after = max(0, cap_remaining_before - (besitos + streak_bonus))
            cap_message = self._build_cap_message(
                cap_remaining_before, cap_remaining_after, self.TRIVIA_SIMPLE_TEMPLATES
            )

        # Registrar jugada (BEFORE claim_for_streak — its commit commits this too)
        record = GameRecord(
            user_id=user_id,
            game_type="trivia_simple",
            result=f"simple_question_{question_idx}",
            payout=besitos + streak_bonus,
            correct=is_correct,
        )
        self.db.add(record)

        # Phase 17: Streak Promotion check
        promo_code_info = None
        if is_correct:
            from services.streak_promotion_service import StreakPromotionService

            promo_service = StreakPromotionService(self.db)
            try:
                promo_code_info = promo_service.claim_for_streak(
                    user_id=user_id,
                    game_type="trivia_simple",
                    streak=new_streak,
                    category_id=category_id,
                )
            finally:
                promo_service.close()

        remaining_after = max(0, limit - (played + 1))

        message_parts = self._build_trivia_simple_message_parts(
            is_correct,
            question,
            besitos,
            streak_message,
            streak_bonus,
            remaining_after,
            promo_code=promo_code_info,
            cap_message=cap_message,
        )
        message = self._build_trivia_simple_message(message_parts)

        # Phase 18: Build session_state for handler decisions
        session_state = None
        if not is_correct:
            session_state = self._build_streak_failure_state(user_id, previous_streak)
        elif promo_code_info:
            session_state = self._build_streak_claim_state(user_id, promo_code_info)

        logger.info(
            f"game_service - play_trivia_simple - {user_id} - correct:{is_correct}, streak:{new_streak}, besitos:{besitos}, bonus:{streak_bonus}"
        )

        # Commit del registro dejugada
        self.db.commit()

        return {
            "correct": is_correct,
            "besitos": besitos,
            "streak_bonus": streak_bonus,
            "besitos_total": besitos + streak_bonus,
            "previous_streak": previous_streak,
            "new_streak": new_streak,
            "streak_message": streak_message,
            "promo_code": promo_code_info,
            "message": message,
            "message_parts": message_parts,
            "remaining_after": remaining_after,
            "limit_reached": False,
            "session_state": session_state,
        }

    def _build_trivia_simple_message_parts(
        self,
        is_correct: bool,
        question: dict,
        besitos: int,
        streak_message: str | None,
        streak_bonus: int,
        remaining: int,
        promo_code: dict | None = None,
        cap_message: str | None = None,
    ) -> dict:
        """Construye las partes del mensaje de trivia simple."""
        correct_letter = ["A", "B", "C", "D"][question["answer"]]
        correct_answer_text = f"{correct_letter}) {question['opts'][question['answer']]}"

        if is_correct:
            header = self._select_template(self.TRIVIA_SIMPLE_TEMPLATES["correct"])
        else:
            header_template = self._select_template(self.TRIVIA_SIMPLE_TEMPLATES["incorrect"])
            header = header_template.format(correct_answer=correct_answer_text)

        reward_text = None
        if is_correct and (besitos > 0 or streak_bonus > 0):
            if besitos > 0:
                reward_text = f"+{besitos} besitos \U0001f48b"
            if streak_bonus > 0:
                if reward_text:
                    reward_text += f"\n+BONUS racha: +{streak_bonus} besitos"
                else:
                    reward_text = f"+BONUS racha: +{streak_bonus} besitos"

        streak_text = streak_message

        encouragement = None
        if remaining > 0:
            encouragement = f"Oportunidades simples restantes: {remaining}"
        else:
            encouragement = "No le quedan jugadas de trivia especial por hoy. Vuelva mañana."

        # Phase 17: Promo code line
        promo_code_line = None
        if promo_code and promo_code.get("code"):
            code = promo_code["code"]
            promo_code_line = (
                f"\U0001f39f️ <b>¡Código de descuento ganado!</b>\n"
                f"<i>Su racha le ha otorgado: <code>{code}</code></i>\n"
                f"<i>Lucien guarda registro de este código en su archivo personal.</i>"
            )

        return {
            "header": header,
            "reward_text": reward_text,
            "streak_text": streak_text,
            "encouragement": encouragement,
            "promo_code_line": promo_code_line,
            "cap_message": cap_message,
        }

    def _build_trivia_simple_message(self, parts: dict) -> str:
        """Construye mensaje final de trivia simple."""
        lines = [parts["header"]]
        if parts.get("reward_text"):
            lines.extend(["", parts["reward_text"]])
        if parts.get("streak_text"):
            lines.extend(["", parts["streak_text"]])
        if parts.get("promo_code_line"):
            lines.extend(["", parts["promo_code_line"]])
        if parts.get("cap_message"):
            lines.extend(["", parts["cap_message"]])
        if parts.get("encouragement"):
            lines.extend(["", parts["encouragement"]])
        return "\n".join(lines)

    def get_active_special_info(self) -> dict | None:
        """Consulta categoria activa y retorna {category_id, display_name} o None."""
        from services.trivia_service import TriviaCategoryService

        tcs = TriviaCategoryService(self.db)
        try:
            active = tcs.get_active_category()
            if not active:
                return None
            return {"category_id": active["category_id"], "display_name": active["display_name"]}
        finally:
            tcs.close()


# =============================================================================
# Cross-domain event listeners (registered explicitly from bot.py on startup).
# The listener lives here (game domain ownership). It is a plain async callable
# receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
# (to avoid any re-entrancy with game award paths or future extensions; game
# award contracts and partial-failure behavior are authoritative in the credit flows
# inside play_* methods + streak protection).
# This is observational only (best effort; errors swallowed by bus).
# =============================================================================


async def on_besitos_awarded_game_award_observer(payload: dict) -> None:
    """
    Game-domain listener for "besitos_awarded" events (emitted by BesitoService.credit_besitos
    post-commit, including from GAME/TRIVIA credits in play_dice_game / play_trivia_game / etc
    and streak bonuses).

    DESIRED CONTRACT (copy of narrative precedent + Reward Item5): log reception with full context
    (user_id/amount/source/ref); purely observational + wiring proof for this domain.
    MUST NOT credit, debit, or mutate besitos state here.
    Future extensions (e.g. streak/promo hooks on game awards) belong in this module and should use
    get_service(GameService) or direct models if a fresh DB session is required.
    """
    uid = payload.get("user_id")
    amt = payload.get("amount")
    src = payload.get("source")
    ref = payload.get("reference_id")
    logger.info(
        f"game | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"
    )
    # No side effects that mutate besitos here (best effort, non-authoritative; 0 impact on game award contracts / atomicity gold / partial failure).
