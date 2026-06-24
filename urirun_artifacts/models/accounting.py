# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The accounting domain — the first batch of concrete artifacts. "Czym jest faktura, czym jest
# rachunek": each is a Pydantic model registered under a stable id so any query can pull its
# expected structure over artifact://host/schema/query/get?name=faktura. These mirror the
# fields the invoice:// connector already extracts, so a parsed invoice validates straight
# against Faktura. Add the next hundreds of artifacts the same way — one class + one decorator.

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from .base import Artifact, Address, LineItem, Party
from ..registry import artifact


@artifact("faktura", domain="accounting", title="Faktura VAT",
          keywords=("faktura", "vat", "invoice", "nip", "ksef"))
class Faktura(Artifact):
    """A Polish VAT invoice (faktura). Net/VAT/gross totals plus seller/buyer parties and
    line items — the structure a KSeF FA(2) document and the invoice:// parser share."""

    number: str = Field(description="Invoice number, e.g. FV 7/2026 (P_2)")
    issueDate: str = Field(description="Issue date YYYY-MM-DD (P_1)")
    saleDate: str | None = Field(default=None, description="Sale/delivery date YYYY-MM-DD (P_6)")
    seller: Party = Field(description="Sprzedawca (Podmiot1)")
    buyer: Party = Field(description="Nabywca (Podmiot2)")
    currency: str = Field(default="PLN", description="ISO-4217 currency code (KodWaluty)")
    items: list[LineItem] = Field(default_factory=list, description="Invoice positions (FaWiersz)")
    net: float | None = Field(default=None, description="Total net amount (sum of P_13_x)")
    vat: float | None = Field(default=None, description="Total VAT amount (sum of P_14_x)")
    gross: float | None = Field(default=None, description="Total gross amount (P_15)")
    ksefNumber: str | None = Field(default=None, description="Assigned KSeF number once submitted")


@artifact("rachunek", domain="accounting", title="Rachunek",
          keywords=("rachunek", "bill", "invoice-without-vat"))
class Rachunek(Artifact):
    """A bill (rachunek) — issued by a non-VAT payer, so there is a single total and no
    per-rate VAT breakdown, unlike a faktura."""

    number: str = Field(description="Bill number")
    issueDate: str = Field(description="Issue date YYYY-MM-DD")
    issuer: Party = Field(description="Wystawca")
    recipient: Party = Field(description="Odbiorca")
    currency: str = Field(default="PLN", description="ISO-4217 currency code")
    items: list[LineItem] = Field(default_factory=list, description="Bill positions")
    total: float | None = Field(default=None, description="Amount due (no VAT split)")


@artifact("paragon", domain="accounting", title="Paragon fiskalny",
          keywords=("paragon", "receipt", "fiscal", "scan"))
class Paragon(Artifact):
    """A fiscal receipt (paragon) — the camera:// scan flow produces this, and invoice://
    turns it into a Faktura draft."""

    receiptId: str | None = Field(default=None, description="Receipt / transaction id")
    date: str | None = Field(default=None, description="Purchase date YYYY-MM-DD")
    seller: Party = Field(default_factory=Party, description="Issuing merchant")
    currency: str = Field(default="PLN", description="ISO-4217 currency code")
    items: list[LineItem] = Field(default_factory=list, description="Purchased items")
    total: float | None = Field(default=None, description="Total paid (gross)")
    fiscalNumber: str | None = Field(default=None, description="Cash-register / fiscal number")


__all__ = ["Faktura", "Rachunek", "Paragon"]
