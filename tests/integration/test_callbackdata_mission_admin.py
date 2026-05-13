"""
Tests de integración para Mission Admin CallbackData migrateados.

Verifica que los CallbackData migrados funcionan correctamente:
- MissionDetailCallback
- MissionToggleCallback
- MissionDeleteCallback
- MissionStatsCallback
- SelectRewardMissionCallback
- ConfirmCreateMissionCallback
"""
import pytest
from unittest.mock import MagicMock

from keyboards.callback_data import (
    MissionDetailCallback,
    MissionToggleCallback,
    MissionDeleteCallback,
    MissionStatsCallback,
    SelectRewardMissionCallback,
    ConfirmCreateMissionCallback,
)


class TestMissionDetailCallback:
    """Tests para MissionDetailCallback - detalle de misión (admin)."""

    def test_callback_packs_correctly(self):
        """MissionDetailCallback.pack() genera el string esperado."""
        mission_id = 5
        callback = MissionDetailCallback(mission_id=mission_id)
        packed = callback.pack()

        assert packed == f"mission_detail:{mission_id}"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes mission_id."""
        test_ids = [1, 5, 10, 50, 100, 999]
        for mission_id in test_ids:
            callback = MissionDetailCallback(mission_id=mission_id)
            packed = callback.pack()
            assert packed == f"mission_detail:{mission_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = MissionDetailCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        mission_id = 42
        callback = MissionDetailCallback(mission_id=mission_id)
        packed = callback.pack()

        prefix, mission_id_str = packed.split(":")
        assert prefix == "mission_detail"
        assert int(mission_id_str) == mission_id

    def test_extract_mission_id_from_packed(self):
        """Valores pueden ser extraídos del packed string."""
        packed = "mission_detail:99"
        prefix, mission_id_str = packed.split(":")

        assert prefix == "mission_detail"
        extracted_id = int(mission_id_str)
        assert extracted_id == 99

    def test_callback_preserves_id_on_repack(self):
        """El ID se preserva al re-empaquetar."""
        original_id = 123
        callback = MissionDetailCallback(mission_id=original_id)
        packed = callback.pack()

        prefix, mission_id_str = packed.split(":")
        new_id = int(mission_id_str)

        assert new_id == original_id


class TestMissionToggleCallback:
    """Tests para MissionToggleCallback - activar/desactivar misión."""

    def test_callback_packs_correctly(self):
        """MissionToggleCallback.pack() genera el string esperado."""
        mission_id = 3
        callback = MissionToggleCallback(mission_id=mission_id)
        packed = callback.pack()

        assert packed == f"toggle_mission:{mission_id}"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes mission_id."""
        test_ids = [1, 2, 8, 15, 77]
        for mission_id in test_ids:
            callback = MissionToggleCallback(mission_id=mission_id)
            packed = callback.pack()
            assert packed == f"toggle_mission:{mission_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = MissionToggleCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_extract_mission_id_from_packed(self):
        """Valores pueden ser extraídos del packed string."""
        packed = "toggle_mission:55"
        prefix, mission_id_str = packed.split(":")

        assert prefix == "toggle_mission"
        extracted_id = int(mission_id_str)
        assert extracted_id == 55


class TestMissionDeleteCallback:
    """Tests para MissionDeleteCallback - eliminar misión."""

    def test_callback_packs_correctly(self):
        """MissionDeleteCallback.pack() genera el string esperado."""
        mission_id = 7
        callback = MissionDeleteCallback(mission_id=mission_id)
        packed = callback.pack()

        # aiogram incluye todos los campos en el pack, incluyendo defaults
        assert packed == f"delete_mission:{mission_id}:0"

    def test_callback_packs_with_confirmed_false(self):
        """MissionDeleteCallback.pack() con confirmed=False."""
        mission_id = 7
        callback = MissionDeleteCallback(mission_id=mission_id, confirmed=False)
        packed = callback.pack()

        # confirmed=False se incluye como 0
        assert packed == f"delete_mission:{mission_id}:0"

    def test_callback_packs_with_confirmed_true(self):
        """MissionDeleteCallback.pack() con confirmed=True."""
        mission_id = 7
        callback = MissionDeleteCallback(mission_id=mission_id, confirmed=True)
        packed = callback.pack()

        # confirmed=True = 1
        assert packed == f"delete_mission:{mission_id}:1"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = MissionDeleteCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_extract_mission_id_from_packed(self):
        """Valores pueden ser extraídos del packed string."""
        packed = "delete_mission:88:0"
        # Usar rsplit para separar solo en la primera ocurrencia
        prefix, rest = packed.split(":", 1)

        assert prefix == "delete_mission"
        # rest es "88:0", separar por :
        parts = rest.split(":")
        mission_id = int(parts[0])
        assert mission_id == 88


class TestMissionStatsCallback:
    """Tests para MissionStatsCallback - estadísticas de misión."""

    def test_callback_packs_correctly(self):
        """MissionStatsCallback.pack() genera el string esperado."""
        mission_id = 12
        callback = MissionStatsCallback(mission_id=mission_id)
        packed = callback.pack()

        assert packed == f"mission_stats:{mission_id}"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes mission_id."""
        test_ids = [1, 3, 20, 100, 500]
        for mission_id in test_ids:
            callback = MissionStatsCallback(mission_id=mission_id)
            packed = callback.pack()
            assert packed == f"mission_stats:{mission_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = MissionStatsCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_extract_mission_id_from_packed(self):
        """Valores pueden ser extraídos del packed string."""
        packed = "mission_stats:33"
        prefix, mission_id_str = packed.split(":")

        assert prefix == "mission_stats"
        extracted_id = int(mission_id_str)
        assert extracted_id == 33


class TestSelectRewardMissionCallback:
    """Tests para SelectRewardMissionCallback - seleccionar recompensa para misión."""

    def test_callback_packs_correctly(self):
        """SelectRewardMissionCallback.pack() genera el string esperado."""
        reward_id = 4
        callback = SelectRewardMissionCallback(reward_id=reward_id)
        packed = callback.pack()

        assert packed == f"select_reward_mission:{reward_id}"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes reward_id."""
        test_ids = [1, 2, 5, 10, 25, 50]
        for reward_id in test_ids:
            callback = SelectRewardMissionCallback(reward_id=reward_id)
            packed = callback.pack()
            assert packed == f"select_reward_mission:{reward_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = SelectRewardMissionCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_extract_reward_id_from_packed(self):
        """Valores pueden ser extraídos del packed string."""
        packed = "select_reward_mission:17"
        prefix, reward_id_str = packed.split(":")

        assert prefix == "select_reward_mission"
        extracted_id = int(reward_id_str)
        assert extracted_id == 17


class TestConfirmCreateMissionCallback:
    """Tests para ConfirmCreateMissionCallback - confirmar creación de misión."""

    def test_callback_packs_correctly(self):
        """ConfirmCreateMissionCallback.pack() genera el string esperado."""
        callback = ConfirmCreateMissionCallback()
        packed = callback.pack()

        # Sin campos, solo el prefix
        assert packed == "confirm_create_mission"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = ConfirmCreateMissionCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = ConfirmCreateMissionCallback()
        packed = callback.pack()

        assert packed == "confirm_create_mission"


class TestCallbackNoCollisions:
    """Tests para verificar que no hay colisiones entre callbacks de misión."""

    def test_all_prefixes_are_unique(self):
        """Todos los prefixes son únicos."""
        packed_callbacks = [
            MissionDetailCallback(mission_id=1).pack(),
            MissionToggleCallback(mission_id=1).pack(),
            MissionDeleteCallback(mission_id=1).pack(),
            MissionStatsCallback(mission_id=1).pack(),
            SelectRewardMissionCallback(reward_id=1).pack(),
            ConfirmCreateMissionCallback().pack(),
        ]

        # Todos deben ser diferentes
        assert len(set(packed_callbacks)) == len(packed_callbacks)

    def test_different_mission_ids_produce_different_packs(self):
        """Diferentes mission_id producen diferentes packs."""
        mission_id = 10

        detail = MissionDetailCallback(mission_id=mission_id).pack()
        toggle = MissionToggleCallback(mission_id=mission_id).pack()
        delete = MissionDeleteCallback(mission_id=mission_id).pack()
        stats = MissionStatsCallback(mission_id=mission_id).pack()

        # Todos deben ser diferentes entre sí
        packs = [detail, toggle, delete, stats]
        assert len(set(packs)) == len(packs)

    def test_cross_callback_no_collision_with_other_prefixes(self):
        """No hay colisión con otros prefijos del sistema."""
        # Usar el mismo ID pero con diferentes callbacks
        test_id = 99

        packs = [
            f"mission_detail:{test_id}",
            f"toggle_mission:{test_id}",
            f"delete_mission:{test_id}:0",
            f"mission_stats:{test_id}",
            f"select_reward_mission:{test_id}",
            "confirm_create_mission",
        ]

        # Todos deben ser únicos
        assert len(set(packs)) == len(packs)