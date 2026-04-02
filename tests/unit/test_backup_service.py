"""
Tests unitarios para BackupService (credentials fix para pg_dump).
"""
import pytest
import os
import subprocess
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '/data/data/com.termux/files/home/repos/lucien_bot')

from services.backup_service import BackupService


@pytest.mark.unit
class TestBackupServiceCredentials:
    """Tests para verificar que las credenciales NO se pasan en CLI (Finding #3)."""

    @pytest.mark.asyncio
    async def test_pg_dump_does_not_expose_password_in_cli(self, tmp_path):
        """Test que pg_dump recibe credenciales via PGPASSWORD env var, no en CLI."""
        service = BackupService(backup_dir=str(tmp_path))

        # URL con credenciales plaintext
        db_url = "postgresql://miusuario:supersecret123@mi.host.com:5432/midb"

        captured_env = {}
        captured_args = []

        def mock_run(args, capture_output=None, text=None, timeout=None, env=None):
            captured_args.extend(args)
            captured_env.update(env or {})
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""
            return result

        with patch.object(subprocess, 'run', mock_run):
            await service._backup_postgresql(db_url, "20260101_120000")

        # Verificar que PGPASSWORD esta en el env, NO en los argumentos CLI
        assert "PGPASSWORD" in captured_env, "PGPASSWORD debe estar en env, no en CLI"
        assert captured_env["PGPASSWORD"] == "supersecret123"
        assert "supersecret123" not in " ".join(captured_args), (
            "La password NO debe aparecer en los argumentos CLI (evita曝光 en ps aux)"
        )
        # Verificar que se usan flags individuales
        assert "-h" in captured_args
        assert "-U" in captured_args
        assert "-p" in captured_args
        assert "-d" in captured_args
        assert db_url not in " ".join(captured_args), (
            "La URL completa NO debe pasarse como argumento a pg_dump"
        )

    @pytest.mark.asyncio
    async def test_pg_dump_extracts_host_port_user_dbname_correctly(self, tmp_path):
        """Test que se extraen correctamente host, port, user, dbname de la URL."""
        service = BackupService(backup_dir=str(tmp_path))

        db_url = "postgresql://admin:mypass@db.example.com:5433/production_db"

        captured_args = {}

        def mock_run(args, capture_output=None, text=None, timeout=None, env=None):
            # Extraer valores de los argumentos
            for i, arg in enumerate(args):
                if arg == "-h":
                    captured_args["host"] = args[i + 1]
                if arg == "-p":
                    captured_args["port"] = args[i + 1]
                if arg == "-U":
                    captured_args["user"] = args[i + 1]
                if arg == "-d":
                    captured_args["db"] = args[i + 1]
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""
            return result

        with patch.object(subprocess, 'run', mock_run):
            await service._backup_postgresql(db_url, "20260101_120000")

        assert captured_args["host"] == "db.example.com"
        assert captured_args["port"] == "5433"
        assert captured_args["user"] == "admin"
        assert captured_args["db"] == "production_db"

    @pytest.mark.asyncio
    async def test_pg_dump_without_password_uses_no_pgpassword(self, tmp_path):
        """Test que si la URL no tiene password, PGPASSWORD no se establece."""
        service = BackupService(backup_dir=str(tmp_path))

        db_url = "postgresql://admin@localhost/mydb"

        captured_env = {}

        def mock_run(args, capture_output=None, text=None, timeout=None, env=None):
            captured_env.update(env or {})
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""
            return result

        with patch.object(subprocess, 'run', mock_run):
            await service._backup_postgresql(db_url, "20260101_120000")

        # PGPASSWORD no debe estar presente si no hay password en la URL
        assert "PGPASSWORD" not in captured_env

    @pytest.mark.asyncio
    async def test_pg_dump_failed_logs_error(self, tmp_path):
        """Test que pg_dump fallido registra el error pero no rompe."""
        service = BackupService(backup_dir=str(tmp_path))

        def mock_run_fail(*args, **kwargs):
            result = MagicMock()
            result.returncode = 1
            result.stderr = "connection refused"
            return result

        with patch.object(subprocess, 'run', mock_run_fail):
            result = await service._backup_postgresql(
                "postgresql://user:pass@localhost/mydb",
                "20260101_120000"
            )

        assert result is None  # None indica fallo (logged internamente)
