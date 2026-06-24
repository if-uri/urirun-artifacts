"""Offline tests for the artifact registry connector: bindings, schema/proto derivation,
example generation and validation against the Pydantic source of truth."""
import json

import urirun_artifacts.core as c
from urirun_artifacts import registry


def test_bindings_valid():
    b = c.urirun_bindings()
    uris = set(b["bindings"])
    assert "artifact://host/schema/query/get" in uris
    assert "artifact://host/schema/query/validate" in uris
    for spec in b["bindings"].values():
        assert spec["python"]["module"].endswith("core")
        assert spec["uri"].startswith("artifact://")


def test_registry_has_core_artifacts():
    ids = registry.all_ids()
    for aid in ("faktura", "rachunek", "paragon"):
        assert aid in ids
    assert registry.info("faktura")["domain"] == "accounting"
    assert "accounting" in registry.domains()


def test_get_json_schema():
    r = c.get_schema(name="faktura", fmt="json-schema")
    assert r["ok"] and r["format"] == "json-schema"
    props = r["schema"]["properties"]
    assert "number" in props and "seller" in props and "gross" in props
    # nested value objects resolve via $defs
    assert "$defs" in r["schema"] and "Party" in r["schema"]["$defs"]


def test_get_proto_has_messages():
    r = c.get_schema(name="faktura", fmt="proto")
    assert r["ok"] and r["format"] == "proto"
    proto = r["proto"]
    assert 'syntax = "proto3";' in proto
    assert "message Party {" in proto              # nested value object
    assert "repeated LineItem items" in proto      # array → repeated nested message
    assert "message FakturaVAT {" in proto         # root message named from the artifact title


def test_unknown_artifact():
    r = c.get_schema(name="does-not-exist")
    assert r["ok"] is False and "unknown artifact" in r["error"]
    assert "faktura" in r["known"]


def test_example_instance_round_trips_through_validate():
    ex = c.example(name="paragon")
    assert ex["ok"]
    sample = ex["example"]
    assert isinstance(sample, dict) and "items" in sample
    v = c.validate(name="paragon", data=json.dumps(sample))
    assert v["ok"] and v["valid"], v.get("errors")


def test_validate_rejects_missing_required():
    # Faktura requires `number` — an empty object must fail with a field error.
    v = c.validate(name="faktura", data="{}")
    assert v["ok"] and v["valid"] is False
    fields = {e["field"] for e in v["errors"]}
    assert "number" in fields


def test_validate_accepts_invoice_like_payload():
    payload = {"number": "FV 7/2026", "issueDate": "2026-05-13",
               "seller": {"name": "ACME", "nip": "7781422455"},
               "buyer": {"name": "Klient"}, "currency": "PLN",
               "net": 1000.0, "vat": 230.0, "gross": 1230.0}
    v = c.validate(name="faktura", data=json.dumps(payload))
    assert v["ok"] and v["valid"], v.get("errors")
    assert v["normalised"]["gross"] == 1230.0


def test_search_finds_by_keyword():
    r = c.search(q="vat")
    ids = {a["id"] for a in r["artifacts"]}
    assert "faktura" in ids
