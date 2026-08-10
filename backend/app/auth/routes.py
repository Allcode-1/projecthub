from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.dependencies import get_current_active_user, require_admin
from app.auth.schemas import RefreshToken, TokenPair, UserCreate, UserRead
from app.core.config import settings
from app.db.session import get_db
from app.dependencies.pagination import Pagination, get_pagination
from app.dependencies.rate_limiter import (
    get_rate_limiter,
    rate_limit_auth_logout,
    rate_limit_auth_refresh,
    rate_limit_auth_register,
)
from app.jobs.email import send_email
from app.models.user import User
from app.security.rate_limiter import RateLimiter

router = APIRouter(prefix="/auth", tags=["jwt-based auth"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
PaginationDep = Annotated[Pagination, Depends(get_pagination)]


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth_register)],
)
def register_user(payload: UserCreate, db: DbSession):

    user = auth_service.register_user(payload, db)
    send_email.delay(
        user.email, "Welcome!", "welcome.html", {"username": user.username}
    )
    return user


@router.post("/login", response_model=TokenPair)
def login_user(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: DbSession,
    rate_limiter: RateLimiterDep,
):

    client_ip = request.client.host if request.client else "unknown"

    rate_limiter.check(
        key=f"rate:auth:login:ip:{client_ip}",
        limit=settings.rate_limit.login_ip_limit,
        window_seconds=settings.rate_limit.login_ip_window_seconds,
    )

    username_key = username.casefold()
    rate_limiter.check(
        key=f"rate:auth:login:username:{username_key}",
        limit=settings.rate_limit.login_username_limit,
        window_seconds=settings.rate_limit.login_username_window_seconds,
    )

    return auth_service.login_user(username, password, db)


@router.post("/logout", dependencies=[Depends(rate_limit_auth_logout)])
def logout_user(payload: RefreshToken, db: DbSession):
    return auth_service.logout_user(payload.refresh_token, db)


@router.get("/users/me", response_model=UserRead)
def get_me(
    user: CurrentUser,
):

    return user


@router.get("/users", response_model=list[UserRead])
def get_all_users(user: AdminUser, db: DbSession, pagination: PaginationDep):

    users = db.scalars(
        select(User).order_by(User.id).limit(pagination.limit).offset(pagination.offset)
    ).all()

    return users


@router.post(
    "/refresh",
    response_model=TokenPair,
    dependencies=[Depends(rate_limit_auth_refresh)],
)
def refresh_tokens(payload: RefreshToken, db: DbSession):
    return auth_service.refresh_tokens(payload.refresh_token, db)
