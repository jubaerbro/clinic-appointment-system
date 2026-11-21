"""Swagger / OpenAPI tests.
They keep the documentation honest: if someone adds an /api route
and forgets to document it in openapi.yaml, the build fails."""
import os
import re

import yaml
from openapi_spec_validator import validate

SPEC_FILE = os.path.join(os.path.dirname(__file__), "..", "openapi.yaml")


def load_spec():
    with open(SPEC_FILE) as f:
        return yaml.safe_load(f)


def test_openapi_file_is_valid():
    validate(load_spec())  # raises an error if the spec breaks OpenAPI 3 rules


def test_every_api_route_is_documented(client):
    documented = set()
    for path, operations in load_spec()["paths"].items():
        for method in operations:
            documented.add((method.upper(), path))

    in_code = set()
    for rule in client.application.url_map.iter_rules():
        if rule.rule.startswith("/api/"):
            path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule)  # <int:id> -> {id}
            for method in rule.methods - {"HEAD", "OPTIONS"}:
                in_code.add((method, path))

    assert in_code == documented


def test_swagger_ui_page_is_served(client):
    assert client.get("/apidocs/").status_code == 200
    spec = client.get("/apispec_1.json").get_json()
    assert spec["info"]["title"] == "Clinic Appointment System API"
