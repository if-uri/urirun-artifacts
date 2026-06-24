# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The scanning domain: what a photo, an object detected on a photo, a barcode and a camera
# analysis report ARE. These mirror the dict shapes the camera:// connector emits (capture /
# analyze / receipt parse), registered so the scan pipeline's output is validatable over
# artifact:// and so a chat request about "the object on this photo" has a schema to check.

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import Artifact, Party
from .enums import Currency, DocumentType
from ..registry import artifact


@artifact("photo", domain="scanning", title="Photo",
          keywords=("photo", "image", "camera", "capture"))
class Photo(Artifact):
    """A captured photo and its metadata (mirrors camera capture output)."""

    path: str = Field(description="File path of the captured image")
    device: str | None = Field(default=None, description="Capture device id")
    backend: str | None = Field(default=None, description="Capture backend")
    width: int | None = Field(default=None, description="Pixel width")
    height: int | None = Field(default=None, description="Pixel height")
    bytes: int | None = Field(default=None, description="File size in bytes")
    beep: bool | None = Field(default=None, description="Whether a capture beep fired")


@artifact("detected-object", domain="scanning", title="Detected object on a photo",
          keywords=("object", "detection", "bbox", "crop", "photo"))
class DetectedObject(Artifact):
    """An object located within a photo — the thing a human may ask about ('what is the object
    in this picture?'). Mirrors the camera analyze `object` block."""

    found: bool = Field(default=False, description="Whether an object was located")
    label: str | None = Field(default=None, description="Detected/target label")
    bbox: list[float] = Field(default_factory=list, description="[x, y, w, h] bounding box")
    coverage: float | None = Field(default=None, description="Fraction of frame covered (0..1)")
    detector: str | None = Field(default=None, description="edges | document | document-cv2 | img2nl | none")
    target: str | None = Field(default=None, description="The label that was searched for")
    cropPath: str | None = Field(default=None, description="Path to the cropped object image")


@artifact("barcode", domain="scanning", title="Barcode / QR code",
          keywords=("barcode", "qr", "code", "scan"))
class Barcode(Artifact):
    """A decoded barcode/QR found on a photo."""

    data: str = Field(description="Decoded payload")
    type: str | None = Field(default=None, description="Symbology, e.g. QRCODE, EAN13")
    isQr: bool = Field(default=False, description="True for a QR code")


@artifact("detected-document", domain="scanning", title="Detected document",
          keywords=("document", "scan", "classification", "detected"))
class DetectedDocument(Artifact):
    """A document the scanner detected and roughly classified — the candidate label shown in the
    scanner-stream widget (type/date/contractor/amount). Bridges a scan to an accounting artifact."""

    type: DocumentType = Field(default=DocumentType.UNKNOWN, description="Detected document type")
    date: str | None = Field(default=None, description="Detected date YYYY-MM-DD")
    contractor: str | None = Field(default=None, description="Detected contractor/supplier")
    category: str | None = Field(default=None, description="Detected category")
    amount: float | None = Field(default=None, description="Detected total amount")


@artifact("receipt-parse-result", domain="scanning", title="Receipt parse result",
          keywords=("receipt", "paragon", "ocr", "parse"))
class ReceiptParseResult(Artifact):
    """The raw output of parsing a receipt scan (mirrors camera receipt parse) — the unvalidated
    precursor that invoice:// turns into a Paragon/InvoiceDraft."""

    items: list[dict[str, Any]] = Field(default_factory=list, description="[{name, price}] line items")
    itemCount: int | None = Field(default=None, description="Number of items")
    total: float | None = Field(default=None, description="Detected total")
    totalSource: str | None = Field(default=None, description="How total was derived (label|sum)")
    itemsSum: float | None = Field(default=None, description="Sum of item prices")
    currency: Currency | None = Field(default=None, description="Detected currency")
    date: str | None = Field(default=None, description="Detected date")
    nip: str | None = Field(default=None, description="Detected seller NIP")
    lines: list[str] = Field(default_factory=list, description="Raw OCR lines")


@artifact("camera-analysis", domain="scanning", title="Camera analysis report",
          keywords=("camera", "analyze", "ocr", "pipeline", "report"))
class CameraAnalysisReport(Artifact):
    """The full camera analyze pipeline output: photo + detected object + OCR contents
    (mirrors camera analyze)."""

    device: str | None = Field(default=None, description="Capture device")
    photo: Photo | None = Field(default=None, description="The captured photo")
    description: str | None = Field(default=None, description="Natural-language scene description")
    object: DetectedObject | None = Field(default=None, description="Primary detected object")
    contents: dict[str, Any] = Field(default_factory=dict, description="{hasText, textPreview, objectFound, summary}")
    ocr: dict[str, Any] = Field(default_factory=dict, description="OCR result {ok, backend, text}")
    outputDir: str | None = Field(default=None, description="Directory artifacts were written to")


__all__ = ["Photo", "DetectedObject", "Barcode", "DetectedDocument",
           "ReceiptParseResult", "CameraAnalysisReport"]
