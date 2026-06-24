# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# A second domain, on purpose: artifacts are not only accounting objects. The same registry
# holds documents, contacts, logistics, HR... — this file shows the pattern scaling past one
# domain so "setki różnych obiektów" all answer the same artifact:// routes.

from __future__ import annotations

from pydantic import Field

from .base import Artifact, Address, Party
from ..registry import artifact


@artifact("document", domain="documents", title="Generic document",
          keywords=("document", "scan", "file", "ocr"))
class Document(Artifact):
    """A scanned/ingested document the office flow has not yet specialised — the catch-all
    an unknown scan validates against before it is reclassified as a faktura/paragon/..."""

    docType: str = Field(default="unknown", description="Detected type, e.g. invoice, contract, letter")
    title: str | None = Field(default=None, description="Document title, if any")
    date: str | None = Field(default=None, description="Document date YYYY-MM-DD")
    party: Party | None = Field(default=None, description="Primary party (contractor/supplier)")
    sourcePath: str | None = Field(default=None, description="Path/URI the document was ingested from")
    text: str | None = Field(default=None, description="Extracted OCR/text body")
    pages: int | None = Field(default=None, description="Page count")


@artifact("contact", domain="contacts", title="Contact / business partner",
          keywords=("contact", "partner", "person", "company", "crm"))
class Contact(Artifact):
    """A business partner — a counterparty referenced by accounting artifacts (the seller on
    one faktura is the contact on a CRM card)."""

    name: str = Field(description="Person or company name")
    nip: str | None = Field(default=None, description="Tax id, if a company")
    email: str | None = Field(default=None, description="Primary email")
    phone: str | None = Field(default=None, description="Primary phone")
    address: Address | None = Field(default=None, description="Postal address")
    isCompany: bool = Field(default=True, description="True for a company, False for a private person")


__all__ = ["Document", "Contact"]
