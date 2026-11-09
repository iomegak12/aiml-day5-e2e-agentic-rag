import pytest

from tests.conftest import headers

ME = "/api/v1/me"


@pytest.mark.parametrize(("user", "role", "levels"), [
    ("alice", "guest", ["public"]),
    ("bob", "employee", ["public", "internal"]),
    ("carol", "admin", ["public", "internal", "restricted"]),
])
async def test_me_returns_profile(client, user, role, levels):
    r = await client.get(ME, headers=headers(user))
    assert r.status_code == 200
    assert r.json() == {"id": user, "name": user.capitalize(), "role": role, "allowed_levels": levels}


async def test_me_without_key_is_401(client):
    r = await client.get(ME)
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")


async def test_me_with_bad_key_is_401(client):
    r = await client.get(ME, headers={"X-API-Key": "nope"})
    assert r.status_code == 401
