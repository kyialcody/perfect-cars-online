"""Response schemas for admin-managed homepage content."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.catalog import CarListItem


class HomePromoOut(BaseModel):
    id: int
    image_url: str | None
    link_url: str | None


class HomeCollectionOut(BaseModel):
    id: int
    title: str
    description: str | None
    button_text: str | None
    button_url: str | None
    image_url: str | None
    car: CarListItem | None


class HomeAboutOut(BaseModel):
    description: str | None
    video_url: str | None


class AboutSalonPhotoOut(BaseModel):
    id: int
    image_url: str | None
    alt: str | None


class BankPartnerOut(BaseModel):
    id: int
    name: str
    logo_url: str | None


class AboutPageResponse(BaseModel):
    description: str | None
    page_text: str | None
    photos: list[AboutSalonPhotoOut]
    banks: list[BankPartnerOut]


class HomeContentResponse(BaseModel):
    promos: list[HomePromoOut]
    collections: list[HomeCollectionOut]
    about: HomeAboutOut | None


class ContactPhoneOut(BaseModel):
    id: int
    value: str


class ContactAddressOut(BaseModel):
    id: int
    value: str
    show_in_header: bool


class ContactPhotoOut(BaseModel):
    id: int
    image_url: str | None
    alt: str | None


class RequisiteOut(BaseModel):
    id: int
    label: str
    value: str


class SocialLinkOut(BaseModel):
    id: int
    kind: str
    url: str | None
    icon_url: str | None


class ContactPageResponse(BaseModel):
    about_text: str | None
    footer_about_text: str | None
    phones: list[ContactPhoneOut]
    addresses: list[ContactAddressOut]
    photos: list[ContactPhotoOut]
    requisites: list[RequisiteOut]
    socials: list[SocialLinkOut]


class DealerLocationOut(BaseModel):
    id: int
    name: str
    address: str
    lat: float
    lng: float
    phone: str | None
    hours: str | None
