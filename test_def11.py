"""DEF-11: report variables must remain text rather than injected HTML.

Run: python -m unittest test_def11 -v
HTML is inspected as text; no script is executed and no real database is used.
"""

import unittest
from contextlib import ExitStack
from html.parser import HTMLParser
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.app.main as api
from backend.app.pdf_generator import generate_mechanic_report_html
from backend.app.schemas import HealthScoreResponse


class ParsedReport(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.attributes = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)

    def handle_data(self, data):
        self.text.append(data)


class TestDef11(unittest.TestCase):
    def render(self, vehicle_id="VEHICLE_001", alert_changes=None, component_scores=None):
        alert = {
            "title": "Battery inspection", "severity": "WARNING",
            "explanation": "Inspect battery terminals.",
            "recommendation": "Schedule inspection.",
        }
        alert.update(alert_changes or {})
        return generate_mechanic_report_html(
            vehicle_id=vehicle_id, overall_health=90.0,
            driving_style="Gentle", driving_score=90.0,
            component_scores=component_scores or {
                "brake_health": 95.0, "engine_health": 90.0, "battery_health": 85.0,
            },
            alerts=[alert],
        )

    def assert_literal_text(self, html, value):
        parsed = ParsedReport(html)
        self.assertIn(value, "".join(parsed.text))
        self.assertNotIn("script", parsed.tags)
        self.assertNotIn("img", parsed.tags)
        self.assertNotIn("svg", parsed.tags)
        self.assertNotIn("b", parsed.tags)
        self.assertFalse(any(name.lower().startswith("on") for name, _ in parsed.attributes))

    def test_vehicle_id_is_literal_text(self):
        value = '<b id="def11">demo</b>'
        self.assert_literal_text(self.render(vehicle_id=value), value)

    def test_vehicle_id_cannot_close_the_title_and_add_a_script(self):
        value = '</title><script>window.__def11 = 1</script>'
        self.assert_literal_text(self.render(vehicle_id=value), value)

    def test_alert_title_cannot_add_an_image_or_event_handler(self):
        value = '<img src="x" onerror="window.__def11 = 1">'
        self.assert_literal_text(self.render(alert_changes={"title": value}), value)

    def test_alert_severity_is_literal_text(self):
        value = 'WARNING<script>window.__def11 = 1</script>'
        self.assert_literal_text(self.render(alert_changes={"severity": value}), value)

    def test_alert_explanation_cannot_add_svg_markup(self):
        value = '<svg onload="window.__def11 = 1"></svg>'
        self.assert_literal_text(self.render(alert_changes={"explanation": value}), value)

    def test_alert_recommendation_is_literal_text(self):
        value = '<a href="javascript:void(0)">test recommendation</a>'
        self.assert_literal_text(self.render(alert_changes={"recommendation": value}), value)

    def test_quotes_ampersands_and_angle_brackets_are_encoded(self):
        value = '"single\' & <test>'
        html = self.render(vehicle_id=value)
        self.assertIn('&quot;single&#x27; &amp; &lt;test&gt;', html)
        self.assert_literal_text(html, value)

    def test_component_values_cannot_insert_html(self):
        value = '<img src="x" onerror="window.__def11 = 1">'
        html = self.render(component_scores={
            "brake_health": value, "engine_health": 90.0, "battery_health": 85.0,
        })
        self.assert_literal_text(html, value)

    def test_ordinary_unicode_text_is_preserved(self):
        value = "Revisión de batería: próxima inspección"
        self.assert_literal_text(self.render(alert_changes={"title": value}), value)

    def test_report_template_and_percentages_are_preserved(self):
        html = self.render()
        parsed = ParsedReport(html)
        for tag in ["html", "head", "body", "style", "h4"]:
            self.assertIn(tag, parsed.tags)
        text = "".join(parsed.text)
        for value in ["VEHICLE_001", "90.0%", "95.0%", "85.0%", "Schedule inspection."]:
            self.assertIn(value, text)

    def request_report(self, path):
        value = '<b id="def11">demo</b>'
        health = HealthScoreResponse(
            vehicle_id=value, overall_health_score=90.0,
            driving_style="Gentle", driving_behavior_score=90.0,
            component_scores={"brake_health": 95.0, "engine_health": 90.0, "battery_health": 85.0},
            plain_language_alerts=[], timestamp="2026-01-01T10:00:00",
            data_source="stored_telemetry", telemetry_origin="simulated",
            origin_basis="scenario_metadata", sample_count=75,
            last_sample_timestamp="2026-01-01T10:00:00",
            model_used="Physics_Degradation_Estimator",
        )
        with ExitStack() as stack:
            stack.enter_context(patch.object(api, "init_db"))
            stack.enter_context(patch.object(api, "get_health_score", return_value=health))
            client = stack.enter_context(TestClient(api.app))
            response = client.get(path, params={"vehicle_id": value})
        self.assertEqual(response.status_code, 200)
        return response, value

    def test_json_report_contains_safe_html(self):
        response, value = self.request_report("/api/v1/report")
        self.assert_literal_text(response.json()["html_report"], value)

    def test_html_endpoint_contains_safe_html(self):
        response, value = self.request_report("/api/v1/report/html")
        self.assertIn("text/html", response.headers["content-type"])
        self.assert_literal_text(response.text, value)


if __name__ == "__main__":
    unittest.main()
