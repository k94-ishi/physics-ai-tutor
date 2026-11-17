from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class ConceptExtractionRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1, max_length=100)


class ConceptExtractionResult(BaseModel):
    question_id: int
    success: bool
    concepts: list[str] = Field(default_factory=list)


class ConceptExtractionBatchResponse(BaseModel):
    results: list[ConceptExtractionResult]


# --- senses and terms ([55]) -------------------------------------------------

TermLanguage = Literal["ja", "en"]
TermText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
GlossText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class ConceptSearchItem(BaseModel):
    """One sense in the student concept search."""

    id: int
    label: str
    gloss: str | None
    matched_term: str | None
    question_count: int


class ConceptTermResponse(BaseModel):
    id: int
    language: str
    term: str
    is_preferred: bool
    source: str

    model_config = {"from_attributes": True}


class ConceptQuestionRef(BaseModel):
    id: int
    question: str
    status: str


class AdminConceptResponse(BaseModel):
    id: int
    gloss_ja: str | None
    gloss_en: str | None
    terms: list[ConceptTermResponse]
    question_count: int
    # Ids of other senses sharing one of this sense's words.
    shares_word_with: list[int] = Field(default_factory=list)
    questions: list[ConceptQuestionRef] | None = None


class AdminConceptListResponse(BaseModel):
    items: list[AdminConceptResponse]
    total: int
    page: int
    size: int


class ConceptGlossUpdate(BaseModel):
    gloss_ja: GlossText | None = None
    gloss_en: GlossText | None = None


class ConceptTermCreate(BaseModel):
    language: TermLanguage
    term: TermText
    is_preferred: bool = False


class ConceptTermUpdate(BaseModel):
    term: TermText | None = None
    is_preferred: bool | None = None


class ConceptMergeRequest(BaseModel):
    into_id: int = Field(ge=1)


class ConceptSplitTerm(BaseModel):
    language: TermLanguage
    term: TermText


class ConceptSplitRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1, max_length=500)
    terms: list[ConceptSplitTerm] = Field(min_length=1, max_length=10)
    gloss_ja: GlossText | None = None
    gloss_en: GlossText | None = None
