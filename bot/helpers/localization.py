LOCALE_EN_RU = {"film": "Фильм", "tvseries": "Сериал", "—": "Неопознанный контент!"}


def get_locale_en_ru(text: str) -> str:
    return LOCALE_EN_RU[text]
