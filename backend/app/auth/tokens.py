from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.auth import utils as auth_utils
from app.core.config import settings
from app.models.user import User


def create_access_token(user: User) -> str:

    payload = {
        "sub": str(user.id),
        "type": "access",
        "username": user.username,
        "email": user.email,
    }

    return auth_utils.encode_jwt(payload)


def create_refresh_token(
    user: User,
) -> tuple[str, str, datetime]:

    jti = str(uuid4())

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.auth_jwt.refresh_token_expire_days
    )

    payload = {"sub": str(user.id), "type": "refresh", "jti": jti}

    token = auth_utils.encode_jwt(
        payload,
        expire_timedelta=timedelta(days=settings.auth_jwt.refresh_token_expire_days),
    )

    return token, jti, expires_at
