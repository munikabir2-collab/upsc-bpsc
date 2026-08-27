from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    },
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

def create_tables():
    # Import models before create_all()
    from app.models.current_affair import CurrentAffair
    from app.models.mcq import MCQ

    Base.metadata.create_all(
        bind=engine
    )

    