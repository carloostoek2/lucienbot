---
name: test_callbackdata_gamification_admin
description: Tests for EditEmojiCallback and ToggleEmojiCallback migration
type: reference
---

Created integration tests for Gamification Admin CallbackData callbacks at `/home/ubuntu/repos/lucienbot/tests/integration/test_callbackdata_gamification_admin.py`.

Tests verify:
- `pack()` generates correct format (e.g., "edit_emoji:7")
- `filter()` is callable
- parse and extract work correctly
- no collision between EditEmojiCallback and ToggleEmojiCallback

16 tests all pass.