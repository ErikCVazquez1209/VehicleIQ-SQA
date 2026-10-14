"""Create a harmless local report to illustrate HTML escaping before/after.

Run: python demo_def11.py
It writes reporte_def11.html next to this script, using only fictional data.
The sample contains bold tags, no JavaScript, and never accesses the database.
"""

from pathlib import Path

from backend.app.pdf_generator import generate_mechanic_report_html


def main():
    report = generate_mechanic_report_html(
        vehicle_id="<b>VEHICLE_DEMO</b>",
        overall_health=90.0,
        driving_style="Demo",
        driving_score=90.0,
        component_scores={"brake_health": 95.0, "engine_health": 90.0, "battery_health": 85.0},
        alerts=[{
            "title": "<b>ALERTA DE PRUEBA</b>",
            "severity": "INFO",
            "explanation": "Datos ficticios para demostrar cómo se muestran las etiquetas HTML.",
            "recommendation": "Comparar el texto antes y después de la corrección DEF-11.",
        }],
    )
    output_file = Path(__file__).resolve().parent / "reporte_def11.html"
    output_file.write_text(report, encoding="utf-8")
    print(f"Reporte de demostración creado: {output_file}")
    print("Abre el archivo HTML en el navegador para tomar la captura.")


if __name__ == "__main__":
    main()
