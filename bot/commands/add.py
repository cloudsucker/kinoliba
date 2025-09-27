from aiogram.filters import Command
from aiogram import Bot, types, Router
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.states import AddMovieState
from bot.helpers import is_search_query_valid
from bot.data import is_content_in_user_lib, save_content_to_user_lib
from bot.conversation import get_random_content_not_found
from bot.conversation import get_random_what_you_wanna_add
from bot.conversation import create_message_founded

from hubble.getters import get_search, get_info

router = Router()


@router.message(Command("add"))
async def add(message: types.Message, state: FSMContext, bot: Bot):
    query = message.text[5:].strip()
    if not is_search_query_valid(query):
        await message.answer(get_random_what_you_wanna_add())
        await state.set_state(AddMovieState.waiting_for_query)
        return
    await process_query(query, message, state, bot)


@router.message(AddMovieState.waiting_for_query)
async def handle_query(message: types.Message, state: FSMContext, bot: Bot):
    if not is_search_query_valid(message.text.strip()):
        await state.clear()
        return
    query = message.text.strip()
    if not is_search_query_valid(query):
        await message.answer(get_random_content_not_found())
        await state.clear()
        return
    await process_query(query, message, state, bot)


@router.callback_query(lambda c: c.data.startswith("add_movie_"))
async def handle_movie_selection(callback: types.CallbackQuery, state: FSMContext):
    movie_id = callback.data.split("_")[2]
    movie_type = callback.data.split("_")[3]
    conversation_id = callback.message.chat.id
    match_info = await get_info(movie_type, movie_id)
    answer_data = create_message_founded(match_info)
    bot_message_answer = answer_data.get("message", None)
    bot_image_answer = answer_data.get("image", None)
    current_data = await state.get_data()
    previous_content_message_id = current_data.get("content_message_id")
    previous_question_message_id = current_data.get("question_message_id")
    if previous_content_message_id:
        try:
            await callback.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=previous_content_message_id,
            )
        except TelegramBadRequest:
            pass
    if previous_question_message_id:
        try:
            await callback.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=previous_question_message_id,
            )
        except TelegramBadRequest:
            pass
    if bot_image_answer:
        try:
            content_message = await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
            )
        except TelegramBadRequest:
            bot_image_answer = str.replace(bot_image_answer, "/orig/", "/360/")
            content_message = await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
            )
    else:
        content_message = await callback.message.answer(
            bot_message_answer,
            parse_mode="HTML",
        )
    if is_content_in_user_lib(conversation_id, movie_type, movie_id):
        await callback.message.answer("Этот контент уже в вашей коллекции! 😊")
        await state.clear()
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Да", callback_data="confirm_add_yes"),
                    InlineKeyboardButton(text="Нет", callback_data="confirm_add_no"),
                ]
            ]
        )
        question_message = await callback.message.answer(
            "Добавить в список к просмотру?", reply_markup=keyboard
        )
        await state.set_state(AddMovieState.waiting_for_confirmation)
        await state.set_data(
            {
                "match_info": match_info,
                "content_message_id": content_message.message_id,
                "question_message_id": question_message.message_id,
            }
        )
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer()


async def process_query(
    query: str, message: types.Message, state: FSMContext, bot: Bot
):
    search_data = await get_search(query)
    match: dict = search_data.get("match", None)
    movies: list = search_data.get("movies", [])
    if not match:
        await message.answer(get_random_content_not_found())
        await state.clear()
        return
    match_typename = match.get("typename")
    conversation_id = message.chat.id
    if match_typename != "person":
        match_info = await get_info(match_typename, match.get("id"))
        match.update(match_info)
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
                        callback_data=f"add_movie_{movie.get('id')}_{movie.get('typename')}",
                    )
                ]
            )
    if bot_image_answer:
        try:
            content_message = await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
                reply_markup=keyboard if movies else None,
            )
        except TelegramBadRequest:
            bot_image_answer = str.replace(bot_image_answer, "/orig/", "/360/")
            content_message = await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
                reply_markup=keyboard if movies else None,
            )
    else:
        content_message = await message.answer(
            bot_message_answer,
            parse_mode="HTML",
            reply_markup=keyboard if movies else None,
        )
    if match_typename != "person" and is_content_in_user_lib(
        conversation_id, match_typename, match.get("id")
    ):
        await message.answer("Этот контент уже в вашей коллекции! 😊")
        await state.clear()
    else:
        confirm_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Да", callback_data="confirm_add_yes"),
                    InlineKeyboardButton(text="Нет", callback_data="confirm_add_no"),
                ]
            ]
        )
        question_message = await message.answer(
            "Добавить в список к просмотру?", reply_markup=confirm_keyboard
        )
        await state.set_state(AddMovieState.waiting_for_confirmation)
        await state.set_data(
            {
                "match_info": match,
                "content_message_id": content_message.message_id,
                "question_message_id": question_message.message_id,
            }
        )


@router.callback_query(lambda c: c.data.startswith("confirm_add_"))
async def handle_confirmation(callback: types.CallbackQuery, state: FSMContext):
    response = callback.data.split("_")[2]
    content_data = await state.get_data()
    match_info = content_data.get("match_info")
    conversation_id = callback.message.chat.id
    question_message_id = content_data.get("question_message_id")

    if response == "yes":
        if save_content_to_user_lib(conversation_id, match_info):
            await callback.message.answer("Добавил в список! 🎉")
        else:
            await callback.message.answer("Не добавляется чёто... 😔")
    else:
        await callback.message.answer("Ну ладно, не добавил... 😔")

    await state.clear()

    if question_message_id:
        try:
            await callback.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=question_message_id,
            )
        except TelegramBadRequest:
            pass

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.message(AddMovieState.waiting_for_confirmation)
async def handle_unexpected_message(message: types.Message):
    await message.answer("⬆️ Выбери ответ чтобы продолжить ⬆️")
