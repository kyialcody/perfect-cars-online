"""Single-form «Авто» screen for the admin (issue #72, R1 refactor).

A car *is* its public card — the admin manages everything (hero fields, colours,
trims, benefits, gifts, spec features, photos and visibility) on one page that
mirrors the public card top-to-bottom. There is no draft stage and no separate
«сборщик»: creating a car publishes it immediately (visible unless hidden), and
the same form edits it afterwards.

Reference values (model, body type, engine, transmission, drive, colour) are
only *selected* here — add new ones in the Справочники section first. Every
write bumps the catalog cache so the public site reflects edits immediately.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from html import escape
from secrets import token_urlsafe

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqladmin import BaseView, expose
from starlette.datastructures import UploadFile

from app.admin.auth import ADMIN_SESSION_KEY
from app.core.cache import bump_catalog_version
from app.core.config import get_settings
from app.core.storage import get_s3_client, public_url, put_object
from app.db.session import SessionLocal
from app.models.catalog import (
    BodyType,
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
from app.models.user import User

CSRF_SESSION_KEY = "car_form_csrf"
BENEFIT_ICONS = ("percent", "trade", "gift", "shield")
SPARE_ROWS = 3  # blank rows rendered after existing ones for adding new entries
CONDITIONS = (
    (Condition.new, "Новое"),
    (Condition.used, "С пробегом"),
    (Condition.special, "Спецпредложение"),
)


# --- tiny parsers ------------------------------------------------------------


def _decimal(raw: str | None, default: Decimal | None = None) -> Decimal | None:
    value = (raw or "").strip().replace(" ", "").replace(",", ".")
    if not value:
        return default
    try:
        return Decimal(value)
    except InvalidOperation:
        return default


def _int(raw: str | None, default: int | None = None) -> int | None:
    # All numeric fields here (qty, power, sort_order, ids…) are non-negative,
    # so a non-digit string (incl. "-5") falls back to the default.
    value = (raw or "").strip()
    return int(value) if value.isdigit() else default


def _bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw in {"1", "true", "on", "yes"}


def _ids(form, name: str) -> set[int]:
    out: set[int] = set()
    for value in form.getlist(name):
        try:
            out.add(int(value))
        except (TypeError, ValueError):
            continue
    return out


def _money(value: Decimal | None) -> str:
    if value is None:
        return ""
    return str(value.quantize(Decimal("1"))) if value == value.to_integral() else str(value)


def _car_title(car: Car) -> str:
    brand = car.model.brand.name if car.model and car.model.brand else ""
    model = car.model.name if car.model else "Авто"
    return f"{brand} {model}".strip()


def _condition_label(condition: Condition) -> str:
    return dict(CONDITIONS).get(condition, condition.value)


# --- auth / csrf -------------------------------------------------------------


def _new_csrf_token(request: Request) -> str:
    token = token_urlsafe(32)
    request.session[CSRF_SESSION_KEY] = token
    return token


async def _is_valid_csrf(request: Request, form) -> bool:
    token = str(form.get("csrf_token") or "")
    expected = request.session.get(CSRF_SESSION_KEY)
    return bool(token and expected and token == expected)


async def _is_admin_session(request: Request) -> bool:
    user_id = request.session.get(ADMIN_SESSION_KEY)
    if not user_id:
        return False
    try:
        user_pk = int(user_id)
    except (TypeError, ValueError):
        return False
    async with SessionLocal() as session:
        user = await session.get(User, user_pk)
    return bool(user and user.is_active and user.is_admin)


# --- storage -----------------------------------------------------------------


async def _store_upload(upload: UploadFile, car_slug: str, order: int, *, name: str = "photo") -> str | None:
    content = await upload.read()
    if not content:
        return None
    ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else "bin"
    key = f"catalog/{car_slug}/{name}-{order}.{ext}"
    settings = get_settings()
    # boto3 put_object is blocking — keep it off the event loop.
    await run_in_threadpool(
        put_object,
        get_s3_client(),
        settings.s3_bucket,
        key,
        content,
        upload.content_type or "application/octet-stream",
    )
    return key


# --- page chrome -------------------------------------------------------------


def _page(content: str, *, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>Авто</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #f6f7f8; color: #262626; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px; }}
    a {{ color: #ca0100; }}
    h1 {{ margin: 0 0 6px; }}
    h2 {{ margin: 26px 0 12px; font-size: 20px; }}
    form {{ display: grid; gap: 18px; }}
    fieldset {{ display: grid; gap: 12px; border: 1px solid #ddd; border-radius: 8px; background: #fff; padding: 18px; }}
    legend {{ font-weight: 700; padding: 0 8px; }}
    label {{ display: grid; gap: 6px; font-size: 13px; color: #737373; }}
    input, select {{ width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1px solid #ddd; border-radius: 6px; font: inherit; color: #262626; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .checks {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px 14px; }}
    .checks label {{ flex-direction: row; align-items: flex-start; gap: 8px; color: #262626; }}
    .checks input {{ width: auto; margin-top: 2px; }}
    .row {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; align-items: end; border-top: 1px dashed #eee; padding-top: 10px; }}
    .row .del {{ flex-direction: row; align-items: center; gap: 6px; color: #ca0100; }}
    .row .del input {{ width: auto; }}
    .carousel {{ display: flex; gap: 12px; overflow-x: auto; scroll-snap-type: x mandatory; padding-bottom: 8px; }}
    .photo {{ flex: 0 0 150px; scroll-snap-align: start; border: 1px solid #eee; border-radius: 8px; padding: 8px; display: grid; gap: 6px; background: #fff; }}
    .photo img {{ width: 100%; height: 90px; object-fit: cover; border-radius: 6px; background: #f0f0f0; }}
    .photo-line {{ flex-direction: row; align-items: center; gap: 6px; color: #262626; font-size: 12px; }}
    .photo input {{ width: 48px; }}
    .photo input[type="radio"], .photo input[type="checkbox"] {{ width: auto; }}
    .trim-thumb {{ display: block; width: 100%; height: 56px; object-fit: contain; border-radius: 6px; background: #f0f0f0; margin-bottom: 4px; }}
    .img-field {{ display: grid; gap: 6px; align-content: start; }}
    .img-field .del {{ margin-top: 2px; }}
    .color-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .color-grid .img-field {{ border: 1px solid #eee; border-radius: 8px; padding: 10px; }}
    .color-head {{ flex-direction: row; align-items: center; gap: 8px; color: #262626; }}
    .color-head input {{ width: auto; }}
    .swatch {{ display: inline-block; width: 16px; height: 16px; border-radius: 50%; box-shadow: 0 0 0 1px #ddd; }}
    .hint {{ margin: 0; color: #737373; font-size: 12px; }}
    .actions {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
    button {{ border: 0; border-radius: 8px; background: #ca0100; color: #fff; padding: 12px 22px; font: inherit; font-weight: 700; cursor: pointer; }}
    .button-secondary {{ background: #262626; }}
    .btn-link {{ display: inline-block; text-decoration: none; background: #262626; color: #fff; padding: 10px 18px; border-radius: 8px; font-weight: 700; }}
    .btn-link.primary {{ background: #ca0100; }}
    .topbar {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; }}
    .inline-form {{ display: inline; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
    th {{ background: #fafafa; color: #737373; font-size: 12px; text-transform: uppercase; }}
    td form {{ display: inline; }}
    td button {{ padding: 6px 12px; font-size: 13px; }}
    .tag {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; }}
    .tag-on {{ background: #e7f7ec; color: #138a36; }}
    .tag-off {{ background: #fde8e8; color: #ca0100; }}
    @media (max-width: 760px) {{ .grid, .checks, .row {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body><main>{content}</main></body>
</html>
        """,
        status_code=status_code,
    )


# --- option / row renderers --------------------------------------------------


def _options(items, selected_id: int | None, *, blank: str | None = None) -> str:
    parts = []
    if blank is not None:
        parts.append(f'<option value="">{escape(blank)}</option>')
    for item in items:
        sel = "selected" if item.id == selected_id else ""
        parts.append(f'<option value="{item.id}" {sel}>{escape(item.name)}</option>')
    return "\n".join(parts)


def _condition_options(selected: Condition) -> str:
    return "\n".join(
        f'<option value="{c.value}" {"selected" if c == selected else ""}>{escape(label)}</option>'
        for c, label in CONDITIONS
    )


def _color_rows(colors: list[Color], color_images: dict[int, str | None]) -> str:
    """One card per reference colour: activate it + upload its banner picture.

    ``color_images`` maps the car's activated colour ids to their stored banner
    key (so we can pre-check the box and show the current picture).
    """
    if not colors:
        return '<p class="hint">Цвета ещё не созданы в справочнике.</p>'
    cards = []
    for c in colors:
        checked = "checked" if c.id in color_images else ""
        key = color_images.get(c.id)
        preview = (
            f'<img class="trim-thumb" src="{escape(public_url(key) or "")}" alt="">' if key else ""
        )
        cards.append(
            f"""
<div class="img-field">
  <label class="color-head"><input type="checkbox" name="color_ids" value="{c.id}" {checked}>
    <span class="swatch" style="background:{escape(c.hex)}"></span>{escape(c.name)}</label>
  {preview}
  <label>Баннер цвета <input type="file" name="color_image_{c.id}" accept="image/*"></label>
</div>
            """
        )
    return f'<div class="color-grid">{"".join(cards)}</div>'


def _single_image_field(name: str, label: str, current_key: str | None) -> str:
    """An upload field for one dedicated image: preview + «убрать» + file input.

    Wrapped in one ``.img-field`` cell so the «убрать» checkbox stays under its
    own field instead of spilling into the next grid column.
    """
    preview = ""
    remove = ""
    if current_key:
        preview = f'<img class="trim-thumb" src="{escape(public_url(current_key) or "")}" alt="">'
        remove = f'<label class="del"><input type="checkbox" name="{name}_delete">убрать</label>'
    return (
        f'<div class="img-field"><label>{escape(label)} {preview}'
        f'<input name="{name}" type="file" accept="image/*"></label>{remove}</div>'
    )


def _trim_photo_cell(t, i: int) -> str:
    """Per-trim photo: current preview (+ remove) and an upload field."""
    preview = ""
    remove = ""
    if t and t.image_url:
        preview = f'<img class="trim-thumb" src="{escape(public_url(t.image_url) or "")}" alt="">'
        remove = (
            f'<label class="del"><input type="checkbox" name="trim_image_delete_{i}">убрать фото</label>'
        )
    return (
        f'<div class="img-field"><label>Фото комплектации {preview}'
        f'<input name="trim_image_{i}" type="file" accept="image/*">'
        f'<span class="hint">640×360 px (16:9)</span></label>{remove}</div>'
    )


def _trim_rows(trims, transmissions, drives) -> str:
    rows = []
    items = sorted(trims, key=lambda t: (t.sort_order, t.id))
    for i in range(len(items) + SPARE_ROWS):
        t = items[i] if i < len(items) else None
        tid = t.id if t else ""
        rows.append(
            f"""
<div class="row">
  <input type="hidden" name="trim_id_{i}" value="{tid}">
  <label>Комплектация <input name="trim_name_{i}" value="{escape(t.name) if t else ''}"></label>
  <label>Объём, л <input name="trim_engine_volume_{i}" value="{_money(t.engine_volume) if t else ''}"></label>
  <label>Мощность, л.с. <input name="trim_power_hp_{i}" value="{t.power_hp if t and t.power_hp else ''}"></label>
  <label>КПП <select name="trim_transmission_{i}">{_options(transmissions, t.transmission_id if t else None, blank='—')}</select></label>
  <label>Привод <select name="trim_drive_{i}">{_options(drives, t.drive_id if t else None, blank='—')}</select></label>
  <label>Цена <input name="trim_price_{i}" value="{_money(t.price) if t else ''}"></label>
  <label>Цена со скидкой <input name="trim_price_discount_{i}" value="{_money(t.price_discount) if t else ''}"></label>
  <label>Порядок <input name="trim_sort_{i}" value="{t.sort_order if t else i}"></label>
  {_trim_photo_cell(t, i)}
  {'<label class="del"><input type="checkbox" name="trim_delete_' + str(i) + '">удалить</label>' if t else ''}
</div>
            """
        )
    return f'<input type="hidden" name="trim_count" value="{len(items) + SPARE_ROWS}">' + "".join(rows)


def _benefit_rows(benefits) -> str:
    rows = []
    items = sorted(benefits, key=lambda b: (b.sort_order, b.id))
    for i in range(len(items) + SPARE_ROWS):
        b = items[i] if i < len(items) else None
        bid = b.id if b else ""
        icon_opts = "\n".join(
            f'<option value="{ic}" {"selected" if b and b.icon == ic else ""}>{ic}</option>'
            for ic in BENEFIT_ICONS
        )
        rows.append(
            f"""
<div class="row">
  <input type="hidden" name="benefit_id_{i}" value="{bid}">
  <label>Иконка <select name="benefit_icon_{i}">{icon_opts}</select></label>
  <label>Текст <input name="benefit_text_{i}" value="{escape(b.text) if b else ''}"></label>
  <label>Порядок <input name="benefit_sort_{i}" value="{b.sort_order if b else i}"></label>
  <label class="del"><input type="checkbox" name="benefit_active_{i}" {'checked' if (b is None or b.is_active) else ''}>активно</label>
  {'<label class="del"><input type="checkbox" name="benefit_delete_' + str(i) + '">удалить</label>' if b else ''}
</div>
            """
        )
    return f'<input type="hidden" name="benefit_count" value="{len(items) + SPARE_ROWS}">' + "".join(rows)


def _gift_rows(gifts) -> str:
    rows = []
    items = sorted(gifts, key=lambda g: (g.sort_order, g.id))
    for i in range(len(items) + SPARE_ROWS):
        g = items[i] if i < len(items) else None
        gid = g.id if g else ""
        rows.append(
            f"""
<div class="row">
  <input type="hidden" name="gift_id_{i}" value="{gid}">
  <label>Подарок <input name="gift_text_{i}" value="{escape(g.text) if g else ''}"></label>
  <label>Порядок <input name="gift_sort_{i}" value="{g.sort_order if g else i}"></label>
  {'<label class="del"><input type="checkbox" name="gift_delete_' + str(i) + '">удалить</label>' if g else ''}
</div>
            """
        )
    return f'<input type="hidden" name="gift_count" value="{len(items) + SPARE_ROWS}">' + "".join(rows)


def _feature_rows(features) -> str:
    rows = []
    items = sorted(features, key=lambda f: (f.sort_order, f.id))
    blocks = list(FeatureBlock)
    for i in range(len(items) + SPARE_ROWS):
        f = items[i] if i < len(items) else None
        fid = f.id if f else ""
        block_opts = "\n".join(
            f'<option value="{blk.value}" {"selected" if f and f.block == blk else ""}>{blk.value}</option>'
            for blk in blocks
        )
        rows.append(
            f"""
<div class="row">
  <input type="hidden" name="feature_id_{i}" value="{fid}">
  <label>Блок <select name="feature_block_{i}">{block_opts}</select></label>
  <label>Текст <input name="feature_text_{i}" value="{escape(f.text) if f else ''}"></label>
  <label>Порядок <input name="feature_sort_{i}" value="{f.sort_order if f else i}"></label>
  {'<label class="del"><input type="checkbox" name="feature_delete_' + str(i) + '">удалить</label>' if f else ''}
</div>
            """
        )
    return f'<input type="hidden" name="feature_count" value="{len(items) + SPARE_ROWS}">' + "".join(rows)


def _image_rows(images) -> str:
    items = sorted(images, key=lambda im: (not im.is_main, im.sort_order, im.id))
    if not items:
        strip = '<p class="hint">Фото ещё нет. Загрузите ниже.</p>'
    else:
        # Compact horizontal carousel so many photos don't stretch the page.
        cards = "".join(
            f"""
<div class="photo">
  <input type="hidden" name="image_id_{i}" value="{im.id}">
  <img src="{escape(public_url(im.url) or '')}" alt="">
  <label class="photo-line">Порядок <input name="image_sort_{i}" value="{im.sort_order}"></label>
  <label class="photo-line"><input type="radio" name="main_image" value="{im.id}" {'checked' if im.is_main else ''}>главное</label>
  <label class="photo-line"><input type="checkbox" name="image_delete_{i}">удалить</label>
</div>
            """
            for i, im in enumerate(items)
        )
        strip = f'<div class="carousel">{cards}</div>'
    return (
        f'<input type="hidden" name="image_count" value="{len(items)}">'
        + strip
        + '<label>Добавить фото <input name="images" type="file" multiple accept="image/*"></label>'
    )


# --- data loading ------------------------------------------------------------


async def _load_car(session, car_id: int) -> Car | None:
    return await session.get(
        Car,
        car_id,
        options=[
            selectinload(Car.model).selectinload(Model.brand),
            selectinload(Car.colors),
            selectinload(Car.trims),
            selectinload(Car.images),
            selectinload(Car.gifts),
            selectinload(Car.benefits),
            selectinload(Car.features),
        ],
    )


async def _load_refs(session):
    models = (await session.execute(select(Model).options(selectinload(Model.brand)).order_by(Model.name))).scalars().all()
    body_types = (await session.execute(select(BodyType).order_by(BodyType.name))).scalars().all()
    engine_types = (await session.execute(select(EngineType).order_by(EngineType.name))).scalars().all()
    transmissions = (await session.execute(select(Transmission).order_by(Transmission.name))).scalars().all()
    drives = (await session.execute(select(Drive).order_by(Drive.name))).scalars().all()
    colors = (await session.execute(select(Color).order_by(Color.name))).scalars().all()
    return models, body_types, engine_types, transmissions, drives, colors


def _model_options(models, selected_id):
    return '<option value="">— выберите —</option>' + "\n".join(
        f'<option value="{m.id}" {"selected" if m.id == selected_id else ""}>'
        f'{escape((m.brand.name + " ") if m.brand else "")}{escape(m.name)}</option>'
        for m in models
    )


# --- list --------------------------------------------------------------------


async def render_list(
    request: Request,
    *,
    condition: Condition | None = None,
    list_path: str = "/admin/cars",
    title: str = "Авто",
) -> HTMLResponse:
    csrf = _new_csrf_token(request)
    async with SessionLocal() as session:
        stmt = (
            select(Car)
            .options(selectinload(Car.model).selectinload(Model.brand))
            .order_by(Car.id.desc())
        )
        if condition is not None:
            stmt = stmt.where(Car.condition == condition)
        cars = (await session.execute(stmt)).scalars().all()

        rows = []
        for car in cars:
            visible = not car.is_hidden
            tag = (
                '<span class="tag tag-on">На сайте</span>'
                if visible
                else '<span class="tag tag-off">Скрыто</span>'
            )
            toggle_label = "Скрыть" if visible else "Показать"
            rows.append(
                f"""
<tr>
  <td>#{car.id}</td>
  <td><a href="{list_path}?car_id={car.id}">{escape(_car_title(car))}</a><br>
      <span class="hint">{escape(car.slug)}</span></td>
  <td>{escape(_condition_label(car.condition))}</td>
  <td>{tag}</td>
  <td>{_money(car.price)} ₽</td>
  <td>{car.qty}</td>
  <td>
    <a href="{list_path}?car_id={car.id}">Редактировать</a>
    <form class="inline-form" method="post">
      <input type="hidden" name="csrf_token" value="{escape(csrf)}">
      <input type="hidden" name="action" value="toggle_visibility">
      <input type="hidden" name="car_id" value="{car.id}">
      <input type="hidden" name="list_path" value="{escape(list_path)}">
      <button class="button-secondary" type="submit">{toggle_label}</button>
    </form>
    <form class="inline-form" method="post" onsubmit="return confirm('Удалить авто #{car.id}?');">
      <input type="hidden" name="csrf_token" value="{escape(csrf)}">
      <input type="hidden" name="action" value="delete">
      <input type="hidden" name="car_id" value="{car.id}">
      <input type="hidden" name="list_path" value="{escape(list_path)}">
      <button type="submit">Удалить</button>
    </form>
  </td>
</tr>
                """
            )
        body = "".join(rows) or '<tr><td colspan="7" class="hint">Авто ещё нет.</td></tr>'

    content = f"""
<h1>{escape(title)}</h1>
<div class="topbar">
  <a class="btn-link" href="/admin">← В админку</a>
  <a class="btn-link primary" href="{list_path}?new=1">+ Создать авто</a>
</div>
<table>
  <thead><tr>
    <th>ID</th><th>Авто</th><th>Состояние</th><th>Видимость</th>
    <th>Цена</th><th>Кол-во</th><th>Действия</th>
  </tr></thead>
  <tbody>{body}</tbody>
</table>
    """
    return _page(content)


# --- create / edit form ------------------------------------------------------


async def render_form(
    request: Request,
    *,
    default_condition: Condition = Condition.new,
    list_path: str = "/admin/cars",
) -> HTMLResponse:
    car_id = _int(request.query_params.get("car_id"))
    csrf = _new_csrf_token(request)
    async with SessionLocal() as session:
        car = await _load_car(session, car_id) if car_id else None
        if car_id and car is None:
            return _page("<h1>Авто не найдено</h1>", status_code=404)
        models, body_types, engine_types, transmissions, drives, colors = await _load_refs(session)
        color_images: dict[int, str | None] = {}
        if car:
            rows = (
                await session.execute(
                    select(car_color.c.color_id, car_color.c.image_url).where(
                        car_color.c.car_id == car.id
                    )
                )
            ).all()
            color_images = {cid: img for cid, img in rows}

        title = _car_title(car) if car else "Новое авто"
        condition = car.condition if car else default_condition

        trims_html = _trim_rows(car.trims if car else [], transmissions, drives)
        benefit_html = _benefit_rows(car.benefits if car else [])
        gift_html = _gift_rows(car.gifts if car else [])
        feature_html = _feature_rows(car.features if car else [])
        image_html = _image_rows(car.images if car else [])
        color_html = _color_rows(colors, color_images)

        # The visibility toggle and «open on site» link only make sense once the
        # car exists; a brand-new car has neither yet.
        visibility_block = ""
        if car is not None:
            toggle_label = "Скрыть с сайта" if not car.is_hidden else "Показать на сайте"
            status_note = (
                "Скрыто — карточка убрана с сайта."
                if car.is_hidden
                else "На сайте — карточка видна публично."
            )
            visibility_block = f"""
<p class="hint">{escape(car.slug)} · {escape(status_note)}</p>
<form class="inline-form" method="post">
  <input type="hidden" name="csrf_token" value="{escape(csrf)}">
  <input type="hidden" name="action" value="toggle_visibility">
  <input type="hidden" name="car_id" value="{car.id}">
  <input type="hidden" name="list_path" value="{escape(list_path)}">
  <button class="button-secondary" type="submit">{escape(toggle_label)}</button>
</form>
            """

        car_id_field = f'<input type="hidden" name="car_id" value="{car.id}">' if car else ""
        save_label = "Сохранить" if car else "Создать авто"

        content = f"""
<div class="topbar">
  <a class="btn-link" href="/admin">← В админку</a>
  <a href="{list_path}">К списку авто</a>
</div>
<h1>{escape(title)}</h1>
{visibility_block}

<form method="post" enctype="multipart/form-data">
  <input type="hidden" name="csrf_token" value="{escape(csrf)}">
  <input type="hidden" name="action" value="save">
  <input type="hidden" name="list_path" value="{escape(list_path)}">
  {car_id_field}

  <fieldset>
    <legend>Основное</legend>
    <div class="grid">
      <label>Slug <input name="slug" value="{escape(car.slug) if car else ''}" required></label>
      <label>Состояние <select name="condition">{_condition_options(condition)}</select></label>
      <label>Модель <select name="model_id" required>{_model_options(models, car.model_id if car else None)}</select></label>
      <label>Тип кузова <select name="body_type_id">{_options(body_types, car.body_type_id if car else None, blank='—')}</select></label>
      <label>Тип двигателя <select name="engine_type_id">{_options(engine_types, car.engine_type_id if car else None, blank='—')}</select></label>
      <label>Цена <input name="price" value="{_money(car.price) if car else ''}" required></label>
      <label>Старая цена <input name="price_old" value="{_money(car.price_old) if car else ''}"></label>
      <label>Бейдж выгоды <input name="benefit_badge" value="{escape(car.benefit_badge or '') if car else ''}"></label>
      <label>Статус-текст <input name="status_text" value="{escape(car.status_text or '') if car else ''}"></label>
      <label>Мощность, л.с. <input name="power_hp" value="{(car.power_hp or '') if car else ''}"></label>
      <label class="cond cond-new">Расход электро, кВт·ч <input name="fuel_consumption" value="{_money(car.fuel_consumption) if car else ''}"></label>
      <label class="cond cond-new">Расход топлива, л/100 км <input name="fuel_consumption_petrol" value="{_money(car.fuel_consumption_petrol) if car else ''}"></label>
      <label class="cond cond-new">Разгон 0–100, с <input name="acceleration_0_100" value="{_money(car.acceleration_0_100) if car else ''}"></label>
      <label class="cond cond-new">Макс. скорость <input name="max_speed" value="{(car.max_speed or '') if car else ''}"></label>
      <label class="cond cond-used">Год <input name="year" value="{(car.year or '') if car else ''}"></label>
      <label class="cond cond-used">Пробег, км <input name="mileage" value="{(car.mileage or '') if car else ''}"></label>
      <label class="cond cond-used">Привод <select name="drive_id">{_options(drives, car.drive_id if car else None, blank='—')}</select></label>
      <label class="cond cond-used">КПП <select name="transmission_id">{_options(transmissions, car.transmission_id if car else None, blank='—')}</select></label>
      <label class="cond cond-used">Объём двигателя, л <input name="engine_volume" value="{_money(car.engine_volume) if car else ''}"></label>
      <label>Количество <input name="qty" value="{car.qty if car else 1}"></label>
      <label>В наличии <select name="in_stock"><option value="1" {'selected' if (car is None or car.in_stock) else ''}>Да</option><option value="0" {'selected' if (car and not car.in_stock) else ''}>Нет</option></select></label>
    </div>
  </fieldset>

  <fieldset><legend>Фото для каталога</legend>
    <p class="hint cond cond-new">Превью-карточка в каталоге (независимо от баннеров цветов и галереи).
      <strong>Размер 1000×750 px (4:3)</strong> — иначе фото обрежется.</p>
    <p class="hint cond cond-used">Превью-карточка авто с пробегом в каталоге.
      На детальной странице используются фото из галереи ниже, без отдельного баннера.</p>
    <div class="grid">
      {_single_image_field('card_image', 'Фото в каталоге (превью-карточка)', car.card_image_url if car else None)}
    </div>
  </fieldset>
  <fieldset class="cond cond-new"><legend>Цвета и баннеры</legend>
    <p class="hint">Отметьте минимум один цвет. К каждому отмеченному цвету загрузите
      баннер — он показывается большим вверху карточки при выборе этого цвета.
      <strong>Размер баннера 1440×480 px (3:1)</strong> — иначе фото обрежется.</p>
    {color_html}
  </fieldset>
  <fieldset class="cond cond-new"><legend>Комплектации</legend>{trims_html}</fieldset>
  <fieldset><legend>Преимущества</legend>
    <p class="hint cond cond-used">Для авто с пробегом эти пункты показываются справа от фото, рядом с кнопкой брони.</p>
    <p class="hint cond cond-new">Для новых авто эти пункты используются в карточке/герое.</p>
    {benefit_html}
  </fieldset>
  <fieldset class="cond cond-new"><legend>Подарки</legend>{gift_html}</fieldset>
  <fieldset class="cond cond-new"><legend>Характеристики</legend>{feature_html}</fieldset>
  <fieldset><legend>Фото</legend>
    <p class="hint cond cond-used">Галерея авто с пробегом: главное фото слева на детальной странице, миниатюры под ним.</p>
    {image_html}
  </fieldset>

  <div class="actions">
    <button type="submit">{escape(save_label)}</button>
  </div>
</form>

<script>
  // Show only the fields that make sense for the chosen condition: trims,
  // colour banners and feature blocks for new cars; car-level specs and a
  // plain photo gallery for used ones. Спецпредложения редактируются по той же
  // форме, что и авто с пробегом.
  (function () {{
    var sel = document.querySelector('select[name="condition"]');
    if (!sel) return;
    function apply() {{
      var used = sel.value === 'used' || sel.value === 'special';
      document.querySelectorAll('.cond-new').forEach(function (el) {{
        el.style.display = used ? 'none' : '';
      }});
      document.querySelectorAll('.cond-used').forEach(function (el) {{
        el.style.display = used ? '' : 'none';
      }});
    }}
    sel.addEventListener('change', apply);
    apply();
  }})();
</script>
        """
    return _page(content)


# --- save --------------------------------------------------------------------


async def _sync_trims(car: Car, form, transmissions, drives, *, slug: str) -> None:
    valid_transmissions = {t.id for t in transmissions}
    valid_drives = {d.id for d in drives}
    by_id = {t.id: t for t in car.trims}
    count = _int(str(form.get("trim_count")), 0) or 0
    for i in range(count):
        tid = _int(str(form.get(f"trim_id_{i}")))
        name = str(form.get(f"trim_name_{i}") or "").strip()
        is_existing = bool(tid and tid in by_id)
        if not (is_existing or (not tid and name)):
            continue
        if is_existing and _bool(form.get(f"trim_delete_{i}")):
            car.trims.remove(by_id[tid])
            continue
        # КПП/привод are selected from the справочники; an unknown id clears it.
        transmission_id = _int(str(form.get(f"trim_transmission_{i}")))
        if transmission_id not in valid_transmissions:
            transmission_id = None
        drive_id = _int(str(form.get(f"trim_drive_{i}")))
        if drive_id not in valid_drives:
            drive_id = None
        if is_existing:
            trim = by_id[tid]
            trim.name = name or trim.name
            trim.engine_volume = _decimal(str(form.get(f"trim_engine_volume_{i}")))
            trim.power_hp = _int(str(form.get(f"trim_power_hp_{i}")))
            trim.transmission_id = transmission_id
            trim.drive_id = drive_id
            trim.price = _decimal(str(form.get(f"trim_price_{i}")), trim.price)
            trim.price_discount = _decimal(str(form.get(f"trim_price_discount_{i}")))
            trim.sort_order = _int(str(form.get(f"trim_sort_{i}")), i)
        else:
            trim = Trim(
                name=name,
                engine_volume=_decimal(str(form.get(f"trim_engine_volume_{i}"))),
                power_hp=_int(str(form.get(f"trim_power_hp_{i}"))),
                transmission_id=transmission_id,
                drive_id=drive_id,
                price=_decimal(str(form.get(f"trim_price_{i}")), Decimal("0")),
                price_discount=_decimal(str(form.get(f"trim_price_discount_{i}"))),
                sort_order=_int(str(form.get(f"trim_sort_{i}")), i),
            )
            car.trims.append(trim)

        # Per-trim photo: «убрать фото» clears it; a new upload replaces it.
        if _bool(form.get(f"trim_image_delete_{i}")):
            trim.image_url = None
        upload = form.get(f"trim_image_{i}")
        if isinstance(upload, UploadFile) and upload.filename:
            key = await _store_upload(upload, slug, i, name="trim")
            if key:
                trim.image_url = key


def _sync_benefits(car: Car, form) -> None:
    by_id = {b.id: b for b in car.benefits}
    count = _int(str(form.get("benefit_count")), 0) or 0
    for i in range(count):
        bid = _int(str(form.get(f"benefit_id_{i}")))
        text = str(form.get(f"benefit_text_{i}") or "").strip()
        icon = str(form.get(f"benefit_icon_{i}") or "gift").strip()
        sort = _int(str(form.get(f"benefit_sort_{i}")), i)
        active = _bool(form.get(f"benefit_active_{i}"))
        if bid and bid in by_id:
            b = by_id[bid]
            if _bool(form.get(f"benefit_delete_{i}")):
                car.benefits.remove(b)
                continue
            b.text, b.icon, b.sort_order, b.is_active = text or b.text, icon, sort, active
        elif not bid and text:
            car.benefits.append(CarBenefit(icon=icon, text=text, sort_order=sort, is_active=active))


def _sync_gifts(car: Car, form) -> None:
    by_id = {g.id: g for g in car.gifts}
    count = _int(str(form.get("gift_count")), 0) or 0
    for i in range(count):
        gid = _int(str(form.get(f"gift_id_{i}")))
        text = str(form.get(f"gift_text_{i}") or "").strip()
        sort = _int(str(form.get(f"gift_sort_{i}")), i)
        if gid and gid in by_id:
            g = by_id[gid]
            if _bool(form.get(f"gift_delete_{i}")):
                car.gifts.remove(g)
                continue
            g.text, g.sort_order = text or g.text, sort
        elif not gid and text:
            car.gifts.append(CarGift(text=text, sort_order=sort))


def _sync_features(car: Car, form) -> None:
    by_id = {f.id: f for f in car.features}
    count = _int(str(form.get("feature_count")), 0) or 0
    for i in range(count):
        fid = _int(str(form.get(f"feature_id_{i}")))
        text = str(form.get(f"feature_text_{i}") or "").strip()
        sort = _int(str(form.get(f"feature_sort_{i}")), i)
        try:
            block = FeatureBlock(str(form.get(f"feature_block_{i}") or "safety"))
        except ValueError:
            block = FeatureBlock.safety
        if fid and fid in by_id:
            f = by_id[fid]
            if _bool(form.get(f"feature_delete_{i}")):
                car.features.remove(f)
                continue
            f.text, f.block, f.sort_order = text or f.text, block, sort
        elif not fid and text:
            car.features.append(CarFeature(block=block, text=text, sort_order=sort))


async def _sync_images(session, car: Car, form, *, slug: str) -> None:
    by_id = {im.id: im for im in car.images}
    count = _int(str(form.get("image_count")), 0) or 0
    main_choice = str(form.get("main_image") or "").strip()
    survivors: list[CarImage] = []
    for i in range(count):
        iid = _int(str(form.get(f"image_id_{i}")))
        if not iid or iid not in by_id:
            continue
        im = by_id[iid]
        if _bool(form.get(f"image_delete_{i}")):
            car.images.remove(im)
            continue
        im.sort_order = _int(str(form.get(f"image_sort_{i}")), im.sort_order)
        im.is_main = False
        survivors.append(im)

    # New uploads land after the survivors, never main by default.
    base = len(survivors)
    new_images: list[CarImage] = []
    for offset, upload in enumerate(form.getlist("images")):
        if not (isinstance(upload, UploadFile) and upload.filename):
            continue
        key = await _store_upload(upload, slug, base + offset)
        if key:
            img = CarImage(url=key, is_main=False, sort_order=base + offset)
            car.images.append(img)
            new_images.append(img)

    # Exactly one main: honour the radio choice, else fall back to the first
    # surviving (or first new) image so the card always has a hero photo.
    all_imgs = survivors + new_images
    if not all_imgs:
        return
    # Flush with every image is_main=False first, so setting one True below can't
    # transiently collide with another True row under the partial unique index
    # uq_car_main_image (one main per car).
    await session.flush()
    chosen = next((im for im in survivors if str(im.id) == main_choice), None)
    (chosen or all_imgs[0]).is_main = True


async def save_card(form) -> HTMLResponse:
    car_id = _int(str(form.get("car_id")))
    new_slug = str(form.get("slug") or "").strip()
    if not new_slug:
        return _page("<h1>Ошибка</h1><p>Укажите slug.</p>", status_code=400)

    async with SessionLocal() as session:
        # Slug must stay unique across cars.
        clash_stmt = select(Car.id).where(Car.slug == new_slug)
        if car_id:
            clash_stmt = clash_stmt.where(Car.id != car_id)
        if (await session.execute(clash_stmt)).scalar_one_or_none() is not None:
            return _page(
                f"<h1>Slug занят</h1><p>Авто со slug <strong>{escape(new_slug)}</strong> уже есть.</p>",
                status_code=409,
            )

        models, body_types, engine_types, transmissions, drives, colors = await _load_refs(session)
        valid_models = {m.id for m in models}
        valid_body = {b.id for b in body_types}
        valid_engine = {e.id for e in engine_types}
        valid_colors = {c.id for c in colors}
        valid_drives = {d.id for d in drives}
        valid_transmissions = {t.id for t in transmissions}

        # Condition is optional in the payload: keep the car's current value on
        # edit; a brand-new car defaults to «new».
        condition: Condition | None = None
        raw_condition = str(form.get("condition") or "")
        if raw_condition:
            try:
                condition = Condition(raw_condition)
            except ValueError:
                condition = None

        if car_id:
            car = await _load_car(session, car_id)
            if car is None:
                return _page("<h1>Авто не найдено</h1>", status_code=404)
        else:
            model_id = _int(str(form.get("model_id")))
            if model_id not in valid_models:
                return _page(
                    "<h1>Ошибка</h1><p>Выберите модель из справочника.</p>", status_code=400
                )
            # Assign the child collections empty so they count as «loaded» — a
            # freshly-flushed Car would otherwise lazy-load them in the sync
            # flush context and raise MissingGreenlet.
            car = Car(
                slug=new_slug,
                condition=condition or Condition.new,
                model_id=model_id,
                price=Decimal("0"),
                trims=[],
                images=[],
                gifts=[],
                benefits=[],
                features=[],
            )
            session.add(car)
            await session.flush()  # assign id before children / colour rows

        car.slug = new_slug
        if condition is not None:
            car.condition = condition
        # Reference fields are selected only; an unknown/blank id keeps (edit) or
        # clears (optional) the value.
        model_id = _int(str(form.get("model_id")))
        if model_id in valid_models:
            car.model_id = model_id
        body_type_id = _int(str(form.get("body_type_id")))
        car.body_type_id = body_type_id if body_type_id in valid_body else None
        engine_type_id = _int(str(form.get("engine_type_id")))
        car.engine_type_id = engine_type_id if engine_type_id in valid_engine else None
        car.price = _decimal(str(form.get("price")), car.price)
        car.price_old = _decimal(str(form.get("price_old")))
        car.benefit_badge = str(form.get("benefit_badge") or "").strip() or None
        car.status_text = str(form.get("status_text") or "").strip() or None
        car.power_hp = _int(str(form.get("power_hp")))
        car.fuel_consumption = _decimal(str(form.get("fuel_consumption")))
        car.fuel_consumption_petrol = _decimal(str(form.get("fuel_consumption_petrol")))
        car.acceleration_0_100 = _decimal(str(form.get("acceleration_0_100")))
        car.max_speed = _int(str(form.get("max_speed")))
        car.year = _int(str(form.get("year")))
        car.mileage = _int(str(form.get("mileage")))
        drive_id = _int(str(form.get("drive_id")))
        car.drive_id = drive_id if drive_id in valid_drives else None
        transmission_id = _int(str(form.get("transmission_id")))
        car.transmission_id = transmission_id if transmission_id in valid_transmissions else None
        car.engine_volume = _decimal(str(form.get("engine_volume")))
        car.qty = _int(str(form.get("qty")), car.qty)
        car.in_stock = _bool(form.get("in_stock"), car.in_stock)

        # Catalog preview: «убрать» clears, a new upload replaces.
        if _bool(form.get("card_image_delete")):
            car.card_image_url = None
        card_upload = form.get("card_image")
        if isinstance(card_upload, UploadFile) and card_upload.filename:
            key = await _store_upload(card_upload, new_slug, 0, name="card_image")
            if key:
                car.card_image_url = key

        # Colours + per-colour banners are required only for new cars: the new
        # car detail uses the active colour as its big hero banner. Used-car
        # detail pages now use the regular gallery instead, so they can be saved
        # without colours or colour banners.
        chosen_colors = _ids(form, "color_ids") & valid_colors
        if car.condition == Condition.new and not chosen_colors:
            return _page(
                "<h1>Ошибка</h1><p>Отметьте хотя бы один цвет — к нему привязан баннер карточки.</p>",
                status_code=400,
            )
        existing_imgs = {
            cid: img
            for cid, img in (
                await session.execute(
                    select(car_color.c.color_id, car_color.c.image_url).where(
                        car_color.c.car_id == car.id
                    )
                )
            ).all()
        }
        await session.execute(car_color.delete().where(car_color.c.car_id == car.id))
        for color_id in chosen_colors:
            img = existing_imgs.get(color_id)
            upload = form.get(f"color_image_{color_id}")
            if isinstance(upload, UploadFile) and upload.filename:
                key = await _store_upload(upload, new_slug, color_id, name="color")
                if key:
                    img = key
            await session.execute(
                car_color.insert().values(car_id=car.id, color_id=color_id, image_url=img)
            )

        await _sync_trims(car, form, transmissions, drives, slug=new_slug)
        _sync_benefits(car, form)
        _sync_gifts(car, form)
        _sync_features(car, form)
        await session.flush()  # settle child deletes before image main-uniqueness
        await _sync_images(session, car, form, slug=new_slug)

        await session.commit()
        saved_id = car.id

    await bump_catalog_version()
    list_path = str(form.get("list_path") or "/admin/cars")
    return _page(
        f'<h1>Сохранено</h1><p>'
        f'<a href="{escape(list_path)}?car_id={saved_id}">Вернуться к редактированию</a> · '
        f'<a href="{escape(list_path)}">К списку</a></p>'
    )


async def toggle_visibility(form) -> HTMLResponse:
    car_id = _int(str(form.get("car_id")))
    if not car_id:
        return _page("<h1>Ошибка</h1><p>Не указан автомобиль.</p>", status_code=400)
    async with SessionLocal() as session:
        car = await session.get(Car, car_id)
        if car is None:
            return _page("<h1>Авто не найдено</h1>", status_code=404)
        car.is_hidden = not car.is_hidden
        await session.commit()
    await bump_catalog_version()
    return RedirectResponse(url=str(form.get("list_path") or "/admin/cars"), status_code=303)


async def delete_car(form) -> HTMLResponse:
    car_id = _int(str(form.get("car_id")))
    if not car_id:
        return _page("<h1>Ошибка</h1><p>Не указан автомобиль.</p>", status_code=400)
    async with SessionLocal() as session:
        car = await session.get(Car, car_id)
        if car is None:
            return _page("<h1>Авто не найдено</h1>", status_code=404)
        await session.delete(car)
        await session.commit()
    await bump_catalog_version()
    return RedirectResponse(url=str(form.get("list_path") or "/admin/cars"), status_code=303)


async def _handle_car_request(
    request: Request,
    *,
    condition: Condition | None,
    list_path: str,
    title: str,
):
    """Shared GET/POST handler for the «Авто» and «Авто с пробегом» screens.

    ``condition`` filters the list and defaults the create form; the redirect
    target travels in the form's ``list_path`` field so saves return to the
    screen you came from.
    """
    if not await _is_admin_session(request):
        return RedirectResponse(url="/admin/login", status_code=302)
    if request.method == "POST":
        form = await request.form()
        if not await _is_valid_csrf(request, form):
            return _page(
                "<h1>Ошибка</h1><p>Сессия формы устарела. Откройте страницу заново.</p>",
                status_code=403,
            )
        action = str(form.get("action"))
        if action == "toggle_visibility":
            return await toggle_visibility(form)
        if action == "delete":
            return await delete_car(form)
        return await save_card(form)
    # GET: form for create (?new=1) / edit (?car_id=), else the list.
    if request.query_params.get("new") or request.query_params.get("car_id"):
        return await render_form(
            request,
            default_condition=condition or Condition.new,
            list_path=list_path,
        )
    return await render_list(request, condition=condition, list_path=list_path, title=title)


class CarView(BaseView):
    name = "Авто"
    icon = "fa-solid fa-car"
    category = "Каталог"

    @expose("/cars", methods=["GET", "POST"], identity="cars")
    async def cars(self, request: Request):
        return await _handle_car_request(
            request, condition=None, list_path="/admin/cars", title="Авто"
        )


class CarUsedView(BaseView):
    name = "Авто с пробегом"
    icon = "fa-solid fa-car-side"
    category = "Каталог"

    @expose("/used-cars", methods=["GET", "POST"], identity="used-cars")
    async def used_cars(self, request: Request):
        return await _handle_car_request(
            request,
            condition=Condition.used,
            list_path="/admin/used-cars",
            title="Авто с пробегом",
        )


class CarSpecialView(BaseView):
    name = "Спецпредложения"
    icon = "fa-solid fa-tags"
    category = "Каталог"

    @expose("/special-cars", methods=["GET", "POST"], identity="special-cars")
    async def special_cars(self, request: Request):
        return await _handle_car_request(
            request,
            condition=Condition.special,
            list_path="/admin/special-cars",
            title="Спецпредложения",
        )
