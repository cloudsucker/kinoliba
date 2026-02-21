from typing import Dict


from bot.helpers import get_locale_en_ru, format_rating
from bot.helpers import format_duration, truncate_after_word


def create_message_founded(data: Dict) -> str:
    """
    Метод для получения сообщения о найденном контенте или человеке.

    Parameters:
        data (Dict): словарь с отформатированными данными.

    Returns:
        message (Dict): готовое сообщение с информацией о контенте или человеке и изображение (опционально).
    """

    typename = data.get("typename")

    if typename == "film" or typename == "tvseries":
        message = _create_message_content_founded(data)
    elif typename == "person":
        message = _create_message_person_founded(data)

    return message


def _create_message_content_founded(content_data: Dict) -> Dict:
    """
    Функция для формирования сообщения о найденном контенте (фильмы, сериалы).

    Parameters:
        content_data (Dict): словарь с отформатированными данными о контенте.

    Returns:
        message (Dict): готовое сообщение с информацией о контенте с изображением (опционально).
    """

    typename = content_data.get("typename")

    # GETTING TITLE RUSSIAN IF IT EXISTS, OTHERWISE GETTING TITLE ENGLISH
    _pre_title = content_data.get("title_russian", "")
    title = content_data.get("title_original", "") if not _pre_title else _pre_title

    rating_kinopoisk = format_rating(content_data.get("rating_kinopoisk", ""))
    rating_imdb = format_rating(content_data.get("rating_imdb", ""))

    # GETTING SHORT DESCRIPTION IF IT EXISTS,
    # OTHERWISE GETTING SYNOPSIS WITH LIMIT OF 100 WORDS
    _short_desc = content_data.get("short_description", "")
    _synopsis = content_data.get("synopsis", "")
    description = _short_desc if _short_desc else truncate_after_word(_synopsis, 100)

    # COUNTRIES
    _pre_countries = content_data.get("countries", [])[:3]
    if _pre_countries:
        countries = ", ".join(
            [dict(country).get("name", "") for country in _pre_countries]
        )
    else:
        countries = "Нет информации"

    # GENRES
    _pre_genres = content_data.get("genres", [])[:3]
    if _pre_genres:
        genres = ", ".join([dict(genre).get("name", "") for genre in _pre_genres])
    else:
        genres = "Нет информации"

    # ACTORS
    _pre_actors = content_data.get("actors", [])[:3]
    if _pre_actors:
        actors = ", ".join(
            [
                (
                    dict(actor).get("name", "")
                    if dict(actor).get("name", "")
                    else dict(actor).get("original_name", "")
                )
                for actor in _pre_actors
            ]
        )
    else:
        actors = "Нет информации"

    # ADDING DURATION FOR FILM AND TVSERIES WITH SPECIFIC FORMATTING
    if typename == "film":
        year = content_data.get("production_year")
        duration = format_duration(content_data.get("duration", ""))
    elif typename == "tvseries":
        year = content_data.get("release_start")
        duration = format_duration(content_data.get("duration_series", ""))

    # POSTER, URL, LOCALIZATION FOR TYPENAME
    # kinopoisk_poster_url — новое имя поля (переименовано в бэке), poster_url — обратная совместимость с сохранёнными данными
    poster_url = content_data.get("kinopoisk_poster_url") or content_data.get("poster_url")
    watch_url = content_data.get("watch_url")
    url = watch_url or content_data.get("url")
    url_label = "🎬 <b>Смотреть:</b>" if watch_url else "🔗 <b>Ссылка:</b>"
    typename = get_locale_en_ru(typename)

    message = "\n\n".join(
        filter(
            None,
            [
                f"<b>{title}{f', {year} г.' if year else ''}</b>",
                "\n".join(
                    filter(
                        None,
                        [
                            f"🌍 <b>Страны:</b> {countries}" if countries else "",
                            f"🎭 <b>Жанры:</b> {genres}" if genres else "",
                            (
                                f"⏳ <b>Длительность:</b> {duration}"
                                if typename == "Фильм" and duration
                                else (
                                    f"⏳ <b>Длительность серии:</b> {duration}"
                                    if duration
                                    else ""
                                )
                            ),
                            f"🎬 <b>Тип контента:</b> {typename}",
                            (
                                (
                                    "⭐ <b>Рейтинг:</b> "
                                    + f"{'КиноПоиск ' + str(rating_kinopoisk) if rating_kinopoisk else ''}"
                                    + (
                                        f" | "
                                        if rating_kinopoisk and rating_imdb
                                        else ""
                                    )
                                    + (f"IMDb {rating_imdb}" if rating_imdb else "")
                                )
                                if rating_kinopoisk or rating_imdb
                                else ""
                            ),
                        ],
                    )
                ),
                f"📝 <b>Описание:</b> {description}" if description else "",
                f"🎭 <b>Актёры:</b> {actors}" if actors else "",
                f"{url_label} {url}",
            ],
        )
    )

    # IF POSTER EXISTS ADDING IT
    return {"message": message, "image": poster_url}


def _create_message_person_founded(person_data: Dict) -> Dict:
    """
    Функция для формирования сообщения о найденном человеке кино.

    Parameters:
        person_data (Dict): словарь с отформатированными данными о человеке.

    Returns:
        message (Dict): готовое сообщение с информацией о человеке с изображением (опционально).
    """

    typename = person_data.get("typename")
    if not typename == "person":
        raise ValueError(
            f"Error: create_message_person_founded got {typename}, expected Person."
        )

    # GETTING LOCALIZED NAME IF IT EXISTS OTHERWISE GETTING ORIGINAL
    _pre_name = person_data.get("original_name")
    name = person_data.get("name", "") if not _pre_name else _pre_name

    # GETTING BIRTH DATE
    birth_date = person_data.get("birth_date", "")

    # TODO: ADD MORE REQEUSTS FOR UPDATE PERSON DATA HERE

    # POSTER, URL
    url = person_data.get("person_url", "")
    avatars_url = person_data.get("avatars_url", None)

    message = f"""
<b>{name}</b>

{f"🎂 <b>Дата рождения:</b> {birth_date}\n" if birth_date else ''}🔗 <b>Ссылка:</b> {url}
"""

    # IF POSTER EXISTS ADDING IT
    return {"message": message, "image": avatars_url}
