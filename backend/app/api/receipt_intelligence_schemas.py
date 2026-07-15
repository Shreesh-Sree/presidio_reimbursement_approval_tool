"""HTTP contracts for manual, advisory receipt-intelligence checks."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReceiptAnalysisInput(BaseModel):
    """Select an existing receipt only; no file bytes or text may be supplied."""

    model_config = ConfigDict(extra="forbid")

    attachment_id: UUID | None = None


class ReceiptAnalysisContextResponse(BaseModel):
    """Opaque identifiers that allow an authorized caller to correlate advice."""

    organization_ref: str
    report_ref: str
    item_ref: str
    attachment_ref: str | None
    event_id: str


class ReceiptAnalysisResponse(BaseModel):
    """Ephemeral advisory result returned from the isolated service."""

    model_config = ConfigDict(extra="forbid")

    advisory: Literal[True] = True
    context: ReceiptAnalysisContextResponse
    analysis: dict[str, Any]
