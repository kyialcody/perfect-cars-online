"""Single «Контакты — настройки» admin screen: the contacts texts and the
contact photos managed together (no separate «Фото контактов» entry).

Phones, addresses, requisites and socials stay as their own list views — they
are naturally repeating lists. This screen only merges the singleton text
settings with the photo gallery, mirroring the «О компании» screen.
"""
from __future__ import annotations

from html import escape

from sqladmin import BaseView, expose
from sqlalchemy import select
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from app.admin.composer import (
    _bool,
    _int,
    _is_admin_session,
    _is_valid_csrf,
    _new_csrf_token,
    _page,
)
from app.admin.views import _store_upload
from app.core.cache import bump_catalog_version
from app.core.storage import public_url
from app.db.session import SessionLocal
from app.models.home import ContactInfo, ContactPhoto

LIST_PATH = "/admin/contacts-settings"


def _photo_rows(photos: list[ContactPhoto]) -> str:
    if not photos:
        strip = '<p class="hint">Фото ещё нет. Загрузите ниже.</p>'
    else:
        cards = "".join(
            f"""
<div class="photo">
  <input type="hidden" name="photo_id_{i}" value="{p.id}">
  <img src="{escape(public_url(p.image_url) or '')}" alt="">
  <label class="photo-line">Описание <input name="photo_alt_{i}" value="{escape(p.alt or '')}"></label>
  <label class="photo-line">Порядок <input name="photo_sort_{i}" value="{p.sort_order}"></label>
  <label class="photo-line"><input type="checkbox" name="photo_active_{i}" {'checked' if p.is_active else ''}>активно</label>
  <label class="photo-line"><input type="checkbox" name="photo_delete_{i}">удалить</label>
</div>
            """
            for i, p in enumerate(photos)
        )
        strip = f'<div class="carousel">{cards}</div>'
    return (
        f'<input type="hidden" name="photo_count" value="{len(photos)}">'
        + strip
        + '<label>Добавить фото <input name="photos" type="file" multiple accept="image/*"></label>'
    )


async def _render(request: Request) -> HTMLResponse:
    csrf = _new_csrf_token(request)
    async with SessionLocal() as session:
        info = (await session.execute(select(ContactInfo).limit(1))).scalar_one_or_none()
        photos = (
            await session.execute(
                select(ContactPhoto).order_by(ContactPhoto.sort_order, ContactPhoto.id)
            )
        ).scalars().all()

        about_text = escape(info.about_text or "") if info else ""
        footer_text = escape(info.footer_about_text or "") if info else ""

        content = f"""
<div class="topbar">
  <a class="btn-link" href="/admin">← В админку</a>
</div>
<h1>Контакты — настройки</h1>
<p class="hint">Телефоны, адреса, реквизиты и соцсети — в отдельных пунктах меню.</p>

<form method="post" enctype="multipart/form-data">
  <input type="hidden" name="csrf_token" value="{escape(csrf)}">

  <fieldset>
    <legend>Тексты</legend>
    <label>Текст «О компании» на странице «Контакты»
      <textarea name="about_text" rows="6">{about_text}</textarea></label>
    <label>Текст футера (слева от реквизитов)
      <textarea name="footer_about_text" rows="4">{footer_text}</textarea></label>
  </fieldset>

  <fieldset>
    <legend>Фото контактов</legend>
    <p class="hint">Показываются и просматриваются на странице «Контакты».</p>
    {_photo_rows(photos)}
  </fieldset>

  <div class="actions">
    <button type="submit">Сохранить</button>
  </div>
</form>
        """
    return _page(content)


async def _save(form) -> HTMLResponse:
    async with SessionLocal() as session:
        info = (await session.execute(select(ContactInfo).limit(1))).scalar_one_or_none()
        if info is None:
            info = ContactInfo(is_active=True)
            session.add(info)
        info.about_text = str(form.get("about_text") or "").strip() or None
        info.footer_about_text = str(form.get("footer_about_text") or "").strip() or None
        info.is_active = True

        photos = (
            await session.execute(
                select(ContactPhoto).order_by(ContactPhoto.sort_order, ContactPhoto.id)
            )
        ).scalars().all()
        by_id = {p.id: p for p in photos}
        count = _int(str(form.get("photo_count")), 0) or 0
        survivors = 0
        for i in range(count):
            pid = _int(str(form.get(f"photo_id_{i}")))
            p = by_id.get(pid) if pid else None
            if p is None:
                continue
            if _bool(form.get(f"photo_delete_{i}")):
                await session.delete(p)
                continue
            p.alt = str(form.get(f"photo_alt_{i}") or "").strip() or None
            p.sort_order = _int(str(form.get(f"photo_sort_{i}")), p.sort_order)
            p.is_active = _bool(form.get(f"photo_active_{i}"))
            survivors += 1

        order = survivors
        for upload in form.getlist("photos"):
            if not (isinstance(upload, UploadFile) and upload.filename):
                continue
            key = await _store_upload(upload, "contacts/photos")
            if key:
                session.add(ContactPhoto(image_url=key, is_active=True, sort_order=order))
                order += 1

        await session.commit()
    await bump_catalog_version()
    return RedirectResponse(url=LIST_PATH, status_code=303)


class ContactsSettingsView(BaseView):
    name = "Контакты — настройки"
    icon = "fa-solid fa-address-card"
    category = "Контакты"

    @expose("/contacts-settings", methods=["GET", "POST"], identity="contacts-settings")
    async def contacts_settings(self, request: Request):
        if not await _is_admin_session(request):
            return RedirectResponse(url="/admin/login", status_code=302)
        if request.method == "POST":
            form = await request.form()
            if not await _is_valid_csrf(request, form):
                return _page(
                    "<h1>Ошибка</h1><p>Сессия формы устарела. Откройте страницу заново.</p>",
                    status_code=403,
                )
            return await _save(form)
        return await _render(request)
