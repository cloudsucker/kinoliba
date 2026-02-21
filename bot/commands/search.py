import logging
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from bot.states import SearchState
from bot.helpers import is_search_query_valid
from bot.keyboards import build_card_keyboard
from bot.helpers.send import send_new_card, edit_card_content
from bot.conversation import get_random_content_not_found
from bot.data import (
    get_user_lib,
    is_content_in_user_lib,
    save_content_to_user_lib,
    delete_content_from_user_lib,
    mark_viewed_only,
    set_recommend_status,
)
from hubble.getters import get_search, get_info, enrich_with_watch_url, get_similars
from ai import get_name_by_description

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_lib_item(user_id: int, content_type: str, content_id: str) -> dict | None:
    """Returns the user's library entry for this content, or None if not present."""
    lib = get_user_lib(user_id, content_type)
    return lib.get(str(content_id))


async def _fetch_full_info(item: dict) -> dict:
    """Fetches detailed info and enriches with watch_url. Returns merged dict."""
    if item.get("typename") == "person":
        return item
    info = await get_info(item["typename"], item["id"])
    merged = {**item, **info}
    merged = await enrich_with_watch_url(merged)
    return merged


def _build_results_list(first_item: dict, alternatives: list) -> list:
    """Returns a flat list of {id, typename} dicts: first item + alternatives."""
    results = [{"id": str(first_item.get("id")), "typename": first_item.get("typename")}]
    for m in alternatives:
        results.append({"id": str(m.get("id")), "typename": m.get("typename")})
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Search entry point — free text in any state
# ─────────────────────────────────────────────────────────────────────────────

@router.message(default_state, lambda msg: msg.text and not msg.text.startswith("/"))
@router.message(SearchState.browsing, lambda msg: msg.text and not msg.text.startswith("/"))
async def handle_search_query(message: types.Message, state: FSMContext):
    query = message.text.strip()
    if not is_search_query_valid(query):
        return

    try:
        search_data = await get_search(query)
    except Exception:
        logger.exception("Search API error for query: %s", query)
        await message.answer("Сервер поиска недоступен, попробуй позже.")
        return

    match = search_data.get("match")
    alternatives = search_data.get("movies", [])

    if not match:
        prediction = await get_name_by_description(query)
        if prediction:
            try:
                search_data = await get_search(prediction)
            except Exception:
                search_data = {}
            match = search_data.get("match")
            alternatives = search_data.get("movies", [])

    if not match:
        await message.answer(get_random_content_not_found())
        await state.clear()
        return

    content_data = await _fetch_full_info(match)
    results = _build_results_list(content_data, alternatives)

    lib_item = _get_lib_item(message.chat.id, content_data["typename"], str(content_data["id"]))
    watch_url = content_data.get("watch_url") or content_data.get("url")
    keyboard = build_card_keyboard(
        content_type=content_data["typename"],
        content_id=str(content_data["id"]),
        lib_item=lib_item,
        watch_url=watch_url,
        idx=0,
        total=len(results),
    )

    sent = await send_new_card(message.bot, message.chat.id, content_data, keyboard)

    await state.set_state(SearchState.browsing)
    await state.set_data({
        "results": results,
        "idx": 0,
        "message_id": sent.message_id,
        "watch_url": watch_url,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Carousel navigation
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.in_({"snext", "sprev"}))
async def handle_search_nav(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data:
        await callback.answer()
        return

    results = data.get("results", [])
    idx = data.get("idx", 0)
    new_idx = idx + (1 if callback.data == "snext" else -1)

    if not (0 <= new_idx < len(results)):
        await callback.answer()
        return

    content_data = await _fetch_full_info(results[new_idx])
    lib_item = _get_lib_item(callback.message.chat.id, content_data["typename"], str(content_data["id"]))
    watch_url = content_data.get("watch_url") or content_data.get("url")
    keyboard = build_card_keyboard(
        content_type=content_data["typename"],
        content_id=str(content_data["id"]),
        lib_item=lib_item,
        watch_url=watch_url,
        idx=new_idx,
        total=len(results),
    )

    await edit_card_content(callback.message, content_data, keyboard)
    await state.update_data(idx=new_idx, watch_url=watch_url)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def handle_noop(callback: types.CallbackQuery):
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Card action callbacks
# ─────────────────────────────────────────────────────────────────────────────

async def _refresh_card_keyboard(
    callback: types.CallbackQuery,
    state: FSMContext,
    content_type: str,
    content_id: str,
) -> None:
    """Re-builds and edits only the keyboard after any library action on a search card."""
    data = await state.get_data()
    results = data.get("results", [])
    idx = data.get("idx", 0)
    watch_url = data.get("watch_url")
    lib_item = _get_lib_item(callback.message.chat.id, content_type, content_id)
    keyboard = build_card_keyboard(
        content_type=content_type,
        content_id=content_id,
        lib_item=lib_item,
        watch_url=watch_url,
        idx=idx,
        total=len(results),
    )
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass


@router.callback_query(F.data.startswith("add:"))
async def handle_add(callback: types.CallbackQuery, state: FSMContext):
    _, content_type, content_id = callback.data.split(":")
    user_id = callback.message.chat.id

    if is_content_in_user_lib(user_id, content_type, content_id):
        await callback.answer("Уже в списке!")
        return

    content_data = await _fetch_full_info({"id": content_id, "typename": content_type})
    save_content_to_user_lib(user_id, content_data)
    await callback.answer("Добавлено в список!")
    await _refresh_card_keyboard(callback, state, content_type, content_id)


@router.callback_query(F.data.startswith("saw:"))
async def handle_saw(callback: types.CallbackQuery, state: FSMContext):
    """Add to library and immediately mark as viewed."""
    _, content_type, content_id = callback.data.split(":")
    user_id = callback.message.chat.id

    if not is_content_in_user_lib(user_id, content_type, content_id):
        content_data = await _fetch_full_info({"id": content_id, "typename": content_type})
        save_content_to_user_lib(user_id, content_data)

    mark_viewed_only(user_id, content_type, content_id)
    await callback.answer("Отмечено как просмотренное!")
    await _refresh_card_keyboard(callback, state, content_type, content_id)


@router.callback_query(F.data.startswith("viewed:"))
async def handle_viewed(callback: types.CallbackQuery, state: FSMContext):
    _, content_type, content_id = callback.data.split(":")
    mark_viewed_only(callback.message.chat.id, content_type, content_id)
    await callback.answer("Отмечено как просмотренное!")
    await _refresh_card_keyboard(callback, state, content_type, content_id)


@router.callback_query(F.data.startswith("del:"))
async def handle_del(callback: types.CallbackQuery, state: FSMContext):
    _, content_type, content_id = callback.data.split(":")
    delete_content_from_user_lib(callback.message.chat.id, content_type, content_id)
    await callback.answer("Удалено из списка!")
    await _refresh_card_keyboard(callback, state, content_type, content_id)


@router.callback_query(F.data.startswith("rec:"))
async def handle_rec(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    _, content_type, content_id, value = parts
    user_id = callback.message.chat.id
    recommend = value == "1"

    # No-op if already set to same value
    lib_item = _get_lib_item(user_id, content_type, content_id)
    if lib_item and lib_item.get("recommend") == recommend:
        await callback.answer()
        return

    set_recommend_status(user_id, content_type, content_id, recommend)
    await callback.answer("👍 Советую ✓" if recommend else "👎 Не советую ✓")
    await _refresh_card_keyboard(callback, state, content_type, content_id)


# ─────────────────────────────────────────────────────────────────────────────
# Similars
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("sim:"))
async def handle_similars(callback: types.CallbackQuery, state: FSMContext):
    _, content_type, content_id = callback.data.split(":")
    await callback.answer("Ищу похожее...")

    similars = await get_similars(content_type, content_id)
    if not similars:
        await callback.message.answer("Похожих не нашёл 😔")
        return

    results = [
        {"id": str(s.get("id")), "typename": s.get("typename")}
        for s in similars
        if s.get("typename") in ("film", "tvseries")
    ]
    if not results:
        await callback.message.answer("Похожих не нашёл 😔")
        return

    content_data = await _fetch_full_info(results[0])
    lib_item = _get_lib_item(callback.message.chat.id, content_data["typename"], str(content_data["id"]))
    watch_url = content_data.get("watch_url") or content_data.get("url")
    keyboard = build_card_keyboard(
        content_type=content_data["typename"],
        content_id=str(content_data["id"]),
        lib_item=lib_item,
        watch_url=watch_url,
        idx=0,
        total=len(results),
    )

    sent = await send_new_card(callback.message.bot, callback.message.chat.id, content_data, keyboard)

    await state.set_state(SearchState.browsing)
    await state.set_data({
        "results": results,
        "idx": 0,
        "message_id": sent.message_id,
        "watch_url": watch_url,
    })
