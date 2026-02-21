from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
)

from bot.states import SearchState
from bot.helpers import is_search_query_valid
from bot.conversation import create_message_founded
from bot.conversation import get_random_content_not_found
from bot.conversation import get_random_what_you_wanna_search

from hubble.getters import get_search, get_info, enrich_with_watch_url

from gemini import gemini_get_name_by_description

router = Router()


@router.message(default_state, lambda msg: msg.text and not msg.text.startswith("/"))
async def handle_search_query(message: types.Message, state: FSMContext):
    """
    Обрабатывает любое сообщение как поисковый запрос, кроме команд.
    """
    query = message.text.strip()

    if not is_search_query_valid(query):
        await message.answer(get_random_what_you_wanna_search())
        await state.set_state(SearchState.waiting_for_query)
        return

    await perform_search(query, message)


@router.message(SearchState.waiting_for_query)
async def handle_query_after_prompt(message: types.Message, state: FSMContext):
    """
    Обрабатывает сообщение после того, как бот запросил уточнение (ожидание запроса).
    """
    query = message.text.strip()

    if not is_search_query_valid(query):
        await message.answer(get_random_content_not_found())
        await state.clear()
        return

    await perform_search(query, message)
    await state.clear()


@router.callback_query(lambda c: c.data.startswith("search_movie_"))
async def handle_movie_selection(callback: types.CallbackQuery):
    """
    Обрабатывает выбор фильма или сериала из инлайн-кнопок.
    """
    movie_id = callback.data.split("_")[2]
    movie_type = callback.data.split("_")[3]

    match_info = await get_info(movie_type, movie_id)
    match_info = await enrich_with_watch_url(match_info)
    answer_data = create_message_founded(match_info)
    bot_message_answer = answer_data.get("message", None)
    bot_image_answer = answer_data.get("image", None)

    if bot_image_answer:
        try:
            await callback.message.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
            )
        except TelegramBadRequest:
            bot_image_answer = str.replace(bot_image_answer, "/orig/", "/360/")
            await callback.message.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
            )
    else:
        await callback.message.answer(bot_message_answer, parse_mode="HTML")

    await callback.message.delete()
    await callback.answer()


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery):
    """
    Обрабатывает inline-запросы для поиска фильмов и сериалов.
    """
    query = inline_query.query.strip()
    if not is_search_query_valid(query):
        await inline_query.answer([], cache_time=1)
        return

    search_data = await get_search(query)
    match: dict = search_data.get("match", None)
    movies: list = search_data.get("movies", [])
    results = []

    if not match:
        gemini_prediction = gemini_get_name_by_description(query)
        if gemini_prediction:
            search_data = await get_search(gemini_prediction)
            match: dict = search_data.get("match", None)
            movies: list = search_data.get("movies", [])
            results = []

    if match:
        match_typename = match.get("typename")
        if match_typename != "person":
            match_info = await get_info(match_typename, match.get("id"))
            match.update(match_info)

        match = await enrich_with_watch_url(match)
        answer_data = create_message_founded(match)
        message_text = answer_data.get("message", "")
        image_url = answer_data.get("image", None)
        title = match.get("title_russian") or match.get("title_original")
        year = match.get("production_year") or match.get("release_start", "N/A")
        content_type = "Сериал" if match_typename == "tvseries" else "Фильм"

        if image_url:
            results.append(
                InlineQueryResultPhoto(
                    id=str(match.get("id")),
                    photo_url=image_url,
                    thumbnail_url=str.replace(image_url, "/orig/", "/360/"),
                    caption=message_text,
                    parse_mode="HTML",
                    title=title,
                    description=f"{content_type}, {year}",
                )
            )
        else:
            results.append(
                InlineQueryResultArticle(
                    id=str(match.get("id")),
                    title=title,
                    input_message_content=InputTextMessageContent(
                        message_text=message_text, parse_mode="HTML"
                    ),
                    description=f"{content_type}, {year}",
                )
            )

    for movie in movies:
        title = movie.get("title_russian") or movie.get("title_original")
        year = movie.get("production_year") or movie.get("release_start", "N/A")
        content_type = "Сериал" if movie.get("typename") == "tvseries" else "Фильм"
        movie_info = await get_info(movie.get("typename"), movie.get("id"))
        movie_info = await enrich_with_watch_url(movie_info)
        answer_data = create_message_founded(movie_info)
        message_text = answer_data.get("message", "")
        image_url = answer_data.get("image", None)

        if image_url:
            results.append(
                InlineQueryResultPhoto(
                    id=str(movie.get("id")),
                    photo_url=image_url,
                    thumbnail_url=str.replace(image_url, "/orig/", "/360/"),
                    caption=message_text,
                    parse_mode="HTML",
                    title=title,
                    description=f"{content_type}, {year}",
                )
            )
        else:
            results.append(
                InlineQueryResultArticle(
                    id=str(movie.get("id")),
                    title=title,
                    input_message_content=InputTextMessageContent(
                        message_text=message_text, parse_mode="HTML"
                    ),
                    description=f"{content_type}, {year}",
                )
            )

    await inline_query.answer(results, cache_time=1)


async def perform_search(query: str, message: types.Message):
    """
    Выполняет поиск и отправляет ответ пользователю с инлайн-кнопками для альтернатив.
    """
    search_data = await get_search(query)
    match: dict = search_data.get("match", None)
    movies: list = search_data.get("movies", [])

    if not match:
        gemini_prediction = gemini_get_name_by_description(query)
        if gemini_prediction:
            search_data = await get_search(gemini_prediction)
            match: dict = search_data.get("match", None)
            movies: list = search_data.get("movies", [])

        if not match:
            await message.answer(get_random_content_not_found())
            return

    match_typename = match.get("typename")
    if match_typename != "person":
        match_info = await get_info(match_typename, match.get("id"))
        match.update(match_info)

    match = await enrich_with_watch_url(match)
    answer_data: dict = create_message_founded(match)
    bot_message_answer = answer_data.get("message", None)
    bot_image_answer = answer_data.get("image", None)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if movies:
        for movie in movies:
            title = movie.get("title_russian") or movie.get("title_original")
            movie_type = "Сериал" if movie.get("typename") == "tvseries" else "Фильм"
            button_text = f"{title} ({movie_type})"
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"search_movie_{movie.get('id')}_{movie.get('typename')}",
                    )
                ]
            )

    if bot_image_answer:
        try:
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
                reply_markup=keyboard if movies else None,
            )
        except TelegramBadRequest:
            bot_image_answer = str.replace(bot_image_answer, "/orig/", "/360/")
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
                reply_markup=keyboard if movies else None,
            )
    else:
        await message.answer(
            bot_message_answer,
            parse_mode="HTML",
            reply_markup=keyboard if movies else None,
        )
