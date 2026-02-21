import json
import os

from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.data import get_passphrase


PASSPHRASE = get_passphrase()
_AUTH_FILE = "bot/data/authorized_users.json"


def _load_authorized() -> set:
    if os.path.exists(_AUTH_FILE):
        try:
            with open(_AUTH_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, ValueError):
            pass
    return set()


def _save_authorized(users: set) -> None:
    with open(_AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(list(users), f)


authorized_users = _load_authorized()


class PassphraseMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            user_id = event.from_user.id

            if user_id in authorized_users:
                return await handler(event, data)

            if event.text == PASSPHRASE:
                authorized_users.add(user_id)
                _save_authorized(authorized_users)
                await event.answer(
                    "✅ Доступ разрешён! Теперь можно пользоваться ботом."
                )
                return

            await event.answer("❌ Введите пароль, чтобы использовать бота.")
            return
        return await handler(event, data)
