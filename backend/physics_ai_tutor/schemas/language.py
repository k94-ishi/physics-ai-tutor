from enum import StrEnum


class Language(StrEnum):
    JA = "ja"
    EN = "en"


class TextProvenance(StrEnum):
    # Text as originally asked, written, or generated.
    ORIGINAL = "ORIGINAL"
    # Translated by a person.
    HUMAN = "HUMAN"
    # Translated by the configured Translator.
    MACHINE = "MACHINE"


LANGUAGES: tuple[Language, ...] = (Language.JA, Language.EN)
