import logging

from physics_ai_tutor.core import prompts
from physics_ai_tutor.core.exceptions import TranslationError
from physics_ai_tutor.schemas.language import Language
from physics_ai_tutor.services import deepseek_service

logger = logging.getLogger(__name__)

QUESTION_MARKER = "=====QUESTION====="
ANSWER_MARKER = "=====ANSWER====="


def _parse(content: str) -> tuple[str, str]:
    # Split on the last pair of markers so stray echoes do not confuse us.
    if QUESTION_MARKER not in content or ANSWER_MARKER not in content:
        raise TranslationError("Translator output did not contain both markers.")

    _, after_question = content.rsplit(QUESTION_MARKER, 1)
    question, answer = after_question.split(ANSWER_MARKER, 1)

    question = question.strip()
    answer = answer.strip()

    if not question or not answer:
        raise TranslationError("Translator returned an empty question or answer.")

    return question, answer


def translate_qa(
    question: str,
    answer: str,
    source: Language,
    target: Language,
) -> tuple[str, str]:
    """Translate a question/answer pair. Raises TranslationError on failure.

    This is the single seam for swapping the translation backend.
    """
    user_prompt = prompts.TRANSLATE_USER_TEMPLATE.format(
        source=prompts.LANGUAGE_NAMES[source],
        target=prompts.LANGUAGE_NAMES[target],
        glossary=prompts.glossary_block(),
        question=question,
        answer=answer,
    )

    try:
        content = deepseek_service.chat_completion(
            prompts.TRANSLATE_SYSTEM_PROMPT, user_prompt
        )
    except Exception as exc:
        raise TranslationError("Translation request failed.") from exc

    translated = _parse(content)

    logger.info(
        "Translated QA: source=%s target=%s question_length=%d",
        source,
        target,
        len(translated[0]),
    )

    return translated
