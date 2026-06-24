# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Controlled vocabularies shared across artifacts. Encoding them as enums means the derived
# JSON Schema/proto carry the allowed values (so a validator/LLM rejects "23.5%" or "BTC" up
# front) instead of leaving them as free strings scattered through the connectors. These mirror
# the hardcoded maps in urirun-connector-invoice (_RATE) and the currency regex.

from __future__ import annotations

from enum import Enum


class VatRate(str, Enum):
    """Polish VAT rates incl. the special KSeF codes (ryczałt, WDT/domestic 0%, zwolnienie)."""

    R23 = "23"
    R8 = "8"
    R5 = "5"
    R0 = "0"
    RYCZALT = "ryczalt"
    WDT_0 = "0_wdt"        # 0% intra-EU supply (P_13_5/P_14_5)
    DOMESTIC_0 = "0_kraj"  # 0% domestic
    EXEMPT = "zw"          # zwolnione


class Currency(str, Enum):
    """ISO-4217 currencies the office flow recognises."""

    PLN = "PLN"
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"


class DocumentType(str, Enum):
    """Document kinds the scanner / classifier emit and the office flow routes on."""

    INVOICE = "invoice"
    RECEIPT = "receipt"
    BILL = "bill"
    CONTRACT = "contract"
    LETTER = "letter"
    PHOTO = "photo"
    UNKNOWN = "unknown"


class LedgerEvent(str, Enum):
    """Events appended to the shared transaction ledger (~/.urirun/ledger.jsonl)."""

    RECEIPT = "receipt"
    INSPECT = "inspect"
    INGEST = "ingest"
    KSEF_BUILD = "ksef_build"
    KSEF_UPO = "ksef_upo"


class ExecutorMode(str, Enum):
    """How a planned ticket's executor runs."""

    AUTOMATIC = "automatic"
    INTERACTIVE = "interactive"


class CheckStatus(str, Enum):
    """Health/monitoring outcome states."""

    OK = "ok"
    HTTP_ERROR = "http_error"
    DNS_ERROR = "dns_error"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


__all__ = ["VatRate", "Currency", "DocumentType", "LedgerEvent", "ExecutorMode", "CheckStatus"]
