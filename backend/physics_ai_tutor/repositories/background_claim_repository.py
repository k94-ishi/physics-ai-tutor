"""Claiming background work so exactly one worker does it ([75])."""

from datetime import timedelta

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from physics_ai_tutor.models import BackgroundClaim

# Work kinds, so a typo cannot silently create a separate namespace.
TRANSLATE_QUESTION = "translate_question"
TRANSLATE_CONCEPT_NAME = "translate_concept_name"


def _claim_statement(kind: str, key: int, timeout_minutes: int):
    """Insert the claim, or take it over if the holder left it to rot.

    One statement, so the decision is the database's and not a read
    followed by a write that another worker can interleave with. The
    `DO UPDATE ... WHERE` only fires for an expired claim: a live one
    matches no row, returns nothing, and the caller knows it lost.
    """
    cutoff = func.now() - timedelta(minutes=timeout_minutes)

    return (
        insert(BackgroundClaim)
        .values(kind=kind, key=key, claimed_at=func.now())
        .on_conflict_do_update(
            constraint="uq_background_claims_work",
            set_={"claimed_at": func.now()},
            where=BackgroundClaim.claimed_at < cutoff,
        )
        .returning(BackgroundClaim.id)
    )


async def claim(db: AsyncSession, kind: str, key: int, timeout_minutes: int) -> bool:
    """True when this worker now owns the work; False when another does."""
    claimed = await db.scalar(_claim_statement(kind, key, timeout_minutes))

    return claimed is not None


async def release(db: AsyncSession, kind: str, key: int) -> None:
    """Give the work back, whether it succeeded or not."""
    await db.execute(
        sql_delete(BackgroundClaim).where(
            BackgroundClaim.kind == kind, BackgroundClaim.key == key
        )
    )


async def is_claimed(db: AsyncSession, kind: str, key: int) -> bool:
    """Whether a claim row exists; for tests and diagnostics."""
    found = await db.scalar(
        select(BackgroundClaim.id).where(
            BackgroundClaim.kind == kind, BackgroundClaim.key == key
        )
    )

    return found is not None
