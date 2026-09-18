# utils.py
from aiobale.enums import ChatType
from aiobale.types import Message
from aiobale.exceptions import BaleError
import logging

logger = logging.getLogger(__name__)


def get_chat_type(msg: Message) -> ChatType:
    t = msg.chat.type
    if isinstance(t, ChatType):
        return t
    try:
        return ChatType(int(t))
    except Exception:
        return ChatType.PRIVATE


async def safe_send(msg: Message, text: str, reply: bool = False):
    """ارسال امن پیام. reply=False یعنی بدون ریپلای"""
    try:
        chat_type = get_chat_type(msg)
        kwargs = {
            "text": text,
            "chat_id": msg.chat.id,
            "chat_type": chat_type,
        }
        if reply:
            kwargs["reply_to"] = msg
        await msg.client.send_message(**kwargs)
    except BaleError as e:
        logger.error("BaleError: %s", e)
    except Exception as e:
        logger.exception("خطا در ارسال: %s", e)


def is_admin(msg: Message, admin_id: int) -> bool:
    return msg.sender_id == admin_id


def bold(text: str) -> str:
    return f"**{text}**"


def italic(text: str) -> str:
    return f"__{text}__"