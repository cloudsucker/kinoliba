import asyncio
import logging

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LinkPreviewOptions,
)

from bot.conversation import create_message_founded
from hubble.getters import get_search, get_info, enrich_with_watch_url

logger = logging.getLogger(__name__)
router = Router()

MAX_RESULTS = 10
MIN_QUERY_LEN = 2


def _poster_url(data: dict) -> str | None:
    url = data.get("kinopoisk_poster_url") or data.get("poster_url")
    if url:
        return url.replace("/orig/", "/360/")
    return None


def _build_article(data: dict) -> InlineQueryResultArticle | None:
    content_id = str(data.get("id", ""))
    typename = data.get("typename", "")
    if not content_id or not typename:
        return None

    answer = create_message_founded(data)
    text = (answer.get("message") or "")[:4096]
    if not text:
        return None

    title = data.get("title_russian") or data.get("title_original") or data.get("name") or "?"
    year = data.get("production_year") or data.get("release_start")
    description = f"{year}" if year else None

    # URL-only keyboard (callback buttons don't work in inline mode with FSM)
    buttons = []
    watch_url = data.get("watch_url")
    if watch_url:
        buttons.append([InlineKeyboardButton(text="▶️ Смотреть", url=watch_url)])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    # Use poster as link preview image above the message text
    poster = _poster_url(data)
    link_preview = None
    if poster:
        link_preview = LinkPreviewOptions(
            url=poster,
            prefer_large_media=True,
            show_above_text=True,
        )

    return InlineQueryResultArticle(
        id=f"{typename}:{content_id}",
        title=title,
        description=description,
        thumbnail_url=poster,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
            link_preview_options=link_preview,
        ),
        reply_markup=reply_markup,
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

    # Build article list
    articles = []
    for result in enriched:
        if isinstance(result, Exception) or not result:
            continue
        article = _build_article(result)
        if article:
            articles.append(article)

    await inline_query.answer(articles, cache_time=30)
