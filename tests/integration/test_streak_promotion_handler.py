"""Integration tests for streak promotion admin handlers -- Phase 17."""


def test_admin_menu_includes_streak_promotions():
    """Verify admin keyboard contains the streak promotions button."""
    from keyboards.inline_keyboards import admin_menu_keyboard
    keyboard = admin_menu_keyboard()
    button_texts = []
    for row in keyboard.inline_keyboard:
        for btn in row:
            button_texts.append(btn.text)
    assert "🏆 Promos de Racha" in button_texts


def test_streak_promotion_service_imports():
    """Verify the service is importable and has expected methods."""
    from services.streak_promotion_service import StreakPromotionService
    assert hasattr(StreakPromotionService, "create_promotion")
    assert hasattr(StreakPromotionService, "claim_for_streak")
    assert hasattr(StreakPromotionService, "activate")
    assert hasattr(StreakPromotionService, "deactivate")
    assert hasattr(StreakPromotionService, "delete_promotion")
    assert hasattr(StreakPromotionService, "_generate_code")
    assert hasattr(StreakPromotionService, "get_all_promotions")
    assert hasattr(StreakPromotionService, "get_active_promotions")
    assert hasattr(StreakPromotionService, "get_redemption_stats")
    assert hasattr(StreakPromotionService, "get_user_redemptions")
