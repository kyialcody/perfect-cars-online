"""Config guards: default JWT secret and localhost-only CORS refused outside dev."""
from __future__ import annotations

import pytest

from app.core.config import _DEFAULT_JWT_SECRET, Settings

_REAL_CORS = "https://perfect-cars.online"


def test_default_jwt_secret_rejected_outside_dev():
    with pytest.raises(ValueError):
        Settings(app_env="prod", jwt_secret=_DEFAULT_JWT_SECRET, cors_origins=_REAL_CORS)


def test_default_jwt_secret_allowed_in_dev():
    # Should not raise.
    Settings(app_env="dev", jwt_secret=_DEFAULT_JWT_SECRET)


def test_custom_secret_allowed_outside_dev():
    Settings(app_env="prod", jwt_secret="a-real-secret", cors_origins=_REAL_CORS)


def test_localhost_only_cors_rejected_outside_dev():
    with pytest.raises(ValueError):
        Settings(
            app_env="prod",
            jwt_secret="a-real-secret",
            cors_origins="http://localhost:5173,https://127.0.0.1",
        )


def test_localhost_cors_allowed_in_dev():
    # Dev is exempt from the CORS check.
    Settings(app_env="dev", cors_origins="http://localhost:5173")


def test_real_cors_allowed_outside_dev():
    Settings(
        app_env="prod",
        jwt_secret="a-real-secret",
        cors_origins="http://localhost:5173,https://perfect-cars.online",
    )
