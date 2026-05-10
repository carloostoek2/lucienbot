# Phase 17: Promociones por Racha - Research

**Researched:** 2026-05-09
**Domain:** Trivia streak promotions, discount code generation, time-bounded trivia events
**Confidence:** HIGH

## Summary

Phase 17 introduces a standalone streak-based promotion system for trivia, completely independent of the existing commercial `Promotion` model. The system allows admins to create time-bounded promotions with configurable streak levels that award unique discount codes when users reach consecutive-correct-answer milestones. 

The key architectural challenge is the hook point: the streak promotion check must fire after a correct trivia answer updates the user's streak count, without coupling the trivia domain to the promotion domain. The recommended approach is a direct service-to-service call from `GameService` to the new `StreakPromotionService` after streak calculation, keeping the coupling minimal (single method call, one direction). 

The promotion's `is_active` state is managed by APScheduler `DateTrigger` jobs for automatic activation/deactivation, and when a promotion is active and has an associated `TriviaCategory`, the category is auto-activated for the duration of the promotion.

**Primary recommendation:** Create new models (`StreakPromotion`, `StreakPromotionLevel`, `StreakPromotionCode`), new service (`StreakPromotionService`), new handler file (`trivia_streak_admin_handlers.py`), and hook into `GameService` via a single `post_streak_check()` call.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Modelo de Datos
- **D-01:** Nuevo modelo `StreakPromotion` independiente del modelo `Promotion` existente. Tabla propia con: nombre, duracion (fechas o relativa), set de preguntas asociado.
- **D-02:** Nuevo modelo `StreakPromotionLevel` relacionado 1:N con `StreakPromotion`. Cada nivel define: preguntas_consecutivas_requeridas (int), porcentaje_descuento (int), codigos_disponibles (int).
- **D-03:** Nuevo modelo `StreakPromotionCode` para codigos de descuento generados. Cada codigo es unico y tiene estado (disponible/entregado/usado).
- **D-04:** Nuevo modelo `StreakPromotionRedemption` para historial de canjeos por usuario: codigo entregado, racha alcanzada, fecha, estado del codigo.

#### Duracion
- **D-05:** Dos modos de vigencia: fechas concretas (start_date, end_date con hora) O duracion relativa (horas o dias desde activacion).
- **D-06:** Una promocion solo esta activa durante su vigencia. Fuera de vigencia no se evaluan rachas ni se entregan codigos.

#### Asociacion con Trivia
- **D-07:** Cada `StreakPromotion` se asocia a un `category_id` de `TriviaCategory` (o `null` para el mazo general).
- **D-08:** El set de preguntas asociado se activa unicamente durante la duracion de la promocion.
- **D-09:** Fuera del periodo de la promocion, el sistema vuelve automaticamente al paquete de preguntas por defecto.

#### Codigos de Descuento
- **D-10:** Los codigos se generan al crear la promocion (no al alcanzar la racha). Todos los codigos para todos los niveles se generan upfront.
- **D-11:** Cada codigo es unico a nivel sistema (no solo dentro de una promocion).
- **D-12:** Los codigos no se descuentan automaticamente al entregarse -- solo cuando el administrador marca un codigo como "usado" se descuenta del total configurado.
- **D-13:** El conteo de "codigos disponibles" mostrado al admin refleja: total_configurado - codigos_entregados.

#### Rachas y Entrega
- **D-14:** Cuando un usuario alcanza una racha que coincide con un nivel de una promocion activa, se le notifica y se le asigna un codigo de descuento.
- **D-15:** Un usuario solo puede recibir un codigo por nivel de promocion (no se entregan multiples codigos del mismo nivel al mismo usuario).
- **D-16:** El historial de rachas y codigos canjeados se registra para evitar duplicidades y abusos.

### Claude's Discretion
- Formato de los codigos de descuento (longitud, caracteres, prefijo)
- Diseno exacto de la UI del panel de administracion para gestion de estas promociones
- Como se notifica al usuario que alcanzo una racha y recibio un codigo
- Si el codigo se entrega como mensaje automatico o el admin lo revisa primero
- Integracion con el scheduler para activacion/desactivacion automatica por fechas

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

TBD (PRD-driven phase). The PRD at `docs/SPEC_fase_17.md` describes the full feature but does not define requirement IDs. These will be assigned during planning.

Key functional areas identified:
1. Model creation (4 new tables)
2. Code generation (unique, upfront per level)
3. Streak hook integration (after correct answer in GameService)
4. Admin interface (create, list, view stats, deactivate)
5. Scheduler integration (auto-activate/deactivate by date/duration)
6. User notification on code delivery
7. Category auto-activation during promotion period
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Streak calculation | API (GameService) | — | Existing `_get_trivia_streak()` and `_get_simple_trivia_streak()` already calculate streaks after each answer |
| Promotion eligibility check | API (StreakPromotionService) | — | New service checks active promotions against streak value after correct answer |
| Code generation | API (StreakPromotionService) | — | Generated upfront at promotion creation time, stored in DB |
| Activation/deactivation timing | API (SchedulerService) | — | APScheduler DateTrigger jobs handle auto-activation based on date or relative duration |
| Category auto-activation | API (TriviaCategoryService) | — | StreakPromotionService calls TriviaCategoryService.activate() during promotion window |
| Admin UI | Browser (inline keyboards) | — | aiogram inline keyboard callbacks, same pattern as existing admin handlers |
| User notification | API (aiogram Bot) | — | Direct message to user via bot.send_message when code is delivered |
| Data storage | Database (PostgreSQL/SQLite) | — | 4 new SQLAlchemy models, Alembic migration |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.x | ORM models | Existing project standard for all models |
| Alembic | 1.x | Database migrations | Existing project standard |
| aiogram | 3.x | Telegram bot framework | Existing project standard |
| APScheduler | 3.x | Job scheduling | Existing standard via SchedulerService pattern |
| Python | 3.11+ | Runtime | Existing project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid (stdlib) | — | Unique code generation | For generating unique discount codes |
| secrets (stdlib) | — | Cryptographic random strings | For discount code tokens |
| datetime (stdlib) | — | Date/time handling | For promotion duration calculations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct service call (GameService -> StreakPromotionService) | Event bus / signal pattern | Direct call is simpler, fits existing project patterns (services already call other services, e.g., GameService calls BesitoService). Event bus would add infrastructure complexity with no benefit at current scale. |

**Installation:**
```bash
# No new libraries needed. All dependencies are already in the project.
```

## Architecture Patterns

### System Architecture Diagram

```
Admin creates StreakPromotion
        |
        v
  StreakPromotionService
        |
        ├── Generates codes upfront (D-10)
        ├── Schedules activation/deactivation via SchedulerService
        └── Stores to DB (4 new tables)
        
        === DURING PROMOTION LIFECYCLE ===
        
        [SchedulerService]
        Scheduler fires DateTrigger    ──►  StreakPromotionService
        (start date reached)                  │
                                             ├── Sets promotion.is_active = True
                                             └── Calls TriviaCategoryService.activate(category_id) [D-08]
        
        === AFTER CORRECT TRIVIA ANSWER ===
        
  GameService.play_trivia*()  
        │
        ├── Calculates new_streak
        ├── Credits besitos (existing logic)
        └── Calls StreakPromotionService.claim(user_id, game_type, streak)
                 │
                 ├── Checks: is any active promotion configured for this game_type?
                 ├── Checks: has user already claimed this level?
                 ├── Checks: are codes available for this level?
                 │
                 └── If eligible:
                      ├── Marks code as 'delivered' (user_id, delivered_at)
                      ├── Creates StreakPromotionRedemption record
                      └── Returns code to GameService for user notification
        
  GameService                              ──►  User receives code notification
       (includes code in result data)
       
        === PROMOTION EXPIRY ===
        
  [SchedulerService]
  Scheduler fires DateTrigger    ──►  StreakPromotionService
  (end date reached OR                    │
   duration expired)                      ├── Sets promotion.is_active = False
                                          └── Calls TriviaCategoryService.deactivate() [D-09]
```

### Recommended Project Structure

```
src/
├── models/models.py              # +4 new models: StreakPromotion, StreakPromotionLevel,
                                  #  StreakPromotionCode, StreakPromotionRedemption
├── services/
│   ├── __init__.py               # +register StreakPromotionService
│   ├── streak_promotion_service.py  # NEW: Domain service for streak promotions
│   └── scheduler_service.py      # +job handlers for auto-activation/deactivation
├── handlers/
│   ├── __init__.py               # +register trivia_streak_admin_router
│   ├── game_user_handlers.py     # +call StreakPromotionService after correct answer
│   ├── game_service.py           # +post_streak_check() call to StreakPromotionService
│   └── trivia_streak_admin_handlers.py  # NEW: Admin handlers for streak promo management
├── keyboards/
│   └── inline_keyboards.py       # +admin_menu button for streak promotions
├── bot.py                        # +register trivia_streak_admin_router
└── alembic/versions/
    └── 20260509_add_streak_promotions_tables.py  # NEW: Migration
```

### Pattern 1: Hook After Streak Calculation

**What:** After a correct trivia answer in `GameService`, check if the user's new streak qualifies for a promotion code from an active streak promotion.

**When to use:** After any `play_trivia*()` method calculates `new_streak` and before/after the `GameRecord` is committed.

**Example:**
```python
# In GameService.play_trivia_simple(), after streak calculation:
# (lines ~1249-1255 in game_service.py)

# After streak_bonus logic, before record creation:
code_data = None
if is_correct:
    from services.streak_promotion_service import StreakPromotionService
    promo_service = StreakPromotionService(self.db)
    try:
        code_data = promo_service.claim_for_streak(
            user_id=user_id,
            game_type='trivia_simple',
            streak=new_streak,
            category_id=category_id
        )
    finally:
        promo_service.close()
```

### Pattern 2: StreakPromotionService.claim_for_streak()

**What:** Core eligibility check and code delivery logic.

**When to use:** Called from GameService after every correct answer.

**Example:**
```python
# In StreakPromotionService
def claim_for_streak(self, user_id: int, game_type: str,
                      streak: int, category_id: str = None) -> Optional[dict]:
    """
    Check if user qualifies for a promotion code at this streak level.
    Returns {code, discount_pct, promotion_name} or None.
    """
    active_promos = self._get_active_promotions(game_type, category_id)
    for promo in active_promos:
        for level in promo.levels:
            if level.consecutive_required != streak:
                continue
            # Already claimed this level?
            if self._has_claimed_level(user_id, level.id):
                continue
            # Available codes?
            code = self._get_available_code(level.id)
            if not code:
                continue
            # Deliver
            code.user_id = user_id
            code.status = 'delivered'
            code.delivered_at = datetime.utcnow()
            self.db.add(code)
            redemption = StreakPromotionRedemption(
                user_id=user_id, level_id=level.id,
                code_id=code.id, streak_achieved=streak
            )
            self.db.add(redemption)
            self.db.commit()
            logger.info(f"streak_promo - claim - user:{user_id} - promo:{promo.id} - streak:{streak}")
            return {
                'code': code.code_value,
                'discount_pct': level.discount_pct,
                'promotion_name': promo.name
            }
    return None
```

### Pattern 3: Scheduler Auto-Activation

**What:** Use APScheduler DateTrigger jobs to activate/deactivate promotions automatically.

**When to use:** When a promotion is created or updated with date/duration parameters.

**Example:**
```python
# In StreakPromotionService
def schedule_promotion(self, promo_id: int, start_date: datetime = None,
                       end_date: datetime = None, duration_hours: int = None):
    """Schedule auto-activation and deactivation for a promotion."""
    from services.scheduler_service import get_scheduler
    
    if start_date:
        get_scheduler()._scheduler.add_job(
            _activate_streak_promotion,
            trigger=DateTrigger(run_date=start_date),
            id=f"streak_promo_activate_{promo_id}",
            replace_existing=True,
            kwargs={"promo_id": promo_id},
        )
    
    # Determine end date
    if duration_hours:
        effective_end = start_date + timedelta(hours=duration_hours)
    else:
        effective_end = end_date
    
    if effective_end:
        get_scheduler()._scheduler.add_job(
            _deactivate_streak_promotion,
            trigger=DateTrigger(run_date=effective_end),
            id=f"streak_promo_deactivate_{promo_id}",
            replace_existing=True,
            kwargs={"promo_id": promo_id},
        )
```

### Anti-Patterns to Avoid
- **Touching Promotion model:** The existing Promotion/PromotionService must not be modified. This is a hard constraint.
- **Putting promo logic in GameService:** Keep streak promotion logic in its own service domain. GameService only calls `claim_for_streak()`.
- **Generating codes on demand:** D-10 mandates upfront generation at promo creation time. Do not generate codes at streak claim time.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unique code generation | Custom algorithm | `secrets.token_hex(8)` or `uuid.uuid4().hex[:12]` | Project already uses `secrets` in `models/models.py:9-10` for token generation |
| Job scheduling | Custom timing loops | APScheduler `DateTrigger` via existing `SchedulerService` | Existing pattern proven in Phase 10 (free channel welcome) and Phase 9 (backup, expiry) |
| DB migrations | Manual ALTER TABLE | Alembic | Existing standard with `alembic revision --autogenerate` |
| Admin state management | Custom state tracking | aiogram FSM `StatesGroup` | Existing pattern used by BroadcastStates, MissionWizardStates, ProductWizardStates |

**Key insight:** This phase introduces zero new library dependencies. Every pattern (APScheduler, aiogram FSM, SQLAlchemy, Alembic, secrets-based code generation) is already established in the codebase.

## Common Pitfalls

### Pitfall 1: Category Activation Collision
**What goes wrong:** A StreakPromotion auto-activates a TriviaCategory, but there's already a Phase 16 active category from admin manual activation. The promotion deactivates the category at the end, interfering with the manually-set category.
**Why it happens:** Both Phase 16 admin interface and Phase 17 promo system can set `is_active` on the same `TriviaCategory` table.
**How to avoid:** When a StreakPromotion activates a category, store the previous active category state before changing it, and restore on deactivation. Or, document that Phase 17 promotions "take over" category activation during their window -- the admin is warned before creating a promotion that conflicts.
**Warning signs:** Post-promotion, the expected Phase 16 category is no longer active.

### Pitfall 2: Duplicate Code Delivery
**What goes wrong:** A user hits the same streak twice (restreaks after reset) and receives multiple codes for the same level.
**Why it happens:** Streaks reset daily -- a user could hit streak=5 on Monday and streak=5 again on Tuesday, both during the same active promotion.
**How to avoid:** D-15 is clear: one code per user per level. The `_has_claimed_level()` check in `claim_for_streak()` uses `StreakPromotionRedemption` table, which is user+level scoped. No time window -- once claimed, always claimed.
**Warning signs:** Multiple redemptions for same user+level appearing in admin view.

### Pitfall 3: Code Inventory Mismatch
**What goes wrong:** Admin views "20 codes available" when 15 are delivered (shown as 5 available per D-13: `total - delivered`), but actually 3 are also "used" by the admin. The admin thinks 5 are usable but only 2 are truly un-delivered and un-used.
**Why it happens:** D-12 says used codes don't decrement from available count until admin marks them. So the display logic needs: `total_configurado - codigos_entregados` (per D-13), not `total - delivered - used`.
**How to avoid:** Implement D-13 exactly: the "available" count shown to admin is `codes_disponibles - count(delivered)`. Used codes reduce from the "remaining usable" pool but don't affect the math for D-13.
**Warning signs:** Confusion between delivered, used, and available counts.

### Pitfall 4: Scheduler Job Persistence
**What goes wrong:** A promotion has activation/deactivation jobs scheduled via APScheduler with SQLAlchemyJobStore. The admin deletes the promotion via admin UI, but the scheduled jobs persist in the DB and fire, attempting to activate a deleted promotion.
**Why it happens:** APScheduler jobs in SQLAlchemyJobStore persist independently of application data.
**How to avoid:** When deleting a promotion, also call `scheduler.remove_job()` for both activate and deactivate jobs. Use a consistent job ID naming pattern like `streak_promo_activate_{id}` and `streak_promo_deactivate_{id}`.
**Warning signs:** Errors in scheduler logs about "promotion not found."

## Code Examples

### Model Definition Pattern

```python
# In models/models.py

class StreakPromotionStatus(str, enum.Enum):
    PENDING = "pending"     # Created, not yet started
    ACTIVE = "active"       # Within active window
    EXPIRED = "expired"     # Past end date
    PAUSED = "paused"       # Manually paused by admin


class StreakPromotion(Base):
    """Promocion por racha de trivia. Independiente del modelo Promotion."""
    __tablename__ = "streak_promotions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Duration mode: 'dates' or 'relative'
    duration_mode = Column(String(10), nullable=False, default='dates')
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    duration_hours = Column(Integer, nullable=True)  # For relative mode

    # Associated category (null = general deck)
    category_id = Column(String(50), nullable=True)

    # Status
    status = Column(Enum(StreakPromotionStatus), default=StreakPromotionStatus.PENDING)
    is_active = Column(Boolean, default=False)

    # Discovery questions
    include_general = Column(Boolean, default=True)
    include_vip = Column(Boolean, default=False)
    include_simple = Column(Boolean, default=True)

    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    levels = relationship("StreakPromotionLevel", back_populates="promotion",
                          cascade="all, delete-orphan",
                          order_by="StreakPromotionLevel.consecutive_required")


class StreakPromotionLevel(Base):
    """Nivel de racha dentro de una promocion."""
    __tablename__ = "streak_promotion_levels"

    id = Column(Integer, primary_key=True, index=True)
    promotion_id = Column(Integer, ForeignKey("streak_promotions.id"), nullable=False)
    consecutive_required = Column(Integer, nullable=False)  # e.g., 5, 10, 15
    discount_pct = Column(Integer, nullable=False)  # e.g., 30, 50, 70
    codes_available = Column(Integer, nullable=False)  # Total codes configured

    promotion = relationship("StreakPromotion", back_populates="levels")
    codes = relationship("StreakPromotionCode", back_populates="level",
                         cascade="all, delete-orphan")


class StreakPromotionCodeStatus(str, enum.Enum):
    AVAILABLE = "available"
    DELIVERED = "delivered"
    USED = "used"


class StreakPromotionCode(Base):
    """Codigo de descuento unico generado para una promocion."""
    __tablename__ = "streak_promotion_codes"

    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("streak_promotion_levels.id"), nullable=False)
    code_value = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(Enum(StreakPromotionCodeStatus), default=StreakPromotionCodeStatus.AVAILABLE)
    user_id = Column(BigInteger, nullable=True)  # Who received it
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by_admin = Column(BigInteger, nullable=True)

    level = relationship("StreakPromotionLevel", back_populates="codes")


class StreakPromotionRedemption(Base):
    """Historial de rachas y codigos canjeados por usuario."""
    __tablename__ = "streak_promotion_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("streak_promotion_levels.id"), nullable=False)
    code_id = Column(Integer, ForeignKey("streak_promotion_codes.id"), nullable=False)
    streak_achieved = Column(Integer, nullable=False)
    redeemed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'level_id', name='uq_streak_redemption_user_level'),
    )
```

### Hook Integration Pattern (in GameService)

```python
# In GameService.play_trivia_simple(), add after streak_bonus logic (~line 1282):

# === Phase 17: Streak Promotion check ===
promo_code_info = None
if is_correct:
    from services.streak_promotion_service import StreakPromotionService
    promo_service = StreakPromotionService(self.db)
    try:
        promo_code_info = promo_service.claim_for_streak(
            user_id=user_id,
            game_type='trivia_simple',
            streak=new_streak,
            category_id=category_id,
        )
    finally:
        promo_service.close()
# ========================================
```

### Admin Handler Pattern (aiogram FSM)

```python
# In handlers/trivia_streak_admin_handlers.py

from aiogram.fsm.state import State, StatesGroup


class StreakPromotionStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_levels = State()  # Repeatable: ask for streak count, discount, codes
    waiting_duration_mode = State()  # 'dates' or 'relative'
    waiting_start_date = State()
    waiting_end_date = State()
    waiting_duration_value = State()
    waiting_duration_unit = State()  # 'hours' or 'days'
    waiting_category = State()
    waiting_game_types = State()
    waiting_confirmation = State()


@router.callback_query(F.data == "admin_streak_promotions",
                       lambda cb: is_admin(cb.from_user.id))
async def admin_streak_promotions_menu(callback: CallbackQuery):
    """Main menu for streak promotion management."""
    with get_service(StreakPromotionService) as service:
        promotions = service.get_all_promotions()

    text = "🏆 <b>Promociones por Racha</b>\n\n"
    if promotions:
        for promo in promotions:
            status_icon = "🟢" if promo.is_active else "🔴"
            text += f"{status_icon} <b>{promo.name}</b>\n"
            text += f"   Niveles: {len(promo.levels)} | Categoria: {promo.category_id or 'General'}\n"
            text += f"   Vigencia: {promo.start_date} - {promo.end_date}\n\n"
    else:
        text += "No hay promociones configuradas.\n"

    buttons = [
        [InlineKeyboardButton(text="➕ Crear nueva promocion", callback_data="streak_promo_create")],
        [InlineKeyboardButton(text="🔙 Panel de administracion", callback_data="back_to_admin")],
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()
```

### Code Generation Pattern

```python
# In StreakPromotionService._generate_codes()
import secrets
import string

def _generate_code(self, prefix: str = "SK") -> str:
    """Generate a unique discount code.
    
    Format: {PREFIX}-{12 hex chars} e.g., SK-a3f8c9e1b2d4
    Uniqueness enforced by DB unique constraint.
    """
    random_part = secrets.token_hex(6)  # 12 hex characters
    return f"{prefix}-{random_part}"


def _pre_generate_codes(self, level: StreakPromotionLevel, prefix: str):
    """Generate all codes for a level upfront (D-10)."""
    existing = len(level.codes)
    needed = level.codes_available - existing
    for _ in range(needed):
        code = StreakPromotionCode(
            level_id=level.id,
            code_value=self._generate_code(prefix),
            status=StreakPromotionCodeStatus.AVAILABLE,
        )
        self.db.add(code)
    self.db.commit()
```

### Scheduler Job Handler Pattern

```python
# In services/scheduler_service.py (module-level function)

async def _activate_streak_promotion(promo_id: int):
    """Activate a streak promotion. Called by APScheduler DateTrigger."""
    db = SessionLocal()
    try:
        from services.streak_promotion_service import StreakPromotionService
        service = StreakPromotionService(db)
        service.activate(promo_id)
        logger.info(f"streak_promo auto-activated: promo_id={promo_id}")
    except Exception as e:
        logger.error(f"Error activating streak promo {promo_id}: {e}")
    finally:
        db.close()


async def _deactivate_streak_promotion(promo_id: int):
    """Deactivate a streak promotion. Called by APScheduler DateTrigger.
    Also deactivates the associated category if applicable (D-09)."""
    db = SessionLocal()
    try:
        from services.streak_promotion_service import StreakPromotionService
        service = StreakPromotionService(db)
        service.deactivate(promo_id)
        logger.info(f"streak_promo auto-deactivated: promo_id={promo_id}")
    except Exception as e:
        logger.error(f"Error deactivating streak promo {promo_id}: {e}")
    finally:
        db.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual category activation via admin panel (Phase 16) | Auto-activation via StreakPromotion lifecycle | Phase 17 | Categories can now be activated by two systems -- need to handle handoff |
| GameService standalone trivia processing | GameService + StreakPromotionService chained after streak | Phase 17 | Added single method call, no architectural change |
| Promotion system (Phase 6) only handles commercial promos | New separate system for trivia streak promos | Phase 17 | Two independent promo systems coexist |

**Deprecated/outdated:**
- Nothing is deprecated. The existing `Promotion` model and `PromotionService` remain untouched.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `GameService` can import and call `StreakPromotionService` directly without creating circular imports | Architecture Patterns | LOW -- `services/__init__.py` centrally registers all services, but imports within methods (lazy) avoid circular deps entirely |
| A2 | APScheduler `DateTrigger` jobs for activation schedule can be added at promotion creation time and removed at deletion | Code Examples | LOW -- same pattern used for `_send_free_welcome_job` in Phase 10 |
| A3 | The new models do not require new enum values in `TransactionSource` | Standard Stack | LOW -- the promotion codes are for external discounts, not besitos. No besitos transactions involved |
| A4 | Promotions can be created with 0 levels and levels can be added incrementally | Model Design | LOW -- `StreakPromotionLevel` cascade delete handles this, but admin UI should validate at least 1 level |
| A5 | `StreakPromotionRedemption.__table_args__` unique constraint on (user_id, level_id) is sufficient for D-15 | Code Examples | MEDIUM -- if streaks are tracked by game_type and a user could hit the same streak in different game types, need to clarify if same-level-different-game counts as "same level." Per D-15, it's per level, not per game_type, so unique constraint is correct |

## Open Questions (RESOLVED)

1. **Streak reset edge case:**
   - What we know: D-15 says one code per user per level. Streaks reset daily.
   - What's unclear: If a user gets streak=5 on Day 1, and hits streak=5 again on Day 2 during the same promotion, should they get another code? Per D-15, no.
   - RESOLVED: Implement as claimed -- `unique(user_id, level_id)` constraint prevents duplicates regardless of time window.

2. **Category priority when both Phase 16 admin and Phase 17 promo set a category:**
   - What we know: Phase 16 admin can manually activate; Phase 17 auto-activates during promo window.
   - What's unclear: What happens when a promo ends -- does it restore the previous manually-set category, or just deactivate entirely?
   - RESOLVED: Save the previous active category state before promo activation, restore on deactivation. Document that promo activation "takes over" and admin should not manually change categories during an active strek promotion.

3. **Game types for promotion:**
   - What we know: `include_general`, `include_vip`, `include_simple` boolean columns allow choosing which trivia modes participate.
   - What's unclear: Should the promotion be able to target ALL game types by default, or require explicit selection?
   - RESOLVED: Default to general + simple only (exclude VIP trivia). Admin can toggle via keyboard.

4. **Code delivery channel:**
   - What we know: D-14 says user should be notified when they receive a code.
   - What's unclear: Should the code be sent inline in the trivia result message, as a separate private message, or both?
   - RESOLVED: Include code info in the trivia result message's data dict; the handler (game_user_handlers) appends it to the response message. This keeps it in context of the achievement.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All code | Yes | (check current) | — |
| SQLAlchemy | Models | Yes | (project dep) | — |
| Alembic | Migrations | Yes | (project dep) | — |
| aiogram | Bot handlers | Yes | (project dep) | — |
| APScheduler | Auto-activation | Yes | (project dep) | — |

**Missing dependencies with no fallback:**
- None -- all dependencies are already in the project.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing project standard) |
| Config file | `pytest.ini` (project root) |
| Quick run command | `pytest tests/services/test_streak_promotion_service.py -x -v` |
| Full suite command | `pytest -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| PRD-01 | Promo creation with levels and upfront code generation | unit | `pytest tests/services/test_streak_promotion_service.py::test_create_promotion -x` |
| PRD-02 | Streak eligibility check (correct streak value, active promo) | unit | `pytest tests/services/test_streak_promotion_service.py::test_claim_for_streak -x` |
| PRD-03 | Duplicate prevention (same user + level) | unit | `pytest tests/services/test_streak_promotion_service.py::test_prevent_duplicate_claim -x` |
| PRD-04 | Code uniquness at system level | unit | `pytest tests/services/test_streak_promotion_service.py::test_code_uniqueness -x` |
| PRD-05 | Inactive promotion does not deliver codes | unit | `pytest tests/services/test_streak_promotion_service.py::test_inactive_promo -x` |
| PRD-06 | Auto-activation via scheduler | integration | `pytest tests/services/test_streak_promotion_service.py::test_auto_activation -x` |
| PRD-07 | Code inventory counting (D-13) | unit | `pytest tests/services/test_streak_promotion_service.py::test_available_count -x` |

### Sampling Rate
- **Per task commit:** `pytest tests/services/test_streak_promotion_service.py -x -v`
- **Per wave merge:** `pytest -x -v`
- **Phase gate:** Full suite green before /gsd-verify-work

### Wave 0 Gaps
- [ ] `tests/services/test_streak_promotion_service.py` -- covers all unit tests
- [ ] `tests/handlers/test_trivia_streak_admin_handlers.py` -- integration tests for admin flow
- [ ] Fixtures: `sample_streak_promotion()`, `sample_level()`, `sample_code()` in `tests/conftest.py` or a dedicated conftest

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | Validate all admin input (levels, dates, codes count) server-side |
| V3 Session Management | Yes | FSM states for admin wizard (existing aiogram FSM pattern) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Duplicate code claim | Tampering | DB unique constraint on (user_id, level_id) + server-side check before delivery |
| Unauthorized admin access | Spoofing | `is_admin()` check on every admin callback (existing pattern) |
| Code guessing | Information Disclosure | Codes use `secrets.token_hex(6)` (128-bit entropy) -- practically unguessable |

No new besitos transactions, authentication, or cryptography are involved. The code is a string token for external use (discount at point of sale), not a cryptographically validated credential.

## Sources

### Primary (HIGH confidence)
- `docs/SPEC_fase_17.md` -- PRD with all feature specifications
- `services/game_service.py` -- Existing trivia streak calculation and daily limits (lines 310-330, 1162-1171, 680-783, 1223-1314)
- `services/trivia_service.py` -- TriviaCategoryService activation/deactivation pattern (Phase 16)
- `models/models.py` -- Existing model patterns (Promotion at lines 722-787, GameRecord at lines 1089-1099, TriviaCategory at lines 1101-1111)
- `services/scheduler_service.py` -- APScheduler DateTrigger pattern (lines 298-313)
- `handlers/trivia_admin_handlers.py` -- Admin handler pattern for Phase 16
- `handlers/admin_handlers.py` -- Admin menu and is_admin() pattern (lines 39-41)
- `keyboards/inline_keyboards.py` -- admin_menu_keyboard pattern (lines 79-123)
- `services/__init__.py` -- Service registration and get_service pattern
- `handlers/__init__.py` -- Router registration pattern
- `bot.py` -- Router include pattern (lines 234-271)
- `models/CLAUDE.md` -- Migration rules, enum-first pattern
- `.planning/config.json` -- nyquist_validation: true

### Secondary (MEDIUM confidence)
- `alembic/versions/20260509_add_trivia_categories_table.py` -- Last migration, revision chain head

### Tertiary (LOW confidence)
- None -- all findings verified against codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed, all patterns verified in codebase
- Architecture: HIGH -- hook pattern, service structure, scheduler integration all match existing codebase patterns
- Pitfalls: MEDIUM -- category collision risk is inferred from combining Phase 16 and Phase 17 features; inventory naming conflicts documented per D-12/D-13

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (standard 30-day validity for mature project)
