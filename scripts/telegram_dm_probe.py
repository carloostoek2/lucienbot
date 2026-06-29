#!/usr/bin/env python3
"""Sondeo live de entrega DM — bot de prueba Telegram.

Uso:
  TELEGRAM_TEST_BOT_TOKEN=... python scripts/telegram_dm_probe.py
  TELEGRAM_TEST_BOT_TOKEN=... TELEGRAM_TEST_TARGET_USER_ID=123 python scripts/telegram_dm_probe.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from utils.telegram_delivery import probe_send_message


async def main() -> int:
    token = os.getenv("TELEGRAM_TEST_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: define TELEGRAM_TEST_BOT_TOKEN")
        return 1

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        me = await bot.get_me()
        print(f"Bot: @{me.username} (id={me.id})")

        updates = await bot.get_updates(limit=20, timeout=0)
        print(f"Updates pendientes: {len(updates)}")
        for u in updates:
            if u.chat_join_request:
                jr = u.chat_join_request
                print(
                    f"  JOIN_REQUEST user={jr.from_user.id} "
                    f"user_chat_id={jr.user_chat_id} channel={jr.chat.id}"
                )

        target = os.getenv("TELEGRAM_TEST_TARGET_USER_ID", "").strip()
        if target:
            uid = int(target)
            r = await probe_send_message(bot, uid, "🧪 probe user.id")
            print(f"send user.id={uid}: success={r.success} code={r.permanent_code} err={r.error_text}")

        uchat = os.getenv("TELEGRAM_TEST_USER_CHAT_ID", "").strip()
        if uchat:
            cid = int(uchat)
            r = await probe_send_message(bot, cid, "🧪 probe user_chat_id")
            print(
                f"send user_chat_id={cid}: success={r.success} "
                f"code={r.permanent_code} err={r.error_text}"
            )

        if not target and not uchat:
            print("Tip: envía /start al bot o solicitud de unión a un canal admin.")
            print("Luego define TELEGRAM_TEST_TARGET_USER_ID y/o TELEGRAM_TEST_USER_CHAT_ID")
        return 0
    finally:
        await bot.session.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))