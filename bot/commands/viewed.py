from aiogram import types, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from bot.states import MarkAsViewedState
from bot.data.handler import mark_as_viewed, is_this_content_already_recommend
from bot.conversation import is_it_yes, create_message_founded
from bot.conversation import get_random_whats_viewed_response
from bot.conversation import get_random_not_found_in_list_response
from bot.conversation import get_random_recommendation_response
from bot.helpers import is_search_query_valid

from hubble.getters import get_search, get_info, enrich_with_watch_url


router = Router()


@router.message(Command("viewed"))
async def viewed(message: types.Message, state: FSMContext):
    """Принимает название контента, ищет его и предлагает отметить как просмотренный."""
    query = message.text[8:].strip()
    conversation_id = message.chat.id

    if not is_search_query_valid(query):
        await message.answer(get_random_whats_viewed_response())
        await state.set_state(MarkAsViewedState.waiting_for_content_name)
        return

    await process_query(query, message, state, conversation_id)


@router.message(StateFilter(MarkAsViewedState.waiting_for_content_name))
async def handle_content_name(message: types.Message, state: FSMContext):
    """Обрабатывает название контента после запроса."""
    query = message.text.strip()
    conversation_id = message.chat.id

    if not is_search_query_valid(query):
        await message.answer(get_random_not_found_in_list_response())
        await state.clear()
        return

    await process_query(query, message, state, conversation_id)


@router.callback_query(lambda c: c.data.startswith("select_movie_"))
async def handle_movie_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор фильма или сериала из инлайн-кнопок."""
    movie_id = callback.data.split("_")[2]
    movie_type = callback.data.split("_")[3]
    conversation_id = callback.message.chat.id

    match_info = await get_info(movie_type, movie_id)
    match_info = await enrich_with_watch_url(match_info)

    if is_this_content_already_recommend(conversation_id, movie_type, movie_id):
        await callback.message.answer("Вы его уже отмечали)")
        await callback.message.delete()
        await callback.answer()
        return

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
        await callback.message.answer(
            bot_message_answer,
            parse_mode="HTML",
        )

    await callback.message.answer(get_random_recommendation_response())
    await state.set_state(MarkAsViewedState.waiting_for_feedback)
    await state.update_data(content_id=movie_id, typename=movie_type)
    await callback.message.delete()
    await callback.answer()


async def process_query(
    query: str, message: types.Message, state: FSMContext, conversation_id: int
):
    """Выполняет поиск и отправляет ответ пользователю с инлайн-кнопками для альтернатив."""
    search_data = await get_search(query)
    match: dict = search_data.get("match", None)
    movies: list = search_data.get("movies", [])

    if not match:
        await message.answer(get_random_not_found_in_list_response())
        return

    content_id = match.get("id")
    content_type = match.get("typename")

    if is_this_content_already_recommend(conversation_id, content_type, content_id):
        await message.answer("Вы его уже отмечали)")
        return

    if content_type != "person":
        match_info = await get_info(content_type, content_id)
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
                        callback_data=f"select_movie_{movie.get('id')}_{movie.get('typename')}",
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

    await message.answer(get_random_recommendation_response())
    await state.update_data(content_id=content_id, typename=content_type)
    await state.set_state(MarkAsViewedState.waiting_for_feedback)


@router.message(StateFilter(MarkAsViewedState.waiting_for_feedback))
async def handle_recommendation(message: types.Message, state: FSMContext):
    """Обработка ответа пользователя на вопрос о рекомендации."""
    user_response = message.text.strip()
    conversation_id = message.chat.id

    data = await state.get_data()
    content_id = data.get("content_id")
    content_type = data.get("typename")

    recommend = is_it_yes(user_response.lower())

    if mark_as_viewed(conversation_id, content_type, content_id, recommend):
        if recommend:
            await message.answer("Отметил, круто, что зашло ☺")
        else:
            await message.answer("Правильно, плохое не рекомендуем... 😏")
    else:
        await message.answer("Чё-то не отметилось блин... 😞")

    await state.clear()
