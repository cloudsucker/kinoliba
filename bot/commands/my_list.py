from aiogram import types, Router
from aiogram.filters import Command

from bot.data import get_user_lib

router = Router()


@router.message(Command("list"))
async def my_list(message: types.Message):
    user_lib = get_user_lib(message.chat.id)

    if not user_lib:
        await message.answer("<b>Ваша коллекция пуста. 😒</b>", parse_mode="HTML")
        return

    films = []
    tvseries = []

    for content_type, contents_pairs in user_lib.items():
        for _, content_data in contents_pairs.items():
            title = content_data.get("title_russian", "") or content_data.get(
                "title_original", ""
            )
            year = (
                content_data.get("production_year", "")
                if content_type == "film"
                else content_data.get("release_start", "")
            )
            _genres_dicts = content_data.get("genres", {})
            _genres_list = [genre.get("name") for genre in _genres_dicts]
            genres = "#" + " #".join(_genres_list[:3]) if _genres_list else ""
            recommend_emoji = "🔥" if content_data.get("recommend", "") else ""
            viewed_emoji = "✅" if content_data.get("viewed", "") else "❌"

            entry = {
                "title": title,
                "year": year,
                "genres": genres,
                "recommend_emoji": recommend_emoji,
                "viewed_emoji": viewed_emoji,
            }

            if content_type == "film":
                films.append(entry)
            elif content_type == "tvseries":
                tvseries.append(entry)

    films.sort(key=lambda x: x["title"].lower())
    tvseries.sort(key=lambda x: x["title"].lower())

    films_text = "<b>🎬 Фильмы:</b>\n\n"
    is_films_found = False
    films_counter = 0

    tvseries_text = "<b>📺 Сериалы:</b>\n\n"
    is_tvseries_found = False
    tvseries_counter = 0

    for film in films:
        films_counter += 1
        is_films_found = True
        films_text += f"{films_counter}. {film['title']}, {film['year']} г. ({film['genres']}) {film['recommend_emoji']}{film['viewed_emoji']}\n"

    for series in tvseries:
        tvseries_counter += 1
        is_tvseries_found = True
        tvseries_text += f"{tvseries_counter}. {series['title']}, {series['year']} г. ({series['genres']}) {series['recommend_emoji']}{series['viewed_emoji']}\n"

    if is_films_found:
        await message.answer(films_text, parse_mode="HTML")
    if is_tvseries_found:
        await message.answer(tvseries_text, parse_mode="HTML")
