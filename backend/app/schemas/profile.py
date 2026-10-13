"""Schemas for the public account/profile area."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.lead import LeadStatus
from app.schemas.lead import normalize_ru_phone


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, min_length=5, max_length=30)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_ru_phone(value) if value else None


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ProfileCarOut(BaseModel):
    id: int
    slug: str
    title: str
    image_url: str | None = None


class ProfileLeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_title: str | None
    dedupe_key: str | None
    status: LeadStatus
    comment: str | None
    phone: str
    created_at: datetime
    car: ProfileCarOut | None = None
