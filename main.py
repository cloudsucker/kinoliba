import asyncio
from aiogram import Bot, Dispatcher

from bot.passphrase import PassphraseMiddleware
from bot.data import get_token
from bot.commands import start, add, delete, search, my_list, help, viewed, share, dates


# BOT WOKEN UP
BOT_TOKEN = get_token()
bot = Bot(token=BOT_TOKEN, default_bot_properties={"parse_mode": "HTML"})

# ROUTERS
dp = Dispatcher()
dp.message.middleware(PassphraseMiddleware())
dp.include_router(start.router)
dp.include_router(add.router)
dp.include_router(delete.router)
dp.include_router(search.router)
dp.include_router(my_list.router)
dp.include_router(viewed.router)
dp.include_router(share.router)
dp.include_router(dates.router)
dp.include_router(help.router)


# MAIN
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
