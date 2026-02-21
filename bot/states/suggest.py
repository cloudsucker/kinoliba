from aiogram.fsm.state import StatesGroup, State


class SuggestState(StatesGroup):
    waiting_for_mood = State()
