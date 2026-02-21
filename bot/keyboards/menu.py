from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Библиотека"),
                KeyboardButton(text="📅 Даты выхода"),
            ],
            [
                KeyboardButton(text="🎲 Что посмотреть?"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
