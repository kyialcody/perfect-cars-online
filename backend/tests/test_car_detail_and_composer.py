from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.admin.composer as composer
import app.api.catalog as catalog_api
import app.models  # noqa: F401
from app.db.base import Base
from app.db.deps import get_session
from app.main import app
from app.models.catalog import (
    BodyType,
    Brand,
    Car,
    CarBenefit,
    CarFeature,
    CarGift,
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


class FakeRedis:
    async def get(self, _key):
        return None

    async def set(self, *_args, **_kwargs):
        return None

    async def incr(self, _key):
        return 2


@pytest_asyncio.fixture
async def session_factory(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_session():
        async with factory() as session:
            yield session

    async def _noop(*_args, **_kwargs):
        return None

    async def _version(_redis):
        return 1

    app.dependency_overrides[get_session] = _override_session
    monkeypatch.setattr(catalog_api, "get_redis", lambda: FakeRedis())
    monkeypatch.setattr(catalog_api, "get_catalog_version", _version)
    monkeypatch.setattr(catalog_api, "cache_get_json", _noop)
    monkeypatch.setattr(catalog_api, "cache_set_json", _noop)
    monkeypatch.setattr(composer, "SessionLocal", factory)
    monkeypatch.setattr(composer, "bump_catalog_version", _noop)

    yield factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_car(factory, *, slug="zeekr-9x", is_hidden=False):
    async with factory() as session:
        brand = Brand(name="Zeekr", slug="zeekr", logo_url=None)
        model = Model(name="9X", slug="9x", brand=brand)
        body = BodyType(name="Внедорожник", slug="vnedorozhnik")
        engine = EngineType(name="Электро", slug="electro")
        transmission = Transmission(name="Автомат", slug="avtomat")
        drive = Drive(name="Полный", slug="full")
        black = Color(name="Чёрный", hex="#262626")
        white = Color(name="Белый", hex="#ffffff")
        car = Car(
            slug=slug,
            condition=Condition.new,
            model=model,
            body_type=body,
            engine_type=engine,
            price=Decimal("9900000"),
            price_old=Decimal("10500000"),
            benefit_badge="Выгода",
            status_text="В наличии с ПТС",
            power_hp=1381,
            in_stock=True,
            qty=3,
            is_promo=True,
            is_hidden=is_hidden,
        )
        session.add_all([brand, model, body, engine, transmission, drive, black, white, car])
        await session.flush()
        await session.execute(car_color.insert().values(car_id=car.id, color_id=black.id))
        session.add_all(
            [
                Trim(
                    car_id=car.id,
                    name="Flagship AWD",
                    power_hp=1100,
                    transmission_id=transmission.id,
                    drive_id=drive.id,
                    price=Decimal("9900000"),
                    price_discount=Decimal("9650000"),
                    sort_order=0,
                ),
                CarFeature(car_id=car.id, block=FeatureBlock.safety, text="ADAS", sort_order=0),
                CarGift(car_id=car.id, text="Страхование в подарок", sort_order=0),
                CarBenefit(car_id=car.id, icon="percent", text="Первое", sort_order=0, is_active=True),
            ]
        )
        await session.commit()
        return car.id, white.id, transmission.id, drive.id


@pytest.mark.asyncio
async def test_car_detail_returns_active_benefits_sorted(session_factory):
    await _seed_car(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/cars/zeekr-9x")

    assert response.status_code == 200
    data = response.json()
    assert [item["text"] for item in data["benefits"]] == ["Первое"]
    assert data["trims"][0]["name"] == "Flagship AWD"
    assert data["features"][0]["block"] == "safety"


class FakeForm(dict):
    def getlist(self, key):
        value = self.get(key, [])
        return value if isinstance(value, list) else [value]


async def _existing_ids(factory):
    async with factory() as session:
        car = (await session.execute(select(Car).where(Car.slug == "zeekr-9x"))).scalar_one()
        trim_id = (await session.execute(select(Trim.id).where(Trim.car_id == car.id))).scalar_one()
        return car.id, trim_id


@pytest.mark.asyncio
async def test_form_save_edits_car_and_children(session_factory):
    car_id, white_id, transmission_id, drive_id = await _seed_car(session_factory)
    _, trim_id = await _existing_ids(session_factory)

    form = FakeForm(
        {
            "car_id": str(car_id),
            "slug": "zeekr-9x",
            "model_id": "",  # keep existing model
            "price": "9800000",
            "qty": "5",
            "in_stock": "1",
            "is_promo": "0",
            "color_ids": [str(white_id)],  # swap colour set to white only
            # one existing trim (edit price) + one brand-new trim
            "trim_count": "2",
            "trim_id_0": str(trim_id),
            "trim_name_0": "Flagship AWD",
            "trim_price_0": "9700000",
            "trim_sort_0": "0",
            "trim_transmission_0": str(transmission_id),
            "trim_drive_0": str(drive_id),
            "trim_id_1": "",
            "trim_name_1": "Standard RWD",
            "trim_price_1": "8000000",
            "trim_sort_1": "1",
            "benefit_count": "0",
            "gift_count": "0",
            "feature_count": "0",
            "image_count": "0",
            "images": [],
        }
    )

    response = await composer.save_card(form)
    assert response.status_code == 200

    async with session_factory() as session:
        car = (await session.execute(select(Car).where(Car.id == car_id))).scalar_one()
        assert car.is_hidden is False  # editing never hides a live car
        assert car.price == Decimal("9800000")
        assert car.qty == 5
        trims = (
            await session.execute(select(Trim).where(Trim.car_id == car_id).order_by(Trim.sort_order))
        ).scalars().all()
        assert [t.name for t in trims] == ["Flagship AWD", "Standard RWD"]
        assert trims[0].price == Decimal("9700000")
        colors = (
            await session.execute(select(car_color.c.color_id).where(car_color.c.car_id == car_id))
        ).scalars().all()
        assert colors == [white_id]


@pytest.mark.asyncio
async def test_form_creates_car_visible_on_site(session_factory):
    # Seed gives us a brand/model/refs to select from.
    _, white_id, transmission_id, drive_id = await _seed_car(session_factory)
    async with session_factory() as session:
        model_id = (await session.execute(select(Model.id))).scalars().first()

    form = FakeForm(
        {
            "car_id": "",  # create
            "slug": "zeekr-7x",
            "condition": "new",
            "model_id": str(model_id),
            "price": "5500000",
            "qty": "2",
            "in_stock": "1",
            "is_promo": "0",
            "color_ids": [str(white_id)],
            "trim_count": "1",
            "trim_id_0": "",
            "trim_name_0": "Base",
            "trim_price_0": "5500000",
            "trim_transmission_0": str(transmission_id),
            "trim_drive_0": str(drive_id),
            "benefit_count": "0",
            "gift_count": "0",
            "feature_count": "0",
            "image_count": "0",
            "images": [],
        }
    )
    response = await composer.save_card(form)
    assert response.status_code == 200

    async with session_factory() as session:
        car = (await session.execute(select(Car).where(Car.slug == "zeekr-7x"))).scalar_one()
        assert car.is_hidden is False  # new cars are live immediately
        assert car.price == Decimal("5500000")
        trim = (await session.execute(select(Trim).where(Trim.car_id == car.id))).scalar_one()
        assert trim.name == "Base"

    # And it's reachable on the public site straight away.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/cars/zeekr-7x")).status_code == 200


@pytest.mark.asyncio
async def test_form_create_requires_model(session_factory):
    await _seed_car(session_factory)
    form = FakeForm(
        {
            "car_id": "",
            "slug": "no-model",
            "condition": "new",
            "model_id": "",  # missing
            "price": "1000000",
        }
    )
    response = await composer.save_card(form)
    assert response.status_code == 400
    async with session_factory() as session:
        assert (await session.execute(select(Car).where(Car.slug == "no-model"))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_form_sets_per_trim_photo(session_factory, monkeypatch):
    import io

    from starlette.datastructures import UploadFile

    car_id, white_id, *_ = await _seed_car(session_factory)
    _, trim_id = await _existing_ids(session_factory)

    async def _fake_store(upload, slug, order, *, name="photo"):
        return f"catalog/{slug}/{name}-{order}.jpg"

    monkeypatch.setattr(composer, "_store_upload", _fake_store)

    form = FakeForm(
        {
            "car_id": str(car_id),
            "slug": "zeekr-9x",
            "price": "9900000",
            "qty": "3",
            "color_ids": [str(white_id)],
            "trim_count": "1",
            "trim_id_0": str(trim_id),
            "trim_name_0": "Flagship AWD",
            "trim_price_0": "9900000",
            "trim_image_0": UploadFile(filename="banner.jpg", file=io.BytesIO(b"x")),
            "benefit_count": "0",
            "gift_count": "0",
            "feature_count": "0",
            "image_count": "0",
            "images": [],
        }
    )
    response = await composer.save_card(form)
    assert response.status_code == 200
    async with session_factory() as session:
        trim = (await session.execute(select(Trim).where(Trim.id == trim_id))).scalar_one()
        assert trim.image_url == "catalog/zeekr-9x/trim-0.jpg"


@pytest.mark.asyncio
async def test_form_sets_card_image_and_color_banner(session_factory, monkeypatch):
    import io

    from starlette.datastructures import UploadFile

    car_id, white_id, *_ = await _seed_car(session_factory)

    async def _fake_store(upload, slug, order, *, name="photo"):
        return f"catalog/{slug}/{name}-{order}.jpg"

    monkeypatch.setattr(composer, "_store_upload", _fake_store)

    form = FakeForm(
        {
            "car_id": str(car_id),
            "slug": "zeekr-9x",
            "price": "9900000",
            "color_ids": [str(white_id)],
            "card_image": UploadFile(filename="card.jpg", file=io.BytesIO(b"x")),
            # banner picture for the chosen colour
            f"color_image_{white_id}": UploadFile(filename="white.jpg", file=io.BytesIO(b"y")),
            "trim_count": "0",
            "benefit_count": "0",
            "gift_count": "0",
            "feature_count": "0",
            "image_count": "0",
            "images": [],
        }
    )
    assert (await composer.save_card(form)).status_code == 200
    async with session_factory() as session:
        car = await session.get(Car, car_id)
        assert car.card_image_url == "catalog/zeekr-9x/card_image-0.jpg"
        banner = (
            await session.execute(
                select(car_color.c.image_url).where(
                    car_color.c.car_id == car_id, car_color.c.color_id == white_id
                )
            )
        ).scalar_one()
        assert banner == f"catalog/zeekr-9x/color-{white_id}.jpg"

    # The detail API surfaces the catalog image and the colour's banner.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        data = (await client.get("/cars/zeekr-9x")).json()
    assert data["image_url"].endswith("card_image-0.jpg")
    white = next(c for c in data["colors"] if c["name"] == "Белый")
    assert white["image_url"].endswith(f"color-{white_id}.jpg")


@pytest.mark.asyncio
async def test_form_requires_a_colour(session_factory):
    car_id, *_ = await _seed_car(session_factory)
    form = FakeForm(
        {
            "car_id": str(car_id),
            "slug": "zeekr-9x",
            "price": "9900000",
            "trim_count": "0",
            "benefit_count": "0",
            "gift_count": "0",
            "feature_count": "0",
            "image_count": "0",
            "images": [],
        }
    )
    # No color_ids → rejected (the banner needs at least one colour).
    assert (await composer.save_card(form)).status_code == 400


@pytest.mark.asyncio
async def test_form_creates_used_car_without_colour_banner(session_factory):
    # Used detail pages render a plain gallery, not a colour hero banner.
    _, _, transmission_id, drive_id = await _seed_car(session_factory)
    async with session_factory() as session:
        model_id = (await session.execute(select(Model.id))).scalars().first()

    form = FakeForm(
        {
            "car_id": "",
            "slug": "zeekr-009-used-admin",
            "condition": "used",
            "model_id": str(model_id),
            "price": "20500000",
            "price_old": "21900000",
            "year": "2025",
            "mileage": "12000",
            "drive_id": str(drive_id),
            "transmission_id": str(transmission_id),
            "power_hp": "790",
            "qty": "1",
            "in_stock": "1",
            "is_promo": "0",
            "trim_count": "0",
            "benefit_count": "0",
            "gift_count": "0",
            "feature_count": "0",
            "image_count": "0",
            "images": [],
        }
    )
    response = await composer.save_card(form)
    assert response.status_code == 200

    async with session_factory() as session:
        car = (
            await session.execute(select(Car).where(Car.slug == "zeekr-009-used-admin"))
        ).scalar_one()
        assert car.condition == Condition.used
        assert car.price == Decimal("20500000")
        assert car.year == 2025
        assert car.mileage == 12000
        assert car.drive_id == drive_id
        assert car.transmission_id == transmission_id
        colors = (
            await session.execute(select(car_color.c.color_id).where(car_color.c.car_id == car.id))
        ).scalars().all()
        assert colors == []


@pytest.mark.asyncio
async def test_form_saves_zero_qty(session_factory):
    # Regression: qty=0 (sold out) must persist, not silently revert.
    car_id, white_id, *_ = await _seed_car(session_factory)
    form = FakeForm(
        {
            "car_id": str(car_id),
            "slug": "zeekr-9x",
            "price": "9900000",
            "qty": "0",
            "color_ids": [str(white_id)],
            "trim_count": "0",
            "benefit_count": "0",
            "gift_count": "0",
            "feature_count": "0",
            "image_count": "0",
            "images": [],
        }
    )
    response = await composer.save_card(form)
    assert response.status_code == 200
    async with session_factory() as session:
        assert (await session.get(Car, car_id)).qty == 0


@pytest.mark.asyncio
async def test_form_can_delete_trim(session_factory):
    car_id, white_id, *_ = await _seed_car(session_factory)
    _, trim_id = await _existing_ids(session_factory)

    form = FakeForm(
        {
            "car_id": str(car_id),
            "slug": "zeekr-9x",
            "price": "9900000",
            "qty": "3",
            "color_ids": [str(white_id)],
            "trim_count": "1",
            "trim_id_0": str(trim_id),
            "trim_name_0": "Flagship AWD",
            "trim_price_0": "9900000",
            "trim_delete_0": "on",
            "benefit_count": "0",
            "gift_count": "0",
            "feature_count": "0",
            "image_count": "0",
            "images": [],
        }
    )
    response = await composer.save_card(form)
    assert response.status_code == 200
    async with session_factory() as session:
        trims = (await session.execute(select(Trim).where(Trim.car_id == car_id))).scalars().all()
        assert trims == []


@pytest.mark.asyncio
async def test_form_rejects_duplicate_slug(session_factory):
    car_id, *_ = await _seed_car(session_factory)
    # A second car owning the target slug.
    async with session_factory() as session:
        model_id = (await session.execute(select(Car.model_id).where(Car.id == car_id))).scalar_one()
        session.add(Car(slug="taken", condition=Condition.new, model_id=model_id, price=Decimal("1")))
        await session.commit()

    form = FakeForm({"car_id": str(car_id), "slug": "taken", "price": "9900000"})
    response = await composer.save_card(form)
    assert response.status_code == 409
    async with session_factory() as session:
        car = (await session.execute(select(Car).where(Car.id == car_id))).scalar_one()
        assert car.slug == "zeekr-9x"


@pytest.mark.asyncio
async def test_toggle_visibility_flips_hidden(session_factory):
    car_id, *_ = await _seed_car(session_factory, is_hidden=False)

    hide = await composer.toggle_visibility(FakeForm({"car_id": str(car_id)}))
    assert hide.status_code == 303
    async with session_factory() as session:
        assert (await session.get(Car, car_id)).is_hidden is True

    show = await composer.toggle_visibility(FakeForm({"car_id": str(car_id)}))
    assert show.status_code == 303
    async with session_factory() as session:
        assert (await session.get(Car, car_id)).is_hidden is False


@pytest.mark.asyncio
async def test_delete_car_removes_it(session_factory):
    car_id, *_ = await _seed_car(session_factory)
    response = await composer.delete_car(FakeForm({"car_id": str(car_id)}))
    assert response.status_code == 303
    async with session_factory() as session:
        assert await session.get(Car, car_id) is None
        # Children are gone too (cascade).
        trims = (await session.execute(select(Trim).where(Trim.car_id == car_id))).scalars().all()
        assert trims == []
