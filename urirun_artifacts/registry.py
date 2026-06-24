# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The artifact registry: a name → Pydantic-model index that the artifact:// connector reads.
# Authors register a model with the @artifact decorator; everything else (JSON Schema, an
# example instance, the .proto message) is derived on demand from that one model, so the four
# representations the office flow wants can never disagree. Designed to hold hundreds of types.

from __future__ import annotations

from typing import Any, Callable, Type, TypeVar

from pydantic import BaseModel

_T = TypeVar("_T", bound=BaseModel)

# id -> model class. Insertion order is preserved so listings are stable.
_REGISTRY: dict[str, Type[BaseModel]] = {}


def artifact(artifact_id: str, *, domain: str = "generic", title: str = "",
             version: str = "0.1.0", keywords: tuple[str, ...] = ()) -> Callable[[Type[_T]], Type[_T]]:
    """Class decorator that registers a Pydantic model as an artifact type.

    Stores the metadata on the class (``__artifact_*``) and indexes it by ``artifact_id``::

        @artifact("faktura", domain="accounting", title="Faktura VAT")
        class Faktura(Artifact):
            number: str
            ...
    """

    def _register(model: Type[_T]) -> Type[_T]:
        if not artifact_id:
            raise ValueError("artifact id must be non-empty")
        existing = _REGISTRY.get(artifact_id)
        if existing is not None and existing is not model:
            raise ValueError(f"artifact id '{artifact_id}' already registered to {existing.__name__}")
        model.__artifact_id__ = artifact_id          # type: ignore[attr-defined]
        model.__artifact_domain__ = domain           # type: ignore[attr-defined]
        model.__artifact_title__ = title or model.__name__  # type: ignore[attr-defined]
        model.__artifact_version__ = version         # type: ignore[attr-defined]
        model.__artifact_keywords__ = tuple(keywords)  # type: ignore[attr-defined]
        _REGISTRY[artifact_id] = model
        return model

    return _register


def get(artifact_id: str) -> Type[BaseModel] | None:
    """Return the model registered under ``artifact_id`` (or None)."""
    return _REGISTRY.get(artifact_id)


def all_ids() -> list[str]:
    """All registered artifact ids, in registration order."""
    return list(_REGISTRY)


def items() -> list[tuple[str, Type[BaseModel]]]:
    """(id, model) pairs for every registered artifact."""
    return list(_REGISTRY.items())


def info(artifact_id: str) -> dict[str, Any] | None:
    """The descriptive metadata of one artifact (id, domain, title, version, keywords)."""
    model = _REGISTRY.get(artifact_id)
    if model is None:
        return None
    return {
        "id": getattr(model, "__artifact_id__", artifact_id),
        "domain": getattr(model, "__artifact_domain__", "generic"),
        "title": getattr(model, "__artifact_title__", model.__name__),
        "version": getattr(model, "__artifact_version__", "0.1.0"),
        "keywords": list(getattr(model, "__artifact_keywords__", ())),
        "model": model.__name__,
    }


def domains() -> dict[str, list[str]]:
    """Map each domain to the artifact ids it contains."""
    out: dict[str, list[str]] = {}
    for aid, model in _REGISTRY.items():
        out.setdefault(getattr(model, "__artifact_domain__", "generic"), []).append(aid)
    return out


__all__ = ["artifact", "get", "all_ids", "items", "info", "domains"]
