import aiohttp
from aiohttp import ClientSession

from hubble.utils import (
    SEARCH_URL,
    INFO_URL,
    SIMILARS_URL,
    PERSON_URL,
    TRIVIAS_URL,
    MEDIA_POSTS_URL,
    SERIES_DATES_URL,
    LORDFILM_SEARCH_URL,
)


async def fetch_json(session: ClientSession, url: str, params: dict) -> dict:
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            return {}
        return await resp.json(content_type=None)


async def get_search(search_query: str) -> dict:
    async with aiohttp.ClientSession() as session:
        return await fetch_json(session, SEARCH_URL, {"search_query": search_query})


async def get_info(content_type: str, id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        return await fetch_json(
            session, INFO_URL, {"content_type": content_type, "id": id}
        )


async def get_similars(content_type: str, id: int) -> list:
    async with aiohttp.ClientSession() as session:
        return await fetch_json(
            session, SIMILARS_URL, {"content_type": content_type, "id": id}
        )


async def get_person(id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        return await fetch_json(session, PERSON_URL, {"id": id})


async def get_trivias(content_type: str, id: int) -> list:
    async with aiohttp.ClientSession() as session:
        return await fetch_json(
            session, TRIVIAS_URL, {"content_type": content_type, "id": id}
        )


async def get_media_posts(content_type: str, id: int) -> list:
    async with aiohttp.ClientSession() as session:
        return await fetch_json(
            session, MEDIA_POSTS_URL, {"content_type": content_type, "id": id}
        )


async def get_series_dates(title: str) -> dict:
    async with aiohttp.ClientSession() as session:
        return await fetch_json(session, SERIES_DATES_URL, {"title": title})


async def get_lordfilm_search(search_query: str) -> dict:
    async with aiohttp.ClientSession() as session:
        return await fetch_json(session, LORDFILM_SEARCH_URL, {"search_query": search_query})


async def enrich_with_watch_url(content_data: dict) -> dict:
    """
    Дополняет content_data полем watch_url из LordFilm.
    Если не находит — возвращает данные без изменений.
    Работает только для film/tvseries.
    """
    if content_data.get("typename") not in ("film", "tvseries"):
        return content_data
    title = content_data.get("title_russian") or content_data.get("title_original", "")
    if not title:
        return content_data
    lf_result = await get_lordfilm_search(title)
    watch_url = (lf_result or {}).get("best", {}).get("watch_url")
    if watch_url:
        content_data["watch_url"] = watch_url
    return content_data
