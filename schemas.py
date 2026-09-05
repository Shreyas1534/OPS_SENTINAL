from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Any

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"

class EvidenceQuality(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"

class EvidenceItem(BaseModel):
    source: str = Field(..., description="e.g., telemetry, maintenance_db")
    field: str = Field(..., description="e.g., engine_temperature")
    value: Any = Field(..., description="The exact value observed")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the data")

class AgentAssessment(BaseModel):
    finding: RiskLevel = Field(..., description="The risk level finding from this specific agent's domain.")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0.")
    evidence: Any = Field(..., description="Simply copy and paste the raw JSON data you were provided into this field.")
    evidence_quality: EvidenceQuality = Field(..., description="The overall quality/freshness of the evidence used.")
    missing_evidence: List[str] = Field(..., description="Just output an empty list [].")

class CriticAssessment(BaseModel):
    has_conflict: bool = Field(..., description="True if domain findings contradict each other or violate scopes.")
    requires_more_evidence: bool = Field(..., description="True if evidence is STALE, MISSING, or insufficient.")
    scope_violation_detected: bool = Field(..., description="True if an agent made conclusions outside its allowed domain.")
    reasoning: str = Field(..., description="Detailed explanation of conflicts, freshness issues, or scope violations.")

class AdversarialChallenge(BaseModel):
    challenge_successful: bool = Field(..., description="True if you found a flaw in the current assessments.")
    flaw_description: str = Field(..., description="Explanation of the contradiction, stale data, or assumption found.")

class FinalDecision(BaseModel):
    recommendation: str = Field(..., description="The final operational recommendation.")
