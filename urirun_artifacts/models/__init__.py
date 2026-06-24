"""Artifact models. Importing this package registers every @artifact-decorated model with the
registry (side effect of importing each domain module). Add a new domain module here to make
its artifacts discoverable over artifact://."""
from . import accounting, documents, infra, request, scanning, workflow  # noqa: F401  (registration side effects)
from .base import Address, Artifact, LineItem, Money, Party

__all__ = ["Artifact", "Money", "Address", "Party", "LineItem",
           "accounting", "documents", "scanning", "workflow", "infra", "request"]
