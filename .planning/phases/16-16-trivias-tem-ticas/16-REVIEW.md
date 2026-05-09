---
phase: 16-16-trivias-tem-ticas
reviewed: 2026-05-09T20:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - models/models.py
  - alembic/versions/20260509_add_trivia_categories_table.py
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
findings:
  critical: 0
  warning: 8
  info: 3
  total: 11
status: issues_found
---

# Phase 16: Code Review Report -- Trivias Tematicas

**Reviewed:** 2026-05-09T20:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

The implementation adds a trivia category system with JSON-based question decks, database-backed category state management, and admin activation/deactivation UI. The architecture is generally sound and follows existing patterns. However, there are 8 warnings and 3 info findings covering incorrect template selection for VIP trivia, missing input validation, encapsulation violations, datetime timezone inconsistencies, code duplication, and a dead parameter.

The migration chain is verified intact (`20260509_add_trivia_categories` properly extends from `20250407_add_game_and_anon_enum`).

---

## Warnings

### WR-01: VIP trivia uses regular trivia streak messages instead of VIP-specific templates

**File:** `services/game_service.py:985`
**Issue:** The method `play_trivia_vip()` calls `self._get_streak_message(new_streak)` at line 985, which references `self.TRIVIA_TEMPLATES['streak_messages']` (the regular trivia template set, defined at line 157-166). The VIP trivia has its own dedicated template set at `self.TRIVIA_VIP_TEMPLATES['streak_messages']` (lines 200-206) with appropriate VIP-themed flavor text, but this is never used. As a result, VIP users playing VIP trivia see the same streak messages as free users playing regular trivia.

This is contradicted by the tematica path, which correctly uses `_get_tematica_streak_message()` referencing `self.TRIVIA_TEMATICA_TEMPLATES['streak_messages']`.

**Fix:** Add a VIP-specific streak message method (or generalize the existing one to accept a template dict parameter) and call it from `play_trivia_vip()`:

```python
def _get_vip_streak_message(self, streak: int) -> Optional[str]:
    if streak < 2:
        return None
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
    templates = self.TRIVIA_VIP_TEMPLATES['streak_messages'].get(level, ["\U0001f3a9 Racha de {streak}!"])
    return self._select_template(templates).format(streak=streak)
```

Then in `play_trivia_vip()` at line 985, change to `streak_message = self._get_vip_streak_message(new_streak)`.

---

### WR-02: Massive code duplication between regular trivia, VIP trivia, and tematica trivia paths

**File:** `services/game_service.py` (multiple locations)
**Issue:** Three parallel implementations exist with nearly identical logic:
- `play_trivia()` (lines 680-783), `play_trivia_vip()` (lines 944-1045), `play_trivia_tematica()` (lines 1223-1314)
- `_get_trivia_streak()` (lines 320-329), `_get_vip_trivia_streak()` (lines 844-853), `_get_tematica_trivia_streak()` (lines 1162-1171)
- `_get_today_trivia_records()` (lines 310-318), `_get_today_vip_trivia_records()` (lines 834-842), `_get_today_tematica_trivia_records()` (lines 1097-1105)
- `get_trivia_entry_data()` (lines 609-636), `get_trivia_vip_entry_data()` (lines 913-942), `get_trivia_tematica_entry_data()` (lines 1197-1221)

These differ only in constants (besitos amounts, limits), template references (TRIVIA_TEMPLATES vs VIP vs TEMATICA), and game_type strings (`'trivia'` vs `'trivia_vip'` vs `'trivia_tematica'`). This violates the project rule **"PROHIBIDO duplicación entre services"** (though technically all within the same service file, the spirit of the rule against duplication applies).

This duplication is the root cause of WR-01: the VIP path accidentally uses regular templates because the copy-paste missed the template swap.

**Fix:** Refactor the common logic into parameterized internal methods that accept:
- `game_type` string
- Template dict
- Win besitos amount  
- A `load_questions` callable / question loader strategy

---

### WR-03: Missing answer index validation in `trivia_answer` and `trivia_vip_answer` handlers

**File:** `handlers/game_user_handlers.py:150-152` (trivia_answer) and lines 222-224 (trivia_vip_answer)
**Issue:** The `trivia_tematica_answer` handler validates the answer index at lines 319-321:
```python
if answer_idx < 0 or answer_idx > 3:
    await callback.answer("Opcion invalida.", show_alert=True)
    return
```

But `trivia_answer` (line 150-152) and `trivia_vip_answer` (line 222-224) do NOT perform this validation. If a malformed callback data is processed (e.g., `trivia_answer_9_0` where answer index 9 exceeds the options list), `check_trivia_answer()` would call `question.get('answer') == answer_idx` which is fine, but the message builder at `_build_trivia_message_parts()` would crash with an `IndexError` at line 793: `correct_letter = letters[question['answer']]` -- this uses the question's answer index which is valid, but the `question['opts'][question['answer']]` at line 793 assumes a valid index. However, the real risk is in the keyboard generation: if `answer_idx` is out of bounds for `question['opts']` but the code doesn't access it directly by that index in the handler -- it's passed to the service which does check equality. The `_build_trivia_message_parts` accesses `question['opts'][question['answer']]` where `question['answer']` comes from the data file, so it should be valid. But for defense-in-depth, answer validation should be consistent across all three handlers.

**Fix:** Add the same validation to `trivia_answer` and `trivia_vip_answer`:

```python
# In trivia_answer, after line 150:
if answer_idx < 0 or answer_idx > 3:
    await callback.answer("Opcion invalida.", show_alert=True)
    return

# In trivia_vip_answer, after line 222:
if answer_idx < 0 or answer_idx > 3:
    await callback.answer("Opcion invalida.", show_alert=True)
    return
```

---

### WR-04: Handler accesses private service members, breaking encapsulation

**File:** `handlers/game_user_handlers.py:276-278`
**Issue:** The `game_trivia_tematica` handler accesses private (underscore-prefixed) members of `GameService`:
```python
exhausted_msg = service._select_template(
    service.TRIVIA_TEMATICA_TEMPLATES['deck_exhausted']
)
```

This violates the architectural rule that **handlers contain no business logic** and should "llamar exactamente 1 service." The handler is reaching into service internals to format a message, which should be the service's responsibility.

**Fix:** Move the deck-exhausted message generation into `GameService` as a public method (e.g., `get_deck_exhausted_message()`) and call it from the handler:

```python
# In GameService:
def get_deck_exhausted_message(self) -> str:
    template = self._select_template(self.TRIVIA_TEMATICA_TEMPLATES['deck_exhausted'])
    return template

# In handler:
exhausted_msg = service.get_deck_exhausted_message()
```

---

### WR-05: Naive datetime used with timezone-aware column

**Files:** `services/trivia_service.py:93,100` and `alembic/versions/20260509_add_trivia_categories_table.py:30`

**Issue:** The `activate()` method uses `datetime.utcnow()` to set `activated_at`:
```python
cat.activated_at = datetime.utcnow()  # naive datetime
```
But the column is defined as `DateTime(timezone=True)`:
```python
activated_at = Column(DateTime(timezone=True), nullable=True)
```

SQLAlchemy will issue a warning or silently coerce the value, potentially storing it incorrectly (as UTC without timezone info vs. as local time). This also affects the migration's `server_default`:
```python
sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
```

In SQLite, `CURRENT_TIMESTAMP` returns a naive string; in PostgreSQL it returns a proper `timestamptz`. This inconsistency can cause subtle bugs when switching databases.

Additionally, the `scheduled_end` parameter accepts `datetime` without specifying timezone awareness, so callers could pass naive datetimes for a timezone-aware column.

**Fix:** Use timezone-aware datetimes:
```python
from datetime import datetime, timezone

# In activate():
cat.activated_at = datetime.now(timezone.utc)

# For the migration, use timezone-aware function:
sa.Column('created_at', sa.DateTime(timezone=True),
          server_default=sa.func.now(), nullable=False)
# Or use text with explicit timezone:
sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
```

---

### WR-06: `_build_trivia_vip_message_parts` hardcodes five kiss emojis instead of using dynamic count

**File:** `services/game_service.py:1065`
**Issue:** The reward text uses a hardcoded string of 5 kiss emojis:
```python
reward_text = f"+{besitos} besitos \U0001f48d\U0001f48d\U0001f48d\U0001f48d\U0001f48d"
```

If the `TRIVIA_VIP_WIN_BESITOS` constant changes from 5 to another value in the future, the emoji display will mismatch the actual besitos awarded.

**Fix:** Generate the emoji count dynamically:
```python
reward_text = f"+{besitos} besitos {'\U0001f48d' * besitos}" if besitos else None
```

---

### WR-07: Dead parameter `is_vip` in `game_menu_keyboard()`

**File:** `keyboards/inline_keyboards.py:428`
**Issue:** The function signature includes `is_vip: bool = False`, but the parameter is never read in the function body. No caller passes this argument either -- all callers (in `game_user_handlers.py`) use keyword arguments for `tematica_button` only.

**Fix:** Remove the dead parameter:
```python
def game_menu_keyboard(tematica_button: tuple = None) -> InlineKeyboardMarkup:
```

---

### WR-08: `activate()` with no display_name defaults to raw category_id on first creation

**File:** `services/trivia_service.py:79-110`
**Issue:** When `activate(category_id)` is called without `display_name` and the category does NOT exist in the database (first-ever activation), the fallback at line 98 sets `display_name = category_id` (e.g., `"halloween"`). The `DISPLAY_NAME_MAP` at lines 25-29 has proper human-readable names (e.g., `"\U0001f383 Trivia de Halloween"`) but these are only used by `discover_categories()`, not by `activate()`.

If the category was previously created and deactivated, the existing record preserves its `display_name`. But the first-ever activation shows a raw machine key to users.

The handler `trivia_category_activate` (in `trivia_admin_handlers.py:65`) calls `service.activate(category_id)` without `display_name`, so this affects all activation attempts.

**Fix:** Have `activate()` look up the display name from `DISPLAY_NAME_MAP` when none is provided:
```python
def activate(self, category_id: str, display_name: str = None,
             scheduled_end: datetime = None) -> bool:
    if display_name is None:
        # Try to find a proper display name from the map
        for stem, name in self.DISPLAY_NAME_MAP.items():
            if stem.endswith(category_id) or stem == f"preguntas_{category_id}":
                display_name = name
                break
    # ... rest of method
```

---

## Info

### IN-01: `discover_categories()` has dead code in filter

**File:** `services/trivia_service.py:50`
**Issue:** The filter skips `"preguntas"` stem:
```python
if f.stem in ("preguntas", "preguntas_vip"):
    continue
```
But the glob pattern `preguntas_*.json` will never match `preguntas.json` (no underscore), so the `"preguntas"` exclusion is unreachable. The `"preguntas_vip"` exclusion is reachable (since `*` matches `vip`).

**Fix:** Either remove the dead `"preguntas"` entry or expand the glob to also match `preguntas.json` if needed:
```python
if f.stem == "preguntas_vip":
    continue
```

---

### IN-02: Admin confirmation alert shows machine key instead of display name

**File:** `handlers/trivia_admin_handlers.py:66`
**Issue:** After activation, the alert shows `category_id` (e.g., `"halloween"`):
```python
await callback.answer(f"Categoria activada: {category_id}", show_alert=True)
```
But the menu shows human-readable `display_name` (e.g., `"\U0001f383 Trivia de Halloween"`). The user-facing message should match what the user sees in the menu.

**Fix:** Use display_name in the confirmation message:
The service's `activate()` could return the display_name, or the handler could look it up from the category data.

---

### IN-03: `deactivate()` docstring is incorrect

**File:** `services/trivia_service.py:113`
**Issue:** The docstring says:
```
"""Desactiva una categoria o la activa si no se especifica."""
```
But the method never activates -- it only deactivates. The second clause ("o la activa si no se especifica") is misleading.

**Fix:** Correct the docstring to:
```
"""Desactiva una categoria especifica o todas las activas si no se especifica."""
```

---

_Reviewed: 2026-05-09T20:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
