import React, { useState, useEffect } from 'react';
import { StitchHeader } from './components/stitch/StitchHeader';
import { StitchFooter } from './components/stitch/StitchFooter';
import { SpatialHeroTheaterView } from './components/stitch/SpatialHeroTheaterView';
import { IncidentCommandCenterView } from './components/stitch/IncidentCommandCenterView';
import { SpatialMemoryExplorerView } from './components/stitch/SpatialMemoryExplorerView';
import { ProvenanceTraceAuditView } from './components/stitch/ProvenanceTraceAuditView';

export type StitchView =
  | 'spatial-hero-memory-theater'
  | 'incident-command-center'
  | 'spatial-memory-explorer'
  | 'provenance-trace-audit';

const pathToView = (path: string): StitchView => {
  if (path === '/command-center') return 'incident-command-center';
  if (path === '/memory') return 'spatial-memory-explorer';
  if (path === '/incident' || path === '/audit' || path === '/trace-audit') return 'provenance-trace-audit';
  return 'spatial-hero-memory-theater';
};

const viewToPath = (view: StitchView): string => {
  switch (view) {
    case 'incident-command-center':
      return '/command-center';
    case 'spatial-memory-explorer':
      return '/memory';
    case 'provenance-trace-audit':
      return '/incident';
    default:
      return '/';
  }
};

export default function App() {
  const [currentView, setCurrentView] = useState<StitchView>(() => {
    if (typeof window !== 'undefined') {
      return pathToView(window.location.pathname);
    }
    return 'spatial-hero-memory-theater';
  });

  const [activeScenarioId, setActiveScenarioId] = useState<string>('INC-104');
  const [runbookStatus, setRunbookStatus] = useState<'IDLE' | 'EXECUTING' | 'EXECUTED'>('IDLE');
  const [retentionStatus, setRetentionStatus] = useState<'UNCOMMITTED' | 'COMMITTING' | 'RETAINED'>('UNCOMMITTED');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Sync browser popstate
  useEffect(() => {
    const handlePopState = () => {
      setCurrentView(pathToView(window.location.pathname));
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateTo = (view: StitchView | string) => {
    const validView = view as StitchView;
    setCurrentView(validView);
    const targetPath = viewToPath(validView);
    if (typeof window !== 'undefined' && window.location.pathname !== targetPath) {
      window.history.pushState(null, '', targetPath);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleSelectScenario = (id: string) => {
    setActiveScenarioId(id);
    setRunbookStatus('IDLE');
    setRetentionStatus('UNCOMMITTED');
    showToast(`Scenario switched to ${id}`);
  };

  // Real backend connection: dry-run only. Production-changing execution is never simulated as successful.
  const handleExecuteRunbook = async () => {
    setRunbookStatus('EXECUTING');

    const runbookId =
      activeScenarioId === 'INC-108'
        ? 'RB-REDIS-TLS-ROTATE'
        : activeScenarioId === 'INC-112'
          ? 'RB-K8S-SCALE-LIMITS'
          : 'RB-PGBOUNCER-120';

    try {
      const response = await fetch(`/api/runbooks/${runbookId}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ executor: 'oncall-sre' }),
      });

      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const payload = await response.json();
          detail = payload?.detail ?? detail;
        } catch {
          // Keep the HTTP status when the response is not JSON.
        }
        setRunbookStatus('IDLE');
        showToast(`Runbook simulation blocked: ${detail}`);
        return;
      }

      setRunbookStatus('EXECUTED');
      showToast('Approved runbook dry-run simulation completed successfully.');
    } catch {
      setRunbookStatus('IDLE');
      showToast('Runbook simulation unavailable. No remediation was executed.');
    }
  };

  // Real Backend connection: Commit Retention / Postmortem
  const handleCommitRetention = async () => {
    setRetentionStatus('COMMITTING');

    const runbookId =
      activeScenarioId === 'INC-108'
        ? 'RB-REDIS-TLS-ROTATE'
        : activeScenarioId === 'INC-112'
          ? 'RB-K8S-SCALE-LIMITS'
          : 'RB-PGBOUNCER-120';

    const rootCause =
      activeScenarioId === 'INC-108'
        ? 'Redis TLS Root CA Expiry'
        : activeScenarioId === 'INC-112'
          ? 'Inventory worker memory exhaustion'
          : 'PgBouncer Max Client Exhaustion';

    const payload = {
      incident_id: activeScenarioId,
      title: `Incident Resolution Precedent - ${activeScenarioId}`,
      service: activeScenarioId === 'INC-108' ? 'auth-service' : activeScenarioId === 'INC-112' ? 'inventory-worker' : 'payment-gateway',
      severity: 'HIGH',
      root_cause: rootCause,
      trigger: 'Incident response scenario selected in the command center.',
      impact_summary: 'Operational impact captured by the incident response workflow.',
      timeline: [{ time: 'T+0m', event: 'Incident response scenario reviewed by SRE.' }],
      resolution_steps: [`Reviewed and validated ${runbookId} as the incident runbook.`],
      runbook_executed: runbookId,
      preventative_actions: ['Retain verified incident outcome for future Hindsight recall.'],
      tags: ['incidentops', 'verified-postmortem'],
      source_incident_id: activeScenarioId,
    };

    try {
      const response = await fetch('/api/postmortems/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const responseBody = await response.json();
          detail = responseBody?.detail ?? detail;
        } catch {
          // Keep the HTTP status when the response is not JSON.
        }
        setRetentionStatus('UNCOMMITTED');
        showToast(`Postmortem commit blocked: ${detail}`);
        return;
      }

      setRetentionStatus('RETAINED');
      showToast('Human-verified postmortem committed to Hindsight memory.');
    } catch {
      setRetentionStatus('UNCOMMITTED');
      showToast('Postmortem retention unavailable. Nothing was marked as retained.');
    }
  };

  return (
    <div className="bg-[#020408] text-on-surface font-body-md text-body-md antialiased min-h-screen flex flex-col justify-between selection:bg-primary selection:text-on-primary">
      {/* Google Stitch persistent header */}
      <StitchHeader
        currentView={currentView}
        onNavigate={(v) => navigateTo(v as StitchView)}
        onAction={showToast}
      />

      {/* Main content */}
      <main className="w-full pt-16 bg-[#020408] flex-1 pb-14">
        {currentView === 'spatial-hero-memory-theater' && (
          <SpatialHeroTheaterView onNavigate={(v) => navigateTo(v as StitchView)} />
        )}

        {currentView === 'incident-command-center' && (
          <IncidentCommandCenterView
            activeScenarioId={activeScenarioId}
            onSelectScenario={handleSelectScenario}
            runbookStatus={runbookStatus}
            onExecuteRunbook={handleExecuteRunbook}
            retentionStatus={retentionStatus}
            onCommitRetention={handleCommitRetention}
            toastMessage={toastMessage}
          />
        )}

        {currentView === 'spatial-memory-explorer' && (
          <SpatialMemoryExplorerView />
        )}

        {currentView === 'provenance-trace-audit' && (
          <ProvenanceTraceAuditView />
        )}
      </main>

      {/* Persistent footer */}
      <StitchFooter />
    </div>
  );
}
