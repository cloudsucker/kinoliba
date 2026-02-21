from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ai import is_available

IKB = InlineKeyboardButton


def build_suggest_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [IKB(text="📚 Из моей библиотеки", callback_data="sug:lib")],
    ]
    if is_available():
        buttons.append([IKB(text="💬 По настроению...", callback_data="sug:mood")])
        buttons.append([IKB(text="🎲 Удивить меня", callback_data="sug:random")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
