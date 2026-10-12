"""DEF-01: telemetry queries must isolate the selected vehicle.

Run from the repository root: python -m unittest test_def01 -v
All records live in a separate, temporary in-memory SQLite database.
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
from backend.app.main import app


class TestDef01(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(self.engine.dispose)
        factory = sessionmaker(bind=self.engine)
        database.Base.metadata.create_all(self.engine)
        with factory() as session:
            start = datetime(2026, 1, 1, 10, 0, 0)
            for index in range(13):
                session.add(database.OBDTelemetry(
                    vehicle_id="VEHICLE_001" if index < 7 else "VEHICLE_002",
                    timestamp=start + timedelta(seconds=index),
                    rpm=1000.0 + index if index < 7 else 5000.0 + index,
                ))
            session.commit()

        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(database, "engine", self.engine))
        stack.enter_context(patch.object(database, "SessionLocal", factory))
        self.client = stack.enter_context(TestClient(app))

    def request_data(self, vehicle_id=None):
        params = {"limit": 5}
        if vehicle_id is not None:
            params["vehicle_id"] = vehicle_id
        response = self.client.get("/api/v1/telemetry/recent", params=params)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_returns_only_the_selected_vehicle(self):
        # Request more than the five most recent global rows to expose mixing.
        response = self.client.get(
            "/api/v1/telemetry/recent",
            params={"vehicle_id": "VEHICLE_002", "limit": 10},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 6)
        self.assertEqual({row["vehicle_id"] for row in body["data"]}, {"VEHICLE_002"})

    def test_filters_before_applying_the_limit(self):
        body = self.request_data("VEHICLE_001")
        self.assertEqual(body["count"], 5)
        self.assertEqual([row["rpm"] for row in body["data"]],
                         [1002.0, 1003.0, 1004.0, 1005.0, 1006.0])

    def test_returns_empty_data_for_vehicle_without_readings(self):
        body = self.request_data("VEHICLE_NO_DATA")
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["data"], [])

    def test_default_query_is_also_vehicle_specific(self):
        body = self.request_data()
        self.assertEqual({row["vehicle_id"] for row in body["data"]}, {"VEHICLE_001"})

    def test_keeps_chronological_response_order(self):
        body = self.request_data("VEHICLE_002")
        timestamps = [row["timestamp"] for row in body["data"]]
        self.assertEqual(len(timestamps), 5)
        self.assertEqual(timestamps, sorted(timestamps))


if __name__ == "__main__":
    unittest.main()
