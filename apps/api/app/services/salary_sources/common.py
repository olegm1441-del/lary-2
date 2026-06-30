from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from html import unescape
from urllib.parse import quote_plus


USER_AGENT = "LARI/0.1 (legacyinfo@yandex.ru)"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def strip_html(value: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", value or "", flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_text(unescape(text))


def parse_salary_number(value: str) -> int | None:
    match = re.search(r"\d[\d\s]{2,}", str(value or ""))
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))
    return int(digits) if digits else None


def int_median(values: list[int]) -> int | None:
    if not values:
        return None
    return int(round(statistics.median(values)))


def int_mean(values: list[int]) -> int | None:
    if not values:
        return None
    return int(round(statistics.mean(values)))


def slugify_ru(value: str) -> str:
    mapping = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
    lowered = normalize_text(value).lower()
    translit = "".join(mapping.get(char, char) for char in lowered)
    translit = re.sub(r"[^a-z0-9]+", "-", translit).strip("-")
    return translit


def human_search_url(base: str, **params: str | int | None) -> str:
    query = "&".join(f"{key}={quote_plus(str(value))}" for key, value in params.items() if value is not None)
    return f"{base}?{query}" if query else base


@dataclass(frozen=True)
class VacancySalaryStats:
    sample_size: int
    median: int | None
    mean: int | None
    values: list[int]

