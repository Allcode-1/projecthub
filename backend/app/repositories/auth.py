from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_session import RefreshSession
from app.models.user import User


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def user_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def user_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def list_users(self, limit: int, offset: int) -> list[User]:
        statement = select(User).order_by(User.id).limit(limit).offset(offset)
        return list(self.db.scalars(statement).all())

    def add_user(self, user: User) -> None:
        self.db.add(user)

    def add_refresh_session(self, refresh_session: RefreshSession) -> None:
        self.db.add(refresh_session)

    def revoke_active_refresh_session(self, jti: str, now: datetime) -> int | None:
        return self.db.scalar(
            update(RefreshSession)
            .where(
                RefreshSession.jti == jti,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.expires_at >= now,
            )
            .values(revoked_at=now)
            .returning(RefreshSession.user_id)
        )
