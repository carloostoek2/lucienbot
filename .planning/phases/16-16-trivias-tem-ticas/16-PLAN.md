---
wave: 1
depends_on: []
files_modified:
  - models/models.py
  - alembic/versions/20260509_add_trivia_categories.py
  - services/trivia_service.py
  - services/__init__.py
  - services/game_service.py
  - handlers/game_user_handlers.py
  - handlers/trivia_admin_handlers.py
  - handlers/__init__.py
  - bot.py
  - keyboards/inline_keyboards.py
  - docs/preguntas_halloween.json
  - docs/preguntas_navidena.json
autonomous: false
requirements:
  - TRIVIA-01: TriviaCategory DB model + Alembic migration
  - TRIVIA-02: TriviaCategoryService with discover/activate/deactivate/get_active
  - TRIVIA-03: GameService extension — thematic trivia methods (load, draw-wo-repetition, play, streak)
  - TRIVIA-04: Streak milestone bonuses for normal + VIP + thematic trivia
  - TRIVIA-05: User-facing handlers (game_trivia_tematica, trivia_tematica_answer)
  - TRIVIA-06: Admin handlers (admin_trivia_categories_menu, activate, deactivate)
  - TRIVIA-07: Dynamic game_menu keyboard with optional thematic button
  - TRIVIA-08: Example question files (Halloween, Navidad)
must_haves:
  truths:
    - "TriviaCategory DB model persists active category state (TRIVIA-01)"
    - "TriviaCategoryService manages category discovery, activation, deactivation (TRIVIA-02)"
    - "GameService extends with thematic trivia methods mirroring VIP pattern (TRIVIA-03)"
    - "Streak milestone bonuses apply uniformly to all trivia types (TRIVIA-04)"
    - "Only one thematic category active at a time; activating new deactivates previous (D-06)"
    - "User-facing handlers use exactly 1 service (GameService), not TriviaCategoryService directly"
  artifacts:
    - "models/models.py: TriviaCategory model"
    - "services/trivia_service.py: TriviaCategoryService"
    - "handlers/trivia_admin_handlers.py: admin category management router"
    - "docs/preguntas_halloween.json: example thematic questions"
    - "docs/preguntas_navidena.json: example thematic questions"
    - "tests/unit/test_trivia_service.py: Wave 0 test stubs"
    - "tests/integration/test_trivia_handler.py: Wave 0 test stubs"
  key_links:
    - "admin_menu -> Mazos de Trivia -> activate/deactivate category UI"
    - "game_menu -> optional thematic trivia button (when category active)"
    - "trivia_tematica_answer -> GameService.play_trivia_tematica() -> GameRecord"
    - "GameService.get_active_tematica_info() -> TriviaCategoryService.get_active_category()"
---

# Plan 16: Trivias Temáticas

**Objective:** Extend the existing trivia system (Phase 14) with thematic question categories managed via JSON files, per-user draw-without-repetition decks that reset daily, streak milestone bonuses (3/5/7/10 correct answers), and an admin interface for category activation/deactivation.

**Context:** The existing trivia system in `GameService` provides complete templates (VIP trivia methods at lines 757-1002) for adding a new game_type. `GameRecord.game_type` is `String(20)` -- no migration needed for the new `'trivia_tematica'` value. `TransactionSource.TRIVIA` already exists and is reused. All 15 user decisions (D-01 through D-15) in CONTEXT.md are LOCKED and NON-NEGOTIABLE.

---

## Threat Model

### Trust Boundaries
1. **Admin boundary:** Only `bot_config.ADMIN_IDS` members can access `/admin` panel and activate/deactivate categories
2. **User boundary:** Any Telegram user can play thematic trivia (no auth gate beyond Telegram ID)
3. **File system boundary:** JSON question files in `docs/` are read by the service; admin cannot write them from the bot (D-15)
4. **DB boundary:** `TriviaCategory` table stores active category state; writes are admin-triggered

### STRIDE Threat Register

| ID | Threat | STRIDE Category | Mitigation |
|----|--------|----------------|------------|
| T-16-01 | Non-admin user accesses category management callback data | Elevation of Privilege | `is_admin()` check via `lambda cb: is_admin(cb.from_user.id)` on ALL admin callback handlers |
| T-16-02 | Malformed callback data `trivia_tematica_answer_{idx}_{qidx}` with out-of-bounds indices | Tampering | Validate `answer_idx` is 0-3 (max 4 options per question); validate `question_idx` is within loaded questions list |
| T-16-03 | Concurrent category state writes (two admins activate different categories simultaneously) | Tampering | Category activation in DB transaction -- deactivate all then activate one atomically |
| T-16-04 | Category JSON file missing or corrupt causes 500 errors | Denial of Service | Graceful file-not-found handling with user-friendly LucienVoice message; `try/except` on JSON parse |
| T-16-05 | Streak bonus stacking (milestones 3,5,7,10 all fire on streak=10) | Information Disclosure (balance inflation) | Only award bonus when `new_streak` EXACTLY equals the milestone value; track awarded milestones in DB to prevent double-awarding |
| T-16-06 | Category cache staleness after admin switches category | Tampering | `_tematica_questions` is keyed by `category_id`; switching categories loads the new file by key |

---

## Waves

### Wave 1 — Foundation (models, migration, trivia service)
Tasks T1–T4. No dependencies between them. Must complete before Wave 2.

### Wave 2 — GameService Extension
Tasks T5–T9. Depend on Wave 1 (TriviaCategory model must exist for GameService imports). Sequential within wave (each task builds on the previous).

### Wave 3 — Handlers
Tasks T10–T13. Depend on Wave 2 (service methods must exist for handlers to call). Tasks T10 and T11 are independent of each other. T12 depends on T10 and T13 (keyboard function). T13 depends on Wave 2.

### Wave 4 — Integration & Data
Tasks T14–T15. T14 depends on Wave 3 (router must exist). T15 is independent.

### Wave 5 — Verification
Task T16. Manual verification and full test suite run. Requires visual Telegram UI check for admin button flow and game menu dynamic button.

---

## Tasks

### Wave 1: Foundation

#### Task 1: Add TriviaCategory model to models/models.py

**Objective:** Define the `TriviaCategory` SQLAlchemy model for persisting active category state, following the `DailyGiftConfig` singleton config pattern.

**Requirements:** TRIVIA-01

**Verification:**
- Model is importable: `python3 -c "from models.models import TriviaCategory; print(TriviaCategory.__tablename__)"` prints `trivia_categories`
- Columns exist: `category_id` (String(50), unique), `display_name` (String(100)), `is_active` (Boolean), `activated_at` (DateTime), `scheduled_end` (DateTime), `created_at` (DateTime, server_default)
- No relationships to other tables (standalone config model)

**Files:**
- MODIFY: `models/models.py` — insert after GameRecord class (~line 1099)

**Threat references:** T-16-03

<read_first>
- models/models.py (lines 1089-1099 — GameRecord model for placement reference)
- models/models.py (lines 940-960 — DailyGiftConfig model for singleton config pattern)
- models/CLAUDE.md — model conventions
</read_first>

<action>
Insert the following class after the GameRecord class closing (after line 1099 in models/models.py, before the end-of-file):

```python
class TriviaCategory(Base):
    """Estado de categorias tematicas de trivia."""
    __tablename__ = "trivia_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

Do NOT add it to `__all__` or any module-level exports -- models are accessed via `from models.models import TriviaCategory`.
</action>

<acceptance_criteria>
1. `grep -n "class TriviaCategory" models/models.py` returns a line number > 1099
2. `grep -n "trivia_categories" models/models.py` matches exactly one line (the `__tablename__`)
3. `grep -c "category_id = Column" models/models.py | tail -1` — verify the model has a `category_id` column of type String(50)
</acceptance_criteria>

<verify>
<automated>
python3 -c "from models.models import TriviaCategory; print(TriviaCategory.__tablename__)"
</automated>
</verify>

---

#### Task 2: Create Alembic migration for trivia_categories table

**Objective:** Generate an Alembic migration that creates the `trivia_categories` table in PostgreSQL/SQLite.

**Requirements:** TRIVIA-01

**Verification:**
- Migration file exists with a descriptive name
- Running `alembic upgrade head` succeeds on SQLite dev DB
- Running `alembic downgrade -1` succeeds (table is dropped)
- Migration depends on the current head: `20250407_add_game_and_anon_enum`

**Files:**
- CREATE: `alembic/versions/20260509_add_trivia_categories_table.py`
- MODIFY: None (migration is self-contained)

**Threat references:** None

<read_first>
- alembic/versions/20250407_add_game_and_anon_enum.py — template for migration structure, revision format, dialect handling
- alembic/versions/c32861733e54_add_game_records_table_for_minijuegos.py — template for table creation migration
- models/models.py (the new TriviaCategory model from Task 1)
- models/CLAUDE.md — alembic rules (Enum-First, idempotency, dialect checks)
</read_first>

<action>
1. Run: `cd /home/ubuntu/repos/lucienbot && python3 -m alembic revision -m "add_trivia_categories_table"`
2. Rename the generated file to `20260509_add_trivia_categories_table.py` (or use the date-prefixed format)
3. Edit the migration file:
   - Set `revision: str = '20260509_add_trivia_categories'` (shorter ID for readability)
   - Set `down_revision: Union[str, None] = '20250407_add_game_and_anon_enum'`
   - In `upgrade()`: create `trivia_categories` table with columns matching the model
   - In `downgrade()`: drop `trivia_categories` table
   - Use dialect-agnostic approach: `op.create_table()` works for both PostgreSQL and SQLite
</action>

<acceptance_criteria>
1. `ls alembic/versions/20260509_add_trivia_categories_table.py` returns the file path
2. `python3 -m alembic upgrade head` exits with code 0
3. `python3 -m alembic downgrade -1` exits with code 0
4. `sqlite3 lucien_dev.db ".schema trivia_categories"` shows the table schema with columns: id, category_id, display_name, is_active, activated_at, scheduled_end, created_at
5. `python3 -m alembic upgrade head` again (re-upgrade) exits with code 0 (idempotent)
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -m alembic upgrade head && python3 -m alembic downgrade -1 && python3 -m alembic upgrade head
</automated>
</verify>

---

#### Task 3: Create TriviaCategoryService in services/trivia_service.py

**Objective:** Create the admin-facing service for discovering available category JSON files, querying active category state, and activating/deactivating categories.

**Requirements:** TRIVIA-02

**Verification:**
- `python3 -c "from services.trivia_service import TriviaCategoryService"` succeeds
- Service has methods: `discover_categories()`, `get_active_category()`, `activate(category_id, display_name, scheduled_end)`, `deactivate(category_id)`, `close()`
- DB session management follows project pattern (`_owns_session` flag, `_get_db()` lazy init, `close()` method)
- Activating a category first deactivates all others (D-06: only one active at a time)

**Files:**
- CREATE: `services/trivia_service.py`
- MODIFY: None

**Threat references:** T-16-03, T-16-04

<read_first>
- services/daily_gift_service.py (full file — singleton config service pattern for DB session management and state queries)
- services/game_service.py (lines 1-20 — imports, logging setup)
- services/__init__.py (lines 36-68 — `get_service` context manager and `_ServiceContext` class)
- models/models.py (the new TriviaCategory model)
- models/CLAUDE.md — access to DB via ORM
- services/CLAUDE.md — service rules
</read_first>

<action>
Create `services/trivia_service.py` with the following class:

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
from models.models import TriviaCategory

logger = logging.getLogger(__name__)


class TriviaCategoryService:
    """Servicio para gestion del estado de categorias tematicas de trivia."""

    QUESTIONS_DIR = Path("docs")

    # Mapping from file stem to display name
    DISPLAY_NAME_MAP = {
        "preguntas_halloween": "🎃 Trivia de Halloween",
        "preguntas_navidena": "❄️ Trivia Navidena",
    }

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

    def discover_categories(self) -> List[dict]:
        """Enumera archivos preguntas_*.json disponibles en docs/.
        Returns list of {category_id, display_name, question_count, file_name}."""
        categories = []
        for f in self.QUESTIONS_DIR.glob("preguntas_*.json"):
            if f.stem in ("preguntas", "preguntas_vip"):
                continue
            category_id = f.stem.replace("preguntas_", "")
            display_name = self.DISPLAY_NAME_MAP.get(
                f.stem, f.stem.replace("preguntas_", "").replace("_", " ").title()
            )
            categories.append({
                'file_name': f.name,
                'category_id': category_id,
                'display_name': display_name,
                'question_count': self._count_questions(f)
            })
        logger.info(f"trivia_category_service - discover_categories - found {len(categories)} categories")
        return categories

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
        """Activa una categoria (desactiva cualquier otra activa primero). D-06."""
        db = self._get_db()
        try:
            db.query(TriviaCategory).filter(TriviaCategory.is_active == True).update(
                {"is_active": False, "scheduled_end": None}
            )
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
            logger.info(f"trivia_category_service - activate - category_id:{category_id} - activated")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"trivia_category_service - activate - error:{e}")
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
            logger.info(f"trivia_category_service - deactivate - category_id:{category_id or 'all_active'} - deactivated")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"trivia_category_service - deactivate - error:{e}")
            return False

    def _count_questions(self, path: Path) -> int:
        """Cuenta preguntas en un archivo JSON."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return len(data) if isinstance(data, list) else len(data.get('questions', []))
        except Exception as e:
            logger.warning(f"trivia_category_service - _count_questions - error reading {path}: {e}")
            return 0
```

Each method MUST be <= 50 lines. The `activate()` method at ~46 lines is within limit.
</action>

<acceptance_criteria>
1. `python3 -c "from services.trivia_service import TriviaCategoryService; print('OK')"` prints `OK`
2. `grep -c "def " services/trivia_service.py` returns >= 7 (methods: __init__, _get_db, close, discover_categories, get_active_category, activate, deactivate, _count_questions)
3. `grep "class TriviaCategoryService" services/trivia_service.py` returns exactly one match
4. `python3 -c "from services.trivia_service import TriviaCategoryService; s = TriviaCategoryService(); print(type(s._owns_session)); s.close()"` prints `<class 'bool'>` with no errors
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "from services.trivia_service import TriviaCategoryService; s = TriviaCategoryService(); print(type(s._owns_session)); s.close()"
</automated>
</verify>

---

#### Task 4: Register TriviaCategoryService in services/__init__.py

**Objective:** Add TriviaCategoryService import and __all__ entry so it is accessible via the `get_service()` context manager.

**Requirements:** TRIVIA-02

**Verification:**
- `python3 -c "from services import TriviaCategoryService, get_service; print('OK')"` prints `OK`

**Files:**
- MODIFY: `services/__init__.py`

**Threat references:** None

<read_first>
- services/__init__.py (full file — import pattern, __all__ list, get_service function)
</read_first>

<action>
In `services/__init__.py`:

1. Add import after line 18 (after `from .backpack_service import BackpackService`):
```python
# Fase 16 - Trivias Tematicas
from .trivia_service import TriviaCategoryService
```

2. Add to `__all__` list after `'BackpackService',`:
```python
    # Fase 16 - Trivias Tematicas
    'TriviaCategoryService',
```
</action>

<acceptance_criteria>
1. `grep "TriviaCategoryService" services/__init__.py` returns exactly 2 lines (one import, one __all__)
2. `python3 -c "from services import TriviaCategoryService, get_service; print('OK')"` prints `OK` with no errors
3. `python3 -c "from services import __all__; print('TriviaCategoryService' in __all__)"` prints `True`
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "from services import TriviaCategoryService, get_service; print('OK')"
</automated>
</verify>

---

### Wave 2: GameService Extension

#### Task 5: Add thematic trivia constants and templates to GameService

**Objective:** Add class-level constants for thematic trivia limits, rewards, streak milestones, and LucienVoice message templates.

**Requirements:** TRIVIA-03, TRIVIA-04

**Verification:**
- `STREAK_MILESTONES = {3: 2, 5: 5, 7: 10, 10: 20}` is present in GameService
- `DAILY_TRIVIA_TEMATICA_LIMIT_FREE = 5` and `DAILY_TRIVIA_TEMATICA_LIMIT_VIP = 10` are present
- `TRIVIA_TEMATICA_TEMPLATES` dict has all required template keys: `entry_title`, `entry_intro`, `counter`, `correct`, `incorrect`, `streak_messages`, `limit_reached`

**Files:**
- MODIFY: `services/game_service.py`

**Threat references:** None

<read_first>
- services/game_service.py (lines 23-37 — existing class constants)
- services/game_service.py (lines 163-201 — TRIVIA_VIP_TEMPLATES for template structure to replicate)
- services/game_service.py (lines 203-209 — __init__ method for instance variables)
</read_first>

<action>
In `services/game_service.py`:

1. After line 37 (`DAILY_TRIVIA_VIP_LIMIT = 5`), add:
```python
    # Limites trivia tematica (Phase 16)
    DAILY_TRIVIA_TEMATICA_LIMIT_FREE = 5
    DAILY_TRIVIA_TEMATICA_LIMIT_VIP = 10

    # Recompensas trivia tematica
    TRIVIA_TEMATICA_WIN_BESITOS = 2
    TRIVIA_TEMATICA_VIP_WIN_BESITOS = 4

    # Hitos de racha (D-09): {streak: bonus_base}
    STREAK_MILESTONES = {3: 2, 5: 5, 7: 10, 10: 20}
```

2. After TRIVIA_VIP_TEMPLATES closing `}` (line 201), add `TRIVIA_TEMATICA_TEMPLATES` with LucienVoice:
```python
    TRIVIA_TEMATICA_TEMPLATES = {
        'entry_title': [
            "🎭 La Trivia Tematica de Diana",
            "🎭 El Desafio Especial",
            "🎭 Donde el Conocimiento se Viste de Ocasión"
        ],
        'entry_intro': [
            "Diana ha preparado un desafio especial para esta ocasión...",
            "Una dinamica especial aguarda a quienes prestan atención.",
            "El conocimiento tematico revela devotos verdaderos."
        ],
        'counter': [
            "Oportunidades tematicas restantes: {remaining} de {limit}",
            "Tiene {remaining} caminos tematicos de {limit} disponibles...",
            "{remaining} de {limit} intentos especiales aguardan."
        ],
        'correct': [
            "🎩 <b>Lucien:</b>\n<i>¡Respuesta correcta! La tematica le favorece...</i>",
            "🎩 <b>Lucien:</b>\n<i>¡Exacto! Diana aprecia su conocimiento tematico.</i>",
            "🎩 <b>Lucien:</b>\n<i>¡Perfecto! Ha demostrado dominio del tema.</i>"
        ],
        'incorrect': [
            "🎩 <b>Lucien:</b>\n<i>Ah... No exactamente.</i>\n\nLa respuesta era: <b>{correct_answer}</b>\n\n<i>Diana observa que incluso en temas especiales se puede errar.</i>",
            "🎩 <b>Lucien:</b>\n<i>Hmm... No.</i>\n\nLa respuesta era: <b>{correct_answer}</b>\n\n<i>El conocimiento tematico requiere dedicación.</i>",
            "🎩 <b>Lucien:</b>\n<i>No...</i>\n\nLa respuesta correcta era: <b>{correct_answer}</b>\n\n<i>Un error, pero la tematica siempre enseña algo.</i>"
        ],
        'streak_messages': {
            2: ["🔥 La tematica comienza a revelarse...", "🔥 Diana nota su interes por el tema..."],
            3: ["⚡ ¡Racha tematica de {streak}! El conocimiento fluye.", "⚡ {streak} aciertos tematicos... admirable."],
            5: ["🌟 ¡Experto tematico! {streak} respuestas perfectas.", "🌟 La tematica se rinde ante su sabiduria."],
            7: ["🎩 ¡Maestro tematico! {streak} aciertos.", "🎩 Los espiritus del tema le observan con respeto."],
            10: ["✨ ¡LEYENDA TEMATICA! {streak} respuestas perfectas.", "✨ Es uno con la esencia del tema."]
        },
        'limit_reached': [
            "Ha agotado sus preguntas tematicas por hoy. La dinamica especial continuara manana.",
            "El desafio tematico ha terminado... por ahora. Regrese manana.",
            "Diana guarda el conocimiento tematico para manana. Sepa esperar."
        ],
        'deck_exhausted': [
            "Ha respondido todas las preguntas tematicas disponibles hoy. El conocimiento se renueva al amanecer.",
            "El mazo tematico esta completo por hoy. Regrese manana para mas desafios.",
            "Ha agotado el saber tematico de esta jornada. El alba traera nuevas preguntas."
        ]
    }
```

3. In `__init__` (line 209, after `self._vip_questions = None`), add:
```python
        self._tematica_questions = {}  # {category_id: [questions]}
```
</action>

<acceptance_criteria>
1. `grep "STREAK_MILESTONES" services/game_service.py` returns exactly one match
2. `grep "DAILY_TRIVIA_TEMATICA_LIMIT_FREE" services/game_service.py` returns exactly one match
3. `grep "TRIVIA_TEMATICA_TEMPLATES" services/game_service.py` returns exactly one match
4. `python3 -c "from services.game_service import GameService; g = GameService(); print(g.STREAK_MILESTONES)"` prints `{3: 2, 5: 5, 7: 10, 10: 20}`
5. `python3 -c "from services.game_service import GameService; g = GameService(); print(type(g._tematica_questions))"` prints `<class 'dict'>`
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "from services.game_service import GameService; g = GameService(); print(g.STREAK_MILESTONES, g.DAILY_TRIVIA_TEMATICA_LIMIT_FREE)"
</automated>
</verify>

---

#### Task 6: Add streak milestone bonus to existing play_trivia() and play_trivia_vip()

**Objective:** Integrate streak milestone bonuses into the existing trivia methods so that streak bonuses apply uniformly to all trivia types (D-10).

**Requirements:** TRIVIA-04

**Verification:**
- `play_trivia()` credits bonus besitos when streak hits 3, 5, 7, or 10
- `play_trivia_vip()` credits double bonus for VIP users
- Streak bonus is a separate `credit_besitos()` call with `TransactionSource.TRIVIA`
- `GameRecord.payout` includes streak bonus in total
- `result` dict includes `streak_bonus` key
- Streak bonus only fires when `new_streak` EXACTLY equals a milestone value (not on every subsequent correct answer)

**Files:**
- MODIFY: `services/game_service.py`

**Threat references:** T-16-05 (no stacking)

<read_first>
- services/game_service.py (lines 617-706 — play_trivia full method)
- services/game_service.py (lines 867-954 — play_trivia_vip full method)
- services/game_service.py (lines 263-272 — _get_trivia_streak)
- services/game_service.py (lines 767-776 — _get_vip_trivia_streak)
</read_first>

<action>
In `services/game_service.py`, modify `play_trivia()` (lines 617-706):

1. After line 671 (after the first `credit_besitos` call in step 7), add streak bonus logic:
```python
        # 7b. Verificar hito de racha (D-09, D-10)
        streak_bonus = 0
        if is_correct and new_streak in self.STREAK_MILESTONES:
            bonus = self.STREAK_MILESTONES[new_streak]
            streak_bonus = bonus * 2 if self.is_user_vip(user_id) else bonus
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=streak_bonus,
                source=TransactionSource.TRIVIA,
                description=f"Bonus por racha de {new_streak} en trivia"
            )
```

2. Update GameRecord payout (line 678) to include streak_bonus:
```python
            payout=besitos + streak_bonus
```

3. Add `'streak_bonus': streak_bonus` to the return dict (after line 698 `'besitos': besitos`)

Similarly modify `play_trivia_vip()` (lines 867-954):

4. After the VIP credit_besitos call (line 919), add the same streak bonus logic (VIP already gets double from `is_user_vip` check)

5. Update VIP GameRecord payout (line 927) to `payout=besitos + streak_bonus`

6. Add `'streak_bonus': streak_bonus` to VIP return dict

7. Update logger.info calls to include `bonus:{streak_bonus}`
</action>

<acceptance_criteria>
1. `grep "streak_bonus" services/game_service.py | wc -l` returns >= 8 (multiple occurrences in both methods)
2. `grep "STREAK_MILESTONES" services/game_service.py | wc -l` returns >= 3 (constant definition + usage in both methods)
3. `grep "Bonus por racha" services/game_service.py | wc -l` returns 2 (one in play_trivia, one in play_trivia_vip)
4. `grep "payout=besitos + streak_bonus" services/game_service.py | wc -l` returns 2 (both trivia methods)
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && grep -c "streak_bonus" services/game_service.py && grep -c "STREAK_MILESTONES" services/game_service.py
</automated>
</verify>

---

#### Task 7: Add thematic trivia question loading and draw-without-repetition methods

**Objective:** Add methods to GameService for loading thematic questions from JSON files, tracking answered questions per user per day, and selecting random unanswered questions.

**Requirements:** TRIVIA-03 (specifically D-04, D-05, D-08)

**Verification:**
- `load_trivia_tematica_questions(category_id)` loads from `docs/preguntas_{category_id}.json`
- `_get_today_tematica_trivia_records(user_id)` queries GameRecord for `game_type='trivia_tematica'`
- `_get_answered_today_indices(user_id, game_type)` returns set of question indices already answered today
- `get_random_tematica_question(user_id, category_id)` returns tuple `(question_dict, index)` or `(None, -1)` if no questions, or `(None, -2)` if all exhausted

**Files:**
- MODIFY: `services/game_service.py`

**Threat references:** None

<read_first>
- services/game_service.py (lines 575-593 — load_trivia_questions for JSON loading pattern)
- services/game_service.py (lines 253-261 — _get_today_trivia_records for daily query pattern)
- services/game_service.py (lines 355-362 — get_today_play_count for count pattern)
- services/game_service.py (lines 595-603 — get_random_question for random pick pattern)
</read_first>

<action>
In `services/game_service.py`, add the following methods before the `__del__` method (before line 1004):

1. `_get_today_tematica_trivia_records(self, user_id: int) -> list` — queries GameRecord WHERE user_id AND game_type='trivia_tematica' AND played_at >= today, ordered by played_at DESC

2. `_get_answered_today_indices(self, user_id: int, game_type: str) -> set` — returns set of int question indices from result field (format: "tematica_question_{idx}") for records played today

3. `load_trivia_tematica_questions(self, category_id: str) -> list` — loads from `Path(f"docs/preguntas_{category_id}.json")`, caches in `self._tematica_questions[category_id]`

4. `get_random_tematica_question(self, user_id: int, category_id: str) -> Tuple[Optional[dict], int]` — loads questions, filters out already-answered indices, picks random from remaining; returns (None, -1) if file not found/empty, (None, -2) if all answered today

All methods MUST be <= 50 lines each. Follow the exact patterns from the existing VIP trivia methods for naming, logging format, and error handling.
</action>

<acceptance_criteria>
1. `grep "def load_trivia_tematica_questions" services/game_service.py` returns exactly one match
2. `grep "def _get_answered_today_indices" services/game_service.py` returns exactly one match
3. `grep "def get_random_tematica_question" services/game_service.py` returns exactly one match
4. `grep "def _get_today_tematica_trivia_records" services/game_service.py` returns exactly one match
5. `python3 -c "from services.game_service import GameService; g = GameService(); q = g.load_trivia_tematica_questions('nonexistent'); print(len(q)); g.close()"` prints `0`
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "from services.game_service import GameService; g = GameService(); q = g.load_trivia_tematica_questions('nonexistent'); print(len(q)); g.close()"
</automated>
</verify>

---

#### Task 8: Add play_trivia_tematica() and supporting methods

**Objective:** Add the complete thematic trivia play method with streak tracking and message construction, mirroring `play_trivia_vip()` (lines 867-954).

**Requirements:** TRIVIA-03

**Verification:**
- `play_trivia_tematica()` processes answers with streak, bonus, and draw-without-repetition
- `_get_tematica_trivia_streak()` calculates streak from today's thematic records
- `get_trivia_tematica_entry_data()` returns enriched data for handler display
- `_build_trivia_tematica_message_parts()` and `_build_trivia_tematica_message()` construct LucienVoice output
- `get_question_by_tematica_index()` retrieves a question by index from loaded thematic questions
- `get_daily_limits()` includes `trivia_tematica_limit`
- `can_play()` handles `game_type='trivia_tematica'`

**Files:**
- MODIFY: `services/game_service.py`

**Threat references:** T-16-05 (streak no stacking)

<read_first>
- services/game_service.py (lines 836-954 — get_trivia_vip_entry_data and play_trivia_vip as complete template)
- services/game_service.py (lines 320-327 — get_daily_limits)
- services/game_service.py (lines 364-382 — can_play)
- services/game_service.py (lines 993-1002 — _build_trivia_vip_message)
- services/game_service.py (lines 956-991 — _build_trivia_vip_message_parts)
</read_first>

<action>
In `services/game_service.py`:

1. Update `get_daily_limits()` (line 326) to add `'trivia_tematica_limit': self.DAILY_TRIVIA_TEMATICA_LIMIT_VIP if is_vip else self.DAILY_TRIVIA_TEMATICA_LIMIT_FREE`

2. Update `can_play()` (line 370) to handle `'trivia_tematica'`:
```python
    elif game_type == 'trivia_tematica':
        limit = limits['trivia_tematica_limit']
```

3. Add `_get_tematica_trivia_streak(self, user_id: int) -> int` — mirror of `_get_vip_trivia_streak()` using `_get_today_tematica_trivia_records()`

4. Add `get_question_by_tematica_index(self, index: int, category_id: str) -> Optional[dict]` — retrieves question from cached thematic questions

5. Add `get_trivia_tematica_entry_data(self, user_id: int) -> dict` — mirror of `get_trivia_vip_entry_data()` using thematic limits and streak

6. Add `play_trivia_tematica(self, user_id: int, question_idx: int, answer_idx: int, category_id: str) -> Dict[str, Any]` — mirror of `play_trivia_vip()` with:
   - Limit checking using `can_play(user_id, 'trivia_tematica')`
   - Streak bonus via `_check_streak_milestone()` helper
   - GameRecord with `game_type='trivia_tematica'` and `result=f"tematica_question_{question_idx}"`
   - Same return dict structure with added `'streak_bonus'` key

7. Add `_build_trivia_tematica_message_parts()` — mirror of `_build_trivia_vip_message_parts()` using `TRIVIA_TEMATICA_TEMPLATES`

8. Add `_build_trivia_tematica_message()` — mirror of `_build_trivia_vip_message()`

9. Add `_get_tematica_streak_message(self, streak: int) -> Optional[str]` — uses `TRIVIA_TEMATICA_TEMPLATES['streak_messages']`

10. Add `get_active_tematica_info(self) -> Optional[dict]` — queries TriviaCategory for is_active=True, returns {category_id, display_name} or None

All methods MUST be <= 50 lines each.
</action>

<acceptance_criteria>
1. `grep "def play_trivia_tematica" services/game_service.py` returns exactly one match
2. `grep "def get_trivia_tematica_entry_data" services/game_service.py` returns exactly one match
3. `grep "trivia_tematica_limit" services/game_service.py | wc -l` returns >= 3 (in get_daily_limits, can_play, and get_trivia_tematica_entry_data)
4. `grep "game_type.*trivia_tematica" services/game_service.py | wc -l` returns >= 5 (in _get_today_tematica_trivia_records, _get_answered_today_indices, play_trivia_tematica, get_trivia_tematica_entry_data, get_active_tematica_info)
5. `grep "def get_active_tematica_info" services/game_service.py` returns exactly one match
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "from services.game_service import GameService; g = GameService(); print(hasattr(g, 'play_trivia_tematica'), hasattr(g, 'get_active_tematica_info')); g.close()"
</automated>
</verify>

---

### Wave 3: Handlers

#### Task 9: Extend game_user_handlers.py with thematic trivia handlers

**Objective:** Add two new callback handlers: `game_trivia_tematica` (entry/show question) and `trivia_tematica_answer` (process answer).

**Requirements:** TRIVIA-05

**Verification:**
- Handler `game_trivia_tematica` is registered with callback_data `"game_trivia_tematica"`
- Handler `trivia_tematica_answer` is registered with callback_data prefix `"trivia_tematica_answer_"`
- Answer handler parses callback data format: `trivia_tematica_answer_{answer_idx}_{question_idx}`
- Both handlers use exactly 1 service (`GameService`) — category info obtained via `GameService.get_active_tematica_info()`
- No direct DB access, no business logic in handlers

**Files:**
- MODIFY: `handlers/game_user_handlers.py`

**Threat references:** T-16-02 (callback data validation)

<read_first>
- handlers/game_user_handlers.py (full file — especially game_trivia lines 84-130 and trivia_answer lines 133-150, game_trivia_vip lines 155-200, trivia_vip_answer lines 205-222)
- keyboards/inline_keyboards.py (lines 424-455 — game_menu_keyboard and trivia_keyboard functions for imports)
</read_first>

<action>
**CRITICAL (Task 9 fix): Both handlers MUST use `GameService.get_active_tematica_info()` — NOT `TriviaCategoryService` directly.**
**Verify with acceptance criterion #6: `grep "TriviaCategoryService\|trivia_service" handlers/game_user_handlers.py | wc -l` MUST return 0.**

In `handlers/game_user_handlers.py`:

1. Add import at top (after line 16):
```python
from keyboards.inline_keyboards import (
    game_menu_keyboard,
    dice_play_keyboard,
    trivia_keyboard,
    trivia_vip_keyboard,
    trivia_vip_result_keyboard,
    trivia_tematica_keyboard,        # NEW Phase 16
    trivia_tematica_result_keyboard  # NEW Phase 16
)
# NOTE: Do NOT import TriviaCategoryService. Category info comes via GameService.get_active_tematica_info().
```

2. Add `game_trivia_tematica` handler (after game_trivia_vip, before the file end):
   - Calls `GameService.get_active_tematica_info()` to check if category is active
   - If no active category: edit message with "No hay dinamicas tematicas activas en este momento" and game_menu_keyboard
   - Calls `GameService.get_trivia_tematica_entry_data(user_id)` for limits
   - If cannot play: show limit message
   - Calls `GameService.get_random_tematica_question(user_id, category_id)` for question
   - If None/-1: "Los pergaminos tematicos estan en el taller de Lucien"
   - If -2: deck exhausted message from TRIVIA_TEMATICA_TEMPLATES
   - Shows question with `trivia_tematica_keyboard(question, question_idx)`
   - Logs: `game_user_handlers - game_trivia_tematica - {user_id} - shown - category:{category_id}`

3. Add `trivia_tematica_answer` handler:
   - Callback data: `trivia_tematica_answer_{answer_idx}_{question_idx}`
   - Validates `answer_idx` is 0-3 (T-16-02)
   - Gets active category via `GameService.get_active_tematica_info()`
   - Calls `GameService.play_trivia_tematica(user_id, question_idx, answer_idx, category_id)`
   - Shows result with `trivia_tematica_result_keyboard()`
   - Logs: `game_user_handlers - trivia_tematica_answer - {user_id} - correct:{result['correct']}, besitos:{result['besitos']}, bonus:{result['streak_bonus']}`
</action>

<acceptance_criteria>
1. `grep "game_trivia_tematica" handlers/game_user_handlers.py | wc -l` returns >= 2 (router registration + handler function)
2. `grep "trivia_tematica_answer_" handlers/game_user_handlers.py | wc -l` returns >= 1 (router registration)
3. `grep "def game_trivia_tematica" handlers/game_user_handlers.py` returns exactly one match
4. `grep "def trivia_tematica_answer" handlers/game_user_handlers.py` returns exactly one match
5. `grep "trivia_tematica_keyboard" handlers/game_user_handlers.py | wc -l` returns >= 2 (import + usage)
6. `grep "TriviaCategoryService\|trivia_service" handlers/game_user_handlers.py | wc -l` returns 0 (handler does NOT use TriviaCategoryService directly -- uses GameService)
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "import handlers.game_user_handlers; print('imported')" && grep -c "TriviaCategoryService\|trivia_service" handlers/game_user_handlers.py
</automated>
</verify>

---

#### Task 10: Create trivia_admin_handlers.py

**Objective:** Create the admin handler file for category management, following the `handlers/admin_handlers.py` pattern.

**Requirements:** TRIVIA-06

**D-14 Scope Note:** The "programar por fecha" (scheduling) UI option from D-14 is DEFERRED to a follow-up task. This task implements manual activate/deactivate only. Scheduled activation via `SchedulerService` with `DateTrigger` will be added in a subsequent phase increment. The `TriviaCategory.scheduled_end` column is included in the model to support this future feature.

**Verification:**
- File: `handlers/trivia_admin_handlers.py`
- Router exported as `router`
- All handlers have `lambda cb: is_admin(cb.from_user.id)` filter
- Handlers: `admin_trivia_categories_menu` (list categories, show active), `trivia_category_activate` (activate a category), `trivia_category_deactivate` (deactivate)
- Uses `get_service(TriviaCategoryService)` context manager
- No direct DB access
- Null-safe: handles case where no categories exist, no active category, etc.

**Files:**
- CREATE: `handlers/trivia_admin_handlers.py`
- MODIFY: None

**Threat references:** T-16-01 (admin auth)

<read_first>
- handlers/admin_handlers.py (lines 1-149 — full admin section pattern with imports, is_admin helper, router, callback handlers with F.data + lambda filter)
- handlers/game_user_handlers.py (lines 1-21 — imports, router pattern)
- keyboards/inline_keyboards.py (lines 79-120 — admin_menu_keyboard for back button pattern)
</read_first>

<action>
Create `handlers/trivia_admin_handlers.py`:

```python
"""
Handlers de Administracion de Trivias Tematicas - Lucien Bot

Handlers para gestion de categorias de trivia desde el panel admin.
Fase 16 - Trivias Tematicas.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import bot_config
from services import get_service, TriviaCategoryService

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS


@router.callback_query(F.data == "admin_trivia_categories", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_categories_menu(callback: CallbackQuery):
    """Menu principal de gestion de categorias de trivia."""
    with get_service(TriviaCategoryService) as service:
        categories = service.discover_categories()
        active = service.get_active_category()

    text = "🎯 <b>Mazos de Trivia</b>\n\n"
    if active:
        text += f"✨ <b>Activa:</b> {active['display_name']}\n\n"
    else:
        text += "📭 <b>Sin categoria activa.</b> Usando mazo general.\n\n"

    buttons = []
    for cat in categories:
        is_active = active and active['category_id'] == cat['category_id']
        btn_text = f"{'✅ ' if is_active else ''}{cat['display_name']} ({cat['question_count']} preguntas)"
        cb_data = f"trivia_cat_activate_{cat['category_id']}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=cb_data)])

    if active:
        buttons.append([InlineKeyboardButton(
            text="⛔ Desactivar categoria activa",
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
    logger.info(f"trivia_admin_handlers - admin_trivia_categories_menu - {callback.from_user.id} - shown")


@router.callback_query(F.data.startswith("trivia_cat_activate_"), lambda cb: is_admin(cb.from_user.id))
async def trivia_category_activate(callback: CallbackQuery):
    """Activa una categoria tematica."""
    category_id = callback.data.replace("trivia_cat_activate_", "")
    with get_service(TriviaCategoryService) as service:
        service.activate(category_id)
    await callback.answer(f"Categoria activada: {category_id}", show_alert=True)
    await admin_trivia_categories_menu(callback)
    logger.info(f"trivia_admin_handlers - trivia_category_activate - {callback.from_user.id} - category:{category_id}")


@router.callback_query(F.data == "trivia_cat_deactivate", lambda cb: is_admin(cb.from_user.id))
async def trivia_category_deactivate(callback: CallbackQuery):
    """Desactiva la categoria activa."""
    with get_service(TriviaCategoryService) as service:
        service.deactivate()
    await callback.answer("Categoria desactivada. Usando mazo general.", show_alert=True)
    await admin_trivia_categories_menu(callback)
    logger.info(f"trivia_admin_handlers - trivia_category_deactivate - {callback.from_user.id} - deactivated")
```

All handler functions must be <= 50 lines.
</action>

<acceptance_criteria>
1. `ls handlers/trivia_admin_handlers.py` returns the file path
2. `grep "lambda cb: is_admin" handlers/trivia_admin_handlers.py | wc -l` returns 3 (one per admin handler)
3. `grep "TriviaCategoryService" handlers/trivia_admin_handlers.py | wc -l` returns >= 3 (import + usage in handlers)
4. `grep "F.data == \"admin_trivia_categories\"" handlers/trivia_admin_handlers.py` returns exactly one match
5. `grep "F.data.startswith(\"trivia_cat_activate_\")" handlers/trivia_admin_handlers.py` returns exactly one match
6. `python3 -c "from handlers.trivia_admin_handlers import router; print(type(router))"` prints `<class 'aiogram.dispatcher.router.Router'>`
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "from handlers.trivia_admin_handlers import router; print(type(router))"
</automated>
</verify>

---

#### Task 11: Update game_menu handler for dynamic thematic button

**Objective:** Modify the `game_menu` callback handler in `game_user_handlers.py` to check for an active thematic category and conditionally add a thematic button to the keyboard.

**Requirements:** TRIVIA-07 (D-12: botón especial visible)

**Verification:**
- `game_menu` handler queries `GameService.get_active_tematica_info()`
- When a category is active, `game_menu_keyboard()` receives a `tematica_button` parameter
- No thematic button shown when no category is active (default behavior preserved)
- Thematic button label uses the category's `display_name` from the DB

**Files:**
- MODIFY: `handlers/game_user_handlers.py`

**Threat references:** None

<read_first>
- handlers/game_user_handlers.py (lines 24-44 — game_menu handler full function)
- keyboards/inline_keyboards.py (lines 424-431 — game_menu_keyboard current signature and body)
</read_first>

<action>
In `handlers/game_user_handlers.py`, modify the `game_menu` handler (lines 24-44):

1. In the existing `with get_service(GameService) as service:` block, add after `data = service.get_menu_data(user_id)`:
```python
        tematica_info = service.get_active_tematica_info()
```

2. Build the tematica_button tuple:
```python
    tematica_button = None
    if tematica_info:
        tematica_button = (tematica_info['display_name'], "game_trivia_tematica")
```

3. Pass `tematica_button` to `game_menu_keyboard()`:
```python
    await callback.message.edit_text(text, reply_markup=game_menu_keyboard(tematica_button=tematica_button))
```

4. Add logging for when a thematic button is shown:
```python
    if tematica_info:
        logger.info(f"game_user_handlers - game_menu - {user_id} - shown with tematica:{tematica_info['category_id']}")
    else:
        logger.info(f"game_user_handlers - game_menu - {user_id} - shown")
```

Note: The handler still only uses ONE service (GameService) — `get_active_tematica_info()` is a GameService method.
</action>

<acceptance_criteria>
1. `grep "get_active_tematica_info" handlers/game_user_handlers.py` returns exactly one match
2. `grep "tematica_button" handlers/game_user_handlers.py | wc -l` returns >= 3 (variable initialization, conditional assignment, passed to keyboard)
3. `grep "tematica_info" handlers/game_user_handlers.py | wc -l` returns >= 3 (service call, null check, logging)
4. No `TriviaCategoryService` import or usage in `handlers/game_user_handlers.py` — verify with `grep "TriviaCategoryService\|trivia_service" handlers/game_user_handlers.py | wc -l` returns 0
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && grep -c "get_active_tematica_info" handlers/game_user_handlers.py
</automated>
</verify>

---

### Wave 4: Keyboards & Router Registration

#### Task 12: Extend keyboards/inline_keyboards.py

**Objective:** Add thematic trivia keyboards and update `game_menu_keyboard()` to accept an optional thematic button parameter. Also add the "Mazos de Trivia" button to `admin_menu_keyboard()`.

**Requirements:** TRIVIA-07, TRIVIA-06

**Verification:**
- `game_menu_keyboard(tematica_button=None)` has updated signature
- `trivia_tematica_keyboard(question, question_idx)` creates 4 answer buttons with callback format `trivia_tematica_answer_{idx}_{qidx}`
- `trivia_tematica_result_keyboard()` has "Otra pregunta" and "Menu de juegos" buttons
- `admin_menu_keyboard()` includes "🎯 Mazos de Trivia" button with callback_data `"admin_trivia_categories"`

**Files:**
- MODIFY: `keyboards/inline_keyboards.py`

**Threat references:** T-16-01 (admin button only visible to admins via handler filter, not keyboard)

<read_first>
- keyboards/inline_keyboards.py (lines 424-431 — game_menu_keyboard current implementation)
- keyboards/inline_keyboards.py (lines 458-479 — trivia_vip_keyboard and trivia_vip_result_keyboard as templates)
- keyboards/inline_keyboards.py (lines 79-119 — admin_menu_keyboard for button insertion point)
</read_first>

<action>
In `keyboards/inline_keyboards.py`:

1. Update `game_menu_keyboard()` signature and body (lines 424-431):
```python
def game_menu_keyboard(tematica_button: tuple = None) -> InlineKeyboardMarkup:
    """Menu de seleccion de juegos. Si tematica_button = (label, callback), anade boton extra."""
    buttons = [
        [InlineKeyboardButton(text="🎲 Lanzar los dados del destino", callback_data="game_dice")],
    ]
    if tematica_button:
        label, cb_data = tematica_button
        buttons.append([InlineKeyboardButton(text=label, callback_data=cb_data)])
    buttons.append([InlineKeyboardButton(text="❓ El examen de Diana", callback_data="game_trivia")])
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

2. Add `trivia_tematica_keyboard()` after `trivia_vip_result_keyboard` (after line 479):
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


def trivia_tematica_result_keyboard() -> InlineKeyboardMarkup:
    """Teclado para resultado de trivia tematica."""
    buttons = [
        [InlineKeyboardButton(text="🔄 Otra pregunta tematica", callback_data="game_trivia_tematica")],
        [InlineKeyboardButton(text="🔙 Menu de juegos", callback_data="game_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

3. In `admin_menu_keyboard()` (line 81, after the first button), insert:
```python
        [InlineKeyboardButton(
            text="🎯 Mazos de Trivia",
            callback_data="admin_trivia_categories"
        )],
```
Insert it at position 2 in the button list (after "Gestionar dominios" and before "El Diván de Diana").
</action>

<acceptance_criteria>
1. `grep "def game_menu_keyboard" keyboards/inline_keyboards.py` shows signature with `tematica_button: tuple = None`
2. `grep "def trivia_tematica_keyboard" keyboards/inline_keyboards.py` returns exactly one match
3. `grep "def trivia_tematica_result_keyboard" keyboards/inline_keyboards.py` returns exactly one match
4. `grep "trivia_tematica_answer_" keyboards/inline_keyboards.py | wc -l` returns 1 (in trivia_tematica_keyboard)
5. `grep "Mazos de Trivia" keyboards/inline_keyboards.py` returns exactly one match
6. `grep "admin_trivia_categories" keyboards/inline_keyboards.py` returns exactly one match
7. `python3 -c "from keyboards.inline_keyboards import trivia_tematica_keyboard, trivia_tematica_result_keyboard, game_menu_keyboard; print('OK')"` prints `OK`
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "from keyboards.inline_keyboards import trivia_tematica_keyboard, trivia_tematica_result_keyboard, game_menu_keyboard; print('OK')"
</automated>
</verify>

---

#### Task 13: Register trivia_admin_handlers router in handlers/__init__.py and bot.py

**Objective:** Export and register the new admin router so the bot dispatches to it.

**Requirements:** TRIVIA-06

**Verification:**
- `handlers/__init__.py` imports `trivia_admin_handlers.router` and exports it
- `bot.py` includes the router in `dp.include_router()`

**Files:**
- MODIFY: `handlers/__init__.py`
- MODIFY: `bot.py`

**Threat references:** None

<read_first>
- handlers/__init__.py (full file — import and __all__ pattern)
- bot.py (lines 232-267 — router registration section)
</read_first>

<action>
In `handlers/__init__.py`:

1. Add import after line 34 (after backpack_router import):
```python
# Phase 16 - Trivias Tematicas
from .trivia_admin_handlers import router as trivia_admin_router
```

2. Add to `__all__` after `'backpack_router'`:
```python
    # Phase 16 - Trivias Tematicas
    'trivia_admin_router',
```

In `bot.py`:

3. Add import after line 58 (after backpack_router import):
```python
    # Phase 16 - Trivias Tematicas
    trivia_admin_router,
```

4. Add `dp.include_router(trivia_admin_router)` after line 267 (after backpack router):
```python
    # Phase 16 - Trivias Tematicas
    dp.include_router(trivia_admin_router)
```
</action>

<acceptance_criteria>
1. `grep "trivia_admin_router" handlers/__init__.py | wc -l` returns 2 (import + __all__)
2. `grep "trivia_admin_router" bot.py | wc -l` returns 2 (import + include_router)
3. `python3 -c "from handlers import trivia_admin_router; print(type(trivia_admin_router))"` prints `<class 'aiogram.dispatcher.router.Router'>`
4. `python3 -c "import bot"` exits with code 0 (no import errors at startup)
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "from handlers import trivia_admin_router; print(type(trivia_admin_router))"
</automated>
</verify>

---

### Wave 5: Example Data

#### Task 14: Create example thematic question JSON files

**Objective:** Create two small example question files so the admin can immediately test the category activation flow.

**Requirements:** TRIVIA-08 (D-01, D-15: files are externally produced; these are placeholders for testing)

**Verification:**
- `docs/preguntas_halloween.json` exists with >= 5 questions
- `docs/preguntas_navidena.json` exists with >= 5 questions
- Both files follow the same format as `docs/preguntas.json`: array of `{q, opts, answer}` objects

**Files:**
- CREATE: `docs/preguntas_halloween.json`
- CREATE: `docs/preguntas_navidena.json`

**Threat references:** T-16-04 (files handle gracefully if missing/corrupt)

<read_first>
- docs/preguntas.json (sample 2-3 questions — confirm the format: array of {q, opts: [string, string, string], answer: int})
</read_first>

<action>
Create `docs/preguntas_halloween.json` with 5-6 Halloween-themed questions. Format:
```json
[
  {"q": "¿Qué tradición de Halloween involucra tallar calabazas?", "opts": ["Trick or treat", "Jack-o'-lantern", "Dulce o travesura"], "answer": 1},
  {"q": "¿En qué país se originó la celebración de Halloween?", "opts": ["Estados Unidos", "México", "Irlanda"], "answer": 2},
  {"q": "¿Qué fruta se usaba originalmente para tallar antes de la calabaza?", "opts": ["Nabo", "Sandía", "Melón"], "answer": 0},
  {"q": "¿Cómo se llama la celebración mexicana que coincide con Halloween?", "opts": ["Día de Muertos", "Navidad", "Cinco de Mayo"], "answer": 0},
  {"q": "¿Qué color NO es tradicional de Halloween?", "opts": ["Naranja", "Negro", "Verde"], "answer": 2}
]
```

Create `docs/preguntas_navidena.json` with 5-6 Christmas-themed questions. Format:
```json
[
  {"q": "¿En qué mes se celebra la Navidad?", "opts": ["Noviembre", "Diciembre", "Enero"], "answer": 1},
  {"q": "¿Quién trae los regalos según la tradición navideña?", "opts": ["El Conejo de Pascua", "Santa Claus", "Cupido"], "answer": 1},
  {"q": "¿Cuál es la flor típica de la Navidad en México?", "opts": ["Rosa", "Nochebuena", "Girasol"], "answer": 1},
  {"q": "¿Cuántos renos tira del trineo de Santa?", "opts": ["6", "9", "8"], "answer": 1},
  {"q": "¿Qué se celebra el 25 de diciembre?", "opts": ["Año Nuevo", "Navidad", "Acción de Gracias"], "answer": 1}
]
```
</action>

<acceptance_criteria>
1. `python3 -c "import json; d=json.load(open('docs/preguntas_halloween.json')); print(len(d))"` prints >= 5
2. `python3 -c "import json; d=json.load(open('docs/preguntas_navidena.json')); print(len(d))"` prints >= 5
3. `python3 -c "import json; d=json.load(open('docs/preguntas_halloween.json')); assert all('q' in q and 'opts' in q and 'answer' in q for q in d); print('OK')"` prints `OK`
4. `python3 -c "import json; d=json.load(open('docs/preguntas_navidena.json')); assert all(isinstance(q['answer'], int) and 0 <= q['answer'] < len(q['opts']) for q in d); print('OK')"` prints `OK`
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -c "import json; assert len(json.load(open('docs/preguntas_halloween.json'))) >= 5; assert len(json.load(open('docs/preguntas_navidena.json'))) >= 5; print('OK')"
</automated>
</verify>

---

### Wave 6: Verification

#### Task 15: Run full test suite and manual verification checklist

**Objective:** Validate the complete implementation with the test suite and manual checks.

**Requirements:** ALL (TRIVIA-01 through TRIVIA-08)

**Verification:**
- `pytest -x tests/ --ignore=tests/e2e -q` passes
- `python3 -m alembic upgrade head && python3 -m alembic downgrade -1 && python3 -m alembic upgrade head` all succeed
- Python import of all modified modules succeeds

**Files:** None (verification only)

**Threat references:** T-16-01, T-16-02, T-16-03 (manual verification of admin auth, callback bounds, and atomic activation)

<read_first>
- .planning/phases/16-16-trivias-tem-ticas/16-VALIDATION.md — test commands and sampling rate
</read_first>

<action>
1. Run: `cd /home/ubuntu/repos/lucienbot && python3 -m alembic upgrade head` — verify exit code 0
2. Run: `cd /home/ubuntu/repos/lucienbot && python3 -m pytest -x tests/ --ignore=tests/e2e -q` — verify exit code 0 (no regressions)
3. Run: `cd /home/ubuntu/repos/lucienbot && python3 -c "
from services.trivia_service import TriviaCategoryService
from services.game_service import GameService
from keyboards.inline_keyboards import trivia_tematica_keyboard, trivia_tematica_result_keyboard, game_menu_keyboard
from handlers.trivia_admin_handlers import router
from services import TriviaCategoryService, get_service
print('ALL IMPORTS OK')
"` — verify prints "ALL IMPORTS OK"
4. Run: `cd /home/ubuntu/repos/lucienbot && python3 -c "
from services.game_service import GameService
g = GameService()
print('STREAK_MILESTONES:', g.STREAK_MILESTONES)
print('DAILY_TRIVIA_TEMATICA_LIMIT_FREE:', g.DAILY_TRIVIA_TEMATICA_LIMIT_FREE)
print('_tematica_questions type:', type(g._tematica_questions))
q = g.load_trivia_tematica_questions('halloween')
print('halloween questions loaded:', len(q))
q = g.load_trivia_tematica_questions('navidena')
print('navidena questions loaded:', len(q))
g.close()
"` — verify halloween and navidena questions load with count >= 5 each
</action>

<acceptance_criteria>
1. `python3 -m alembic upgrade head` exit code 0
2. `python3 -m pytest -x tests/ --ignore=tests/e2e -q` exit code 0
3. All import verification commands succeed
4. Halloween and Navidad question files load correctly (>= 5 questions each)
</acceptance_criteria>

<verify>
<automated>
cd /home/ubuntu/repos/lucienbot && python3 -m alembic upgrade head && python3 -m pytest -x tests/ --ignore=tests/e2e -q && python3 -c "from services.trivia_service import TriviaCategoryService; from services.game_service import GameService; from keyboards.inline_keyboards import trivia_tematica_keyboard, trivia_tematica_result_keyboard, game_menu_keyboard; from handlers.trivia_admin_handlers import router; from services import TriviaCategoryService, get_service; print('ALL IMPORTS OK')" && python3 -c "from services.game_service import GameService; g = GameService(); print('halloween:', len(g.load_trivia_tematica_questions('halloween'))); print('navidena:', len(g.load_trivia_tematica_questions('navidena'))); g.close()"
</automated>
</verify>

---

## Verification Matrix

| Task | Requirement | Automated Verify | Manual Verify |
|------|-------------|-----------------|---------------|
| T1 | TRIVIA-01 | grep + python3 import | — |
| T2 | TRIVIA-01 | alembic upgrade/downgrade + sqlite3 schema | — |
| T3 | TRIVIA-02 | python3 import + method count | — |
| T4 | TRIVIA-02 | python3 import + grep | — |
| T5 | TRIVIA-03, TRIVIA-04 | grep + python3 attribute check | — |
| T6 | TRIVIA-04 | grep for streak_bonus patterns | — |
| T7 | TRIVIA-03 | grep + python3 method call | — |
| T8 | TRIVIA-03 | grep + method count | — |
| T9 | TRIVIA-05 | grep + handler count | — |
| T10 | TRIVIA-06 | grep admin filter + import check | Telegram UI: /admin → Mazos de Trivia |
| T11 | TRIVIA-07 | grep get_active_tematica_info | Telegram UI: game_menu with active category |
| T12 | TRIVIA-07, TRIVIA-06 | grep keyboard functions | — |
| T13 | TRIVIA-06 | python3 import + bot.py import check | — |
| T14 | TRIVIA-08 | python3 JSON validation | — |
| T15 | ALL | pytest suite + alembic + import checks | — |

## Success Criteria (must_haves)

1. **MH-01:** Admin can see "🎯 Mazos de Trivia" button in admin panel, list available category JSON files, activate/deactivate categories with visual feedback (D-14)
2. **MH-02:** When a category is active, the game menu shows a thematic trivia button with the category's display name; when inactive, no extra button appears (D-12)
3. **MH-03:** Thematic trivia questions are drawn without repetition within the same day; answered questions are excluded until daily reset (D-04, D-05)
4. **MH-04:** Streak milestone bonuses (3/5/7/10) are awarded for normal, VIP, and thematic trivia with VIP receiving double (D-09, D-10)
5. **MH-05:** Thematic trivia has independent daily limits (Free=5, VIP=10) that do not consume general trivia attempts (D-13)
6. **MH-06:** Only one category can be active at a time; activating a new category deactivates the previous one atomically (D-06)
7. **MH-07:** If no category is active, the default general deck (`preguntas.json`) is used for normal trivia; the system is invisible to users (D-02, D-07)
8. **MH-08:** All admin category handlers require `is_admin()` check; callback data indices are bounds-validated (T-16-01, T-16-02)
9. **MH-09:** Full test suite passes with no regressions; all imports succeed

---

*Plan created: 2026-05-09*
*Phase: 16-Trivias Temáticas*
*Sources: CONTEXT.md (15 locked decisions), RESEARCH.md, PATTERNS.md, VALIDATION.md, game_service.py, game_user_handlers.py, admin_handlers.py, inline_keyboards.py, scheduler_service.py, bot.py, alembic migrations*
