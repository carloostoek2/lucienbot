"""
Tests unitarios para BackupService (credentials fix para pg_dump).
"""

import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from config.settings import bot_config
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

        with patch.object(subprocess, "run", mock_run):
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

        with patch.object(subprocess, "run", mock_run):
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

        with patch.object(subprocess, "run", mock_run):
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

        with patch.object(subprocess, "run", mock_run_fail):
            result = await service._backup_postgresql(
                "postgresql://user:pass@localhost/mydb", "20260101_120000"
            )

        assert result is None  # None indica fallo (logged internamente)

    @pytest.mark.asyncio
    async def test_sqlite_backup_happy_path_creates_file(self, tmp_path):
        """DESIRED CONTRACT: daily_backup for sqlite returns path + .exists() (gold deterministic)."""
        from pathlib import Path

        service = BackupService(backup_dir=str(tmp_path))
        expected = str(tmp_path / "lucien_20260101_120000.db")
        Path(expected).touch()
        # shutil.which fijado: el contrato no debe depender de si la máquina
        # tiene el cliente sqlite3 instalado.
        with (
            patch("services.backup_service.shutil.which", return_value="/usr/bin/sqlite3"),
            patch.object(service, "_backup_sqlite", return_value=expected),
        ):
            result = await service.daily_backup()
        assert result == expected
        assert Path(result).exists()


@pytest.mark.unit
class TestBackupServiceMissingClient:
    """El backup se OMITE (no falla) cuando el cliente no está instalado en la imagen.

    En producción los respaldos los cubre la plataforma y el dump local no sería
    durable en un contenedor efímero: un ERROR diario por binario ausente era ruido
    que ocultaba fallos reales.
    """

    @pytest.mark.asyncio
    async def test_daily_backup_skips_when_pg_dump_missing(self, tmp_path, caplog):
        """Sin pg_dump: no invoca subprocess y avisa con warning claro."""
        service = BackupService(backup_dir=str(tmp_path))
        with (
            patch.object(bot_config, "DATABASE_URL", "postgresql://u:p@h:5432/db"),
            patch("services.backup_service.shutil.which", return_value=None),
            patch.object(subprocess, "run") as run_mock,
            caplog.at_level(logging.WARNING),
        ):
            result = await service.daily_backup()

        assert result is None
        run_mock.assert_not_called()
        assert "pg_dump" in caplog.text
        assert "omitido" in caplog.text

    @pytest.mark.asyncio
    async def test_daily_backup_skips_when_sqlite3_missing(self, tmp_path, caplog):
        """Sin sqlite3: no invoca subprocess y avisa con warning claro."""
        service = BackupService(backup_dir=str(tmp_path))
        with (
            patch.object(bot_config, "DATABASE_URL", "sqlite:///./lucien_bot.db"),
            patch("services.backup_service.shutil.which", return_value=None),
            patch.object(subprocess, "run") as run_mock,
            caplog.at_level(logging.WARNING),
        ):
            result = await service.daily_backup()

        assert result is None
        run_mock.assert_not_called()
        assert "sqlite3" in caplog.text
        assert "omitido" in caplog.text

    @pytest.mark.asyncio
    async def test_daily_backup_runs_when_client_available(self, tmp_path):
        """Con el cliente presente el flujo no se corta: delega en el dump real."""
        service = BackupService(backup_dir=str(tmp_path))
        expected = str(tmp_path / "lucien_20260101_120000.sql")
        with (
            patch.object(bot_config, "DATABASE_URL", "postgresql://u:p@h:5432/db"),
            patch("services.backup_service.shutil.which", return_value="/usr/bin/pg_dump"),
            patch.object(service, "_backup_postgresql", return_value=expected) as dump_mock,
        ):
            result = await service.daily_backup()

        assert result == expected
        dump_mock.assert_awaited_once()
