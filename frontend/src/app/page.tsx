'use client';

import { useEffect, useMemo, useState } from 'react';
import './mars-lab.css';
import './mars-atmosphere.css';
import MarsPlanetScene, { type MarsPhase } from './MarsPlanetScene';

type Tab = 'overview' | 'classify' | 'archive' | 'map' | 'anomalies';

const API = typeof window !== 'undefined'
  ? `http://${window.location.hostname}:8000`
  : 'http://127.0.0.1:8000';

const CLUSTER_COLORS = ['#e45e39', '#2f6c82', '#93a84b', '#b17b9e', '#d19a42', '#657a71'];
const CHEMICAL_LABELS = ['basalt', 'carbonate', 'chloride', 'iron_oxide', 'oxalate', 'oxychlorine', 'phyllosilicate', 'silicate', 'sulfate', 'sulfide'];

interface Experiment {
  experiment_id: string;
  filename?: string;
  cluster?: number;
  anomaly?: number | boolean;
  anomaly_status?: string;
  anomaly_score?: number;
  [key: string]: any;
}
interface Overview {
  total_experiments: number;
  total_features: number;
  total_clusters: number;
  total_anomalies: number;
  pca_components: number;
  pca_explained_variance: number;
  chemical_families?: number;
}
interface Cluster { cluster: number; experiment_count: number; anomaly_count: number; percentage: number; }
interface PCAPoint { experiment_id: string; pc1: number; pc2: number; cluster: number; anomaly: boolean; }
interface QmsPoint { amu: number; counts_per_second: number; }
interface QmsResult { experiment_id: string; filename: string; total_measurements: number; displayed_points: number; points: QmsPoint[]; }
interface SpectrumPoint { time: number; temp: number; 'm/z': number; abundance: number; }
interface ChemicalPrediction { chemical_family: string; prediction: number; score: number; status: string; }
interface PredictionResult {
  success: boolean; filename: string; total_measurements: number; features_extracted: number;
  total_chemical_families: number; detected_count: number; detected_families: string[];
  predictions: ChemicalPrediction[]; spectrum: SpectrumPoint[];
}

const NAV: { id: Tab; number: string; title: string; sub: string }[] = [
  { id: 'overview', number: '01', title: 'Overview', sub: 'Mission desk' },
  { id: 'classify', number: '02', title: 'Spectral lab', sub: 'Classify a sample' },
  { id: 'archive', number: '03', title: 'Experiment archive', sub: 'Browse QMS records' },
  { id: 'map', number: '04', title: 'Data map', sub: 'PCA + clusters' },
  { id: 'anomalies', number: '05', title: 'Outlier watch', sub: 'Flagged records' },
];

function fmt(value: unknown, digits = 2) {
  if (typeof value === 'number' && Number.isFinite(value)) return value.toLocaleString(undefined, { maximumFractionDigits: digits });
  return value == null || value === '' ? '—' : String(value);
}
function label(value: string) { return value.replaceAll('_', ' '); }
function isAnomaly(item: Experiment) {
  return item.anomaly_status?.toLowerCase() === 'anomaly' || item.anomaly === -1 || item.anomaly === true;
}

export default function Home() {
  const [tab, setTab] = useState<Tab>('overview');
  const [phase, setPhase] = useState<MarsPhase>('dawn');
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [anomalies, setAnomalies] = useState<Experiment[]>([]);
  const [pcaPoints, setPcaPoints] = useState<PCAPoint[]>([]);
  const [search, setSearch] = useState('');
  const [clusterFilter, setClusterFilter] = useState('all');
  const [selected, setSelected] = useState<Experiment | null>(null);
  const [selectedSpectrum, setSelectedSpectrum] = useState<QmsResult | null>(null);
  const [spectrumLoading, setSpectrumLoading] = useState(false);
  const [spectrumError, setSpectrumError] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState('');

  async function fetchAPI(path: string) {
    const response = await fetch(`${API}${path}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
    return response.json();
  }

  async function loadDashboard() {
    setLoading(true); setError('');
    try {
      const [health, overviewData, experimentData, clusterData, anomalyData, pcaData] = await Promise.all([
        fetchAPI('/api/health'), fetchAPI('/api/overview'), fetchAPI('/api/experiments'),
        fetchAPI('/api/clusters'), fetchAPI('/api/anomalies'), fetchAPI('/api/visualization/pca'),
      ]);
      if (health.status !== 'healthy') throw new Error('Backend health check failed.');
      setOverview(overviewData);
      setExperiments(Array.isArray(experimentData) ? experimentData : experimentData.experiments || []);
      setClusters(Array.isArray(clusterData) ? clusterData : clusterData.clusters || []);
      setAnomalies(Array.isArray(anomalyData) ? anomalyData : anomalyData.anomalies || []);
      setPcaPoints(pcaData.points || []);
      setConnected(true);
    } catch (err: any) {
      setConnected(false); setError(err?.message || 'Unable to connect to the API.');
    } finally { setLoading(false); }
  }

  async function analyzeSpectrum() {
    if (!selectedFile) { setPredictionError('Choose a CSV spectrum first.'); return; }
    setPredictionLoading(true); setPredictionError(''); setPrediction(null);
    try {
      const body = new FormData(); body.append('file', selectedFile);
      const response = await fetch(`${API}/api/predict`, { method: 'POST', body });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.detail || result.message || 'Spectrum analysis failed.');
      setPrediction(result as PredictionResult);
    } catch (err: any) { setPredictionError(err?.message || 'Unable to analyze this file.'); }
    finally { setPredictionLoading(false); }
  }

  useEffect(() => { void loadDashboard(); }, []);

  useEffect(() => {
    const phases: MarsPhase[] = ['dawn', 'day', 'dust', 'night'];
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) return;
    let index = 0;
    const timer = window.setInterval(() => {
      index = (index + 1) % phases.length;
      setPhase(phases[index]);
    }, 28000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selected) { setSelectedSpectrum(null); setSpectrumError(''); return; }
    const controller = new AbortController();
    async function getSpectrum() {
      setSpectrumLoading(true); setSelectedSpectrum(null); setSpectrumError('');
      try {
        const response = await fetch(`${API}/api/experiment/${encodeURIComponent(selected!.experiment_id)}/spectrum`, { cache: 'no-store', signal: controller.signal });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Unable to load this QMS spectrum.');
        setSelectedSpectrum(result as QmsResult);
      } catch (err: any) {
        if (err?.name !== 'AbortError') setSpectrumError(err?.message || 'Unable to load QMS spectrum.');
      } finally { if (!controller.signal.aborted) setSpectrumLoading(false); }
    }
    void getSpectrum();
    return () => controller.abort();
  }, [selected]);

  const filteredExperiments = useMemo(() => experiments.filter((item) => {
    const matchesSearch = JSON.stringify(item).toLowerCase().includes(search.toLowerCase());
    const matchesCluster = clusterFilter === 'all' || String(item.cluster) === clusterFilter;
    return matchesSearch && matchesCluster;
  }), [experiments, search, clusterFilter]);

  const selectedPca = useMemo(() => selected
    ? pcaPoints.find((point) => String(point.experiment_id) === String(selected.experiment_id)) || null
    : null, [selected, pcaPoints]);

  const selectedFeatures = useMemo(() => {
    if (!selected) return [];
    const ignore = new Set(['experiment_id', 'filename', 'cluster', 'anomaly', 'anomaly_status', 'anomaly_score', 'records']);
    const priority = ['peak_amu', 'max_amu', 'max_counts', 'mean_counts', 'median_counts', 'std_counts', 'total_counts', 'zero_count_percentage', 'mean_rf_counts', 'time_duration_seconds', 'unique_amu'];
    return Object.entries(selected).filter(([key, value]) => !ignore.has(key) && typeof value === 'number' && Number.isFinite(value))
      .sort(([a], [b]) => (priority.indexOf(a) < 0 ? 999 : priority.indexOf(a)) - (priority.indexOf(b) < 0 ? 999 : priority.indexOf(b))).slice(0, 12);
  }, [selected]);

  const pageInfo = NAV.find((item) => item.id === tab)!;

  return (
    <main className="ml-app" data-phase={phase}>
      <header className="ml-topbar">
        <button className="ml-brand" onClick={() => setTab('overview')} aria-label="MARS LAB home">
          <span className="ml-brand-mark"><span /></span>
          <span className="ml-brand-name">MARS<span>LAB</span><small>PLANETARY SAMPLE INTELLIGENCE</small></span>
        </button>
        <nav className="ml-nav" aria-label="Main navigation">
          {NAV.map((item) => <button key={item.id} className={`ml-nav-item ${tab === item.id ? 'is-active' : ''}`} onClick={() => { setTab(item.id); setSelected(null); }}>
            <span className="ml-nav-num">{item.number}</span><span>{item.title}</span>
          </button>)}
        </nav>
        <div className="ml-top-actions">
          <span className={`ml-status ${connected ? 'online' : loading ? 'pending' : 'offline'}`}><i />{loading ? 'SYNCING' : connected ? 'API ONLINE' : 'API OFFLINE'}</span>
          <span className="ml-cycle-indicator" title="Decorative simulated lighting cycle, not live Mars weather"><i /> ATMOSPHERE <strong>{phase.toUpperCase()}</strong></span><button className="ml-refresh" onClick={() => void loadDashboard()} disabled={loading} title="Refresh data">↻</button>
        </div>
      </header>

      <div className="ml-page-wrap">
        <div className="ml-page-heading">
          <div><span className="ml-eyebrow">FIELD STATION 01 <b>/</b> {pageInfo.number} — {pageInfo.sub.toUpperCase()}</span><h1>{pageInfo.title}<span className="ml-title-dot">.</span></h1></div>
          <div className="ml-heading-meta"><span className="ml-meta-label">DATA SOURCE</span><strong>NASA / MSL / SAM</strong><span className="ml-meta-line">PARTIALLY PROCESSED QMS · LEVEL 1A</span></div>
        </div>

        {!connected && !loading && <div className="ml-alert"><div><strong>Connection needs attention</strong><p>{error} <span>API: {API}</span></p></div><button onClick={() => void loadDashboard()}>Retry connection ↗</button></div>}

        {tab === 'overview' && <>
          <section className="ml-hero">
            <div className="ml-hero-copy"><div className="ml-stamp"><span className="ml-stamp-dot" /> RESEARCH ENVIRONMENT / SIMULATED LIGHT CYCLE</div>
              <p className="ml-hero-overline">THE RED PLANET, READ THROUGH DATA</p>
              <h2>Every sample<br /><em>leaves a signal.</em></h2>
              <p className="ml-hero-description">A scientific workspace for exploring Mars Sample Analysis at Mars (SAM) measurements, mapping statistical patterns and screening new spectra for chemical-family signals.</p>
              <div className="ml-hero-actions"><button className="ml-button ml-button-light" onClick={() => setTab('archive')}>Explore SAM archive <span>↗</span></button><button className="ml-text-button" onClick={() => setTab('classify')}>Analyze a spectrum <span>→</span></button></div>
              <div className="ml-hero-foot"><span>MISSION DATA</span><b>MSL · SAM · QMS</b><span className="ml-hero-divider" /><span>ANALYTICS</span><b>PCA / K-MEANS / IF</b></div>
            </div>
            <MarsPlanetScene phase={phase} /></section>
        </>}

        {tab === 'classify' && <section className="ml-classify-layout">
          <div className="ml-classify-intro"><span className="ml-section-index">02 / MODEL WORKSPACE</span><h2>Turn a spectrum<br /><em>into a hypothesis.</em></h2><p>Upload a CSV with <code>time</code>, <code>temp</code>, <code>m/z</code> and <code>abundance</code> columns. The trained multi-label classifier scores ten chemical families independently.</p><div className="ml-model-facts"><div><strong>10</strong><span>chemical families</span></div><div><strong>395</strong><span>model features</span></div><div><strong>0.782</strong><span>validation macro-F1</span></div></div><div className="ml-model-warning">MODEL OUTPUTS ARE SCORES — NOT CALIBRATED PROBABILITIES OR DEFINITIVE CHEMICAL CONFIRMATIONS.</div></div>
          <div className="ml-classifier-workspace"><div className="ml-panel ml-upload-panel"><PanelTitle eyebrow="INPUT / CSV SPECTRUM" title="Load a sample" detail="CSV file · comma separated values"/><label className={`ml-dropzone ${selectedFile ? 'has-file' : ''}`} htmlFor="ml-spectrum-file"><input id="ml-spectrum-file" type="file" accept=".csv,text/csv" onChange={(event) => { setSelectedFile(event.target.files?.[0] || null); setPrediction(null); setPredictionError(''); }}/><span className="ml-upload-icon">↥</span><strong>{selectedFile ? selectedFile.name : 'Drop a spectrum file here'}</strong><span>{selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} KB · Ready to analyze` : 'or click to browse from your computer'}</span><small>REQUIRED FIELDS: TIME · TEMP · M/Z · ABUNDANCE</small></label>{predictionError && <p className="ml-inline-error">{predictionError}</p>}<button className="ml-button ml-button-orange ml-analyze-button" onClick={() => void analyzeSpectrum()} disabled={!selectedFile || predictionLoading}>{predictionLoading ? 'Analyzing sample…' : 'Run chemical-family analysis  →'}</button></div>
            {predictionLoading && <div className="ml-panel ml-loading-card"><span className="ml-spinner"/><div><strong>Processing spectral signature</strong><p>Extracting features and scoring chemical families…</p></div></div>}
            {prediction && <div className="ml-results"><div className="ml-results-head"><div><span className="ml-section-index">OUTPUT / {prediction.filename}</span><h3>Classification results</h3></div><span className="ml-result-count">{prediction.detected_count} / {prediction.total_chemical_families} detected</span></div><div className="ml-result-metrics"><Metric label="Measurements" value={fmt(prediction.total_measurements, 0)} note="Rows in uploaded file" accent="orange"/><Metric label="Features extracted" value={fmt(prediction.features_extracted, 0)} note="Input descriptors" accent="blue"/><Metric label="Families scored" value={fmt(prediction.total_chemical_families, 0)} note="Independent labels" accent="green"/></div><div className="ml-panel"><PanelTitle eyebrow="MODEL OUTPUT" title="Chemical-family scores" detail="Higher scores indicate stronger model support; they are not calibrated probabilities."/><div className="ml-family-grid">{prediction.predictions.map((item) => <FamilyScore key={item.chemical_family} item={item}/>)}</div></div>{prediction.spectrum?.length > 0 && <div className="ml-panel"><PanelTitle eyebrow="SIGNAL / UPLOADED SAMPLE" title="Input spectrum" detail="Abundance against mass-to-charge ratio"/><SpectrumChart points={prediction.spectrum}/></div>}</div>}
          </div>
        </section>}

        {tab === 'archive' && <section className="ml-workspace-page"><div className="ml-section-hero"><div><span className="ml-section-index">03 / NASA SAM DATASET</span><h2>Experiment<br/><em>archive.</em></h2></div><p>Browse the local collection of Sample Analysis at Mars QMS experiments. Open any record to see its source spectrum, statistical position and extracted descriptors.</p></div><div className="ml-toolbar"><div className="ml-search"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search experiment ID, filename, feature…"/></div><select value={clusterFilter} onChange={(event) => setClusterFilter(event.target.value)} aria-label="Filter by cluster"><option value="all">All clusters</option>{clusters.map((item) => <option value={String(item.cluster)} key={item.cluster}>Cluster {item.cluster}</option>)}</select><span className="ml-toolbar-count">{filteredExperiments.length} RECORDS</span></div><div className="ml-table-wrap"><table className="ml-table"><thead><tr><th>Experiment</th><th>Cluster</th><th>Status</th><th>Peak AMU</th><th>Mean counts</th><th>Source file</th><th></th></tr></thead><tbody>{filteredExperiments.map((item) => <tr key={item.experiment_id}><td><strong className="ml-table-id">{item.experiment_id}</strong><small>NASA SAM / QMS</small></td><td><ClusterTag cluster={item.cluster}/></td><td><StatusTag anomaly={isAnomaly(item)}/></td><td>{fmt(item.peak_amu)}</td><td>{fmt(item.mean_counts)}</td><td className="ml-file-cell">{item.filename || '—'}</td><td><button className="ml-row-action" onClick={() => setSelected(item)}>Inspect ↗</button></td></tr>)}</tbody></table>{filteredExperiments.length === 0 && <div className="ml-empty">No experiment records match this search.</div>}</div><p className="ml-table-foot">Showing {filteredExperiments.length} of {experiments.length} experiment records · Original QMS measurements are loaded on demand.</p></section>}

        {tab === 'map' && <section className="ml-workspace-page"><div className="ml-section-hero"><div><span className="ml-section-index">04 / UNSUPERVISED ANALYSIS</span><h2>Map the<br/><em>structure.</em></h2></div><p>Principal Component Analysis projects engineered experiment features into a lower-dimensional view. Colour indicates K-Means cluster; the outlined markers flag Isolation Forest outliers.</p></div><div className="ml-map-layout"><div className="ml-panel ml-pca-panel"><PanelTitle eyebrow="PCA PROJECTION" title="Experiment similarity map" detail={`${pcaPoints.length} observations · PC1 + PC2`} /><PCAChart points={pcaPoints} onSelect={(id) => { const match = experiments.find((item) => String(item.experiment_id) === String(id)); if (match) setSelected(match); }}/><div className="ml-chart-legend">{clusters.map((item, index) => <span key={item.cluster}><i style={{ background: CLUSTER_COLORS[index % CLUSTER_COLORS.length] }}/>Cluster {item.cluster}</span>)}<span><i className="ml-legend-ring"/>Outlier</span></div></div><div className="ml-side-analysis"><div className="ml-panel"><PanelTitle eyebrow="MODEL / PCA" title="Variance retained"/><div className="ml-big-number">{fmt(overview?.pca_explained_variance)}<small>%</small></div><p className="ml-small-muted">Explained by {fmt(overview?.pca_components, 0)} retained principal components.</p><div className="ml-progress"><span style={{ width: `${Math.max(0, Math.min(100, overview?.pca_explained_variance || 0))}%` }}/></div></div><div className="ml-panel"><PanelTitle eyebrow="K-MEANS" title="Cluster breakdown"/><ClusterBars clusters={clusters}/></div></div></div><div className="ml-method-note"><b>HOW TO READ THIS VIEW</b><span>Nearby points have more similar engineered features in the PCA projection. This is a statistical view, not a geographic map or chemical identification.</span></div></section>}

        {tab === 'anomalies' && <section className="ml-workspace-page"><div className="ml-section-hero"><div><span className="ml-section-index">05 / ISOLATION FOREST</span><h2>Outlier<br/><em>watch.</em></h2></div><p>Review experiments flagged as statistically unusual by the Isolation Forest model. These observations warrant inspection; unusual scores do not imply unusual chemistry.</p></div><div className="ml-alert-summary"><div className="ml-alert-symbol">!</div><div><span>FLAGGED OBSERVATIONS</span><strong>{anomalies.length} <small>of {experiments.length} experiments</small></strong></div><div className="ml-alert-rate">{experiments.length ? (anomalies.length / experiments.length * 100).toFixed(1) : '0.0'}% of dataset</div></div><div className="ml-table-wrap"><table className="ml-table"><thead><tr><th>Experiment</th><th>Cluster</th><th>Anomaly score</th><th>Peak AMU</th><th>Mean counts</th><th></th></tr></thead><tbody>{anomalies.map((item) => <tr key={item.experiment_id}><td><strong className="ml-table-id">{item.experiment_id}</strong><small>Flagged by Isolation Forest</small></td><td><ClusterTag cluster={item.cluster}/></td><td className="ml-score">{fmt(item.anomaly_score, 6)}</td><td>{fmt(item.peak_amu)}</td><td>{fmt(item.mean_counts)}</td><td><button className="ml-row-action" onClick={() => setSelected(item)}>Inspect ↗</button></td></tr>)}</tbody></table>{anomalies.length === 0 && <div className="ml-empty">No anomaly records are currently available.</div>}</div><div className="ml-method-note"><b>SCIENTIFIC CAUTION</b><span>Anomaly detection is an unsupervised statistical screen. It does not establish the cause of an outlier or provide evidence of biosignatures, life or habitability.</span></div></section>}

        <footer className="ml-footer"><span>MARS LAB <b>·</b> PLANETARY SAMPLE SPECTROMETRY ANALYSIS</span><span>NASA MSL / SAM DATA <b>·</b> RESEARCH PROTOTYPE</span></footer>
      </div>

      {selected && <div className="ml-drawer-backdrop" onMouseDown={() => setSelected(null)}><aside className="ml-drawer" role="dialog" aria-modal="true" aria-label={`Experiment ${selected.experiment_id} details`} onMouseDown={(event) => event.stopPropagation()}><div className="ml-drawer-head"><div><span className="ml-section-index">NASA SAM / QMS RECORD</span><h2>Experiment <em>{selected.experiment_id}</em></h2><p>Source measurement · partially processed Level 1A</p></div><button className="ml-drawer-close" onClick={() => setSelected(null)} aria-label="Close details">×</button></div><div className="ml-drawer-stats"><div><span>CLUSTER</span><strong>{selected.cluster ?? '—'}</strong></div><div><span>STATUS</span><strong className={isAnomaly(selected) ? 'text-orange' : 'text-green'}>{isAnomaly(selected) ? 'Outlier' : 'Normal'}</strong></div><div><span>ANOMALY SCORE</span><strong>{fmt(selected.anomaly_score, 5)}</strong></div><div><span>RECORDS</span><strong>{fmt(selected.records, 0)}</strong></div></div>
        <section className="ml-drawer-section"><PanelTitle eyebrow="DIMENSION REDUCTION" title="PCA position"/><div className="ml-pca-readout">{selectedPca ? <><div><span>PC 01</span><strong>{fmt(selectedPca.pc1, 6)}</strong></div><div><span>PC 02</span><strong>{fmt(selectedPca.pc2, 6)}</strong></div><div><span>CLUSTER</span><strong>{selectedPca.cluster}</strong></div></> : <p>Coordinates are not available for this experiment.</p>}</div></section>
        <section className="ml-drawer-section"><div className="ml-drawer-spectrum-head"><PanelTitle eyebrow="ORIGINAL MEASUREMENT" title="QMS mass spectrum" detail="AMU against counts per second"/>{selectedSpectrum && <span className="ml-record-total">{selectedSpectrum.total_measurements.toLocaleString()} points</span>}</div>{spectrumLoading ? <div className="ml-chart-loading"><span className="ml-spinner"/>Loading source spectrum…</div> : spectrumError ? <div className="ml-inline-error">{spectrumError}</div> : selectedSpectrum?.points?.length ? <><QmsChart points={selectedSpectrum.points}/><p className="ml-source-file">SOURCE FILE / {selectedSpectrum.filename}</p></> : <p className="ml-small-muted">No original QMS spectrum is available for this record.</p>}</section>
        <section className="ml-drawer-section"><PanelTitle eyebrow="FEATURE ENGINEERING" title="Extracted numerical features"/><div className="ml-feature-grid">{selectedFeatures.length ? selectedFeatures.map(([key, value]) => <div key={key}><span>{label(key)}</span><strong>{fmt(value, 6)}</strong></div>) : <p>No numerical feature values are available.</p>}</div></section>
        <section className="ml-drawer-section"><PanelTitle eyebrow="SOURCE METADATA" title="Experiment metadata"/><div className="ml-metadata-list">{Object.entries(selected).filter(([key, value]) => typeof value !== 'number' && key !== 'anomaly' && key !== 'anomaly_status').map(([key, value]) => <div key={key}><span>{label(key)}</span><strong>{String(value ?? '—')}</strong></div>)}</div></section>
        <div className="ml-science-note"><strong>INTERPRETATION NOTE</strong><p>This chart displays associated, partially processed SAM QMS measurements. Cluster and anomaly labels describe statistical patterns only; they are not confirmed chemical identifications or evidence of life or habitability.</p></div></aside></div>}
    </main>
  );
}

function Metric({ label: title, value, note, accent }: { label: string; value: string; note: string; accent: string }) {
  return <div className={`ml-metric accent-${accent}`}><span>{title}</span><strong>{value}</strong><small>{note}</small><i/></div>;
}
function PanelTitle({ eyebrow, title, detail }: { eyebrow: string; title: string; detail?: string }) {
  return <div className="ml-panel-title"><span>{eyebrow}</span><h3>{title}</h3>{detail && <p>{detail}</p>}</div>;
}
function ClusterTag({ cluster }: { cluster?: number }) {
  const color = cluster == null ? '#9a9a91' : CLUSTER_COLORS[Math.abs(cluster) % CLUSTER_COLORS.length];
  return <span className="ml-cluster-tag"><i style={{ background: color }}/>{cluster == null ? 'Unassigned' : `Cluster ${cluster}`}</span>;
}
function StatusTag({ anomaly }: { anomaly: boolean }) { return <span className={`ml-status-tag ${anomaly ? 'flagged' : 'clear'}`}>{anomaly ? 'Flagged outlier' : 'Within range'}</span>; }
function ExperimentList({ items, onSelect, compact = false }: { items: Experiment[]; onSelect: (item: Experiment) => void; compact?: boolean }) {
  return <div className={`ml-experiment-list ${compact ? 'compact' : ''}`}>{items.length ? items.map((item) => <button key={item.experiment_id} onClick={() => onSelect(item)} className="ml-experiment-row"><span className="ml-record-glyph">⌁</span><span className="ml-record-name"><strong>Experiment {item.experiment_id}</strong><small>{item.filename || 'NASA SAM QMS measurement'}</small></span><ClusterTag cluster={item.cluster}/><span className="ml-row-arrow">↗</span></button>) : <p className="ml-empty">No experiment records loaded.</p>}</div>;
}
function ClusterBars({ clusters }: { clusters: Cluster[] }) {
  return <div className="ml-cluster-bars">{clusters.map((item, index) => <div className="ml-cluster-bar-row" key={item.cluster}><div className="ml-cluster-bar-label"><span><i style={{ background: CLUSTER_COLORS[index % CLUSTER_COLORS.length] }}/>Cluster {item.cluster}</span><b>{item.experiment_count}<small> / {item.percentage}%</small></b></div><div className="ml-bar-track"><span style={{ width: `${Math.max(0, Math.min(100, item.percentage))}%`, background: CLUSTER_COLORS[index % CLUSTER_COLORS.length] }}/></div></div>)}{!clusters.length && <p className="ml-empty">Cluster summary is not available.</p>}</div>;
}
function FamilyScore({ item }: { item: ChemicalPrediction }) {
  const score = Math.max(0, Math.min(1, Number(item.score) || 0)); const detected = Number(item.prediction) === 1;
  return <div className={`ml-family-card ${detected ? 'detected' : ''}`}><div className="ml-family-top"><strong>{label(item.chemical_family)}</strong><span>{detected ? 'DETECTED' : 'NOT DETECTED'}</span></div><div className="ml-family-score"><b>{score.toFixed(3)}</b><small>MODEL SCORE</small></div><div className="ml-family-track"><i style={{ width: `${score * 100}%` }}/></div></div>;
}
function QmsChart({ points }: { points: QmsPoint[] }) {
  const width = 900, height = 250, pad = 48;
  const valid = points.filter((p) => Number.isFinite(p.amu) && Number.isFinite(p.counts_per_second) && p.counts_per_second >= 0);
  if (!valid.length) return <p className="ml-empty">No valid spectrum points to display.</p>;
  const minX = Math.min(...valid.map((p) => p.amu)), maxX = Math.max(...valid.map((p) => p.amu));
  const maxY = Math.max(...valid.map((p) => p.counts_per_second), 1), range = maxX - minX || 1;
  return <div className="ml-svg-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="QMS mass spectrum, counts per second against AMU">{[0,1,2,3,4].map((n) => { const y = pad + n * (height - 2*pad) / 4; return <g key={n}><line x1={pad} y1={y} x2={width-pad} y2={y} className="ml-grid-line"/><text x={pad-10} y={y+4} textAnchor="end" className="ml-svg-tick">{fmt(maxY * (4-n) / 4, 0)}</text></g>; })}{valid.map((p, i) => { const x = pad + (p.amu-minX)/range*(width-2*pad), y = height-pad-(p.counts_per_second/maxY)*(height-2*pad); return <line key={`${p.amu}-${i}`} x1={x} x2={x} y1={height-pad} y2={y} className="ml-qms-stem"><title>{`AMU ${p.amu} · ${p.counts_per_second} counts/sec`}</title></line>; })}<line x1={pad} y1={height-pad} x2={width-pad} y2={height-pad} className="ml-axis-line"/><text x={width/2} y={height-8} textAnchor="middle" className="ml-svg-label">AMU / MASS-TO-CHARGE RATIO</text><text x={14} y={height/2} textAnchor="middle" className="ml-svg-label" transform={`rotate(-90 14 ${height/2})`}>COUNTS / SEC</text></svg></div>;
}
function SpectrumChart({ points }: { points: SpectrumPoint[] }) {
  const sorted = [...points].filter((p) => Number.isFinite(Number(p['m/z'])) && Number.isFinite(Number(p.abundance))).sort((a,b) => Number(a['m/z'])-Number(b['m/z']));
  if (!sorted.length) return <p className="ml-empty">No spectrum data to display.</p>;
  const count = Math.min(1000, sorted.length), sampled: SpectrumPoint[] = [];
  for (let i=0;i<count;i++) { const start=Math.floor(i*sorted.length/count), end=Math.floor((i+1)*sorted.length/count); const chunk=sorted.slice(start,Math.max(start+1,end)); if (chunk.length) sampled.push(chunk.reduce((a,b)=>Number(a.abundance)>Number(b.abundance)?a:b)); }
  const width=900,height=250,pad=46,minX=Math.min(...sampled.map(p=>Number(p['m/z']))),maxX=Math.max(...sampled.map(p=>Number(p['m/z']))),maxY=Math.max(...sampled.map(p=>Number(p.abundance)),1e-15),range=maxX-minX||1;
  return <div className="ml-svg-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Uploaded spectrum, abundance against m/z">{[0,1,2,3,4].map(n=>{const y=pad+n*(height-2*pad)/4;return <line key={n} x1={pad} y1={y} x2={width-pad} y2={y} className="ml-grid-line"/>;})}{sampled.map((p,i)=>{const x=pad+(Number(p['m/z'])-minX)/range*(width-2*pad),y=height-pad-(Number(p.abundance)/maxY)*(height-2*pad);return <line key={i} x1={x} x2={x} y1={height-pad} y2={y} className="ml-spectrum-stem"><title>{`m/z ${p['m/z']} · abundance ${p.abundance}`}</title></line>;})}<line x1={pad} y1={height-pad} x2={width-pad} y2={height-pad} className="ml-axis-line"/><text x={width/2} y={height-8} textAnchor="middle" className="ml-svg-label">MASS-TO-CHARGE RATIO (M/Z)</text></svg></div>;
}
function PCAChart({ points, onSelect }: { points: PCAPoint[]; onSelect: (id: string) => void }) {
  const width=900,height=510,pad=55;
  if (!points.length) return <div className="ml-empty">PCA coordinates are not available.</div>;
  const xs=points.map(p=>p.pc1),ys=points.map(p=>p.pc2),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys),rangeX=maxX-minX||1,rangeY=maxY-minY||1;
  return <div className="ml-pca-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="PCA scatter plot of SAM experiments">{[0,1,2,3,4].map(n=><g key={n}><line x1={pad+n*(width-2*pad)/4} y1={pad} x2={pad+n*(width-2*pad)/4} y2={height-pad} className="ml-grid-line"/><line x1={pad} y1={pad+n*(height-2*pad)/4} x2={width-pad} y2={pad+n*(height-2*pad)/4} className="ml-grid-line"/></g>)}{points.map((point,i)=>{const x=pad+(point.pc1-minX)/rangeX*(width-2*pad),y=height-pad-(point.pc2-minY)/rangeY*(height-2*pad),color=CLUSTER_COLORS[Math.abs(point.cluster)%CLUSTER_COLORS.length];return <circle key={`${point.experiment_id}-${i}`} cx={x} cy={y} r={point.anomaly?7:5} fill={color} stroke={point.anomaly?'#e45e39':'#fffdf8'} strokeWidth={point.anomaly?3:1.2} className="ml-pca-point" onClick={()=>onSelect(String(point.experiment_id))} tabIndex={0} role="button" onKeyDown={(event)=>{if(event.key==='Enter'||event.key===' ')onSelect(String(point.experiment_id));}}><title>{`Experiment ${point.experiment_id} · Cluster ${point.cluster}${point.anomaly?' · Outlier':''}`}</title></circle>;})}<line x1={pad} y1={height-pad} x2={width-pad} y2={height-pad} className="ml-axis-line"/><line x1={pad} y1={pad} x2={pad} y2={height-pad} className="ml-axis-line"/><text x={width/2} y={height-10} textAnchor="middle" className="ml-svg-label">PRINCIPAL COMPONENT 1</text><text x={15} y={height/2} textAnchor="middle" className="ml-svg-label" transform={`rotate(-90 15 ${height/2})`}>PRINCIPAL COMPONENT 2</text></svg><p className="ml-chart-hint">Select any point to open the corresponding experiment.</p></div>;
}
