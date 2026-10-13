"""
VehicleIQ Pydantic Schemas
Data contracts for Auth, Ingestion, Component Health Scores, Solutions, and Mechanic Reports.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# --- Auth Schemas ---
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
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
