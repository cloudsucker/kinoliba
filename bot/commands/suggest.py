import random
import logging
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from bot.states import SearchState, SuggestState
from bot.keyboards.suggest import build_suggest_keyboard
from bot.keyboards import build_card_keyboard, build_library_keyboard
from bot.helpers.send import send_new_card
from bot.conversation.messages_creator.library import create_library_message
from bot.data import get_filtered_lib, get_user_lib
from hubble.getters import get_search, get_info, enrich_with_watch_url
from ai import suggest_by_mood, suggest_random

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "🎲 Что посмотреть?")
async def suggest_menu(message: types.Message):
    await message.answer("Чего душа просит? 🤔", reply_markup=build_suggest_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# Option A: random unwatched from library
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sug:lib")
async def suggest_from_library(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id

    items = get_filtered_lib(chat_id, "unseen")
    if not items:
        items = get_filtered_lib(chat_id, "all")
    if not items:
        await callback.answer(
            "Библиотека пустая! Добавь что-нибудь через поиск.", show_alert=True
        )
        return

    item = random.choice(items)
    all_items = get_filtered_lib(chat_id, "all")
    idx = next(
        (i for i, x in enumerate(all_items) if str(x.get("id")) == str(item.get("id"))),
        0,
    )
    caption = create_library_message(item)
    keyboard = build_library_keyboard(item, idx=idx, total=len(all_items), current_filter="all")
    poster = item.get("kinopoisk_poster_url") or item.get("poster_url")

    if poster:
        try:
            await callback.message.bot.send_photo(
                chat_id=chat_id, photo=poster, caption=caption,
                parse_mode="HTML", reply_markup=keyboard,
            )
        except TelegramBadRequest:
            try:
                await callback.message.bot.send_photo(
                    chat_id=chat_id, photo=poster.replace("/orig/", "/360/"),
                    caption=caption, parse_mode="HTML", reply_markup=keyboard,
                )
            except TelegramBadRequest:
                await callback.message.answer(caption, parse_mode="HTML", reply_markup=keyboard)
    else:
        await callback.message.answer(caption, parse_mode="HTML", reply_markup=keyboard)

    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Option B: by mood/description (requires OpenRouter)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sug:mood")
async def suggest_mood_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Опиши что хочется — жанр, эпоха, настроение.\n"
        "<i>Например: «боевичок с юмором» или «что-нибудь душевное на вечер»</i>",
        parse_mode="HTML",
    )
    await state.set_state(SuggestState.waiting_for_mood)
    await callback.answer()


@router.message(SuggestState.waiting_for_mood)
async def suggest_mood_result(message: types.Message, state: FSMContext):
    mood = message.text.strip()
    await state.clear()
    await _find_via_ai(message.bot, message.chat.id, state, suggest_by_mood, mood)


# ─────────────────────────────────────────────────────────────────────────────
# Option C: fully random (requires OpenRouter)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sug:random")
async def suggest_random_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Подбираю...")
    await _find_via_ai(callback.message.bot, callback.message.chat.id, state, suggest_random)


# ─────────────────────────────────────────────────────────────────────────────
# Shared AI → search → show card helper
# ─────────────────────────────────────────────────────────────────────────────

async def _find_via_ai(bot, chat_id: int, state: FSMContext, ai_func, *args) -> None:
    """Calls AI function, searches hubble, shows result as a navigable search card."""
    title = await ai_func(*args)
    if not title:
        await bot.send_message(chat_id, "Не смог придумать... Попробуй ещё раз 😔")
        return

    search_data = await get_search(title)
    match = search_data.get("match")
    alternatives = search_data.get("movies", [])

    if not match:
        await bot.send_message(
            chat_id,
            f"Нейронка предложила «{title}», но в базе не нашёл 😔 Попробуй ещё раз.",
        )
        return

    if match.get("typename") != "person":
        info = await get_info(match["typename"], match["id"])
        match = {**match, **info}
    match = await enrich_with_watch_url(match)

    lib_item = get_user_lib(chat_id, match["typename"]).get(str(match.get("id")))
    watch_url = match.get("watch_url") or match.get("url")
    results = [{"id": str(match["id"]), "typename": match["typename"]}] + [
        {"id": str(m.get("id")), "typename": m.get("typename")} for m in alternatives
    ]
    keyboard = build_card_keyboard(
        content_type=match["typename"],
        content_id=str(match["id"]),
        lib_item=lib_item,
        watch_url=watch_url,
        idx=0,
        total=len(results),
    )

    sent = await send_new_card(bot, chat_id, match, keyboard)

    await state.set_state(SearchState.browsing)
    await state.set_data({
        "results": results,
        "idx": 0,
        "message_id": sent.message_id,
        "watch_url": watch_url,
    })
