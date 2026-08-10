from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from physics_ai_tutor.core.config import settings

engine = create_engine(
    settings.database_url,
    echo=(settings.environment == "development"),
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
