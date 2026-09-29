import React from 'react';

interface StitchHeaderProps {
  currentView: string;
  onNavigate: (view: string) => void;
  onAction: (message: string) => void;
}

export const StitchHeader: React.FC<StitchHeaderProps> = ({ currentView, onNavigate, onAction }) => {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#020408]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.4)] border-b border-white/5"><div className="h-16 w-full px-margin flex items-center justify-between gap-space-md"><div className="flex items-center gap-space-md shrink-0"><img alt="IncidentOps Kernel Logo" className="h-8 w-auto object-contain" src="https://lh3.googleusercontent.com/aida/AEtjO1Un_C3cspdHTcV6UNLPDBfyrHvCpv84mB6Zvi8CEyX0v5Kq9SdtoMICcm7ajssEJc3AhvhbKJPPPZ1WhdujY70Xhu5_xvO5yzJL-0dNH2VSKdWXAdFw0FmdNYs4rUZHsFK6xANwD-MRtaI9sqfehuOdabjP79NKxYxuNNGyPej72wIqARtvkS3DGms6pQHnxTsywGA_90q_2X_CdgL_GiSWnTJkYKwgK0RxzVdKlXVHMWjP6XXa20Gc2p0"/><div className="flex flex-col"><span className="font-headline-sm text-headline-sm uppercase tracking-wider text-on-surface flex items-center gap-space-xs">IncidentOps Copilot <span className="font-label-sm text-label-sm px-space-xs py-0.5 bg-surface-container-high text-secondary">v2.4.0</span></span><span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">SRE Continuous Memory Agent</span></div><div className="hidden xl:flex items-center gap-space-sm pl-space-md"><div className="px-space-sm py-1 bg-surface-container-lowest font-label-sm text-label-sm text-tertiary flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>AIRGAP ENCLAVE: SEALED (ED25519)</div><div className="px-space-sm py-1 bg-surface-container-lowest font-label-sm text-label-sm text-on-surface-variant">CLUSTER: <span className="text-on-surface font-bold">us-east-prod</span></div><div className="px-space-sm py-1 bg-surface-container-lowest font-label-sm text-label-sm text-secondary">LATENCY: <span className="font-bold">142ms</span></div></div></div><nav className="hidden lg:flex items-center gap-space-xs bg-surface-container-lowest p-1">
          <button
            type="button"
            onClick={() => onNavigate('spatial-hero-memory-theater')}
            className={`px-space-sm py-1.5 font-label-md text-label-md uppercase tracking-wider transition-colors ${
              currentView === 'spatial-hero-memory-theater'
                ? 'bg-surface-container-high text-on-surface font-bold'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
          >
            Spatial Hero / Memory Theater
          </button>
          <button
            type="button"
            onClick={() => onNavigate('incident-command-center')}
            className={`px-space-sm py-1.5 font-label-md text-label-md uppercase tracking-wider transition-colors ${
              currentView === 'incident-command-center'
                ? 'bg-surface-container-high text-on-surface font-bold'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
          >
            Incident Command Center
          </button>
          <button
            type="button"
            onClick={() => onNavigate('spatial-memory-explorer')}
            className={`px-space-sm py-1.5 font-label-md text-label-md uppercase tracking-wider transition-colors ${
              currentView === 'spatial-memory-explorer'
                ? 'bg-surface-container-high text-on-surface font-bold'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
          >
            Spatial Memory Explorer
          </button>
          <button
            type="button"
            onClick={() => onNavigate('provenance-trace-audit')}
            className={`px-space-sm py-1.5 font-label-md text-label-md uppercase tracking-wider transition-colors ${
              currentView === 'provenance-trace-audit'
                ? 'bg-surface-container-high text-on-surface font-bold'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
          >
            Provenance Trace &amp; Audit
          </button>
        </nav><div className="flex items-center gap-space-sm shrink-0"><button className="hidden sm:inline-flex items-center px-space-sm py-1.5 bg-surface-container font-label-sm text-label-sm uppercase tracking-wider text-on-surface hover:bg-surface-container-high hover:text-on-surface transition-colors" type="button" onClick={() => onAction("Runbook catalog synchronized with git:main (ED25519 verified)")}>Runbook Sync</button><button className="hidden sm:inline-flex items-center px-space-sm py-1.5 bg-surface-container font-label-sm text-label-sm uppercase tracking-wider text-secondary hover:bg-surface-container-high hover:text-on-surface transition-colors" type="button" onClick={() => onAction("Hindsight 1536-D Vector Ingest Stream active: 4,819,204 records")}>Vector Ingest</button><button className="inline-flex items-center px-space-sm py-1.5 bg-error-container text-on-error-container font-label-sm text-label-sm uppercase tracking-widest hover:bg-primary-container hover:text-on-primary-container transition-colors" type="button" onClick={() => onAction("Airgap Enclave sealed: Killswitch primed. Autonomous execution locked.")}>Emergency Killswitch</button><div className="relative flex items-center ml-space-xs"><img alt="Profile" className="w-8 h-8 rounded-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBubtdFwGZly5wMx2iBS0emHklivEJfTPYcPOYz1DxMamNCd5xVZDS_Hq5_R9k6FVD1fga7I9Qw-bHAJ0YnrXwDFl9zUNArJMvXnZSVeDpurvZiLHHnVzvcDKWDpJuwfRtvxpKfuJaRdgOxJ-Z4y5tze9nhda0Wdsgy0aRAHzkQLB5P8oCd_Wm-IQTQSWKHmvdn39xja7kK8urKXiZe5-cvB8CvrbrcXcZzIzIv5nSAmkls9xiW4ur7ig"/><span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-tertiary ring-2 ring-[#020408] animate-ping"></span><span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-tertiary ring-2 ring-[#020408]"></span></div></div></div></header>
  );
};
