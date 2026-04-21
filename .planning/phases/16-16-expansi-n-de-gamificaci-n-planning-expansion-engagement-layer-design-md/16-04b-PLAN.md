---
phase: 16
plan: 16-04b
wave: 5
depends_on: ["16-04a"]
files_modified:
  - handlers/engagement_user_handlers.py
  - handlers/engagement_admin_handlers.py
  - keyboards/inline_keyboards.py
  - utils/lucien_voice.py
autonomous: true
type: auto
must_haves:
  - User sees "Susurros de Diana" in main menu and can view claim eligibility
  - User receives Lucien-voice feedback when claiming a whisper or hitting the daily limit
  - Admin can view whisper reward pools through a pure handler that calls exactly 1 service method
---

# Plan 16-04b: Susurros de Diana — Handlers, Keyboards, Voice, and Admin UI

**Objective:** Wire the Susurros de Diana feature into the Telegram bot UI with pure handlers, keyboard updates, and Lucien voice messages.

**Requirements mapped:** ENG-04, ENG-07

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section IV (Susurros de Diana)
- `services/reward_service.py`
- `handlers/gamification_user_handlers.py`

---

<task>
<name>Add LucienVoice messages for Susurros</name>
<files>utils/lucien_voice.py</files>
<action>
Add to `utils/lucien_voice.py` inside `LucienVoice`:

```python
    @staticmethod
    def susurros_menu(can_claim: dict) -> str:
        free_ok = can_claim.get("free_daily")
        vip_ok = can_claim.get("vip_daily")
        text = """🎩 <b>Lucien:</b>

<i>Diana tiene susurros para quienes se acercan con constancia...</i>

🌙 <b>Susurros de Diana</b>

"""
        if free_ok:
            text += "✅ Susurro diario disponible\n"
        else:
            text += "⏳ Susurro diario ya reclamado\n"
        if vip_ok:
            text += "💎 Susurro VIP disponible\n"
        elif can_claim.get("vip_claimed_today", 0) > 0:
            text += "⏳ Susurro VIP ya reclamado\n"
        return text

    @staticmethod
    def susurro_claimed(reward_name: str, message: str) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>El susurro de Diana ha llegado a sus oídos...</i>

🎁 <b>Recompensa:</b> {reward_name}

<i>{message}</i>

<i>Mañana habrá otro secreto esperando.</i>"""

    @staticmethod
    def susurro_limit_reached() -> str:
        return """🎩 <b>Lucien:</b>

<i>Los susurros de Diana son finitos cada día...</i>

⏳ <b>Límite alcanzado</b>

<i>Vuelva mañana para escuchar más.</i>"""
```
</action>
<verify>
<command>grep -c "susurros_menu\|susurro_claimed\|susurro_limit_reached" utils/lucien_voice.py</command>
<expected>3</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Update main menu keyboard with Susurros button</name>
<files>keyboards/inline_keyboards.py</files>
<action>
In `keyboards/inline_keyboards.py`, inside `main_menu_keyboard()`, modify the row that has Ritmo Diario and Regalo diario to a 3-button row:

```python
    # Ritmo Diario - Susurros - Regalo diario
    buttons.append([
        InlineKeyboardButton(
            text="🌙 Ritmo Diario",
            callback_data="ritmo_diario"
        ),
        InlineKeyboardButton(
            text="🌙 Susurros",
            callback_data="susurros_diana"
        ),
        InlineKeyboardButton(
            text="🎁 Regalo diario",
            callback_data="daily_gift"
        )
    ])
```
</action>
<verify>
<command>grep -c "susurros_diana" keyboards/inline_keyboards.py</command>
<expected>1</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add Susurros handlers to engagement_user_handlers.py</name>
<files>handlers/engagement_user_handlers.py</files>
<action>
Append to `handlers/engagement_user_handlers.py`:

```python
from services.reward_service import RewardService


@router.callback_query(F.data == "susurros_diana")
async def susurros_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_vip = _is_vip(user_id)

    reward_service = RewardService()
    try:
        status = reward_service.can_claim_whisper(user_id, is_vip=is_vip)
    finally:
        reward_service.close()

    text = LucienVoice.susurros_menu(status)

    buttons = []
    if status.get("free_daily"):
        buttons.append([InlineKeyboardButton(
            text="🌙 Reclamar susurro diario", callback_data="claim_whisper_free"
        )])
    if status.get("vip_daily"):
        buttons.append([InlineKeyboardButton(
            text="💎 Reclamar susurro VIP", callback_data="claim_whisper_vip"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver", callback_data="back_to_main"
    )])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "claim_whisper_free")
async def susurros_claim_free(callback: CallbackQuery):
    user_id = callback.from_user.id

    reward_service = RewardService()
    try:
        result = await reward_service.claim_whisper(user_id, "free_daily", bot=callback.bot)
    finally:
        reward_service.close()

    if result.get("success"):
        text = LucienVoice.susurro_claimed(
            result.get("reward_name", "Misterio"),
            result.get("message", "")
        )
    else:
        text = LucienVoice.susurro_limit_reached() if "hoy" in result.get("message", "") else f"🎩 <b>Lucien:</b>\n\n<i>{result.get('message')}</i>"

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("susurros_diana"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "claim_whisper_vip")
async def susurros_claim_vip(callback: CallbackQuery):
    user_id = callback.from_user.id

    reward_service = RewardService()
    try:
        result = await reward_service.claim_whisper(user_id, "vip_daily", bot=callback.bot)
    finally:
        reward_service.close()

    if result.get("success"):
        text = LucienVoice.susurro_claimed(
            result.get("reward_name", "Misterio"),
            result.get("message", "")
        )
    else:
        text = LucienVoice.susurro_limit_reached() if "hoy" in result.get("message", "") else f"🎩 <b>Lucien:</b>\n\n<i>{result.get('message')}</i>"

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("susurros_diana"),
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
<name>Add admin handlers for WhisperRewardPool CRUD</name>
<files>handlers/engagement_admin_handlers.py</files>
<action>
Append to `handlers/engagement_admin_handlers.py`:

```python
@router.callback_query(F.data == "admin_whisper_pools")
async def admin_whisper_pools_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(LucienVoice.not_admin_error(), show_alert=True)
        return

    reward_service = RewardService()
    try:
        pools = reward_service.list_whisper_pools()
    finally:
        reward_service.close()

    text = "🎩 <b>Lucien:</b>\n\n<i>Bolsas de susurros configuradas...</i>\n\n"
    if not pools:
        text += "No hay pools configurados."
    else:
        for p in pools:
            status = "✅" if p.is_active else "❌"
            text += f"{status} <b>{p.name}</b> ({p.code})\n"

    await callback.message.edit_text(text, reply_markup=back_keyboard("admin_gamification"), parse_mode="HTML")
    await callback.answer()
```
</action>
<verify>
<command>grep -c "admin_whisper_pools" handlers/engagement_admin_handlers.py</command>
<expected>1</expected>
</verify>
<done>false</done>
</task>
