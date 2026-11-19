"""Raw status response and failure handling with mocked HTTP."""

import json

import httpx
import pytest

from mrscraper import APIError, AuthenticationError, MrScraper, NetworkError


@pytest.mark.parametrize("body", [
    {"message": "OK", "data": {"tokenLimit": "100", "tokenUsage": 25,
        "stripeCustomerId": "billing-example", "custom": None,
        "user": {"name": "User", "latestApiToken": "token-example"}}},
    {"tokenLimit": 100, "tokenUsage": 150},
    {"data": [{"tokenUsage": 1}, {"tokenUsage": 2}]},
    {"data": None}, None, [], {},
])
async def test_status_preserves_complete_response(body):
    async def handler(request):
        assert request.method == "GET"
        assert str(request.url) == "https://api.app.mrscraper.com/api/v1/subscription-accounts"
        assert request.content == b""
        assert request.headers["authorization"] == "Bearer test-token"
        assert request.headers["x-api-token"] == "test-token"
        assert request.extensions["timeout"]["read"] == 600
        return httpx.Response(200, text=json.dumps(body), headers={
            "set-cookie": "session=example", "x-request-id": "req-1",
            "content-type": "application/json",
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await MrScraper("test-token", http_client=http_client).status()
        assert not http_client.is_closed
    assert result["status_code"] == 200
    assert result["data"] == body
    assert result["headers"]["x-request-id"] == "req-1"
    assert "set-cookie" not in result["headers"]


@pytest.mark.parametrize("status,exception", [(401, AuthenticationError), (403, APIError), (500, APIError)])
async def test_status_preserves_authentication_and_http_errors(status, exception):
    async def handler(request):
        return httpx.Response(status, json={"message": "failed"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(exception) as error:
            await MrScraper("test-token", http_client=http_client).status()
    if isinstance(error.value, APIError):
        assert error.value.status_code == status


async def test_status_validates_missing_token(monkeypatch):
    monkeypatch.delenv("MRSCRAPER_API_TOKEN", raising=False)
    with pytest.raises(AuthenticationError):
        await MrScraper().status()


async def test_status_uses_environment_token_and_closes_owned_client(monkeypatch):
    async def handler(request):
        assert request.headers["x-api-token"] == "environment-token"
        return httpx.Response(200, json={})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setenv("MRSCRAPER_API_TOKEN", "environment-token")
    monkeypatch.setattr("mrscraper.mrscraper.httpx.AsyncClient", lambda: http_client)
    await MrScraper().status()
    assert http_client.is_closed


async def test_status_wraps_network_timeout():
    async def handler(request):
        raise httpx.ReadTimeout("Timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(NetworkError, match="Timed out"):
            await MrScraper("test-token", http_client=http_client).status()
