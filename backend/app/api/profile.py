"""Public profile API: editable account data and user-owned leads."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.core.storage import public_url
from app.core.security import hash_password, verify_password
from app.db.deps import get_session
from app.models.catalog import Car, Model
from app.models.lead import Lead
from app.models.user import User
from app.schemas.auth import UserOut
from app.schemas.profile import (
    ProfileCarOut,
    ProfileLeadOut,
    ProfileUpdate,
    PasswordChangeIn,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _car_title(car: Car) -> str:
    model = car.model.name if car.model else "Авто"
    brand = car.model.brand.name if car.model and car.model.brand else ""
    return f"{brand} {model}".strip()


def _lead_out(lead: Lead) -> ProfileLeadOut:
    car = None
    if lead.car is not None:
        image_key = lead.car.card_image_url or (
            lead.car.images[0].url if lead.car.images else None
        )
        car = ProfileCarOut(
            id=lead.car.id,
            slug=lead.car.slug,
            title=_car_title(lead.car),
            image_url=public_url(image_key),
        )
    return ProfileLeadOut(
        id=lead.id,
        source_title=lead.source_title,
        dedupe_key=lead.dedupe_key,
        status=lead.status,
        comment=lead.comment,
        phone=lead.phone,
        created_at=lead.created_at,
        car=car,
    )


@router.patch("", response_model=UserOut)
async def update_profile(
    payload: ProfileUpdate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    current.full_name = payload.full_name
    current.phone = payload.phone
    await session.commit()
    await session.refresh(current)
    return UserOut.model_validate(current)


@router.post("/password")
async def change_password(
    payload: PasswordChangeIn,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if not verify_password(payload.current_password, current.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Текущий пароль указан неверно",
        )
    current.password_hash = hash_password(payload.new_password)
    await session.commit()
    return {"status": "ok"}


@router.get("/leads", response_model=list[ProfileLeadOut])
async def list_profile_leads(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProfileLeadOut]:
    leads = (
        await session.execute(
            select(Lead)
            .where(Lead.user_id == current.id)
            .options(
                selectinload(Lead.car).selectinload(Car.model).selectinload(Model.brand),
                selectinload(Lead.car).selectinload(Car.images),
            )
            .order_by(Lead.created_at.desc(), Lead.id.desc())
        )
    ).scalars().all()
    return [_lead_out(lead) for lead in leads]
