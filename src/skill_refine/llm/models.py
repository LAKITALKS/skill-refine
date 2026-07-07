"""Models specific to the optional LLM/refinement layer."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from skill_refine.lint.models import Severity


class RewriteMode(str, Enum):
    CLARITY = "clarity"
    COMPACT = "compact"
    ROBUSTNESS = "robustness"
    STRUCTURE = "structure"
    SAFETY = "safety"
    ALL = "all"


class BoundaryConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GuardWarning(BaseModel):
    code: str
    message: str
    severity: Severity = Severity.WARNING


class GuardResult(BaseModel):
    passed: bool
    warnings: list[GuardWarning] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""


class PatchProposal(BaseModel):
    section_name: str
    original: str
    proposed: str
    confidence: BoundaryConfidence
    reason: str = ""
