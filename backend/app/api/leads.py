"""Lead capture API: POST /leads with validation, anti-spam and Telegram ping."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.ratelimit import hit
from app.core.telegram import send_message
from app.db.deps import get_session
from app.models.catalog import Car
from app.models.lead import Lead, LeadStatus
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.lead import LeadCreate, LeadOut

router = APIRouter(prefix="/leads", tags=["leads"])
settings = get_settings()


def _client_ip(request: Request) -> str:
    """Client IP for rate limiting.

    X-Forwarded-For is client-controlled and trivially spoofable, so it is only
    honoured when ``trust_proxy`` is set (i.e. a trusted proxy overwrites it).
    By default we use the real socket peer.
    """
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _notification_text(lead: Lead, car: Car | None) -> str:
    # Lead fields are user-controlled and go into a parse_mode=HTML message —
    # escape them so a stray "<" doesn't break (and silently drop) the message.
    lines = [
        "<b>🚗 Новая заявка</b>",
        f"Имя: {escape(lead.name)}",
        f"Телефон: {escape(lead.phone)}",
        f"Источник: {escape(lead.source.value)}",
    ]
    if car is not None:
        lines.append(f"Авто: {escape(car.slug)}")
    if lead.source_title:
        lines.append(f"Заявка: {escape(lead.source_title)}")
    if lead.comment:
        lines.append(f"Комментарий: {escape(lead.comment)}")
    return "\n".join(lines)


@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    request: Request,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> LeadOut:
    # Honeypot: silently pretend success without persisting, so bots get no
    # signal that they were filtered.
    if payload.company:
        return LeadOut(
            id=0,
            user_id=current.id,
            name=payload.name,
            phone=payload.phone,
            source=payload.source,
            source_title=payload.source_title,
            dedupe_key=payload.dedupe_key,
            car_id=payload.car_id,
            comment=payload.comment,
            status=LeadStatus.new,
            created_at=datetime.now(timezone.utc),
        )

    ip = _client_ip(request)
    allowed = await hit(
        f"leads:rl:{ip}", settings.leads_rate_limit, settings.leads_rate_window
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много заявок, попробуйте позже",
        )

    car: Car | None = None
    if payload.car_id is not None:
        car = await session.get(Car, payload.car_id)
        # An admin-hidden car must not be referenceable from the public lead
        # form — reject it the same as a missing car.
        if car is None or not car.is_public:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Указанный автомобиль не найден",
            )

    dedupe_key = payload.dedupe_key
    if dedupe_key:
        existing = (
            await session.execute(
                select(Lead).where(
                    Lead.user_id == current.id,
                    Lead.dedupe_key == dedupe_key,
                    Lead.status.notin_([LeadStatus.done, LeadStatus.rejected]),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return LeadOut.model_validate(existing)

    lead = Lead(
        user_id=current.id,
        name=payload.name,
        phone=payload.phone,
        source=payload.source,
        source_title=payload.source_title,
        dedupe_key=dedupe_key,
        car_id=payload.car_id,
        comment=payload.comment,
        consent=payload.consent,
    )
    session.add(lead)
    await session.flush()
    await session.refresh(lead)
    await session.commit()

    # Fire-and-forget Telegram ping after the response is sent.
    background.add_task(send_message, _notification_text(lead, car))

    return LeadOut.model_validate(lead)
