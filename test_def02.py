"""DEF-02: health scores must use stored vehicle telemetry.

Run: python -m unittest test_def02 -v
The test database is in memory and never changes the development database.
"""

import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import backend.app.main as api
from obd_simulator import OBDSimulator


class TestDef02(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.addCleanup(self.engine.dispose)
        self.factory = sessionmaker(bind=self.engine)
        database.Base.metadata.create_all(self.engine)
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(database, "engine", self.engine))
        stack.enter_context(patch.object(database, "SessionLocal", self.factory))
        # Keep assertions independent of an optional trained TensorFlow model.
        stack.enter_context(patch.object(api.health_predictor, "model", None))
        stack.enter_context(patch.object(api.health_predictor, "is_trained", False))
        self.client = stack.enter_context(TestClient(api.app))

    def seed(self, count=75, vehicle_id="VEHICLE_001", scenario="city_driving"):
        with self.factory() as session:
            for index in range(count):
                session.add(database.OBDTelemetry(
                    vehicle_id=vehicle_id,
                    timestamp=datetime(2026, 1, 1, 10, 0, 0) + timedelta(seconds=index),
                    rpm=1500.0, speed_kph=30.0, coolant_temp_c=90.0,
                    battery_voltage=14.0, throttle_pos_pct=20.0,
                    short_fuel_trim_pct=0.0, long_fuel_trim_pct=0.0,
                    maf_g_s=8.0, scenario=scenario,
                ))
            session.commit()

    def request(self, vehicle_id="VEHICLE_001"):
        return self.client.get("/api/v1/health-score", params={"vehicle_id": vehicle_id})

    def test_no_history_returns_a_controlled_error(self):
        response = self.request()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "NO_TELEMETRY")

    def test_insufficient_history_returns_a_controlled_error(self):
        self.seed(count=29)
        response = self.request()
        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "INSUFFICIENT_TELEMETRY")
        self.assertEqual(detail["sample_count"], 29)
        self.assertEqual(detail["required_samples"], 30)

    def test_does_not_use_another_vehicles_history(self):
        self.seed(vehicle_id="VEHICLE_002")
        self.assertEqual(self.request().status_code, 404)

    def test_does_not_create_a_simulator_during_diagnosis(self):
        self.seed()
        with patch("obd_simulator.OBDSimulator", wraps=OBDSimulator) as simulator:
            self.assertEqual(self.request().status_code, 200)
            simulator.assert_not_called()

    def test_passes_stored_ordered_readings_to_the_extractor(self):
        self.seed()
        with patch.object(api.feature_extractor, "transform_dataframe",
                          wraps=api.feature_extractor.transform_dataframe) as extractor:
            self.assertEqual(self.request().status_code, 200)
        readings = extractor.call_args.args[0]
        self.assertEqual(len(readings), 75)
        self.assertEqual(set(readings["vehicle_id"]), {"VEHICLE_001"})
        self.assertTrue((readings["rpm"] == 1500.0).all())
        self.assertTrue(readings["timestamp"].is_monotonic_increasing)

    def test_changing_stored_temperature_changes_the_diagnosis(self):
        self.seed()
        # The old implementation will see identical simulated data twice,
        # so this test cannot pass just because its random values changed.
        fixed_sample = {
            "vehicle_id": "VEHICLE_001", "timestamp": "2026-01-01T10:00:00",
            "rpm": 1500.0, "speed_kph": 30.0, "coolant_temp_c": 90.0,
            "battery_voltage": 14.0, "throttle_pos_pct": 20.0,
            "short_fuel_trim_pct": 0.0, "long_fuel_trim_pct": 0.0,
            "maf_g_s": 8.0, "scenario": "city_driving",
        }
        with patch.object(OBDSimulator, "generate_sample", return_value=fixed_sample):
            before = self.request().json()
            with self.factory() as session:
                session.query(database.OBDTelemetry).filter_by(
                    vehicle_id="VEHICLE_001",
                ).update({"coolant_temp_c": 125.0})
                session.commit()
            after = self.request().json()
        self.assertLess(after["component_scores"]["engine_health"],
                        before["component_scores"]["engine_health"])

    def test_identifies_stored_simulated_data_and_the_model(self):
        self.seed()
        body = self.request().json()
        self.assertEqual(body.get("data_source"), "stored_telemetry")
        self.assertEqual(body.get("telemetry_origin"), "simulated")
        self.assertEqual(body.get("sample_count"), 75)
        self.assertEqual(body.get("last_sample_timestamp"), "2026-01-01T10:01:14")
        self.assertEqual(body.get("model_used"), "Physics_Degradation_Estimator")

    def test_does_not_assume_unknown_origin_is_live(self):
        self.seed(scenario="normal")
        self.assertEqual(self.request().json().get("telemetry_origin"), "unknown")

    def test_marks_live_origin_only_as_declared_metadata(self):
        self.seed(scenario="live_driving")
        body = self.request().json()
        self.assertEqual(body.get("telemetry_origin"), "live")
        self.assertEqual(body.get("origin_basis"), "scenario_metadata")

    def test_minimum_window_uses_heuristics_without_sequence_padding(self):
        self.seed(count=30)
        with patch.object(api.health_predictor, "predict_sequence",
                          wraps=api.health_predictor.predict_sequence) as predictor:
            response = self.request()
        self.assertEqual(response.status_code, 200)
        predictor.assert_not_called()
        self.assertEqual(response.json().get("sample_count"), 30)


if __name__ == "__main__":
    unittest.main()
