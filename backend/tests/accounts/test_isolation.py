"""Users see only their own records (spec Section 8): user A cannot read, delete or
export user B's items by guessing ids."""

import uuid

BASE = "/api/v1/calculations"


def test_other_users_item_cannot_be_read_deleted_or_listed(sign_in, inputs):
    alice = sign_in("alice@example.test")
    bob = sign_in("bob@example.test")
    bobs = bob.save(inputs, "BOB-1").json()["id"]
    alices = alice.save({**inputs, "nec": False}, "ALICE-1").json()["id"]

    # read
    assert alice.client.get(f"{BASE}/{bobs}").status_code == 404
    assert alice.client.get(f"{BASE}/{bobs}").json() == {"errors": [{"field": None, "code": "not_found"}]}
    # delete: refused, and the item is still there for its owner
    assert alice.client.delete(f"{BASE}/{bobs}", headers=alice.headers).status_code == 404
    assert bob.client.get(f"{BASE}/{bobs}").status_code == 200
    # list
    assert [i["id"] for i in alice.client.get(BASE).json()["items"]] == [alices]
    assert [i["id"] for i in bob.client.get(BASE).json()["items"]] == [bobs]
    # filtering by the other user's case code gives nothing
    assert alice.client.get(BASE, params={"case_code": "BOB-1"}).json() == {"items": []}


def test_export_contains_only_own_rows(sign_in, inputs):
    alice = sign_in("alice@example.test")
    bob = sign_in("bob@example.test")
    bobs = bob.save(inputs, "BOB-1").json()["id"]
    alices = alice.save(inputs, "ALICE-1").json()["id"]

    exported = alice.client.get(f"{BASE}/export.csv")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert alices in exported.text and "ALICE-1" in exported.text
    assert bobs not in exported.text and "BOB-1" not in exported.text
    assert len(exported.text.strip().splitlines()) == 2  # header + one row


def test_unknown_and_foreign_ids_look_the_same(sign_in, inputs):
    """A guessed id that exists (someone else's) and one that does not give the same answer."""
    alice = sign_in("alice@example.test")
    bob = sign_in("bob@example.test")
    foreign = alice.client.get(f"{BASE}/{bob.save(inputs).json()['id']}")
    missing = alice.client.get(f"{BASE}/{uuid.uuid4()}")
    assert (foreign.status_code, foreign.json()) == (missing.status_code, missing.json())


def test_admin_role_gives_no_access_to_other_users_items(sign_in, inputs):
    """`admin` is for the command line (creating users); it is not a read-all role."""
    admin = sign_in("admin@example.test", role="admin")
    bob = sign_in("bob@example.test")
    bobs = bob.save(inputs).json()["id"]
    assert admin.client.get(f"{BASE}/{bobs}").status_code == 404
    assert admin.client.get(BASE).json() == {"items": []}
    assert bobs not in admin.client.get(f"{BASE}/export.csv").text


def test_signed_out_client_gets_nothing(make_client, sign_in, inputs):
    bob = sign_in("bob@example.test")
    bobs = bob.save(inputs).json()["id"]
    anonymous = make_client()
    for path in (BASE, f"{BASE}/{bobs}", f"{BASE}/export.csv", "/api/v1/auth/me"):
        response = anonymous.get(path)
        assert response.status_code == 401, path
        assert response.json() == {"errors": [{"field": None, "code": "not_signed_in"}]}
    assert anonymous.post(BASE, json={"inputs": inputs}).status_code == 401
    assert anonymous.delete(f"{BASE}/{bobs}").status_code == 401


def test_deleting_a_user_removes_their_calculations(sign_in, inputs, db):
    from sqlalchemy import func, select

    from app.accounts import service
    from app.db.models import Calculation

    bob = sign_in("bob@example.test")
    alice = sign_in("alice@example.test")
    bob.save(inputs)
    alice.save(inputs)
    db.delete(service.find_user(db, "bob@example.test"))
    db.commit()
    assert db.scalar(select(func.count()).select_from(Calculation)) == 1
    assert bob.client.get(BASE).status_code == 401  # the session went with the user
