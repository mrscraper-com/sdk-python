"""Account endpoint, response summary, and failure handling with mocked HTTP."""

import json

import httpx
import pytest

from mrscraper import APIError, AuthenticationError, MrScraper, NetworkError


@pytest.mark.parametrize("wrapped", [False, True])
async def test_account_uses_authenticated_get_and_returns_safe_summary(wrapped):
    details = {
        "stripeStatus": "active", "isEnterprise": True,
        "tokenLimit": "100", "tokenUsage": 25, "rateLimit": 10, "rateTtl": 60,
        "isAutoRenew": True, "endsAt": "2026-11-01T00:00:00Z",
        "stripeCustomerId": "private-billing-id",
        "user": {
            "name": "Test User", "email": "user@example.com", "isVerified": True,
            "latestApiToken": "private-key",
        },
    }

    async def handler(request):
        assert request.method == "GET"
        assert str(request.url) == "https://api.app.mrscraper.com/api/v1/subscription-accounts"
        assert request.content == b""
        assert request.headers["authorization"] == "Bearer test-token"
        assert request.headers["x-api-token"] == "test-token"
        assert request.extensions["timeout"]["read"] == 12
        return httpx.Response(
            200, json={"data": details} if wrapped else details,
            headers={"set-cookie": "session=private", "x-request-id": "req-1"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await MrScraper("test-token", http_client=http_client).account(timeout=12)
        assert not http_client.is_closed
    assert result["status_code"] == 200
    assert result["data"] == {
        "subscription_status": "active", "enterprise": True,
        "token_usage": 25, "token_limit": 100, "token_remaining": 75, "usage_percent": 25,
        "rate_limit": 10, "rate_ttl": 60, "auto_renew": True,
        "ends_at": "2026-11-01T00:00:00Z",
        "user": {"name": "Test User", "email": "user@example.com", "verified": True},
    }
    assert result["headers"]["x-request-id"] == "req-1"
    assert "private" not in json.dumps(result)
    assert "stripeCustomerId" not in json.dumps(result)
    assert "latestApiToken" not in json.dumps(result)


@pytest.mark.parametrize("details,percent", [({}, 0), ({"tokenLimit": 10, "tokenUsage": 15}, 150)])
async def test_account_handles_absent_quota_and_overuse(details, percent):
    async def handler(request):
        return httpx.Response(200, json={"data": details})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await MrScraper("test-token", http_client=http_client).account()
    assert result["data"]["token_remaining"] == 0
    assert result["data"]["usage_percent"] == percent
    assert result["data"]["user"] == {"name": None, "email": None, "verified": False}


@pytest.mark.parametrize("status,exception", [(401, AuthenticationError), (403, APIError), (500, APIError)])
async def test_account_preserves_authentication_and_http_errors(status, exception):
    async def handler(request):
        return httpx.Response(status, json={"message": "failed"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(exception) as error:
            await MrScraper("test-token", http_client=http_client).account()
    if isinstance(error.value, APIError):
        assert error.value.status_code == status


@pytest.mark.parametrize("body", [None, [], {"data": None}])
async def test_account_rejects_malformed_payloads(body):
    async def handler(request):
        return httpx.Response(200, text=json.dumps(body), headers={"content-type": "application/json"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(APIError, match="Account response must contain an object"):
            await MrScraper("test-token", http_client=http_client).account()


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
async def test_account_validates_timeout_before_sending(timeout):
    with pytest.raises(ValueError, match="timeout must be greater than 0"):
        await MrScraper("test-token").account(timeout=timeout)


async def test_account_validates_missing_token(monkeypatch):
    monkeypatch.delenv("MRSCRAPER_API_TOKEN", raising=False)
    with pytest.raises(AuthenticationError):
        await MrScraper().account()


async def test_account_uses_environment_token_and_closes_owned_client(monkeypatch):
    async def handler(request):
        assert request.headers["x-api-token"] == "environment-token"
        return httpx.Response(200, json={})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setenv("MRSCRAPER_API_TOKEN", "environment-token")
    monkeypatch.setattr("mrscraper.mrscraper.httpx.AsyncClient", lambda: http_client)
    await MrScraper().account()
    assert http_client.is_closed


async def test_account_wraps_network_timeout():
    async def handler(request):
        raise httpx.ReadTimeout("Timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(NetworkError, match="Timed out"):
            await MrScraper("test-token", http_client=http_client).account()
