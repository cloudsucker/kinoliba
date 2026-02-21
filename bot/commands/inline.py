import asyncio
import logging

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from bot.conversation import create_message_founded
from hubble.getters import get_search, get_info, enrich_with_watch_url

logger = logging.getLogger(__name__)
router = Router()

MAX_RESULTS = 10
MIN_QUERY_LEN = 2


def _poster_urls(data: dict) -> tuple[str | None, str | None]:
    """Returns (full_url, thumbnail_url) for the poster."""
    url = data.get("kinopoisk_poster_url") or data.get("poster_url")
    if not url:
        return None, None
    thumb = url.replace("/orig/", "/360/")
    return url, thumb


def _watch_keyboard(data: dict) -> InlineKeyboardMarkup | None:
    watch_url = data.get("watch_url")
    if not watch_url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="▶️ Смотреть", url=watch_url)]]
    )


def _build_result(data: dict):
    """Build InlineQueryResultPhoto (with poster) or Article (without)."""
    content_id = str(data.get("id", ""))
    typename = data.get("typename", "")
    if not content_id or not typename:
        return None

    answer = create_message_founded(data)
    caption = (answer.get("message") or "")[:1024]
    if not caption:
        return None

    title = data.get("title_russian") or data.get("title_original") or data.get("name") or "?"
    result_id = f"{typename}:{content_id}"
    keyboard = _watch_keyboard(data)
    photo_url, thumb_url = _poster_urls(data)

    if photo_url:
        return InlineQueryResultPhoto(
            id=result_id,
            photo_url=photo_url,
            thumbnail_url=thumb_url,
            title=title,
            caption=caption,
            parse_mode="HTML",
            show_caption_above_media=False,
            reply_markup=keyboard,
        )

    # No poster — fall back to text article
    return InlineQueryResultArticle(
        id=result_id,
        title=title,
        input_message_content=InputTextMessageContent(
            message_text=caption,
            parse_mode="HTML",
        ),
        reply_markup=keyboard,
    )


async def _fetch_full_info(item: dict) -> dict:
    if item.get("typename") == "person":
        return item
    info = await get_info(item["typename"], item["id"])
    merged = {**item, **info}
    merged = await enrich_with_watch_url(merged)
    return merged


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery):
    query = inline_query.query.strip()
    if len(query) < MIN_QUERY_LEN:
        await inline_query.answer([], cache_time=5)
        return

    try:
        search_data = await get_search(query)
    except Exception:
        logger.exception("Inline search API error for query: %s", query)
        await inline_query.answer([], cache_time=5)
        return

    match = search_data.get("match")
    alternatives = search_data.get("movies", [])

    if not match:
        await inline_query.answer([], cache_time=10)
        return

    # Deduplicate by (typename, id)
    all_items = [match] + alternatives
    seen = set()
    unique = []
    for item in all_items:
        key = (item.get("typename"), str(item.get("id")))
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # Fetch full info + watch URL for ALL results in parallel
    enriched = await asyncio.gather(
        *(_fetch_full_info(it) for it in unique[:MAX_RESULTS]),
        return_exceptions=True,
    )

    # Build result list
    results = []
    for result in enriched:
        if isinstance(result, Exception) or not result:
            continue
        item = _build_result(result)
        if item:
            results.append(item)

    await inline_query.answer(results, cache_time=30)
