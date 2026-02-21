from typing import Dict

from bot.helpers import format_rating


def create_library_message(lib_item: Dict) -> str:
    """
    Builds a compact caption for a library carousel card.
    Works with data stored in the library JSON (no API call needed).
    """
    typename = lib_item.get("typename", "")
    title = lib_item.get("title_russian") or lib_item.get("title_original", "")

    if typename == "film":
        year = lib_item.get("production_year", "")
        type_label = "Фильм"
    else:
        year = lib_item.get("release_start", "")
        type_label = "Сериал"

    genres_list = [g.get("name", "") for g in lib_item.get("genres", [])][:3]
    genres = ", ".join(genres_list) if genres_list else ""

    countries_list = [c.get("name", "") for c in lib_item.get("countries", [])][:3]
    countries = ", ".join(countries_list) if countries_list else ""

    rating_kp = format_rating(lib_item.get("rating_kinopoisk"))
    rating_imdb = format_rating(lib_item.get("rating_imdb"))
    rating_parts = []
    if rating_kp:
        rating_parts.append(f"КиноПоиск {rating_kp}")
    if rating_imdb:
        rating_parts.append(f"IMDb {rating_imdb}")
    rating_str = " | ".join(rating_parts)

    viewed = lib_item.get("viewed", False)
    recommend = lib_item.get("recommend")
    if viewed and recommend is True:
        status = "✅ Просмотрено · 🔥 Советую"
    elif viewed and recommend is False:
        status = "✅ Просмотрено · 👎 Не советую"
    elif viewed:
        status = "✅ Просмотрено"
    else:
        status = "❌ Не смотрел"

    lines = [f"<b>{title}{f', {year} г.' if year else ''}</b>", f"🎬 {type_label}"]
    if genres:
        lines.append(f"🎭 {genres}")
    if countries:
        lines.append(f"🌍 {countries}")
    if rating_str:
        lines.append(f"⭐ {rating_str}")
    lines.append("")
    lines.append(status)

    return "\n".join(lines)
