# Phase 18: Protección de Rachas - Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 8 (3 extended, 2 added new content to, 1 new, 1 new migration)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `models/models.py` (extend) | model | CRUD | `models/models.py:1138-1143` (StreakPromotionCodeStatus), `models/models.py:167-177` (TransactionSource), `models/models.py:1194-1207` (StreakPromotionCode) | exact |
| `services/streak_promotion_service.py` (extend) | service | CRUD + event-driven | `services/streak_promotion_service.py:192-222` (claim_for_streak), `services/besito_service.py:131-187` (debit_besitos atomic) | exact |
| `services/game_service.py` (extend) | service | request-response | `services/game_service.py:740-814` (play_trivia) | exact |
| `handlers/game_user_handlers.py` (extend) | handler | request-response + FSM | `handlers/game_user_handlers.py:150-165` (trivia_answer), `handlers/mission_admin_handlers.py:30-51` (FSM StatesGroup) | exact |
| `keyboards/callback_data.py` (add) | utility | request-response | `keyboards/callback_data.py:602-617` (TriviaAnswerCallback) | exact |
| `keyboards/inline_keyboards.py` (add) | utility | request-response | `keyboards/inline_keyboards.py:475-487` (trivia_keyboard) | exact |
| `alembic/versions/XXXX_add_streak_session.py` (new) | migration | batch | `alembic/versions/20250406_add_trivia_to_transaction_source_enum.py`, `alembic/versions/36c345796281_add_streak_promotions_tables.py` | exact |
| `services/besito_service.py` (use existing) | service | CRUD | `services/besito_service.py:131-187` (debit_besitos), `services/besito_service.py:189-192` (has_sufficient_balance) | n/a — read-only |

---

## Pattern Assignments

### 1. `models/models.py` — EXTEND: StreakPromotionCodeStatus + CANCELLED

**What to add:** New `CANCELLED = "cancelled"` value to `StreakPromotionCodeStatus` enum.

**Analog:** `OrderStatus` enum at line 679-683 (uses same `"cancelled"` string convention):

```python
# models/models.py:679-683 — OrderStatus enum (naming convention reference)
class OrderStatus(str, enum.Enum):
    """Estados de una orden"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

**Pattern to copy at line 1142 (after `USED = "used"`):**
```python
# models/models.py:1138-1143 — StreakPromotionCodeStatus (existing)
class StreakPromotionCodeStatus(str, enum.Enum):
    """States for a streak promotion discount code."""
    AVAILABLE = "available"
    DELIVERED = "delivered"
    USED = "used"
    CANCELLED = "cancelled"  # NEW: matches OrderStatus convention
```

---

### 2. `models/models.py` — EXTEND: TransactionSource + STREAK_PROTECTION

**What to add:** New `STREAK_PROTECTION = "streak_protection"` value to `TransactionSource` enum.

**Analog:** `TransactionSource` enum itself at lines 167-177:

```python
# models/models.py:167-177 — TransactionSource enum (existing)
class TransactionSource(str, enum.Enum):
    """Fuentes de transacción de besitos"""
    REACTION = "reaction"
    DAILY_GIFT = "daily_gift"
    MISSION = "mission"
    PURCHASE = "purchase"
    ADMIN = "admin"
    ANONYMOUS_MESSAGE = "anonymous_message"
    GAME = "GAME"
    TRIVIA = "TRIVIA"
    STREAK_PROTECTION = "streak_protection"  # NEW: after TRIVIA
```

---

### 3. `models/models.py` — ADD: StreakSession model

**What to add:** New `StreakSession` model class after `StreakPromotionRedemption` (after line ~1222).

**Analog:** `StreakPromotionCode` model at lines 1194-1207 (same domain, similar structure) + `models/models.py:1-8` for import conventions:

```python
# models/models.py:1-8 — Imports convention
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger, Text, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base
import enum
import secrets
import string
```

**Pattern to copy (model structure from StreakPromotionCode:1194-1207 + relationship patterns):**
```python
# models/models.py:1194-1207 — StreakPromotionCode model (structure analog)
class StreakPromotionCode(Base):
    __tablename__ = "streak_promotion_codes"
    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("streak_promotion_levels.id"), nullable=False)
    code_value = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(Enum(StreakPromotionCodeStatus), default=StreakPromotionCodeStatus.AVAILABLE)
    user_id = Column(BigInteger, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by_admin = Column(BigInteger, nullable=True)
    level = relationship("StreakPromotionLevel", back_populates="codes")
```

**Add `session_id` FK to `StreakPromotionCode` (after `used_by_admin` on line 1205):**
```python
    session_id = Column(Integer, ForeignKey("streak_sessions.id"), nullable=True)  # NEW
    session = relationship("StreakSession", back_populates="codes")  # NEW
```

---

### 4. `services/streak_promotion_service.py` — EXTEND: New session methods + modify claim_for_streak

**What to add:** `get_active_session()`, `_get_or_create_session()`, `close_session()`, `cancel_session_codes()`, `calculate_protection_cost()` methods. Modify `claim_for_streak()` at lines 192-222.

**Analog:** Self — `claim_for_streak()` at lines 192-222 and `_get_available_code()` at lines 177-190 for DB query patterns:

```python
# services/streak_promotion_service.py:192-222 — claim_for_streak (core CRUD pattern to extend)
def claim_for_streak(self, user_id: int, game_type: str, streak: int,
                     category_id: str = None) -> Optional[dict]:
    db = self._get_db()
    promotions = self.get_active_promotions(game_type, category_id)
    for promo in promotions:
        for level in promo.levels:
            if level.consecutive_required != streak:
                continue
            if self._has_claimed_level(user_id, level.id):
                continue
            code = self._get_available_code(level.id)
            if not code:
                continue
            code.status = StreakPromotionCodeStatus.DELIVERED
            code.user_id = user_id
            code.delivered_at = datetime.now(timezone.utc)
            # --- NEW: link to session ---
            session = self._get_or_create_session(user_id, code.level.promotion_id)
            code.session_id = session.id
            codes = json.loads(session.codes_delivered or '[]')
            codes.append(code.id)
            session.codes_delivered = json.dumps(codes)
            # --- end NEW ---
            redemption = StreakPromotionRedemption(...)
            db.add(redemption)
            db.commit()
            logger.info(...)
            return {...}
    return None
```

**Atomic debit pattern analog from besito_service.py:131-187:**
```python
# services/besito_service.py:131-187 — debit_besitos with commit=False for atomicity
def debit_besitos(self, user_id, amount, source, description=None,
                  reference_id=None, commit=True):
    if amount <= 0:
        return False
    db = self._get_db()
    try:
        balance = self.get_or_create_balance(user_id, lock=True)  # SELECT FOR UPDATE
        if balance.balance < amount:
            db.rollback()  # Release lock
            return False
        balance.balance -= amount
        balance.total_spent += amount
        transaction = BesitoTransaction(
            user_id=user_id, amount=-amount, type=TransactionType.DEBIT,
            source=source, description=description, reference_id=reference_id
        )
        db.add(transaction)
        if commit:
            db.commit()
        return True
    except Exception as e:
        db.rollback()
        return False
```

**Query with_for_update pattern from streak_promotion_service.py:163-175:**
```python
# services/streak_promotion_service.py:163-175 — _has_claimed_level (with_for_update)
def _has_claimed_level(self, user_id: int, level_id: int) -> bool:
    db = self._get_db()
    existing = (
        db.query(StreakPromotionRedemption)
        .filter(
            StreakPromotionRedemption.user_id == user_id,
            StreakPromotionRedemption.level_id == level_id,
        )
        .with_for_update()
        .first()
    )
    return existing is not None
```

**Imports pattern (add `json`, `uuid` to existing imports at line 1-22):**
```python
# services/streak_promotion_service.py:1-22 — existing imports
import logging
import secrets
import json          # NEW: for codes_delivered JSON
import uuid          # NEW: for StreakSession UUID PK
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from models.models import (
    StreakPromotion, StreakPromotionLevel, StreakPromotionCode,
    StreakPromotionCodeStatus, StreakPromotionStatus,
    StreakPromotionRedemption,
    StreakSession,    # NEW
)
from models.database import SessionLocal
```

**New method structure pattern (matching existing method style at lines 224-255, `activate()`):**
```python
# services/streak_promotion_service.py:224-255 — activate() method (logging pattern)
def activate(self, promo_id: int) -> bool:
    db = self._get_db()
    promotion = db.query(StreakPromotion).filter(StreakPromotion.id == promo_id).first()
    if not promotion:
        logger.warning(f"streak_promotion_service - activate - promo_id:{promo_id} - not_found")
        return False
    promotion.is_active = True
    promotion.status = StreakPromotionStatus.ACTIVE
    # ...
    db.commit()
    logger.info(f"streak_promotion_service - activate - promo_id:{promo_id} - activated")
    return True
```

**Logging convention for new methods:**
```
streak_promotion_service - {method_name} - user:{user_id} - action:{result}
```

---

### 5. `services/game_service.py` — EXTEND: Session-aware play methods

**What to add:** Return `session_state` key from `play_trivia()`, `play_trivia_vip()`, `play_trivia_simple()`. Add `_check_session_timeout()` and `_handle_streak_failure()` private methods.

**Analog:** `play_trivia()` return dict at lines 800-814:

```python
# services/game_service.py:800-814 — play_trivia return dict (extend with session_state)
return {
    'correct': is_correct,
    'besitos': besitos,
    'besitos_total': besitos + streak_bonus,
    'previous_streak': previous_streak,
    'new_streak': new_streak,
    'streak_message': streak_message,
    'streak_bonus': streak_bonus,
    'promo_code': promo_code_info,
    'message': message,
    'message_parts': message_parts,
    'remaining_after': remaining_after,
    'limit_reached': False,
    # NEW:
    'session_state': session_state,  # dict or None — session info for handler FSM decisions
}
```

**Existing `claim_for_streak` integration block (present in all 3 play methods):**
```python
# services/game_service.py:769-782 — play_trivia claim_for_streak block
# This block exists in play_trivia (L769-782), play_trivia_vip (L1062-1075),
# and play_trivia_simple (~L1400). Factor into shared _handle_streak_session().
promo_code_info = None
if is_correct:
    from services.streak_promotion_service import StreakPromotionService
    promo_service = StreakPromotionService(self.db)
    try:
        promo_code_info = promo_service.claim_for_streak(
            user_id=user_id, game_type='trivia', streak=new_streak, category_id=None,
        )
    finally:
        promo_service.close()
```

**New error path pattern (incorrect answer + active session check):**
```
Before returning result for incorrect answer, check:
1. get_active_session(user_id) — if exists:
2. if protection_used: cancel all codes, close session, reset streak
3. elif protection available + has besitos: offer protection (via session_state in result)
4. else: set timeout (via session_state in result)
```

**Imports addition (services/game_service.py:1-19):**
```python
# services/game_service.py:1-19 — existing imports
import json
import logging
import random
from datetime import datetime, timezone        # datetime already imported
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from models.models import GameRecord, TransactionSource
from models.database import SessionLocal
from services.besito_service import BesitoService
from services.user_service import UserService
from services.vip_service import VIPService
```

---

### 6. `handlers/game_user_handlers.py` — EXTEND: FSM states + new callbacks

**What to add:** `TriviaStreakStates` StatesGroup. Modify `trivia_answer`, `trivia_vip_answer`, `trivia_simple_answer` to check `session_state` and transition to FSM. Add new handlers for protection accept/decline, retire/continue, timeout.

**Analog — FSM StatesGroup pattern from handlers/mission_admin_handlers.py:30-51:**
```python
# handlers/mission_admin_handlers.py:30-51 — StatesGroup pattern
from aiogram.fsm.state import State, StatesGroup

class MissionWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    selecting_type = State()
    waiting_target = State()
    selecting_frequency = State()
    selecting_reward = State()
    confirming = State()
```

**Analog — Handler structure from handlers/game_user_handlers.py:150-165:**
```python
# handlers/game_user_handlers.py:150-165 — trivia_answer handler (extend)
@router.callback_query(TriviaAnswerCallback.filter())
async def trivia_answer(callback: CallbackQuery, callback_data: TriviaAnswerCallback):
    """Procesa respuesta de trivia"""
    user_id = callback.from_user.id
    answer_idx = callback_data.answer_idx
    question_idx = callback_data.question_idx

    with get_service(GameService) as service:
        result = service.play_trivia(user_id, question_idx, answer_idx)

    # --- NEW: check session_state before displaying result ---
    if result.get('session_state'):
        state_info = result['session_state']
        if state_info['action'] == 'offer_protection':
            await callback.message.edit_text(
                state_info['message'],
                reply_markup=protection_keyboard(state_info['protection_cost'])
            )
            # Set FSM state via callback state parameter or FSMContext
            return
        elif state_info['action'] == 'offer_retire':
            await callback.message.edit_text(
                state_info['message'],
                reply_markup=risk_mode_keyboard(...)
            )
            return
    # --- end NEW ---

    await callback.message.edit_text(result['message'], reply_markup=game_menu_keyboard())
```

**Analog — Imports pattern from handlers/game_user_handlers.py:1-26:**
```python
# handlers/game_user_handlers.py:1-26 — existing imports (extend)
import logging
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext      # NEW: for FSM states
from aiogram.fsm.state import State, StatesGroup  # NEW
from keyboards.callback_data import (
    TriviaAnswerCallback, TriviaVipAnswerCallback, TriviaSimpleAnswerCallback,
    # NEW callbacks:
    StreakProtectAcceptCallback, StreakProtectDeclineCallback,
    StreakRetireCallback, StreakContinueCallback,
    StreakTimeoutReturnCallback,
)
from keyboards.inline_keyboards import (
    game_menu_keyboard, ...
    # NEW keyboards:
    protection_keyboard, risk_mode_keyboard, timeout_keyboard,
)
from services import get_service, GameService
```

**New StatesGroup to add (after imports, before router):**
```python
# handlers/game_user_handlers.py — NEW StatesGroup (after line 28)
class TriviaStreakStates(StatesGroup):
    waiting_protection_choice = State()  # Proteger (-X besitos) vs No proteger
    waiting_retire_choice = State()      # Continuar por X% vs Retirarse con Y%
    in_timeout = State()                 # Timeout de 2 minutos: jugando trivia libre
```

---

### 7. `keyboards/callback_data.py` — ADD: New CallbackData classes

**What to add:** `StreakProtectAcceptCallback`, `StreakProtectDeclineCallback`, `StreakRetireCallback`, `StreakContinueCallback`, `StreakTimeoutReturnCallback`.

**Analog — TriviaAnswerCallback at lines 602-617:**
```python
# keyboards/callback_data.py:602-617 — game callback data pattern
class TriviaAnswerCallback(CallbackData, prefix="trivia_answer"):
    """Respuesta de trivia"""
    answer_idx: int
    question_idx: int

class TriviaVipAnswerCallback(CallbackData, prefix="trivia_vip_answer"):
    """Respuesta de trivia VIP"""
    answer_idx: int
    question_idx: int

class TriviaSimpleAnswerCallback(CallbackData, prefix="trivia_simple_answer"):
    """Respuesta de trivia especial"""
    answer_idx: int
    question_idx: int
```

**Imports already exist at line 1-8:**
```python
# keyboards/callback_data.py:1-7 — imports (no changes needed)
from aiogram.filters.callback_data import CallbackData
```

**New callbacks to add (after line 617, before `# ==================== BACKPACK ====================`):**
```python
# keyboards/callback_data.py — NEW (after line 617)

class StreakProtectAcceptCallback(CallbackData, prefix="streak_protect_accept"):
    """Aceptar proteccion de racha pagando besitos"""
    streak: int      # streak actual a proteger
    question_idx: int

class StreakProtectDeclineCallback(CallbackData, prefix="streak_protect_decline"):
    """Rechazar proteccion de racha"""
    streak: int
    question_idx: int

class StreakRetireCallback(CallbackData, prefix="streak_retire"):
    """Retirarse del modo arriesgo conservando codigos"""
    pass  # No extra data needed; session identified by user_id

class StreakContinueCallback(CallbackData, prefix="streak_continue"):
    """Continuar en modo arriesgo por el siguiente codigo"""
    pass

class StreakTimeoutReturnCallback(CallbackData, prefix="streak_timeout_return"):
    """Volver a la trivia promo despues del timeout"""
    pass
```

---

### 8. `keyboards/inline_keyboards.py` — ADD: New keyboard functions

**What to add:** `protection_keyboard()`, `risk_mode_keyboard()`, `timeout_keyboard()`.

**Analog — trivia_keyboard at lines 475-487:**
```python
# keyboards/inline_keyboards.py:475-487 — trivia keyboard pattern
def trivia_keyboard(question: dict, question_idx: int, back_callback: str = "game_menu") -> InlineKeyboardMarkup:
    """Teclado con opciones de trivia A, B, C"""
    buttons = []
    for idx, opt_text in enumerate(question['opts']):
        buttons.append([InlineKeyboardButton(
            text=opt_text,
            callback_data=TriviaAnswerCallback(answer_idx=idx, question_idx=question_idx).pack()
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver al menú de juegos",
        callback_data=back_callback
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

**Existing imports at lines 1-6 (extend with new callback imports):**
```python
# keyboards/inline_keyboards.py:1-6 — existing imports
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.callback_data import (
    SelectTariffCallback, CopyTokenCallback,
    # ... existing imports ...
    # NEW:
    StreakProtectAcceptCallback, StreakProtectDeclineCallback,
    StreakRetireCallback, StreakContinueCallback,
    StreakTimeoutReturnCallback,
)
```

**New keyboard pattern to add (after line 535, `trivia_simple_result_keyboard`):**
```python
def protection_keyboard(protection_cost: int, streak: int, question_idx: int) -> InlineKeyboardMarkup:
    """Teclado para decision de proteccion de racha."""
    buttons = [
        [InlineKeyboardButton(
            text=f"Proteger (-{protection_cost} besitos)",
            callback_data=StreakProtectAcceptCallback(streak=streak, question_idx=question_idx).pack()
        )],
        [InlineKeyboardButton(
            text="No proteger",
            callback_data=StreakProtectDeclineCallback(streak=streak, question_idx=question_idx).pack()
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def risk_mode_keyboard() -> InlineKeyboardMarkup:
    """Teclado para modo arriesgo: continuar o retirarse."""
    buttons = [
        [InlineKeyboardButton(
            text="Continuar",
            callback_data=StreakContinueCallback().pack()
        )],
        [InlineKeyboardButton(
            text="Retirarse y conservar codigos",
            callback_data=StreakRetireCallback().pack()
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def timeout_keyboard() -> InlineKeyboardMarkup:
    """Teclado para timeout: volver a la trivia promo."""
    buttons = [
        [InlineKeyboardButton(
            text="Regresar a la Trivia Promo",
            callback_data=StreakTimeoutReturnCallback().pack()
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

---

### 9. `alembic/versions/XXXX_add_streak_session.py` — NEW: Migration

**What to add:** Migration that: (1) adds `CANCELLED` to `streakpromotioncodestatus` enum, (2) creates `streak_sessions` table, (3) adds `session_id` FK to `streak_promotion_codes`.

**Analog — Enum-first migration from `20250406_add_trivia_to_transaction_source_enum.py` (full file):**

```python
# alembic/versions/20250406_add_trivia_to_transaction_source_enum.py — enum migration pattern
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20250406_add_trivia_to_transaction_source'
down_revision: Union[str, None] = 'c32861733e54'
branch_labels = None
depends_on = None

ENUM_NAME = 'transactionsource'
NEW_VALUE = 'TRIVIA'

def upgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == 'postgresql':
        op.execute(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{NEW_VALUE}'")
    else:
        pass  # SQLite: no action needed

def downgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == 'postgresql':
        # PostgreSQL does not support DROP VALUE for enums
        # Check for data before proceeding
        result = op.get_bind().execute(
            sa.text(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE {COLUMN_NAME} = '{NEW_VALUE}'")
        ).scalar()
        if result > 0:
            raise RuntimeError(f"Cannot downgrade: {result} row(s) exist with '{NEW_VALUE}'.")
        pass  # Enum value remains but is no longer used by code
    else:
        pass
```

**Table creation + FK pattern from `36c345796281_add_streak_promotions_tables.py`:**
```python
# alembic/versions/36c345796281_add_streak_promotions_tables.py — table creation pattern
def upgrade():
    # Create table with UUID PK
    op.create_table(
        'streak_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        # Or: sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True) for UUID
        sa.Column('user_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('promotion_id', sa.Integer(), nullable=False),
        sa.Column('is_in_risk_mode', sa.Boolean(), default=False),
        sa.Column('protection_used', sa.Boolean(), default=False),
        sa.Column('codes_delivered', sa.Text(), nullable=True),  # JSON stored as text
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Add FK from streak_promotion_codes
    op.add_column('streak_promotion_codes', sa.Column('session_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_streak_promotion_codes_session',
        'streak_promotion_codes', 'streak_sessions',
        ['session_id'], ['id']
    )
```

**Migration naming convention:** Use Alembic auto-generated revision ID with descriptive name: `{revision_id}_add_streak_session.py`

**Enum name:** `streakpromotioncodestatus` (lowercase — check with `SELECT typname FROM pg_type WHERE typname = 'streakpromotioncodestatus'`)

**Down revision:** Find with `SELECT * FROM alembic_version;` or `alembic heads` — likely the latest Phase 17 migration.

---

## Shared Patterns

### Authentication / Ownership Verification
**Source:** Every handler in `game_user_handlers.py`
**Apply to:** All new trunkStreakStates handlers

```python
# handlers/game_user_handlers.py:151 — every handler uses this pattern
user_id = callback.from_user.id
# Always verify: callback.from_user.id matches session.user_id before any mutation
```

### Service Access via Context Manager
**Source:** All handlers in `game_user_handlers.py`, `services/__init__.py:48-62`
**Apply to:** All handler and service code

```python
# handlers/game_user_handlers.py:157 — get_service pattern
with get_service(GameService) as service:
    result = service.play_trivia(user_id, question_idx, answer_idx)

# For sharing DB session between services:
with get_service(GameService, db=shared_db) as service:
    ...
```

### Logging Convention
**Source:** All services and handlers
**Apply to:** All new code

```python
# Service logging pattern (streak_promotion_service.py:215):
logger.info(f"streak_promotion_service - claim_for_streak - user:{user_id} - game_type:{game_type} - streak:{streak} - result:claimed")

# Handler logging pattern (game_user_handlers.py:165):
logger.info(f"game_user_handlers - trivia_answer - {user_id} - correct:{result['correct']}")

# Format: {module} - {action} - {user_id} - {key1}:{val1} - {key2}:{val2}
```

### FSM State Transition Pattern
**Source:** `handlers/mission_admin_handlers.py:30-51` (StatesGroup), all admin handlers
**Apply to:** New streak-related FSM transitions

```python
# State definition:
class TriviaStreakStates(StatesGroup):
    waiting_protection_choice = State()
    waiting_retire_choice = State()
    in_timeout = State()

# State transition in handler:
await state.set_state(TriviaStreakStates.waiting_protection_choice)
await state.update_data(streak=result['previous_streak'], question_idx=question_idx)

# State-based routing (filter on FSM state):
@router.callback_query(StreakProtectAcceptCallback.filter(), TriviaStreakStates.waiting_protection_choice)
async def handle_protection_accept(callback: CallbackQuery, callback_data: StreakProtectAcceptCallback, state: FSMContext):
    ...

# State clearing on exit:
await state.clear()
```

### Atomic Payment Pattern
**Source:** `services/besito_service.py:131-187`
**Apply to:** Protection payment in StreakPromotionService

```python
# services/besito_service.py:131-187 — atomic debit with commit=False
besito_service = BesitoService(db)
if not besito_service.debit_besitos(
    user_id=user_id,
    amount=cost,
    source=TransactionSource.STREAK_PROTECTION,
    description=f"Proteccion de racha streak={streak}",
    commit=False  # Defer commit for atomicity with session update
):
    return False  # Insufficient balance
# Then update session and commit both:
session.protection_used = True
db.commit()
```

### CallbackData Naming Convention
**Source:** `keyboards/callback_data.py` (entire file)
**Apply to:** All new callback classes

```python
# Prefix convention: lowercase_snake_case matching class purpose
# TriviaAnswerCallback → prefix="trivia_answer"
# StreakProtectAcceptCallback → prefix="streak_protect_accept"
# StreakRetireCallback → prefix="streak_retire"
```

### Keyboard Return Pattern
**Source:** `keyboards/inline_keyboards.py:475-487` (trivia_keyboard)
**Apply to:** All new keyboards

```python
# Always include a back/return button
def protection_keyboard(...) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="...", callback_data=...)],  # Action row
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

---

## Anti-Patterns to Avoid (verified from codebase + research)

| Anti-Pattern | Why Forbidden | Where Documented |
|-------------|---------------|------------------|
| Direct DB access in handlers | Violates handler/service/model separation | `CLAUDE.md`, `handlers/CLAUDE.md` |
| Logic in handlers beyond 1 service call | Handlers only route events | `CLAUDE.md`, `handlers/CLAUDE.md` |
| Raw SQL instead of ORM | Project standard is SQLAlchemy ORM | `models/CLAUDE.md` |
| Copy-pasting session logic across 3 play methods | Must factor into shared `_handle_streak_failure()` in GameService | RESEARCH.md Pitfall 3 |
| JSON column mutation without re-assignment (`codes.append()` without `session.codes_delivered = json.dumps(codes)`) | SQLAlchemy change tracking misses in-place mutations | RESEARCH.md Pitfall 4 |
| Per-session scheduled job for timeout | Creates DB-scheduler coupling. Use lazy check with `expires_at` | RESEARCH.md Pattern 2 |
| Creating session on `get_trivia_entry_data()` | Generates empty sessions. Create in `claim_for_streak()` or on first answer | RESEARCH.md Pitfall 2 |
| Enum value added in same migration as table | Must follow enum-first migration per `models/CLAUDE.md` | `models/CLAUDE.md` |

---

## No Analog Found

None. All files have close analogs in the existing codebase. The codebase already has:
- FSM StatesGroup patterns in every admin handler
- Atomic payment patterns in BesitoService
- Streak promotion code delivery in StreakPromotionService
- Trivia handlers with callback data and inline keyboards
- Alembic enum-first migrations for TransactionSource
- Table creation + FK migration patterns for streak_promotions

---

## Metadata

**Analog search scope:** `models/`, `services/`, `handlers/`, `keyboards/`, `alembic/versions/`
**Files scanned:** 12 source files + 2 migration files
**Pattern extraction date:** 2026-05-23
**Dependency:** Phase 17 (streak promotions system) — already implemented and verified functional
