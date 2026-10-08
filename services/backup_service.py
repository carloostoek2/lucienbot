"""
Backup Service - Lucien Bot

Realiza backups automaticos de la base de datos.
Soporta SQLite (desarrollo) y PostgreSQL (produccion en Railway).
"""

import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from config.settings import bot_config

logger = logging.getLogger(__name__)


class BackupService:
    """Servicio de backup de base de datos."""

    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

    def _skip_missing_client(self, binary: str) -> bool:
        """True si el cliente requerido no está instalado (backup omitido, no fallido).

        En producción los respaldos los cubre la plataforma; el dump local no
        sería durable en un contenedor efímero. Se registra una vez por corrida
        como warning claro en lugar de un error diario repetido.
        """
        if shutil.which(binary):
            return False
        logger.warning(
            f"backup_service | daily_backup | omitido: {binary} no está instalado en "
            "esta imagen -- usar los respaldos de la plataforma o instalar el cliente"
        )
        return True

    async def daily_backup(self) -> str | None:
        """
        Ejecuta un backup de la base de datos.

        Usa pg_dump para PostgreSQL, sqlite3 para SQLite.
        Guarda en backups/lucien_YYYYMMDD_HHMMSS.[sql|db]

        Returns:
            Ruta del archivo de backup, o None si falla o se omite.
        """
        db_url = bot_config.DATABASE_URL
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            if "postgresql" in db_url or "postgres" in db_url:
                if self._skip_missing_client("pg_dump"):
                    return None
                return await self._backup_postgresql(db_url, timestamp)
            else:
                if self._skip_missing_client("sqlite3"):
                    return None
                return await self._backup_sqlite(db_url, timestamp)
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    async def _backup_postgresql(self, db_url: str, timestamp: str) -> str | None:
        """Backup para PostgreSQL usando pg_dump.

        Credenciales se pasan via PGPASSWORD env var (no CLI) para evitar
        que aparezcan en ps aux / /proc.
        """
        try:
            parsed = urlparse(db_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
            user = parsed.username or "postgres"
            db_name = parsed.path.lstrip("/") or parsed.hostname

            backup_file = self.backup_dir / f"lucien_{timestamp}.sql"

            # Construir env sin credenciales en CLI
            env = os.environ.copy()
            if parsed.password:
                env["PGPASSWORD"] = parsed.password

            result = subprocess.run(
                [
                    "pg_dump",
                    "-h",
                    host,
                    "-p",
                    str(port),
                    "-U",
                    user,
                    "-d",
                    db_name,
                    "-f",
                    str(backup_file),
                ],
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )

            if result.returncode == 0:
                logger.info(f"PostgreSQL backup saved: {backup_file}")
                return str(backup_file)
            else:
                logger.error(f"pg_dump failed: {result.stderr}")
                return None
        except FileNotFoundError:
            logger.error("pg_dump not found -- is PostgreSQL client installed?")
            return None
        except Exception as e:
            logger.error(f"PostgreSQL backup error: {e}")
            return None

    async def _backup_sqlite(self, db_url: str, timestamp: str) -> str | None:
        """Backup para SQLite usando sqlite3 .backup command."""
        try:
            db_path = db_url.replace("sqlite:///", "")
            backup_file = self.backup_dir / f"lucien_{timestamp}.db"

            result = subprocess.run(
                ["sqlite3", db_path, f".backup '{backup_file}'"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and backup_file.exists():
                logger.info(f"SQLite backup saved: {backup_file}")
                return str(backup_file)
            else:
                logger.error(f"sqlite3 backup failed: {result.stderr}")
                return None
        except FileNotFoundError:
            logger.error("sqlite3 not found -- is sqlite3 CLI installed?")
            return None
        except Exception as e:
            logger.error(f"SQLite backup error: {e}")
            return None


# Module-level async wrapper for APScheduler compatibility
async def daily_backup() -> str | None:
    """Standalone async wrapper for APScheduler job scheduling."""
    service = BackupService()
    return await service.daily_backup()
