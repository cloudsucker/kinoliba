from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest

from bot.conversation import create_message_founded


def _fix_poster_url(url: str) -> str:
    return url.replace("/orig/", "/360/") if url else url


async def send_new_card(
    bot: Bot,
    chat_id: int,
    content_data: dict,
    keyboard: InlineKeyboardMarkup,
) -> Message:
    """Sends a new card message (photo + caption). Returns the sent Message."""
    answer = create_message_founded(content_data)
    caption = answer.get("message", "")
    poster = answer.get("image")

    if poster:
        try:
            return await bot.send_photo(
                chat_id=chat_id,
                photo=poster,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except TelegramBadRequest:
            try:
                return await bot.send_photo(
                    chat_id=chat_id,
                    photo=_fix_poster_url(poster),
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            except TelegramBadRequest:
                pass

    return await bot.send_message(
        chat_id=chat_id,
        text=caption,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def edit_card_content(
    message: Message,
    content_data: dict,
    keyboard: InlineKeyboardMarkup,
) -> None:
    """
    Edits an existing card message: replaces photo, caption, and keyboard.
    Used for search carousel navigation.
    """
    answer = create_message_founded(content_data)
    caption = answer.get("message", "")
    poster = answer.get("image")

    if poster:
        try:
            await message.edit_media(
                media=InputMediaPhoto(
                    media=poster,
                    caption=caption,
                    parse_mode="HTML",
                ),
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest:
            try:
                await message.edit_media(
                    media=InputMediaPhoto(
                        media=_fix_poster_url(poster),
                        caption=caption,
                        parse_mode="HTML",
                    ),
                    reply_markup=keyboard,
                )
                return
            except TelegramBadRequest:
                pass

    try:
        await message.edit_text(
            text=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except TelegramBadRequest:
        pass


async def edit_library_card(
    message: Message,
    lib_item: dict,
    caption: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    """
    Edits a library carousel card. Uses simplified caption built outside.
    Used for library navigation and after library actions that change the item.
    """
    poster = lib_item.get("kinopoisk_poster_url") or lib_item.get("poster_url")

    if poster:
        try:
            await message.edit_media(
                media=InputMediaPhoto(
                    media=poster,
                    caption=caption,
                    parse_mode="HTML",
                ),
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest:
            try:
                await message.edit_media(
                    media=InputMediaPhoto(
                        media=_fix_poster_url(poster),
                        caption=caption,
                        parse_mode="HTML",
                    ),
                    reply_markup=keyboard,
                )
                return
            except TelegramBadRequest:
                pass

    try:
        await message.edit_text(
            text=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except TelegramBadRequest:
        pass
