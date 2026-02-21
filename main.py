import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()  # must happen before any os.getenv() calls in other modules

from aiogram import Bot, Dispatcher

from bot.data import get_token
from bot.passphrase import PassphraseMiddleware
from bot.commands import start, search, my_list, suggest, help, dates, inline


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
logging.getLogger("ai").setLevel(logging.WARNING)
logger = logging.getLogger("kinoliba")

# BOT SETUP
BOT_TOKEN = get_token()
bot = Bot(token=BOT_TOKEN, default_bot_properties={"parse_mode": "HTML"})
logger.info("Bot created")

# ROUTERS
# Order matters: specific handlers (start, list, dates, help) before the
# generic free-text search handler so reply keyboard buttons are not
# intercepted as search queries.
dp = Dispatcher()
dp.message.middleware(PassphraseMiddleware())
dp.include_router(start.router)
dp.include_router(my_list.router)
dp.include_router(suggest.router)  # before search: handles "🎲 Что посмотреть?" text
dp.include_router(dates.router)
dp.include_router(help.router)
dp.include_router(inline.router)   # inline queries (@bot query)
dp.include_router(search.router)   # free-text catch-all must be last
logger.info("Routers added")


async def main():
    await dp.start_polling(bot)
    logger.info("Bot started")


if __name__ == "__main__":
    asyncio.run(main())
