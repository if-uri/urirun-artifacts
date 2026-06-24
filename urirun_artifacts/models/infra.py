# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The infra domain: the audit-trail and monitoring records the host writes. Registered so the
# ledger line, a domain-check result and a host_db dataset/record have a schema to validate
# against and to attach to a query.

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import Artifact
from .enums import CheckStatus, LedgerEvent
from ..registry import artifact


@artifact("ledger-entry", domain="infra", title="Ledger entry",
          keywords=("ledger", "audit", "transaction", "event"))
class LedgerEntry(Artifact):
    """One line of the shared transaction ledger (~/.urirun/ledger.jsonl) the connectors append
    to. `extra` carries the event-specific fields (gross, nip, ksefNumber, ...)."""

    ts: float = Field(description="Epoch timestamp")
    connector: str = Field(description="Connector that wrote the line")
    event: LedgerEvent = Field(description="Event kind")
    live: bool = Field(default=False, description="False — the ledger only holds frozen artifacts")
    extra: dict[str, Any] = Field(default_factory=dict, description="Event-specific fields")


@artifact("domain-check", domain="infra", title="Domain check result",
          keywords=("domain", "monitor", "http", "dns", "health"))
class DomainCheckResult(Artifact):
    """The result of monitoring a domain — HTTP + DNS status and any mismatches (mirrors
    domain_monitor.check_domain)."""

    ok: bool = Field(description="Overall pass/fail")
    domain: str = Field(description="Checked domain")
    url: str | None = Field(default=None, description="Checked URL")
    status: CheckStatus = Field(default=CheckStatus.UNKNOWN, description="Outcome state")
    http: dict[str, Any] = Field(default_factory=dict, description="{ok, status, elapsedMs, headers|error}")
    dns: dict[str, Any] = Field(default_factory=dict, description="{ok, records:{A,AAAA}, provider}")
    dnsMismatches: list[dict[str, Any]] = Field(default_factory=list, description="[{type, expected, actual}]")
    screenshot: str | None = Field(default=None, description="Path to a captured screenshot artifact")


@artifact("dataset", domain="infra", title="Dataset",
          keywords=("dataset", "schema", "host_db", "records"))
class Dataset(Artifact):
    """A host_db dataset descriptor: a named, schema-validated collection of records."""

    id: str | None = Field(default=None, description="Dataset id")
    name: str = Field(description="Dataset name")
    description: str = Field(default="", description="What the dataset holds")
    recordSchema: dict[str, Any] = Field(default_factory=dict, description="JSON Schema for records")
    created_at: str | None = Field(default=None, description="Creation timestamp")


@artifact("dataset-record", domain="infra", title="Dataset record",
          keywords=("record", "dataset", "row", "host_db"))
class DatasetRecord(Artifact):
    """One record stored in a dataset, validated against the dataset's schema."""

    key: str = Field(description="Record key (unique within the dataset)")
    data: dict[str, Any] = Field(default_factory=dict, description="The record payload")
    source_uri: str | None = Field(default=None, description="URI the record came from")
    confidence: float | None = Field(default=None, description="Extraction confidence 0..1")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")


__all__ = ["LedgerEntry", "DomainCheckResult", "Dataset", "DatasetRecord"]
