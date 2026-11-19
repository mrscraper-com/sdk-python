import httpx
import pytest

from mrscraper import MrScraper


@pytest.fixture
async def recorded():
    calls = []

    async def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": {"tokenLimit": 100, "tokenUsage": 20}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        yield MrScraper("test-token", http_client=http), calls
        assert not http.is_closed
