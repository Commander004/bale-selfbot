# main.py
import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from aiobale import Client, Dispatcher

from config import PHONE_NUMBER, SESSION_NAME, NAME_UPDATE_INTERVAL
from database import init_db
from state import state
from handlers import start_router, panel_router, messages_router

logging.basicConfig(
    level=logging.WARNING,  # ترمینال خلوت
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

TEHRAN = timezone(timedelta(hours=3, minutes=30))

dp = Dispatcher()
# ترتیب مهم است
dp.include_router(start_router)
dp.include_router(panel_router)
dp.include_router(messages_router)


async def name_clock_loop(client: Client):
    while True:
        try:
            if state.name_clock_enabled and state.name_format:
                now = datetime.now(TEHRAN).strftime("%H:%M")
                new_name = re.sub(r"time", now, state.name_format, flags=re.IGNORECASE)
                try:
                    await client.edit_name(new_name)
                except Exception as e:
                    logger.warning("edit_name failed: %s", e)
        except Exception as e:
            logger.exception("name_clock_loop: %s", e)

        await asyncio.sleep(NAME_UPDATE_INTERVAL)


async def main():
    print("🚀 Connecting to your Bale account...")
    init_db()

    session_path = Path(f"{SESSION_NAME}.bale")
    client = Client(
        dp,
        session_file=session_path,
        phone_number=PHONE_NUMBER if PHONE_NUMBER != "YOUR_PHONE" else None,
    )

    asyncio.create_task(name_clock_loop(client))
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())