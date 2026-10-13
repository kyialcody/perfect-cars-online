"""Admin-managed homepage content blocks."""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class HomePromo(TimestampMixin, Base):
    """Homepage hero banner: just a picture and where it links on click."""

    __tablename__ = "home_promo"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    image_url: Mapped[str | None] = mapped_column(String(500))
    link_url: Mapped[str | None] = mapped_column(String(300))  # page the banner opens
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.slug


class HomeCollection(TimestampMixin, Base):
    __tablename__ = "home_collection"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    button_text: Mapped[str | None] = mapped_column(String(80))
    button_url: Mapped[str | None] = mapped_column(String(300))
    image_url: Mapped[str | None] = mapped_column(String(500))
    car_id: Mapped[int | None] = mapped_column(ForeignKey("car.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    show_on_home: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    car = relationship("Car")

    def __str__(self) -> str:
        return self.title


class HomeAbout(TimestampMixin, Base):
    """Singleton 'About the company' block on the homepage."""

    __tablename__ = "home_about"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    page_text: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __str__(self) -> str:
        return "О компании"


class AboutSalonPhoto(TimestampMixin, Base):
    """Showroom photo displayed on the public About page."""

    __tablename__ = "about_salon_photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_url: Mapped[str | None] = mapped_column(String(500))
    alt: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.alt or f"Фото салона #{self.id}"


class BankPartner(TimestampMixin, Base):
    """Bank partner logo displayed on the public About page."""

    __tablename__ = "bank_partner"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.name


class ContactInfo(TimestampMixin, Base):
    """Singleton block backing the public Contacts page (and shared by the footer).

    Phones and addresses live in their own ordered child tables so admins can add
    or remove as many as needed; the ``about_text`` here is the Contacts-page
    «О компании» copy, independent from the homepage/About one.
    """

    __tablename__ = "contact_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    about_text: Mapped[str | None] = mapped_column(Text)
    # Paragraph shown to the left of the requisites block in the footer.
    footer_about_text: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __str__(self) -> str:
        return "Контакты"


class ContactPhone(TimestampMixin, Base):
    """One phone number shown on the Contacts page and in the footer."""

    __tablename__ = "contact_phone"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String(60))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.value


class ContactAddress(TimestampMixin, Base):
    """One address shown on the Contacts page and in the footer."""

    __tablename__ = "contact_address"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String(300))
    # Whether this address is shown in the site header (admin picks which/how many).
    show_in_header: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.value


class ContactPhoto(TimestampMixin, Base):
    """Photo of the showroom shown (and viewable) on the Contacts page."""

    __tablename__ = "contact_photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_url: Mapped[str | None] = mapped_column(String(500))
    alt: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.alt or f"Фото контактов #{self.id}"


class Requisite(TimestampMixin, Base):
    """One organisation requisite (label + value) shown in the footer."""

    __tablename__ = "requisite"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.label


class SocialLink(TimestampMixin, Base):
    """A social/contact link shown in the header and footer.

    ``kind`` selects a built-in icon (telegram, instagram, whatsapp, tiktok,
    phone, …); an uploaded ``icon_url`` overrides it. ``kind == "phone"`` with
    several phone numbers offers a chooser on click.
    """

    __tablename__ = "social_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    url: Mapped[str | None] = mapped_column(String(500))
    icon_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.kind


class DealerLocation(TimestampMixin, Base):
    """Dealer showroom location displayed on the homepage Yandex Map."""

    __tablename__ = "dealer_location"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str] = mapped_column(String(300))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(60))
    hours: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.name
