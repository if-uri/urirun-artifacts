"""artifact:// connector — a URI-addressable registry of artifact data models (faktura,
rachunek, paragon, ...). Pydantic is the source of truth; JSON Schema, proto3 and example
instances are derived from it, so a query can attach any artifact's expected structure."""
from .core import (ARTIFACT, example, get_proto, get_schema, list_artifacts, list_domains,
                   main, search, urirun_bindings, validate)
from . import registry
from .registry import artifact

__all__ = ["ARTIFACT", "list_artifacts", "list_domains", "search", "get_schema", "get_proto",
           "example", "validate", "main", "urirun_bindings", "registry", "artifact"]
