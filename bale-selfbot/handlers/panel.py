# handlers/panel.py
import asyncio
import random
import re
import time
import logging
from datetime import datetime, timezone, timedelta

from aiobale import Router, F
from aiobale.types import Message

from config import ADMIN_ID
from database import get_user, save_user
from state import state
from utils import safe_send, is_admin

logger = logging.getLogger(__name__)
router = Router()

TEHRAN = timezone(timedelta(hours=3, minutes=30))

SWEARS = [
    "کصخل", "کیری", "حرومزاده", "لاشی", "جنده",
    "کصکش", "مادرجنده", "گوه", "احمق", "بی‌شعور",
    "کثافت", "ننه جنده", "پدر سگ", "حرومی", "گوساله",
]


def _waiting_name_format(msg: Message) -> bool:
    """Only match when admin is entering name format after /time on."""
    if not state.waiting_for_format:
        return False
    if msg.sender_id != ADMIN_ID:
        return False
    if not msg.text:
        return False
    if str(msg.text).startswith("/"):
        return False
    return True


@router.message(F.text == "/panel")
async def cmd_panel(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    text = (
        "⚙️ پنل مدیریت\n\n"
        "/profile       اطلاعات + پینگ\n"
        "/status        وضعیت سیستم\n"
        "/test          تست ارسال\n"
        "/afk متن       فعال کردن AFK\n"
        "/unafk         خاموش کردن AFK\n"
        "/time on       روشن کردن ساعت اسم\n"
        "/time off      خاموش کردن ساعت اسم\n"
        "/bold on|off   بولد خودکار\n"
        "/italic on|off ایتالیک خودکار\n"
        "اسپم N متن     تکرار متن\n"
        "رگباری N       فحش رگباری"
    )
    await safe_send(msg, text)


@router.message(F.text == "/profile")
async def cmd_profile(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return

    save_user(msg.sender_id)
    user = get_user(msg.sender_id)

    t0 = time.perf_counter()
    try:
        await msg.client.get_me()
        ping_ms = int((time.perf_counter() - t0) * 1000)
    except Exception:
        ping_ms = -1

    active = []
    if state.afk_enabled:
        active.append("AFK")
    if state.name_clock_enabled:
        active.append("ساعت اسم")
    if state.bold_enabled:
        active.append("Bold")
    if state.italic_enabled:
        active.append("Italic")

    features = " and ".join(active) if active else "هیچکدام"

    text = (
        "👤 پروفایل\n\n"
        f"🆔 شناسه: `{msg.sender_id}`\n"
        f"💬 چت: `{msg.chat.id}`\n"
        f"📌 نوع چت: `{msg.chat.type}`\n"
        f"📡 پینگ: `{ping_ms} ms`\n\n"
        f"قابلیت‌های فعال:\n{features}"
    )
    if user:
        text += f"\n\n📅 اولین حضور: {user['first_seen']}\n🕒 آخرین حضور: {user['last_seen']}"

    await safe_send(msg, text)


@router.message(F.text == "/status")
async def cmd_status(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    afk = "🟢 روشن" if state.afk_enabled else "🔴 خاموش"
    clock = "🟢 روشن" if state.name_clock_enabled else "🔴 خاموش"
    bold = "🟢 روشن" if state.bold_enabled else "🔴 خاموش"
    italic = "🟢 روشن" if state.italic_enabled else "🔴 خاموش"
    await safe_send(
        msg,
        f"🟢 سیستم فعال است.\n\n"
        f"AFK: {afk}\n"
        f"ساعت اسم: {clock}\n"
        f"Bold: {bold}\n"
        f"Italic: {italic}"
    )


@router.message(F.text == "/test")
async def cmd_test(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    await safe_send(msg, "✅ سیستم ارسال پیام سالم است.")


@router.message(F.text == "/bold on")
async def cmd_bold_on(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    state.bold_enabled = True
    await safe_send(msg, "✅ Bold روشن شد.\nاز این به بعد پیام‌های شما بولد می‌شوند.")


@router.message(F.text == "/bold off")
async def cmd_bold_off(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    state.bold_enabled = False
    await safe_send(msg, "❌ Bold خاموش شد.")


@router.message(F.text == "/italic on")
async def cmd_italic_on(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    state.italic_enabled = True
    await safe_send(msg, "✅ Italic روشن شد.\nاز این به بعد پیام‌های شما ایتالیک می‌شوند.")


@router.message(F.text == "/italic off")
async def cmd_italic_off(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    state.italic_enabled = False
    await safe_send(msg, "❌ Italic خاموش شد.")


@router.message(F.text.startswith("اسپم "))
async def cmd_spam(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await safe_send(msg, "فرمت: اسپم 3 متن مورد نظر")
        return
    try:
        count = int(parts[1])
    except ValueError:
        await safe_send(msg, "عدد نامعتبر است.")
        return
    if count < 1 or count > 30:
        await safe_send(msg, "تعداد باید بین ۱ تا ۳۰ باشد.")
        return
    text = parts[2]
    for _ in range(count):
        await safe_send(msg, text)
        await asyncio.sleep(0.4)


@router.message(F.text.startswith("رگباری "))
async def cmd_ragbari(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await safe_send(msg, "فرمت: رگباری 10")
        return
    try:
        count = int(parts[1])
    except ValueError:
        await safe_send(msg, "عدد نامعتبر است.")
        return
    if count < 1 or count > 50:
        await safe_send(msg, "تعداد باید بین ۱ تا ۵۰ باشد.")
        return
    for _ in range(count):
        await safe_send(msg, random.choice(SWEARS))
        await asyncio.sleep(0.35)


@router.message(F.text == "/time")
async def cmd_time_help(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    await safe_send(
        msg,
        "⏰ مدیریت ساعت روی اسم\n\n"
        "/time on   - روشن کردن\n"
        "/time off  - خاموش کردن\n\n"
        "بعد از on فرمت را بفرستید.\n"
        "مثال: commander04 time\n"
        "کلمه time با ساعت جایگزین می‌شود."
    )


@router.message(F.text == "/time on")
async def cmd_time_on(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    state.waiting_for_format = True
    await safe_send(
        msg,
        "📝 فرمت اسم را وارد کنید:\n\n"
        "مثال:\n"
        "commander04 time\n\n"
        "کلمه time با ساعت تهران جایگزین می‌شود.\n"
        "مثل: commander04 14:35"
    )


@router.message(F.text == "/time off")
async def cmd_time_off(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    state.name_clock_enabled = False
    state.waiting_for_format = False
    await safe_send(msg, "❌ ساعت روی اسم خاموش شد.")


# IMPORTANT: no bare @router.message() — that was blocking AFK
@router.message(F.func(_waiting_name_format))
async def receive_name_format(msg: Message):
    text = msg.text.strip()

    if "time" not in text.lower():
        await safe_send(
            msg,
            "❌ فرمت نامعتبر است.\n"
            "باید کلمه time داخلش باشد.\n"
            "مثال: commander04 time"
        )
        return

    state.name_format = text
    state.name_clock_enabled = True
    state.waiting_for_format = False

    now = datetime.now(TEHRAN).strftime("%H:%M")
    new_name = re.sub(r"time", now, text, flags=re.IGNORECASE)

    try:
        await msg.client.edit_name(new_name)
        await safe_send(
            msg,
            f"✅ ساعت روی اسم فعال شد.\n"
            f"فرمت: `{text}`\n"
            f"الان: `{new_name}`"
        )
    except Exception as e:
        logger.error("edit_name error: %s", e)
        await safe_send(msg, f"فرمت ذخیره شد ولی ویرایش اسم خطا داد:\n{e}")
