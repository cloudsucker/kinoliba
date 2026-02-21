import os
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY") or None
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_HEADERS = {
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/cloudsucker/kinoliba",
}

_PROMPT_FIND = (
    "Ты — помощник по поиску фильмов и сериалов. "
    "По описанию или частичной информации определи конкретный фильм или сериал. "
    "Верни ТОЛЬКО его русское название (как на Кинопоиске). "
    "Если не можешь определить — ответь ровно: NOT_FOUND"
)

_PROMPT_SUGGEST_MOOD = (
    "Ты — эксперт по фильмам и сериалам. "
    "По описанию настроения, жанра или пожелания предложи ОДИН подходящий "
    "фильм или сериал с высоким рейтингом. "
    "Верни ТОЛЬКО русское название (как на Кинопоиске), без пояснений, года и знаков препинания."
)

_PROMPT_SUGGEST_RANDOM = (
    "Ты — эксперт по фильмам и сериалам. "
    "Предложи ОДИН интересный фильм или сериал с хорошим рейтингом, который не все смотрели. "
    "Предлагай разное каждый раз. Верни ТОЛЬКО русское название (как на Кинопоиске), больше ничего."
)


def is_available() -> bool:
    """Returns True if OpenRouter key is configured."""
    return bool(OPENROUTER_API_KEY)


async def _call(system_prompt: str, user_message: str) -> Optional[str]:
    """Makes a single OpenRouter API call. Returns stripped text or None on failure."""
    if not OPENROUTER_API_KEY:
        return None

    payload = {
        "model": OPENROUTER_MODEL,
        "max_tokens": 60,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    headers = {**_HEADERS, "Authorization": f"Bearer {OPENROUTER_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"OpenRouter {resp.status}: {await resp.text()}")
                    return None
                data = await resp.json()
                text = data["choices"][0]["message"]["content"].strip()
                return text.strip('«»"\'"')
    except Exception as e:
        logger.warning(f"OpenRouter call failed: {e}")
        return None


async def get_name_by_description(prompt: str) -> Optional[str]:
    """
    Identifies a specific movie/series by description.
    Used as search fallback when Kinopoisk finds nothing.
    """
    result = await _call(_PROMPT_FIND, prompt)
    if not result or "NOT_FOUND" in result.upper():
        logger.info(f"AI could not identify: {prompt!r}")
        return None
    logger.info(f"AI identified {result!r} from {prompt!r}")
    return result


async def suggest_by_mood(mood: str) -> Optional[str]:
    """
    Suggests a title based on mood/genre description.
    Used in 'Что посмотреть?' -> 'По настроению' flow.
    """
    result = await _call(_PROMPT_SUGGEST_MOOD, mood)
    if not result or "NOT_FOUND" in result.upper():
        return None
    logger.info(f"AI mood suggestion for {mood!r}: {result!r}")
    return result


async def suggest_random() -> Optional[str]:
    """
    Suggests a random acclaimed title.
    Used in 'Что посмотреть?' -> 'Удивить меня' flow.
    """
    result = await _call(_PROMPT_SUGGEST_RANDOM, "Предложи что-нибудь интересное")
    if not result or "NOT_FOUND" in result.upper():
        return None
    logger.info(f"AI random suggestion: {result!r}")
    return result
