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
from services.trivia_discount_service import TriviaDiscountService
from services.trivia_config_service import TriviaConfigService

logger = logging.getLogger(__name__)


class GameService:
    """Servicio para minijuegos de dados y trivia"""

    # Constantes de límites diarios
    DAILY_DICE_LIMIT_FREE = 10
    DAILY_DICE_LIMIT_VIP = 20
    DAILY_TRIVIA_LIMIT_FREE = 7
    DAILY_TRIVIA_LIMIT_VIP = 15

    # Recompensas por victoria
    DICE_WIN_BESITOS = 1
    TRIVIA_WIN_BESITOS = 1
    TRIVIA_VIP_WIN_BESITOS = 5

    # Límites trivia VIP
    DAILY_TRIVIA_VIP_LIMIT = 5

    # Class-level cache for active question set path (updated by scheduler)
    _active_question_set_path = "docs/preguntas.json"
    _active_question_set_vip_path = None  # None = use default VIP questions

    def _get_active_question_set_path(self) -> str:
        """Returns the file path of the currently active question set.
        Priority: manual override > promotion active > default
        Updated by scheduler job, cached here for synchronous access.
        """
        return self._active_question_set_path

    def _get_active_question_set_vip_path(self) -> Optional[str]:
        """Returns optional VIP themed question set path, or None for default."""
        return self._active_question_set_vip_path

    # ==================== TEMPLATES DE COPY ====================

    MENU_TEMPLATES = {
        'title': [
            "🎮 Los Juegos del Destino",
            "🎮 El Salón de las Oportunidades",
            "🎮 Donde la Fortuna Baila"
        ],
        'subtitle': [
            "Ah... pensé que podría verle esta noche.",
            "Diana ha preparado entretenimientos para quienes saben encontrar placer en los rituales.",
            "Los dados y el conocimiento aguardan su decisión..."
        ],
        'dice_description': [
            "🎲 Dados — el azar revela el carácter",
            "🎲 Los dados del destino guardan secretos...",
            "🎲 En cada tirada, la suerte se revela."
        ],
        'trivia_description': [
            "❓ Trivia — el conocimiento es poder",
            "❓ El examen de Diana aguarda...",
            "❓ Las preguntas revelan quienes realmente observan."
        ],
        'trivia_vip_description': [
            "🎩 Trivia VIP — solo para los más devotos",
            "🎩 El Examen Secreto de Diana",
            "🎩 Demuestra tu conocimiento íntimo"
        ],
        'footer': [
            "Sus oportunidades de esta noche:",
            "¿Cuál será su elección, visitante?",
            "Lucien observa con interés..."
        ]
    }

    DICE_TEMPLATES = {
        'entry_title': [
            "🎲 Los Dados del Destino",
            "🎲 El Ritual de los Números",
            "🎲 Donde la Fortuna Gira"
        ],
        'entry_intro': [
            "Los dados guardan secretos antiguos...",
            "En cada cara, un destino diferente.",
            "La suerte es un lenguaje que pocos entienden."
        ],
        'rules': [
            "• Pares (ambos pares): +1 besito 💋\n• Dobles (iguales): +1 besito 💋",
            "• Dobles: la perfección se recompensa 💋\n• Pares: la armonía tiene su precio 💋",
            "• Dos iguales: la fortuna sonríe 💋\n• Dos pares: el equilibrio premia 💋"
        ],
        'win_doubles': [
            "¡DOBLES! La perfección absoluta...",
            "¡Los dados se alinean en su honor!",
            "¡Un espejo de números! La suerte le abraza."
        ],
        'win_pairs': [
            "¡PARES! La armonía de los pares...",
            "Los números pares bailan para usted...",
            "¡La simetría de la fortuna le sonríe!"
        ],
        'near_miss_consecutive': [
            "<i>inhala lentamente</i>... <b>{dice1}</b> y <b>{dice2}</b>. Tan cerca que duele, ¿no cree?",
            "Oh, la ironía... <b>{dice1}</b> y <b>{dice2}</b> son vecinos, pero el destino no permite visitas.",
            "Casi, casi... <b>{dice1}</b> y <b>{dice2}</b> le susurran al oído: 'la próxima vez, quizás'."
        ],
        'near_miss_seven': [
            "Siete, el número de la fortuna... pero no para usted, al parecer.",
            "La suma perfecta en una combinación imperfecta. La vida es así de graciosa.",
            "Siete le susurra... 'hoy no es su día'."
        ],
        'loss': [
            "Hmm... <b>{dice1}</b> y <b>{dice2}</b>. El destino ha decidido ser discreto con usted. No se preocupe — Diana ha visto a sus favoritos perder muchas veces antes de que todo cambie.",
            "<b>{dice1}</b> y <b>{dice2}</b>... Interesante. Lucien observa que la fortuna le está haciendo esperar. Quizás debería intentarlo de nuevo... o no.",
            "<b>{dice1}</b> y <b>{dice2}</b>. Ah, la ironía del azar. Un momento desalentador, certamente, pero ¿quién sabe? Quizás mañana el destino sea más... generoso."
        ],
        'limit_reached': [
            "Ha completado todos sus rituales del día. El destino, como Diana misma, aprecia la mesura sobre la obsesión.",
            "Los dados descansan... al igual que usted debería. Hasta mañana.",
            "Su tiempo con la fortuna ha terminado por hoy. Regrese mañana... hay quienes dicen que la suerte cambia después del descanso."
        ]
    }

    TRIVIA_TEMPLATES = {
        'entry_title': [
            "❓ El Examen de Diana",
            "❓ Las Preguntas del Conocimiento",
            "❓ El Desafío de la Sabiduría"
        ],
        'entry_intro': [
            "Diana observa quién realmente presta atención...",
            "El conocimiento revela devoción verdadera.",
            "Solo los atentos conocen las respuestas."
        ],
        'counter': [
            "Oportunidades restantes: {remaining} de {limit}",
            "Tiene {remaining} caminos de {limit} disponibles...",
            "{remaining} de {limit} intentos aguardan su sabiduría."
        ],
        'correct': [
            "🎩 <b>Lucien:</b>\n<i>¡Correcto! Diana asiente con aprobación...</i>",
            "🎩 <b>Lucien:</b>\n<i>¡La respuesta exacta! Su atención no pasa desapercibida.</i>",
            "🎩 <b>Lucien:</b>\n<i>¡Sabiduría revelada! Ha demostrado su devoción.</i>"
        ],
        'incorrect': [
            "🎩 <b>Lucien:</b>\n<i>Ah... No exactamente.</i>\n\nLa respuesta era: <b>{correct_answer}</b>\n\n<i>Diana dice que equivocarse es inevitable. Lo revelador es cómo uno continúa después.</i>",
            "🎩 <b>Lucien:</b>\n<i>Hmm... No.</i>\n\nLa respuesta era: <b>{correct_answer}</b>\n\n<i>Lucien observa que incluso los más devotos pueden distraerse. Quizás debería prestar más atención...</i>",
            "🎩 <b>Lucien:</b>\n<i>No...</i>\n\nLa respuesta correcta era: <b>{correct_answer}</b>\n\n<i>Un momento humillante, ¿verdad? Pero no se preocupe — Diana ha perdonado errores peores.</i>"
        ],
        'streak_messages': {
            2: ["🔥 Comienza a calentar...", "🔥 Diana nota su constancia..."],
            3: ["⚡ ¡Racha de {streak}! Su mente despierta...", "⚡ {streak} correctas... impresionante."],
            5: ["🌟 ¡Imparable! La sabiduría fluye en usted.", "🌟 {streak} victorias... es un prodigio."],
            7: ["🎩 ¡Una leyenda nace! {streak} aciertos.", "🎩 Los dioses envidian su conocimiento."],
            10: ["✨ ¡DIVINO! {streak} respuestas perfectas.", "✨ Es uno con la sabiduría de Diana."]
        },
        'limit_reached': [
            "Ha agotado sus preguntas por hoy. El conocimiento, como el buen vino, requiere pausas.",
            "El examen ha terminado... por ahora. Diana aprecia la mesura sobre la obsesión.",
            "Diana guarda las preguntas para mañana. El verdadero sabio sabe cuándo descansar."
        ]
    }

    TRIVIA_VIP_TEMPLATES = {
        'entry_title': [
            "🎩 El Examen Secreto de Diana",
            "🎩 La Trivia que solo los iniciados conocen",
            "🎩 Donde el conocimiento tiene recompensa mayor"
        ],
        'entry_intro': [
            "Solo los verdaderamente devotos conocen estas respuestas...",
            "Diana ha preparado preguntas especiales para sus favoritos.",
            "El conocimiento íntimo se recompensa con generosidad."
        ],
        'counter': [
            "Oportunidades VIP restantes: {remaining} de {limit}",
            "Tiene {remaining} preguntas secretas de {limit}...",
            "{remaining} de {limit} caminos exclusivos aguardan."
        ],
        'correct': [
            "🎩 <b>Lucien:</b>\n<i>¡Impresionante! Diana está complacida...</i>",
            "🎩 <b>Lucien:</b>\n<i>¡La respuesta perfecta! Su devoción es innegable.</i>",
            "🎩 <b>Lucien:</b>\n<i>¡Sabiduría de élite! Diana asiente con admiración.</i>"
        ],
        'incorrect': [
            "🎩 <b>Lucien:</b>\n<i>Ah... No exactamente.</i>\n\nLa respuesta era: <b>{correct_answer}</b>\n\n<i>Diana observa que incluso los más cercanos pueden fallar. Continúe intentándolo...</i>",
            "🎩 <b>Lucien:</b>\n<i>Hmm... No.</i>\n\nLa respuesta era: <b>{correct_answer}</b>\n\n<i>El camino del conocimiento íntimo requiere paciencia. Diana perdona el error.</i>",
            "🎩 <b>Lucien:</b>\n<i>No...</i>\n\nLa respuesta correcta era: <b>{correct_answer}</b>\n\n<i>Un tropiezo, certamente. Pero el verdadero devoto se levanta.</i>"
        ],
        'streak_messages': {
            2: ["🔥 Comienza a destacar entre los demás...", "🔥 Diana nota su dedicación VIP..."],
            3: ["⚡ ¡Racha de {streak}! Es verdaderamente especial.", "⚡ {streak} correctas... hay quienes pagarían por este conocimiento."],
            5: ["🌟 ¡Imparable! La aristocracia del conocimiento.", "🌟 {streak} victorias... es usted crème de la crème."],
            7: ["🎩 ¡LEYENDA! {streak} aciertos. Diana le observa con interés.", "🎩 Los dioses del conocimiento palidecen ante usted."],
            10: ["✨ ¡DIVINO! {streak} respuestas perfectas. Es parte del círculo íntimo.", "✨ Ha alcanzado la iluminación de Diana."]
        },
        'limit_reached': [
            "Ha agotado sus preguntas secretas por hoy. Diana aprecia su persistencia, pero también la mesura.",
            "El examen VIP ha terminado... por ahora. Regrese mañana para más desafíos.",
            "Diana ha guardado sus preguntas VIP para mañana. El verdadero connaisseur sabe esperar."
        ]
    }

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.besito_service = BesitoService(self.db)
        self._user_service = UserService(self.db)
        self._vip_service = VIPService(self.db)
        self._trivia_discount_service = TriviaDiscountService()
        self._trivia_config_service = TriviaConfigService(self.db)
        self._questions = None
        self._vip_questions = None
        # Instance-level cache tracking - each instance tracks its own loaded path
        self._last_loaded_path = None
        self._last_loaded_vip_path = None

    def close(self):
        """Cierra la sesión de base de datos"""
        if hasattr(self, 'db') and self.db:
            self.db.close()

    # ==================== TEMPLATE HELPERS ====================

    def _select_template(self, template_list: list) -> str:
        """Selecciona una variación aleatoria de template"""
        selected = random.choice(template_list)
        logger.debug(f"game_service - _select_template - selected from {len(template_list)} variations")
        return selected

    def _is_near_miss(self, dice1: int, dice2: int) -> dict:
        """
        Detecta 'casi victorias' en dados.
        Returns: {is_near_miss, type, description}
        """
        # No es near miss si es victoria
        if dice1 == dice2 or (dice1 % 2 == 0 and dice2 % 2 == 0):
            return {'is_near_miss': False, 'type': None, 'description': None}

        # Dados consecutivos (3-4, 5-6, etc.)
        if abs(dice1 - dice2) == 1:
            template = self._select_template(self.DICE_TEMPLATES['near_miss_consecutive'])
            return {
                'is_near_miss': True,
                'type': 'consecutive',
                'description': template.format(dice1=dice1, dice2=dice2)
            }

        # Suma 7
        if dice1 + dice2 == 7:
            template = self._select_template(self.DICE_TEMPLATES['near_miss_seven'])
            return {
                'is_near_miss': True,
                'type': 'seven',
                'description': template.format(dice1=dice1, dice2=dice2)
            }

        return {'is_near_miss': False, 'type': None, 'description': None}

    def _get_today_trivia_records(self, user_id: int) -> list:
        """Obtiene registros de trivia de hoy ordenados por tiempo DESC"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        records = self.db.query(GameRecord).filter(
            GameRecord.user_id == user_id,
            GameRecord.game_type == 'trivia',
            GameRecord.played_at >= today
        ).order_by(GameRecord.played_at.desc()).all()
        return records

    def _get_trivia_streak(self, user_id: int) -> int:
        """Calcula racha actual de victorias en trivia (solo hoy)"""
        records = self._get_today_trivia_records(user_id)
        streak = 0
        for record in records:
            if record.payout > 0:
                streak += 1
            else:
                break
        return streak

    def _get_streak_message(self, streak: int) -> Optional[str]:
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

        templates = self.TRIVIA_TEMPLATES['streak_messages'].get(level, ["¡Racha de {streak}!"])
        return self._select_template(templates).format(streak=streak)

    def _build_dice_message(self, parts: dict) -> str:
        """Construye mensaje final de dados desde partes"""
        lines = [parts['header'], '', parts['dice_display'], '', parts['result_text']]
        if parts.get('reward_text'):
            lines.extend(['', parts['reward_text']])
        if parts.get('encouragement'):
            lines.extend(['', parts['encouragement']])
        return '\n'.join(lines)

    def _build_trivia_message(self, parts: dict) -> str:
        """Construye mensaje final de trivia desde partes"""
        lines = [parts['header']]
        if parts.get('reward_text'):
            lines.extend(['', parts['reward_text']])
        if parts.get('streak_text'):
            lines.extend(['', parts['streak_text']])
        if parts.get('encouragement'):
            lines.extend(['', parts['encouragement']])
        return '\n'.join(lines)

    # ==================== VIP DETECTION ====================

    def is_user_vip(self, user_id: int) -> bool:
        """Verifica si usuario es VIP"""
        return self._vip_service.is_user_vip(user_id)

    def get_daily_limits(self, user_id: int) -> dict:
        """Obtiene límites diarios según tipo de usuario"""
        is_vip = self.is_user_vip(user_id)
        trivia_config = self._trivia_config_service.get_config()
        return {
            'dice_limit': self.DAILY_DICE_LIMIT_VIP if is_vip else self.DAILY_DICE_LIMIT_FREE,
            'trivia_limit': trivia_config.daily_trivia_limit_vip if is_vip else trivia_config.daily_trivia_limit_free,
            'trivia_vip_limit': trivia_config.daily_trivia_vip_limit
        }

    def get_menu_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para el menú de juegos"""
        limits = self.get_daily_limits(user_id)
        dice_played = self.get_today_play_count(user_id, 'dice')
        trivia_played = self.get_today_play_count(user_id, 'trivia')

        remaining_dice = max(0, limits['dice_limit'] - dice_played)
        remaining_trivia = max(0, limits['trivia_limit'] - trivia_played)

        logger.info(f"game_service - get_menu_data - {user_id} - dice:{remaining_dice}/{limits['dice_limit']}, trivia:{remaining_trivia}/{limits['trivia_limit']}")

        return {
            'title': self._select_template(self.MENU_TEMPLATES['title']),
            'subtitle': self._select_template(self.MENU_TEMPLATES['subtitle']),
            'dice_description': self._select_template(self.MENU_TEMPLATES['dice_description']),
            'trivia_description': self._select_template(self.MENU_TEMPLATES['trivia_description']),
            'footer': self._select_template(self.MENU_TEMPLATES['footer']),
            'remaining_dice': remaining_dice,
            'remaining_trivia': remaining_trivia,
            'limit_dice': limits['dice_limit'],
            'limit_trivia': limits['trivia_limit'],
            'is_vip': self.is_user_vip(user_id)
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
                return False, played, limit, "Ha alcanzado su límite diario. Regrese mañana."
            else:
                return False, played, limit, (
                    "Ha alcanzado su límite diario de juegos.\n"
                    "¡Pero! Los miembros VIP tienen el doble de oportunidades..."
                )
        return True, played, limit, None

    # ==================== DADOS ====================

    def get_dice_entry_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para la entrada del juego de dados"""
        limits = self.get_daily_limits(user_id)
        played = self.get_today_play_count(user_id, 'dice')
        remaining = max(0, limits['dice_limit'] - played)

        logger.info(f"game_service - get_dice_entry_data - {user_id} - remaining:{remaining}/{limits['dice_limit']}")

        return {
            'title': self._select_template(self.DICE_TEMPLATES['entry_title']),
            'intro': self._select_template(self.DICE_TEMPLATES['entry_intro']),
            'rules': self._select_template(self.DICE_TEMPLATES['rules']),
            'remaining': remaining,
            'limit': limits['dice_limit'],
            'is_vip': self.is_user_vip(user_id)
        }

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
        Procesa una partida de dados con near-miss detection.
        Returns: {dice1, dice2, sum, won, win_type, is_near_miss, near_miss_type,
                 besitos, remaining_after, message_parts, limit_reached, message}
        """
        # 1. Verificar límites
        can_play, played, limit, limit_msg = self.can_play(user_id, 'dice')
        if not can_play:
            limit_template = self._select_template(self.DICE_TEMPLATES['limit_reached'])
            return {
                'dice1': None, 'dice2': None, 'sum': 0, 'won': False,
                'win_type': None, 'is_near_miss': False, 'near_miss_type': None,
                'besitos': 0, 'remaining_after': 0,
                'message_parts': {}, 'limit_reached': True,
                'message': limit_template + "\n\n" + limit_msg
            }

        # 2. Lanzar dados
        dice1, dice2 = self.roll_dice()
        dice_sum = dice1 + dice2

        # 3. Verificar victoria
        win_type = self.check_dice_win(dice1, dice2)
        won = win_type != 'none'

        # 4. Verificar near-miss (solo si no ganó)
        near_miss = {'is_near_miss': False, 'type': None, 'description': None}
        if not won:
            near_miss = self._is_near_miss(dice1, dice2)

        # 5. Acreditar besitos si ganó
        besitos = 0
        if won:
            besitos = self.DICE_WIN_BESITOS
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=besitos,
                source=TransactionSource.GAME,
                description=f"Victoria en dados: {win_type}"
            )

        # 6. Registrar jugada
        record = GameRecord(
            user_id=user_id,
            game_type='dice',
            result=f"{dice1}+{dice2}",
            payout=besitos
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

        logger.info(f"game_service - play_dice_game - {user_id} - dice:{dice1}+{dice2}, won:{won}, near_miss:{near_miss['is_near_miss']}")

        return {
            'dice1': dice1,
            'dice2': dice2,
            'sum': dice_sum,
            'won': won,
            'win_type': win_type if won else None,
            'is_near_miss': near_miss['is_near_miss'],
            'near_miss_type': near_miss['type'],
            'besitos': besitos,
            'remaining_after': remaining_after,
            'message_parts': message_parts,
            'limit_reached': False,
            'message': message
        }

    def _build_dice_message_parts(self, dice1: int, dice2: int, won: bool,
                                   win_type: str, near_miss: dict, besitos: int,
                                   remaining: int) -> dict:
        """Construye las partes del mensaje de dados"""
        # Header con resultado visual y tipo de victoria si aplica
        if won:
            if win_type == 'doubles':
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
                self.DICE_TEMPLATES['win_doubles'] if win_type == 'doubles' else self.DICE_TEMPLATES['win_pairs']
            )
        elif near_miss['is_near_miss']:
            result_text = near_miss['description']
        else:
            result_text = self._select_template(self.DICE_TEMPLATES['loss']).format(dice1=dice1, dice2=dice2)

        # Texto de recompensa
        reward_text = None
        if won:
            reward_text = f"+{besitos} besito{'s' if besitos > 1 else ''} 💋"

        # Mensaje de ánimo/oportunidades restantes
        encouragement = None
        if remaining > 0:
            encouragement = f"Oportunidades restantes: {remaining}"
        else:
            encouragement = "Ha agotado sus oportunidades por hoy."

        return {
            'header': header,
            'dice_display': dice_display,
            'result_text': result_text,
            'reward_text': reward_text,
            'encouragement': encouragement
        }

    # ==================== TRIVIA ====================

    def get_trivia_entry_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para la entrada de trivia"""
        limits = self.get_daily_limits(user_id)
        played = self.get_today_play_count(user_id, 'trivia')
        remaining = max(0, limits['trivia_limit'] - played)
        streak = self._get_trivia_streak(user_id)

        can_play = remaining > 0
        limit_message = None
        if not can_play:
            limit_message = self._select_template(self.TRIVIA_TEMPLATES['limit_reached'])
            is_vip = self.is_user_vip(user_id)
            if not is_vip:
                limit_message += "\n\nLos caminos de VIP siempre tienen más oportunidades..."

        # Información de descuento por racha
        discount_info = self._get_trivia_discount_info(user_id)

        logger.info(f"game_service - get_trivia_entry_data - {user_id} - remaining:{remaining}, streak:{streak}")

        return {
            'title': self._select_template(self.TRIVIA_TEMPLATES['entry_title']),
            'intro': self._select_template(self.TRIVIA_TEMPLATES['entry_intro']),
            'counter_template': self._select_template(self.TRIVIA_TEMPLATES['counter']),
            'remaining': remaining,
            'limit': limits['trivia_limit'],
            'current_streak': streak,
            'is_vip': self.is_user_vip(user_id),
            'can_play': can_play,
            'limit_message': limit_message,
            'discount_info': discount_info
        }

    def load_trivia_questions(self) -> list:
        """Carga preguntas del question set activo"""
        active_path = self._get_active_question_set_path()
        if self._questions is not None and getattr(self, '_last_loaded_path', None) == active_path:
            return self._questions

        questions_path = Path(active_path)
        if not questions_path.exists():
            logger.warning(f"Questions file not found: {active_path}")
            return []

        try:
            with open(questions_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._questions = data if isinstance(data, list) else data.get('questions', [])
        except Exception as e:
            logger.error(f"Error loading trivia questions: {e}")
            self._questions = []

        self._last_loaded_path = active_path
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
        Procesa respuesta de trivia con sistema de rachas.
        Returns: {correct, besitos, previous_streak, new_streak, streak_message,
                 message, message_parts, remaining_after, limit_reached}
        """
        # 1. Verificar límites
        can_play, played, limit, limit_msg = self.can_play(user_id, 'trivia')
        if not can_play:
            limit_template = self._select_template(self.TRIVIA_TEMPLATES['limit_reached'])
            full_message = limit_template + "\n\n" + limit_msg
            return {
                'correct': False, 'besitos': 0,
                'previous_streak': 0, 'new_streak': 0, 'streak_message': None,
                'message': full_message, 'message_parts': {},
                'remaining_after': 0, 'limit_reached': True
            }

        # 2. Obtener pregunta
        question = self.get_question_by_index(question_idx)
        if not question:
            return {
                'correct': False, 'besitos': 0,
                'previous_streak': 0, 'new_streak': 0, 'streak_message': None,
                'message': "Pregunta no encontrada.", 'message_parts': {},
                'remaining_after': max(0, limit - played), 'limit_reached': False
            }

        # 3. Obtener racha previa
        previous_streak = self._get_trivia_streak(user_id)

        # 4. Verificar respuesta
        is_correct = self.check_trivia_answer(question, answer_idx)

        # 5. Calcular nueva racha
        if is_correct:
            new_streak = previous_streak + 1
        else:
            new_streak = 0

        # 6. Obtener mensaje de racha si aplica
        streak_message = None
        if is_correct:
            streak_message = self._get_streak_message(new_streak)

        # 7. Acreditar besitos si correcto
        besitos = 0
        if is_correct:
            besitos = self.TRIVIA_WIN_BESITOS
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=besitos,
                source=TransactionSource.TRIVIA,
                description=f"Victoria en trivia (racha: {new_streak})"
            )

        # 8. Registrar jugada
        record = GameRecord(
            user_id=user_id,
            game_type='trivia',
            result=f"question_{question_idx}",
            payout=besitos
        )
        self.db.add(record)
        self.db.commit()

        # 9. Calcular oportunidades restantes
        remaining_after = max(0, limit - (played + 1))

        # 10. Construir partes del mensaje
        message_parts = self._build_trivia_message_parts(
            is_correct, question, besitos, streak_message, remaining_after
        )

        # 11. Construir mensaje final
        message = self._build_trivia_message(message_parts)

        logger.info(f"game_service - play_trivia - {user_id} - correct:{is_correct}, streak:{new_streak}")

        # 12. Verificar si alcanzó un tier (pero NO generar código automáticamente)
        tier_info = None
        if is_correct and new_streak > 0:
            tier_info = self._get_streak_tier_info(user_id, new_streak)

        return {
            'correct': is_correct,
            'besitos': besitos,
            'previous_streak': previous_streak,
            'new_streak': new_streak,
            'streak_message': streak_message,
            'message': message,
            'message_parts': message_parts,
            'remaining_after': remaining_after,
            'limit_reached': False,
            'tier_info': tier_info  # Info del tier alcanzado (para mostrar decisión)
        }

    def _build_trivia_message_parts(self, is_correct: bool, question: dict,
                                     besitos: int, streak_message: Optional[str],
                                     remaining: int) -> dict:
        """Construye las partes del mensaje de trivia"""
        # Respuesta correcta (para formatear templates)
        letters = ["A", "B", "C", "D"]
        answer_idx = min(question['answer'], len(letters) - 1)
        correct_letter = letters[answer_idx]
        correct_answer_text = f"{correct_letter}) {question['opts'][question['answer']]}"

        # Header según resultado
        if is_correct:
            header = self._select_template(self.TRIVIA_TEMPLATES['correct'])
        else:
            header_template = self._select_template(self.TRIVIA_TEMPLATES['incorrect'])
            header = header_template.format(correct_answer=correct_answer_text)

        # Resultado de la respuesta - simplificado
        result_text = None

        # Respuesta correcta (solo se muestra si se equivocó - ahora ya está en el header)
        correct_answer = None

        # Recompensa
        reward_text = None
        if is_correct:
            reward_text = f"+{besitos} besitos 💋"

        # Mensaje de racha
        streak_text = streak_message

        # Mensaje de oportunidades/ánimo
        encouragement = None
        if remaining > 0:
            encouragement = f"Oportunidades restantes: {remaining}"
        else:
            encouragement = "Ha agotado sus preguntas por hoy."

        return {
            'header': header,
            'result_text': result_text,
            'correct_answer': correct_answer,
            'reward_text': reward_text,
            'streak_text': streak_text,
            'encouragement': encouragement
        }

    # ==================== TRIVIA DISCOUNT ====================

    def _get_active_trivia_promotion(self) -> Optional[object]:
        """Obtiene promoción activa de trivia (primera que encuentra)"""
        configs = self._trivia_discount_service.get_active_trivia_promotion_configs()
        for config in configs:
            if config.is_active:
                return config
        return None

    def _get_streak_tier_info(self, user_id: int, new_streak: int) -> Optional[dict]:
        """Verifica si el streak alcanza un tier y retorna info del tier"""
        config = self._get_active_trivia_promotion()
        if not config:
            return None

        # Usar el sistema de tiers del trivia_discount_service
        tier = self._trivia_discount_service.get_tier_for_streak(config, new_streak)
        if not tier:
            return None

        # Verificar códigos disponibles
        available = self._trivia_discount_service.get_available_codes_count(config.id)
        if available <= 0:
            return None

        # Obtener siguiente tier para mostrar al usuario
        next_tier = self._trivia_discount_service.get_next_tier(config, new_streak)

        return {
            'tier_reached': True,
            'current_tier': tier,
            'next_tier': next_tier,
            'config_id': config.id,
            'is_final': next_tier is None  # True si no hay siguiente tier (100% gratis)
        }

    def _generate_tier_discount_code(self, user_id: int, config_id: int, discount_percentage: int) -> Optional[dict]:
        """Genera código de descuento con porcentaje específico del tier"""
        user_data = self._user_service.get_user(user_id)
        username = user_data.username if user_data else None
        first_name = user_data.first_name if user_data else None

        return self._trivia_discount_service.generate_tiered_discount_code(
            user_id=user_id,
            config_id=config_id,
            discount_percentage=discount_percentage,
            username=username,
            first_name=first_name
        )

    def _get_trivia_discount_info(self, user_id: int) -> Optional[dict]:
        """Obtiene información de descuento para mostrar en menú de trivia"""
        config = self._get_active_trivia_promotion()
        if not config:
            return None

        user_code = self._trivia_discount_service.get_user_discount_code(user_id, config.id)
        available = self._trivia_discount_service.get_available_codes_count(config.id)

        # Obtener tiempo restante si es duración relativa
        time_remaining = None
        if self._trivia_discount_service.is_duration_based(config):
            time_remaining = self._trivia_discount_service.get_time_remaining_formatted(config.id)

        return {
            'promotion_id': config.promotion_id,
            'promotion_name': config.promotion.name if config.promotion_id and config.promotion else config.custom_description,
            'discount_percentage': config.discount_percentage,
            'required_streak': config.required_streak,
            'available_codes': available,
            'total_codes': config.max_codes,
            'user_has_code': user_code is not None,
            'user_code': user_code.code if user_code else None,
            'user_code_status': user_code.status.value if user_code else None,
            'time_remaining': time_remaining,
            'is_duration_based': self._trivia_discount_service.is_duration_based(config)
        }

    # ==================== TRIVIA VIP ====================

    def _get_today_vip_trivia_records(self, user_id: int) -> list:
        """Obtiene registros de trivia VIP de hoy ordenados por tiempo DESC"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        records = self.db.query(GameRecord).filter(
            GameRecord.user_id == user_id,
            GameRecord.game_type == 'trivia_vip',
            GameRecord.played_at >= today
        ).order_by(GameRecord.played_at.desc()).all()
        return records

    def _get_vip_trivia_streak(self, user_id: int) -> int:
        """Calcula racha actual de victorias en trivia VIP (solo hoy)"""
        records = self._get_today_vip_trivia_records(user_id)
        streak = 0
        for record in records:
            if record.payout > 0:
                streak += 1
            else:
                break
        return streak

    def can_play_vip_trivia(self, user_id: int) -> Tuple[bool, int, int, str]:
        """
        Verifica si usuario VIP puede jugar trivia VIP.
        Returns: (puede_jugar, jugadas_hoy, limite, mensaje)
        """
        if not self.is_user_vip(user_id):
            config = self._trivia_config_service.get_config()
            return False, 0, config.daily_trivia_vip_limit, "Esta trivia es exclusiva para miembros VIP."

        played = len(self._get_today_vip_trivia_records(user_id))
        config = self._trivia_config_service.get_config()
        limit = config.daily_trivia_vip_limit

        if played >= limit:
            return False, played, limit, self._select_template(self.TRIVIA_VIP_TEMPLATES['limit_reached'])

        return True, played, limit, None

    def load_trivia_vip_questions(self) -> list:
        """Carga preguntas VIP del question set activo"""
        active_path = self._get_active_question_set_vip_path() or "docs/preguntas_vip.json"
        if self._vip_questions is not None and getattr(self, '_last_loaded_vip_path', None) == active_path:
            return self._vip_questions

        questions_path = Path(active_path)
        if not questions_path.exists():
            logger.warning(f"VIP Questions file not found: {active_path}")
            return []

        try:
            with open(questions_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._vip_questions = data if isinstance(data, list) else data.get('questions', [])
        except Exception as e:
            logger.error(f"Error loading VIP trivia questions: {e}")
            self._vip_questions = []

        self._last_loaded_vip_path = active_path
        return self._vip_questions

    def get_random_vip_question(self) -> Tuple[Optional[dict], int]:
        """Retorna pregunta VIP aleatoria con índice"""
        questions = self.load_trivia_vip_questions()
        if not questions:
            return None, -1

        idx = random.randint(0, len(questions) - 1)
        return questions[idx], idx

    def get_vip_question_by_index(self, index: int) -> Optional[dict]:
        """Retorna pregunta VIP por índice"""
        questions = self.load_trivia_vip_questions()
        if 0 <= index < len(questions):
            return questions[index]
        return None

    def check_trivia_vip_answer(self, question: dict, answer_idx: int) -> bool:
        """Verifica si respuesta VIP es correcta"""
        if not question:
            return False
        return question.get('answer') == answer_idx

    def get_trivia_vip_entry_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para la entrada de trivia VIP"""
        limits = self.get_daily_limits(user_id)
        played = len(self._get_today_vip_trivia_records(user_id))
        remaining = max(0, limits['trivia_vip_limit'] - played)
        streak = self._get_vip_trivia_streak(user_id)

        can_play = remaining > 0
        is_vip = self.is_user_vip(user_id)
        limit_message = None

        if not is_vip:
            limit_message = "Esta trivia es exclusiva para miembros VIP."
            can_play = False
        elif not can_play:
            limit_message = self._select_template(self.TRIVIA_VIP_TEMPLATES['limit_reached'])

        logger.info(f"game_service - get_trivia_vip_entry_data - {user_id} - remaining:{remaining}, streak:{streak}, is_vip:{is_vip}")

        return {
            'title': self._select_template(self.TRIVIA_VIP_TEMPLATES['entry_title']),
            'intro': self._select_template(self.TRIVIA_VIP_TEMPLATES['entry_intro']),
            'counter_template': self._select_template(self.TRIVIA_VIP_TEMPLATES['counter']),
            'remaining': remaining,
            'limit': limits['trivia_vip_limit'],
            'current_streak': streak,
            'is_vip': is_vip,
            'can_play': can_play,
            'limit_message': limit_message,
            'discount_info': self._get_trivia_discount_info(user_id)
        }

    def play_trivia_vip(self, user_id: int, question_idx: int, answer_idx: int) -> Dict[str, Any]:
        """
        Procesa respuesta de trivia VIP con sistema de rachas y 5 besitos.
        Returns: {correct, besitos, previous_streak, new_streak, streak_message,
                 message, message_parts, remaining_after, limit_reached}
        """
        # 1. Verificar si es VIP y límites
        can_play, played, limit, limit_msg = self.can_play_vip_trivia(user_id)
        if not can_play:
            return {
                'correct': False, 'besitos': 0,
                'previous_streak': 0, 'new_streak': 0, 'streak_message': None,
                'message': limit_msg, 'message_parts': {},
                'remaining_after': 0, 'limit_reached': True
            }

        # 2. Obtener pregunta
        question = self.get_vip_question_by_index(question_idx)
        if not question:
            return {
                'correct': False, 'besitos': 0,
                'previous_streak': 0, 'new_streak': 0, 'streak_message': None,
                'message': "Pregunta no encontrada.", 'message_parts': {},
                'remaining_after': max(0, limit - played), 'limit_reached': False
            }

        # 3. Obtener racha previa
        previous_streak = self._get_vip_trivia_streak(user_id)

        # 4. Verificar respuesta
        is_correct = self.check_trivia_vip_answer(question, answer_idx)

        # 5. Calcular nueva racha
        if is_correct:
            new_streak = previous_streak + 1
        else:
            new_streak = 0

        # 6. Obtener mensaje de racha si aplica
        streak_message = None
        if is_correct:
            streak_message = self._get_streak_message(new_streak)

        # 7. Acreditar 5 besitos si correcto
        besitos = 0
        if is_correct:
            besitos = self.TRIVIA_VIP_WIN_BESITOS
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=besitos,
                source=TransactionSource.TRIVIA,
                description=f"Victoria en trivia VIP (racha: {new_streak})"
            )

        # 8. Registrar jugada
        record = GameRecord(
            user_id=user_id,
            game_type='trivia_vip',
            result=f"vip_question_{question_idx}",
            payout=besitos
        )
        self.db.add(record)
        self.db.commit()

        # 9. Calcular oportunidades restantes
        remaining_after = max(0, limit - (played + 1))

        # 10. Construir partes del mensaje
        message_parts = self._build_trivia_vip_message_parts(
            is_correct, question, besitos, streak_message, remaining_after
        )

        # 11. Construir mensaje final
        message = self._build_trivia_vip_message(message_parts)

        logger.info(f"game_service - play_trivia_vip - {user_id} - correct:{is_correct}, streak:{new_streak}, besitos:{besitos}")

        # 12. Verificar si alcanzó un tier (pero NO generar código automáticamente)
        tier_info = None
        if is_correct and new_streak > 0:
            tier_info = self._get_streak_tier_info(user_id, new_streak)

        return {
            'correct': is_correct,
            'besitos': besitos,
            'previous_streak': previous_streak,
            'new_streak': new_streak,
            'streak_message': streak_message,
            'message': message,
            'message_parts': message_parts,
            'remaining_after': remaining_after,
            'limit_reached': False,
            'tier_info': tier_info
        }

    def _build_trivia_vip_message_parts(self, is_correct: bool, question: dict,
                                        besitos: int, streak_message: Optional[str],
                                        remaining: int) -> dict:
        """Construye las partes del mensaje de trivia VIP"""
        correct_letter = ["A", "B", "C", "D"][question['answer']]
        correct_answer_text = f"{correct_letter}) {question['opts'][question['answer']]}"

        if is_correct:
            header = self._select_template(self.TRIVIA_VIP_TEMPLATES['correct'])
        else:
            header_template = self._select_template(self.TRIVIA_VIP_TEMPLATES['incorrect'])
            header = header_template.format(correct_answer=correct_answer_text)

        result_text = None
        correct_answer = None

        reward_text = None
        if is_correct:
            reward_text = f"+{besitos} besitos 💋💋💋💋💋"

        streak_text = streak_message

        encouragement = None
        if remaining > 0:
            encouragement = f"Oportunidades VIP restantes: {remaining}"
        else:
            encouragement = "Ha agotado sus preguntas secretas por hoy."

        return {
            'header': header,
            'result_text': result_text,
            'correct_answer': correct_answer,
            'reward_text': reward_text,
            'streak_text': streak_text,
            'encouragement': encouragement
        }

    def _build_trivia_vip_message(self, parts: dict) -> str:
        """Construye mensaje final de trivia VIP"""
        lines = [parts['header']]
        if parts.get('reward_text'):
            lines.extend(['', parts['reward_text']])
        if parts.get('streak_text'):
            lines.extend(['', parts['streak_text']])
        if parts.get('encouragement'):
            lines.extend(['', parts['encouragement']])
        return '\n'.join(lines)

    def __del__(self):
        """Cierra la sesión"""
        self.close()