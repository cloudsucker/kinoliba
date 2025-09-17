import re


def is_search_query_valid(query: str) -> bool:
    if not query or len(query) > 100:
        return False
    return True


def seconds_to_hours_and_minutes(seconds: int) -> str:
    if not seconds:
        return ""

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours} ч {minutes} мин"
    else:
        return f"{minutes} мин"


def format_duration(minutes: int) -> str:
    if not minutes:
        return ""

    hours = minutes // 60
    minutes = minutes % 60

    if hours > 0:
        return f"{hours} ч {minutes} мин"
    else:
        return f"{minutes} мин"


def truncate_after_word(text: str, max_words: int) -> str:
    if not text:
        return ""

    words = re.split(r"(\s+)", text)
    word_count = 0
    truncated_text = []

    for part in words:
        if part.strip():
            word_count += 1
        if word_count > max_words:
            break
        truncated_text.append(part)

    if word_count > max_words:
        truncated_text.append("...")

    return "".join(truncated_text)


def format_rating(rating: str) -> float:
    try:
        return f"{float(rating):.1f}"
    except (ValueError, TypeError):
        return ""
