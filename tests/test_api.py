"""Exercise the wire contract against an actual local HTTP server."""

import aiohttp
from aiohttp import web
import pytest

from custom_components.habitat_tablet.api import CannotConnect, CommandFailed, InvalidAuth, TabletApi, normalize_url


async def test_authenticated_commands(aiohttp_server, snapshot):
    async def screen(request):
        assert request.headers["Authorization"] == "Bearer pairing-key"
        assert "pairing-key" not in str(request.rel_url)
        if request.method == "POST":
            snapshot["screen_on"] = (await request.json())["screen_on"]
        return web.json_response(snapshot)

    app = web.Application()
    app.router.add_route("*", "/api/screen", screen)
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as session:
        api = TabletApi(session, str(server.make_url("/")), "pairing-key")
        assert (await api.get_screen())["screen_on"] is True
        assert (await api.set_screen(False))["screen_on"] is False
        assert (await api.set_screen(True))["screen_on"] is True


@pytest.mark.parametrize("status,body,error", [
    (401, {}, InvalidAuth),
    (409, {"error": "device admin permission required"}, CommandFailed),
    (200, {"protocol": 1, "screen_on": "false"}, CannotConnect),
    (200, {"protocol": 2}, CannotConnect),
])
async def test_rejected_responses(aiohttp_server, status, body, error):
    app = web.Application()
    app.router.add_get("/api/screen", lambda _: web.json_response(body, status=status))
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(error):
            await TabletApi(session, str(server.make_url("/")), "key").get_screen()


async def test_does_not_follow_redirect_with_secret(aiohttp_server):
    app = web.Application()
    async def redirect(_):
        raise web.HTTPFound("http://127.0.0.1:1/steal")
    app.router.add_get("/api/screen", redirect)
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(CannotConnect):
            await TabletApi(session, str(server.make_url("/")), "key").get_screen()


async def test_command_must_confirm_actual_state(aiohttp_server, snapshot):
    app = web.Application()
    app.router.add_post("/api/screen", lambda _: web.json_response(snapshot))
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(CommandFailed):
            await TabletApi(session, str(server.make_url("/")), "key").set_screen(False)


def test_address_validation():
    assert normalize_url("192.168.1.50") == "http://192.168.1.50:8765"
    assert normalize_url("http://192.168.1.50:8765/") == "http://192.168.1.50:8765"
    for value in ("ftp://host", "http://user:pass@host", "http://host/camera", "http://host/?token=secret"):
        with pytest.raises(ValueError):
            normalize_url(value)
