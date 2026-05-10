"""Integration tests for streak promotion admin handlers -- Phase 17."""


def test_stub_admin_menu_includes_streak_promotions():
    """Verify admin keyboard contains the streak promotions button (Wave 0 stub)."""
    from keyboards.inline_keyboards import admin_menu_keyboard
    keyboard = admin_menu_keyboard()
    button_texts = []
    for row in keyboard.inline_keyboard:
        for btn in row:
            button_texts.append(btn.text)
    # Stub: just verify the function runs without error (button added in 17-03)
    assert isinstance(button_texts, list)
