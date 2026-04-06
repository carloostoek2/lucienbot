"""
Servicio de Minijuegos - Lucien Bot

Gestiona los minijuegos de dados y trivia con límites diarios.
"""
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session
from models.models import GameRecord, TransactionSource
from models.database import SessionLocal
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
    TRIVIA_WIN_BESITOS = 2

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.besito_service = BesitoService(self.db)
        self._user_service = UserService(self.db)
        self._vip_service = VIPService(self.db)
        self._questions = None

    def close(self):
        """Cierra la sesión de base de datos"""
        if hasattr(self, 'db') and self.db:
            self.db.close()

    # ==================== VIP DETECTION ====================

    def is_user_vip(self, user_id: int) -> bool:
        """Verifica si usuario es VIP"""
        return self._vip_service.is_user_vip(user_id)

    def get_daily_limits(self, user_id: int) -> dict:
        """Obtiene límites diarios según tipo de usuario"""
        is_vip = self.is_user_vip(user_id)
        return {
            'dice_limit': self.DAILY_DICE_LIMIT_VIP if is_vip else self.DAILY_DICE_LIMIT_FREE,
            'trivia_limit': self.DAILY_TRIVIA_LIMIT_VIP if is_vip else self.DAILY_TRIVIA_LIMIT_FREE
        }

    # ==================== CONTEO DIARIO ====================

    def get_today_play_count(self, user_id: int, game_type: str) -> int:
        """Obtiene jugadas de hoy para un tipo de juego"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.db.query(GameRecord).filter(
            GameRecord.user_id == user_id,
            GameRecord.game_type == game_type,
            GameRecord.played_at >= today
        ).count()

    def can_play(self, user_id: int, game_type: str) -> Tuple[bool, int, int, str]:
        """
        Verifica si usuario puede jugar según límites diarios.
        Returns: (puede_jugar, jugadas_hoy, limite, mensaje)
        """
        limits = self.get_daily_limits(user_id)
        limit = limits['dice_limit'] if game_type == 'dice' else limits['trivia_limit']
        played = self.get_today_play_count(user_id, game_type)

        if played >= limit:
            is_vip = self.is_user_vip(user_id)
            if is_vip:
                return False, played, limit, "Has alcanzado tu límite diario. Regresa mañana."
            else:
                return False, played, limit, (
                    "Has alcanzado tu límite diario de juegos.\n"
                    "¡Pero! Los miembros VIP tienen el doble de oportunidades..."
                )
        return True, played, limit, None

    # ==================== DADOS ====================

    def roll_dice(self) -> Tuple[int, int]:
        """Lanza dos dados (1-6)"""
        return random.randint(1, 6), random.randint(1, 6)

    def check_dice_win(self, dice1: int, dice2: int) -> str:
        """
        Verifica victoria: pares (ambos pares) o dobles (iguales).
        Returns: 'pairs', 'doubles', o 'none'
        """
        if dice1 == dice2:
            return 'doubles'
        if dice1 % 2 == 0 and dice2 % 2 == 0:
            return 'pairs'
        return 'none'

    def play_dice_game(self, user_id: int) -> Dict[str, Any]:
        """
        Procesa una partida de dados.
        Returns: {dice1, dice2, won, win_type, besitos, message, limit_reached}
        """
        # 1. Verificar límites
        can_play, played, limit, limit_msg = self.can_play(user_id, 'dice')
        if not can_play:
            return {
                'dice1': None, 'dice2': None, 'won': False,
                'win_type': None, 'besitos': 0, 'message': limit_msg,
                'limit_reached': True
            }

        # 2. Roll dice
        dice1, dice2 = self.roll_dice()

        # 3. Check win
        win_type = self.check_dice_win(dice1, dice2)
        won = win_type != 'none'

        # 4. Credit besitos si ganó
        besitos = 0
        if won:
            besitos = self.DICE_WIN_BESITOS
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=besitos,
                source=TransactionSource.GAME,
                description=f"Victoria en dados: {win_type}"
            )

        # 5. Registrar jugada
        record = GameRecord(
            user_id=user_id,
            game_type='dice',
            result=f"{dice1}+{dice2}",
            payout=besitos
        )
        self.db.add(record)
        self.db.commit()

        # 6. Construir mensaje
        if won:
            win_label = "pares" if win_type == 'pairs' else "dobles"
            message = f"🎲 {dice1} + {dice2} GANASTE!\n\n" \
                     f"¡Son {win_label}! Has ganado {besitos} besito 💋"
        else:
            message = f"🎲 {dice1} + {dice2}\n\nMejor suerte la próxima..."

        logger.info(f"game_service - play_dice_game - {user_id} - won: {won}, win_type: {win_type}")

        return {
            'dice1': dice1, 'dice2': dice2, 'won': won,
            'win_type': win_type, 'besitos': besitos, 'message': message,
            'limit_reached': False
        }

    # ==================== TRIVIA ====================

    def load_trivia_questions(self) -> list:
        """Carga preguntas de docs/preguntas.json"""
        if self._questions is not None:
            return self._questions

        questions_path = Path("docs/preguntas.json")
        if not questions_path.exists():
            logger.warning("Questions file not found: docs/preguntas.json")
            return []

        try:
            with open(questions_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._questions = data if isinstance(data, list) else data.get('questions', [])
        except Exception as e:
            logger.error(f"Error loading trivia questions: {e}")
            self._questions = []

        return self._questions

    def get_random_question(self) -> Tuple[Optional[dict], int]:
        """Retorna pregunta aleatoria con índice"""
        questions = self.load_trivia_questions()
        if not questions:
            return None, -1

        idx = random.randint(0, len(questions) - 1)
        return questions[idx], idx

    def get_question_by_index(self, index: int) -> Optional[dict]:
        """Retorna pregunta por índice"""
        questions = self.load_trivia_questions()
        if 0 <= index < len(questions):
            return questions[index]
        return None

    def check_trivia_answer(self, question: dict, answer_idx: int) -> bool:
        """Verifica si respuesta es correcta"""
        if not question:
            return False
        return question.get('answer') == answer_idx

    def play_trivia(self, user_id: int, question_idx: int, answer_idx: int) -> Dict[str, Any]:
        """
        Procesa respuesta de trivia.
        Returns: {correct, besitos, message, correct_answer, limit_reached}
        """
        # 1. Verificar límites
        can_play, played, limit, limit_msg = self.can_play(user_id, 'trivia')
        if not can_play:
            return {
                'correct': False, 'besitos': 0,
                'message': limit_msg, 'correct_answer': -1,
                'limit_reached': True
            }

        # 2. Obtener pregunta
        question = self.get_question_by_index(question_idx)
        if not question:
            return {
                'correct': False, 'besitos': 0,
                'message': "Pregunta no encontrada.", 'correct_answer': -1,
                'limit_reached': False
            }

        # 3. Verificar respuesta
        is_correct = self.check_trivia_answer(question, answer_idx)

        # 4. Credit besitos si correcto
        besitos = 0
        if is_correct:
            besitos = self.TRIVIA_WIN_BESITOS
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=besitos,
                source=TransactionSource.TRIVIA,
                description="Victoria en trivia"
            )

        # 5. Registrar jugada
        record = GameRecord(
            user_id=user_id,
            game_type='trivia',
            result=f"question_{question_idx}",
            payout=besitos
        )
        self.db.add(record)
        self.db.commit()

        # 6. Construir mensaje
        correct_opt = ["A", "B", "C"][question['answer']]
        if is_correct:
            message = f"🌟 ¡CORRECTO! 🌟\n\nHas respondido bien y ganado {besitos} besitos 💋"
        else:
            message = f"❌ No es correcto...\n\nLa respuesta era: {correct_opt})"

        logger.info(f"game_service - play_trivia - {user_id} - correct: {is_correct}")

        return {
            'correct': is_correct, 'besitos': besitos,
            'message': message, 'correct_answer': question['answer'],
            'limit_reached': False
        }

    def __del__(self):
        """Cierra la sesión"""
        self.close()