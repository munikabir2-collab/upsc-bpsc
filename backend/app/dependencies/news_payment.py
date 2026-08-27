from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

from app.services.news_payment_service import (
    require_news_access,
)

from app.dependencies.auth import get_current_user


def require_news_daily_access(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = current_user.id

    require_news_access(
        db=db,
        user_id=user_id,
    )

    return current_user