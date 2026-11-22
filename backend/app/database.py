
import os

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./users.db"

# Use psycopg 3 for PostgreSQL connections.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
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


def create_tables():
    # Register all models before creating tables.
    from app.models.user import User
    from app.models.current_affair import CurrentAffair
    from app.models.mcq import MCQ
    from app.models.news_payment import NewsDailyPayment
    from app.models.writing_subscription import WritingSubscription

    Base.metadata.create_all(bind=engine)


def add_official_source_url_column():
    """
    Safely add official source cache columns.
    Existing records are preserved.
    """

    inspector = inspect(engine)

    if not inspector.has_table("current_affairs"):
        print(
            "current_affairs table does not exist. "
            "Migration skipped."
        )
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("current_affairs")
    }

    additions = {
        "official_source_url": "VARCHAR(1000)",
        "official_source_checked_at": "TIMESTAMP",
        "official_social_source_url": "VARCHAR(1000)",
    }

    with engine.begin() as connection:
        for column_name, column_type in additions.items():
            if column_name not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE current_affairs "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )
                print(f"{column_name} column added successfully.")
            else:
                print(f"{column_name} column already exists.")
