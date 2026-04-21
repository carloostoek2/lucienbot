---
phase: 16
plan: 16-03b
wave: 4
depends_on: ["16-03a"]
files_modified:
  - handlers/engagement_user_handlers.py
  - handlers/engagement_admin_handlers.py
  - keyboards/inline_keyboards.py
  - utils/lucien_voice.py
autonomous: true
type: auto
must_haves:
  - User sees "Senderos del Espejo" in main menu and can start available paths
  - User receives Lucien-voice feedback when starting, advancing, or completing a path
  - Admin can view active story paths through a pure handler that calls exactly 1 service method
---

# Plan 16-03b: Senderos Narrativos — Handlers, Keyboards, Voice, and Admin UI

**Objective:** Wire the Senderos Narrativos feature into the Telegram bot UI with pure handlers, keyboard updates, and Lucien voice messages.

**Requirements mapped:** ENG-02, ENG-07

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section II (Senderos Narrativos)
- `services/story_service.py`
- `handlers/story_user_handlers.py`

---

<task>
<name>Add LucienVoice messages for Senderos</name>
<files>utils/lucien_voice.py</files>
<action>
Add to `utils/lucien_voice.py` inside `LucienVoice`:

```python
    @staticmethod
    def senderos_menu(paths: list) -> str:
        if not paths:
            return """🎩 <b>Lucien:</b>

<i>Los senderos del espejo aún no se han revelado para usted...</i>

📖 <b>Senderos Narrativos</b>

<i>Vuelva más tarde, o considere adentrarse en El Diván.</i>"""
        text = """🎩 <b>Lucien:</b>

<i>Los senderos que Diana ha tejido para quienes desean algo más...</i>

📖 <b>Senderos disponibles:</b>

"""
        for p in paths:
            vip = "💎 " if p.get('is_vip_exclusive') else ""
            text += f"{vip}<b>{p.get('name')}</b>\n"
            if p.get('description'):
                text += f"   <i>{p.get('description')}</i>\n"
        return text

    @staticmethod
    def sendero_started(path_name: str) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Ha elegido un camino entre muchos...</i>

📖 <b>{path_name}</b>

<i>Diana observa cada paso que da.</i>"""

    @staticmethod
    def sendero_completed(path_name: str, reward_msg: str = None) -> str:
        reward_part = f"\n\n🎁 <i>{reward_msg}</i>" if reward_msg else ""
        return f"""🎩 <b>Lucien:</b>

<i>Ha llegado al final del sendero...</i>

✅ <b>{path_name} — Completado</b>{reward_part}

<i>Las historias que vivió aquí permanecerán con usted.</i>"""

    @staticmethod
    def sendero_locked(reason: str) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Este sendero aún no le reconoce como digno...</i>

🔒 <b>Acceso bloqueado</b>

<i>{reason}</i>"""
```
</action>
<verify>
<command>grep -c "senderos_menu\|sendero_started\|sendero_completed\|sendero_locked" utils/lucien_voice.py</command>
<expected>4</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Update main menu keyboard with Senderos button</name>
<files>keyboards/inline_keyboards.py</files>
<action>
In `keyboards/inline_keyboards.py`, inside `main_menu_keyboard()`, add before the "Fragmentos de la historia" row:

```python
    # Senderos del Espejo
    buttons.append([InlineKeyboardButton(
        text="📖 Senderos del Espejo",
        callback_data="senderos_espejo"
    )])
```
</action>
<verify>
<command>grep -c "senderos_espejo" keyboards/inline_keyboards.py</command>
<expected>1</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add Senderos handlers to engagement_user_handlers.py</name>
<files>handlers/engagement_user_handlers.py</files>
<action>
Append to `handlers/engagement_user_handlers.py`:

```python
from services.story_service import StoryService
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@router.callback_query(F.data == "senderos_espejo")
async def senderos_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_vip = _is_vip(user_id)

    story_service = StoryService()
    try:
        paths = story_service.list_available_paths(user_id, is_vip=is_vip)
    finally:
        story_service.close()

    path_dicts = [{"name": p.name, "description": p.description, "is_vip_exclusive": p.is_vip_exclusive} for p in paths]
    text = LucienVoice.senderos_menu(path_dicts)

    keyboard_buttons = []
    for p in paths:
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"📖 {p.name}",
            callback_data=f"start_path_{p.id}"
        )])
    keyboard_buttons.append([InlineKeyboardButton(
        text="🔙 Volver", callback_data="back_to_main"
    )])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("start_path_"))
async def senderos_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_vip = _is_vip(user_id)
    try:
        path_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("Error en el sendero", show_alert=True)
        return

    story_service = StoryService()
    try:
        success, msg, progress = story_service.start_path(user_id, path_id, is_vip=is_vip)
    finally:
        story_service.close()

    if success:
        text = LucienVoice.sendero_started(progress.path.name if hasattr(progress, 'path') else "Sendero")
        keyboard = back_keyboard("senderos_espejo")
    else:
        text = LucienVoice.sendero_locked(msg or "No disponible")
        keyboard = back_keyboard("senderos_espejo")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("advance_path_"))
async def senderos_advance(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_vip = _is_vip(user_id)
    try:
        parts = callback.data.split("_")
        path_id = int(parts[2])
        choice_id = int(parts[3])
    except (IndexError, ValueError):
        await callback.answer("Error avanzando sendero", show_alert=True)
        return

    story_service = StoryService()
    try:
        success, msg, progress = await story_service.advance_path(
            user_id, path_id, choice_id, is_vip=is_vip, bot=callback.bot
        )
    finally:
        story_service.close()

    if not success:
        text = LucienVoice.sendero_locked(msg or "Error")
        keyboard = back_keyboard("senderos_espejo")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    if progress.is_completed:
        text = LucienVoice.sendero_completed(progress.path.name if hasattr(progress, 'path') else "Sendero")
    else:
        text = f"""🎩 <b>Lucien:</b>

<i>Avanza en el sendero...</i>

📖 <b>Progreso:</b> {progress.current_node_index + 1} / {len(progress.path.node_sequence if hasattr(progress, 'path') else [])}"""

    keyboard = back_keyboard("senderos_espejo")
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
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
<name>Add admin handlers for StoryPath CRUD</name>
<files>handlers/engagement_admin_handlers.py</files>
<action>
Append to `handlers/engagement_admin_handlers.py`:

```python
from services.story_service import StoryService


@router.callback_query(F.data == "admin_story_paths")
async def admin_story_paths_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(LucienVoice.not_admin_error(), show_alert=True)
        return

    story_service = StoryService()
    try:
        paths = story_service.list_active_story_paths()
    finally:
        story_service.close()

    text = "🎩 <b>Lucien:</b>\n\n<i>Senderos narrativos configurados...</i>\n\n"
    if not paths:
        text += "No hay senderos activos."
    else:
        for p in paths:
            vip = "💎" if p.is_vip_exclusive else ""
            text += f"{vip}<b>{p.name}</b> | Intentos: {p.max_attempts}\n"

    await callback.message.edit_text(text, reply_markup=back_keyboard("admin_narrative"), parse_mode="HTML")
    await callback.answer()
```
</action>
<verify>
<command>grep -c "admin_story_paths" handlers/engagement_admin_handlers.py</command>
<expected>1</expected>
</verify>
<done>false</done>
</task>
