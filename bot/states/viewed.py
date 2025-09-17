from aiogram.fsm.state import StatesGroup, State


class MarkAsViewedState(StatesGroup):
    waiting_for_content_name = State()
    waiting_for_feedback = State()
