from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.core.config import settings

engine = create_engine(
    settings.database_url,
    hide_parameters=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
