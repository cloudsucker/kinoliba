from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from bot.data import get_filtered_lib, mark_viewed_only, set_recommend_status, delete_content_from_user_lib
from bot.keyboards import build_library_keyboard
from bot.helpers.send import edit_library_card
from bot.conversation.messages_creator.library import create_library_message

router = Router()

EMPTY_MSG = "<b>Ничего не найдено в библиотеке 🙁</b>\n\nПопробуй другой фильтр или добавь что-нибудь — просто напиши название!"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _show_library(
    bot,
    chat_id: int,
    filter_key: str,
    idx: int,
    message_to_edit=None,
) -> None:
    """
    Renders a library carousel card. Sends a new message or edits an existing one.
    message_to_edit: the Message object to call edit_* on, or None to send new.
    """
    items = get_filtered_lib(chat_id, filter_key)

    if not items:
        text = EMPTY_MSG
        if message_to_edit:
            try:
                await message_to_edit.edit_caption(caption=text, parse_mode="HTML", reply_markup=None)
            except TelegramBadRequest:
                try:
                    await message_to_edit.edit_text(text=text, parse_mode="HTML", reply_markup=None)
                except TelegramBadRequest:
                    pass
        else:
            await bot.send_message(chat_id, text, parse_mode="HTML")
        return

    idx = max(0, min(idx, len(items) - 1))
    item = items[idx]

    caption = create_library_message(item)
    keyboard = build_library_keyboard(item, idx=idx, total=len(items), current_filter=filter_key)

    if message_to_edit:
        await edit_library_card(message_to_edit, item, caption, keyboard)
    else:
        poster = item.get("kinopoisk_poster_url") or item.get("poster_url")
        if poster:
            from aiogram.exceptions import TelegramBadRequest as TBR
            try:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=poster,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            except TBR:
                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=poster.replace("/orig/", "/360/"),
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                except TBR:
                    await bot.send_message(chat_id, caption, parse_mode="HTML", reply_markup=keyboard)
        else:
            await bot.send_message(chat_id, caption, parse_mode="HTML", reply_markup=keyboard)


# ─────────────────────────────────────────────────────────────────────────────
# Entry points
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("list"))
@router.message(F.text == "📋 Библиотека")
async def show_library(message: types.Message):
    await _show_library(message.bot, message.chat.id, filter_key="all", idx=0)


# ─────────────────────────────────────────────────────────────────────────────
# Library navigation and filter callbacks  (lib:action:filter:idx)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("lib:"))
async def handle_library_nav(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]   # n(ext) | p(rev) | f(ilter)
    filt = parts[2]     # all | film | tv | seen | unseen | rec
    idx = int(parts[3])

    if action == "n":
        new_idx = idx + 1
    elif action == "p":
        new_idx = idx - 1
    else:
        new_idx = 0     # filter change always resets to first item

    await _show_library(callback.bot, callback.message.chat.id, filt, new_idx, callback.message)
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Library action callbacks  (lv / ld / lr0 / lr1 : type : id : filter : idx)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_lib_action(data: str):
    """Returns (action, content_type, content_id, filter_key, idx)."""
    parts = data.split(":")
    return parts[0], parts[1], parts[2], parts[3], int(parts[4])


@router.callback_query(F.data.startswith("lv:"))
async def handle_lib_viewed(callback: types.CallbackQuery):
    action, content_type, content_id, filt, idx = _parse_lib_action(callback.data)
    mark_viewed_only(callback.message.chat.id, content_type, content_id)
    await callback.answer("✅ Просмотрено!")
    await _show_library(callback.bot, callback.message.chat.id, filt, idx, callback.message)


@router.callback_query(F.data.startswith("ld:"))
async def handle_lib_delete(callback: types.CallbackQuery):
    action, content_type, content_id, filt, idx = _parse_lib_action(callback.data)
    delete_content_from_user_lib(callback.message.chat.id, content_type, content_id)
    await callback.answer("Удалено!")
    # After delete: show item at same position (or last if we were at the end)
    await _show_library(callback.bot, callback.message.chat.id, filt, idx, callback.message)


@router.callback_query(F.data.startswith("lr"))
async def handle_lib_recommend(callback: types.CallbackQuery):
    action, content_type, content_id, filt, idx = _parse_lib_action(callback.data)
    recommend = action == "lr1"
    set_recommend_status(callback.message.chat.id, content_type, content_id, recommend)
    await callback.answer("👍 Советую ✓" if recommend else "👎 Не советую ✓")
    # Refresh caption + keyboard (status text changes in caption)
    await _show_library(callback.bot, callback.message.chat.id, filt, idx, callback.message)
