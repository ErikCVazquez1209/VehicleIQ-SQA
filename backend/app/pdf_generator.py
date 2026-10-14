"""
VehicleIQ Mechanic Diagnostic Report Generator
Renders a clean, professional, print-ready HTML/PDF diagnostic report for sharing with mechanics.
"""

from datetime import datetime
from html import escape
from typing import Dict, Any, List

def _escape_text(value: Any) -> str:
    """Encode a variable for a text position in our fixed HTML template."""
    return escape(str(value), quote=True)

def generate_mechanic_report_html(
    vehicle_id: str,
    overall_health: float,
    driving_style: str,
    driving_score: float,
    component_scores: Dict[str, float],
    alerts: List[Dict[str, Any]]
) -> str:
    """Renders HTML template for downloadable & printable mechanic summary."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    safe_vehicle_id = _escape_text(vehicle_id)

    alerts_html = ""
    for alert in alerts:
        badge_color = "#ef4444" if alert.get("severity") == "CRITICAL" else "#f59e0b" if alert.get("severity") == "WARNING" else "#3b82f6"
        alerts_html += f"""
        <div style="border-left: 4px solid {badge_color}; background-color: #1e293b; padding: 12px 16px; margin-bottom: 12px; border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0; color: #f8fafc; font-size: 16px;">{_escape_text(alert.get('title'))}</h4>
                <span style="background-color: {badge_color}; color: #ffffff; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">
                    {_escape_text(alert.get('severity'))}
                </span>
            </div>
            <p style="margin: 6px 0 4px 0; color: #cbd5e1; font-size: 13px; line-height: 1.4;">
                <strong>Diagnostic Finding:</strong> {_escape_text(alert.get('explanation'))}
            </p>
            <p style="margin: 4px 0 0 0; color: #38bdf8; font-size: 13px;">
                <strong>Mechanic Recommendation:</strong> {_escape_text(alert.get('recommendation'))}
            </p>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>VehicleIQ Diagnostic Mechanic Report - {safe_vehicle_id}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 24px;
        }}
        .report-card {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 24px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #334155;
            padding-bottom: 16px;
            margin-bottom: 20px;
        }}
        .brand {{
            font-size: 24px;
            font-weight: bold;
            color: #38bdf8;
        }}
        .subbrand {{
            font-size: 12px;
            color: #94a3b8;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }}
        .metric-box {{
            background-color: #1e293b;
            padding: 12px;
            border-radius: 6px;
            text-align: center;
        }}
        .metric-title {{
            font-size: 11px;
            color: #94a3b8;
            text-transform: uppercase;
        }}
        .metric-val {{
            font-size: 22px;
            font-weight: bold;
            color: #38bdf8;
            margin-top: 4px;
        }}
    </style>
</head>
<body>
    <div class="report-card">
        <div class="header">
            <div>
                <div class="brand">âš¡ VehicleIQ</div>
                <div class="subbrand">Real-Time Vehicle Health & Failure Prediction Summary</div>
            </div>
            <div style="text-align: right; color: #94a3b8; font-size: 12px;">
                <div>Vehicle ID: <strong>{safe_vehicle_id}</strong></div>
                <div>Generated: {_escape_text(now_str)}</div>
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-title">Overall Health</div>
                <div class="metric-val" style="color: {'#22c55e' if overall_health >= 80 else '#f59e0b' if overall_health >= 60 else '#ef4444'};">{_escape_text(overall_health)}%</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Brake Health</div>
                <div class="metric-val">{_escape_text(component_scores.get('brake_health', 100))}%</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Engine Health</div>
                <div class="metric-val">{_escape_text(component_scores.get('engine_health', 100))}%</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Battery Health</div>
                <div class="metric-val">{_escape_text(component_scores.get('battery_health', 100))}%</div>
            </div>
        </div>

        <h3 style="color: #cbd5e1; border-bottom: 1px solid #334155; padding-bottom: 8px;">Plain-Language Diagnostic Findings</h3>
        {alerts_html}

        <div style="margin-top: 30px; text-align: center; border-top: 1px solid #334155; padding-top: 12px; font-size: 11px; color: #64748b;">
            VehicleIQ Autonomous AI Diagnostic System â€¢ Printable Mechanic Summary
        </div>
    </div>
</body>
</html>
"""
    return html_content
