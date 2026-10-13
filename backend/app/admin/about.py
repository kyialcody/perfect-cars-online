"""Single «О компании» admin screen: homepage + /about texts, video and salon
photos managed together on one page (no separate «Фото салона» entry).

Reuses the page chrome / CSRF / upload helpers from the car composer and the
SQLAdmin views, so it matches the rest of the panel.
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
from app.models.home import AboutSalonPhoto, HomeAbout

LIST_PATH = "/admin/about-company"


def _photo_rows(photos: list[AboutSalonPhoto]) -> str:
    if not photos:
        strip = '<p class="hint">Фото салона ещё нет. Загрузите ниже.</p>'
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
        + '<label>Добавить фото салона <input name="photos" type="file" multiple accept="image/*"></label>'
    )


async def _render(request: Request) -> HTMLResponse:
    csrf = _new_csrf_token(request)
    async with SessionLocal() as session:
        about = (await session.execute(select(HomeAbout).limit(1))).scalar_one_or_none()
        photos = (
            await session.execute(
                select(AboutSalonPhoto).order_by(AboutSalonPhoto.sort_order, AboutSalonPhoto.id)
            )
        ).scalars().all()

        description = escape(about.description or "") if about else ""
        page_text = escape(about.page_text or "") if about else ""
        video_url = escape(about.video_url or "") if about else ""

        content = f"""
<div class="topbar">
  <a class="btn-link" href="/admin">← В админку</a>
</div>
<h1>О компании</h1>

<form method="post" enctype="multipart/form-data">
  <input type="hidden" name="csrf_token" value="{escape(csrf)}">

  <fieldset>
    <legend>Тексты</legend>
    <label>Текст на главной странице (блок «О компании»)
      <textarea name="description" rows="4">{description}</textarea></label>
    <label>Текст на странице «О компании» (/about)
      <textarea name="page_text" rows="8">{page_text}</textarea></label>
    <label>Ссылка на видео (YouTube, необязательно)
      <input name="video_url" value="{video_url}"></label>
  </fieldset>

  <fieldset>
    <legend>Фото салона</legend>
    <p class="hint">Показываются на странице «О компании». Рекомендуется 16:9.</p>
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
        about = (await session.execute(select(HomeAbout).limit(1))).scalar_one_or_none()
        if about is None:
            about = HomeAbout(is_active=True)
            session.add(about)
        about.description = str(form.get("description") or "").strip() or None
        about.page_text = str(form.get("page_text") or "").strip() or None
        about.video_url = str(form.get("video_url") or "").strip() or None
        about.is_active = True

        photos = (
            await session.execute(
                select(AboutSalonPhoto).order_by(AboutSalonPhoto.sort_order, AboutSalonPhoto.id)
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
            key = await _store_upload(upload, "about/salon")
            if key:
                session.add(
                    AboutSalonPhoto(image_url=key, is_active=True, sort_order=order)
                )
                order += 1

        await session.commit()
    await bump_catalog_version()
    return RedirectResponse(url=LIST_PATH, status_code=303)


class AboutCompanyView(BaseView):
    name = "О компании"
    icon = "fa-solid fa-circle-info"
    category = "О компании"

    @expose("/about-company", methods=["GET", "POST"], identity="about-company")
    async def about_company(self, request: Request):
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
