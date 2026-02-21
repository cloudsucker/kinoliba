from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

IKB = InlineKeyboardButton

FILTER_LABELS = {
    "all":    "Все",
    "film":   "🎞 Фильмы",
    "tv":     "📺 Сериалы",
    "unseen": "❌ Не смотрел",
    "seen":   "✅ Смотрел",
    "rec":    "🔥 Советую",
}


def build_library_keyboard(
    lib_item: dict,
    idx: int,
    total: int,
    current_filter: str = "all",
) -> InlineKeyboardMarkup:
    """
    Builds inline keyboard for the library carousel.
    All needed data (typename, id, viewed, recommend, watch_url) is in lib_item.
    """
    content_type = lib_item.get("typename")
    content_id = str(lib_item.get("id"))
    viewed = lib_item.get("viewed", False)
    recommend = lib_item.get("recommend")  # None / True / False
    watch_url = lib_item.get("watch_url")

    f = current_filter  # short alias for callback encoding
    buttons = []

    # Action row(s) based on watch status
    if not viewed:
        buttons.append([
            IKB(text="✅ Просмотрено", callback_data=f"lv:{content_type}:{content_id}:{f}:{idx}"),
            IKB(text="🗑 Удалить",     callback_data=f"ld:{content_type}:{content_id}:{f}:{idx}"),
        ])
    elif recommend is None:
        buttons.append([
            IKB(text="👍 Советую",    callback_data=f"lr1:{content_type}:{content_id}:{f}:{idx}"),
            IKB(text="👎 Не советую", callback_data=f"lr0:{content_type}:{content_id}:{f}:{idx}"),
        ])
        buttons.append([
            IKB(text="🗑 Удалить", callback_data=f"ld:{content_type}:{content_id}:{f}:{idx}"),
        ])
    elif recommend:
        buttons.append([
            IKB(text="👍 Советую ✓",  callback_data=f"lr1:{content_type}:{content_id}:{f}:{idx}"),
            IKB(text="👎 Не советую", callback_data=f"lr0:{content_type}:{content_id}:{f}:{idx}"),
        ])
        buttons.append([
            IKB(text="🗑 Удалить", callback_data=f"ld:{content_type}:{content_id}:{f}:{idx}"),
        ])
    else:
        buttons.append([
            IKB(text="👍 Советую",      callback_data=f"lr1:{content_type}:{content_id}:{f}:{idx}"),
            IKB(text="👎 Не советую ✓", callback_data=f"lr0:{content_type}:{content_id}:{f}:{idx}"),
        ])
        buttons.append([
            IKB(text="🗑 Удалить", callback_data=f"ld:{content_type}:{content_id}:{f}:{idx}"),
        ])

    # Watch button
    if watch_url:
        buttons.append([IKB(text="▶️ Смотреть", url=watch_url)])

    # Navigation row
    nav = []
    if idx > 0:
        nav.append(IKB(text="◀", callback_data=f"lib:p:{f}:{idx}"))
    nav.append(IKB(text=f"{idx + 1} / {total}", callback_data="noop"))
    if idx < total - 1:
        nav.append(IKB(text="▶", callback_data=f"lib:n:{f}:{idx}"))
    buttons.append(nav)

    # Filter rows
    def _filter_btn(key: str) -> IKB:
        label = FILTER_LABELS[key]
        if key == current_filter:
            label = f"• {label}"
        return IKB(text=label, callback_data=f"lib:f:{key}:0")

    buttons.append([_filter_btn("all"), _filter_btn("film"), _filter_btn("tv")])
    buttons.append([_filter_btn("unseen"), _filter_btn("seen"), _filter_btn("rec")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
