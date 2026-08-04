from physics_ai_tutor.database.database import engine
from physics_ai_tutor.database.base import Base

from physics_ai_tutor.models.question import Question


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()