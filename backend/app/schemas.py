"""
VehicleIQ Pydantic Schemas
Data contracts for Auth, Ingestion, Component Health Scores, Solutions, and Mechanic Reports.
"""

from typing import List, Dict, Any, Optional, Literal, Annotated
from pydantic import BaseModel, Field, EmailStr, StringConstraints, field_validator
from datetime import datetime

# --- Auth Schemas ---
Username = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50),
]
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

class UserRegister(BaseModel):
    username: Username
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must contain at least one non-whitespace character")
        # Preserve the exact password, including intentional spaces.
        return value

class UserLogin(BaseModel):
    username: Username
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

# --- Telemetry Ingestion Schemas ---
class TelemetrySampleSchema(BaseModel):
    timestamp: Optional[str] = None
    vehicle_id: str = "VEHICLE_001"
    rpm: Optional[float] = Field(None, ge=0, le=9000)
    speed_kph: Optional[float] = Field(None, ge=0, le=300)
    coolant_temp_c: Optional[float] = Field(None, ge=-40, le=150)
    throttle_pos_pct: Optional[float] = Field(None, ge=0, le=100)
    short_fuel_trim_pct: Optional[float] = Field(None, ge=-100, le=100)
    long_fuel_trim_pct: Optional[float] = Field(None, ge=-100, le=100)
    battery_voltage: Optional[float] = Field(None, ge=5, le=20)
    maf_g_s: Optional[float] = Field(None, ge=0, le=650)
    scenario: Optional[str] = "live"

class IngestBatchRequest(BaseModel):
    samples: List[TelemetrySampleSchema]

class IngestResponse(BaseModel):
    status: str = "success"
    received_count: int
    saved_count: int
    message: str

# --- Diagnostic Solution Schema ---
class ProblemSolutionSchema(BaseModel):
    component: str
    severity: str
    title: str
    explanation: str
    solution_title: str
    diy_fix_steps: List[str]
    estimated_cost: str
    urgency: str
    difficulty: str
    parts_needed: List[str]

class HealthScoreResponse(BaseModel):
    vehicle_id: str
    overall_health_score: float
    driving_style: str
    driving_behavior_score: float
    component_scores: Dict[str, float]
    plain_language_alerts: List[ProblemSolutionSchema]
    timestamp: str
    data_source: Literal["stored_telemetry"]
    telemetry_origin: Literal["simulated", "live", "mixed", "unknown"]
    origin_basis: Literal["scenario_metadata"]
    sample_count: int
    last_sample_timestamp: str
    model_used: str

# --- Mechanic Report Schema ---
class MechanicReportResponse(BaseModel):
    vehicle_id: str
    report_date: str
    overall_health_score: float
    driving_style: str
    component_scores: Dict[str, float]
    summary: str
    alerts: List[ProblemSolutionSchema]
    html_report: str
