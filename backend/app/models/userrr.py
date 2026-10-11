
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    func,
)

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    username = Column(
        String,
        nullable=False,
    )

    email = Column(
        String,
        nullable=False,
        index=True,
    )

    password = Column(
        String,
        nullable=False,
    )

    hashed_password = Column(
        String,
        nullable=False,
    )

    role = Column(
        String,
        nullable=False,
        default="user",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    is_developer = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_admin = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    developer_active = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    developer_plan = Column(
        String,
        nullable=False,
        default="free",
    )

    payment_status = Column(
        String,
        nullable=False,
        default="unpaid",
    )

    activated_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Python attribute name = name
    # Existing database column name = full_name
    name = Column(
        "full_name",
        String,
        nullable=True,
    )

    developer_type = Column(
        String,
        nullable=False,
        default="individual",
    )

    country = Column(
        String,
        nullable=True,
    )

    phone = Column(
        String,
        nullable=True,
    )

    address = Column(
        Text,
        nullable=True,
    )

    company_name = Column(
        String,
        nullable=True,
    )

    bio = Column(
        Text,
        nullable=True,
    )

    website = Column(
        String,
        nullable=True,
    )

    github = Column(
        String,
        nullable=True,
    )
