from aiogram.fsm.state import StatesGroup, State


class SearchState(StatesGroup):
    browsing = State()
    # state data: {
    #   "results": [{"id": "123", "typename": "film"}, ...],
    #   "idx": 0,
    #   "message_id": 123456,
    #   "watch_url": "https://..." or None,
    # }
