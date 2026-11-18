import pytest

from tests.test_client import URL


@pytest.mark.parametrize(
    "method,options,expected",
    [
        (
            "scrape_markdown",
            {"html": True, "browser_rendering": False},
            {"html": "true", "markdown": "true", "browserRendering": "true"},
        ),
        (
            "get_screenshot",
            {"screenshot": "top", "html": False, "markdown": True},
            {"screenshot": "top", "html": "false", "markdown": "true", "browserRendering": "true"},
        ),
    ],
)
async def test_combined_outputs(recorded, method, options, expected):
    client, calls = recorded
    await getattr(client, method)(URL, **options)
    for key, value in expected.items():
        assert calls[0].url.params[key] == value


@pytest.mark.parametrize(
    "method,options",
    [
        ("scrape_html", {"timeout": 0}),
        ("scrape_html", {"timeout": 301}),
        ("scrape_html", {"timeout": True}),
        ("scrape_html", {"timeout": 1.5}),
        ("scrape_html", {"max_retries": -1}),
        ("scrape_html", {"max_retries": 1.5}),
        ("scrape_html", {"geo_code": "usa"}),
        ("scrape_html", {"proxy_country": "1a"}),
        ("scrape_html", {"wait_until": "networkidle"}),
        ("get_screenshot", {"screenshot": True}),
        ("scrape_json", {"prompt": " "}),
        ("scrape_html", {"url": "file:///tmp/test"}),
    ],
)
async def test_invalid_controls_do_not_send(recorded, method, options):
    client, calls = recorded
    target = options.pop("url", URL)
    with pytest.raises(ValueError):
        await getattr(client, method)(target, **options)
    assert calls == []


@pytest.mark.parametrize(
    "query,options",
    [
        (" ", {}),
        ("a" * 1001, {}),
        ("ok", {"country": "usa"}),
        ("ok", {"num_results": 9}),
        ("ok", {"num_results": 101}),
        ("ok", {"num_results": True}),
        ("ok", {"num_results": 10.5}),
        ("ok", {"timeout": 0}),
    ],
)
async def test_invalid_search_controls(recorded, query, options):
    client, calls = recorded
    with pytest.raises(ValueError):
        await client.web_search(query, **options)
    assert calls == []


async def test_unicode_query_boundary(recorded):
    client, calls = recorded
    await client.web_search("😀" * 1000, country="ID", num_results=100)
    assert calls[0].url.params["country"] == "id"
    assert calls[0].url.params["numResults"] == "100"


async def test_json_rejects_unsupported_loading_controls(recorded):
    client, calls = recorded
    with pytest.raises(TypeError):
        await client.scrape_json(URL, block_resources=True)
    assert calls == []
