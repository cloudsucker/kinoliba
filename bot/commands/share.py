from aiogram import types, Router
from aiogram.filters import Command
from aiogram.types import InputMediaPhoto

from bot.data import get_users_recommends

router = Router()


@router.message(Command("share"))
async def my_list(message: types.Message):
    user_recommends = get_users_recommends(message.chat.id)

    if not user_recommends:
        await message.answer("<b>У вас нет рекомендаций 😒</b>", parse_mode="HTML")
        return

    await message.answer(
        "<b>Вот ваши рекомендации, перешлите другу! 😎</b>", parse_mode="HTML"
    )

    recommended_films: list[dict] = user_recommends.get("film", [])
    recommended_tvseries: list[dict] = user_recommends.get("tvseries", [])

    media_group = []

    for film in recommended_films:
        year = film.get("production_year", "")

        _genres_dicts: list[dict] = film.get("genres", [])
        _genres_list: list[str] = [genre.get("name") for genre in _genres_dicts]
        genres = "#" + " #".join(_genres_list[:3]) if _genres_list else ""

        _pre_title = film.get("title_russian", film.get("title_original"))
        title = f"{_pre_title}, {year} г. {"(" + genres + ")" if genres else ''}"

        media_group.append(InputMediaPhoto(media=film.get("kinopoisk_poster_url") or film.get("poster_url"), caption=title))

    for tvseries in recommended_tvseries:
        year = tvseries.get("release_start", "")

        _genres_dicts: list[dict] = tvseries.get("genres", [])
        _genres_list: list[str] = [genre.get("name") for genre in _genres_dicts]
        genres = "#" + " #".join(_genres_list[:3]) if _genres_list else ""

        _pre_title = tvseries.get("title_russian", tvseries.get("title_original"))
        title = f"{_pre_title}, {year} г. {"(" + genres + ")" if genres else ''}"

        media_group.append(
            InputMediaPhoto(media=tvseries.get("kinopoisk_poster_url") or tvseries.get("poster_url"), caption=title)
        )

    counter = 0
    for i in range(1, len(media_group) + 1):
        if i % 10 == 0 or i == len(media_group):
            await message.answer_media_group(media=media_group[counter:i])
            counter = i
