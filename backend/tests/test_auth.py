"""Auth tests — focus on the gmail block plus the register/login/JWT flow."""
from __future__ import annotations

import pytest

PASSWORD = "Sup3rSecret!"


@pytest.mark.parametrize(
    "email,allowed",
    [
        ("user@gmail.com", False),
        ("User@Gmail.Com", False),  # case-insensitive
        ("user@googlemail.com", False),  # gmail alias
        ("user@yandex.ru", True),
        ("user@mail.ru", True),
        ("user@example.com", True),
    ],
)
async def test_gmail_registration_blocked(client, email, allowed):
    resp = await client.post(
        "/auth/register", json={"email": email, "password": PASSWORD}
    )
    if allowed:
        assert resp.status_code == 201, resp.text
        assert resp.json()["email"] == email.lower()
    else:
        assert resp.status_code == 451, resp.text
        assert resp.json()["detail"]["code"] == "GMAIL_FORBIDDEN"
        assert "gmail" in resp.json()["detail"]["message"].lower()


async def test_register_login_me_refresh(client):
    email = "alice@example.com"
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Alice"},
    )
    assert reg.status_code == 201

    # Duplicate registration is rejected.
    dup = await client.post(
        "/auth/register", json={"email": email, "password": PASSWORD}
    )
    assert dup.status_code == 409

    # Login returns an access/refresh pair.
    login = await client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    # Wrong password is rejected.
    bad = await client.post(
        "/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert bad.status_code == 401

    # The access token authorizes /auth/me.
    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == email

    # The refresh token yields a fresh access token.
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


async def test_me_requires_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)


async def test_no_password_hash_in_responses(client):
    reg = await client.post(
        "/auth/register", json={"email": "carol@example.com", "password": PASSWORD}
    )
    assert "password_hash" not in reg.json()
    login = await client.post(
        "/auth/login", json={"email": "carol@example.com", "password": PASSWORD}
    )
    me = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert "password_hash" not in me.json()


@pytest.mark.parametrize("sub", ["not-an-int", None])
async def test_token_with_bad_sub_is_401_not_500(client, sub):
    """A validly-signed token with a missing/non-int sub must 401, not 500."""
    import jwt

    from app.core.config import get_settings
    from app.core.security import ACCESS

    s = get_settings()
    claims = {"type": ACCESS, "exp": 9999999999}
    if sub is not None:
        claims["sub"] = sub
    token = jwt.encode(claims, s.jwt_secret, algorithm=s.jwt_algorithm)
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_refresh_rejects_access_token(client):
    """An access token must not be accepted where a refresh token is required."""
    await client.post(
        "/auth/register", json={"email": "bob@example.com", "password": PASSWORD}
    )
    login = await client.post(
        "/auth/login", json={"email": "bob@example.com", "password": PASSWORD}
    )
    access = login.json()["access_token"]
    resp = await client.post("/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401
