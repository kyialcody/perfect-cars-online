"""Idempotent seed for the Zeekr MVP catalog.

Run inside the api container:

    docker compose exec api python -m app.seed

Re-running is safe: top-level rows are matched by their unique slug/name and
reused; missing car children (trims/images/features/gifts/colors/benefits) are
backfilled without duplicating existing rows. Placeholder images are SVGs
uploaded to MinIO.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import bump_catalog_version
from app.core.config import get_settings
from app.core.storage import ensure_bucket, get_s3_client, put_object
from app.core.text import slugify as _slug
from app.db.session import SessionLocal
from app.models.catalog import (
    BodyType,
    Brand,
    Car,
    CarBenefit,
    CarFeature,
    CarGift,
    CarImage,
    Color,
    Condition,
    Drive,
    EngineType,
    FeatureBlock,
    Model,
    Transmission,
    Trim,
    car_color,
)
from app.models.home import (
    AboutSalonPhoto,
    BankPartner,
    ContactAddress,
    ContactInfo,
    ContactPhone,
    ContactPhoto,
    HomeAbout,
    HomeCollection,
    HomePromo,
    Requisite,
    SocialLink,
)
from app.models.parts import Part, PartCategory, PartCondition, PartImage, PartKind

settings = get_settings()

COLORS = [
    ("Чёрный", "#262626"),
    ("Белый", "#FFFFFF"),
    ("Серый", "#737373"),
    ("Синий", "#1A3E73"),
    ("Зелёный", "#1A7F37"),
]

# name, slug, body type, drive, power(hp), accel 0-100(s), max speed, kWh/100km, price, price_old, trims
ZEEKR = [
    {
        "name": "001", "slug": "001", "body": "Лифтбек", "drive": "Полный",
        "power": 544, "accel": Decimal("3.8"), "max_speed": 200, "consumption": Decimal("15.5"),
        "price": Decimal("5500000"), "price_old": Decimal("5900000"),
        "colors": ["Чёрный", "Белый", "Серый", "Синий"],
        "trims": [("Long Range", 400, Decimal("5500000"), Decimal("5300000")),
                  ("Performance", 544, Decimal("5900000"), Decimal("5700000"))],
    },
    {
        "name": "7", "slug": "7", "body": "Седан", "drive": "Задний",
        "power": 421, "accel": Decimal("5.4"), "max_speed": 210, "consumption": Decimal("14.8"),
        "price": Decimal("4700000"), "price_old": Decimal("5000000"),
        "colors": ["Чёрный", "Белый", "Зелёный"],
        "trims": [("RWD", 421, Decimal("4700000"), Decimal("4550000")),
                  ("AWD", 638, Decimal("5200000"), Decimal("5000000"))],
    },
    {
        "name": "X", "slug": "x", "body": "Кроссовер", "drive": "Полный",
        "power": 428, "accel": Decimal("3.7"), "max_speed": 180, "consumption": Decimal("16.2"),
        "price": Decimal("3900000"), "price_old": Decimal("4200000"),
        "colors": ["Белый", "Серый", "Синий"],
        "trims": [("Core", 272, Decimal("3900000"), Decimal("3800000")),
                  ("Privilege AWD", 428, Decimal("4300000"), Decimal("4150000"))],
    },
    {
        "name": "9X", "slug": "9x", "body": "Внедорожник", "drive": "Полный",
        "power": 1381, "accel": Decimal("3.1"), "max_speed": 240, "consumption": Decimal("19.5"),
        "price": Decimal("9900000"), "price_old": Decimal("10500000"),
        "colors": ["Чёрный", "Белый", "Серый", "Зелёный"],
        "trims": [("Flagship AWD", 1100, Decimal("9900000"), Decimal("9650000")),
                  ("Hyper AWD", 1381, Decimal("11200000"), Decimal("10900000"))],
    },
    {
        "name": "009", "slug": "009", "body": "Минивэн", "drive": "Полный",
        "power": 544, "accel": Decimal("4.5"), "max_speed": 190, "consumption": Decimal("18.0"),
        "price": Decimal("8200000"), "price_old": Decimal("8800000"),
        "colors": ["Чёрный", "Белый"],
        "trims": [("Me", 544, Decimal("8200000"), Decimal("8000000")),
                  ("Grand", 790, Decimal("9500000"), Decimal("9200000"))],
    },
]

TEST_USED_CAR = {
    "name": "009 Grand тестовый с пробегом",
    "slug": "zeekr-009-grand-used-test",
    "model": "009",
    "model_slug": "009",
    "body": "Минивэн",
    "drive": "Полный",
    "price": Decimal("20500000"),
    "price_old": Decimal("21900000"),
    "year": 2025,
    "mileage": 12000,
    "power": 790,
    "engine_volume": None,
    "accel": Decimal("3.9"),
    "max_speed": 190,
    "consumption": Decimal("18.2"),
    "colors": ["Чёрный", "Белый"],
}

# Спецпредложение редактируется по форме «с пробегом» (год/пробег/галерея).
TEST_SPECIAL_CAR = {
    "name": "001 тестовое спецпредложение",
    "slug": "zeekr-001-special-test",
    "model": "001",
    "model_slug": "001",
    "body": "Кроссовер",
    "drive": "Полный",
    "price": Decimal("15900000"),
    "price_old": Decimal("17500000"),
    "year": 2025,
    "mileage": 5000,
    "power": 544,
    "engine_volume": None,
    "accel": Decimal("3.8"),
    "max_speed": 200,
    "consumption": Decimal("16.5"),
    "colors": ["Чёрный", "Белый"],
}

FEATURES = {
    FeatureBlock.safety: [
        "Системы ADAS второго уровня",
        "Подушки безопасности по кругу",
        "Контроль слепых зон",
        "Камеры кругового обзора",
    ],
    FeatureBlock.exterior: [
        "Полностью светодиодная оптика",
        "Безрамочные двери",
        "Панорамная крыша",
        "Литые диски 20\"",
    ],
    FeatureBlock.interior: [
        "Мультимедиа с большим экраном",
        "Беспроводная зарядка",
        "Премиальная аудиосистема",
        "Электрорегулировка сидений с памятью",
    ],
}

GIFTS = ["Страхование в подарок", "Зарядное оборудование в подарок", "Комплект резины в подарок"]

BENEFITS = [
    ("percent", "Выгодный кредит"),
    ("trade", "Зачёт вашего авто в trade-in"),
    ("gift", "Подарок на выбор при покупке авто"),
]

# Spare-parts catalog. name, slug — reference categories (справочник).
PART_CATEGORIES = [
    ("Тормозная система", "brakes"),
    ("Подвеска", "suspension"),
    ("Оптика", "optics"),
    ("Электрика", "electrics"),
    ("Фильтры", "filters"),
    ("Шины и диски", "wheels"),
]

# name, slug, category slug, condition, kind, manufacturer, article, price, price_old
PARTS = [
    ("Тормозные колодки передние Zeekr 001", "zeekr-001-front-brake-pads", "brakes",
     PartCondition.new, PartKind.original, "Zeekr", "ZK-BP-001F",
     Decimal("18500"), Decimal("21000")),
    ("Амортизатор задний Zeekr X", "zeekr-x-rear-shock", "suspension",
     PartCondition.new, PartKind.aftermarket, "KYB", "KYB-349205",
     Decimal("24900"), None),
    ("Фара левая LED Zeekr 001", "zeekr-001-left-headlight", "optics",
     PartCondition.new, PartKind.original, "Zeekr", "ZK-HL-001L",
     Decimal("89000"), Decimal("97000")),
    ("Салонный фильтр Zeekr 7", "zeekr-7-cabin-filter", "filters",
     PartCondition.new, PartKind.aftermarket, "MANN", "MANN-CU-26010",
     Decimal("2400"), None),
    ("Аккумулятор 12В Zeekr 009", "zeekr-009-aux-battery", "electrics",
     PartCondition.used, PartKind.original, "Zeekr", "ZK-BAT-009",
     Decimal("15500"), Decimal("18000")),
    ("Комплект зимних шин 20\" Zeekr 9X", "zeekr-9x-winter-tires", "wheels",
     PartCondition.new, PartKind.aftermarket, "Nokian", "NOK-HKPL-R5",
     Decimal("142000"), Decimal("158000")),
]

ABOUT_TEXT = """Официальный дилер Electro-avto предлагает широкий выбор автомобилей различных цветов и комплектаций на самых выгодных условиях.

На территории автосалона представлены новые автомобили и автомобили с пробегом. Среди ассортимента представлены модели ведущих производителей, включая электрокары и гибриды.

Выбирая автосалон, вы получаете:
• выгодные цены на автомобили в наличии;
• помощь в подборе комплектации и цвета;
• консультацию по Trade-in, кредиту и рассрочке;
• юридическое сопровождение сделки;
• возможность участия в программах банков-партнёров.

Мы ценим каждого клиента и гарантируем высокий уровень сервиса."""


def placeholder_svg(label: str, bg: str) -> bytes:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" '
        'viewBox="0 0 800 500">'
        f'<rect width="800" height="500" fill="{bg}"/>'
        '<text x="400" y="260" font-family="Roboto, Arial, sans-serif" '
        'font-size="46" font-weight="700" fill="#FFFFFF" text-anchor="middle">'
        f'{label}</text></svg>'
    )
    return svg.encode("utf-8")


def home_hero_svg() -> bytes:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="560" viewBox="0 0 1440 560">'
        '<defs>'
        '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#f4f5f5"/><stop offset="1" stop-color="#ffffff"/>'
        '</linearGradient>'
        '</defs>'
        '<rect width="1440" height="560" rx="24" fill="url(#g)"/>'
        '<g opacity=".45" stroke="#d9dcdf" stroke-width="3">'
        '<path d="M760 102h48v278h-48zM842 58h56v322h-56zM928 132h52v248h-52zM1014 84h68v296h-68zM1116 148h46v232h-46z"/>'
        '<path d="M690 380h560M720 324h500M758 268h428" opacity=".55"/>'
        '</g>'
        '<g transform="translate(492 246)">'
        '<ellipse cx="360" cy="168" rx="320" ry="28" fill="#000" opacity=".16"/>'
        '<path d="M72 138c48-75 112-112 198-112h234c70 0 134 40 178 108l26 40H48z" fill="#1f1f1f"/>'
        '<path d="M112 128c38-48 90-72 160-72h206c54 0 98 22 132 66H112z" fill="#dfe6eb"/>'
        '<path d="M72 138h638c18 0 32 14 32 32v10H34v-8c0-19 17-34 38-34z" fill="#ca0100"/>'
        '<circle cx="172" cy="180" r="48" fill="#242424"/><circle cx="172" cy="180" r="24" fill="#f5f5f5"/>'
        '<circle cx="592" cy="180" r="48" fill="#242424"/><circle cx="592" cy="180" r="24" fill="#f5f5f5"/>'
        '<path d="M284 56h102l-28 72H230z" fill="#cfd8de"/>'
        '<text x="350" y="178" font-family="Arial, sans-serif" font-size="42" font-weight="700" fill="#fff" text-anchor="middle">ZEEKR</text>'
        '</g>'
        '</svg>'
    )
    return svg.encode("utf-8")


def salon_svg(label: str, accent: str) -> bytes:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="560" viewBox="0 0 1000 560">'
        '<rect width="1000" height="560" rx="34" fill="#f4f5f5"/>'
        '<path d="M0 412h1000v148H0z" fill="#e6e8e8"/>'
        '<path d="M72 80h856v302H72z" fill="#ffffff"/>'
        '<path d="M72 80h856v58H72z" fill="#252525"/>'
        '<g fill="#d9dcdf"><rect x="120" y="176" width="190" height="150" rx="8"/><rect x="406" y="176" width="190" height="150" rx="8"/><rect x="692" y="176" width="190" height="150" rx="8"/></g>'
        f'<path d="M135 356h220c22 0 42 12 52 32l20 38H90l18-35c10-21 27-35 27-35z" fill="{accent}"/>'
        '<circle cx="164" cy="428" r="28" fill="#262626"/><circle cx="352" cy="428" r="28" fill="#262626"/>'
        '<g opacity=".38" stroke="#ffffff" stroke-width="2"><path d="M128 456h760M128 488h760M128 520h760"/></g>'
        f'<text x="500" y="508" font-family="Arial, sans-serif" font-size="38" font-weight="700" fill="#262626" text-anchor="middle">{label}</text>'
        '</svg>'
    )
    return svg.encode("utf-8")


def bank_logo_svg(name: str, color: str) -> bytes:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="140" viewBox="0 0 420 140">'
        '<rect width="420" height="140" rx="16" fill="#f0f1f1"/>'
        f'<circle cx="78" cy="70" r="24" fill="{color}" opacity=".16"/>'
        f'<path d="M62 70l11 11 24-26" fill="none" stroke="{color}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<text x="124" y="80" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="{color}">{name}</text>'
        '</svg>'
    )
    return svg.encode("utf-8")


async def get_or_create(session: AsyncSession, model, defaults: dict | None = None, **filters):
    res = await session.execute(select(model).filter_by(**filters))
    obj = res.scalar_one_or_none()
    if obj is not None:
        return obj, False
    obj = model(**filters, **(defaults or {}))
    session.add(obj)
    await session.flush()
    return obj, True


async def seed() -> None:
    s3 = get_s3_client()
    ensure_bucket(s3, settings.s3_bucket)

    async with SessionLocal() as session:
        # Reference data
        engine_type, _ = await get_or_create(
            session, EngineType, slug="electro", defaults={"name": "Электро"}
        )
        transmission, _ = await get_or_create(
            session, Transmission, slug="avtomat", defaults={"name": "Автомат"}
        )
        drives = {}
        for name, slug in [("Полный", "full"), ("Задний", "rear")]:
            drives[name], _ = await get_or_create(
                session, Drive, slug=slug, defaults={"name": name}
            )
        colors = {}
        for name, hex_ in COLORS:
            colors[name], _ = await get_or_create(
                session, Color, name=name, defaults={"hex": hex_}
            )

        # Brand + logo
        brand, _ = await get_or_create(
            session, Brand, slug="zeekr",
            defaults={
                "name": "Zeekr",
                "logo_url": "https://autokuz.ru/assets/emblems/zeekr.png",
            },
        )
        brand.logo_url = "https://autokuz.ru/assets/emblems/zeekr.png"

        created_cars = 0
        for spec in ZEEKR:
            body_type, _ = await get_or_create(
                session, BodyType, name=spec["body"],
                defaults={"slug": _slug(spec["body"])},
            )
            model_obj, _ = await get_or_create(
                session, Model, brand_id=brand.id, slug=spec["slug"],
                defaults={"name": spec["name"]},
            )

            car_slug = f"zeekr-{spec['slug']}"
            car, created = await get_or_create(
                session, Car, slug=car_slug,
                defaults={
                    "condition": Condition.new,
                    "model_id": model_obj.id,
                    "body_type_id": body_type.id,
                    "engine_type_id": engine_type.id,
                    "price": spec["price"],
                    "price_old": spec["price_old"],
                    "benefit_badge": f"Выгода до {int(spec['price_old'] - spec['price']):,} ₽".replace(",", " "),
                    "status_text": "В наличии с ПТС",
                    "power_hp": spec["power"],
                    "fuel_consumption": spec["consumption"],
                    "acceleration_0_100": spec["accel"],
                    "max_speed": spec["max_speed"],
                    "in_stock": True,
                    "qty": 3,
                },
            )
            if created:
                created_cars += 1

            # Colors (insert association rows directly — avoids async lazy-load)
            for cname in spec["colors"]:
                color_id = colors[cname].id
                linked = await session.scalar(
                    select(car_color.c.car_id).where(
                        car_color.c.car_id == car.id,
                        car_color.c.color_id == color_id,
                    )
                )
                if linked is None:
                    await session.execute(
                        car_color.insert().values(car_id=car.id, color_id=color_id)
                    )

            # Images (main + 2 gallery placeholders)
            backgrounds = ["#262626", "#1A3E73", "#737373", "#1A7F37"]
            has_images = await session.scalar(select(CarImage.id).where(CarImage.car_id == car.id).limit(1))
            if has_images is None:
                for i, bg in enumerate(backgrounds):
                    key = f"catalog/{car_slug}/{'main' if i == 0 else f'gallery-{i}'}.svg"
                    put_object(s3, settings.s3_bucket, key,
                               placeholder_svg(f"Zeekr {spec['name']}", bg), "image/svg+xml")
                    session.add(CarImage(car_id=car.id, url=key, is_main=(i == 0), sort_order=i))

            # Trims
            for order, (tname, tpower, tprice, tdiscount) in enumerate(spec["trims"]):
                exists_trim = await session.scalar(
                    select(Trim.id).where(Trim.car_id == car.id, Trim.name == tname).limit(1)
                )
                if exists_trim is None:
                    session.add(Trim(
                        car_id=car.id, name=tname, engine_volume=None, power_hp=tpower,
                        transmission_id=transmission.id, drive_id=drives[spec["drive"]].id,
                        price=tprice, price_discount=tdiscount, sort_order=order,
                    ))

            # Features
            for block, items in FEATURES.items():
                for order, text in enumerate(items):
                    exists_feature = await session.scalar(
                        select(CarFeature.id).where(
                            CarFeature.car_id == car.id,
                            CarFeature.block == block,
                            CarFeature.text == text,
                        ).limit(1)
                    )
                    if exists_feature is None:
                        session.add(CarFeature(car_id=car.id, block=block, text=text, sort_order=order))

            # Gifts
            for order, text in enumerate(GIFTS):
                exists_gift = await session.scalar(
                    select(CarGift.id).where(CarGift.car_id == car.id, CarGift.text == text).limit(1)
                )
                if exists_gift is None:
                    session.add(CarGift(car_id=car.id, text=text, sort_order=order))

            # Detail hero benefits
            for order, (icon, text) in enumerate(BENEFITS):
                exists_benefit = await session.scalar(
                    select(CarBenefit.id).where(
                        CarBenefit.car_id == car.id,
                        CarBenefit.text == text,
                    ).limit(1)
                )
                if exists_benefit is None:
                    session.add(
                        CarBenefit(
                            car_id=car.id,
                            icon=icon,
                            text=text,
                            sort_order=order,
                            is_active=True,
                        )
                    )

        used = TEST_USED_CAR
        body_type, _ = await get_or_create(
            session, BodyType, name=used["body"],
            defaults={"slug": _slug(used["body"])},
        )
        model_obj, _ = await get_or_create(
            session, Model, brand_id=brand.id, slug=used["model_slug"],
            defaults={"name": used["model"]},
        )
        used_car, created = await get_or_create(
            session,
            Car,
            slug=used["slug"],
            defaults={
                "condition": Condition.used,
                "model_id": model_obj.id,
                "body_type_id": body_type.id,
                "engine_type_id": engine_type.id,
                "drive_id": drives[used["drive"]].id,
                "transmission_id": transmission.id,
                "price": used["price"],
                "price_old": used["price_old"],
                "benefit_badge": f"Выгода до {int(used['price_old'] - used['price']):,} ₽".replace(",", " "),
                "status_text": "Тестовый автомобиль с пробегом",
                "power_hp": used["power"],
                "fuel_consumption": used["consumption"],
                "acceleration_0_100": used["accel"],
                "max_speed": used["max_speed"],
                "year": used["year"],
                "mileage": used["mileage"],
                "engine_volume": used["engine_volume"],
                "in_stock": True,
                "qty": 1,
            },
        )
        if created:
            created_cars += 1

        for cname in used["colors"]:
            color_id = colors[cname].id
            linked = await session.scalar(
                select(car_color.c.car_id).where(
                    car_color.c.car_id == used_car.id,
                    car_color.c.color_id == color_id,
                )
            )
            if linked is None:
                await session.execute(
                    car_color.insert().values(car_id=used_car.id, color_id=color_id)
                )

        has_images = await session.scalar(select(CarImage.id).where(CarImage.car_id == used_car.id).limit(1))
        if has_images is None:
            for i, bg in enumerate(["#262626", "#737373", "#1A3E73"]):
                key = f"catalog/{used['slug']}/{'main' if i == 0 else f'gallery-{i}'}.svg"
                put_object(
                    s3,
                    settings.s3_bucket,
                    key,
                    placeholder_svg("Zeekr 009 used test", bg),
                    "image/svg+xml",
                )
                session.add(CarImage(car_id=used_car.id, url=key, is_main=(i == 0), sort_order=i))

        for order, text in enumerate(GIFTS[:2]):
            exists_gift = await session.scalar(
                select(CarGift.id).where(CarGift.car_id == used_car.id, CarGift.text == text).limit(1)
            )
            if exists_gift is None:
                session.add(CarGift(car_id=used_car.id, text=text, sort_order=order))

        for order, (icon, text) in enumerate(BENEFITS[:2]):
            exists_benefit = await session.scalar(
                select(CarBenefit.id).where(
                    CarBenefit.car_id == used_car.id,
                    CarBenefit.text == text,
                ).limit(1)
            )
            if exists_benefit is None:
                session.add(
                    CarBenefit(
                        car_id=used_car.id,
                        icon=icon,
                        text=text,
                        sort_order=order,
                        is_active=True,
                    )
                )

        special = TEST_SPECIAL_CAR
        body_type, _ = await get_or_create(
            session, BodyType, name=special["body"],
            defaults={"slug": _slug(special["body"])},
        )
        model_obj, _ = await get_or_create(
            session, Model, brand_id=brand.id, slug=special["model_slug"],
            defaults={"name": special["model"]},
        )
        special_car, created = await get_or_create(
            session,
            Car,
            slug=special["slug"],
            defaults={
                "condition": Condition.special,
                "model_id": model_obj.id,
                "body_type_id": body_type.id,
                "engine_type_id": engine_type.id,
                "drive_id": drives[special["drive"]].id,
                "transmission_id": transmission.id,
                "price": special["price"],
                "price_old": special["price_old"],
                "benefit_badge": f"Выгода до {int(special['price_old'] - special['price']):,} ₽".replace(",", " "),
                "status_text": "Тестовое спецпредложение",
                "power_hp": special["power"],
                "fuel_consumption": special["consumption"],
                "acceleration_0_100": special["accel"],
                "max_speed": special["max_speed"],
                "year": special["year"],
                "mileage": special["mileage"],
                "engine_volume": special["engine_volume"],
                "in_stock": True,
                "qty": 1,
            },
        )
        if created:
            created_cars += 1

        for cname in special["colors"]:
            color_id = colors[cname].id
            linked = await session.scalar(
                select(car_color.c.car_id).where(
                    car_color.c.car_id == special_car.id,
                    car_color.c.color_id == color_id,
                )
            )
            if linked is None:
                await session.execute(
                    car_color.insert().values(car_id=special_car.id, color_id=color_id)
                )

        has_images = await session.scalar(
            select(CarImage.id).where(CarImage.car_id == special_car.id).limit(1)
        )
        if has_images is None:
            for i, bg in enumerate(["#262626", "#737373", "#1A3E73"]):
                key = f"catalog/{special['slug']}/{'main' if i == 0 else f'gallery-{i}'}.svg"
                put_object(
                    s3,
                    settings.s3_bucket,
                    key,
                    placeholder_svg("Zeekr 001 special test", bg),
                    "image/svg+xml",
                )
                session.add(CarImage(car_id=special_car.id, url=key, is_main=(i == 0), sort_order=i))

        hero_key = "home/zeekr-hero.svg"
        put_object(s3, settings.s3_bucket, hero_key, home_hero_svg(), "image/svg+xml")
        await get_or_create(
            session,
            HomePromo,
            slug="main-zeekr-hero",
            defaults={
                "link_url": "/catalog?brand=zeekr",
                "image_url": hero_key,
                "is_active": True,
                "sort_order": 0,
            },
        )

        about = (await session.execute(select(HomeAbout).limit(1))).scalar_one_or_none()
        if about is None:
            about = HomeAbout(
                description="Electro-avto помогает выбрать электромобиль, гибрид или автомобиль с пробегом под ваш сценарий и бюджет.",
                page_text=ABOUT_TEXT,
                video_url=None,
                is_active=True,
            )
            session.add(about)
            await session.flush()
        about.description = about.description or "Electro-avto помогает выбрать электромобиль, гибрид или автомобиль с пробегом под ваш сценарий и бюджет."
        about.page_text = about.page_text or ABOUT_TEXT
        about.is_active = True

        salon_specs = [
            ("Зона выдачи автомобилей", "#ca0100"),
            ("Клиентский зал", "#1a7f37"),
            ("Шоурум Electro-avto", "#1a3e73"),
        ]
        for order, (label, accent) in enumerate(salon_specs):
            key = f"about/salon/demo-{order + 1}.svg"
            put_object(s3, settings.s3_bucket, key, salon_svg(label, accent), "image/svg+xml")
            photo, _ = await get_or_create(
                session,
                AboutSalonPhoto,
                image_url=key,
                defaults={"alt": label, "is_active": True, "sort_order": order},
            )
            photo.alt = label
            photo.is_active = True
            photo.sort_order = order

        bank_specs = [
            ("СБЕР БАНК", "#1aaf5d"),
            ("ВТБ", "#0a4aa3"),
            ("Альфа-Банк", "#ef3124"),
            ("Газпромбанк", "#1f5fa8"),
        ]
        for order, (name, color) in enumerate(bank_specs):
            key = f"about/banks/{order + 1}.svg"
            put_object(s3, settings.s3_bucket, key, bank_logo_svg(name, color), "image/svg+xml")
            bank, _ = await get_or_create(
                session,
                BankPartner,
                name=name,
                defaults={"logo_url": key, "is_active": True, "sort_order": order},
            )
            bank.logo_url = bank.logo_url or key
            bank.is_active = True
            bank.sort_order = order

        # --- Contacts page (shared phones/addresses with the footer) ---------
        company_blurb = (
            "Мы располагаем огромной торговой площадкой более 5000 квадратных "
            "метров, у нас в наличии не менее 200 автомобилей как отечественного, "
            "так и иностранного производства. В штате автосалона работают настоящие "
            "профессионалы, которые знают особенности каждого конкретного автомобиля."
        )
        contact_info = (await session.execute(select(ContactInfo).limit(1))).scalar_one_or_none()
        if contact_info is None:
            contact_info = ContactInfo(
                about_text=company_blurb,
                footer_about_text=company_blurb,
                is_active=True,
            )
            session.add(contact_info)
            await session.flush()
        contact_info.footer_about_text = contact_info.footer_about_text or company_blurb
        contact_info.is_active = True

        contact_phones = ["+7 (800) 335-54-31", "+7 (495) 522-52-67"]
        for order, value in enumerate(contact_phones):
            phone, _ = await get_or_create(
                session,
                ContactPhone,
                value=value,
                defaults={"is_active": True, "sort_order": order},
            )
            phone.is_active = True
            phone.sort_order = order

        contact_addresses = ["Кыргызстан, г. Бишкек, ул. Лев Толстого 30"]
        for order, value in enumerate(contact_addresses):
            address, _ = await get_or_create(
                session,
                ContactAddress,
                value=value,
                defaults={"is_active": True, "sort_order": order, "show_in_header": order == 0},
            )
            address.is_active = True
            address.sort_order = order

        contact_photo_specs = [
            ("Автосалон", "#1a3e73"),
            ("Шоурум", "#ca0100"),
            ("Зона выдачи", "#1a7f37"),
        ]
        for order, (label, accent) in enumerate(contact_photo_specs):
            key = f"contacts/photos/demo-{order + 1}.svg"
            put_object(s3, settings.s3_bucket, key, salon_svg(label, accent), "image/svg+xml")
            photo, _ = await get_or_create(
                session,
                ContactPhoto,
                image_url=key,
                defaults={"alt": label, "is_active": True, "sort_order": order},
            )
            photo.alt = label
            photo.is_active = True
            photo.sort_order = order

        requisite_specs = [
            ("Полное название организации", 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ARENDA"'),
            ("Английское название", 'ООО "ARENDA"'),
            ("Адрес", "Красноярский кр., г. Красноярск, ул. Молокова, д. 56 стр. 1"),
            ("Уставный капитал", "10 000"),
            ("ОКФС", "Частная собственность"),
            ("ОКОПФ", "Общества с ограниченной ответственностью"),
            ("ИНН", "2463087637"),
            ("ОГРН", "1072463005537"),
            ("КПП", "246501001"),
            ("ОКАТО", "Красноярский край, Красноярск, Советский"),
            ("ОКПО", "81213568"),
            ("ОКТМО", "Красноярский край, Городские округа Красноярского края, г Красноярск"),
        ]
        for order, (label, value) in enumerate(requisite_specs):
            req, _ = await get_or_create(
                session,
                Requisite,
                label=label,
                defaults={"value": value, "is_active": True, "sort_order": order},
            )
            req.value = req.value or value
            req.is_active = True
            req.sort_order = order

        social_specs = [
            ("tiktok", "#"),
            ("telegram", "#"),
            ("instagram", "#"),
            ("whatsapp", "#"),
            ("phone", "tel:+78005519431"),
        ]
        for order, (kind, url) in enumerate(social_specs):
            social, _ = await get_or_create(
                session,
                SocialLink,
                kind=kind,
                defaults={"url": url, "is_active": True, "sort_order": order},
            )
            social.url = social.url or url
            social.is_active = True
            social.sort_order = order

        zeekr_cars = (
            await session.execute(
                select(Car)
                .join(Model, Car.model_id == Model.id)
                .where(Model.brand_id == brand.id)
                .order_by(Car.price.desc())
                .options(selectinload(Car.images))
                .limit(3)
            )
        ).scalars().all()
        collection_copy = [
            (
                "Флагманские Zeekr",
                "Максимальный запас хода, полный привод и премиальный салон.",
                "/catalog?brand=zeekr&sort=price_desc",
            ),
            (
                "Городские электромобили",
                "Маневренные модели для ежедневных поездок и быстрых зарядок.",
                "/catalog?brand=zeekr&body_type=krossover",
            ),
            (
                "В наличии с ПТС",
                "Автомобили, которые можно забрать быстрее обычного заказа.",
                "/catalog?brand=zeekr",
            ),
        ]
        for order, (title, description, url) in enumerate(collection_copy):
            car = zeekr_cars[order] if order < len(zeekr_cars) else None
            await get_or_create(
                session,
                HomeCollection,
                slug=f"zeekr-home-{order + 1}",
                defaults={
                    "title": title,
                    "description": description,
                    "button_text": "Смотреть",
                    "button_url": url,
                    "image_url": car.images[0].url if car and car.images else None,
                    "car_id": car.id if car else None,
                    "is_active": True,
                    "sort_order": order,
                },
            )

        # --- Spare parts ------------------------------------------------------
        part_categories: dict[str, PartCategory] = {}
        for cat_name, cat_slug in PART_CATEGORIES:
            cat, _ = await get_or_create(
                session, PartCategory, slug=cat_slug, defaults={"name": cat_name}
            )
            part_categories[cat_slug] = cat

        part_bgs = ["#262626", "#1A3E73", "#737373"]
        for (pname, pslug, cat_slug, pcond, pkind, manuf, article,
             pprice, pprice_old) in PARTS:
            part, created = await get_or_create(
                session,
                Part,
                slug=pslug,
                defaults={
                    "name": pname,
                    "category_id": part_categories[cat_slug].id,
                    "brand_id": brand.id,
                    "condition": pcond,
                    "kind": pkind,
                    "manufacturer": manuf,
                    "part_number": article,
                    "price": pprice,
                    "price_old": pprice_old,
                    "benefit_badge": (
                        f"Выгода {int(pprice_old - pprice):,} ₽".replace(",", " ")
                        if pprice_old else None
                    ),
                    "status_text": "В наличии" if pcond == PartCondition.new else "Б/У, проверена",
                    "description": (
                        f"{pname}. Производитель: {manuf}. Артикул: {article}. "
                        "Совместимость и наличие уточняйте у менеджера."
                    ),
                    "in_stock": True,
                    "qty": 5,
                },
            )
            has_images = await session.scalar(
                select(PartImage.id).where(PartImage.part_id == part.id).limit(1)
            )
            if has_images is None:
                for i, bg in enumerate(part_bgs):
                    key = f"parts/{pslug}/{'main' if i == 0 else f'gallery-{i}'}.svg"
                    put_object(s3, settings.s3_bucket, key,
                               placeholder_svg(pname[:22], bg), "image/svg+xml")
                    session.add(PartImage(part_id=part.id, url=key, is_main=(i == 0), sort_order=i))

        await session.commit()

    # Catalog changed — drop every cached selection.
    await bump_catalog_version()
    print(f"Seed done. New cars created: {created_cars}; total Zeekr models: {len(ZEEKR)}.")


if __name__ == "__main__":
    asyncio.run(seed())
