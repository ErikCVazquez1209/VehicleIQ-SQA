import unittest

from data_pipeline import DEFAULT_IMPUTE_VALUES, OBDDataPipeline


class TestDef15(unittest.TestCase):
    def setUp(self):
        self.pipeline = OBDDataPipeline()

    def test_does_not_copy_readings_between_vehicles(self):
        samples = [
            {"timestamp": "2026-01-01T10:00:00", "vehicle_id": "A",
             "rpm": 5000.0, "battery_voltage": 10.0},
            {"timestamp": "2026-01-01T10:00:01", "vehicle_id": "B",
             "rpm": None, "battery_voltage": None},
        ]
        result = self.pipeline.clean_batch(samples)
        vehicle_b = result.loc[result["vehicle_id"] == "B"].iloc[0]
        self.assertEqual(vehicle_b["rpm"], DEFAULT_IMPUTE_VALUES["rpm"])
        self.assertEqual(vehicle_b["battery_voltage"],
                         DEFAULT_IMPUTE_VALUES["battery_voltage"])

    def test_uses_previous_reading_when_input_is_out_of_order(self):
        samples = [
            {"timestamp": "2026-01-01T10:00:02", "vehicle_id": "A", "rpm": None},
            {"timestamp": "2026-01-01T10:00:01", "vehicle_id": "A", "rpm": 2000.0},
        ]
        result = self.pipeline.clean_batch(samples)
        self.assertTrue(result["timestamp"].is_monotonic_increasing)
        self.assertEqual(result.iloc[-1]["rpm"], 2000.0)

    def test_does_not_use_a_future_reading(self):
        samples = [
            {"timestamp": "2026-01-01T10:00:02", "vehicle_id": "A", "rpm": 5000.0},
            {"timestamp": "2026-01-01T10:00:01", "vehicle_id": "A", "rpm": None},
        ]
        result = self.pipeline.clean_batch(samples)
        self.assertEqual(result.iloc[0]["rpm"], DEFAULT_IMPUTE_VALUES["rpm"])
        self.assertEqual(result.iloc[-1]["rpm"], 5000.0)

    def test_keeps_defaults_and_physical_limits(self):
        result = self.pipeline.clean_batch([
            {"timestamp": "2026-01-01T10:00:00", "rpm": 12000.0,
             "speed_kph": -50.0},
        ])
        self.assertEqual(result.iloc[0]["rpm"], 9000.0)
        self.assertEqual(result.iloc[0]["speed_kph"], 0.0)
        self.assertEqual(result.iloc[0]["coolant_temp_c"], 90.0)
        self.assertEqual(result.iloc[0]["vehicle_id"], "VEHICLE_001")

    def test_empty_batch_is_supported(self):
        self.assertTrue(self.pipeline.clean_batch([]).empty)


if __name__ == "__main__":
    unittest.main()
