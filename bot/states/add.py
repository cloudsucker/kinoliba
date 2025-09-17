from aiogram.fsm.state import StatesGroup, State


class AddMovieState(StatesGroup):
    waiting_for_query = State()
    waiting_for_confirmation = State()
