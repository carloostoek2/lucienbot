#!/usr/bin/env python3
"""
Identifica visitantes que alguna vez tuvieron VIP pero ya no tienen suscripción
activa, y los banea del canal VIP en Telegram (ban persistente).

Uso (producción Railway):
  railway run --service Postgres -- python -m scripts.ban_expired_vip_members --dry-run
  railway run --service Postgres -- python -m scripts.ban_expired_vip_members --apply

Requiere BOT_TOKEN (lucienbot) y DATABASE_URL o DATABASE_PUBLIC_URL (Postgres).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("ban_expired_vip_members")

EX_VIP_QUERY = text(
    """
    WITH active_vip AS (
        SELECT DISTINCT s.user_id
        FROM subscriptions s
        JOIN channels c ON c.id = s.channel_id
        WHERE c.channel_type = 'VIP'
          AND s.is_active = true
          AND s.end_date > NOW()
    ),
    ever_vip AS (
        SELECT DISTINCT s.user_id
        FROM subscriptions s
        JOIN channels c ON c.id = s.channel_id
        WHERE c.channel_type = 'VIP'
    )
    SELECT e.user_id, u.username, u.first_name,
           (SELECT MAX(s2.end_date)
            FROM subscriptions s2
            JOIN channels c2 ON c2.id = s2.channel_id
            WHERE s2.user_id = e.user_id AND c2.channel_type = 'VIP') AS last_end
    FROM ever_vip e
    LEFT JOIN active_vip a ON a.user_id = e.user_id
    LEFT JOIN users u ON u.telegram_id = e.user_id
    WHERE a.user_id IS NULL
    ORDER BY last_end DESC NULLS LAST
    """
)

VIP_CHANNELS_QUERY = text(
    """
    SELECT channel_id, channel_name
    FROM channels
    WHERE channel_type = 'VIP' AND is_active = true
    ORDER BY id
    """
)


def resolve_database_url() -> str:
    """Usa URL pública si DATABASE_URL apunta al host interno de Railway."""
    url = os.getenv("DATABASE_URL", "").strip()
    public = os.getenv("DATABASE_PUBLIC_URL", "").strip()
    if public and (not url or "railway.internal" in url):
        return public
    if url:
        return url
    if public:
        return public
    raise SystemExit("ERROR: define DATABASE_URL o DATABASE_PUBLIC_URL")


def parse_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "")
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


def fetch_ex_vip_users(engine) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(EX_VIP_QUERY).fetchall()
        channels = conn.execute(VIP_CHANNELS_QUERY).fetchall()
    if not channels:
        raise SystemExit("ERROR: no hay canales VIP activos en BD")
    return [
        {
            "user_id": int(r[0]),
            "username": r[1],
            "first_name": r[2],
            "last_end": r[3],
        }
        for r in rows
    ], [(int(c[0]), c[1]) for c in channels]


async def ban_user(bot: Bot, chat_id: int, user_id: int) -> tuple[str, str | None]:
    try:
        await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        return "banned", None
    except TelegramBadRequest as exc:
        msg = str(exc).lower()
        if "user_not_participant" in msg or "not found" in msg:
            return "not_member", str(exc)
        if "user is an administrator" in msg:
            return "skipped_admin", str(exc)
        return "error", str(exc)
    except TelegramForbiddenError as exc:
        return "forbidden", str(exc)
    except Exception as exc:
        return "error", str(exc)


async def run_apply(bot: Bot, users: list[dict], channels: list[tuple[int, str]]) -> dict:
    stats = {"banned": 0, "not_member": 0, "skipped_admin": 0, "error": 0, "forbidden": 0}
    for user in users:
        uid = user["user_id"]
        for chat_id, channel_name in channels:
            status, detail = await ban_user(bot, chat_id, uid)
            stats[status] = stats.get(status, 0) + 1
            logger.info(
                f"ban_expired_vip | user_id={uid} | channel={channel_name} | "
                f"chat_id={chat_id} | result={status}"
                + (f" | detail={detail}" if detail and status == "error" else "")
            )
            await asyncio.sleep(0.05)
    return stats


def print_report(users: list[dict], channels: list[tuple[int, str]], admin_ids: set[int]) -> None:
    excluded = [u for u in users if u["user_id"] in admin_ids]
    targets = [u for u in users if u["user_id"] not in admin_ids]
    print(f"\nCanales VIP activos: {len(channels)}")
    for chat_id, name in channels:
        print(f"  - {name} ({chat_id})")
    print(f"\nEx-VIP sin suscripción activa: {len(users)}")
    print(f"  Objetivo de ban: {len(targets)}")
    if excluded:
        print(f"  Excluidos (ADMIN_IDS): {len(excluded)} -> {[u['user_id'] for u in excluded]}")
    print("\nPrimeros 15 candidatos:")
    for u in targets[:15]:
        uname = f"@{u['username']}" if u["username"] else "?"
        print(
            f"  tg={u['user_id']} {uname} "
            f"name={u['first_name'] or '?'} last_end={u['last_end']}"
        )
    if len(targets) > 15:
        print(f"  ... y {len(targets) - 15} más")


async def async_main(args: argparse.Namespace) -> int:
    token = os.getenv("BOT_TOKEN", "").strip()
    if args.apply and not token:
        raise SystemExit("ERROR: BOT_TOKEN requerido para --apply")

    engine = create_engine(resolve_database_url())
    users, channels = fetch_ex_vip_users(engine)
    admin_ids = parse_admin_ids()
    targets = [u for u in users if u["user_id"] not in admin_ids]

    print_report(users, channels, admin_ids)

    if args.dry_run or not args.apply:
        print("\n[DRY-RUN] No se ejecutaron bans. Usa --apply para banear en Telegram.")
        return 0

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        me = await bot.get_me()
        print(f"\nBot: @{me.username} (id={me.id})")
        print(f"Iniciando ban de {len(targets)} usuarios — {datetime.now(UTC).isoformat()}")
        stats = await run_apply(bot, targets, channels)
        print("\nResumen:")
        for key, count in sorted(stats.items()):
            print(f"  {key}: {count}")
        return 0 if stats.get("error", 0) == 0 and stats.get("forbidden", 0) == 0 else 1
    finally:
        await bot.session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ban ex-VIP users from Telegram VIP channel(s)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Solo listar candidatos")
    mode.add_argument("--apply", action="store_true", help="Ejecutar ban_chat_member en Telegram")
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    sys.exit(main())