# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The request domain: a structured view of what a human asks for in chat, so the request itself
# can be validated before the system acts on it. "Stwórz fakturę na 1230 zł dla ACME" parses
# into a RequestObject {artifactType: faktura, action: create, fields: {...}}; checking it
# against the faktura artifact's required fields yields a RequestValidation that tells the chat
# what is still missing. This is why artifacts exist — to define the objects a request is about.

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import Artifact
from ..registry import artifact


@artifact("request-object", domain="request", title="Chat request object",
          keywords=("request", "chat", "intent", "nl", "validate"))
class RequestObject(Artifact):
    """A normalised user request: which artifact type it concerns, the action, and the fields
    extracted so far from the natural-language prompt. The bridge from chat NL to a typed,
    checkable object."""

    artifactType: str = Field(description="Which artifact the request is about, e.g. 'faktura'")
    action: str = Field(default="create", description="create | find | validate | update")
    fields: dict[str, Any] = Field(default_factory=dict, description="Fields extracted from the prompt")
    freeText: str | None = Field(default=None, description="The original user prompt")


@artifact("request-validation", domain="request", title="Request validation result",
          keywords=("request", "validation", "missing", "chat"))
class RequestValidation(Artifact):
    """The outcome of checking a request against its artifact type: what is present, what
    required fields are still missing, and whether the request is ready to act on."""

    artifactType: str = Field(description="The artifact the request was checked against")
    valid: bool = Field(description="True when no required field is missing and values type-check")
    present: list[str] = Field(default_factory=list, description="Required fields that are present")
    missingRequired: list[str] = Field(default_factory=list, description="Required fields still missing")
    extra: list[str] = Field(default_factory=list, description="Provided fields not in the schema")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="[{field, message}] type errors")


__all__ = ["RequestObject", "RequestValidation"]
