"""SQLAdmin panel wiring (issue #18).

``setup_admin`` mounts the panel at ``/admin`` with the cookie-session auth
backend; ``ensure_admin_user`` provisions the admin account from settings on
startup.
"""
from __future__ import annotations

import io

from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy import func, select
from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request

from app.admin.about import AboutCompanyView
from app.admin.auth import AdminAuth
from app.admin.composer import CarSpecialView, CarUsedView, CarView
from app.admin.contacts import ContactsSettingsView
from app.admin.guide import GuideView
from app.admin.parts_composer import PartView
from app.admin.views import ALL_VIEWS
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models.user import User


class CarsAdmin(Admin):
    """Admin app that tolerates our custom non-column ``upload`` file fields.

    Several views add an ``upload`` FileField whose value is moved into the real
    column (``image_url``/``url``) in ``on_model_change``. On edit with no new
    file chosen, sqladmin's ``_handle_form_data`` does ``getattr(obj, "upload")``
    and raises ``AttributeError`` (the model has no such attribute) → HTTP 500.
    Using ``getattr(obj, key, None)`` turns that into a harmless no-op.
    """

    async def _handle_form_data(self, request: Request, obj=None) -> FormData:
        form = await request.form()
        form_data: list[tuple[str, str | UploadFile]] = []
        for key, value in form.multi_items():
            if not isinstance(value, UploadFile):
                form_data.append((key, value))
                continue
            should_clear = form.get(key + "_checkbox")
            empty_upload = len(await value.read(1)) != 1
            await value.seek(0)
            if should_clear:
                form_data.append((key, UploadFile(io.BytesIO(b""))))
            elif empty_upload and obj is not None and getattr(obj, key, None):
                f = getattr(obj, key)  # existing stored file — keep it on update
                form_data.append((key, UploadFile(filename=f.name, file=f.open())))
            else:
                form_data.append((key, value))
        return FormData(form_data)


def setup_admin(app: FastAPI) -> Admin:
    settings = get_settings()
    admin = CarsAdmin(
        app,
        engine=engine,
        authentication_backend=AdminAuth(secret_key=settings.jwt_secret),
        title="cars-zeekr · админка",
        base_url="/admin",
    )
    admin.add_base_view(CarView)
    admin.add_base_view(CarUsedView)
    admin.add_base_view(CarSpecialView)
    admin.add_base_view(PartView)
    admin.add_base_view(AboutCompanyView)
    admin.add_base_view(ContactsSettingsView)
    admin.add_base_view(GuideView)
    for view in ALL_VIEWS:
        admin.add_view(view)
    return admin


async def ensure_admin_user() -> None:
    """Create or promote the admin account from ADMIN_EMAIL / ADMIN_PASSWORD.

    No-op when either is unset. Existing accounts are promoted (is_admin /
    is_active) but their password is left untouched — change it from the panel.
    """
    settings = get_settings()
    if not (settings.admin_email and settings.admin_password):
        return

    email = settings.admin_email.strip().lower()
    async with SessionLocal() as session:
        user = (
            await session.execute(select(User).where(func.lower(User.email) == email))
        ).scalar_one_or_none()
        if user is None:
            session.add(
                User(
                    email=email,
                    password_hash=hash_password(settings.admin_password),
                    full_name="Администратор",
                    is_admin=True,
                    is_active=True,
                )
            )
        else:
            user.is_admin = True
            user.is_active = True
        await session.commit()
