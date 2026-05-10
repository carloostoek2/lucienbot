# Phase 16: Trivias Tematicas - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 12
**Analogs found:** 10 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `services/game_service.py` | service | CRUD | Self-analog: VIP trivia methods (lines 757-1002) | exact |
| `services/trivia_service.py` | service | CRUD | `services/daily_gift_service.py` | role-match |
| `handlers/game_user_handlers.py` | handler | request-response | Self-analog: game_trivia_vip (lines 155-222) | exact |
| `handlers/trivia_admin_handlers.py` | handler | request-response | `handlers/admin_handlers.py` (lines 39-148) | exact |
| `keyboards/inline_keyboards.py` | utility | N/A | Self-analog: game_menu_keyboard line 424, trivia_vip_keyboard line 458 | exact |
| `models/models.py` | model | N/A | `DailyGiftConfig` ~line 946 | role-match |
| `services/__init__.py` | config | N/A | Existing imports pattern (entire file) | exact |
| `tests/services/test_trivia_service.py` | test | N/A | (No existing service test files found -- use RESEARCH.md patterns) | no-analog |
| `tests/handlers/test_trivia_handler.py` | test | N/A | (No existing handler test files found -- use RESEARCH.md patterns) | no-analog |
| `docs/preguntas_halloween.json` | config | N/A | `docs/preguntas_vip.json` | exact |
| `docs/preguntas_navidena.json` | config | N/A | `docs/preguntas_vip.json` | exact |

## Pattern Assignments

### `services/game_service.py` (service, CRUD) -- EXTEND

**Analog:** Self-analog -- VIP trivia methods within the same file (lines 757-1002)

**Imports pattern** (lines 1-18):
```python
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
```

**New class constants pattern** (lines 26-38, insert after existing constants):
```python
    # Limites trivia tematica
    DAILY_TRIVIA_TEMATICA_LIMIT_FREE = 5
    DAILY_TRIVIA_TEMATICA_LIMIT_VIP = 10

    # Recompensas
    TRIVIA_TEMATICA_WIN_BESITOS = 2
    TRIVIA_TEMATICA_VIP_WIN_BESITOS = 4

    # Hitos de racha: {streak: bonus_base}
    STREAK_MILESTONES = {3: 2, 5: 5, 7: 10, 10: 20}

    TRIVIA_TEMATICA_TEMPLATES = {
        # Same structure as TRIVIA_VIP_TEMPLATES (lines 163-201)
        # but with thematic flavor text
    }
```

**Init extension** (lines 203-209, add `self._tematica_questions = None`):
```python
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.besito_service = BesitoService(self.db)
        self._user_service = UserService(self.db)
        self._vip_service = VIPService(self.db)
        self._questions = None
        self._vip_questions = None
        self._tematica_questions = {}  # {category_id: [questions]}
```

**Load questions pattern** (lines 794-812, parameterized path):
```python
    def load_trivia_tematica_questions(self, category_id: str) -> list:
        """Carga preguntas tematicas de docs/preguntas_{category_id}.json"""
        if category_id in self._tematica_questions:
            return self._tematica_questions[category_id]

        questions_path = Path(f"docs/preguntas_{category_id}.json")
        if not questions_path.exists():
            logger.warning(f"Tematica questions file not found: {questions_path}")
            return []

        try:
            with open(questions_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._tematica_questions[category_id] = data if isinstance(data, list) else data.get('questions', [])
        except Exception as e:
            logger.error(f"Error loading tematica trivia questions: {e}")
            self._tematica_questions[category_id] = []

        return self._tematica_questions[category_id]
```

**Draw-without-repetition pattern** (lines 253-261, same pattern for 'trivia_tematica'):
```python
    def _get_today_tematica_trivia_records(self, user_id: int) -> list:
        """Obtiene registros de trivia tematica de hoy ordenados por tiempo DESC"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        records = self.db.query(GameRecord).filter(
            GameRecord.user_id == user_id,
            GameRecord.game_type == 'trivia_tematica',
            GameRecord.played_at >= today
        ).order_by(GameRecord.played_at.desc()).all()
        return records
```

**Draw-without-repetition: get random unanswered** (new, not in VIP -- answers already-answered filtering):
```python
    def _get_answered_today_indices(self, user_id: int, game_type: str) -> set:
        """Returns set of question indices already answered today for draw-without-repetition."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        records = self.db.query(GameRecord).filter(
            GameRecord.user_id == user_id,
            GameRecord.game_type == game_type,
            GameRecord.played_at >= today
        ).all()
        answered = set()
        prefix = "tematica_question_"  # matches result format in play
        for r in records:
            if r.result.startswith(prefix):
                # Extract index from result string: "tematica_question_3" -> 3
                answered.add(int(r.result.split("_")[-1]))
        return answered

    def get_random_tematica_question(self, user_id: int, category_id: str) -> Tuple[Optional[dict], int]:
        """Retorna pregunta tematica NO respondida hoy con indice."""
        questions = self.load_trivia_tematica_questions(category_id)
        if not questions:
            return None, -1

        answered = self._get_answered_today_indices(user_id, 'trivia_tematica')
        available = [(q, i) for i, q in enumerate(questions) if i not in answered]

        if not available:
            return None, -2  # -2 signals all answered (deck exhausted)

        return random.choice(available)
```

**Streak bonus pattern** (new, RESEARCH.md pattern):
```python
    def _check_streak_milestone(self, new_streak: int, is_vip: bool = False) -> Optional[int]:
        """Returns bonus besitos if streak milestone reached, else None."""
        bonus = self.STREAK_MILESTONES.get(new_streak)
        if bonus is not None:
            return bonus * 2 if is_vip else bonus
        return None
```

**Play method** (mirror play_trivia_vip lines 867-954, add streak bonus step):
```python
    def play_trivia_tematica(self, user_id: int, question_idx: int, answer_idx: int,
                             category_id: str) -> Dict[str, Any]:
        """
        Procesa respuesta de trivia tematica con sistema de rachas + hitos de bonus.
        Returns: {correct, besitos, previous_streak, new_streak, streak_message,
                 streak_bonus, message, message_parts, remaining_after, limit_reached}
        """
        # 1. Verificar limites (same pattern as play_trivia_vip step 1)
        can_play, played, limit, limit_msg = self.can_play(user_id, 'trivia_tematica')
        if not can_play:
            return {
                'correct': False, 'besitos': 0,
                'previous_streak': 0, 'new_streak': 0,
                'streak_message': None, 'streak_bonus': 0,
                'message': limit_msg, 'message_parts': {},
                'remaining_after': 0, 'limit_reached': True
            }

        # 2. Obtener pregunta
        question = self.get_question_by_index(question_idx)  # Uses loaded tematica questions
        if not question:
            return {
                'correct': False, 'besitos': 0,
                'previous_streak': 0, 'new_streak': 0,
                'streak_message': None, 'streak_bonus': 0,
                'message': "Pregunta no encontrada.", 'message_parts': {},
                'remaining_after': max(0, limit - played), 'limit_reached': False
            }

        # 3. Obtener racha previa (same pattern as VIP line 894)
        previous_streak = self._get_tematica_trivia_streak(user_id)

        # 4. Verificar respuesta (same as VIP line 897)
        is_correct = self.check_trivia_answer(question, answer_idx)

        # 5. Calcular nueva racha (same as VIP lines 900-903)
        if is_correct:
            new_streak = previous_streak + 1
        else:
            new_streak = 0

        # 6. Obtener mensaje de racha (same as VIP lines 906-908)
        streak_message = None
        if is_correct:
            streak_message = self._get_streak_message(new_streak)

        # 7. Acreditar besitos si correcto (same pattern as VIP lines 910-919)
        besitos = 0
        if is_correct:
            is_vip = self.is_user_vip(user_id)
            besitos = self.TRIVIA_TEMATICA_VIP_WIN_BESITOS if is_vip else self.TRIVIA_TEMATICA_WIN_BESITOS
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=besitos,
                source=TransactionSource.TRIVIA,
                description=f"Victoria en trivia tematica (racha: {new_streak})"
            )

        # 7b. Streak milestone bonus (NEW: not in VIP pattern)
        streak_bonus = 0
        if is_correct and new_streak in self.STREAK_MILESTONES:
            bonus = self.STREAK_MILESTONES[new_streak]
            streak_bonus = bonus * 2 if self.is_user_vip(user_id) else bonus
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=streak_bonus,
                source=TransactionSource.TRIVIA,
                description=f"Bonus por racha de {new_streak} en trivia tematica"
            )

        # 8. Registrar jugada (same pattern as VIP lines 921-929)
        record = GameRecord(
            user_id=user_id,
            game_type='trivia_tematica',
            result=f"tematica_question_{question_idx}",
            payout=besitos + streak_bonus
        )
        self.db.add(record)
        self.db.commit()

        # 9-11. Same as VIP lines 931-954
        remaining_after = max(0, limit - (played + 1))
        message_parts = self._build_trivia_tematica_message_parts(
            is_correct, question, besitos, streak_bonus, streak_message, remaining_after
        )
        message = self._build_trivia_tematica_message(message_parts)

        return {
            'correct': is_correct, 'besitos': besitos,
            'previous_streak': previous_streak, 'new_streak': new_streak,
            'streak_message': streak_message, 'streak_bonus': streak_bonus,
            'message': message, 'message_parts': message_parts,
            'remaining_after': remaining_after, 'limit_reached': False
        }
```

**Streak helper for tematica** (mirror _get_vip_trivia_streak lines 767-776):
```python
    def _get_tematica_trivia_streak(self, user_id: int) -> int:
        """Calcula racha actual en trivia tematica (solo hoy)"""
        records = self._get_today_tematica_trivia_records(user_id)
        streak = 0
        for record in records:
            if record.payout > 0:
                streak += 1
            else:
                break
        return streak
```

**Entry data method** (mirror get_trivia_vip_entry_data lines 836-865):
```python
    def get_trivia_tematica_entry_data(self, user_id: int) -> dict:
        """Obtiene datos enriquecidos para entrada de trivia tematica"""
        limits = self.get_daily_limits(user_id)
        played = len(self._get_today_tematica_trivia_records(user_id))
        remaining = max(0, limits['trivia_tematica_limit'] - played)
        streak = self._get_tematica_trivia_streak(user_id)

        can_play = remaining > 0
        limit_message = None
        if not can_play:
            limit_message = self._select_template(self.TRIVIA_TEMATICA_TEMPLATES['limit_reached'])

        return {
            'title': self._select_template(self.TRIVIA_TEMATICA_TEMPLATES['entry_title']),
            'intro': self._select_template(self.TRIVIA_TEMATICA_TEMPLATES['entry_intro']),
            'counter_template': self._select_template(self.TRIVIA_TEMATICA_TEMPLATES['counter']),
            'remaining': remaining,
            'limit': limits['trivia_tematica_limit'],
            'current_streak': streak,
            'is_vip': self.is_user_vip(user_id),
            'can_play': can_play,
            'limit_message': limit_message
        }
```

---

### `services/trivia_service.py` (service, CRUD) -- NEW

**Analog:** `services/daily_gift_service.py` (lines 1-198)

**Rationale:** DailyGiftService manages config-state (active/inactive, amounts) persisted in a DB model with a singleton config row. TriviaCategoryService manages active category state in the same way.

**Imports** (mirror daily_gift_service.py lines 1-14):
```python
"""
Servicio de Trivias Tematicas - Lucien Bot

Gestiona categorias tematicas de trivia: activacion, desactivacion,
descubrimiento de archivos JSON y consulta de estado.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session
from models.database import SessionLocal
from models.models import TriviaCategory  # NEW model

logger = logging.getLogger(__name__)
```

**Service class pattern** (mirror DailyGiftService init pattern lines 20-36):
```python
class TriviaCategoryService:
    """Servicio para gestion del estado de categorias tematicas de trivia."""

    QUESTIONS_DIR = Path("docs")

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        if self._owns_session and self.db:
            self.db.close()
            self.db = None
```

**Category discovery pattern** (mirror load_trivia_vip_questions but listing files):
```python
    def discover_categories(self) -> List[dict]:
        """Enumera archivos preguntas_*.json disponibles en docs/."""
        categories = []
        for f in self.QUESTIONS_DIR.glob("preguntas_*.json"):
            # Skip vip and general
            if f.stem in ("preguntas", "preguntas_vip"):
                continue
            display_name = self._derive_display_name(f.stem)
            categories.append({
                'file_name': f.name,
                'category_id': f.stem.replace("preguntas_", ""),
                'display_name': display_name,
                'question_count': self._count_questions(f)
            })
        return categories

    def _derive_display_name(self, stem: str) -> str:
        """Derives display name from file stem, e.g. preguntas_halloween -> '🎃 Trivia de Halloween'."""
        mapping = {
            "preguntas_halloween": "🎃 Trivia de Halloween",
            "preguntas_navidena": "❄️ Trivia Navidena",
        }
        return mapping.get(stem, stem.replace("preguntas_", "").replace("_", " ").title())

    def _count_questions(self, path: Path) -> int:
        """Counts questions in a JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return len(data) if isinstance(data, list) else len(data.get('questions', []))
        except Exception:
            return 0
```

**State management pattern** (similar to DailyGiftService `get_config`/`update_config`):
```python
    def get_active_category(self) -> Optional[dict]:
        """Obtiene la categoria activa actual, o None si no hay ninguna."""
        db = self._get_db()
        cat = db.query(TriviaCategory).filter(TriviaCategory.is_active == True).first()
        if not cat:
            return None
        return {
            'id': cat.id,
            'category_id': cat.category_id,
            'display_name': cat.display_name,
            'activated_at': cat.activated_at,
            'scheduled_end': cat.scheduled_end
        }

    def activate(self, category_id: str, display_name: str = None,
                 scheduled_end: datetime = None) -> bool:
        """Activa una categoria (desactiva cualquier otra activa primero)."""
        db = self._get_db()
        try:
            # Desactivar cualquier categoria activa (D-06: solo una a la vez)
            db.query(TriviaCategory).filter(TriviaCategory.is_active == True).update(
                {"is_active": False}
            )
            # Activar o crear la nueva
            cat = db.query(TriviaCategory).filter(
                TriviaCategory.category_id == category_id
            ).first()
            if cat:
                cat.is_active = True
                cat.display_name = display_name or cat.display_name
                cat.activated_at = datetime.utcnow()
                cat.scheduled_end = scheduled_end
            else:
                cat = TriviaCategory(
                    category_id=category_id,
                    display_name=display_name or category_id,
                    is_active=True,
                    activated_at=datetime.utcnow(),
                    scheduled_end=scheduled_end
                )
                db.add(cat)
            db.commit()
            logger.info(f"Categoria activada: {category_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error activando categoria: {e}")
            return False

    def deactivate(self, category_id: str = None) -> bool:
        """Desactiva una categoria o la activa si no se especifica."""
        db = self._get_db()
        try:
            query = db.query(TriviaCategory).filter(TriviaCategory.is_active == True)
            if category_id:
                query = query.filter(TriviaCategory.category_id == category_id)
            query.update({"is_active": False, "scheduled_end": None})
            db.commit()
            logger.info(f"Categoria desactivada: {category_id or 'todas'}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error desactivando categoria: {e}")
            return False
```

---

### `handlers/game_user_handlers.py` (handler, request-response) -- EXTEND

**Analog:** Self-analog -- game_trivia_vip (lines 155-202) and trivia_vip_answer (lines 205-222)

**Import additions** (extend lines 10-17):
```python
from keyboards.inline_keyboards import (
    game_menu_keyboard,
    dice_play_keyboard,
    trivia_keyboard,
    trivia_vip_keyboard,
    trivia_vip_result_keyboard,
    trivia_tematica_keyboard,        # NEW
    trivia_tematica_result_keyboard  # NEW
)
from services import get_service, GameService
# NOTE: Handler does NOT import TriviaCategoryService.
# Category info is obtained via GameService.get_active_tematica_info().
```

**game_trivia_tematica handler** (mirror game_trivia_vip lines 155-202):
```python
@router.callback_query(lambda c: c.data == "game_trivia_tematica")
async def game_trivia_tematica(callback: CallbackQuery):
    """Inicia trivia tematica con pregunta aleatoria de la categoria activa"""
    user_id = callback.from_user.id

    with get_service(GameService) as service:
        # 1. Obtener categoria activa via GameService (NOT TriviaCategoryService directly)
        tematica_info = service.get_active_tematica_info()
        if not tematica_info:
            await callback.message.edit_text(
                "No hay dinamicas tematicas activas en este momento.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        category_id = tematica_info['category_id']
        data = service.get_trivia_tematica_entry_data(user_id)

        if not data['can_play']:
            await callback.message.edit_text(
                data['limit_message'],
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        question, question_idx = service.get_random_tematica_question(user_id, category_id)

        if question is None or question_idx == -1:
            await callback.message.edit_text(
                "Los pergaminos tematicos estan en el taller de Lucien. Regresa mas tarde.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        if question_idx == -2:  # All answered today -- deck exhausted
            await callback.message.edit_text(
                "Has respondido todas las preguntas tematicas de hoy. "
                "El conocimiento se renueva manana.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

    # Build message outside service context (data and question are plain values)
    counter_text = data['counter_template'].format(
        remaining=data['remaining'],
        limit=data['limit']
    )

    streak_text = ""
    if data['current_streak'] > 0:
        streak_text = f"\n🔥 Tu racha tematica: {data['current_streak']}"

    text = (
        f"<b>{data['title']}</b>{streak_text}\n\n"
        f"{data['intro']}\n\n"
        f"<i>{counter_text}</i>\n\n"
        f"🎭 <b>Pregunta Tematica:</b> {question['q']}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=trivia_tematica_keyboard(question, question_idx)
    )
    await callback.answer()
    logger.info(f"game_user_handlers - game_trivia_tematica - {user_id} - shown - category:{category_id}")


@router.callback_query(lambda c: c.data.startswith("trivia_tematica_answer_"))
async def trivia_tematica_answer(callback: CallbackQuery):
    """Procesa respuesta de trivia tematica"""
    user_id = callback.from_user.id

    # Format: trivia_tematica_answer_{answer_idx}_{question_idx}
    parts = callback.data.split("_")
    answer_idx = int(parts[3])
    question_idx = int(parts[4])

    with get_service(GameService) as service:
        # Get active category via GameService (NOT TriviaCategoryService directly)
        tematica_info = service.get_active_tematica_info()
        category_id = tematica_info['category_id'] if tematica_info else None
        result = service.play_trivia_tematica(user_id, question_idx, answer_idx, category_id)

    await callback.message.edit_text(
        result['message'],
        reply_markup=trivia_tematica_result_keyboard()
    )
    await callback.answer()
    logger.info(f"game_user_handlers - trivia_tematica_answer - {user_id} - correct:{result['correct']}, besitos:{result['besitos']}, bonus:{result['streak_bonus']}")
```

---

### `handlers/trivia_admin_handlers.py` (handler, request-response) -- NEW

**Analog:** `handlers/admin_handlers.py` (lines 1-148)

**Imports pattern** (mirror admin_handlers.py lines 1-20):
```python
"""
Handlers de Administracion de Trivias Tematicas - Lucien Bot

Handlers para gestion de categorias de trivia desde el panel admin.
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import bot_config
from keyboards.inline_keyboards import back_keyboard
from services.trivia_service import TriviaCategoryService
from services import get_service

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS
```

**Admin section handler** (mirror admin_channels pattern lines 45-55):
```python
@router.callback_query(F.data == "admin_trivia_categories", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_categories_menu(callback: CallbackQuery):
    """Menu principal de gestion de categorias de trivia."""
    with get_service(TriviaCategoryService) as service:
        categories = service.discover_categories()
        active = service.get_active_category()

    text = "🎯 <b>Mazos de Trivia</b>\n\n"
    if active:
        text += f"✨ <b>Activa:</b> {active['display_name']}\n"
    else:
        text += "📭 <b>Sin categoria activa.</b> Usando mazo general.\n\n"

    buttons = []
    for cat in categories:
        is_active = active and active['category_id'] == cat['category_id']
        btn_text = f"{'✅ ' if is_active else ''}{cat['display_name']} ({cat['question_count']} preg.)"
        callback = f"trivia_cat_activate_{cat['category_id']}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=callback)])

    if active:
        buttons.append([InlineKeyboardButton(
            text="⛔ Desactivar categoria",
            callback_data="trivia_cat_deactivate"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Panel de administracion",
        callback_data="back_to_admin"
    )])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()
```

**Activation handler** (mirror admin_handlers pattern for callback routing):
```python
@router.callback_query(F.data.startswith("trivia_cat_activate_"), lambda cb: is_admin(cb.from_user.id))
async def trivia_category_activate(callback: CallbackQuery):
    """Activa una categoria tematica."""
    category_id = callback.data.replace("trivia_cat_activate_", "")
    with get_service(TriviaCategoryService) as service:
        service.activate(category_id)
    await callback.answer(f"Categoria activada: {category_id}", show_alert=True)
    # Refresh menu
    await admin_trivia_categories_menu(callback)


@router.callback_query(F.data == "trivia_cat_deactivate", lambda cb: is_admin(cb.from_user.id))
async def trivia_category_deactivate(callback: CallbackQuery):
    """Desactiva la categoria activa."""
    with get_service(TriviaCategoryService) as service:
        service.deactivate()
    await callback.answer("Categoria desactivada.", show_alert=True)
    await admin_trivia_categories_menu(callback)
```

---

### `keyboards/inline_keyboards.py` (utility, N/A) -- EXTEND

**Analog:** Self-analog -- game_menu_keyboard (lines 424-431), trivia_vip_keyboard (lines 458-470), trivia_vip_result_keyboard (lines 473-479)

**game_menu_keyboard extended** (replace lines 424-431):
```python
def game_menu_keyboard(is_vip: bool = False, tematica_button: Optional[tuple] = None) -> InlineKeyboardMarkup:
    """Menu de seleccion de juegos. Si tematica_button = (label, callback), anade boton extra."""
    buttons = [
        [InlineKeyboardButton(text="🎲 Lanzar los dados del destino", callback_data="game_dice")],
        [InlineKeyboardButton(text="❓ El examen de Diana", callback_data="game_trivia")],
    ]
    if tematica_button:
        label, callback = tematica_button
        # Insert as second button, before Volver
        buttons.insert(1, [InlineKeyboardButton(text=label, callback_data=callback)])
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

**New trivia_tematica_keyboard** (mirror trivia_vip_keyboard lines 458-470):
```python
def trivia_tematica_keyboard(question: dict, question_idx: int) -> InlineKeyboardMarkup:
    """Teclado con opciones de trivia tematica."""
    buttons = []
    for idx, opt_text in enumerate(question['opts']):
        buttons.append([InlineKeyboardButton(
            text=opt_text,
            callback_data=f"trivia_tematica_answer_{idx}_{question_idx}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver al menu de juegos",
        callback_data="game_menu"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

**New trivia_tematica_result_keyboard** (mirror trivia_vip_result_keyboard lines 473-479):
```python
def trivia_tematica_result_keyboard() -> InlineKeyboardMarkup:
    """Teclado para resultado de trivia tematica."""
    buttons = [
        [InlineKeyboardButton(text="🔄 Otra pregunta", callback_data="game_trivia_tematica")],
        [InlineKeyboardButton(text="🔙 Menu de juegos", callback_data="game_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

---

### `models/models.py` (model, N/A) -- EXTEND

**Analog:** DailyGiftConfig model (for singleton config pattern)

**New TriviaCategory model** (insert near GameRecord ~line 1098):
```python
class TriviaCategory(Base):
    """Estado de categorias tematicas de trivia."""
    __tablename__ = "trivia_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(String(50), unique=True, nullable=False)  # e.g. "halloween"
    display_name = Column(String(100), nullable=True)  # e.g. "🎃 Trivia de Halloween"
    is_active = Column(Boolean, default=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

### `services/__init__.py` (config, N/A) -- EXTEND

**Analog:** Existing imports within same file

**Additions** (insert after line 18, in alphabetical order by phase):
```python
# Fase 16 - Trivias Tematicas
from .trivia_service import TriviaCategoryService
```

**Add to __all__** (insert after 'StoreService'):
```python
    'TriviaCategoryService',
```

---

## Shared Patterns

### Service access with context manager
**Source:** `services/__init__.py` lines 36-68
**Apply to:** All handler files
```python
# Pattern for any handler accessing a service
with get_service(GameService) as service:
    data = service.get_menu_data(user_id)
```

### Service DB session management
**Source:** `services/daily_gift_service.py` lines 22-36
**Apply to:** `services/trivia_service.py`
```python
class TriviaCategoryService:
    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        if self._owns_session and self.db:
            self.db.close()
            self.db = None
```

### Admin authentication guard
**Source:** `handlers/admin_handlers.py` lines 39-40
**Apply to:** `handlers/trivia_admin_handlers.py`
```python
def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS

# Used as filter on every admin handler:
@router.callback_query(F.data == "admin_trivia_categories", lambda cb: is_admin(cb.from_user.id))
```

### Logging pattern
**Source:** Throughout all handlers and services
**Apply to:** All files
```python
logger.info(f"module - method - {user_id} - action:result")
```

### JSON question loading
**Source:** `services/game_service.py` lines 575-593
**Apply to:** `services/game_service.py` (tematica loading)
```python
questions_path = Path("docs/preguntas_vip.json")
if not questions_path.exists():
    logger.warning("Questions file not found: docs/preguntas_vip.json")
    return []
try:
    with open(questions_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        self._vip_questions = data if isinstance(data, list) else data.get('questions', [])
except Exception as e:
    logger.error(f"Error loading VIP trivia questions: {e}")
    self._vip_questions = []
```

### Daily limit tracking
**Source:** `services/game_service.py` lines 253-261, 355-362
**Apply to:** Thematic trivia daily limits (reuse `get_today_play_count(user_id, 'trivia_tematica')`)
```python
today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
records = self.db.query(GameRecord).filter(
    GameRecord.user_id == user_id,
    GameRecord.game_type == 'trivia_vip',
    GameRecord.played_at >= today
).order_by(GameRecord.played_at.desc()).all()
```

### Streak calculation
**Source:** `services/game_service.py` lines 263-272
**Apply to:** Tematica streak (same algorithm, different game_type)
```python
def _get_trivia_streak(self, user_id: int) -> int:
    records = self._get_today_trivia_records(user_id)
    streak = 0
    for record in records:
        if record.payout > 0:
            streak += 1
        else:
            break
    return streak
```

### Message construction with Lucien voice
**Source:** `handlers/game_user_handlers.py` lines 32-42
**Apply to:** Tematica handler messages
```python
text = (
    f"🎩 Lucien: <b>{data['title']}</b>\n\n"
    f"{data['subtitle']}\n\n"
    f"<b>Trivia:</b> {data['trivia_description']}\n"
    f"<i>{data['remaining_trivia']} de {data['limit_trivia']} disponibles</i>\n\n"
    f"{data['footer']}"
)
```

### Scheduled activation (APScheduler DateTrigger)
**Source:** `services/scheduler_service.py` lines 298-313
**Apply to:** Scheduled category activation/deactivation
```python
def schedule_free_welcome(self, user_id: int, channel_id: int):
    job_id = f"free_welcome_{user_id}_{channel_id}"
    run_date = datetime.now(timezone.utc) + timedelta(seconds=30)
    self._scheduler.add_job(
        _send_free_welcome_job,
        trigger=DateTrigger(run_date=run_date),
        id=job_id,
        replace_existing=True,
        kwargs={"user_id": user_id, "channel_id": channel_id},
    )
```

### Admin menu keyboard button pattern
**Source:** `keyboards/inline_keyboards.py` lines 79-119
**Apply to:** Adding "Mazos de Trivia" button to admin_menu_keyboard
```python
[InlineKeyboardButton(
    text="🎯 Mazos de Trivia",
    callback_data="admin_trivia_categories"
)],
```

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/services/test_trivia_service.py` | test | N/A | No existing service test files found in codebase |
| `tests/handlers/test_trivia_handler.py` | test | N/A | No existing handler test files found in codebase |

**For test files:** Use standard pytest + pytest-asyncio patterns. RESEARCH.md specifies tests should verify: category activation persistence, draw-without-repetition logic, streak milestone bonuses, and no-stacking edge case. See `tests/unit/` pycache files for naming conventions.

## Metadata

**Analog search scope:** `services/`, `handlers/`, `keyboards/`, `models/`, `models/CLAUDE.md`, `handlers/CLAUDE.md`, `services/CLAUDE.md`
**Files scanned:** 12 (6 existing code files read in full or in targeted sections)
**Pattern extraction date:** 2026-05-09
