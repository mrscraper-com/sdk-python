import pytest

from tests.test_client import URL

PAGE_METHODS = ("scrape_html", "scrape_markdown", "get_screenshot", "scrape_json")
LOADING_METHODS = ("scrape_html", "scrape_markdown", "scrape_json")


@pytest.mark.parametrize("method", LOADING_METHODS)
async def test_browser_rendering_is_omitted_unless_set(recorded, method):
    client, calls = recorded
    for value in (None, True, False):
        await getattr(client, method)(URL, browser_rendering=value)
        sent = calls[-1].url.params.get("browserRendering")
        assert sent == (None if value is None else str(value).lower())


@pytest.mark.parametrize(
    "screenshot",
    [False, "full", "top", "100x100", "1280x800", "3840x3840", "1280x800-25", "1920x1080-300"],
)
async def test_scrape_html_accepts_documented_screenshots(recorded, screenshot):
    client, calls = recorded
    await client.scrape_html(URL, screenshot=screenshot)
    assert calls[0].url.params["screenshot"] == str(screenshot).lower()
    rendering = calls[0].url.params.get("browserRendering")
    assert rendering == (None if screenshot is False else "true")


@pytest.mark.parametrize("screenshot", ["top", "full", "1280x800", "1920x1080-75"])
@pytest.mark.parametrize("browser_rendering", [None, True, False])
async def test_scrape_html_screenshot_sends_browser_rendering(
    recorded, screenshot, browser_rendering
):
    client, calls = recorded
    await client.scrape_html(URL, screenshot=screenshot, browser_rendering=browser_rendering)
    params = list(calls[0].url.params.multi_items())
    assert params[:4] == [
        ("url", URL),
        ("html", "true"),
        ("markdown", "false"),
        ("browserRendering", "true"),
    ]
    assert dict(params)["screenshot"] == screenshot


@pytest.mark.parametrize("browser_rendering", [None, True, False])
async def test_scrape_html_without_screenshot_keeps_browser_rendering(recorded, browser_rendering):
    client, calls = recorded
    await client.scrape_html(URL, browser_rendering=browser_rendering)
    params = calls[0].url.params
    assert params["screenshot"] == "false"
    assert params.get("browserRendering") == (
        None if browser_rendering is None else str(browser_rendering).lower()
    )


async def test_scrape_html_screenshot_still_validates_browser_rendering(recorded):
    client, calls = recorded
    with pytest.raises(ValueError, match="browser_rendering must be a boolean"):
        await client.scrape_html(URL, screenshot="top", browser_rendering="false")
    assert calls == []


async def test_json_screenshot_does_not_force_browser_rendering(recorded):
    client, calls = recorded
    await client.scrape_json(URL, screenshot=True)
    await client.scrape_json(URL, screenshot=True, browser_rendering=False)
    assert "browserRendering" not in calls[0].url.params
    assert calls[1].url.params["browserRendering"] == "false"


@pytest.mark.parametrize(
    "screenshot",
    [
        True,
        0,
        "",
        "FULL",
        "bottom",
        "99x800",
        "1280x3841",
        "12345x800",
        "1280x800-24",
        "1280x800-301",
        "1280x800-",
        "1280x800\n",
        "١٢٨٠x800",
        None,
    ],
)
async def test_scrape_html_rejects_other_screenshots(recorded, screenshot):
    client, calls = recorded
    with pytest.raises(ValueError, match="screenshot must be False, full, top"):
        await client.scrape_html(URL, screenshot=screenshot)
    assert calls == []


@pytest.mark.parametrize("method", PAGE_METHODS)
@pytest.mark.parametrize(
    "options",
    [
        {"timeout": 0},
        {"timeout": 331},
        {"timeout": True},
        {"timeout": 1.5},
        {"timeout": None},
        {"max_age": -1},
        {"max_age": 604800001},
        {"max_age": 1.5},
        {"max_age": None},
        {"max_retries": -1},
        {"max_retries": 1.5},
        {"geo_code": "usa"},
        {"geo_code": "1a"},
        {"wait_for_selector": " "},
        {"wait_for_selector": "a" * 501},
        {"url": "file:///tmp/test"},
    ],
)
async def test_invalid_page_controls_do_not_send(recorded, method, options):
    client, calls = recorded
    options = dict(options)
    target = options.pop("url", URL)
    with pytest.raises(ValueError):
        await getattr(client, method)(target, **options)
    assert calls == []


@pytest.mark.parametrize("method", LOADING_METHODS)
@pytest.mark.parametrize(
    "options",
    [
        {"browser_rendering": "true"},
        {"browser_rendering": 1},
        {"block_resources": 1},
        {"block_resources": None},
    ],
)
async def test_invalid_loading_controls_do_not_send(recorded, method, options):
    client, calls = recorded
    with pytest.raises(ValueError):
        await getattr(client, method)(URL, **options)
    assert calls == []


@pytest.mark.parametrize(
    "method,options",
    [
        ("scrape_html", {"action": " "}),
        ("scrape_markdown", {"action": 1}),
        ("scrape_json", {"prompt": " "}),
        ("scrape_json", {"html": "true"}),
        ("scrape_json", {"screenshot": "full"}),
        ("scrape_brand", {"url": "example.com"}),
    ],
)
async def test_invalid_service_controls_do_not_send(recorded, method, options):
    client, calls = recorded
    options = dict(options)
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
        ("ok", {"country": ""}),
        ("ok", {"num_results": 9}),
        ("ok", {"num_results": 101}),
        ("ok", {"num_results": True}),
        ("ok", {"num_results": 10.5}),
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


@pytest.mark.parametrize(
    "method,option",
    [
        (method, option)
        for method in PAGE_METHODS
        for option in (
            "super",
            "wait_until",
            "proxy_country",
            "proxy",
            "return_cookie",
            "save_result",
            "token_cap",
        )
    ]
    + [
        ("scrape_markdown", "html"),
        ("scrape_markdown", "screenshot"),
        ("get_screenshot", "screenshot"),
        ("get_screenshot", "html"),
        ("get_screenshot", "markdown"),
        ("get_screenshot", "browser_rendering"),
        ("get_screenshot", "warm_start"),
        ("get_screenshot", "block_resources"),
        ("get_screenshot", "action"),
        ("scrape_json", "action"),
    ],
)
async def test_undocumented_controls_are_not_accepted(recorded, method, option):
    client, calls = recorded
    with pytest.raises(TypeError):
        await getattr(client, method)(URL, **{option: "value"})
    assert calls == []


async def test_brand_sends_only_the_url(recorded):
    client, calls = recorded
    await client.scrape_brand(URL)
    assert list(calls[0].url.params.multi_items()) == [
        ("action", "brand-scraping"),
        ("url", URL),
        ("bundle", "none"),
    ]
    # Brand keeps the fixed 120-second deadline.
    assert calls[0].extensions["timeout"]["read"] == 120


@pytest.mark.parametrize(
    "option",
    [
        "timeout",
        "warm_start",
        "geo_code",
        "max_age",
        "save_result",
        "wait_for_selector",
        "browser_rendering",
        "block_resources",
        "token_cap",
        "max_retries",
        "screenshot",
        "bundle",
        "action",
    ],
)
async def test_brand_rejects_other_controls(recorded, option):
    client, calls = recorded
    with pytest.raises(TypeError):
        await client.scrape_brand(URL, **{option: "value"})
    assert calls == []


async def test_status_and_search_controls_stay_minimal(recorded):
    client, calls = recorded
    with pytest.raises(TypeError):
        await client.status(timeout=30)
    with pytest.raises(TypeError):
        await client.web_search("query", timeout=120)
    assert calls == []


async def test_search_keeps_its_fixed_deadline(recorded):
    client, calls = recorded
    await client.web_search("query")
    assert calls[0].extensions["timeout"]["read"] == 120


@pytest.mark.parametrize("method", LOADING_METHODS)
async def test_warm_start_is_forwarded_and_strictly_boolean(recorded, method):
    client, calls = recorded
    operation = getattr(client, method)
    for value in [False, True]:
        await operation(URL, warm_start=value)
        assert calls[-1].url.params["warmStart"] == str(value).lower()
    sent = len(calls)
    for value in ["true", 1, None]:
        with pytest.raises(ValueError, match="warm_start must be a boolean"):
            await operation(URL, warm_start=value)
    assert len(calls) == sent
