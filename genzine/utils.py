import re
import string


def to_camelcase(text: str) -> str:
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(" ", "_", text).lower()
    return text


def h1(text: str) -> str:
    return "# " + text


def h2(text: str) -> str:
    return "## " + text
