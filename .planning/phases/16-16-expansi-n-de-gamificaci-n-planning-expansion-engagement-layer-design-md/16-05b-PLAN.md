---
phase: 16
plan: 16-05b
wave: 6
depends_on: ["16-05a"]
files_modified:
  - services/daily_gift_service.py
  - handlers/engagement_user_handlers.py
  - keyboards/inline_keyboards.py
  - utils/lucien_voice.py
autonomous: true
type: auto
must_haves:
  - VIP streak recovery resets monthly and preserves streak once per month when break is detected
  - User sees "Mi Percentil" in main menu and can view anonymous percentile display
  - Full test suite passes after all Phase 16 changes
---

# Plan 16-05b: Percentiles UI, VIP Streak Recovery Finalization, and Full Suite

**Objective:** Wire percentile display into the UI, finalize VIP streak recovery logic, and verify the full test suite passes.

**Requirements mapped:** ENG-05, ENG-07

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section V (Estadísticas Anónimas)
- `services/daily_gift_service.py`
- `services/besito_service.py`
- `services/mission_service.py`

---

<task>
<name>Add LucienVoice and update keyboards for Percentiles</name>
<files>utils/lucien_voice.py, keyboards/inline_keyboards.py</files>
<action>
1. Add to `utils/lucien_voice.py` inside `LucienVoice`:

```python
    @staticmethod
    def percentil_menu(besito_percentile: str, mission_percentile: str) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Diana guarda los secretos de todos... pero solo comparte sombras.</i>

📊 <b>Tu lugar entre los visitantes:</b>

💋 Besitos acumulados: <b>{besito_percentile}</b>
🎯 Misiones completadas: <b>{mission_percentile}</b>

<i>Sin nombres. Sin comparaciones exactas. Solo la sensación de avanzar.</i>"""
```

2. In `keyboards/inline_keyboards.py`, inside `main_menu_keyboard()`, add a new row after the Ritmo/Susurros/Regalo row:

```python
    # Mi saldo - Mi Percentil (misma fila)
    buttons.append([
        InlineKeyboardButton(
            text="💋 Mi saldo de besitos",
            callback_data="my_balance"
        ),
        InlineKeyboardButton(
            text="📊 Mi Percentil",
            callback_data="mi_percentil"
        )
    ])
```
</action>
<verify>
<command>grep -c "percentil_menu" utils/lucien_voice.py</command>
<expected>1</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add percentile handler to engagement_user_handlers.py</name>
<files>handlers/engagement_user_handlers.py</files>
<action>
Append to `handlers/engagement_user_handlers.py`:

```python
from services.mission_service import MissionService


@router.callback_query(F.data == "mi_percentil")
async def percentil_menu(callback: CallbackQuery):
    user_id = callback.from_user.id

    besito_service = BesitoService()
    mission_service = MissionService()
    try:
        besito_pct = besito_service.get_percentile(user_id)
        mission_pct = mission_service.get_percentile(user_id)
    finally:
        besito_service.close()
        mission_service.close()

    text = LucienVoice.percentil_menu(besito_pct, mission_pct)

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
<name>Finalize VIP streak recovery in DailyGiftService</name>
<files>services/daily_gift_service.py</files>
<action>
Review `services/daily_gift_service.py` `claim_ritmo` method. Ensure the streak update block looks like:

```python
        streak = self.get_or_create_streak(user_id)
        now = datetime.now(timezone.utc)
        if streak.last_claimed_at:
            # Reset monthly recovery if new month
            if streak.last_claimed_at.month != now.month or streak.last_claimed_at.year != now.year:
                streak.recoveries_used_this_month = 0

            hours_since = (now - streak.last_claimed_at).total_seconds() / 3600
            if hours_since > 48:
                if is_vip and streak.recoveries_used_this_month < 1:
                    streak.recoveries_used_this_month += 1
                else:
                    streak.current_streak = 0
            else:
                streak.current_streak += 1
        else:
            streak.current_streak = 1
        streak.last_claimed_at = now
```

If this logic is missing or incomplete, add/update it within `claim_ritmo`.
</action>
<verify>
<command>grep -c "recoveries_used_this_month" services/daily_gift_service.py</command>
<expected>1</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Run full test suite and verify green</name>
<files>N/A</files>
<action>
Run `pytest tests/ -x` in the project root. If any tests fail, diagnose and fix the root cause (do not modify test expectations to match buggy behavior). Focus on:
1. Any import errors in new handler files
2. Any enum-related errors if migrations were not run in the test environment
3. Any session/transaction issues in new service methods
</action>
<verify>
<command>pytest tests/ -x</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>
