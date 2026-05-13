"""
Tests de integración para callbacks Trivia Streak Admin migrateados.

Verifica que los CallbackData migrados funcionan correctamente:
- TriviaStreakDetailCallback
- TriviaStreakToggleCallback
- TriviaStreakDeleteCallback
- TriviaStreakConfirmDeleteCallback
- TriviaStreakRedemptionsCallback
- TriviaStreakCategoryCallback
- TriviaStreakGoalTypeCallback
"""
import pytest

from keyboards.callback_data import (
    TriviaStreakDetailCallback,
    TriviaStreakToggleCallback,
    TriviaStreakDeleteCallback,
    TriviaStreakConfirmDeleteCallback,
    TriviaStreakRedemptionsCallback,
    TriviaStreakCategoryCallback,
    TriviaStreakGoalTypeCallback,
)


class TestTriviaStreakDetailCallback:
    """Tests para TriviaStreakDetailCallback."""

    def test_callback_packs_correctly(self):
        """TriviaStreakDetailCallback.pack() genera el string esperado."""
        promo_id = 42
        callback = TriviaStreakDetailCallback(promo_id=promo_id)
        packed = callback.pack()

        # Formato esperado: "streak_detail:42"
        assert packed == "streak_detail:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes promo_id."""
        for promo_id in [1, 10, 100, 999]:
            callback = TriviaStreakDetailCallback(promo_id=promo_id)
            packed = callback.pack()
            assert packed == f"streak_detail:{promo_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = TriviaStreakDetailCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = TriviaStreakDetailCallback(promo_id=123)
        packed = callback.pack()

        prefix, promo_id_str = packed.split(":")
        assert prefix == "streak_detail"
        assert int(promo_id_str) == 123


class TestTriviaStreakToggleCallback:
    """Tests para TriviaStreakToggleCallback."""

    def test_callback_packs_correctly(self):
        """TriviaStreakToggleCallback.pack() genera el string esperado."""
        promo_id = 42
        callback = TriviaStreakToggleCallback(promo_id=promo_id)
        packed = callback.pack()

        # Formato esperado: "streak_toggle:42"
        assert packed == "streak_toggle:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes promo_id."""
        for promo_id in [1, 10, 100, 999]:
            callback = TriviaStreakToggleCallback(promo_id=promo_id)
            packed = callback.pack()
            assert packed == f"streak_toggle:{promo_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = TriviaStreakToggleCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = TriviaStreakToggleCallback(promo_id=456)
        packed = callback.pack()

        prefix, promo_id_str = packed.split(":")
        assert prefix == "streak_toggle"
        assert int(promo_id_str) == 456


class TestTriviaStreakDeleteCallback:
    """Tests para TriviaStreakDeleteCallback."""

    def test_callback_packs_correctly(self):
        """TriviaStreakDeleteCallback.pack() genera el string esperado."""
        promo_id = 42
        callback = TriviaStreakDeleteCallback(promo_id=promo_id)
        packed = callback.pack()

        # Formato esperado: "streak_delete:42"
        assert packed == "streak_delete:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes promo_id."""
        for promo_id in [1, 10, 100, 999]:
            callback = TriviaStreakDeleteCallback(promo_id=promo_id)
            packed = callback.pack()
            assert packed == f"streak_delete:{promo_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = TriviaStreakDeleteCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)


class TestTriviaStreakConfirmDeleteCallback:
    """Tests para TriviaStreakConfirmDeleteCallback."""

    def test_callback_packs_correctly(self):
        """TriviaStreakConfirmDeleteCallback.pack() genera el string esperado."""
        promo_id = 42
        callback = TriviaStreakConfirmDeleteCallback(promo_id=promo_id)
        packed = callback.pack()

        # Formato esperado: "streak_confirm_del:42"
        assert packed == "streak_confirm_del:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes promo_id."""
        for promo_id in [1, 10, 100, 999]:
            callback = TriviaStreakConfirmDeleteCallback(promo_id=promo_id)
            packed = callback.pack()
            assert packed == f"streak_confirm_del:{promo_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = TriviaStreakConfirmDeleteCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)


class TestTriviaStreakRedemptionsCallback:
    """Tests para TriviaStreakRedemptionsCallback."""

    def test_callback_packs_correctly(self):
        """TriviaStreakRedemptionsCallback.pack() genera el string esperado."""
        promo_id = 42
        callback = TriviaStreakRedemptionsCallback(promo_id=promo_id)
        packed = callback.pack()

        # Formato esperado: "streak_redemptions:42"
        assert packed == "streak_redemptions:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes promo_id."""
        for promo_id in [1, 10, 100, 999]:
            callback = TriviaStreakRedemptionsCallback(promo_id=promo_id)
            packed = callback.pack()
            assert packed == f"streak_redemptions:{promo_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = TriviaStreakRedemptionsCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)


class TestTriviaStreakCategoryCallback:
    """Tests para TriviaStreakCategoryCallback."""

    def test_callback_packs_with_none_category(self):
        """TriviaStreakCategoryCallback.pack() con category='none'."""
        callback = TriviaStreakCategoryCallback(category="none")
        packed = callback.pack()

        # Formato esperado: "streak_promo_cat:none"
        assert packed == "streak_promo_cat:none"

    def test_callback_packs_with_category_id(self):
        """TriviaStreakCategoryCallback.pack() con category numérico."""
        callback = TriviaStreakCategoryCallback(category="5")
        packed = callback.pack()

        # Formato esperado: "streak_promo_cat:5"
        assert packed == "streak_promo_cat:5"

    def test_callback_packs_with_different_categories(self):
        """Funciona con diferentes valores de category."""
        test_cases = ["none", "1", "10", "100"]
        for category in test_cases:
            callback = TriviaStreakCategoryCallback(category=category)
            packed = callback.pack()
            assert packed == f"streak_promo_cat:{category}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = TriviaStreakCategoryCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)


class TestTriviaStreakGoalTypeCallback:
    """Tests para TriviaStreakGoalTypeCallback."""

    def test_callback_packs_with_general(self):
        """TriviaStreakGoalTypeCallback.pack() con goal_type='general'."""
        callback = TriviaStreakGoalTypeCallback(goal_type="general")
        packed = callback.pack()

        # Formato esperado: "streak_promo_gt:general"
        assert packed == "streak_promo_gt:general"

    def test_callback_packs_with_simple(self):
        """TriviaStreakGoalTypeCallback.pack() con goal_type='simple'."""
        callback = TriviaStreakGoalTypeCallback(goal_type="simple")
        packed = callback.pack()

        # Formato esperado: "streak_promo_gt:simple"
        assert packed == "streak_promo_gt:simple"

    def test_callback_packs_with_vip(self):
        """TriviaStreakGoalTypeCallback.pack() con goal_type='vip'."""
        callback = TriviaStreakGoalTypeCallback(goal_type="vip")
        packed = callback.pack()

        # Formato esperado: "streak_promo_gt:vip"
        assert packed == "streak_promo_gt:vip"

    def test_callback_packs_with_done(self):
        """TriviaStreakGoalTypeCallback.pack() con goal_type='done'."""
        callback = TriviaStreakGoalTypeCallback(goal_type="done")
        packed = callback.pack()

        # Formato esperado: "streak_promo_gt:done"
        assert packed == "streak_promo_gt:done"

    def test_callback_packs_with_different_goal_types(self):
        """Funciona con diferentes valores de goal_type."""
        goal_types = ["general", "simple", "vip", "done"]
        for goal_type in goal_types:
            callback = TriviaStreakGoalTypeCallback(goal_type=goal_type)
            packed = callback.pack()
            assert packed == f"streak_promo_gt:{goal_type}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = TriviaStreakGoalTypeCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)