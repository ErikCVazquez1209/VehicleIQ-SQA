'use client';
import React, { useState, useEffect, useRef } from 'react';
import { getComponentStatus } from '../lib/component-status.mjs';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
interface VehicleProfile {
  vehicle_id: string;
  driver_name: string;
  description: string;
  scenario: string;
  model_name: string;
  tagline: string;
  specs: string;
}
interface ProblemSolution {
  component: string;
  severity: string;
  title: string;
  explanation: string;
  solution_title: string;
  diy_fix_steps: string[];
  estimated_cost: string;
  urgency: string;
  difficulty: string;
  parts_needed: string[];
}
interface HealthData {
  vehicle_id: string;
  overall_health_score: number;
  driving_style: string;
  driving_behavior_score: number;
  component_scores: {
    brake_health: number;
    engine_health: number;
    battery_health: number;
  };
  plain_language_alerts: ProblemSolution[];
  timestamp: string;
  data_source: 'stored_telemetry';
  telemetry_origin: 'simulated' | 'live' | 'mixed' | 'unknown';
  origin_basis: 'scenario_metadata';
  sample_count: number;
  last_sample_timestamp: string;
  model_used: string;
}
interface TelemetryPoint {
  vehicle_id: string;
  rpm: number | null;
  speed_kph: number | null;
  coolant_temp_c: number | null;
  battery_voltage: number | null;
  throttle_pos_pct: number | null;
  maf_g_s: number | null;
}
interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
  solution?: ProblemSolution;
  timestamp: string;
}
function AccessibleModal({
  children,
  titleId,
  onClose,
  returnFocusElement,
}: {
  children: React.ReactNode;
  titleId: string;
  onClose: () => void;
  returnFocusElement?: HTMLElement | null;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const trigger =
      returnFocusElement ??
      (document.activeElement as HTMLElement | null);
    dialog.showModal();
    dialog.querySelector<HTMLElement>("[data-dialog-close]")?.focus();
    return () => {
      if (dialog.open) dialog.close();
      if (trigger?.isConnected) trigger.focus();
    };
  }, [returnFocusElement]);
  const handleTab = (
    event: React.KeyboardEvent<HTMLDialogElement>
  ) => {
    if (event.key !== "Tab") return;
    const elements = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      ) ?? []
    ).filter(
      (element) =>
        element.tabIndex >= 0 &&
        element.getClientRects().length > 0
    );
    const first = elements[0];
    const last = elements[elements.length - 1];
    if (first && event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (
      last &&
      !event.shiftKey &&
      document.activeElement === last
    ) {
      event.preventDefault();
      first.focus();
    }
  };
  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      aria-modal="true"
      onKeyDown={handleTab}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        width: "100vw",
        maxWidth: "none",
        height: "100vh",
        maxHeight: "none",
        margin: 0,
        border: "none",
        padding: "20px",
        background: "rgba(0, 0, 0, 0.92)",
        color: "#fff",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          height: "100%",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {children}
      </div>
    </dialog>
  );
}
export default function LuxuryRedDashboard() {
  const [garage] = useState<VehicleProfile[]>([
    {
      vehicle_id: 'VEHICLE_001',
      driver_name: 'Alice Smith',
      description: 'Gentle City Commuter',
      scenario: 'city_driving',
      model_name: 'Phantom GT V12',
      tagline: '6.0L Twin-Turbo Grand Tourer',
      specs: '720 HP | 0-100 in 3.1s'
    },
    {
      vehicle_id: 'VEHICLE_002',
      driver_name: 'Bob Johnson',
      description: 'Aggressive Track Driver',
      scenario: 'aggressive_sport',
      model_name: 'Apex Hyperion Track Special',
      tagline: 'Quad-Motor Carbon Hypercar',
      specs: '1450 HP | 0-100 in 1.9s'
    },
    {
      vehicle_id: 'VEHICLE_003',
      driver_name: 'Charlie Davis',
      description: 'Thermal Overheat Test',
      scenario: 'thermal_overheat',
      model_name: 'Monaco RS V10',
      tagline: 'Naturally Aspirated Track Weapon',
      specs: '640 HP | Redline 8900 RPM'
    }
  ]);
  const [selectedVehicle, setSelectedVehicle] = useState<string>('VEHICLE_001');
  // Red Racing Concept Showcase Tab State (Option 1, Option 2, Option 3)
  const [activeConceptTab, setActiveConceptTab] = useState<'hud' | 'concierge' | 'mobile'>('hud');
  const [health, setHealth] = useState<HealthData | null>(null);
  const [healthIssue, setHealthIssue] = useState<string | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryPoint | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'online' | 'error'>('checking');
  const [lastSuccessfulCheck, setLastSuccessfulCheck] = useState<string | null>(null);
  const [hasTelemetryData, setHasTelemetryData] = useState(false);
  const [healthFromApi, setHealthFromApi] = useState(false);
  const [telemetryFromApi, setTelemetryFromApi] = useState(false);
  const [activeSolution, setActiveSolution] = useState<ProblemSolution | null>(null);
  const [showReportModal, setShowReportModal] = useState<boolean>(false);
  const [reportHtml, setReportHtml] = useState<string>('');
  const [isAudioPlaying, setIsAudioPlaying] = useState<boolean>(false);
  // --- Interactive AI Repair Chatbot State ---
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false);
  const [chatInput, setChatInput] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: 'ai',
      text: 'Greetings! I am your VehicleIQ Red Racing AI Repair Concierge. Describe any symptom or issue (e.g. "brakes squeal", "coolant temp high", "battery voltage drop"), and I will diagnose it instantly with step-by-step DIY fix guides!',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatTriggerRef = useRef<HTMLButtonElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const reportTriggerRef = useRef<HTMLButtonElement>(null);
  const handleCarSelect = (carId: string) => {
    if (carId === selectedVehicle) return;
    setConnectionStatus('checking');
    setLastSuccessfulCheck(null);
    setHasTelemetryData(false);
    setTelemetry(null);
    setTelemetryFromApi(false);
    setHealthFromApi(false);
    setSelectedVehicle(carId);
    setHealth(null);
    setHealthIssue(null);
  };
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  useEffect(() => {
    if (!isChatOpen) return;

    const trigger = chatTriggerRef.current;
    chatInputRef.current?.focus();

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !document.querySelector('dialog[open]')) {
        event.preventDefault();
        setIsChatOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('keydown', handleEscape);
      if (trigger?.isConnected) trigger.focus();
    };
  }, [isChatOpen]);
  useEffect(() => {
    let active = true;
    let fetching = false;
    let requestController: AbortController | null = null;
    const fetchData = async () => {
      if (fetching || !active) return;
      fetching = true;
      const controller = new AbortController();
      requestController = controller;
      const timeout = setTimeout(() => controller.abort(), 8000);
      try {
        const telemRes = await fetch(
          `${API_BASE_URL}/api/v1/telemetry/recent?limit=5&vehicle_id=${encodeURIComponent(selectedVehicle)}`,
          { signal: controller.signal, cache: 'no-store' }
        );
        if (!telemRes.ok) throw new Error(`Telemetry API: ${telemRes.status}`);
        const telemJson = await telemRes.json();
        if (!Array.isArray(telemJson.data)) throw new Error('Invalid telemetry response');
        if (
          telemJson.vehicle_id !== selectedVehicle ||
          telemJson.data.some((point: TelemetryPoint) => point.vehicle_id !== selectedVehicle)
        ) throw new Error('Response does not match the selected vehicle');
        if (!active) return;
        setHasTelemetryData(telemJson.data.length > 0);
        if (telemJson.data.length > 0) {
          const currentTelem = telemJson.data[telemJson.data.length - 1];
          setTelemetry(currentTelem);
          setTelemetryFromApi(true);
        } else {
          setTelemetry(null);
          setTelemetryFromApi(false);
        }
        const healthRes = await fetch(
          `${API_BASE_URL}/api/v1/health-score?vehicle_id=${encodeURIComponent(selectedVehicle)}`,
          { signal: controller.signal, cache: 'no-store' }
        );
        const healthJson = await healthRes.json();
        if (!active) return;
        if (!healthRes.ok) {
          const detail = healthJson.detail;
          if (
            (healthRes.status === 404 || healthRes.status === 422) &&
            ['NO_TELEMETRY', 'INSUFFICIENT_TELEMETRY'].includes(detail?.code)
          ) {
            setHealth(null);
            setHealthFromApi(false);
            setHealthIssue(detail.message);
          } else {
            throw new Error(`Health API: ${healthRes.status}`);
          }
        } else {
          if (healthJson.vehicle_id !== selectedVehicle) {
            throw new Error('Health response does not match the selected vehicle');
          }
          setHealth(healthJson);
          setHealthFromApi(true);
          setHealthIssue(null);
        }
        setLastSuccessfulCheck(new Date().toLocaleTimeString());
        setConnectionStatus('online');
      } catch {
        if (active) setConnectionStatus('error');
      } finally {
        clearTimeout(timeout);
        fetching = false;
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => {
      active = false;
      clearInterval(interval);
      requestController?.abort();
    };
  }, [selectedVehicle]);
  const handleSendMessage = (textToSend?: string) => {
    const query = textToSend || chatInput;
    if (!query.trim()) return;
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg: ChatMessage = { sender: 'user', text: query, timestamp: timeStr };
    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setChatInput('');
    setTimeout(() => {
      const qLower = query.toLowerCase();
      let aiText = "I analyzed your vehicle's telemetry log. Here is the diagnostic breakdown and recommended repair action:";
      let solutionObj: ProblemSolution | undefined = undefined;
      if (qLower.includes('brake') || qLower.includes('squeal') || qLower.includes('pad') || qLower.includes('stop')) {
        solutionObj = {
          component: 'Brake System',
          severity: 'CRITICAL',
          title: 'High-Wear Ceramic Brake Pad Replacement',
          explanation: 'Friction pad thickness detected below 3mm. Hard braking telemetry indicates elevated rotor thermal wear.',
          solution_title: 'Brake Pad & Rotor Service Guide',
          diy_fix_steps: [
            'Jack up vehicle safely and remove wheel lug nuts.',
            'Unbolt caliper guide pins and replace worn ceramic friction pads.',
            'Clean rotor surface with brake cleaner spray and flush DOT-4 fluid.'
          ],
          estimated_cost: '$140 - $350 / ₹4,500 - ₹11,500',
          urgency: 'High',
          difficulty: 'Intermediate',
          parts_needed: ['Ceramic Brake Pads', 'DOT-4 Fluid', 'Brake Cleaner']
        };
        aiText = `🚨 **Diagnostic Alert**: ${solutionObj.title}\n${solutionObj.explanation}`;
      } else if (qLower.includes('heat') || qLower.includes('overheat') || qLower.includes('temp') || qLower.includes('coolant')) {
        solutionObj = {
          component: 'Engine Thermal System',
          severity: 'CRITICAL',
          title: 'Coolant System Thermal Bleed & Thermostat Service',
          explanation: 'Engine coolant temp breached 105°C threshold. Possible thermostat sticking or air pockets in cooling lines.',
          solution_title: 'Radiator Flush & Thermostat Replacement',
          diy_fix_steps: [
            'Allow engine block to cool down completely.',
            'Flush coolant reservoir with distilled water solution.',
            'Replace thermostat valve unit and bleed air pockets using funnel kit.'
          ],
          estimated_cost: '$75 - $160 / ₹2,500 - ₹5,200',
          urgency: 'Critical',
          difficulty: 'Easy',
          parts_needed: ['Thermostat Valve', 'OAT 50/50 Coolant']
        };
        aiText = `⚠️ **Diagnostic Alert**: ${solutionObj.title}\n${solutionObj.explanation}`;
      } else if (qLower.includes('battery') || qLower.includes('voltage') || qLower.includes('charge') || qLower.includes('light')) {
        solutionObj = {
          component: 'Electrical & Charging',
          severity: 'WARNING',
          title: '12V Battery Cell Degradation & Alternator Test',
          explanation: 'Voltage dropped below 12.4V at idle. Alternator output bus stability requires terminal inspection.',
          solution_title: 'Battery Terminal Cleaning & Voltage Test',
          diy_fix_steps: [
            'Disconnect negative battery terminal clamp first.',
            'Clean corrosion oxidation using wire brush and baking soda solution.',
            'Check alternator belt tension and re-tighten terminal fasteners.'
          ],
          estimated_cost: '$30 - $85 / ₹1,000 - ₹2,800',
          urgency: 'Moderate',
          difficulty: 'Easy',
          parts_needed: ['Terminal Cleaner Brush', 'Dielectric Grease']
        };
        aiText = `⚡ **Diagnostic Alert**: ${solutionObj.title}\n${solutionObj.explanation}`;
      } else {
        aiText = health && telemetry && telemetry.rpm != null && telemetry.coolant_temp_c != null && telemetry.battery_voltage != null
          ? `🔧 **AI Diagnostic Analysis**: No critical hardware fault detected for "${query}". Your overall vehicle health is ${health.overall_health_score}%. Sensor telemetry (RPM: ${Math.round(telemetry.rpm)}, Temp: ${Math.round(telemetry.coolant_temp_c)}°C, Voltage: ${telemetry.battery_voltage}V) operating normally.`
          : 'No hay una evaluación de salud y telemetría completas para el vehículo seleccionado.';
      }
      setMessages(prev => [...prev, {
        sender: 'ai',
        text: aiText,
        solution: solutionObj,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    }, 600);
  };
  const handleGenerateReport = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/report?vehicle_id=${selectedVehicle}`);
      if (res.ok) {
        const data = await res.json();
        setReportHtml(data.html_report);
        setShowReportModal(true);
      }
    } catch (e) {
      alert('Could not fetch report from backend.');
    }
  };
  const activeCar = garage.find(c => c.vehicle_id === selectedVehicle) || garage[0];
  const brakeStatus = getComponentStatus('brake', health?.component_scores?.brake_health, health?.plain_language_alerts);
  const engineStatus = getComponentStatus('engine', health?.component_scores?.engine_health, health?.plain_language_alerts);
  const batteryStatus = getComponentStatus('battery', health?.component_scores?.battery_health, health?.plain_language_alerts);
  return (
    <div style={{ minHeight: '100vh', padding: '32px 40px', maxWidth: '1440px', margin: '0 auto', background: '#000' }}>
      <style>{`
        button:focus-visible,
        input:focus-visible {
          outline: 3px solid #00f2fe !important;
          outline-offset: 4px;
        }
      `}</style>
      <div
        role={connectionStatus === 'error' ? 'alert' : 'status'}
        style={{
          padding: '14px 18px', marginBottom: '24px', borderRadius: '12px',
          border: `1px solid ${connectionStatus === 'online' ? '#43e97b' : '#ffb454'}`,
          color: connectionStatus === 'online' ? '#43e97b' : '#ffb454',
          background: '#111'
        }}
      >
        {connectionStatus === 'checking' && (
          <p>Comprobando conexión. Los valores visibles aún no están confirmados para esta selección.</p>
        )}
        {connectionStatus === 'error' && (
          <p>
            No se pudieron actualizar los datos. Los valores visibles pueden ser lecturas anteriores
            o datos de demostración. No representan una actualización confirmada.
            Reintentando automáticamente.
          </p>
        )}
        {connectionStatus === 'online' && (
          <>
            <p>API conectada. Última consulta exitosa: {lastSuccessfulCheck}.</p>
            {!hasTelemetryData && (
              <p>No hay telemetría almacenada para el vehículo seleccionado. Los instrumentos muestran —.</p>
            )}
          </>
        )}
        <p style={{ marginTop: '8px', fontSize: '13px' }}>
          Salud: {healthFromApi ? 'estimación basada en telemetría almacenada' : 'evaluación no disponible'}.
          {' '}Instrumentos: {telemetryFromApi ? 'última lectura recibida de la API para este vehículo' : 'sin lectura para el vehículo seleccionado'}.
        </p>
        {healthIssue && <p role="status">{healthIssue}</p>}
        {healthFromApi && health && (
          <p style={{ marginTop: '8px', fontSize: '13px' }}>
            Muestras utilizadas: {health.sample_count}. Origen declarado: {
              { simulated: 'simulado', live: 'sensor OBD', mixed: 'mixto', unknown: 'desconocido' }[health.telemetry_origin]
            }. Método: {health.model_used === 'LSTM_NeuralNetwork' ? 'modelo LSTM' : 'estimación heurística'}.
            {' '}El origen se basa en metadatos y no verifica una conexión física.
          </p>
        )}
      </div>
      {/* --- Top Red Racing Header --- */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px', flexWrap: 'wrap', gap: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span style={{ fontSize: '32px' }}>🏎️</span>
            <h1 className="brand-logo-font text-red-gradient" style={{ fontSize: '38px', fontWeight: 900, letterSpacing: '2px' }}>
              VEHICLE<span className="brand-iq-font" style={{ color: '#00f2fe', fontStyle: 'normal', marginLeft: '4px' }}>IQ</span>
            </h1>
            <span style={{ background: 'rgba(255, 8, 68, 0.12)', color: '#ff0844', border: '1px solid rgba(255, 8, 68, 0.4)', padding: '6px 16px', borderRadius: '30px', fontSize: '11px', fontWeight: 800, letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="red-beacon"></span> RED RACING AI TELEMETRY
            </span>
          </div>
          <p style={{ color: '#a1a1aa', fontSize: '14px', marginTop: '6px' }}>
            Predictive Telemetry Failure Engine & AI Maintenance Concierge
          </p>
        </div>
        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <button
            ref={chatTriggerRef}
            aria-expanded={isChatOpen}
            aria-controls="repair-chat"
            onClick={() => setIsChatOpen(!isChatOpen)}
            style={{ background: 'linear-gradient(135deg, #00f2fe, #4facfe)', color: '#000', border: 'none', padding: '12px 22px', borderRadius: '16px', fontWeight: 900, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', boxShadow: '0 6px 20px rgba(0, 242, 254, 0.3)', fontSize: '13.5px' }}
          >
            💬 AI Repair Assistant Chat
          </button>
          <button ref={reportTriggerRef} onClick={handleGenerateReport} className="btn-red-luxury">
            📜 Printable Report
          </button>
        </div>
      </header>
      {/* --- Executive Hypercar Showroom Selector Cards --- */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 className="font-serif-luxury" style={{ fontSize: '22px', color: '#fff' }}>
          🏎️ Select Monitored Garage Vehicle Profile
        </h2>
        <span style={{ fontSize: '12px', color: '#ff0844', fontWeight: 700 }}>Click any car card to switch active vehicle monitoring</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginBottom: '36px' }}>
        {garage.map((car) => {
          const isSelected = car.vehicle_id === selectedVehicle;
          return (
            <div
              key={car.vehicle_id}
              className="luxury-glass"
              style={{
                padding: '24px',
                cursor: 'pointer',
                border: isSelected ? '2px solid #ff0844' : '1px solid rgba(255, 8, 68, 0.2)',
                background: isSelected ? 'linear-gradient(135deg, rgba(255, 8, 68, 0.18), rgba(12, 12, 12, 0.95))' : 'rgba(12, 12, 12, 0.85)',
                position: 'relative'
              }}
            >
              <button
                type="button"
                aria-label={`Seleccionar ${car.model_name}`}
                aria-pressed={isSelected}
                onClick={() => handleCarSelect(car.vehicle_id)}
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  border: 'none',
                  borderRadius: 'inherit',
                  background: 'transparent',
                  cursor: 'pointer',
                  zIndex: 1
                }}
              />
              {isSelected && (
                <span style={{ position: 'absolute', top: '16px', right: '16px', background: '#ff0844', color: '#fff', fontSize: '10px', fontWeight: 900, padding: '3px 10px', borderRadius: '12px', textTransform: 'uppercase', zIndex: 2, pointerEvents: 'none' }}>
                  {connectionStatus === 'online' ? 'API CONNECTED' : connectionStatus === 'checking' ? 'CHECKING CONNECTION' : 'UPDATE FAILED'}
                </span>
              )}
              <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>
                {car.driver_name} • {car.description}
              </span>
              <h3 className="font-serif-luxury" style={{ fontSize: '22px', color: isSelected ? '#ff758c' : '#fff', marginTop: '4px', fontWeight: 800 }}>
                {car.model_name}
              </h3>
              <p style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '2px' }}>{car.tagline}</p>
              <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: '#ff0844', fontWeight: 700 }}>⚡ {car.specs}</span>
                <span style={{ fontSize: '12px', color: '#a1a1aa' }}>ID: {car.vehicle_id}</span>
              </div>
            </div>
          );
        })}
      </div>
      {/* --- Active Monitored Vehicle Banner --- */}
      <div className="luxury-glass" style={{ padding: '20px 28px', marginBottom: '36px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', background: 'linear-gradient(135deg, rgba(255, 8, 68, 0.12), rgba(12, 12, 12, 0.95))' }}>
        <div>
          <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>Currently Monitored Vehicle</span>
          <h2 className="font-serif-luxury" style={{ fontSize: '24px', color: '#fff', fontWeight: 800, marginTop: '2px' }}>
            {activeCar.model_name} <span style={{ color: '#ff0844', fontSize: '16px', fontWeight: 500 }}>(Driver: {activeCar.driver_name})</span>
          </h2>
          <p style={{ fontSize: '13px', color: '#a1a1aa', marginTop: '2px' }}>Operational Mode: <strong style={{ color: '#00f2fe' }}>{activeCar.description}</strong></p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: 700 }}>AI Predicted Vehicle Health</span>
            <div style={{ fontSize: '36px', fontWeight: 900, color: !health ? '#a1a1aa' : health.overall_health_score >= 80 ? '#43e97b' : health.overall_health_score >= 60 ? '#ff758c' : '#ff0844' }}>
              {health ? `${health.overall_health_score}%` : '—'}
            </div>
          </div>
        </div>
      </div>
      {/* --- Live Instrument Cluster --- */}
      <h2 className="font-serif-luxury" style={{ fontSize: '22px', color: '#fff', marginBottom: '16px' }}>
        ⚡ Cockpit Instrument Telemetry & Sound Engine
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '20px', marginBottom: '36px' }}>
        {/* Tachometer RPM Dial */}
        <div className="luxury-glass" style={{ padding: '24px', textAlign: 'center' }}>
          <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>TACHOMETER (ENGINE RPM)</span>
          <div style={{ position: 'relative', margin: '20px auto 14px', width: '140px', height: '140px', borderRadius: '50%', background: 'radial-gradient(circle, #000 60%, rgba(255, 8, 68, 0.1) 100%)', border: '3px solid rgba(255, 8, 68, 0.5)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', boxShadow: '0 0 30px rgba(255, 8, 68, 0.25)' }}>
            <span style={{ fontSize: '32px', fontWeight: 900, color: '#ff0844' }}>
              {telemetry?.rpm != null ? Math.round(telemetry.rpm) : '—'}
            </span>
            <span style={{ fontSize: '11px', color: '#a1a1aa', fontWeight: 700 }}>RPM</span>
          </div>
          <span style={{ fontSize: '12px', color: '#71717a' }}>Peak Torque: 4200 RPM</span>
        </div>
        {/* Speedometer km/h Dial */}
        <div className="luxury-glass" style={{ padding: '24px', textAlign: 'center' }}>
          <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>SPEEDOMETER (KM/H)</span>
          <div style={{ position: 'relative', margin: '20px auto 14px', width: '140px', height: '140px', borderRadius: '50%', background: 'radial-gradient(circle, #000 60%, rgba(0, 242, 254, 0.1) 100%)', border: '3px solid rgba(0, 242, 254, 0.4)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', boxShadow: '0 0 30px rgba(0, 242, 254, 0.2)' }}>
            <span style={{ fontSize: '32px', fontWeight: 900, color: '#00f2fe' }}>
              {telemetry?.speed_kph != null ? Math.round(telemetry.speed_kph) : '—'}
            </span>
            <span style={{ fontSize: '11px', color: '#a1a1aa', fontWeight: 700 }}>KM/H</span>
          </div>
          <span style={{ fontSize: '12px', color: '#71717a' }}>OBD ECU Stream</span>
        </div>
        {/* Thermal Engine Temp */}
        <div className="luxury-glass" style={{ padding: '24px', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>COOLANT THERMAL TEMP</span>
          <div style={{ fontSize: '38px', fontWeight: 900, color: telemetry?.coolant_temp_c != null && telemetry.coolant_temp_c > 100 ? '#ff0844' : '#43e97b', margin: '14px 0' }}>
            {telemetry?.coolant_temp_c != null ? `${Math.round(telemetry.coolant_temp_c)}°C` : '—'}
          </div>
          <span style={{ fontSize: '12px', color: '#a1a1aa' }}>Optimal Range: 85°C - 95°C</span>
        </div>
        {/* Battery & Charging Voltage */}
        <div className="luxury-glass" style={{ padding: '24px', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>ALTERNATOR / BUS VOLTAGE</span>
          <div style={{ fontSize: '38px', fontWeight: 900, color: telemetry?.battery_voltage != null && telemetry.battery_voltage < 12.4 ? '#ff0844' : '#ff758c', margin: '14px 0' }}>
            {telemetry?.battery_voltage != null ? `${telemetry.battery_voltage} V` : '—'}
          </div>
          <span style={{ fontSize: '12px', color: '#a1a1aa' }}>Target: 13.8V - 14.4V</span>
        </div>
      </div>
      {/* --- Predictive Component Degradation Metrics --- */}
      <h2 className="font-serif-luxury" style={{ fontSize: '22px', color: '#fff', marginBottom: '16px' }}>
        🧠 AI Predictive Degradation & Health Forecasting
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: '20px', marginBottom: '36px' }}>
        {/* Brake System */}
        <div className="luxury-glass" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontWeight: 700, color: '#fff', fontSize: '15px' }}>Brake System Pad Lifespan</span>
            <span style={{ fontWeight: 900, fontSize: '18px', color: brakeStatus.color }}>
              {brakeStatus.level === 'unavailable' ? '—' : `${health?.component_scores?.brake_health}%`}
            </span>
          </div>
          <div style={{ height: '8px', background: '#1e293b', borderRadius: '6px', overflow: 'hidden', marginBottom: '12px' }}>
            <div style={{ height: '100%', width: `${brakeStatus.level === 'unavailable' ? 0 : health?.component_scores?.brake_health}%`, background: brakeStatus.color }}></div>
          </div>
          <span style={{ fontSize: '12px', color: brakeStatus.color }}>Estado de frenos: {brakeStatus.label}</span>
        </div>
        {/* Engine Stress */}
        <div className="luxury-glass" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontWeight: 700, color: '#fff', fontSize: '15px' }}>Engine Thermal & Mechanical</span>
            <span style={{ fontWeight: 900, fontSize: '18px', color: engineStatus.color }}>
              {engineStatus.level === 'unavailable' ? '—' : `${health?.component_scores?.engine_health}%`}
            </span>
          </div>
          <div style={{ height: '8px', background: '#1e293b', borderRadius: '6px', overflow: 'hidden', marginBottom: '12px' }}>
            <div style={{ height: '100%', width: `${engineStatus.level === 'unavailable' ? 0 : health?.component_scores?.engine_health}%`, background: engineStatus.color }}></div>
          </div>
          <span style={{ fontSize: '12px', color: engineStatus.color }}>Estado del motor: {engineStatus.label}</span>
        </div>
        {/* Battery Health */}
        <div className="luxury-glass" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontWeight: 700, color: '#fff', fontSize: '15px' }}>Battery & Charging System</span>
            <span style={{ fontWeight: 900, fontSize: '18px', color: batteryStatus.color }}>
              {batteryStatus.level === 'unavailable' ? '—' : `${health?.component_scores?.battery_health}%`}
            </span>
          </div>
          <div style={{ height: '8px', background: '#1e293b', borderRadius: '6px', overflow: 'hidden', marginBottom: '12px' }}>
            <div style={{ height: '100%', width: `${batteryStatus.level === 'unavailable' ? 0 : health?.component_scores?.battery_health}%`, background: batteryStatus.color }}></div>
          </div>
          <span style={{ fontSize: '12px', color: batteryStatus.color }}>Estado de batería: {batteryStatus.label}</span>
        </div>
      </div>
      {/* --- Executive Diagnostic Findings & Step-by-Step Fix Guides --- */}
      <h2 className="font-serif-luxury" style={{ fontSize: '22px', color: '#fff', marginBottom: '16px' }}>
        🛠️ Executive Maintenance Butler & Step-by-Step Fix Solutions
      </h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '36px' }}>
        {health?.plain_language_alerts?.map((alert, idx) => (
          <div key={idx} className="luxury-glass" style={{ padding: '26px', borderLeft: `6px solid ${alert.severity === 'CRITICAL' ? '#ff0844' : alert.severity === 'WARNING' ? '#ff758c' : '#00f2fe'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '10px' }}>
              <h3 className="font-serif-luxury" style={{ fontSize: '20px', fontWeight: 800, color: '#fff' }}>{alert.title}</h3>
              <span style={{ background: alert.severity === 'CRITICAL' ? 'linear-gradient(135deg, #ff0844, #990022)' : alert.severity === 'WARNING' ? 'linear-gradient(135deg, #ff758c, #ff0844)' : 'linear-gradient(135deg, #00f2fe, #4facfe)', color: '#fff', padding: '4px 14px', borderRadius: '20px', fontSize: '11px', fontWeight: 900, letterSpacing: '0.5px' }}>
                {alert.severity} SEVERITY
              </span>
            </div>
            <p style={{ color: '#cbd5e1', fontSize: '14px', lineHeight: 1.6, marginBottom: '16px' }}>
              <strong>Diagnostic Anomaly Finding:</strong> {alert.explanation}
            </p>
            <button
              onClick={() => setActiveSolution(alert)}
              className="btn-red-luxury"
              style={{ fontSize: '13px', padding: '10px 20px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              🛠️ View DIY Repair Solution Guide & Cost Breakdown
            </button>
          </div>
        ))}
      </div>
      {/* --- Interactive AI Repair Assistant Floating Chatbot Widget --- */}
      {isChatOpen && (
        <div id="repair-chat" role="dialog" aria-labelledby="repair-chat-title" style={{ position: 'fixed', bottom: '24px', right: '24px', width: '420px', height: '560px', background: '#08080c', border: '2px solid #ff0844', borderRadius: '24px', zIndex: 3000, display: 'flex', flexDirection: 'column', boxShadow: '0 20px 60px rgba(255, 8, 68, 0.3)', overflow: 'hidden' }}>
          {/* Chat Header */}
          <div style={{ background: 'linear-gradient(135deg, #18080c, #08080c)', padding: '18px 20px', borderBottom: '1px solid rgba(255, 8, 68, 0.4)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '20px' }}>🤖</span>
              <div>
                <h3 id="repair-chat-title" className="font-serif-luxury text-red-gradient" style={{ fontSize: '16px', fontWeight: 800 }}>VehicleIQ AI Repair Concierge</h3>
                <span style={{ fontSize: '11px', color: '#a1a1aa', fontWeight: 700 }}>
                  {connectionStatus === 'online' ? '● API connected' : '● Data update unconfirmed'}
                </span>
              </div>
            </div>
            <button aria-label="Cerrar chat" onClick={() => setIsChatOpen(false)} style={{ background: 'transparent', color: '#a1a1aa', border: 'none', fontSize: '18px', cursor: 'pointer', fontWeight: 800 }}>✕</button>
          </div>
          {/* Quick Suggestion Chips */}
          <div style={{ padding: '10px 14px', background: '#0a0a0f', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', gap: '8px', overflowX: 'auto' }}>
            <button onClick={() => handleSendMessage('My brakes squeal')} style={{ background: 'rgba(255, 8, 68, 0.15)', color: '#ff758c', border: '1px solid rgba(255, 8, 68, 0.4)', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', whiteSpace: 'nowrap', cursor: 'pointer' }}>
              🛑 Squealing Brakes
            </button>
            <button onClick={() => handleSendMessage('Engine temperature rose to 105C')} style={{ background: 'rgba(255, 8, 68, 0.15)', color: '#ffb199', border: '1px solid rgba(255, 8, 68, 0.4)', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', whiteSpace: 'nowrap', cursor: 'pointer' }}>
              🔥 Engine Overheat
            </button>
            <button onClick={() => handleSendMessage('Battery voltage dropped')} style={{ background: 'rgba(0, 242, 254, 0.12)', color: '#00f2fe', border: '1px solid rgba(0, 242, 254, 0.3)', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', whiteSpace: 'nowrap', cursor: 'pointer' }}>
              ⚡ Battery Voltage Drop
            </button>
          </div>
          {/* Chat Messages Log */}
          <div style={{ flex: 1, padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {messages.map((msg, index) => (
              <div key={index} style={{ alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
                <div style={{
                  background: msg.sender === 'user' ? 'linear-gradient(135deg, #ff0844, #990022)' : '#12121a',
                  color: '#ffffff',
                  padding: '12px 16px',
                  borderRadius: '16px',
                  fontSize: '13px',
                  lineHeight: 1.5,
                  border: msg.sender === 'ai' ? '1px solid rgba(255, 8, 68, 0.3)' : 'none',
                  boxShadow: '0 4px 15px rgba(0,0,0,0.5)'
                }}>
                  {msg.text}
                  {msg.solution && (
                    <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                      <div style={{ fontSize: '12px', color: '#43e97b', fontWeight: 800 }}>💰 Est. Cost: {msg.solution.estimated_cost}</div>
                      <button
                        onClick={() => setActiveSolution(msg.solution!)}
                        style={{ marginTop: '8px', background: '#00f2fe', color: '#000', border: 'none', padding: '6px 12px', borderRadius: '8px', fontSize: '11px', fontWeight: 900, cursor: 'pointer', width: '100%' }}
                      >
                        🛠️ Open Full DIY Fix Guide
                      </button>
                    </div>
                  )}
                </div>
                <span style={{ fontSize: '10px', color: '#71717a', display: 'block', marginTop: '4px', textAlign: msg.sender === 'user' ? 'right' : 'left' }}>
                  {msg.timestamp}
                </span>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
          {/* Chat Input Bar */}
          <div style={{ padding: '14px', background: '#0c0c12', borderTop: '1px solid rgba(255, 8, 68, 0.3)', display: 'flex', gap: '10px' }}>
            <input
              ref={chatInputRef}
              aria-label="Mensaje para el asistente"
              type="text"
              placeholder="Type your vehicle issue or error code..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              style={{ flex: 1, background: '#181824', color: '#fff', border: '1px solid rgba(255, 8, 68, 0.4)', borderRadius: '12px', padding: '10px 14px', fontSize: '13px', outline: 'none' }}
            />
            <button
              onClick={() => handleSendMessage()}
              style={{ background: 'linear-gradient(135deg, #ff0844, #990022)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: '12px', fontWeight: 900, cursor: 'pointer' }}
            >
              Send
            </button>
          </div>
        </div>
      )}
      {/* --- DIY Solution Guide Modal --- */}
      {activeSolution && (
        <AccessibleModal titleId="diy-guide-title" onClose={() => setActiveSolution(null)}>
          <div className="luxury-glass" style={{ width: '100%', maxWidth: '780px', maxHeight: '90vh', overflowY: 'auto', padding: '32px', border: '1px solid #ff0844', background: '#0a0a0f' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255, 8, 68, 0.3)', paddingBottom: '18px', marginBottom: '24px' }}>
              <div>
                <span style={{ background: '#ff0844', color: '#fff', fontSize: '10px', fontWeight: 900, padding: '3px 10px', borderRadius: '10px', textTransform: 'uppercase' }}>
                  {activeSolution.severity} URGENCY
                </span>
                <h2 id="diy-guide-title" className="font-serif-luxury text-red-gradient" style={{ fontSize: '24px', fontWeight: 900, marginTop: '8px' }}>
                  {activeSolution.solution_title}
                </h2>
              </div>
              <button data-dialog-close autoFocus onClick={() => setActiveSolution(null)} style={{ background: '#ff0844', color: '#fff', border: 'none', padding: '8px 18px', borderRadius: '10px', cursor: 'pointer', fontWeight: 800 }}>Close</button>
            </div>
            {/* Cost & Urgency Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '28px' }}>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '14px', border: '1px solid rgba(255, 8, 68, 0.3)' }}>
                <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: 700 }}>Estimated Repair Cost</span>
                <div style={{ fontSize: '20px', fontWeight: 900, color: '#43e97b', marginTop: '4px' }}>{activeSolution.estimated_cost}</div>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '14px', border: '1px solid rgba(255, 8, 68, 0.3)' }}>
                <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: 700 }}>Urgency Rating</span>
                <div style={{ fontSize: '15px', fontWeight: 800, color: '#ff758c', marginTop: '4px' }}>{activeSolution.urgency}</div>
              </div>
            </div>
            {/* DIY Step-by-Step Fix Instructions */}
            <h3 className="font-serif-luxury" style={{ fontSize: '18px', color: '#00f2fe', marginBottom: '14px' }}>
              🛠️ Step-by-Step DIY Repair Instructions:
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '28px' }}>
              {activeSolution.diy_fix_steps?.map((step, sIdx) => (
                <div key={sIdx} style={{ background: 'rgba(18, 18, 28, 0.9)', padding: '14px 18px', borderRadius: '12px', borderLeft: '4px solid #ff0844', color: '#cbd5e1', fontSize: '14px' }}>
                  <strong style={{ color: '#ff758c' }}>Step {sIdx + 1}:</strong> {step}
                </div>
              ))}
            </div>
            {/* Recommended OEM Replacement Parts */}
            {activeSolution.parts_needed?.length > 0 && (
              <div style={{ marginBottom: '28px' }}>
                <h4 style={{ fontSize: '13px', color: '#a1a1aa', marginBottom: '10px', textTransform: 'uppercase', fontWeight: 700 }}>Recommended OEM Replacement Parts:</h4>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  {activeSolution.parts_needed.map((part, pIdx) => (
                    <span key={pIdx} style={{ background: 'rgba(255, 8, 68, 0.15)', color: '#ff758c', padding: '8px 16px', borderRadius: '10px', fontSize: '13px', fontWeight: 700, border: '1px solid rgba(255, 8, 68, 0.4)' }}>
                      🔧 {part}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div style={{ display: 'flex', gap: '14px' }}>
              <button onClick={() => alert('Master Concierge Mechanic dispatched to your location!')} className="btn-red-luxury" style={{ flex: 1, padding: '16px', fontSize: '15px' }}>
                👨‍🔧 Dispatch Official White-Glove Concierge Service
              </button>
            </div>
          </div>
        </AccessibleModal>
      )}
      {/* --- Executive Report Modal --- */}
      {showReportModal && (
        <AccessibleModal
          titleId="report-title"
          onClose={() => setShowReportModal(false)}
          returnFocusElement={reportTriggerRef.current}
        >
          <div className="luxury-glass" style={{ width: '100%', maxWidth: '880px', maxHeight: '90vh', overflowY: 'auto', padding: '28px', border: '1px solid #ff0844', background: '#0a0a0f' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h2 id="report-title" className="font-serif-luxury text-red-gradient" style={{ fontSize: '22px' }}>Executive Diagnostic Certificate — {activeCar.model_name}</h2>
              <button data-dialog-close autoFocus onClick={() => setShowReportModal(false)} style={{ background: '#ff0844', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', fontWeight: 800 }}>Close</button>
            </div>
            <div dangerouslySetInnerHTML={{ __html: reportHtml }} />
          </div>
        </AccessibleModal>
      )}
    </div>
  );
}
