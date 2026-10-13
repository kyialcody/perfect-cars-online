"""Declarative base for all ORM models.

Models (issue #4) subclass `Base`; Alembic autogenerate reads
`Base.metadata`. Importing `app.models` registers every model on the
metadata — env.py does that so migrations see the full schema.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
