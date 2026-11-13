import json

from app.inference import default_model_dir
from tests.api.conftest import PREDICT


def test_health(client, predictor):
    body = client.get("/api/v1/health").json()
    assert body == {
        "status": "ok",
        "model_version": predictor.model_version,
        "artifacts_sha256": predictor.artifact_sha256,
    }


def test_model_endpoint_serves_the_files_unchanged(client):
    body = client.get("/api/v1/model").json()
    model_dir = default_model_dir()
    card = json.loads((model_dir / "model_card.json").read_text(encoding="utf-8"))
    spec = json.loads((model_dir / "feature_spec.json").read_text(encoding="utf-8"))
    assert body["model_card"] == card
    assert body["feature_spec"] == spec
    assert body["citation"]["doi"] == "10.3389/fped.2026.1801840"
    assert body["model_version"] == card["model_version"]


def test_weight_warning(client, valid_body):
    def warnings(weight):
        return client.post(PREDICT, json={**valid_body, "birth_weight_g": weight}).json()["warnings"]

    assert warnings(1500) == []
    assert warnings(1501) == ["WEIGHT_ABOVE_COHORT"]


def test_openapi_and_docs_are_self_hosted(client):
    schema = client.get("/api/openapi.json").json()
    assert {"/api/v1/health", "/api/v1/model", "/api/v1/predict"} <= set(schema["paths"])
    request_schema = schema["components"]["schemas"]["PredictRequest"]
    assert len(request_schema["required"]) == 11
    assert request_schema["additionalProperties"] is False

    page = client.get("/api/docs")
    assert page.status_code == 200
    assert "https://" not in page.text and "http://" not in page.text  # no CDN, no third party
    for asset in ("swagger-ui-bundle.js", "swagger-ui.css"):
        assert f"/api/docs/assets/{asset}" in page.text
        assert client.get(f"/api/docs/assets/{asset}").status_code == 200


def test_no_cors_headers(client, valid_body):
    response = client.post(PREDICT, json=valid_body, headers={"Origin": "https://example.org"})
    assert not [h for h in response.headers if h.lower().startswith("access-control-")]
    preflight = client.options(
        PREDICT, headers={"Origin": "https://example.org", "Access-Control-Request-Method": "POST"}
    )
    assert "access-control-allow-origin" not in preflight.headers


def test_unknown_path_and_method_use_error_codes(client):
    assert client.get("/api/v1/nope").json() == {"errors": [{"field": None, "code": "not_found"}]}
    assert client.get(PREDICT).json() == {"errors": [{"field": None, "code": "method_not_allowed"}]}
