from aiogram import types, Router
from aiogram.filters import Command

from bot.keyboards import build_main_menu

router = Router()

START_MESSAGE = """<b>Привет, я КиноЛиба! 👋</b>

Просто напиши название фильма или сериала — я найду всё что нужно.
Можно и описание, если не помнишь название 😉

📋 <b>Библиотека</b> — твоя коллекция с удобной навигацией
📅 <b>Даты выхода</b> — когда выйдут новые серии твоих сериалов
"""


@router.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer(START_MESSAGE, parse_mode="HTML", reply_markup=build_main_menu())
