import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from aiogram import Bot, Dispatcher

from bot.data import get_token
from bot.commands import start, add, delete, search, my_list, help, viewed, share, dates


# LOGGER SETUP
log_handler = RotatingFileHandler(
    "bot.log",
    maxBytes=5_000_000,
    backupCount=5,
    encoding="utf-8",
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        log_handler,
        logging.StreamHandler(sys.stdout),
    ],
)
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("hubble").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("gemini").setLevel(logging.WARNING)
logger = logging.getLogger("kinoliba")

# BOT WOKEN UP
BOT_TOKEN = get_token()
bot = Bot(token=BOT_TOKEN, default_bot_properties={"parse_mode": "HTML"})
logger.info("Bot created")

# ROUTERS
dp = Dispatcher()
dp.include_router(start.router)
dp.include_router(add.router)
dp.include_router(delete.router)
dp.include_router(search.router)
dp.include_router(my_list.router)
dp.include_router(viewed.router)
dp.include_router(share.router)
dp.include_router(dates.router)
dp.include_router(help.router)
logger.info("Routers added")


# MAIN
async def main():
    await dp.start_polling(bot)
    logger.info("Bot started")


if __name__ == "__main__":
    asyncio.run(main())


# TODO:
#   - Добавить везде кнопки для ответов.
#   - Что посмотреть? (Рекомендации к просмотру)
#   - Что посмотреть? (непросмотренный контент из коллекции)
