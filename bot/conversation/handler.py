import random

from bot.conversation._responses import WHAT_YOU_WANNA_SEARCH_RESPONSES
from bot.conversation._responses import WHAT_YOU_WANNA_ADD_RESPONSES
from bot.conversation._responses import CONTENT_NOT_FOUND_RESPONSES
from bot.conversation._responses import POSITIVE_REQUESTS, ALREADY_IN_LIST_RESPONSES
from bot.conversation._responses import VIEWED_RESPONSES, NOT_FOUND_RESPONSES
from bot.conversation._responses import RECOMMENDATION_RESPONSES
from bot.conversation._responses import WHAT_YOU_WANNA_DELETE_RESPONSES

# = = = = = = = = = = ANSWER CHECKER = = = = = = = = = =


def is_it_yes(text: str):
    if text in POSITIVE_REQUESTS:
        return True
    return False


# = = = = = = = = = = = = /add = = = = = = = = = = = = =


def get_random_what_you_wanna_search():
    return random.choice(WHAT_YOU_WANNA_SEARCH_RESPONSES)


def get_random_what_you_wanna_add():
    return random.choice(WHAT_YOU_WANNA_ADD_RESPONSES)


# Контент для добавления не найден.
def get_random_content_not_found():
    return random.choice(CONTENT_NOT_FOUND_RESPONSES)


# Контент уже в вашем списке
def get_random_already_in_list_response():
    return random.choice(ALREADY_IN_LIST_RESPONSES)


# = = = = = = = = = = = /delete = = = = = = = = = = = = =


def get_random_what_you_wanna_delete():
    return random.choice(WHAT_YOU_WANNA_DELETE_RESPONSES)


# = = = = = = = = = = = = /viewed = = = = = = = = = = = =


# Запрос на название того, что посмотрели
def get_random_whats_viewed_response():
    return random.choice(VIEWED_RESPONSES)


# Посмотренный фильм не найден в списке
def get_random_not_found_in_list_response():
    return random.choice(NOT_FOUND_RESPONSES)


# Призыв к рекомендации
def get_random_recommendation_response():
    return random.choice(RECOMMENDATION_RESPONSES)
