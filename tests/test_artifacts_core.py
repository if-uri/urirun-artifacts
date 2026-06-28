"""Offline tests for the artifact registry connector: bindings, schema/proto derivation,
example generation and validation against the Pydantic source of truth."""
import json
from pathlib import Path

import urirun_artifacts.core as c
from urirun_artifacts import registry


def test_bindings_valid():
    b = c.urirun_bindings()
    uris = set(b["bindings"])
    assert "artifact://host/schema/query/get" in uris
    assert "artifact://host/schema/query/validate" in uris
    for spec in b["bindings"].values():
        assert spec["python"]["module"].endswith("core")
        assert spec["uri"].split("://", 1)[0] in {"artifact", "schema"}


def test_schema_alias_mirrors_every_artifact_route():
    # Non-breaking split: the schema registry is ALSO addressable under schema:// (distinct
    # from the frozen-artifact file store on artifact://), reusing the same handlers.
    b = c.urirun_bindings()["bindings"]
    artifact_uris = {u for u in b if u.startswith("artifact://")}
    schema_uris = {u for u in b if u.startswith("schema://")}
    assert artifact_uris, "canonical artifact:// routes must remain"
    assert schema_uris == {"schema://" + u[len("artifact://"):] for u in artifact_uris}
    # twin routes reuse the same handler export
    assert b["schema://host/schema/query/get"]["python"]["export"] == \
        b["artifact://host/schema/query/get"]["python"]["export"]


def test_schema_alias_runs_through_compiled_registry():
    import urirun
    from urirun import v2

    registry = urirun.compile_registry(json.loads(json.dumps(c.urirun_bindings())))
    env = v2.run("schema://host/registry/query/domains", registry, payload={}, mode="execute",
                 policy=urirun.policy(allow=["schema://*"]))
    assert env["ok"] is True, env
    data = urirun.result_data(env)
    assert "accounting" in (data.get("domains") or data)


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


def test_new_domains_registered():
    ids = set(registry.all_ids())
    # one representative per new domain
    for aid in ("planned-ticket", "flow", "photo", "detected-object", "ledger-entry",
                "request-object", "invoice-draft", "ksef-upo", "faktura-ksef"):
        assert aid in ids, aid
    doms = registry.domains()
    for d in ("workflow", "scanning", "infra", "request", "accounting"):
        assert d in doms, d


# --- connector + contract examples -----------------------------------------

def _contract_kernel():
    import pytest

    return pytest.importorskip("urirun_contract")


def _artifact_contracts():
    uc = _contract_kernel()
    return {
        "schema/query/get": uc.Contract(
            version="v1",
            effect="query",
            inp={"name": "str", "fmt": "?str"},
            out={
                "ok": "const:true",
                "connector": "const:artifact",
                "kind": "const:schema",
                "live": "const:false",
                "artifact": "obj",
                "format": "enum:json-schema|proto|pydantic",
            },
            examples=(
                {
                    "payload": {"name": "faktura", "fmt": "json-schema"},
                    "result": {
                        "ok": True,
                        "connector": "artifact",
                        "kind": "schema",
                        "live": False,
                        "artifact": {"id": "faktura"},
                        "format": "json-schema",
                        "schema": {"type": "object"},
                    },
                },
            ),
        ),
        "schema/query/validate": uc.Contract(
            version="v1",
            effect="query",
            inp={"name": "str", "data": "?str"},
            out={
                "ok": "const:true",
                "connector": "const:artifact",
                "kind": "const:validation",
                "live": "const:false",
                "artifact": "obj",
                "valid": "bool",
            },
            examples=(
                {
                    "payload": {"name": "faktura", "data": "{}"},
                    "result": {
                        "ok": True,
                        "connector": "artifact",
                        "kind": "validation",
                        "live": False,
                        "artifact": {"id": "faktura"},
                        "valid": False,
                        "errors": [{"field": "number", "message": "Field required"}],
                    },
                },
            ),
        ),
    }


def test_artifact_manifest_examples_satisfy_contracts():
    uc = _contract_kernel()
    contracts = _artifact_contracts()
    uc.conform(contracts)

    manifest = json.loads((Path(c.__file__).with_name("connector.manifest.json")).read_text())
    examples = {item["uri"]: item for item in manifest["examples"]}

    get_payload = examples["artifact://host/schema/query/get"]["payload"]
    uc.check(contracts["schema/query/get"].inp, get_payload, "manifest schema payload")
    get_result = c.get_schema(**get_payload)
    assert uc.envelope_violation(contracts["schema/query/get"], get_result) is None

    validate_payload = examples["artifact://host/schema/query/validate"]["payload"]
    uc.check(contracts["schema/query/validate"].inp, validate_payload, "manifest validate payload")
    validate_result = c.validate(**validate_payload)
    assert uc.envelope_violation(contracts["schema/query/validate"], validate_result) is None


def test_artifact_contract_reaches_alias_bindings_and_mcp_output_schema():
    uc = _contract_kernel()
    import urirun
    from urirun_runtime.v2_mcp import to_mcp_tools

    contracts = _artifact_contracts()
    uc.attach_contracts(c.ARTIFACT, contracts)

    bindings = c.urirun_bindings()["bindings"]
    canonical = bindings["artifact://host/schema/query/get"]["meta"]["contract"]
    alias = bindings["schema://host/schema/query/get"]["meta"]["contract"]
    assert alias["output"] == canonical["output"]

    registry_doc = c.urirun_bindings()
    compiled = urirun.compile_registry(json.loads(json.dumps(registry_doc)))
    tools = {tool["_uri"]: tool for tool in to_mcp_tools(compiled)}
    schema_tool = tools["schema://host/schema/query/get"]
    assert schema_tool["outputSchema"]["properties"]["format"] == {
        "enum": ["json-schema", "proto", "pydantic"]
    }
    assert schema_tool["outputSchema"]["examples"][0]["format"] == "json-schema"


def test_enum_values_in_schema():
    # VAT rate / currency enums must surface their allowed values in the derived JSON Schema.
    sch = c.get_schema(name="invoice-draft", fmt="json-schema")["schema"]
    # FakturaKSeF carries byRate -> RateAmount -> VatRate enum in $defs
    fk = c.get_schema(name="faktura-ksef", fmt="json-schema")["schema"]
    defs = fk.get("$defs", {})
    rate_enum = defs.get("VatRate", {}).get("enum") or []
    assert "23" in rate_enum and "zw" in rate_enum


def test_request_check_missing_fields():
    # user asked to create a faktura but only gave a couple of fields
    r = c.request_check(artifact="faktura", data=json.dumps({"seller": {"name": "ACME"}}))
    assert r["ok"] and r["valid"] is False
    # number/issueDate/buyer are required and missing
    assert {"number", "issueDate", "buyer"}.issubset(set(r["missingRequired"]))


def test_request_check_ready_request():
    payload = {"number": "FV 1/2026", "issueDate": "2026-06-24",
               "seller": {"name": "ACME"}, "buyer": {"name": "Klient"}}
    r = c.request_check(artifact="faktura", data=json.dumps(payload))
    assert r["ok"] and r["valid"] is True and not r["missingRequired"]


def test_request_check_reports_type_error_not_missing():
    # net must be a number; a string is a type error, not a missing field
    payload = {"number": "X", "issueDate": "2026-06-24", "seller": {"name": "A"},
               "buyer": {"name": "B"}, "net": "not-a-number"}
    r = c.request_check(artifact="faktura", data=json.dumps(payload))
    fields = {e["field"] for e in r["errors"]}
    assert "net" in fields and r["valid"] is False
