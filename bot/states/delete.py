from aiogram.fsm.state import StatesGroup, State


class DeleteMovieState(StatesGroup):
    waiting_for_query = State()
    waiting_for_confirmation = State()
