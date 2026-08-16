import logging

from sqlalchemy.orm import Session

from physics_ai_tutor.core.config import settings
from physics_ai_tutor.core.exceptions import ConceptExtractionError
from physics_ai_tutor.models import Concept
from physics_ai_tutor.repositories import (
    concept_repository,
    question_concept_repository,
)
from physics_ai_tutor.services import deepseek_service, embedding_service

logger = logging.getLogger(__name__)

CONCEPT_EXTRACTION_PROMPT_VERSION = "v1"

_SYSTEM_PROMPT = (
    "あなたは物理教育の専門家です。"
    "あなたの出力は自動処理されるため、"
    "指定フォーマット(概念名を1行に1つずつ）以外は一切出力しないでください。"
)

_USER_PROMPT_TEMPLATE = """---例---

質問:
加速度って何?


回答:
加速度は単位時間あたりの速度の変化量です。
速度と同じくベクトル量で、単位は $m/s^2$ です。

速度-時間グラフの接線の傾きを考えると、加速度になります。

Output:
加速度
単位時間
速度
変化量
ベクトル
単位
$m/s^2$
v-tグラフ
接線の傾き
微分
---例 ここまで---
上記例のように、以下の物理に関する質問および回答から、物理概念を抜き出してください。
概念名を1行に1つずつ、改行区切りで出力してください。それ以外は一切出力しないこと。

質問:
{question}


回答:
{answer}

Output:
"""


def extract_concept_names(question: str, answer: str) -> list[str]:
    user_prompt = _USER_PROMPT_TEMPLATE.format(question=question, answer=answer)

    content = deepseek_service.chat_completion(_SYSTEM_PROMPT, user_prompt)

    concept_names = [line.strip() for line in content.splitlines() if line.strip()]

    if not concept_names:
        logger.warning(
            "Concept extraction returned no concepts: content=%r", content[:500]
        )
        raise ConceptExtractionError(
            "DeepSeek returned no concepts for concept extraction."
        )

    logger.info("Concepts extracted: count=%d", len(concept_names))

    return concept_names


def attach_concepts_to_question(
    db: Session,
    question_id: int,
    concept_names: list[str],
) -> list[Concept]:
    concepts = []

    for name in dict.fromkeys(concept_names):
        concept = concept_repository.get_by_name(db, name)

        if concept is None:
            embedding = embedding_service.create_embeddings([name])[0]
            concept = concept_repository.create(
                db,
                name=name,
                embedding=embedding,
                extraction_model=settings.deepseek_chat_model,
                embedding_model=settings.embedding_model,
                extraction_prompt_version=CONCEPT_EXTRACTION_PROMPT_VERSION,
            )

        question_concept_repository.link(
            db, question_id=question_id, concept_id=concept.id
        )
        concepts.append(concept)

    return concepts
