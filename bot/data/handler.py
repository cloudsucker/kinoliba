import os
import json

# = = = = = = = = = = = = = = = = = = FILEPATHS = = = = = = = = = = = = = = = = = =

DATA_PATH = "bot/data/"
USER_DATA_PATH = DATA_PATH + "users/"
TOKEN_FILEPATH = DATA_PATH + "token.txt"
CURRENT_USER_DATA_FILEPATH_TEMPLATE = USER_DATA_PATH + "{}.json"


# = = = = = = = = = = = = = = = = BOT_TOKEN GETTER = = = = = = = = = = = = = = = = =


def get_token():
    with open(TOKEN_FILEPATH, "r") as file:
        return file.read().strip()


# = = = = = = = = = = = = = = = USER_DATA MANAGE = = = = = = = = = = = = = = = =


def _get_user_file_path(conversation_id: int) -> str:
    return CURRENT_USER_DATA_FILEPATH_TEMPLATE.format(conversation_id)


def _get_user_data(conversation_id: int) -> dict[str:list]:
    file_path = _get_user_file_path(conversation_id)

    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump({}, file, ensure_ascii=False, indent=4)
        return {}

    with open(file_path, "r", encoding="utf-8") as file:
        try:
            return json.load(file)

        except json.JSONDecodeError:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump({}, file, ensure_ascii=False, indent=4)
            return {}


def _save_user_file(conversation_id: int, data: dict):
    file_path = _get_user_file_path(conversation_id)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# = = = = = = = = = = = = = = = = = USERLIB MANAGE = = = = = = = = = = = = = = = = = = = = = =


def is_content_in_user_lib(
    conversation_id: int, content_type: str, content_id: int
) -> bool:
    content_id = str(content_id)
    data = _get_user_data(conversation_id)
    content_data: dict = data.get(content_type, {})
    content_data: dict = content_data.get(content_id, {})

    if content_data:
        return True
    return False


def get_user_lib(conversation_id: int, content_type: str = None) -> dict:
    user_data = _get_user_data(conversation_id)

    if content_type:
        current_content_type_user_data = user_data.get(content_type, {})
        return current_content_type_user_data

    return user_data


def save_content_to_user_lib(conversation_id: int, content_data: dict) -> bool:
    content_id = content_data.get("id")
    content_type = content_data.get("typename")

    if is_content_in_user_lib(conversation_id, content_type, content_id):
        return False

    user_data = _get_user_data(conversation_id)
    current_content_type_user_data = user_data.get(content_type, {})

    if content_id not in current_content_type_user_data:
        current_content_type_user_data[content_id] = content_data
        user_data[content_type] = current_content_type_user_data
        _save_user_file(conversation_id, user_data)
        return True

    return False


def update_content_in_user_lib(conversation_id: int, content_data: dict) -> bool:
    content_id = str(content_data.get("id"))
    content_type = content_data.get("typename")

    if not is_content_in_user_lib(conversation_id, content_type, content_id):
        # TODO: добавить обработку с сообщением
        print(f"content not in lib. id: {content_id}, type: {content_type}")

    user_data = _get_user_data(conversation_id)
    current_content_type_user_data = user_data.get(content_type, {})

    current_content_type_user_data[content_id] = content_data
    user_data[content_type] = current_content_type_user_data

    _save_user_file(conversation_id, user_data)

    return True


def delete_content_from_user_lib(
    conversation_id: int, content_type: str, content_id: int
) -> bool:
    content_id = str(content_id)
    if not is_content_in_user_lib(conversation_id, content_type, content_id):
        return False

    user_data = _get_user_data(conversation_id)
    current_content_type_user_data = user_data.get(content_type, {})

    if content_id in current_content_type_user_data:
        del current_content_type_user_data[content_id]
        user_data[content_type] = current_content_type_user_data
        _save_user_file(conversation_id, user_data)
        return True

    return False


# = = = = = = = = = = = = = = = = VIEWED = = = = = = = = = = = = = = =


def mark_as_viewed(
    conversation_id: int, content_type: str, content_id: int, recommend: bool = False
) -> bool:
    content_id = str(content_id)
    if not is_content_in_user_lib(conversation_id, content_type, content_id):
        return False

    user_data = _get_user_data(conversation_id)
    current_content_type_user_data = user_data.get(content_type, {})

    current_content_type_user_data[content_id]["viewed"] = True
    if recommend:
        current_content_type_user_data[content_id]["recommend"] = True
    elif not recommend:
        current_content_type_user_data[content_id]["recommend"] = False

    for content_data in current_content_type_user_data.values():
        if not update_content_in_user_lib(conversation_id, content_data):
            return False
    return True


# = = = = = = = = = = = = = = = = RECOMMENDS = = = = = = = = = = = = = = =


def get_users_recommends(conversation_id: int) -> dict[str:list]:
    user_data = _get_user_data(conversation_id)
    recommends = {"film": [], "tvseries": []}

    # get all subdicts where is key 'recommend' == True:
    user_films: dict = user_data.get("film", {})
    user_tvseries: dict = user_data.get("tvseries", {})

    for film in user_films.values():
        if film.get("recommend"):
            recommends["film"].append(film)

    for tvseries in user_tvseries.values():
        if tvseries.get("recommend"):
            recommends["tvseries"].append(tvseries)

    if not recommends["film"] and not recommends["tvseries"]:
        return None
    return recommends


def is_this_content_already_recommend(
    conversation_id: int, content_type: str, content_id: int
) -> bool:
    user_recommends = get_users_recommends(conversation_id).get(content_type, [])
    if user_recommends:
        return content_id in get_users_recommends(conversation_id).get(content_type)
    return False


def mark_as_recommend(
    conversation_id: int,
    content_type: str,
    content_id: int,
    recommend: bool,
    user_review: str = "",
) -> bool:
    """
    Если контент отмечен как непросмотренный - меняет его статус.
    Перед вызовом проверить не отмечен ли контент как рекомендованный
    Если контент уже рекомендован - возвращает False.
    """

    if not is_content_in_user_lib(conversation_id, content_type, content_id):
        return False

    if is_this_content_already_recommend(conversation_id, content_type, content_id):
        return False

    user_data = _get_user_data(conversation_id)
    current_content_type_user_data = user_data.get(content_type, {})
    current_content_type_user_data[content_id]["viewed"] = True

    if recommend:
        current_content_type_user_data[content_id]["recommend"] = True
    elif not recommend:
        current_content_type_user_data[content_id]["recommend"] = False

    if user_review:
        current_content_type_user_data[content_id]["user_review"] = user_review

    return True


# = = = = = = = = = = = = = = = = RECOMMENDATIONS = = = = = = = = = = = = = = = =


def import_recomendations(conversation_id: int, new_content: list) -> bool:
    if not new_content or not all(isinstance(content, dict) for content in new_content):
        return False
    for content in new_content:
        save_content_to_user_lib(conversation_id, content)
    return True
