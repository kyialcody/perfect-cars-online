"""SQLAdmin model views for the catalog (issue #18, R1 refactor #72).

The reference tables (brands, models, body types, transmissions, drives, engine
types, colours) and the home content blocks. The car itself and all its children
(trims, images, colours, spec features, gifts) live on the single «Авто» form in
``app.admin.composer`` — not as separate ModelViews. Any change bumps the catalog
cache version so the public API reflects edits immediately.
"""
from __future__ import annotations

import uuid

from fastapi.concurrency import run_in_threadpool
from sqladmin import ModelView
from starlette.datastructures import UploadFile
from starlette.requests import Request
from wtforms import FileField
from wtforms.validators import Optional as OptionalValidator

from app.core.cache import bump_catalog_version
from app.core.config import get_settings
from app.core.storage import get_s3_client, public_url, put_object
from app.models.catalog import (
    BodyType,
    Brand,
    Color,
    Drive,
    EngineType,
    Model,
    Transmission,
)
from app.models.home import (
    BankPartner,
    ContactAddress,
    ContactPhone,
    DealerLocation,
    HomeCollection,
    HomePromo,
    Requisite,
    SocialLink,
)
from app.models.lead import Lead
from app.models.parts import PartCategory


class CatalogView(ModelView):
    """Base view: invalidate the catalog cache after any write."""

    async def after_model_change(self, data, model, is_created, request) -> None:
        await bump_catalog_version()

    async def after_model_delete(self, model, request) -> None:
        await bump_catalog_version()


# --- Reference tables --------------------------------------------------------


async def _store_upload(upload: UploadFile, prefix: str) -> str | None:
    """Save an uploaded file to S3/MinIO under ``prefix`` and return its key."""
    content = await upload.read()
    if not content:
        return None
    ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else "bin"
    key = f"{prefix}/{uuid.uuid4().hex}.{ext}"
    s = get_settings()
    client = get_s3_client()
    await run_in_threadpool(
        put_object,
        client,
        s.s3_bucket,
        key,
        content,
        upload.content_type or "application/octet-stream",
    )
    return key


def _logo_url_formatter(obj, _prop):
    """Render the stored S3 key as a browser-reachable URL in admin tables."""
    return public_url(obj.logo_url)


class BrandAdmin(CatalogView, model=Brand):
    name = "Бренд"
    name_plural = "Бренды"
    icon = "fa-solid fa-copyright"
    category = "Справочники"
    column_list = [Brand.id, Brand.name, Brand.slug, Brand.logo_url]
    column_searchable_list = [Brand.name, Brand.slug]
    column_formatters = {Brand.logo_url: _logo_url_formatter}
    column_formatters_detail = {Brand.logo_url: _logo_url_formatter}
    # `logo_url` is the stored S3 key; admins normally fill it via the upload
    # field below, but it stays editable for fixups (optional in the form).
    form_columns = [Brand.name, Brand.slug, Brand.logo_url]
    form_args = {"logo_url": {"validators": [OptionalValidator()]}}

    async def scaffold_form(self, rules=None):
        base = await super().scaffold_form(rules)

        class FormWithUpload(base):  # type: ignore[valid-type, misc]
            upload = FileField("Загрузить логотип (в MinIO)")

        return FormWithUpload

    async def on_model_change(self, data, model, is_created, request: Request) -> None:
        upload = data.pop("upload", None)
        if isinstance(upload, UploadFile) and upload.filename:
            key = await _store_upload(upload, "catalog/brand/uploads")
            if key:
                data["logo_url"] = key


class ModelAdmin(CatalogView, model=Model):
    name = "Модель"
    name_plural = "Модели"
    icon = "fa-solid fa-car-side"
    category = "Справочники"
    column_list = [Model.id, Model.name, Model.slug, Model.brand]
    column_searchable_list = [Model.name, Model.slug]
    form_columns = [Model.brand, Model.name, Model.slug]


class BodyTypeAdmin(CatalogView, model=BodyType):
    name = "Тип кузова"
    name_plural = "Типы кузова"
    category = "Справочники"
    column_list = [BodyType.id, BodyType.name, BodyType.slug]
    form_columns = [BodyType.name, BodyType.slug]


class TransmissionAdmin(CatalogView, model=Transmission):
    name = "КПП"
    name_plural = "КПП"
    category = "Справочники"
    column_list = [Transmission.id, Transmission.name, Transmission.slug]
    form_columns = [Transmission.name, Transmission.slug]


class DriveAdmin(CatalogView, model=Drive):
    name = "Привод"
    name_plural = "Приводы"
    category = "Справочники"
    column_list = [Drive.id, Drive.name, Drive.slug]
    form_columns = [Drive.name, Drive.slug]


class EngineTypeAdmin(CatalogView, model=EngineType):
    name = "Тип двигателя"
    name_plural = "Типы двигателя"
    category = "Справочники"
    column_list = [EngineType.id, EngineType.name, EngineType.slug]
    form_columns = [EngineType.name, EngineType.slug]


class ColorAdmin(CatalogView, model=Color):
    name = "Цвет"
    name_plural = "Цвета"
    category = "Справочники"
    column_list = [Color.id, Color.name, Color.hex]
    form_columns = [Color.name, Color.hex]


def _promo_image_formatter(obj, _prop):
    """Render the stored S3 key as a browser-reachable URL in admin tables."""
    return public_url(obj.image_url)


class HomePromoAdmin(CatalogView, model=HomePromo):
    name = "Баннер главной"
    name_plural = "Баннеры главной"
    icon = "fa-solid fa-image"
    category = "Главная"
    # The banner is just a picture + the page it opens on click.
    column_list = [
        HomePromo.id,
        HomePromo.slug,
        HomePromo.image_url,
        HomePromo.link_url,
        HomePromo.is_active,
        HomePromo.sort_order,
    ]
    column_sortable_list = [HomePromo.id, HomePromo.sort_order]
    column_formatters = {HomePromo.image_url: _promo_image_formatter}
    column_formatters_detail = {HomePromo.image_url: _promo_image_formatter}
    form_columns = [
        HomePromo.slug,
        HomePromo.link_url,
        HomePromo.image_url,
        HomePromo.is_active,
        HomePromo.sort_order,
    ]
    form_args = {"image_url": {"validators": [OptionalValidator()]}}

    async def scaffold_form(self, rules=None):
        base = await super().scaffold_form(rules)

        class FormWithUpload(base):  # type: ignore[valid-type, misc]
            upload = FileField("Загрузить фото баннера — 1440×480 px (3:1), иначе обрежется")

        return FormWithUpload

    async def on_model_change(self, data, model, is_created, request: Request) -> None:
        upload = data.pop("upload", None)
        if isinstance(upload, UploadFile) and upload.filename:
            key = await _store_upload(upload, "home/promo")
            if key:
                data["image_url"] = key


class HomeCollectionAdmin(CatalogView, model=HomeCollection):
    name = "Подборка"
    name_plural = "Подборки автомобилей"
    icon = "fa-solid fa-layer-group"
    category = "Подборки"
    column_list = [
        HomeCollection.id,
        HomeCollection.slug,
        HomeCollection.title,
        HomeCollection.car,
        HomeCollection.show_on_home,
        HomeCollection.is_active,
        HomeCollection.sort_order,
    ]
    column_sortable_list = [HomeCollection.id, HomeCollection.sort_order]
    form_columns = [
        HomeCollection.slug,
        HomeCollection.title,
        HomeCollection.description,
        HomeCollection.button_text,
        HomeCollection.button_url,
        HomeCollection.image_url,
        HomeCollection.car,
        HomeCollection.show_on_home,
        HomeCollection.is_active,
        HomeCollection.sort_order,
    ]


def _bank_logo_formatter(obj, _prop):
    return public_url(obj.logo_url)


class BankPartnerAdmin(CatalogView, model=BankPartner):
    name = "Банк-партнёр"
    name_plural = "Банки-партнёры"
    icon = "fa-solid fa-building-columns"
    category = "О компании"
    column_list = [
        BankPartner.id,
        BankPartner.name,
        BankPartner.logo_url,
        BankPartner.is_active,
        BankPartner.sort_order,
    ]
    column_sortable_list = [BankPartner.id, BankPartner.sort_order]
    column_formatters = {BankPartner.logo_url: _bank_logo_formatter}
    column_formatters_detail = {BankPartner.logo_url: _bank_logo_formatter}
    form_columns = [
        BankPartner.name,
        BankPartner.logo_url,
        BankPartner.is_active,
        BankPartner.sort_order,
    ]
    form_args = {"logo_url": {"validators": [OptionalValidator()]}}

    async def scaffold_form(self, rules=None):
        base = await super().scaffold_form(rules)

        class FormWithUpload(base):  # type: ignore[valid-type, misc]
            upload = FileField("Загрузить логотип банка")

        return FormWithUpload

    async def on_model_change(self, data, model, is_created, request: Request) -> None:
        upload = data.pop("upload", None)
        if isinstance(upload, UploadFile) and upload.filename:
            key = await _store_upload(upload, "about/banks")
            if key:
                data["logo_url"] = key


class PartCategoryAdmin(CatalogView, model=PartCategory):
    name = "Категория запчастей"
    name_plural = "Категории запчастей"
    icon = "fa-solid fa-layer-group"
    category = "Справочники"
    column_list = [PartCategory.id, PartCategory.name, PartCategory.slug]
    column_searchable_list = [PartCategory.name, PartCategory.slug]
    form_columns = [PartCategory.name, PartCategory.slug]


class DealerLocationAdmin(CatalogView, model=DealerLocation):
    name = "Точка на карте"
    name_plural = "Точки на карте"
    icon = "fa-solid fa-location-dot"
    category = "Главная"
    column_list = [
        DealerLocation.id,
        DealerLocation.name,
        DealerLocation.address,
        DealerLocation.is_active,
        DealerLocation.sort_order,
    ]
    column_sortable_list = [DealerLocation.id, DealerLocation.sort_order]
    form_columns = [
        DealerLocation.name,
        DealerLocation.address,
        DealerLocation.lat,
        DealerLocation.lng,
        DealerLocation.phone,
        DealerLocation.hours,
        DealerLocation.is_active,
        DealerLocation.sort_order,
    ]


class RequisiteAdmin(CatalogView, model=Requisite):
    name = "Реквизит"
    name_plural = "Реквизиты"
    icon = "fa-solid fa-file-invoice"
    category = "Контакты"
    column_list = [
        Requisite.id,
        Requisite.label,
        Requisite.value,
        Requisite.is_active,
        Requisite.sort_order,
    ]
    column_sortable_list = [Requisite.id, Requisite.sort_order]
    form_columns = [
        Requisite.label,
        Requisite.value,
        Requisite.is_active,
        Requisite.sort_order,
    ]


def _social_icon_formatter(obj, _prop):
    return public_url(obj.icon_url) if obj.icon_url else None


class SocialLinkAdmin(CatalogView, model=SocialLink):
    name = "Соцсеть"
    name_plural = "Соцсети"
    icon = "fa-solid fa-share-nodes"
    category = "Контакты"
    column_list = [
        SocialLink.id,
        SocialLink.kind,
        SocialLink.url,
        SocialLink.icon_url,
        SocialLink.is_active,
        SocialLink.sort_order,
    ]
    column_sortable_list = [SocialLink.id, SocialLink.sort_order]
    column_formatters = {SocialLink.icon_url: _social_icon_formatter}
    column_formatters_detail = {SocialLink.icon_url: _social_icon_formatter}
    form_columns = [
        SocialLink.kind,
        SocialLink.url,
        SocialLink.icon_url,
        SocialLink.is_active,
        SocialLink.sort_order,
    ]
    form_args = {"icon_url": {"validators": [OptionalValidator()]}}
    column_labels = {
        SocialLink.kind: "Тип (telegram, instagram, whatsapp, tiktok, vk, youtube, phone)",
        SocialLink.url: "Ссылка (для phone — tel:+7..., можно оставить пустым)",
        SocialLink.icon_url: "Иконка (необязательно; PNG/SVG, рекомендуется 32×32 px)",
    }

    async def scaffold_form(self, rules=None):
        base = await super().scaffold_form(rules)

        class FormWithUpload(base):  # type: ignore[valid-type, misc]
            upload = FileField("Загрузить иконку (32×32 px, PNG/SVG)")

        return FormWithUpload

    async def on_model_change(self, data, model, is_created, request: Request) -> None:
        upload = data.pop("upload", None)
        if isinstance(upload, UploadFile) and upload.filename:
            key = await _store_upload(upload, "socials")
            if key:
                data["icon_url"] = key


class ContactPhoneAdmin(CatalogView, model=ContactPhone):
    name = "Телефон"
    name_plural = "Телефоны"
    icon = "fa-solid fa-phone"
    category = "Контакты"
    column_list = [
        ContactPhone.id,
        ContactPhone.value,
        ContactPhone.is_active,
        ContactPhone.sort_order,
    ]
    column_sortable_list = [ContactPhone.id, ContactPhone.sort_order]
    form_columns = [
        ContactPhone.value,
        ContactPhone.is_active,
        ContactPhone.sort_order,
    ]


class ContactAddressAdmin(CatalogView, model=ContactAddress):
    name = "Адрес"
    name_plural = "Адреса"
    icon = "fa-solid fa-location-dot"
    category = "Контакты"
    column_list = [
        ContactAddress.id,
        ContactAddress.value,
        ContactAddress.show_in_header,
        ContactAddress.is_active,
        ContactAddress.sort_order,
    ]
    column_sortable_list = [ContactAddress.id, ContactAddress.sort_order]
    form_columns = [
        ContactAddress.value,
        ContactAddress.show_in_header,
        ContactAddress.is_active,
        ContactAddress.sort_order,
    ]
    column_labels = {ContactAddress.show_in_header: "Показывать в шапке"}


class LeadAdmin(ModelView, model=Lead):
    name = "Заявка"
    name_plural = "Заявки"
    icon = "fa-solid fa-clipboard-list"
    category = "Заявки"
    column_list = [
        Lead.id,
        Lead.user,
        Lead.name,
        Lead.phone,
        Lead.source_title,
        Lead.car,
        Lead.status,
        Lead.created_at,
    ]
    column_sortable_list = [Lead.id, Lead.created_at, Lead.status]
    column_searchable_list = [Lead.phone, Lead.source_title, Lead.comment]
    form_columns = [
        Lead.user,
        Lead.name,
        Lead.phone,
        Lead.source,
        Lead.source_title,
        Lead.dedupe_key,
        Lead.car,
        Lead.comment,
        Lead.consent,
        Lead.status,
    ]
    column_labels = {
        Lead.user: "Пользователь",
        Lead.name: "Имя пользователя",
        Lead.phone: "Телефон",
        Lead.source_title: "Источник заявки",
        Lead.car: "Автомобиль",
        Lead.status: "Статус",
        Lead.created_at: "Дата",
    }


ALL_VIEWS = [
    LeadAdmin,
    HomePromoAdmin,
    BankPartnerAdmin,
    DealerLocationAdmin,
    ContactPhoneAdmin,
    ContactAddressAdmin,
    RequisiteAdmin,
    SocialLinkAdmin,
    HomeCollectionAdmin,
    BrandAdmin,
    ModelAdmin,
    BodyTypeAdmin,
    TransmissionAdmin,
    DriveAdmin,
    EngineTypeAdmin,
    ColorAdmin,
    PartCategoryAdmin,
]
