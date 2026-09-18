# core/auth_service.py
"""لاگین برنامه‌ای اکانت شخصی بله با aiobale (بدون ترمینال)."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

from aiobale import Client, Dispatcher
from aiobale.enums import AuthErrors

from core.config import SESSIONS_DIR

logger = logging.getLogger(__name__)


def normalize_phone(raw: str) -> Optional[int]:
    """تبدیل شماره به int بین‌المللی (مثال: 98912...)."""
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = "98" + digits[1:]
    if digits.startswith("9") and len(digits) == 10:
        digits = "98" + digits
    if len(digits) < 10 or len(digits) > 15:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def session_path_for(bot_user_id: int) -> Path:
    Path(SESSIONS_DIR).mkdir(parents=True, exist_ok=True)
    return Path(SESSIONS_DIR) / f"user_{bot_user_id}.bale"


def _make_client(bot_user_id: int) -> Client:
    path = session_path_for(bot_user_id)
    dp = Dispatcher()
    return Client(dp, session_file=path)


async def send_login_code(bot_user_id: int, phone_raw: str) -> Dict[str, Any]:
    """ارسال کد ورود. خروجی: ok / error + transaction_hash."""
    phone = normalize_phone(phone_raw)
    if phone is None:
        return {"ok": False, "error": "شماره نامعتبر است. مثال: 09123456789"}

    client = _make_client(bot_user_id)
    try:
        result = await client.start_phone_auth(phone)
    except Exception as e:
        logger.exception("start_phone_auth failed")
        return {"ok": False, "error": f"خطا در ارسال کد: {e}"}

    if isinstance(result, AuthErrors):
        mapping = {
            AuthErrors.NUMBER_BANNED: "این شماره مسدود است.",
            AuthErrors.RATE_LIMIT: "تعداد درخواست زیاد است. کمی صبر کنید.",
            AuthErrors.AUTH_LIMIT: "محدودیت احراز هویت. کمی صبر کنید.",
            AuthErrors.INVALID: "شماره نامعتبر است.",
        }
        return {"ok": False, "error": mapping.get(result, f"خطای احراز هویت: {result.name}")}

    tx = getattr(result, "transaction_hash", None)
    if not tx:
        return {"ok": False, "error": "پاسخ نامعتبر از سرور بله."}

    return {
        "ok": True,
        "phone": str(phone),
        "transaction_hash": tx,
        "is_registered": bool(getattr(result, "is_registered", True)),
    }


async def verify_code(
    bot_user_id: int,
    code: str,
    transaction_hash: str,
) -> Dict[str, Any]:
    """تأیید کد. ممکن است نیاز به پسورد باشد."""
    code = (code or "").strip()
    if not code.isdigit() or len(code) < 4:
        return {"ok": False, "error": "کد نامعتبر است."}

    client = _make_client(bot_user_id)
    try:
        result = await client.validate_code(code, transaction_hash)
    except Exception as e:
        logger.exception("validate_code failed")
        return {"ok": False, "error": f"خطا در بررسی کد: {e}"}

    if result == AuthErrors.WRONG_CODE:
        return {"ok": False, "error": "کد اشتباه است."}
    if result == AuthErrors.PASSWORD_NEEDED:
        return {"ok": False, "need_password": True, "error": None}
    if result == AuthErrors.SIGN_UP_NEEDED:
        return {"ok": False, "error": "این شماره در بله ثبت‌نام نشده است."}
    if isinstance(result, AuthErrors):
        return {"ok": False, "error": f"خطا: {result.name}"}

    path = session_path_for(bot_user_id)
    account_id = None
    account_name = None
    try:
        # بعد از ذخیره سشن، اطلاعات پایه
        if hasattr(result, "id"):
            account_id = result.id
        me = getattr(client, "me", None) or getattr(client, "_me", None)
        if me is not None:
            account_id = getattr(me, "id", account_id)
            account_name = getattr(me, "name", None) or getattr(me, "title", None)
    except Exception:
        pass

    return {
        "ok": True,
        "session_file": str(path),
        "account_id": account_id,
        "account_name": account_name,
    }


async def verify_password(
    bot_user_id: int,
    password: str,
    transaction_hash: str,
) -> Dict[str, Any]:
    password = (password or "").strip()
    if not password:
        return {"ok": False, "error": "رمز خالی است."}

    client = _make_client(bot_user_id)
    try:
        result = await client.validate_password(password, transaction_hash)
    except Exception as e:
        logger.exception("validate_password failed")
        return {"ok": False, "error": f"خطا در بررسی رمز: {e}"}

    if result == AuthErrors.WRONG_PASSWORD:
        return {"ok": False, "error": "رمز اشتباه است."}
    if isinstance(result, AuthErrors):
        return {"ok": False, "error": f"خطا: {result.name}"}

    path = session_path_for(bot_user_id)
    return {
        "ok": True,
        "session_file": str(path),
        "account_id": getattr(result, "id", None),
        "account_name": None,
    }


def session_exists(bot_user_id: int) -> bool:
    p = session_path_for(bot_user_id)
    return p.exists() and p.stat().st_size > 0
