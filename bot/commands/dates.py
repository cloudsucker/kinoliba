import locale
import platform
import datetime
import re

from aiogram import types, Router
from aiogram.filters import Command

from bot.data import get_user_lib
from hubble.getters import get_series_dates

router = Router()


# SET LOCALE FOR RUSSIAN MONTHS NAMING
try:
    if platform.system() == "Windows":
        locale.setlocale(locale.LC_TIME, "Russian_Russia.1251")
    else:
        locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
except locale.Error:
    print("Warning: locale not found, using default")


months_genitive = {
    "январь": "января",
    "февраль": "февраля",
    "март": "марта",
    "апрель": "апреля",
    "май": "мая",
    "июнь": "июня",
    "июль": "июля",
    "август": "августа",
    "сентябрь": "сентября",
    "октябрь": "октября",
    "ноябрь": "ноября",
    "декабрь": "декабря",
}


@router.message(Command("dates"))
async def dates(message: types.Message):
    user_lib = get_user_lib(message.chat.id)
    user_tvseries: list[dict] = user_lib.get("tvseries", {})

    if not user_tvseries:
        await message.answer(
            "<b>У вас нет сериалов в коллекции. 😒</b>", parse_mode="HTML"
        )
        return

    await message.answer("<b>Сейчас всё проверю, секунду! 🤔</b>", parse_mode="HTML")

    # GETTING ALL TVSERIES DATA
    tvseries_not_sorted = []
    for tvseries in user_tvseries.values():
        title = tvseries.get("title_russian")
        tvseries_dates_data = await get_series_dates(title)

        production_year = tvseries_dates_data.get("production_year", "")
        is_next_season_in_prod = tvseries_dates_data.get("is_next_season_in_prod", "")
        new_episode_release_date = tvseries_dates_data.get("new_seria_date", "")
        seasons_dates_data = tvseries_dates_data.get("seasons", [])

        tvseries_not_sorted.append(
            {
                "title": title,
                "production_year": production_year,
                "is_next_season_in_prod": is_next_season_in_prod,
                "new_episode_release_date": new_episode_release_date,
                "seasons": seasons_dates_data,
            }
        )

    # IF NO 'new_episode_release_date' sorting by seasons.episodes.release_date
    for tvseries in tvseries_not_sorted:
        if not tvseries.get("new_episode_release_date"):
            seasons = tvseries.get("seasons")
            for season in seasons:
                episodes = season.get("episodes")
                for episode in episodes:
                    try:
                        release_date = datetime.datetime.strptime(
                            episode.get("release_date"), "%Y-%m-%d"
                        )
                        if release_date > datetime.datetime.now():
                            tvseries["new_episode_release_date"] = release_date
                            break
                    except Exception:
                        continue

            if not tvseries.get("new_episode_release_date"):
                tvseries["new_episode_release_date"] = None

    # SORTING TVSERIES
    tvseries_sorted_by_new_series_dates = []
    tvseries_withous_new_series_dates = []
    for tvseries in tvseries_not_sorted:
        if tvseries.get("new_episode_release_date"):
            tvseries_sorted_by_new_series_dates.append(tvseries)
        else:
            tvseries_withous_new_series_dates.append(tvseries)

    answer_text = "<b>📅 Даты выхода сериалов:</b>\n\n"

    for tvseries in tvseries_sorted_by_new_series_dates:
        title = tvseries.get("title")
        raw_date = tvseries.get("new_episode_release_date", "")

        new_episode_release_text = "дата неизвестна"

        if isinstance(raw_date, datetime.datetime):
            if raw_date.month == 0 or raw_date.day == 0:
                new_episode_release_text = f"{raw_date.year} год"
            else:
                day = raw_date.day
                month = raw_date.strftime("%B")
                month_genitive = months_genitive.get(month.lower(), month)
                new_episode_release_text = f"{day} {month_genitive}"

        elif isinstance(raw_date, str):
            if re.match(r"^\d{4}-00-00$", raw_date):
                year = raw_date.split("-")[0]
                new_episode_release_text = f"{year} год"
            elif re.match(r"^\d{4}-\d{2}-\d{2}$", raw_date):
                try:
                    parsed = datetime.datetime.strptime(raw_date, "%Y-%m-%d")
                    day = parsed.day
                    month = parsed.strftime("%B")
                    month_genitive = months_genitive.get(month.lower(), month)
                    new_episode_release_text = f"{day} {month_genitive}"
                except Exception:
                    pass
            elif re.match(r"^\d{4}$", raw_date):
                new_episode_release_text = f"{raw_date} год"

        answer_text += f"{title} - {new_episode_release_text}\n"

    await message.answer(answer_text, parse_mode="HTML")

    # SENDING CLOSED TVSERIES
    if tvseries_withous_new_series_dates:
        answer_text = "\n<b>😥 Завершённые сериалы:</b>\n\n"
        for tvseries in tvseries_withous_new_series_dates:
            title = tvseries.get("title")
            answer_text += f"{title}\n"
        await message.answer(answer_text, parse_mode="HTML")
