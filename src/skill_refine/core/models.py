"""Data models for skill-refine."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


# --- Enums ---


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SmellType(str, Enum):
    VAGUE_TRIGGER = "VAGUE_TRIGGER"
    NO_WARNINGS = "NO_WARNINGS"
    NO_FAILURE_CASES = "NO_FAILURE_CASES"
    TOKEN_BLOAT = "TOKEN_BLOAT"
    NO_INPUTS_OUTPUTS = "NO_INPUTS_OUTPUTS"
    NO_BOUNDARIES = "NO_BOUNDARIES"
    WALL_OF_TEXT = "WALL_OF_TEXT"
    EMPTY_FRONTMATTER = "EMPTY_FRONTMATTER"


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


# --- Core Models ---


class SkillMetadata(BaseModel):
    name: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class Section(BaseModel):
    heading: str
    level: int
    content: str
    word_count: int = 0


class Skill(BaseModel):
    path: Path
    raw_content: str
    metadata: SkillMetadata
    body: str
    sections: list[Section] = Field(default_factory=list)
    word_count: int = 0
    estimated_tokens: int = 0


# --- Analysis Models ---


class Finding(BaseModel):
    rule: str
    message: str
    severity: Severity = Severity.WARNING
    section: str | None = None


class ScoreCard(BaseModel):
    completeness: float = 0.0
    structure: float = 0.0
    metadata: float = 0.0
    conciseness: float = 0.0
    total: float = 0.0
    llm_score: float | None = None


class SkillReport(BaseModel):
    skill: Skill
    findings: list[Finding] = Field(default_factory=list)
    smells: list[SmellType] = Field(default_factory=list)
    score: ScoreCard = Field(default_factory=ScoreCard)


# --- Refine Models ---


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
