"""Public homepage content API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.catalog import _to_item
from app.core.storage import public_url
from app.db.deps import get_session
from app.models.catalog import Car, Model
from app.models.home import (
    AboutSalonPhoto,
    BankPartner,
    ContactAddress,
    ContactInfo,
    ContactPhone,
    ContactPhoto,
    DealerLocation,
    HomeAbout,
    HomeCollection,
    HomePromo,
    Requisite,
    SocialLink,
)
from app.schemas.home import (
    AboutPageResponse,
    AboutSalonPhotoOut,
    BankPartnerOut,
    ContactAddressOut,
    ContactPageResponse,
    ContactPhoneOut,
    ContactPhotoOut,
    DealerLocationOut,
    HomeAboutOut,
    HomeCollectionOut,
    HomeContentResponse,
    HomePromoOut,
    RequisiteOut,
    SocialLinkOut,
)

router = APIRouter(prefix="/home", tags=["home"])


def _asset_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(("http://", "https://", "/")):
        return value
    return public_url(value)


@router.get("", response_model=HomeContentResponse)
async def home_content(session: AsyncSession = Depends(get_session)) -> HomeContentResponse:
    promos = (
        await session.execute(
            select(HomePromo)
            .where(HomePromo.is_active.is_(True))
            .order_by(HomePromo.sort_order, HomePromo.id)
        )
    ).scalars().all()

    collections = (
        await session.execute(
            select(HomeCollection)
            .where(
                HomeCollection.is_active.is_(True),
                HomeCollection.show_on_home.is_(True),
                or_(
                    HomeCollection.car_id.is_(None),
                    HomeCollection.car_id.in_(
                        select(Car.id).where(Car.is_public)
                    ),
                ),
            )
            .order_by(HomeCollection.sort_order, HomeCollection.id)
            .options(
                selectinload(HomeCollection.car).joinedload(Car.model).joinedload(Model.brand),
                selectinload(HomeCollection.car).joinedload(Car.body_type),
                selectinload(HomeCollection.car).joinedload(Car.engine_type),
                selectinload(HomeCollection.car).joinedload(Car.drive),
                selectinload(HomeCollection.car).joinedload(Car.transmission),
                selectinload(HomeCollection.car).selectinload(Car.colors),
                selectinload(HomeCollection.car).selectinload(Car.images),
            )
        )
    ).unique().scalars().all()

    about_row = (
        await session.execute(
            select(HomeAbout).where(HomeAbout.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()

    about = HomeAboutOut(
        description=about_row.description,
        video_url=about_row.video_url,
    ) if about_row else None

    return HomeContentResponse(
        promos=[
            HomePromoOut(
                id=p.id,
                image_url=_asset_url(p.image_url),
                link_url=p.link_url,
            )
            for p in promos
        ],
        collections=[
            HomeCollectionOut(
                id=c.id,
                title=c.title,
                description=c.description,
                button_text=c.button_text,
                button_url=c.button_url,
                image_url=_asset_url(c.image_url),
                car=_to_item(c.car) if c.car else None,
            )
            for c in collections
        ],
        about=about,
    )


@router.get("/collections", response_model=list[HomeCollectionOut])
async def all_collections(session: AsyncSession = Depends(get_session)) -> list[HomeCollectionOut]:
    """All active collections — used by the catalog picks page."""
    rows = (
        await session.execute(
            select(HomeCollection)
            .where(
                HomeCollection.is_active.is_(True),
                or_(
                    HomeCollection.car_id.is_(None),
                    HomeCollection.car_id.in_(
                        select(Car.id).where(Car.is_public)
                    ),
                ),
            )
            .order_by(HomeCollection.sort_order, HomeCollection.id)
            .options(
                selectinload(HomeCollection.car).joinedload(Car.model).joinedload(Model.brand),
                selectinload(HomeCollection.car).joinedload(Car.body_type),
                selectinload(HomeCollection.car).joinedload(Car.engine_type),
                selectinload(HomeCollection.car).joinedload(Car.drive),
                selectinload(HomeCollection.car).joinedload(Car.transmission),
                selectinload(HomeCollection.car).selectinload(Car.colors),
                selectinload(HomeCollection.car).selectinload(Car.images),
            )
        )
    ).unique().scalars().all()

    return [
        HomeCollectionOut(
            id=c.id,
            title=c.title,
            description=c.description,
            button_text=c.button_text,
            button_url=c.button_url,
            image_url=_asset_url(c.image_url),
            car=_to_item(c.car) if c.car else None,
        )
        for c in rows
    ]


@router.get("/about", response_model=AboutPageResponse)
async def about_page(session: AsyncSession = Depends(get_session)) -> AboutPageResponse:
    about_row = (
        await session.execute(
            select(HomeAbout).where(HomeAbout.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    photos = (
        await session.execute(
            select(AboutSalonPhoto)
            .where(AboutSalonPhoto.is_active.is_(True))
            .order_by(AboutSalonPhoto.sort_order, AboutSalonPhoto.id)
        )
    ).scalars().all()
    banks = (
        await session.execute(
            select(BankPartner)
            .where(BankPartner.is_active.is_(True))
            .order_by(BankPartner.sort_order, BankPartner.id)
        )
    ).scalars().all()

    return AboutPageResponse(
        description=about_row.description if about_row else None,
        page_text=about_row.page_text if about_row else None,
        photos=[
            AboutSalonPhotoOut(id=item.id, image_url=_asset_url(item.image_url), alt=item.alt)
            for item in photos
        ],
        banks=[
            BankPartnerOut(id=item.id, name=item.name, logo_url=_asset_url(item.logo_url))
            for item in banks
        ],
    )


@router.get("/contacts", response_model=ContactPageResponse)
async def contacts_page(session: AsyncSession = Depends(get_session)) -> ContactPageResponse:
    info = (
        await session.execute(
            select(ContactInfo).where(ContactInfo.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    phones = (
        await session.execute(
            select(ContactPhone)
            .where(ContactPhone.is_active.is_(True))
            .order_by(ContactPhone.sort_order, ContactPhone.id)
        )
    ).scalars().all()
    addresses = (
        await session.execute(
            select(ContactAddress)
            .where(ContactAddress.is_active.is_(True))
            .order_by(ContactAddress.sort_order, ContactAddress.id)
        )
    ).scalars().all()
    photos = (
        await session.execute(
            select(ContactPhoto)
            .where(ContactPhoto.is_active.is_(True))
            .order_by(ContactPhoto.sort_order, ContactPhoto.id)
        )
    ).scalars().all()
    requisites = (
        await session.execute(
            select(Requisite)
            .where(Requisite.is_active.is_(True))
            .order_by(Requisite.sort_order, Requisite.id)
        )
    ).scalars().all()
    socials = (
        await session.execute(
            select(SocialLink)
            .where(SocialLink.is_active.is_(True))
            .order_by(SocialLink.sort_order, SocialLink.id)
        )
    ).scalars().all()

    return ContactPageResponse(
        about_text=info.about_text if info else None,
        footer_about_text=info.footer_about_text if info else None,
        phones=[ContactPhoneOut(id=p.id, value=p.value) for p in phones],
        addresses=[
            ContactAddressOut(id=a.id, value=a.value, show_in_header=a.show_in_header)
            for a in addresses
        ],
        photos=[
            ContactPhotoOut(id=item.id, image_url=_asset_url(item.image_url), alt=item.alt)
            for item in photos
        ],
        requisites=[RequisiteOut(id=r.id, label=r.label, value=r.value) for r in requisites],
        socials=[
            SocialLinkOut(id=s.id, kind=s.kind, url=s.url, icon_url=_asset_url(s.icon_url))
            for s in socials
        ],
    )


@router.get("/locations", response_model=list[DealerLocationOut])
async def dealer_locations(session: AsyncSession = Depends(get_session)) -> list[DealerLocationOut]:
    rows = (
        await session.execute(
            select(DealerLocation)
            .where(DealerLocation.is_active.is_(True))
            .order_by(DealerLocation.sort_order, DealerLocation.id)
        )
    ).scalars().all()

    return [
        DealerLocationOut(
            id=r.id,
            name=r.name,
            address=r.address,
            lat=r.lat,
            lng=r.lng,
            phone=r.phone,
            hours=r.hours,
        )
        for r in rows
    ]
