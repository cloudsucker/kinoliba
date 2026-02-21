from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

IKB = InlineKeyboardButton


def build_card_keyboard(
    content_type: str,
    content_id: str,
    lib_item: Optional[dict],
    watch_url: Optional[str] = None,
    idx: int = 0,
    total: int = 1,
) -> InlineKeyboardMarkup:
    """
    Builds inline keyboard for a search result card.

    lib_item: None if content is not in user's library,
              dict with {viewed, recommend, ...} if it is.
    idx/total: for search results carousel navigation.
    """
    buttons = []

    if content_type in ("film", "tvseries"):
        if lib_item is None:
            # Not in library
            buttons.append([
                IKB(text="➕ В список", callback_data=f"add:{content_type}:{content_id}"),
                IKB(text="✅ Уже видел", callback_data=f"saw:{content_type}:{content_id}"),
            ])
        elif not lib_item.get("viewed", False):
            # In library, not yet viewed
            buttons.append([
                IKB(text="✅ Просмотрено", callback_data=f"viewed:{content_type}:{content_id}"),
                IKB(text="🗑 Удалить", callback_data=f"del:{content_type}:{content_id}"),
            ])
        else:
            recommend = lib_item.get("recommend")  # None / True / False
            if recommend is None:
                buttons.append([
                    IKB(text="👍 Советую", callback_data=f"rec:{content_type}:{content_id}:1"),
                    IKB(text="👎 Не советую", callback_data=f"rec:{content_type}:{content_id}:0"),
                ])
            elif recommend:
                buttons.append([
                    IKB(text="👍 Советую ✓", callback_data=f"rec:{content_type}:{content_id}:1"),
                    IKB(text="👎 Не советую", callback_data=f"rec:{content_type}:{content_id}:0"),
                ])
            else:
                buttons.append([
                    IKB(text="👍 Советую", callback_data=f"rec:{content_type}:{content_id}:1"),
                    IKB(text="👎 Не советую ✓", callback_data=f"rec:{content_type}:{content_id}:0"),
                ])
            buttons.append([
                IKB(text="🗑 Удалить", callback_data=f"del:{content_type}:{content_id}"),
            ])

    # Watch button
    if watch_url:
        buttons.append([IKB(text="▶️ Смотреть", url=watch_url)])

    # Similars button
    if content_type in ("film", "tvseries"):
        buttons.append([
            IKB(text="🎯 Похожие", callback_data=f"sim:{content_type}:{content_id}"),
        ])

    # Carousel navigation
    if total > 1:
        nav = []
        if idx > 0:
            nav.append(IKB(text="◀", callback_data="sprev"))
        nav.append(IKB(text=f"{idx + 1} / {total}", callback_data="noop"))
        if idx < total - 1:
            nav.append(IKB(text="▶", callback_data="snext"))
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)
