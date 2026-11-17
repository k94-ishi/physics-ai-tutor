"""Which language a response is in, and what it still needs translated ([62]).

Built once per request instead of passing `strict_language`,
`only_with_language` and `missing_language_ids` through every call.
"""

from dataclasses import dataclass, field

from physics_ai_tutor.models.question import Question
from physics_ai_tutor.schemas.language import Language


@dataclass(frozen=True)
class ResponseLanguage:
    """The response language and whether falling back is allowed.

    Students get `strict`: they never read the other language, so rows and
    concept names lacking `language` are left out ([53]). Admins see every
    row, with text falling back to the original language.
    """

    language: Language
    strict: bool = False

    @classmethod
    def for_caller(cls, language: Language | str, admin: bool) -> "ResponseLanguage":
        return cls(Language(language), strict=not admin)

    @classmethod
    def of(cls, language: "Language | str | ResponseLanguage") -> "ResponseLanguage":
        """A plain language means the admin fallback."""
        if isinstance(language, ResponseLanguage):
            return language
        return cls(Language(language))

    def readable(self, questions: list[Question]) -> tuple[list[Question], list[int]]:
        """Rows a strict reader can read, and the ids of those they cannot."""
        if not self.strict:
            return questions, []
        kept = [q for q in questions if q.has(self.language)]
        return kept, [q.id for q in questions if not q.has(self.language)]


@dataclass
class TranslationNeeds:
    """What a strict response left out, for one background translation each."""

    question_ids: list[int] = field(default_factory=list)
    # Questions whose concept names should be checked for a missing language.
    concept_question_ids: list[int] = field(default_factory=list)

    def merge(self, other: "TranslationNeeds") -> "TranslationNeeds":
        return TranslationNeeds(
            self.question_ids + other.question_ids,
            self.concept_question_ids + other.concept_question_ids,
        )
