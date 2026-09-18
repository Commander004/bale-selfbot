# handlers/start.py
from aiobale import Router, F
from aiobale.types import Message

from config import ADMIN_ID
from database import save_user
from utils import safe_send, is_admin
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "/start")
async def cmd_start(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    save_user(msg.sender_id)
    await safe_send(msg, "سلام 👋\nدستیار شخصی شما فعال است.")


@router.message(F.text == "/help")
async def cmd_help(msg: Message):
    if not is_admin(msg, ADMIN_ID):
        return
    text = (
        "📚 راهنما (فقط شما)\n\n"
        "/start /panel /profile /status /test\n"
        "/afk متن | /unafk\n"
        "/bioclock\n"
        "/bold متن | /italic متن\n"
        "اسپم 3 متن\n"
        "رگباری 10\n"
        "ping | سلام"
    )
    await safe_send(msg, text)