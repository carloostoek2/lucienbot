"""
Configuración de base de datos - Lucien Bot
"""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import bot_config

# Crear engine
engine = create_engine(
    bot_config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in bot_config.DATABASE_URL else {},
    echo=False
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def init_db():
    """
    DEPRECATED: Schema management is now handled by Alembic.

    This function is kept as a no-op for backwards compatibility.
    All schema creation and migration is done via:
        alembic revision --autogenerate -m "description"
        alembic upgrade head

    The Alembic baseline was established in Phase 07.1.
    """
    pass


def get_db():
    """Generador de sesiones de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager para sesiones de base de datos.

    Uso:
        with get_db_session() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
