# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Base building blocks for every artifact. Artifacts are Pydantic models (the single source
# of truth) — JSON Schema, an example instance and a .proto message are all *derived* from
# them, so the four representations the office flow needs (pydantic / json-schema / protobuf /
# grpc) can never drift from one another. The reusable value objects below (Money, Address,
# Party, LineItem) are shared by hundreds of concrete artifacts so a faktura and a rachunek
# describe a "seller" the same way.

from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    """Marker base for every registered artifact type.

    The class-level ``__artifact_*`` attributes are descriptive metadata the registry reads;
    they are *not* model fields, so they never appear in the data/JSON-Schema. Concrete
    artifacts set them via the :func:`urirun_artifacts.registry.artifact` decorator, so an
    author writes a plain Pydantic model and the registry fills in id/domain/version.
    """

    __artifact_id__: ClassVar[str] = ""
    __artifact_domain__: ClassVar[str] = "generic"
    __artifact_version__: ClassVar[str] = "0.1.0"
    __artifact_title__: ClassVar[str] = ""
    __artifact_keywords__: ClassVar[tuple[str, ...]] = ()

    model_config = {"extra": "forbid"}


class Money(BaseModel):
    """An amount with its ISO-4217 currency — never a bare float, so 100 PLN and 100 EUR
    can't be silently added across artifacts."""

    amount: float = Field(description="Numeric amount, rounded to the currency's minor unit")
    currency: str = Field(default="PLN", min_length=3, max_length=3,
                          description="ISO-4217 code, e.g. PLN, EUR, USD")


class Address(BaseModel):
    """A postal address (KSeF FA(2) Adres maps onto this)."""

    countryCode: str = Field(default="PL", min_length=2, max_length=2, description="ISO-3166 alpha-2")
    line1: str = Field(default="", description="Street, building, flat")
    line2: str = Field(default="", description="Optional second address line")
    postalCode: str = Field(default="", description="e.g. 00-001")
    city: str = Field(default="", description="City / town")


class Party(BaseModel):
    """A business or person on a document — seller, buyer, issuer, recipient."""

    name: str = Field(default="", description="Legal or full name")
    nip: str | None = Field(default=None, description="Polish tax id (10 digits), or None")
    vatId: str | None = Field(default=None, description="EU VAT id incl. country prefix, or None")
    address: Address | None = Field(default=None, description="Postal address, if known")


class LineItem(BaseModel):
    """One line of a document (an invoice/receipt position)."""

    name: str = Field(description="Item / service description")
    quantity: float = Field(default=1.0, description="Quantity (P_8B on a faktura)")
    unit: str = Field(default="szt", description="Unit of measure")
    unitNet: float | None = Field(default=None, description="Net unit price")
    vatRate: float = Field(default=23.0, description="VAT rate in percent (23, 8, 5, 0)")
    net: float | None = Field(default=None, description="Line net amount")
    vat: float | None = Field(default=None, description="Line VAT amount")
    gross: float | None = Field(default=None, description="Line gross amount")


# A small alias used by the proto generator and docs so dates are obvious in derived schemas.
ISODate = date


__all__ = ["Artifact", "Money", "Address", "Party", "LineItem", "ISODate"]
