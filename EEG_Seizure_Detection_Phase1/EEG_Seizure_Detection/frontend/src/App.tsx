import { useMemo, useState } from "react";
import {
  Activity, AlertCircle, ArrowUpRight, Bell, Brain,
  CalendarDays, CheckCircle2, ChevronDown, CircleHelp, Clock3, Database,
  FilePlus2, FileText, Gauge, LayoutDashboard, Menu, Microscope,
  MoreHorizontal, Search, Settings2, ShieldCheck, SlidersHorizontal,
  Upload, Users, Waves, X,
} from "lucide-react";

type Section = "Overview" | "EEG Analysis" | "Recordings" | "Model Performance" | "Patients";

const navigation: { label: Section; icon: typeof LayoutDashboard }[] = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "EEG Analysis", icon: Waves },
  { label: "Recordings", icon: Database },
  { label: "Model Performance", icon: Gauge },
  { label: "Patients", icon: Users },
];

const channelNames = ["FP1-F7", "F7-T7", "T7-P7", "P7-O1", "FP1-F3", "F3-C3", "C3-P3", "P3-O1"];

function SignalPreview({ compact = false }: { compact?: boolean }) {
  const traces = useMemo(() => Array.from({ length: compact ? 3 : 5 }, (_, row) => {
    const points = Array.from({ length: 150 }, (_, i) => {
      const spike = i > 83 && i < 91 ? Math.sin((i - 83) * 1.8) * (1 - Math.abs(i - 87) / 5) * 17 : 0;
      const y = 24 + Math.sin(i * 0.19 + row * 1.7) * 5 + Math.sin(i * 0.61 + row) * 2.1 + spike;
      return `${(i / 149) * 1000},${y}`;
    });
    return points.join(" ");
  }), [compact]);

  return (
    <svg className={compact ? "signal-svg signal-svg-compact" : "signal-svg"} viewBox={`0 0 1000 ${compact ? 100 : 170}`} preserveAspectRatio="none" role="img" aria-label="Illustrative EEG waveform preview">
      {Array.from({ length: compact ? 3 : 5 }, (_, i) => (
        <g key={i}>
          <line x1="0" x2="1000" y1={i * (compact ? 33 : 34) + 16} y2={i * (compact ? 33 : 34) + 16} className="signal-grid" />
          <polyline points={traces[i]} transform={`translate(0 ${i * (compact ? 33 : 34)})`} className={i === 2 ? "signal-line signal-line-accent" : "signal-line"} />
        </g>
      ))}
    </svg>
  );
}

function MetricCard({ title, value, change, icon: Icon, tone = "blue", note }: {
  title: string; value: string; change: string; icon: typeof Activity;
  tone?: "blue" | "violet" | "green" | "amber"; note: string;
}) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span className="metric-label">{title}</span>
        <span className={`metric-icon ${tone}`}><Icon size={18} /></span>
      </div>
      <div className="metric-value-row">
        <strong>{value}</strong>
        <span className="metric-change"><ArrowUpRight size={13} />{change}</span>
      </div>
      <p className="metric-note">{note}</p>
    </article>
  );
}

function App() {
  const [active, setActive] = useState<Section>("Overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [showUpload, setShowUpload] = useState(false);

  const pageTitle = active === "Overview" ? "Overview" : active;
  const recordings = [
    { id: "CHB01-03", patient: "Patient 01", date: "Nov 02, 2026", duration: "1h 00m", status: "Reviewed", risk: "Normal" },
    { id: "CHB02-16", patient: "Patient 02", date: "Nov 02, 2026", duration: "1h 00m", status: "Processed", risk: "Seizure event" },
    { id: "CHB03-01", patient: "Patient 03", date: "Nov 01, 2026", duration: "1h 00m", status: "Processed", risk: "Normal" },
    { id: "CHB04-08", patient: "Patient 04", date: "Oct 31, 2026", duration: "0h 45m", status: "Pending", risk: "Pending review" },
  ];
  const filteredRecordings = recordings.filter((recording) =>
    [recording.id, recording.patient, recording.status, recording.risk].join(" ").toLowerCase().includes(query.toLowerCase()),
  );

  const sectionDescription: Record<Section, string> = {
    Overview: "A research workspace for reviewing EEG data and model outputs.",
    "EEG Analysis": "Inspect multichannel EEG signals and review analysis outputs.",
    Recordings: "Browse and manage EEG recordings in the research cohort.",
    "Model Performance": "Review validated model metrics and experiment comparisons.",
    Patients: "Explore patient-level recording and evaluation summaries.",
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Brain size={22} strokeWidth={2.2} /></div>
          <div><strong>NeuroScope</strong><span>EEG RESEARCH SUITE</span></div>
          <button className="icon-button mobile-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><X size={18} /></button>
        </div>

        <div className="workspace-switch">
          <div className="workspace-avatar">NS</div>
          <div className="workspace-copy"><strong>Research Workspace</strong><span>CHB-MIT Cohort</span></div>
          <ChevronDown size={15} className="muted-icon" />
        </div>

        <div className="nav-caption">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          {navigation.map(({ label, icon: Icon }) => (
            <button key={label} className={`nav-item ${active === label ? "active" : ""}`} onClick={() => { setActive(label); setSidebarOpen(false); }}>
              <Icon size={17} /><span>{label}</span>
              {label === "Recordings" && <span className="nav-count">683</span>}
            </button>
          ))}
        </nav>

        <div className="nav-caption nav-caption-spaced">TOOLS</div>
        <button className="nav-item" onClick={() => setShowUpload(true)}><Upload size={17} /><span>Import EEG data</span></button>
        <button className="nav-item" onClick={() => setActive("Model Performance")}><Microscope size={17} /><span>Experiments</span></button>

        <div className="sidebar-bottom">
          <div className="help-card">
            <div className="help-icon"><CircleHelp size={17} /></div>
            <strong>Research guide</strong>
            <p>Learn about the evaluation workflow and dataset protocol.</p>
            <a href="https://physionet.org/content/chbmit/1.0.0/" target="_blank" rel="noreferrer">CHB-MIT dataset docs ↗</a>
          </div>
          <button className="profile-row" onClick={() => setActive("Patients")}>
            <div className="profile-avatar">R</div>
            <div><strong>Researcher</strong><span>Local workspace</span></div>
            <MoreHorizontal size={18} className="muted-icon" />
          </button>
        </div>
      </aside>

      {sidebarOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button menu-trigger" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
            <div className="breadcrumb">Workspace <span>/</span> <strong>{pageTitle}</strong></div>
          </div>
          <div className="topbar-actions">
            <div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search recordings..." aria-label="Search recordings" /></div>
            <button className="icon-button notification-button" aria-label="Notifications"><Bell size={18} /><i /></button>
            <div className="top-avatar">R</div>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div><div className="eyebrow"><span className="status-dot" /> RESEARCH ENVIRONMENT</div><h1>{pageTitle}</h1><p>{sectionDescription[active]}</p></div>
            <div className="heading-actions"><span className="date-chip"><CalendarDays size={15} /> Nov 03, 2026</span><button className="primary-button" onClick={() => setShowUpload(true)}><FilePlus2 size={16} /> Import recording</button></div>
          </div>

          <div className="demo-banner"><AlertCircle size={16} /><span><strong>Preview environment:</strong> All dashboard values and waveforms are illustrative mock data. No clinical predictions are being made.</span><span className="demo-tag">DEMO DATA</span></div>

          {active === "Overview" ? (
            <>
              <section className="metrics-grid" aria-label="Research summary metrics">
                <MetricCard title="Recordings processed" value="683" change="Cohort target" icon={Database} tone="blue" note="Audited primary cohort recordings" />
                <MetricCard title="Independent patients" value="23" change="Patient-wise" icon={Users} tone="violet" note="CHB01 and CHB21 grouped together" />
                <MetricCard title="Annotated seizure events" value="185" change="Audited" icon={Activity} tone="amber" note="Across the primary cohort" />
                <MetricCard title="Preprocessing status" value="In progress" change="Phase 1" icon={Clock3} tone="green" note="Full-cohort export and validation" />
              </section>

              <section className="content-grid">
                <article className="panel signal-panel">
                  <div className="panel-heading"><div><span className="panel-kicker">SIGNAL PREVIEW</span><h2>EEG waveform monitor</h2></div><button className="subtle-button" onClick={() => setActive("EEG Analysis")}>Open analysis <ArrowUpRight size={14} /></button></div>
                  <div className="signal-meta"><span><i className="legend-dot" /> Illustrative EEG channels</span><span>10 sec window · 256 Hz</span></div>
                  <SignalPreview />
                  <div className="channel-strip">{channelNames.slice(0, 5).map((channel, index) => <span key={channel}><i className={index === 2 ? "channel-dot active" : "channel-dot"} />{channel}</span>)}</div>
                </article>

                <article className="panel protocol-panel">
                  <div className="panel-heading"><div><span className="panel-kicker">EVALUATION DESIGN</span><h2>Research protocol</h2></div><ShieldCheck size={19} className="protocol-shield" /></div>
                  <div className="protocol-step"><span className="step-number">01</span><div><strong>Patient-wise evaluation</strong><p>Leave-One-Patient-Out (LOPO) strategy</p></div><CheckCircle2 size={16} className="step-check" /></div>
                  <div className="protocol-step"><span className="step-number">02</span><div><strong>Leakage-safe normalization</strong><p>Fit on inner training patients only</p></div><CheckCircle2 size={16} className="step-check" /></div>
                  <div className="protocol-step"><span className="step-number">03</span><div><strong>Fixed signal configuration</strong><p>17 channels · 10s windows · 5s stride</p></div><CheckCircle2 size={16} className="step-check" /></div>
                  <div className="protocol-note"><ShieldCheck size={15} /><span>Test patients remain isolated from model selection and threshold tuning.</span></div>
                </article>
              </section>

              <section className="panel recordings-panel">
                <div className="panel-heading"><div><span className="panel-kicker">LATEST ACTIVITY</span><h2>Recent recordings</h2></div><button className="subtle-button" onClick={() => setActive("Recordings")}>View all <ArrowUpRight size={14} /></button></div>
                <RecordingTable rows={filteredRecordings} />
              </section>
            </>
          ) : active === "EEG Analysis" ? (
            <section className="panel analysis-view">
              <div className="panel-heading"><div><span className="panel-kicker">SIGNAL INSPECTION</span><h2>Multichannel EEG viewer</h2></div><span className="preview-chip">Illustrative signal</span></div>
              <div className="analysis-toolbar"><span>Recording <strong>CHB01-03</strong></span><span>Sampling rate <strong>256 Hz</strong></span><span>Window <strong>10 seconds</strong></span><button className="subtle-button"><SlidersHorizontal size={14} /> Channels</button></div>
              <SignalPreview />
              <div className="channel-list">{channelNames.map((channel, i) => <div key={channel}><span className="channel-index">{String(i + 1).padStart(2, "0")}</span><span>{channel}</span><span className="channel-state">Preview only</span></div>)}</div>
            </section>
          ) : active === "Recordings" ? (
            <section className="panel recordings-panel full-panel"><div className="panel-heading"><div><span className="panel-kicker">DATA LIBRARY</span><h2>Recording library</h2></div><button className="primary-button" onClick={() => setShowUpload(true)}><Upload size={15} /> Import data</button></div><RecordingTable rows={filteredRecordings} /></section>
          ) : active === "Model Performance" ? (
            <section className="panel empty-state"><div className="empty-icon"><Gauge size={26} /></div><h2>Model evaluation is not available yet</h2><p>Performance charts will appear after patient-wise model training and held-out evaluation are complete. We will report sensitivity, specificity, precision, F1, AUROC and AUPRC from verified test folds.</p><span className="preview-chip">Awaiting validated experiments</span></section>
          ) : (
            <section className="panel empty-state"><div className="empty-icon"><Users size={26} /></div><h2>Patient summaries</h2><p>Patient-level views will be populated from the audited cohort manifest and validated fold results. Identifiers will remain pseudonymous.</p><span className="preview-chip">23 independent patients in cohort</span></section>
          )}
          <footer className="page-footer"><span>NeuroScope Research Suite <span className="footer-separator">·</span> Academic prototype</span><span>Not for clinical diagnosis or treatment</span></footer>
        </div>
      </main>

      {showUpload && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowUpload(false); }}><div className="upload-modal" role="dialog" aria-modal="true" aria-labelledby="upload-title"><button className="modal-close icon-button" onClick={() => setShowUpload(false)} aria-label="Close dialog"><X size={18} /></button><div className="upload-icon"><Upload size={22} /></div><h2 id="upload-title">Import EEG recording</h2><p>EDF import will be connected to the FastAPI preprocessing service in a later milestone.</p><div className="upload-dropzone"><FileText size={24} /><strong>EDF upload integration coming next</strong><span>CHB-MIT files are currently processed by the Python pipeline.</span></div><button className="primary-button modal-action" onClick={() => setShowUpload(false)}>Got it</button></div></div>}
    </div>
  );
}

function RecordingTable({ rows }: { rows: { id: string; patient: string; date: string; duration: string; status: string; risk: string }[] }) {
  if (rows.length === 0) return <div className="table-empty">No recordings match your search.</div>;
  return (
    <div className="table-wrap"><table><thead><tr><th>RECORDING ID</th><th>PATIENT</th><th>DATE</th><th>DURATION</th><th>PROCESSING</th><th>ANNOTATION</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td><span className="recording-file"><FileText size={15} />{row.id}</span></td><td>{row.patient}</td><td>{row.date}</td><td>{row.duration}</td><td><span className={`table-status ${row.status.toLowerCase()}`}><i />{row.status}</span></td><td><span className={row.risk === "Seizure event" ? "risk-event" : "risk-normal"}>{row.risk}</span></td></tr>)}</tbody></table></div>
  );
}

export default App;
