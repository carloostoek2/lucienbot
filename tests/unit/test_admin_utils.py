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

    @patch("utils.admin._is_admin_in_db", return_value=True)
    @patch("utils.admin.bot_config")
    def test_admin_by_db_role_when_not_in_admin_ids(self, mock_config, mock_db_check):
        """Usuario con role=admin en BD debe retornar True aunque no esté en ADMIN_IDS."""
        mock_config.ADMIN_IDS = [999]
        assert is_admin(555) is True
        mock_db_check.assert_called_once_with(555)

    @patch("utils.admin._is_admin_in_db", return_value=False)
    @patch("utils.admin.bot_config")
    def test_non_admin_skips_db_when_in_admin_ids(self, mock_config, mock_db_check):
        """Si está en ADMIN_IDS, no consulta la base de datos."""
        mock_config.ADMIN_IDS = [123, 456]
        assert is_admin(123) is True
        mock_db_check.assert_not_called()

    @patch("utils.admin._is_admin_in_db", return_value=False)
    @patch("utils.admin.bot_config")
    def test_non_admin_checks_db_fallback(self, mock_config, mock_db_check):
        """Usuario fuera de ADMIN_IDS y sin role admin en BD retorna False."""
        mock_config.ADMIN_IDS = [123]
        assert is_admin(789) is False
        mock_db_check.assert_called_once_with(789)
