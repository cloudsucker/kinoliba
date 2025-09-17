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
)


async def fetch_json(session: ClientSession, url: str, params: dict) -> dict:
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            return {}
        return await resp.json()


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
