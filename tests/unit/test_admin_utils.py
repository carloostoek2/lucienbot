"""
Tests unitarios para utils/admin.py — is_admin().
"""
import pytest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from utils.admin import is_admin


@pytest.mark.unit
class TestIsAdmin:
    """Tests para la función is_admin que verifica permisos de Custodio."""

    @patch("utils.admin.bot_config")
    def test_admin_user_returns_true(self, mock_config):
        """Usuario en ADMIN_IDS debe retornar True."""
        mock_config.ADMIN_IDS = [123, 456]
        assert is_admin(123) is True

    @patch("utils.admin.bot_config")
    def test_non_admin_user_returns_false(self, mock_config):
        """Usuario fuera de ADMIN_IDS debe retornar False."""
        mock_config.ADMIN_IDS = [123, 456]
        assert is_admin(789) is False

    @patch("utils.admin.bot_config")
    def test_empty_admin_ids_all_false(self, mock_config):
        """Si ADMIN_IDS está vacío, nadie es admin."""
        mock_config.ADMIN_IDS = []
        assert is_admin(0) is False
        assert is_admin(999) is False
        assert is_admin(None) is False  # type: ignore

    @patch("utils.admin.bot_config")
    def test_user_id_as_string_does_not_match_int(self, mock_config):
        """String '123' no debe coincidir con int 123 (type safety)."""
        mock_config.ADMIN_IDS = [123, 456]
        assert is_admin("123") is False
