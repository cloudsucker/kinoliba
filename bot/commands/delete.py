from aiogram.filters import Command
from aiogram import Bot, types, Router
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from bot.helpers import is_search_query_valid

from bot.states import DeleteMovieState
from bot.data import is_content_in_user_lib, delete_content_from_user_lib
from bot.conversation import is_it_yes, create_message_founded
from bot.conversation import get_random_what_you_wanna_delete
from bot.conversation import get_random_content_not_found

from hubble.getters import get_search, get_info

router = Router()


@router.message(Command("delete"))
async def delete(message: types.Message, state: FSMContext, bot: Bot):
    query = message.text[7:].strip()

    if not is_search_query_valid(query):
        await message.answer(get_random_what_you_wanna_delete())
        await state.set_state(DeleteMovieState.waiting_for_query)
        return

    await process_delete_query(query, message, state, bot)


@router.message(DeleteMovieState.waiting_for_query)
async def handle_delete_query(message: types.Message, state: FSMContext, bot: Bot):
    query = message.text.strip()

    if not is_search_query_valid(query):
        await message.answer(get_random_content_not_found())
        await state.clear()
        return

    await process_delete_query(query, message, state, bot)


async def process_delete_query(
    query: str, message: types.Message, state: FSMContext, bot: Bot
):
    search_data = await get_search(query)
    match: dict = search_data.get("match", None)

    if not match:
        await message.answer(get_random_content_not_found())
        return

    match_typename = match.get("typename")
    if match_typename != "person":
        match_info = await get_info(match_typename, match.get("id"))
        match.update(match_info)

    answer_data = create_message_founded(match)
    bot_message_answer = answer_data.get("message")
    bot_image_answer = answer_data.get("image")

    if bot_image_answer:
        try:
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
            )
        except TelegramBadRequest:
            bot_image_answer = bot_image_answer.replace("/orig/", "/360/")
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=bot_image_answer,
                caption=bot_message_answer,
                parse_mode="HTML",
            )
    else:
        await message.answer(bot_message_answer, parse_mode="HTML")

    content_id = match.get("id")
    content_type = match.get("typename")
    conversation_id = message.chat.id

    if is_content_in_user_lib(conversation_id, content_type, content_id):
        await message.answer("Удалить из списка?")
        await state.set_state(DeleteMovieState.waiting_for_confirmation)
        await state.set_data(match)
    else:
        await message.answer("Этого и так нет в списке.")
        await state.clear()


@router.message(DeleteMovieState.waiting_for_confirmation)
async def confirm_deletion(message: types.Message, state: FSMContext):
    response = message.text.strip().lower()

    if is_it_yes(response):
        content_data = await state.get_data()
        content_id = content_data.get("id")
        content_type = content_data.get("typename")
        conversation_id = message.chat.id

        success = delete_content_from_user_lib(
            conversation_id, content_type, content_id
        )

        if success:
            await message.answer("Удалил! 🗑️")
        else:
            await message.answer("Не получилось удалить... 😕")
    else:
        await message.answer("Ну и пусть остаётся. 😉")

    await state.clear()
