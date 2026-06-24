# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# artifact:// connector — a URI in front of the artifact registry, so any urirun query can
# pull the *expected data structure* for a domain object (faktura, rachunek, paragon, ...) and
# attach it as context. Pydantic is the source of truth; this connector serves the derived
# JSON Schema (for validation/LLM tool-args), the .proto (for gRPC/cross-language), an example
# instance, and validates a payload against a named artifact. Hundreds of artifacts, one scheme.
#
#   artifact://host/registry/query/list                     → every artifact (id, domain, title)
#   artifact://host/registry/query/domains                  → domain → ids map
#   artifact://host/registry/query/search?q=faktura         → fuzzy search the registry
#   artifact://host/schema/query/get?name=faktura&fmt=...   → schema in json-schema|pydantic|proto
#   artifact://host/schema/query/example?name=faktura       → minimal example instance
#   artifact://host/schema/query/validate?name=faktura      → validate `data` (JSON) against it

from __future__ import annotations

import json
from typing import Any

import urirun

# Importing the models package registers every @artifact via its decorators (side effect).
from . import models as _models  # noqa: F401
from . import registry
from .protobuf import model_to_proto

CONNECTOR_ID = "artifact"
ARTIFACT = urirun.connector(CONNECTOR_ID, scheme="artifact", target="host",
                            meta={"label": "Artifact data-model registry"})


# --- example-instance generation (derived from the JSON Schema, so it scales to any model) ---
def _example_from_schema(schema: dict[str, Any], defs: dict[str, Any], depth: int = 0) -> Any:
    """Build a minimal valid-ish example value for a (sub)schema. Uses declared defaults and
    examples first, then type-based placeholders. Bounded depth guards self-referential models."""
    if depth > 6:
        return None
    if "default" in schema and schema["default"] is not None:
        return schema["default"]
    if schema.get("examples"):
        return schema["examples"][0]
    ref = schema.get("$ref")
    if ref:
        return _example_from_schema(defs.get(ref.rsplit("/", 1)[-1], {}), defs, depth + 1)
    for key in ("anyOf", "oneOf"):
        for branch in schema.get(key, []):
            if branch.get("type") != "null":
                return _example_from_schema(branch, defs, depth + 1)
    typ = schema.get("type")
    if typ == "object" or "properties" in schema:
        return {p: _example_from_schema(s if isinstance(s, dict) else {}, defs, depth + 1)
                for p, s in (schema.get("properties") or {}).items()}
    if typ == "array":
        return [_example_from_schema(schema.get("items") or {}, defs, depth + 1)]
    if schema.get("format") == "date":
        return "2026-06-24"
    return {"integer": 0, "number": 0.0, "boolean": False, "string": ""}.get(typ, None)


def _resolve(name: str) -> Any:
    return registry.get((name or "").strip())


@ARTIFACT.handler("registry/query/list", isolated=True,
                  meta={"label": "List every registered artifact type", "cliAlias": "list"})
def list_artifacts(domain: str = "") -> dict[str, Any]:
    """List all registered artifacts (id, domain, title, version, keywords). Filter by
    `domain` (e.g. accounting) to narrow it down."""
    rows = [registry.info(aid) for aid in registry.all_ids()]
    if domain:
        rows = [r for r in rows if r and r["domain"] == domain]
    return {"ok": True, "connector": CONNECTOR_ID, "kind": "registry", "live": False,
            "count": len(rows), "artifacts": rows}


@ARTIFACT.handler("registry/query/domains", isolated=True,
                  meta={"label": "Group artifacts by domain", "cliAlias": "domains"})
def list_domains() -> dict[str, Any]:
    """Map each domain (accounting, documents, contacts, ...) to the artifact ids it holds."""
    d = registry.domains()
    return {"ok": True, "connector": CONNECTOR_ID, "kind": "domains", "live": False,
            "count": len(d), "domains": d}


@ARTIFACT.handler("registry/query/search", isolated=True,
                  meta={"label": "Search the artifact registry by id/title/keyword", "cliAlias": "search"})
def search(q: str = "") -> dict[str, Any]:
    """Find artifacts whose id, title, domain or keywords contain `q` (case-insensitive)."""
    needle = (q or "").strip().lower()
    hits = []
    for aid in registry.all_ids():
        meta = registry.info(aid) or {}
        haystack = " ".join([aid, meta.get("title", ""), meta.get("domain", ""),
                             " ".join(meta.get("keywords", []))]).lower()
        if not needle or needle in haystack:
            hits.append(meta)
    return {"ok": True, "connector": CONNECTOR_ID, "kind": "search", "live": False,
            "query": q, "count": len(hits), "artifacts": hits}


@ARTIFACT.handler("schema/query/get", isolated=True,
                  meta={"label": "Get an artifact's schema (json-schema | pydantic | proto)", "cliAlias": "schema"})
def get_schema(name: str = "", fmt: str = "json-schema") -> dict[str, Any]:
    """Return the structure of artifact `name` in `fmt`: `json-schema` (Draft 2020-12, the
    default — attach it to a query so the LLM/validator knows the expected shape), `pydantic`
    (the field list with types/defaults), or `proto` (a proto3 message for gRPC). This is the
    route a query uses to embed an artifact's expected data structure as context."""
    model = _resolve(name)
    if model is None:
        return {"ok": False, "error": f"unknown artifact '{name}'", "connector": CONNECTOR_ID,
                "known": registry.all_ids()}
    meta = registry.info(name)
    fmt = (fmt or "json-schema").lower()
    if fmt in ("json-schema", "jsonschema", "json"):
        schema = model.model_json_schema(ref_template="#/$defs/{model}")
        return {"ok": True, "connector": CONNECTOR_ID, "kind": "schema", "live": False,
                "artifact": meta, "format": "json-schema", "schema": schema}
    if fmt in ("proto", "protobuf", "grpc"):
        return {"ok": True, "connector": CONNECTOR_ID, "kind": "schema", "live": False,
                "artifact": meta, "format": "proto", "proto": model_to_proto(model)}
    if fmt == "pydantic":
        def _default(f: Any) -> Any:
            # default_factory / required fields carry PydanticUndefined — not JSON-serialisable.
            d = f.get_default(call_default_factory=True)
            try:
                json.dumps(d)
                return d
            except (TypeError, ValueError):
                return None
        fields = {fname: {"type": str(f.annotation), "required": f.is_required(),
                          "default": None if f.is_required() else _default(f),
                          "description": f.description}
                  for fname, f in model.model_fields.items()}
        return {"ok": True, "connector": CONNECTOR_ID, "kind": "schema", "live": False,
                "artifact": meta, "format": "pydantic", "model": model.__name__, "fields": fields}
    return {"ok": False, "error": f"unknown fmt '{fmt}' (use json-schema|pydantic|proto)",
            "connector": CONNECTOR_ID}


@ARTIFACT.handler("schema/query/proto", isolated=True,
                  meta={"label": "Get an artifact as a proto3 message", "cliAlias": "proto"})
def get_proto(name: str = "", package: str = "urirun.artifacts") -> dict[str, Any]:
    """Return artifact `name` as a proto3 `.proto` (one message per nested value object) under
    `package` — feed it to protoc for real gRPC stubs, or wrap it with grpc/artifacts.proto."""
    model = _resolve(name)
    if model is None:
        return {"ok": False, "error": f"unknown artifact '{name}'", "connector": CONNECTOR_ID,
                "known": registry.all_ids()}
    return {"ok": True, "connector": CONNECTOR_ID, "kind": "proto", "live": False,
            "artifact": registry.info(name), "package": package,
            "proto": model_to_proto(model, package=package)}


@ARTIFACT.handler("schema/query/example", isolated=True,
                  meta={"label": "Get a minimal example instance of an artifact", "cliAlias": "example"})
def example(name: str = "") -> dict[str, Any]:
    """Return a minimal example instance of artifact `name`, derived from its schema — a
    starting point a flow can fill in, or a fixture for tests."""
    model = _resolve(name)
    if model is None:
        return {"ok": False, "error": f"unknown artifact '{name}'", "connector": CONNECTOR_ID,
                "known": registry.all_ids()}
    schema = model.model_json_schema(ref_template="#/$defs/{model}")
    sample = _example_from_schema(schema, schema.get("$defs", {}))
    return {"ok": True, "connector": CONNECTOR_ID, "kind": "example", "live": False,
            "artifact": registry.info(name), "example": sample}


@ARTIFACT.handler("schema/query/validate", isolated=True,
                  meta={"label": "Validate a payload against a named artifact", "cliAlias": "validate"})
def validate(name: str = "", data: str = "") -> dict[str, Any]:
    """Validate `data` (a JSON object string) against artifact `name`. Returns ok=true with the
    normalised object, or ok=false with per-field errors — the gate before a flow trusts a
    parsed faktura/paragon. Reuses the same Pydantic model the schema/proto are derived from."""
    model = _resolve(name)
    if model is None:
        return {"ok": False, "error": f"unknown artifact '{name}'", "connector": CONNECTOR_ID,
                "known": registry.all_ids()}
    try:
        payload = json.loads(data) if data else {}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"data is not valid JSON: {exc}", "connector": CONNECTOR_ID}
    if not isinstance(payload, dict):
        return {"ok": False, "error": "data must be a JSON object", "connector": CONNECTOR_ID}
    try:
        obj = model.model_validate(payload)
    except Exception as exc:  # pydantic.ValidationError and friends
        errors = getattr(exc, "errors", lambda: None)()
        norm = [{"field": ".".join(str(p) for p in e.get("loc", ())), "message": e.get("msg")}
                for e in errors] if errors else [{"field": "", "message": str(exc)}]
        return {"ok": True, "connector": CONNECTOR_ID, "kind": "validation", "live": False,
                "artifact": registry.info(name), "valid": False, "errors": norm,
                "errorCount": len(norm)}
    return {"ok": True, "connector": CONNECTOR_ID, "kind": "validation", "live": False,
            "artifact": registry.info(name), "valid": True,
            "normalised": obj.model_dump(mode="json")}


@ARTIFACT.handler("request/query/check", isolated=True,
                  meta={"label": "Check a human's chat request against an artifact type", "cliAlias": "request-check"})
def request_check(artifact: str = "", data: str = "") -> dict[str, Any]:
    """Validate what a human asked for in chat. Given the target `artifact` type (e.g. faktura)
    and the `fields` extracted from their prompt (`data`, a JSON object), report which required
    fields are present, which are still missing, which are unknown, and whether the request is
    ready to act on. This is the gate the chat planner uses to decide whether to ask a follow-up
    question. Required = the artifact's required fields that have no default."""
    model = _resolve(artifact)
    if model is None:
        return {"ok": False, "error": f"unknown artifact '{artifact}'", "connector": CONNECTOR_ID,
                "known": registry.all_ids()}
    try:
        provided = json.loads(data) if data else {}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"data is not valid JSON: {exc}", "connector": CONNECTOR_ID}
    if not isinstance(provided, dict):
        return {"ok": False, "error": "data must be a JSON object", "connector": CONNECTOR_ID}

    required = {name for name, f in model.model_fields.items() if f.is_required()}
    known = set(model.model_fields)
    given = set(provided)
    present = sorted(required & given)
    missing = sorted(required - given)
    extra = sorted(given - known)

    # Type-check the fields that were given (without enforcing the missing required ones).
    errors: list[dict[str, Any]] = []
    try:
        model.model_validate(provided)
    except Exception as exc:  # pydantic.ValidationError
        rows = getattr(exc, "errors", lambda: [])()
        for e in rows:
            field = ".".join(str(p) for p in e.get("loc", ()))
            # a "missing" error is already captured by `missing`; keep only real type errors
            if e.get("type") != "missing":
                errors.append({"field": field, "message": e.get("msg")})

    valid = not missing and not errors
    return {"ok": True, "connector": CONNECTOR_ID, "kind": "request-check", "live": False,
            "artifactType": artifact, "valid": valid, "present": present,
            "missingRequired": missing, "extra": extra, "errors": errors}


def main(argv: list[str] | None = None) -> int:
    return ARTIFACT.cli(argv, manifest_prose=urirun.load_manifest(__package__))


urirun_bindings = ARTIFACT.bindings
