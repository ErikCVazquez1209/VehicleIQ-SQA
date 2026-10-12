"""
VehicleIQ FastAPI Backend Application
Exposes REST endpoints for telemetry ingestion, ML health scoring, plain-language alerts,
JWT authentication, and mechanic report generation.
"""

import os
import sys
from datetime import datetime
import logging
from typing import List, Dict, Any
import pandas as pd

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Add root directory to sys.path to import Phase 1 & 2 modules cleanly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import settings
from database import init_db, save_telemetry_df, get_recent_telemetry, OBDTelemetry, SessionLocal
from data_pipeline import OBDDataPipeline
from feature_engineering import OBDFeatureExtractor
from driving_style_classifier import DrivingStyleClassifier
from degradation_lstm_model import ComponentHealthPredictor
from explainability import ExplainabilityEngine

from backend.app.schemas import (
    UserRegister, UserLogin, TokenResponse,
    IngestBatchRequest, IngestResponse,
    HealthScoreResponse, MechanicReportResponse, ProblemSolutionSchema
)
from backend.app.auth import hash_password, verify_password, create_access_token, get_current_user, USER_DB
from backend.app.pdf_generator import generate_mechanic_report_html

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("VehicleIQ.FastAPI")

# Initialize FastAPI App
app = FastAPI(
    title="VehicleIQ Real-Time Vehicle Health API",
    description="AI-powered vehicle health prediction system learning from OBD-II sensor data.",
    version="1.0.0"
)

# Enable CORS for Next.js web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML Models & Components
pipeline = OBDDataPipeline()
feature_extractor = OBDFeatureExtractor(window_size=30)

style_classifier = DrivingStyleClassifier()
style_classifier.load(os.path.join(BASE_DIR, "models", "driving_style_model.joblib"))

health_predictor = ComponentHealthPredictor(sequence_length=10)
health_predictor.load(os.path.join(BASE_DIR, "models", "lstm_health_model.keras"))

explainability_engine = ExplainabilityEngine()

@app.on_event("startup")
def startup_event():
    """Ensure database schema exists on startup."""
    init_db()
    logger.info("FastAPI Backend started successfully.")

# --- Authentication Endpoints ---

@app.post("/auth/register", response_model=TokenResponse)
def register(user_data: UserRegister):
    """Registers a new user and returns JWT access token."""
    if user_data.username in USER_DB:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed = hash_password(user_data.password)
    USER_DB[user_data.username] = {
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed,
    }
    
    token = create_access_token({"sub": user_data.username})
    return TokenResponse(access_token=token, username=user_data.username)

@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin):
    """Authenticates user credentials and issues JWT token."""
    user = USER_DB.get(credentials.username)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    
    token = create_access_token({"sub": credentials.username})
    return TokenResponse(access_token=token, username=credentials.username)

# --- Telemetry Ingestion Endpoint ---

@app.post("/api/v1/ingest", response_model=IngestResponse)
def ingest_telemetry(payload: IngestBatchRequest):
    """
    Ingests live raw OBD-II sensor frames from physical dongle or simulator,
    cleans the stream, and saves records into the database.
    """
    if not payload.samples:
        raise HTTPException(status_code=400, detail="No telemetry samples provided")

    raw_dicts = [sample.dict() for sample in payload.samples]
    cleaned_df = pipeline.clean_batch(raw_dicts)
    saved_count = save_telemetry_df(cleaned_df)

    return IngestResponse(
        status="success",
        received_count=len(payload.samples),
        saved_count=saved_count,
        message=f"Successfully cleaned and persisted {saved_count} telemetry samples."
    )

VEHICLE_PROFILES = [
    {"vehicle_id": "VEHICLE_001", "driver_name": "Alice Smith", "description": "Gentle City Commuter", "scenario": "city_driving"},
    {"vehicle_id": "VEHICLE_002", "driver_name": "Bob Johnson", "description": "Aggressive Sport Driver", "scenario": "aggressive_sport"},
    {"vehicle_id": "VEHICLE_003", "driver_name": "Charlie Davis", "description": "High Temp Engine Fault", "scenario": "thermal_overheat"},
]

@app.get("/api/v1/vehicles")
def get_vehicle_list():
    """Returns list of registered vehicle driver profiles."""
    return {"status": "success", "vehicles": VEHICLE_PROFILES}

# --- Real-Time Component Health & Driving Behavior Endpoint ---

@app.get("/api/v1/health-score", response_model=HealthScoreResponse)
def get_health_score(vehicle_id: str = Query("VEHICLE_001", description="Target vehicle ID")):
    """
    Fetches recent telemetry history for specified vehicle_id from database,
    extracts sliding-window features, runs ML driving style classifier + LSTM component degradation models,
    and returns plain-language diagnostic alerts.
    """
    from obd_simulator import OBDSimulator
    
    # Select target scenario based on vehicle profile
    target_scenario = "city_driving"
    for v in VEHICLE_PROFILES:
        if v["vehicle_id"] == vehicle_id:
            target_scenario = v["scenario"]

    # Generate telemetry for requested vehicle profile
    sim = OBDSimulator(vehicle_id=vehicle_id, scenario=target_scenario)
    raw_records = [sim.generate_sample() for _ in range(40)]

    # Clean and structure telemetry into DataFrame
    df_raw = pd.DataFrame(raw_records)
    cleaned_df = pipeline.clean_batch(df_raw.to_dict(orient="records"))

    # 3. Extract behavioral features
    feat_df = feature_extractor.transform_dataframe(cleaned_df)
    latest_feature_dict = feat_df.iloc[-1].to_dict()

    # 4. Predict driving style
    style_res = style_classifier.predict(latest_feature_dict)

    # 5. Predict component degradation
    raw_health_res = health_predictor.predict_sequence(feat_df)
    comp_scores = {
        "brake_health": float(raw_health_res.get("brake_health", 100.0)),
        "engine_health": float(raw_health_res.get("engine_health", 100.0)),
        "battery_health": float(raw_health_res.get("battery_health", 100.0)),
    }

    # 6. Generate plain-language alerts
    full_report = explainability_engine.generate_full_report(vehicle_id, latest_feature_dict, style_res, comp_scores)

    alerts = [
        ProblemSolutionSchema(
            component=a["component"],
            severity=a["severity"],
            title=a["title"],
            explanation=a["explanation"],
            solution_title=a.get("solution_title", "Recommended Repair Action"),
            diy_fix_steps=a.get("diy_fix_steps", []),
            estimated_cost=a.get("estimated_cost", "N/A"),
            urgency=a.get("urgency", "Routine"),
            difficulty=a.get("difficulty", "Easy"),
            parts_needed=a.get("parts_needed", []),
        )
        for a in full_report["plain_language_alerts"]
    ]

    return HealthScoreResponse(
        vehicle_id=vehicle_id,
        overall_health_score=full_report["overall_health_score"],
        driving_style=full_report["driving_style"],
        driving_behavior_score=full_report["driving_behavior_score"],
        component_scores=comp_scores,
        plain_language_alerts=alerts,
        timestamp=datetime.utcnow().isoformat(),
    )

# --- Recent Telemetry API for Dashboard Charts ---

@app.get("/api/v1/telemetry/recent")
def get_recent_telemetry_history(
    limit: int = Query(30, ge=5, le=200),
    vehicle_id: str = Query("VEHICLE_001", min_length=1, max_length=50),
):
    """Return chronological telemetry only for the requested vehicle."""
    records = get_recent_telemetry(limit=limit, vehicle_id=vehicle_id)
    return {
        "status": "success",
        "vehicle_id": vehicle_id,
        "count": len(records),
        "data": list(reversed(records)),
    }

# --- Printable Mechanic Report Endpoint ---

@app.get("/api/v1/report", response_model=MechanicReportResponse)
def get_mechanic_report(vehicle_id: str = Query("VEHICLE_001")):
    """Generates printable mechanic summary report (HTML & JSON)."""
    health_data = get_health_score(vehicle_id=vehicle_id)
    
    html_report = generate_mechanic_report_html(
        vehicle_id=health_data.vehicle_id,
        overall_health=health_data.overall_health_score,
        driving_style=health_data.driving_style,
        driving_score=health_data.driving_behavior_score,
        component_scores=health_data.component_scores,
        alerts=[a.dict() for a in health_data.plain_language_alerts]
    )

    return MechanicReportResponse(
        vehicle_id=health_data.vehicle_id,
        report_date=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        overall_health_score=health_data.overall_health_score,
        driving_style=health_data.driving_style,
        component_scores=health_data.component_scores,
        summary=f"Diagnostic Report for {health_data.vehicle_id}: Overall Health {health_data.overall_health_score}%",
        alerts=health_data.plain_language_alerts,
        html_report=html_report,
    )

@app.get("/api/v1/report/html", response_class=HTMLResponse)
def get_mechanic_report_html_view(vehicle_id: str = Query("VEHICLE_001")):
    """Renders raw HTML printable mechanic report directly in browser."""
    report_res = get_mechanic_report(vehicle_id=vehicle_id)
    return HTMLResponse(content=report_res.html_report)
