"""Common type definitions used in ESI Link."""

from enum import StrEnum
from typing import Literal, TypedDict

type LangType = Literal["en", "de", "fr", "ja", "ru", "zh", "ko", "es"]
"""A type representing the supported languages for localization."""


class LangEnum(StrEnum):
    """An enum representing the supported languages for localization."""

    EN = "en"
    DE = "de"
    FR = "fr"
    JA = "ja"
    RU = "ru"
    ZH = "zh"
    KO = "ko"
    ES = "es"


class LocalizedString(TypedDict):
    """The shape of a localized string.

    The languages are defined in the SDE file: translationLanguages.jsonl
    """

    en: str
    de: str
    fr: str
    ja: str
    zh: str
    ru: str
    ko: str
    es: str
