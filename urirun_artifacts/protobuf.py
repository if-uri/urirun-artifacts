# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Pydantic → protobuf/gRPC. Pydantic is the source of truth (the user's choice), so this
# derives a proto3 message definition from a model's JSON Schema instead of maintaining a
# second hand-written .proto that could drift. It walks the schema, emits a `message` per
# referenced object ($defs become nested messages), and maps JSON-Schema types to proto3
# scalar/`repeated` types. The output is text you can save as .proto and feed to protoc to get
# real gRPC stubs — see grpc/artifacts.proto for the service that wraps these messages.

from __future__ import annotations

import re
from typing import Any, Type

from pydantic import BaseModel

# JSON-Schema (Draft 2020-12) type/format → proto3 scalar.
_SCALARS = {
    ("integer", None): "int64",
    ("number", None): "double",
    ("boolean", None): "bool",
    ("string", None): "string",
    ("string", "date"): "string",       # ISO date carried as a string for round-trip fidelity
    ("string", "date-time"): "string",
}


def _camel(name: str) -> str:
    """A safe proto message name from a $def key / model name."""
    parts = re.split(r"[^0-9a-zA-Z]+", name)
    return "".join(p[:1].upper() + p[1:] for p in parts if p) or "Message"


def _proto_type(schema: dict[str, Any], defs: dict[str, Any]) -> tuple[str, bool]:
    """Return (proto_type, is_repeated) for one property schema."""
    # $ref → a nested message
    ref = schema.get("$ref")
    if ref:
        return _camel(ref.rsplit("/", 1)[-1]), False
    # arrays → repeated of the item type
    if schema.get("type") == "array":
        inner, _ = _proto_type(schema.get("items") or {}, defs)
        return inner, True
    # anyOf/oneOf (Optional[...] is anyOf[T, null]) → first non-null branch
    for key in ("anyOf", "oneOf"):
        for branch in schema.get(key, []):
            if branch.get("type") != "null":
                return _proto_type(branch, defs)
    fmt = schema.get("format")
    typ = schema.get("type")
    return _SCALARS.get((typ, fmt)) or _SCALARS.get((typ, None)) or "string", False


def _message(name: str, schema: dict[str, Any], defs: dict[str, Any]) -> str:
    """Render one proto3 `message` block from an object schema."""
    lines = [f"message {name} {{"]
    for i, (prop, spec) in enumerate((schema.get("properties") or {}).items(), start=1):
        ptype, repeated = _proto_type(spec if isinstance(spec, dict) else {}, defs)
        prefix = "repeated " if repeated else ""
        lines.append(f"  {prefix}{ptype} {prop} = {i};")
    lines.append("}")
    return "\n".join(lines)


def model_to_proto(model: Type[BaseModel], *, package: str = "urirun.artifacts") -> str:
    """Render a complete proto3 file for ``model``, with one nested message per $def."""
    schema = model.model_json_schema(ref_template="#/$defs/{model}")
    defs = schema.get("$defs", {})
    root_name = _camel(getattr(model, "__artifact_title__", "") or model.__name__)
    blocks = [f'syntax = "proto3";', f"package {package};", ""]
    # Referenced value objects first (Money, Party, Address, LineItem, ...), then the root.
    for def_name, def_schema in defs.items():
        if def_schema.get("type") == "object":
            blocks.append(_message(_camel(def_name), def_schema, defs))
            blocks.append("")
    blocks.append(_message(root_name, schema, defs))
    blocks.append("")
    return "\n".join(blocks)


__all__ = ["model_to_proto"]
