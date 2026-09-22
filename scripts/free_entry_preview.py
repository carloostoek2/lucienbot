#!/usr/bin/env python
"""
Preview de los mensajes del flujo Free ENTRY con la config real de un canal.

Reusa los builders de runtime (services.channel_grant + LucienVoice), asi que lo
que imprime es EXACTAMENTE lo que el bot envia, resuelto contra la fila real de
`channels` (mensajes custom del canal o fallback de Lucien + invite_link).

Read-only: solo SELECT. No imprime credenciales.

Usage:
    python -m scripts.free_entry_preview                    # DATABASE_URL_PREVIEW del .env
    python -m scripts.free_entry_preview --database-url sqlite:///lucien_bot.db
    python -m scripts.free_entry_preview --var MI_OTRA_DB
    python -m scripts.free_entry_preview --channel Kinkys    # filtra por nombre o id

Exit codes:
    0 si imprimio al menos un canal Free
    1 si falta la URL o no hay canales Free

Driver Postgres: usa psycopg2 si esta disponible; si no (p.ej. Termux, donde
psycopg2-binary no compila), cae a pg8000 (Python puro, `pip install pg8000`).
"""

import argparse
import importlib
import logging
import os
import re
import sys
from types import SimpleNamespace

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from services.channel_grant import (
    build_approval_payload,
    build_welcome_payload,
    is_valid_telegram_invite_link,
)
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)

DEFAULT_ENV_VAR = "DATABASE_URL_PREVIEW"
FALLBACK_CHANNEL_NAME = "Los Kinkys"

_SELECT_FREE_CHANNELS = text(
    """
    SELECT id, channel_id, channel_name, channel_type, is_active,
           wait_time_minutes, invite_link, approval_message, welcome_message
    FROM channels
    WHERE channel_type = 'FREE'
    ORDER BY is_active DESC, id
    """
)


def module_is_importable(name: str) -> bool:
    """True si el modulo esta instalado (sin importar side effects)."""
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def mask_credentials(url: str) -> str:
    """Oculta la password de una URL de conexion antes de imprimirla."""
    return re.sub(r"://([^:/@]+):[^@]+@", r"://\1:***@", url)


def resolve_database_url(cli_url: str | None, env_var: str) -> str | None:
    """Prioriza --database-url; si no, la variable de entorno indicada."""
    if cli_url:
        return cli_url
    value = os.environ.get(env_var)
    if value and value.strip():
        return value.strip()
    return None


def normalize_postgres_url(url: str) -> tuple[str, dict]:
    """Elige driver Postgres disponible y devuelve (url, connect_args)."""
    parsed = make_url(url)
    if parsed.drivername not in ("postgres", "postgresql"):
        return url, {}

    if module_is_importable("psycopg2"):
        return parsed.set(drivername="postgresql+psycopg2").render_as_string(
            hide_password=False
        ), {}
    if module_is_importable("pg8000"):
        # pg8000 no entiende sslmode: se quita y se fuerza TLS via ssl_context.
        query = {k: v for k, v in parsed.query.items() if k != "sslmode"}
        url_pg8000 = parsed.set(drivername="postgresql+pg8000", query=query)
        # OJO: str(URL) enmascara la password con '***'. Hay que render explicito.
        return url_pg8000.render_as_string(hide_password=False), {"ssl_context": True}
    raise RuntimeError(
        "No hay driver Postgres instalado. Instala psycopg2-binary o pg8000 "
        "(`pip install pg8000`)."
    )


def build_database_engine(url: str):
    """Crea engine read-only-friendly para sqlite o postgres."""
    normalized, connect_args = normalize_postgres_url(url)
    return create_engine(normalized, connect_args=connect_args)


def load_free_channels(engine) -> list[SimpleNamespace]:
    """SELECT de canales Free (activos primero). Solo lectura."""
    with engine.connect() as conn:
        rows = conn.execute(_SELECT_FREE_CHANNELS).mappings().all()
    return [SimpleNamespace(**dict(row)) for row in rows]


def collect_channel_warnings(channel: SimpleNamespace) -> list[str]:
    """Avisos de config que afectan al mensaje final (link / parse_mode)."""
    warnings = []
    name = channel.channel_name or FALLBACK_CHANNEL_NAME
    link = channel.invite_link or ""
    if not (link or "").strip():
        warnings.append(
            "invite_link vacio: el mensaje 4 se envia SIN link "
            f"(el fallback de Lucien no incluye {name})."
        )
    elif not is_valid_telegram_invite_link(link):
        warnings.append(
            "invite_link con formato invalido: se omite en silencio (solo warning en logs). "
            "Debe cumplir https://t.me/..."
        )
    for field in ("approval_message", "welcome_message"):
        custom = (getattr(channel, field, None) or "").strip()
        if custom and ("<" in custom or "&" in custom):
            warnings.append(
                f"{field} custom contiene '<' o '&' y se envia con parse_mode=HTML: "
                "escapa o Telegram rechazara el mensaje."
            )
    return warnings


def render_free_entry_flow(channel: SimpleNamespace) -> list[tuple[str, str]]:
    """Devuelve los 4 mensajes del flujo Free tal como los envia el bot."""
    name = channel.channel_name or FALLBACK_CHANNEL_NAME
    return [
        (
            "1) 1a solicitud del usuario",
            "(silencio: el bot NO envia nada; solo crea PendingRequest y agenda "
            "el job ritual a los 30s)",
        ),
        ("2) +30s ritual + social_links_keyboard()", build_approval_payload(channel)),
        ("3) solicitud duplicada (sin teclado)", LucienVoice.free_entry_impatient(name)),
        (
            f"4) aceptado tras {channel.wait_time_minutes} min + free_entry_welcome_keyboard()",
            build_welcome_payload(channel),
        ),
    ]


def describe_channel_source(channel: SimpleNamespace) -> str:
    """Linea de resumen de config: DB vs custom vs fallback de Lucien."""
    approval = "custom" if (channel.approval_message or "").strip() else "Lucien (fallback)"
    welcome = "custom" if (channel.welcome_message or "").strip() else "Lucien (fallback)"
    return (
        f"[id={channel.id}] canal={channel.channel_name!r} tg_id={channel.channel_id} "
        f"activo={bool(channel.is_active)} wait_time_minutes={channel.wait_time_minutes} "
        f"ritual={approval} welcome={welcome} invite_link={channel.invite_link!r}"
    )


def print_channel_preview(channel: SimpleNamespace) -> None:
    """Imprime config, avisos y los 4 mensajes de un canal."""
    print("#" * 74)
    print(describe_channel_source(channel))
    print("#" * 74)
    for warning in collect_channel_warnings(channel):
        print(f"  AVISO: {warning}")
    for title, body in render_free_entry_flow(channel):
        print("\n" + "-" * 74)
        print(title)
        print("-" * 74)
        print(body)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview read-only de los mensajes Free ENTRY con la config real de la BD."
    )
    parser.add_argument("--database-url", help="URL explicita (sqlite o postgres).")
    parser.add_argument("--var", default=DEFAULT_ENV_VAR, help="Variable de entorno a leer.")
    parser.add_argument("--channel", help="Filtra por nombre (substring) o por id de BD.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    load_dotenv()

    url = resolve_database_url(args.database_url, args.var)
    if not url:
        print(
            f"Falta la URL de conexion. Define {args.var} en el .env "
            "o pasa --database-url.",
            file=sys.stderr,
        )
        return 1

    print(f"Conectando a: {mask_credentials(url)}")
    logger.info("free_entry_preview | SELECT channels FREE | user_id=0 | read-only")

    try:
        engine = build_database_engine(url)
        channels = load_free_channels(engine)
    except Exception as e:
        print(f"Error consultando canales: {e}", file=sys.stderr)
        return 1

    if args.channel:
        needle = args.channel.lower()
        channels = [
            c
            for c in channels
            if needle in (c.channel_name or "").lower() or needle == str(c.id)
        ]

    if not channels:
        print("No se encontraron canales Free en la base de datos.", file=sys.stderr)
        return 1

    for channel in channels:
        print_channel_preview(channel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
