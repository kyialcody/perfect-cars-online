"""Auth API: optional registration (gmail blocked), login and JWT tokens."""
from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.ratelimit import hit
from app.core.security import (
    ACCESS,
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    dummy_verify,
    hash_password,
    verify_password,
)
from app.db.deps import get_session
from app.models.user import User
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, TokenPair, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
_bearer = HTTPBearer(auto_error=True)

# Email domains blocked from registration (legal constraint). googlemail.com is
# a gmail alias, so it's blocked too.
_BLOCKED_DOMAINS = {"gmail.com", "googlemail.com"}
_GMAIL_MESSAGE = (
    "По законодательству РФ мы не можем зарегистрировать пользователя с gmail почтой"
)


def _client_ip(request: Request) -> str:
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _email_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    ip = _client_ip(request)
    if not await hit(
        f"register:rl:{ip}", settings.register_rate_limit, settings.register_rate_window
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток регистрации, попробуйте позже",
        )

    if _email_domain(payload.email) in _BLOCKED_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
            detail={"code": "GMAIL_FORBIDDEN", "message": _GMAIL_MESSAGE},
        )

    email = payload.email.lower()
    exists = (
        await session.execute(select(User.id).where(func.lower(User.email) == email))
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким e-mail уже существует",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        # Lost a race with a concurrent registration of the same email.
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким e-mail уже существует",
        ) from None
    await session.refresh(user)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    ip = _client_ip(request)
    if not await hit(
        f"login:rl:{ip}", settings.login_rate_limit, settings.login_rate_window
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа, попробуйте позже",
        )

    email = payload.email.lower()
    user = (
        await session.execute(select(User).where(func.lower(User.email) == email))
    ).scalar_one_or_none()
    # Same response — and same timing — for unknown user and wrong password
    # (no account enumeration). For an unknown user we still run a dummy verify.
    if user is None:
        dummy_verify(payload.password)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный e-mail или пароль",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт отключён")

    sub = str(user.id)
    return TokenPair(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshIn) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, expected_type=REFRESH)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh-токен",
        ) from None
    sub = str(claims["sub"])
    return TokenPair(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
    )


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        claims = decode_token(creds.credentials, expected_type=ACCESS)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        ) from None
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден"
        )
    return user


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current)
