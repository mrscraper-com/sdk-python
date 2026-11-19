"""Manual runner dispatch remains aligned with the SDK."""

import pytest

runner = pytest.importorskip("file", reason="Manual runner is only available in the checkout")


@pytest.mark.parametrize("name", runner.METHOD_ORDER)
async def test_manual_dispatch(recorded, name):
    client, calls = recorded
    args = runner.build_parser().parse_args([name])
    result = await runner.run_method(client, args)
    assert result["status_code"] == 200
    assert len(calls) == 1


def test_manual_services():
    assert runner.METHOD_ORDER == (
        "status",
        "scrape-html",
        "scrape-markdown",
        "get-screenshot",
        "scrape-brand",
        "scrape-json",
        "web-search",
    )
