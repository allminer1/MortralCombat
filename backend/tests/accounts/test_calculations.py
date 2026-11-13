import csv
import io
import logging

import pytest

BASE = "/api/v1/calculations"


def test_saved_result_is_computed_by_the_server(sign_in, inputs, golden):
    carol = sign_in("carol@example.test")
    saved = carol.save(inputs, "CASE-7")
    assert saved.status_code == 201
    item = saved.json()
    reference = next(c for c in golden["cases"] if c["id"] == "anchor_figure_8")
    assert abs(item["outputs"]["log_risk"] - reference["log_risk"]) <= 1e-4
    assert (
        max(abs(a - b) for a, b in zip(item["outputs"]["curve"], reference["survival"], strict=True)) <= 1e-5
    )
    assert item["inputs"] == inputs
    assert item["case_code"] == "CASE-7"
    assert item["model_version"] == "deepsurv-vlbw-1.0.0"

    fetched = carol.client.get(f"{BASE}/{item['id']}").json()
    assert fetched == item
    listed = carol.client.get(BASE).json()["items"]
    assert len(listed) == 1 and "curve" not in listed[0]["outputs"]


def test_client_cannot_supply_outputs_or_extra_fields(sign_in, inputs):
    carol = sign_in("carol@example.test")
    for extra in ({"outputs": {"log_risk": -9}}, {"notes": "free text"}, {"patient_name": "x"}):
        answer = carol.client.post(BASE, json={"inputs": inputs} | extra, headers=carol.headers)
        assert answer.status_code == 422
        assert answer.json()["errors"][0]["code"] == "unknown_field"
    answer = carol.client.post(BASE, json={"inputs": inputs | {"notes": "x"}}, headers=carol.headers)
    assert answer.json()["errors"] == [{"field": "notes", "code": "unknown_field"}]


def test_inputs_are_validated_like_predict(sign_in, inputs, spec):
    carol = sign_in("carol@example.test")
    weight = next(f for f in spec.features if f.api_field == "birth_weight_g")
    answer = carol.save(inputs | {"birth_weight_g": weight.max + 1})
    assert answer.status_code == 422
    assert answer.json()["errors"] == [
        {"field": "birth_weight_g", "code": "out_of_range", "min": weight.min, "max": weight.max}
    ]
    assert carol.client.get(BASE).json() == {"items": []}


@pytest.mark.parametrize("code", ["A", "CASE-7", "nicu_2026-001", "x" * 32])
def test_case_code_accepted(sign_in, inputs, code):
    assert sign_in("carol@example.test").save(inputs, code).status_code == 201


@pytest.mark.parametrize(
    "code",
    ["", "x" * 33, "Ivan Petrov", "Иванов", "a b", "=1+1", "-7", "_x", "a,b", "a;b", "a\nb", "a@b.c", "12.5"],
)
def test_case_code_rejected(sign_in, inputs, code):
    """No spaces, no punctuation, Latin letters and digits only: not a place for a name,
    a sentence, or a spreadsheet formula."""
    answer = sign_in("carol@example.test").save(inputs, code)
    assert answer.status_code == 422
    assert answer.json()["errors"][0]["field"] == "case_code"


def test_case_code_groups_a_timeline(sign_in, inputs):
    carol = sign_in("carol@example.test")
    first = carol.save(inputs | {"nec": False}, "CASE-7").json()["id"]
    second = carol.save(inputs, "CASE-7").json()["id"]
    carol.save(inputs, "CASE-8")
    carol.save(inputs)
    timeline = carol.client.get(BASE, params={"case_code": "CASE-7"}).json()["items"]
    assert [i["id"] for i in timeline] == [second, first]  # newest first
    assert len(carol.client.get(BASE).json()["items"]) == 4


def test_delete_own_item(sign_in, inputs):
    carol = sign_in("carol@example.test")
    item = carol.save(inputs).json()["id"]
    assert carol.client.delete(f"{BASE}/{item}", headers=carol.headers).status_code == 204
    assert carol.client.get(f"{BASE}/{item}").status_code == 404
    assert carol.client.delete(f"{BASE}/{item}", headers=carol.headers).status_code == 404


def test_export_columns(sign_in, inputs, spec):
    carol = sign_in("carol@example.test")
    carol.save(inputs | {"birth_weight_g": 1600}, "CASE-7")
    rows = list(csv.DictReader(io.StringIO(carol.client.get(f"{BASE}/export.csv").text)))
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == {
        "id", "created_at", "case_code", "model_version", *spec.api_fields,
        "log_risk", "day_7", "day_28", "day_100", "warnings",
    }  # fmt: skip
    assert row["case_code"] == "CASE-7" and row["birth_weight_g"] == "1600"
    assert row["warnings"] == "WEIGHT_ABOVE_COHORT"
    assert 0 < float(row["day_100"]) < float(row["day_28"]) < float(row["day_7"]) < 1


def test_nothing_personal_reaches_the_logs(make_client, make_user, inputs, caplog, capsys):
    """No password, e-mail, case code, input value or session token in any log line."""
    caplog.set_level(logging.DEBUG)
    email, password = make_user("zoe.marker@example.test")
    client = make_client()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}
    client.post(
        BASE, json={"inputs": inputs | {"birth_weight_g": 1483}, "case_code": "MARKER-9Q"}, headers=headers
    )
    client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-MARKERPASS-1"})
    client.get(BASE, params={"case_code": "MARKER-9Q"})
    client.get(f"{BASE}/export.csv")

    records = [r for r in caplog.records if not r.name.startswith(("httpx", "httpx2", "httpcore"))]
    text = "\n".join(f"{r.name} {r.getMessage()}" for r in records) + "".join(capsys.readouterr())
    assert "path=/api/v1/calculations status=201" in text
    assert "errors=invalid_credentials" in text
    token = next(iter(client.cookies.values()))
    for secret in (password, "MARKERPASS", "zoe.marker", "MARKER-9Q", "1483", token, headers["X-CSRF-Token"]):
        assert secret not in text
