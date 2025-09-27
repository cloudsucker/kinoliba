from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.data.handler import get_passphrase


PASSPHRASE = get_passphrase()
authorized_users = set()


class PassphraseMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            user_id = event.from_user.id

            if user_id in authorized_users:
                return await handler(event, data)

            if event.text == PASSPHRASE:
                authorized_users.add(user_id)
                await event.answer(
                    "✅ Доступ разрешён! Теперь можно пользоваться ботом."
                )
                return

            await event.answer("❌ Введите пароль, чтобы использовать бота.")
            return
        return await handler(event, data)
