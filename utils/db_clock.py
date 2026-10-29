"""Reloj único de base de datos.

Las comparaciones de idempotencia/cooldown mezclaban ``datetime.now(UTC)`` (reloj de la
app en Railway) con ``server_default=now()`` (reloj de PostgreSQL). Con desfase entre
ambos, una entrega podía no verse como hecha. Este helper lee ``now()`` de la BD para
que ambos lados usen el mismo reloj.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def as_aware_utc(value: datetime) -> datetime:
    """Normaliza un datetime naive (SQLite) a UTC aware."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def db_now(db: Session) -> datetime:
    """``now()`` de la base de datos como datetime UTC aware."""
    value = db.execute(select(func.now())).scalar()
    if isinstance(value, str):  # SQLite sin tipo resuelto
        value = datetime.fromisoformat(value)
    return as_aware_utc(value)
