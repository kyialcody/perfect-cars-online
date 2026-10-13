"""SQLAdmin authentication backend.

Reuses the public auth stack (issue #10): the same ``user_account`` rows and
argon2 password hashes. Access is limited to users with ``is_admin`` set —
public registration never sets that flag, so admins are provisioned only
server-side (see ``ensure_admin_user`` in this package's ``__init__``).
"""
from __future__ import annotations

from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import func, select
from starlette.requests import Request

from app.core.security import dummy_verify, verify_password
from app.db.session import SessionLocal
from app.models.user import User

ADMIN_SESSION_KEY = "admin_user_id"
_SESSION_KEY = ADMIN_SESSION_KEY


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = str(form.get("username", "")).strip().lower()
        password = str(form.get("password", ""))

        async with SessionLocal() as session:
            user = (
                await session.execute(select(User).where(func.lower(User.email) == email))
            ).scalar_one_or_none()

        # Constant-time-ish: run a dummy verify for unknown users so the panel
        # doesn't leak which emails exist.
        if user is None:
            dummy_verify(password)
            return False
        if not verify_password(password, user.password_hash):
            return False
        if not (user.is_active and user.is_admin):
            return False

        request.session.update({_SESSION_KEY: user.id})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get(_SESSION_KEY)
        if not user_id:
            return False
        # Re-check on every request: a revoked admin (is_admin/is_active cleared)
        # loses access immediately, even with a live session cookie.
        async with SessionLocal() as session:
            user = await session.get(User, int(user_id))
        return bool(user and user.is_active and user.is_admin)
