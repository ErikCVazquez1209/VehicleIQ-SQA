/** Display rules aligned with explainability.py; these are project thresholds. */
const THRESHOLDS = {
  brake: { warning: 75, critical: 55 },
  engine: { warning: 80, critical: 50 },
  battery: { warning: 80, critical: 50 },
};

const STATUS = {
  normal: { level: 'normal', label: 'Normal', color: '#43e97b' },
  warning: { level: 'warning', label: 'Atención', color: '#ffb454' },
  critical: { level: 'critical', label: 'Crítico', color: '#ff0844' },
  unavailable: { level: 'unavailable', label: 'Sin evaluación', color: '#a1a1aa' },
};

/**
 * Derive one component's visible label and color from its score and API alerts.
 * A warning/critical alert can raise severity; it cannot lower score severity.
 * @param {'brake' | 'engine' | 'battery'} component
 * @param {number | null | undefined} score
 * @param {Array<{component?: string, severity?: string}>} [alerts]
 */
export function getComponentStatus(component, score, alerts = []) {
  const thresholds = THRESHOLDS[component];
  if (!thresholds || typeof score !== 'number' || !Number.isFinite(score) || score < 0 || score > 100) {
    return STATUS.unavailable;
  }

  let level = score < thresholds.critical ? 'critical'
    : score < thresholds.warning ? 'warning' : 'normal';

  for (const alert of Array.isArray(alerts) ? alerts : []) {
    const matches = String(alert?.component ?? '').toLowerCase().includes(component);
    if (!matches) continue;
    const severity = String(alert?.severity ?? '').toUpperCase();
    if (severity === 'CRITICAL') return STATUS.critical;
    if (severity === 'WARNING' && level === 'normal') level = 'warning';
  }

  return STATUS[level];
}
