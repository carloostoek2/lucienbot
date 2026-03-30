"""
Migración: Agregar columna invite_link a la tabla channels.

Idempotente - puede ejecutarse múltiples veces sin errores.
Compatible con SQLite (desarrollo) y PostgreSQL (producción).
"""
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

load_dotenv()

DATABASE_URL = "sqlite:///lucien_bot.db"


def run_migration():
    """Ejecuta la migración de forma idempotente."""
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    )

    dialect = "sqlite" if "sqlite" in DATABASE_URL else "postgresql"
    print(f"[migración] Usando dialecto: {dialect}")
    print(f"[migración] Base de datos: {DATABASE_URL}")

    inspector = inspect(engine)
    existing_columns = [col["name"] for col in inspector.get_columns("channels")]

    if "invite_link" in existing_columns:
        print("[migración] La columna 'invite_link' ya existe en la tabla 'channels'. Nada que hacer.")
        return

    print("[migración] Agregando columna 'invite_link' a 'channels'...")

    # VARCHAR(500) compatible con ambos dialectos
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE channels ADD COLUMN invite_link VARCHAR(500)"
        ))
        conn.commit()

    print("[migración] Columna 'invite_link' agregada exitosamente.")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"[migración] ERROR: {e}")
        sys.exit(1)
