import asyncio
import logging

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
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
    kinopoisk_url = data.get("url")
    if kinopoisk_url:
        buttons.append([InlineKeyboardButton(text="🔗 Кинопоиск", url=kinopoisk_url)])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    return InlineQueryResultArticle(
        id=f"{typename}:{content_id}",
        title=title,
        description=description,
        thumbnail_url=_poster_url(data),
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
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

    # Top match: full info + watch URL
    top = await _fetch_full_info(unique[0])

    # Alternatives: fetch info in parallel, no lordfilm enrichment
    rest = unique[1:MAX_RESULTS]
    if rest:
        rest_infos = await asyncio.gather(
            *(get_info(it["typename"], it["id"]) for it in rest),
            return_exceptions=True,
        )
    else:
        rest_infos = []

    # Build article list
    articles = []
    top_article = _build_article(top)
    if top_article:
        articles.append(top_article)

    for item, info in zip(rest, rest_infos):
        if isinstance(info, Exception) or not info:
            continue
        merged = {**item, **info}
        article = _build_article(merged)
        if article:
            articles.append(article)

    await inline_query.answer(articles, cache_time=30)
