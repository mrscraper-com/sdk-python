"""Public method descriptions match the common documentation reference."""

import inspect
import json
from pathlib import Path

import pytest

from mrscraper import MrScraper

REFERENCE = json.loads((Path(__file__).parents[1] / "docs/service-reference.json").read_text())


@pytest.mark.parametrize("service", REFERENCE["services"], ids=lambda service: service["name"])
def test_method_and_parameter_descriptions(service):
    method = getattr(MrScraper, service["name"].replace("-", "_"))
    doc = inspect.getdoc(method)
    assert doc.split("\n\n")[0] == service["description"]
    for key in service["parameters"]:
        parameter = REFERENCE["parameters"][key]
        name = "".join("_" + char.lower() if char.isupper() else char for char in parameter["name"])
        assert f"{name}: {parameter['description']}" in doc
