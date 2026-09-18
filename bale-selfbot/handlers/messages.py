# handlers/messages.py
"""AFK commands + auto-reply to private messages from others."""
import logging

from aiobale import Router, F
from aiobale.types import Message

from config import ADMIN_ID
from state import state
from utils import safe_send

logger = logging.getLogger(__name__)
router = Router()


def is_private(msg: Message) -> bool:
    try:
        return int(getattr(msg.chat.type, "value", msg.chat.type)) == 1
    except Exception:
        return False


@router.message(F.text.startswith("/afk"))
async def cmd_afk(msg: Message):
    if msg.sender_id != ADMIN_ID:
        return
    afk_text = (msg.text or "")[4:].strip() or "سلام نیستم، بعداً پیام بده."
    state.afk_enabled = True
    state.afk_text = afk_text
    await safe_send(msg, f"✅ AFK فعال شد:\n{afk_text}")


@router.message(F.text == "/unafk")
async def cmd_unafk(msg: Message):
    if msg.sender_id != ADMIN_ID:
        return
    state.afk_enabled = False
    await safe_send(msg, "❌ AFK خاموش شد.")


@router.message()
async def afk_auto_reply(msg: Message):
    """
    Catch remaining updates for AFK reply only.
    Must be last handler in this router.
    Does NOT block other routers if they are registered BEFORE messages_router
    and those handlers already matched — in aiobale, order is include order.
    Panel must NOT have a bare @router.message() catch-all.
    """
    if not state.afk_enabled:
        return
    if not msg.sender_id or msg.sender_id == ADMIN_ID:
        return
    if not is_private(msg):
        return
    text = msg.text
    if not text or str(text).startswith("/"):
        return

    try:
        await safe_send(msg, state.afk_text, reply=False)
    except Exception as e:
        logger.error("AFK send failed: %s", e)
