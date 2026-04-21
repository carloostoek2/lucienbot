---
phase: 16
plan: 16-01b
wave: 2
depends_on: ["16-01a"]
files_modified:
  - handlers/engagement_user_handlers.py
  - handlers/engagement_admin_handlers.py
  - keyboards/inline_keyboards.py
  - utils/lucien_voice.py
  - bot.py
  - handlers/__init__.py
autonomous: true
type: auto
must_haves:
  - User sees "Ritmo Diario" in main menu and can view claim status
  - User receives elegant Lucien-voice messages for claim success, streak broken, and streak recovered
  - Admin can view Ritmo configuration through a pure handler
---

# Plan 16-01b: Ritmo Diario — Handlers, Keyboards, Voice, and Bot Wiring

**Objective:** Wire the Ritmo Diario feature into the Telegram bot UI with pure handlers, keyboard updates, Lucien voice messages, and router registration.

**Requirements mapped:** ENG-01, ENG-07

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section I (Ritmo Diario)
- `handlers/gamification_user_handlers.py` (handler purity pattern)
- `services/daily_gift_service.py`

---

<task>
<name>Add LucienVoice messages and update keyboard with Ritmo Diario</name>
<files>utils/lucien_voice.py, keyboards/inline_keyboards.py</files>
<action>
1. Add to `utils/lucien_voice.py` inside the `LucienVoice` class:

```python
@staticmethod
def ritmo_menu(status: dict) -> str:
    can_claim = status.get('can_claim')
    base = status.get('base_amount', 0)
    passive = status.get('passive_amount', 0)
    streak = status.get('streak', 0)
    multiplier = status.get('multiplier_percent', 0)
    total = status.get('total_amount', 0)
    if can_claim:
        return f"""🎩 <b>Lucien:</b>

<i>El ritmo de Diana lo espera...</i>

🌙 <b>Ritmo Diario</b>
💋 Base: {base} besitos
💤 Pasivo acumulado: {passive} besitos
🔥 Racha actual: {streak} días (+{multiplier}%)
✨ <b>Total a reclamar:</b> {total} besitos

<i>No deje besitos en la mesa.</i>"""
    else:
        msg = status.get('message', 'Aún no puede reclamar.')
        return f"""🎩 <b>Lucien:</b>

<i>La paciencia también tiene su recompensa...</i>

⏳ <b>Ritmo Diario</b>

{msg}

<i>Vuelva cuando el tiempo lo permita.</i>"""

@staticmethod
def ritmo_claimed(amount: int, passive: int, streak: int, balance: int) -> str:
    return f"""🎩 <b>Lucien:</b>

<i>Diana se complace con su constancia...</i>

✅ <b>Ritmo Diario reclamado</b>
💋 Besitos recibidos: {amount}
💤 Pasivo incluido: {passive}
🔥 Racha actual: {streak} días
💰 Saldo: {balance} besitos

<i>Mañana habrá más para quien regrese.</i>"""

@staticmethod
def ritmo_streak_broken() -> str:
    return """🎩 <b>Lucien:</b>

<i>El tiempo se interpone entre usted y la racha...</i>

💔 <b>Racha perdida</b>

<i>Pero cada día es una nueva oportunidad de comenzar.</i>"""

@staticmethod
def ritmo_streak_recovered() -> str:
    return """🎩 <b>Lucien:</b>

<i>Diana ha decidido perdonar una ausencia...</i>

💎 <b>Racha recuperada</b>

<i>Use este favor con sabiduría; no siempre se concede.</i>"""
```

2. In `keyboards/inline_keyboards.py`, inside `main_menu_keyboard()`, modify the row that currently has "Mi saldo de besitos" and "Regalo diario" to also include "Ritmo Diario":

Change:
```python
    # Mi saldo - Regalo diario (misma fila)
    buttons.append([
        InlineKeyboardButton(
            text="💋 Mi saldo de besitos",
            callback_data="my_balance"
        ),
        InlineKeyboardButton(
            text="🎁 Regalo diario",
            callback_data="daily_gift"
        )
    ])
```

To:
```python
    # Ritmo Diario - Regalo diario (misma fila)
    buttons.append([
        InlineKeyboardButton(
            text="🌙 Ritmo Diario",
            callback_data="ritmo_diario"
        ),
        InlineKeyboardButton(
            text="🎁 Regalo diario",
            callback_data="daily_gift"
        )
    ])
```
</action>
<verify>
<command>grep -c "ritmo_menu\|ritmo_claimed\|ritmo_streak_broken\|ritmo_streak_recovered" utils/lucien_voice.py</command>
<expected>4</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Create engagement_user_handlers.py with Ritmo handlers</name>
<files>handlers/engagement_user_handlers.py</files>
<action>
Create `handlers/engagement_user_handlers.py`:

```python
"""
Handlers de Engagement para Usuarios - Lucien Bot
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.daily_gift_service import DailyGiftService
from services.vip_service import VIPService
from keyboards.inline_keyboards import back_keyboard
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()


def _is_vip(user_id: int) -> bool:
    vip_service = VIPService()
    try:
        return vip_service.is_user_vip(user_id)
    finally:
        vip_service.close()


@router.callback_query(F.data == "ritmo_diario")
async def ritmo_menu(callback: CallbackQuery):
    """Muestra el menú de Ritmo Diario"""
    user_id = callback.from_user.id
    is_vip = _is_vip(user_id)

    gift_service = DailyGiftService()
    try:
        status = gift_service.get_ritmo_status(user_id, is_vip=is_vip)
    finally:
        gift_service.close()

    text = LucienVoice.ritmo_menu(status)

    if status.get("can_claim"):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌙 Reclamar Ritmo", callback_data="claim_ritmo")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")]
        ])
    else:
        keyboard = back_keyboard("back_to_main")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "claim_ritmo")
async def ritmo_claim(callback: CallbackQuery):
    """Procesa el reclamo del Ritmo Diario"""
    user_id = callback.from_user.id
    is_vip = _is_vip(user_id)

    gift_service = DailyGiftService()
    try:
        result = await gift_service.claim_ritmo(user_id, is_vip=is_vip, bot=callback.bot)
    finally:
        gift_service.close()

    if result.get("success"):
        text = LucienVoice.ritmo_claimed(
            amount=result.get("amount", 0),
            passive=result.get("passive", 0),
            streak=result.get("streak", 0),
            balance=result.get("balance", 0)
        )
    else:
        text = f"""🎩 <b>Lucien:</b>

<i>{result.get('message', 'No se pudo reclamar el Ritmo Diario.')}</i>"""

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("back_to_main"),
        parse_mode="HTML"
    )
    await callback.answer()
```
</action>
<verify>
<command>python -c "from handlers.engagement_user_handlers import router; print('router ok')"</command>
<expected>router ok</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Create engagement_admin_handlers.py with Ritmo config handlers</name>
<files>handlers/engagement_admin_handlers.py</files>
<action>
Create `handlers/engagement_admin_handlers.py`:

```python
"""
Handlers de Engagement para Administradores - Lucien Bot
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from services.daily_gift_service import DailyGiftService
from keyboards.inline_keyboards import back_keyboard
from utils.lucien_voice import LucienVoice
from utils.helpers import is_admin
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "admin_ritmo_config")
async def admin_ritmo_config(callback: CallbackQuery):
    """Muestra configuración actual del Ritmo Diario"""
    if not is_admin(callback.from_user.id):
        await callback.answer(LucienVoice.not_admin_error(), show_alert=True)
        return

    service = DailyGiftService()
    try:
        config = service.get_config()
    finally:
        service.close()

    text = f"""🎩 <b>Lucien:</b>

<i>Configuración del Ritmo Diario...</i>

💋 Besitos base: {config.besito_amount}
🔄 Activo: {'Sí' if config.is_active else 'No'}

<i>Use el comando adecuado para modificar.</i>"""

    await callback.message.edit_text(text, reply_markup=back_keyboard("admin_gamification"), parse_mode="HTML")
    await callback.answer()
```
</action>
<verify>
<command>python -c "from handlers.engagement_admin_handlers import router; print('router ok')"</command>
<expected>router ok</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Register engagement routers in bot.py and handlers/__init__.py</name>
<files>bot.py, handlers/__init__.py</files>
<action>
1. In `handlers/__init__.py`:
   - Add imports:
     ```python
     from .engagement_user_handlers import router as engagement_user_router
     from .engagement_admin_handlers import router as engagement_admin_router
     ```
   - Add both to `__all__`

2. In `bot.py`:
   - Add to the imports from `handlers`:
     ```python
     engagement_user_router,
     engagement_admin_router,
     ```
   - Add to `dp.include_router` calls:
     ```python
     dp.include_router(engagement_user_router)
     dp.include_router(engagement_admin_router)
     ```
     Place them near the gamification routers.
</action>
<verify>
<command>python -c "from bot import main; print('import ok')"</command>
<expected>import ok</expected>
</verify>
<done>false</done>
</task>
