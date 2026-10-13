"""Request/response schemas for lead capture."""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.lead import LeadSource, LeadStatus

_DIGITS = re.compile(r"\D+")


def normalize_ru_phone(raw: str) -> str:
    """Normalize a Russian phone to ``+7XXXXXXXXXX`` or raise ValueError."""
    digits = _DIGITS.sub("", raw)
    if len(digits) == 11 and digits[0] in {"7", "8"}:
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    else:
        raise ValueError("Некорректный номер телефона")
    return "+" + digits


class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=30)
    source: LeadSource = LeadSource.other
    source_title: str | None = Field(default=None, max_length=200)
    dedupe_key: str | None = Field(default=None, max_length=240)
    car_id: int | None = None
    comment: str | None = Field(default=None, max_length=500)
    consent: bool

    # Honeypot: real users never see/fill this. Bots that auto-fill all fields
    # trip it. Must stay empty.
    company: str | None = Field(default=None, max_length=200)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        return normalize_ru_phone(v)

    @field_validator("consent")
    @classmethod
    def _require_consent(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("Требуется согласие на обработку персональных данных")
        return v


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    source: LeadSource
    source_title: str | None
    dedupe_key: str | None
    car_id: int | None
    user_id: int | None = None
    comment: str | None
    status: LeadStatus
    created_at: datetime
