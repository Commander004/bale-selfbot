# bot/handlers.py
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from bot.api import BaleBotAPI
from core import database as db
from core.auth_service import (
    send_login_code,
    session_exists,
    verify_code,
    verify_password,
)
from core.config import MAX_USERS

logger = logging.getLogger(__name__)


def _uid(message: Dict[str, Any]) -> int:
    return int(message["from"]["id"])


def _chat_id(message: Dict[str, Any]) -> int:
    return int(message["chat"]["id"])


def _text(message: Dict[str, Any]) -> str:
    return (message.get("text") or "").strip()


async def handle_message(bot: BaleBotAPI, message: Dict[str, Any]) -> None:
    if "from" not in message:
        return

    user_id = _uid(message)
    chat_id = _chat_id(message)
    text = _text(message)

    if not text:
        return

    # دستورات عمومی
    if text in ("/start", "/help"):
        await cmd_start(bot, chat_id, user_id)
        return

    if text == "/status":
        await cmd_status(bot, chat_id, user_id)
        return

    if text == "/logout":
        await cmd_logout(bot, chat_id, user_id)
        return

    if text == "/cancel":
        db.clear_login_state(user_id)
        bot.send_message(chat_id, "عملیات لغو شد. برای شروع دوباره /start بزنید.")
        return

    # ادامه فلو لاگین
    state = db.get_login_state(user_id)
    if state:
        step = state.get("step")
        if step == "wait_phone":
            await on_phone(bot, chat_id, user_id, text)
            return
        if step == "wait_code":
            await on_code(bot, chat_id, user_id, text, state)
            return
        if step == "wait_password":
            await on_password(bot, chat_id, user_id, text, state)
            return

    bot.send_message(
        chat_id,
        "دستور نامشخص است.\n"
        "/start — شروع / ثبت‌نام\n"
        "/status — وضعیت حساب\n"
        "/logout — خروج از سشن\n"
        "/cancel — لغو عملیات جاری",
    )


async def cmd_start(bot: BaleBotAPI, chat_id: int, user_id: int) -> None:
    user = db.get_user(user_id)
    if user and user.get("status") == "active" and session_exists(user_id):
        name = user.get("account_name") or "—"
        phone = user.get("phone") or "—"
        bot.send_message(
            chat_id,
            "✅ شما قبلاً وارد شده‌اید.\n\n"
            f"📱 شماره: `{phone}`\n"
            f"👤 نام: {name}\n"
            f"🆔 اکانت: {user.get('account_id') or '—'}\n"
            f"📁 سشن: {user.get('session_file') or '—'}\n\n"
            "دستورات را در پیوی خودتان (Saved Messages) بزنید.\n"
            "وضعیت: /status\n"
            "خروج: /logout",
        )
        return

    if db.count_users() >= MAX_USERS and not (user and user.get("status") == "active"):
        bot.send_message(chat_id, f"ظرفیت پر است (حداکثر {MAX_USERS} کاربر).")
        return

    db.set_login_state(user_id, step="wait_phone")
    bot.send_message(
        chat_id,
        "👋 به سامانه خوش آمدید.\n\n"
        "برای اولین ورود، شماره موبایل بله خود را بفرستید.\n"
        "مثال: `09123456789`\n\n"
        "لغو: /cancel",
    )


async def cmd_status(bot: BaleBotAPI, chat_id: int, user_id: int) -> None:
    user = db.get_user(user_id)
    if not user or user.get("status") != "active":
        bot.send_message(chat_id, "هنوز وارد نشده‌اید. /start را بزنید.")
        return
    has_session = session_exists(user_id)
    bot.send_message(
        chat_id,
        "📊 وضعیت شما\n\n"
        f"وضعیت: {'🟢 فعال' if has_session else '🔴 سشن ناقص'}\n"
        f"شماره: {user.get('phone')}\n"
        f"نام: {user.get('account_name') or '—'}\n"
        f"آخرین ورود: {user.get('last_login') or '—'}\n"
        f"سشن: {user.get('session_file')}",
    )


async def cmd_logout(bot: BaleBotAPI, chat_id: int, user_id: int) -> None:
    user = db.get_user(user_id)
    if user and user.get("session_file"):
        try:
            from pathlib import Path

            p = Path(user["session_file"])
            if p.exists():
                p.unlink()
        except Exception as e:
            logger.warning("delete session: %s", e)
    db.upsert_user(user_id, status="logged_out")
    db.clear_login_state(user_id)
    bot.send_message(chat_id, "خارج شدید. برای ورود دوباره /start بزنید.")


async def on_phone(bot: BaleBotAPI, chat_id: int, user_id: int, text: str) -> None:
    bot.send_message(chat_id, "⏳ در حال ارسال کد...")
    result = await send_login_code(user_id, text)
    if not result.get("ok"):
        bot.send_message(chat_id, f"❌ {result.get('error')}\nدوباره شماره را بفرستید یا /cancel")
        return

    db.set_login_state(
        user_id,
        step="wait_code",
        phone=result["phone"],
        transaction_hash=result["transaction_hash"],
    )
    bot.send_message(
        chat_id,
        "✅ کد ارسال شد.\n"
        "کد را از پیامک / اعلان بله وارد کنید.\n\n"
        "لغو: /cancel",
    )


async def on_code(
    bot: BaleBotAPI,
    chat_id: int,
    user_id: int,
    text: str,
    state: Dict[str, Any],
) -> None:
    tx = state.get("transaction_hash")
    if not tx:
        db.set_login_state(user_id, step="wait_phone")
        bot.send_message(chat_id, "نشست منقضی شد. دوباره شماره را بفرستید.")
        return

    bot.send_message(chat_id, "⏳ در حال بررسی کد...")
    result = await verify_code(user_id, text, tx)

    if result.get("need_password"):
        db.set_login_state(user_id, step="wait_password", transaction_hash=tx)
        bot.send_message(chat_id, "🔐 این اکانت رمز دو مرحله‌ای دارد.\nرمز را وارد کنید:")
        return

    if not result.get("ok"):
        bot.send_message(chat_id, f"❌ {result.get('error')}\nکد را دوباره بفرستید یا /cancel")
        return

    await _finish_login(bot, chat_id, user_id, state.get("phone"), result)


async def on_password(
    bot: BaleBotAPI,
    chat_id: int,
    user_id: int,
    text: str,
    state: Dict[str, Any],
) -> None:
    tx = state.get("transaction_hash")
    if not tx:
        db.clear_login_state(user_id)
        bot.send_message(chat_id, "نشست منقضی شد. /start")
        return

    bot.send_message(chat_id, "⏳ در حال بررسی رمز...")
    result = await verify_password(user_id, text, tx)
    if not result.get("ok"):
        bot.send_message(chat_id, f"❌ {result.get('error')}")
        return

    await _finish_login(bot, chat_id, user_id, state.get("phone"), result)


async def _finish_login(
    bot: BaleBotAPI,
    chat_id: int,
    user_id: int,
    phone: str,
    result: Dict[str, Any],
) -> None:
    db.upsert_user(
        user_id,
        phone=phone,
        session_file=result.get("session_file"),
        account_id=result.get("account_id"),
        account_name=result.get("account_name"),
        status="active",
    )
    db.clear_login_state(user_id)
    bot.send_message(
        chat_id,
        "🎉 ورود موفق!\n\n"
        "سشن شما ذخیره شد.\n"
        "از این به بعد دستورات را در **پیوی خودتان** (Saved Messages) بزنید.\n\n"
        "وضعیت: /status\n"
        "خروج: /logout",
    )
