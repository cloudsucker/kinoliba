CONTENT_TYPE_ATTRIBUTES = {"film": "production_year", "tvseries": "release_start"}


def get_content_type_attributes(content_type: str):
    return CONTENT_TYPE_ATTRIBUTES.get(content_type)
