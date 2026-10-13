"""Single-form «Запчасть» screen for the admin.

Mirrors the car composer (``app.admin.composer``) in shape and UX — a list with
visibility/delete plus one create/edit form with a photo gallery — but for the
independent Part domain. Parts are added and edited on their own; they are not
bound to any Car. Generic form helpers are imported from the car composer to
avoid duplication; only part-specific storage and sync logic live here.
"""
from __future__ import annotations

from decimal import Decimal
from html import escape

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse
from sqladmin import BaseView, expose
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.datastructures import UploadFile

from app.admin.composer import (
    _bool,
    _decimal,
    _image_rows,
    _int,
    _is_admin_session,
    _is_valid_csrf,
    _money,
    _new_csrf_token,
    _options,
    _page,
    _single_image_field,
)
from app.core.cache import bump_catalog_version
from app.core.config import get_settings
from app.core.storage import get_s3_client, put_object
from app.db.session import SessionLocal
from app.models.catalog import Brand
from app.models.parts import Part, PartCategory, PartCondition, PartImage, PartKind

LIST_PATH = "/admin/parts"

CONDITIONS = ((PartCondition.new, "Новая"), (PartCondition.used, "Б/У"))
KINDS = ((PartKind.original, "Оригинал"), (PartKind.aftermarket, "Аналог"))


async def _store_upload(upload: UploadFile, part_slug: str, order: int, *, name: str = "photo") -> str | None:
    content = await upload.read()
    if not content:
        return None
    ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else "bin"
    key = f"parts/{part_slug}/{name}-{order}.{ext}"
    settings = get_settings()
    await run_in_threadpool(
        put_object,
        get_s3_client(),
        settings.s3_bucket,
        key,
        content,
        upload.content_type or "application/octet-stream",
    )
    return key


def _enum_options(pairs, selected) -> str:
    return "\n".join(
        f'<option value="{value.value}" {"selected" if value == selected else ""}>{escape(label)}</option>'
        for value, label in pairs
    )


async def _load_part(session, part_id: int) -> Part | None:
    return await session.get(
        Part, part_id, options=[selectinload(Part.images)]
    )


async def _load_refs(session):
    categories = (
        await session.execute(select(PartCategory).order_by(PartCategory.name))
    ).scalars().all()
    brands = (await session.execute(select(Brand).order_by(Brand.name))).scalars().all()
    return categories, brands


# --- list --------------------------------------------------------------------


async def render_list(request: Request) -> HTMLResponse:
    csrf = _new_csrf_token(request)
    async with SessionLocal() as session:
        parts = (
            await session.execute(select(Part).order_by(Part.id.desc()))
        ).scalars().all()

        rows = []
        for part in parts:
            visible = not part.is_hidden
            tag = (
                '<span class="tag tag-on">На сайте</span>'
                if visible
                else '<span class="tag tag-off">Скрыто</span>'
            )
            toggle_label = "Скрыть" if visible else "Показать"
            rows.append(
                f"""
<tr>
  <td>#{part.id}</td>
  <td><a href="{LIST_PATH}?part_id={part.id}">{escape(part.name)}</a><br>
      <span class="hint">{escape(part.slug)}</span></td>
  <td>{tag}</td>
  <td>{_money(part.price)} ₽</td>
  <td>{part.qty}</td>
  <td>
    <a href="{LIST_PATH}?part_id={part.id}">Редактировать</a>
    <form class="inline-form" method="post">
      <input type="hidden" name="csrf_token" value="{escape(csrf)}">
      <input type="hidden" name="action" value="toggle_visibility">
      <input type="hidden" name="part_id" value="{part.id}">
      <button class="button-secondary" type="submit">{toggle_label}</button>
    </form>
    <form class="inline-form" method="post" onsubmit="return confirm('Удалить запчасть #{part.id}?');">
      <input type="hidden" name="csrf_token" value="{escape(csrf)}">
      <input type="hidden" name="action" value="delete">
      <input type="hidden" name="part_id" value="{part.id}">
      <button type="submit">Удалить</button>
    </form>
  </td>
</tr>
                """
            )
        body = "".join(rows) or '<tr><td colspan="6" class="hint">Запчастей ещё нет.</td></tr>'

    content = f"""
<h1>Запчасти</h1>
<div class="topbar">
  <a class="btn-link" href="/admin">← В админку</a>
  <a class="btn-link primary" href="{LIST_PATH}?new=1">+ Создать запчасть</a>
</div>
<table>
  <thead><tr>
    <th>ID</th><th>Запчасть</th><th>Видимость</th><th>Цена</th><th>Кол-во</th><th>Действия</th>
  </tr></thead>
  <tbody>{body}</tbody>
</table>
    """
    return _page(content)


# --- create / edit form ------------------------------------------------------


async def render_form(request: Request) -> HTMLResponse:
    part_id = _int(request.query_params.get("part_id"))
    csrf = _new_csrf_token(request)
    async with SessionLocal() as session:
        part = await _load_part(session, part_id) if part_id else None
        if part_id and part is None:
            return _page("<h1>Запчасть не найдена</h1>", status_code=404)
        categories, brands = await _load_refs(session)

        title = part.name if part else "Новая запчасть"
        image_html = _image_rows(part.images if part else [])
        part_id_field = f'<input type="hidden" name="part_id" value="{part.id}">' if part else ""
        save_label = "Сохранить" if part else "Создать запчасть"

        visibility_block = ""
        if part is not None:
            toggle_label = "Скрыть с сайта" if not part.is_hidden else "Показать на сайте"
            status_note = (
                "Скрыто — карточка убрана с сайта."
                if part.is_hidden
                else "На сайте — карточка видна публично."
            )
            visibility_block = f"""
<p class="hint">{escape(part.slug)} · {escape(status_note)}</p>
<form class="inline-form" method="post">
  <input type="hidden" name="csrf_token" value="{escape(csrf)}">
  <input type="hidden" name="action" value="toggle_visibility">
  <input type="hidden" name="part_id" value="{part.id}">
  <button class="button-secondary" type="submit">{escape(toggle_label)}</button>
</form>
            """

        content = f"""
<div class="topbar">
  <a class="btn-link" href="/admin">← В админку</a>
  <a href="{LIST_PATH}">К списку запчастей</a>
</div>
<h1>{escape(title)}</h1>
{visibility_block}

<form method="post" enctype="multipart/form-data">
  <input type="hidden" name="csrf_token" value="{escape(csrf)}">
  <input type="hidden" name="action" value="save">
  {part_id_field}

  <fieldset>
    <legend>Основное</legend>
    <div class="grid">
      <label>Slug <input name="slug" value="{escape(part.slug) if part else ''}" required></label>
      <label>Название <input name="name" value="{escape(part.name) if part else ''}" required></label>
      <label>Категория <select name="category_id">{_options(categories, part.category_id if part else None, blank='—')}</select></label>
      <label>Совместимая марка <select name="brand_id">{_options(brands, part.brand_id if part else None, blank='—')}</select></label>
      <label>Состояние <select name="condition">{_enum_options(CONDITIONS, part.condition if part else PartCondition.new)}</select></label>
      <label>Тип <select name="kind">{_enum_options(KINDS, part.kind if part else PartKind.original)}</select></label>
      <label>Производитель <input name="manufacturer" value="{escape(part.manufacturer or '') if part else ''}"></label>
      <label>Артикул / OEM <input name="part_number" value="{escape(part.part_number or '') if part else ''}"></label>
      <label>Цена <input name="price" value="{_money(part.price) if part else ''}" required></label>
      <label>Старая цена <input name="price_old" value="{_money(part.price_old) if part else ''}"></label>
      <label>Бейдж выгоды <input name="benefit_badge" value="{escape(part.benefit_badge or '') if part else ''}"></label>
      <label>Статус-текст <input name="status_text" value="{escape(part.status_text or '') if part else ''}"></label>
      <label>Количество <input name="qty" value="{part.qty if part else 1}"></label>
      <label>В наличии <select name="in_stock"><option value="1" {'selected' if (part is None or part.in_stock) else ''}>Да</option><option value="0" {'selected' if (part and not part.in_stock) else ''}>Нет</option></select></label>
    </div>
    <label>Описание <textarea name="description" rows="4" style="width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #ddd;border-radius:6px;font:inherit;">{escape(part.description or '') if part else ''}</textarea></label>
  </fieldset>

  <fieldset><legend>Фото для каталога</legend>
    <p class="hint">Превью-карточка в каталоге. <strong>1000×750 px (4:3)</strong> — иначе фото обрежется.</p>
    <div class="grid">
      {_single_image_field('card_image', 'Фото в каталоге (превью-карточка)', part.card_image_url if part else None)}
    </div>
  </fieldset>

  <fieldset><legend>Галерея</legend>
    <p class="hint">Главное фото слева на детальной странице, миниатюры под ним.</p>
    {image_html}
  </fieldset>

  <div class="actions">
    <button type="submit">{escape(save_label)}</button>
  </div>
</form>
        """
    return _page(content)


# --- save --------------------------------------------------------------------


async def _sync_part_images(session, part: Part, form, *, slug: str) -> None:
    by_id = {im.id: im for im in part.images}
    count = _int(str(form.get("image_count")), 0) or 0
    main_choice = str(form.get("main_image") or "").strip()
    survivors: list[PartImage] = []
    for i in range(count):
        iid = _int(str(form.get(f"image_id_{i}")))
        if not iid or iid not in by_id:
            continue
        im = by_id[iid]
        if _bool(form.get(f"image_delete_{i}")):
            part.images.remove(im)
            continue
        im.sort_order = _int(str(form.get(f"image_sort_{i}")), im.sort_order)
        im.is_main = False
        survivors.append(im)

    base = len(survivors)
    new_images: list[PartImage] = []
    for offset, upload in enumerate(form.getlist("images")):
        if not (isinstance(upload, UploadFile) and upload.filename):
            continue
        key = await _store_upload(upload, slug, base + offset)
        if key:
            img = PartImage(url=key, is_main=False, sort_order=base + offset)
            part.images.append(img)
            new_images.append(img)

    all_imgs = survivors + new_images
    if not all_imgs:
        return
    # Flush with every image is_main=False first so setting one True can't
    # collide under the partial unique index uq_part_main_image.
    await session.flush()
    chosen = next((im for im in survivors if str(im.id) == main_choice), None)
    (chosen or all_imgs[0]).is_main = True


async def save_part(form) -> HTMLResponse:
    part_id = _int(str(form.get("part_id")))
    new_slug = str(form.get("slug") or "").strip()
    name = str(form.get("name") or "").strip()
    if not new_slug or not name:
        return _page("<h1>Ошибка</h1><p>Укажите slug и название.</p>", status_code=400)

    async with SessionLocal() as session:
        clash_stmt = select(Part.id).where(Part.slug == new_slug)
        if part_id:
            clash_stmt = clash_stmt.where(Part.id != part_id)
        if (await session.execute(clash_stmt)).scalar_one_or_none() is not None:
            return _page(
                f"<h1>Slug занят</h1><p>Запчасть со slug <strong>{escape(new_slug)}</strong> уже есть.</p>",
                status_code=409,
            )

        categories, brands = await _load_refs(session)
        valid_categories = {c.id for c in categories}
        valid_brands = {b.id for b in brands}

        if part_id:
            part = await _load_part(session, part_id)
            if part is None:
                return _page("<h1>Запчасть не найдена</h1>", status_code=404)
        else:
            part = Part(slug=new_slug, name=name, price=Decimal("0"), images=[])
            session.add(part)
            await session.flush()

        part.slug = new_slug
        part.name = name
        category_id = _int(str(form.get("category_id")))
        part.category_id = category_id if category_id in valid_categories else None
        brand_id = _int(str(form.get("brand_id")))
        part.brand_id = brand_id if brand_id in valid_brands else None
        try:
            part.condition = PartCondition(str(form.get("condition") or "new"))
        except ValueError:
            part.condition = PartCondition.new
        try:
            part.kind = PartKind(str(form.get("kind") or "original"))
        except ValueError:
            part.kind = PartKind.original
        part.manufacturer = str(form.get("manufacturer") or "").strip() or None
        part.part_number = str(form.get("part_number") or "").strip() or None
        part.price = _decimal(str(form.get("price")), part.price)
        part.price_old = _decimal(str(form.get("price_old")))
        part.benefit_badge = str(form.get("benefit_badge") or "").strip() or None
        part.status_text = str(form.get("status_text") or "").strip() or None
        part.description = str(form.get("description") or "").strip() or None
        part.qty = _int(str(form.get("qty")), part.qty)
        part.in_stock = _bool(form.get("in_stock"), part.in_stock)

        if _bool(form.get("card_image_delete")):
            part.card_image_url = None
        card_upload = form.get("card_image")
        if isinstance(card_upload, UploadFile) and card_upload.filename:
            key = await _store_upload(card_upload, new_slug, 0, name="card_image")
            if key:
                part.card_image_url = key

        await session.flush()
        await _sync_part_images(session, part, form, slug=new_slug)

        await session.commit()
        saved_id = part.id

    await bump_catalog_version()
    return _page(
        f'<h1>Сохранено</h1><p>'
        f'<a href="{LIST_PATH}?part_id={saved_id}">Вернуться к редактированию</a> · '
        f'<a href="{LIST_PATH}">К списку</a></p>'
    )


async def toggle_visibility(form) -> HTMLResponse:
    part_id = _int(str(form.get("part_id")))
    if not part_id:
        return _page("<h1>Ошибка</h1><p>Не указана запчасть.</p>", status_code=400)
    async with SessionLocal() as session:
        part = await session.get(Part, part_id)
        if part is None:
            return _page("<h1>Запчасть не найдена</h1>", status_code=404)
        part.is_hidden = not part.is_hidden
        await session.commit()
    await bump_catalog_version()
    return RedirectResponse(url=LIST_PATH, status_code=303)


async def delete_part(form) -> HTMLResponse:
    part_id = _int(str(form.get("part_id")))
    if not part_id:
        return _page("<h1>Ошибка</h1><p>Не указана запчасть.</p>", status_code=400)
    async with SessionLocal() as session:
        part = await session.get(Part, part_id)
        if part is None:
            return _page("<h1>Запчасть не найдена</h1>", status_code=404)
        await session.delete(part)
        await session.commit()
    await bump_catalog_version()
    return RedirectResponse(url=LIST_PATH, status_code=303)


async def _handle_part_request(request: Request):
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
            return await delete_part(form)
        return await save_part(form)
    if request.query_params.get("new") or request.query_params.get("part_id"):
        return await render_form(request)
    return await render_list(request)


class PartView(BaseView):
    name = "Запчасти"
    icon = "fa-solid fa-gears"
    category = "Каталог"

    @expose("/parts", methods=["GET", "POST"], identity="parts")
    async def parts(self, request: Request):
        return await _handle_part_request(request)
