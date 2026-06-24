# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The accounting domain — the first batch of concrete artifacts. "Czym jest faktura, czym jest
# rachunek": each is a Pydantic model registered under a stable id so any query can pull its
# expected structure over artifact://host/schema/query/get?name=faktura. These mirror the
# fields the invoice:// connector already extracts, so a parsed invoice validates straight
# against Faktura. Add the next hundreds of artifacts the same way — one class + one decorator.

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import Artifact, Address, LineItem, Party
from .enums import Currency, VatRate
from ..registry import artifact


class RateAmount(Artifact):
    """Net + VAT for a single VAT rate (the per-rate breakdown a VAT register/JPK needs)."""

    rate: VatRate = Field(description="VAT rate code")
    net: float | None = Field(default=None, description="Net for this rate (P_13_x)")
    vat: float | None = Field(default=None, description="VAT for this rate (P_14_x)")


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
    byRate: list[RateAmount] = Field(default_factory=list, description="Per-VAT-rate net/VAT breakdown")
    source: str | None = Field(default=None, description="How it was obtained: regex | regex+llm | ksef")
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


@artifact("invoice-draft", domain="accounting", title="Invoice draft",
          keywords=("draft", "faktura", "receipt", "ksef", "bridge"))
class InvoiceDraft(Artifact):
    """A KSeF-ready invoice draft built from a receipt/paragon — the bridge from
    camera://host/receipt to the FA(2) flow (mirrors invoice:// receipt_draft output)."""

    type: str = Field(default="invoice-draft", description="Always 'invoice-draft'")
    source: str = Field(default="receipt", description="Where the draft came from")
    number: str | None = Field(default=None, description="Invoice number")
    issueDate: str | None = Field(default=None, description="Issue date YYYY-MM-DD")
    seller: str | None = Field(default=None, description="Seller name")
    sellerNip: str | None = Field(default=None, description="Seller NIP (10 digits)")
    buyerNip: str | None = Field(default=None, description="Buyer NIP")
    currency: str = Field(default="PLN", description="ISO-4217 currency code")
    vatRate: float = Field(default=23.0, description="VAT rate used to derive net/VAT from gross")
    items: list[dict[str, Any]] = Field(default_factory=list, description="Receipt items")
    itemsSum: float | None = Field(default=None, description="Sum of item prices")
    net: float | None = Field(default=None, description="Derived net")
    vat: float | None = Field(default=None, description="Derived VAT")
    gross: float | None = Field(default=None, description="Gross total")
    ksefReady: bool = Field(default=False, description="True when NIP + gross are present")


@artifact("ksef-upo", domain="accounting", title="KSeF UPO (confirmation)",
          keywords=("ksef", "upo", "confirmation", "poswiadczenie"))
class KsefUpo(Artifact):
    """A KSeF UPO (Urzędowe Poświadczenie Odbioru) — the confirmation KSeF returns after a
    submission, carrying the assigned KSeF number (mirrors invoice:// ksef_upo)."""

    ksefNumber: str | None = Field(default=None, description="Assigned KSeF number")
    referenceNumber: str | None = Field(default=None, description="Session/element reference number")
    timestamp: str | None = Field(default=None, description="Acquisition timestamp")
    invoiceNumber: str | None = Field(default=None, description="Invoice number")
    invoiceHash: str | None = Field(default=None, description="Document hash")
    nip: str | None = Field(default=None, description="Seller NIP")


@artifact("vat-register-row", domain="accounting", title="VAT register row",
          keywords=("vat", "register", "ewidencja", "jpk", "ksef"))
class VatRegisterRow(Artifact):
    """One row of a VAT register (ewidencja → JPK), aggregated from KSeF invoices (mirrors
    invoice:// ksef_register row)."""

    file: str | None = Field(default=None, description="Source file name")
    number: str | None = Field(default=None, description="Invoice number")
    issueDate: str | None = Field(default=None, description="Issue date")
    sellerNip: str | None = Field(default=None, description="Seller NIP")
    sellerName: str | None = Field(default=None, description="Seller name")
    buyerNip: str | None = Field(default=None, description="Buyer NIP")
    net: float | None = Field(default=None, description="Net amount")
    vat: float | None = Field(default=None, description="VAT amount")
    gross: float | None = Field(default=None, description="Gross amount")
    currency: str = Field(default="PLN", description="ISO-4217 currency code")


@artifact("faktura-ksef", domain="accounting", title="KSeF FA(2) faktura",
          keywords=("ksef", "fa", "fa_vat", "faktura", "xml", "byrate"))
class FakturaKSeF(Artifact):
    """A faktura parsed from a KSeF FA_VAT/FA(2) XML — exact fields (no OCR), including the
    per-rate breakdown (mirrors invoice:// _parse_fa_vat)."""

    formCode: str | None = Field(default=None, description="KodFormularza, e.g. FA")
    variant: str | None = Field(default=None, description="WariantFormularza, e.g. 2")
    seller: Party = Field(description="Podmiot1 (seller)")
    buyer: Party = Field(description="Podmiot2 (buyer)")
    number: str | None = Field(default=None, description="P_2 invoice number")
    issueDate: str | None = Field(default=None, description="P_1 issue date")
    saleDate: str | None = Field(default=None, description="P_6 sale date")
    currency: str = Field(default="PLN", description="KodWaluty")
    net: float | None = Field(default=None, description="Total net (sum P_13_x)")
    vat: float | None = Field(default=None, description="Total VAT (sum P_14_x)")
    gross: float | None = Field(default=None, description="P_15 gross")
    byRate: list[RateAmount] = Field(default_factory=list, description="Per-rate net/VAT breakdown")


__all__ = ["Faktura", "Rachunek", "Paragon", "RateAmount", "InvoiceDraft", "KsefUpo",
           "VatRegisterRow", "FakturaKSeF"]
