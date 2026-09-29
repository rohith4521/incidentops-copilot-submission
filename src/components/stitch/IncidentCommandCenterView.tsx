import React from 'react';

interface IncidentCommandCenterViewProps {
  activeScenarioId: string;
  onSelectScenario: (id: string) => void;
  runbookStatus: 'IDLE' | 'EXECUTING' | 'EXECUTED';
  onExecuteRunbook: () => void;
  retentionStatus: 'UNCOMMITTED' | 'COMMITTING' | 'RETAINED';
  onCommitRetention: () => void;
  toastMessage?: string | null;
}

export const IncidentCommandCenterView: React.FC<IncidentCommandCenterViewProps> = ({
  activeScenarioId,
  onSelectScenario,
  runbookStatus,
  onExecuteRunbook,
  retentionStatus,
  onCommitRetention,
  toastMessage
}) => {
  const scenarioRunbook = activeScenarioId === 'INC-108' 
    ? 'RB-REDIS-TLS-ROTATE' 
    : activeScenarioId === 'INC-112' 
    ? 'RB-K8S-SCALE-LIMITS' 
    : 'RB-PGBOUNCER-120';

  return (
    <div className="relative">
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 px-4 py-2 bg-secondary text-on-secondary font-mono text-xs font-bold shadow-2xl flex items-center gap-2 border border-white/20">
          <span className="material-symbols-outlined text-base">info</span>
          <span>{toastMessage}</span>
        </div>
      )}
<main className="w-full pt-16 bg-[#020408] flex-1 pb-10"><div className="flex flex-col w-full">
<div className="w-full px-margin py-space-md grid grid-cols-1 xl:grid-cols-12 gap-gutter items-start">
{/*  LEFT COLUMN: Telemetry & Ingestion (Cols 1-3.5)  */}
<div className="xl:col-span-4 flex flex-col gap-space-md min-w-0">
{/*  P1 Alert Module  */}
<div className="relative bg-surface-container-lowest p-space-md shadow-xl overflow-hidden">
<div className="absolute top-0 left-0 w-1 h-full bg-primary-container"></div>
<div className="flex items-center justify-between gap-space-sm mb-space-sm">
<div className="flex items-center gap-space-xs">
<span className="inline-flex w-2.5 h-2.5 rounded-full bg-primary-container animate-ping"></span>
<span className="inline-flex w-2 h-2 rounded-full bg-primary-container -ml-3.5"></span>
<span className="font-label-lg text-label-lg uppercase tracking-wider text-primary">CRITICAL P1 ALERT</span>
</div>
<span className="px-space-xs py-0.5 bg-surface-container-high text-on-surface-variant font-label-sm text-label-sm">SEV-1 ACTIVE (04m 18s)</span>
</div>
<div className="font-headline-sm text-headline-sm text-on-surface font-bold tracking-tight break-all mb-1">
          payments.prod.cluster-us-east
        </div>
<div className="font-body-sm text-body-sm text-on-surface-variant flex items-center gap-space-xs mb-space-md">
<span className="material-symbols-outlined text-sm text-primary">error</span>
<span>HTTP 504 Gateway Timeout | Ingress Envoy proxy saturation</span>
</div>
{/*  Telemetry Metrics Split  */}
<div className="grid grid-cols-2 gap-space-sm">
<div className="bg-surface-container-low p-space-sm">
<div className="font-label-sm text-label-sm text-on-surface-variant uppercase">PgBouncer Active Pool</div>
<div className="flex items-baseline gap-space-xs my-0.5">
<span className="font-headline-lg text-headline-lg text-primary font-bold">120</span>
<span className="font-label-md text-label-md text-on-surface-variant">/ 120 (100%)</span>
</div>
<div className="w-full bg-surface-container-highest h-1.5 overflow-hidden">
<div className="bg-primary-container h-full w-full"></div>
</div>
</div>
<div className="bg-surface-container-low p-space-sm">
<div className="font-label-sm text-label-sm text-on-surface-variant uppercase">P99 Latency Spike</div>
<div className="flex items-baseline gap-space-xs my-0.5">
<span className="font-headline-lg text-headline-lg text-primary font-bold">842</span>
<span className="font-label-md text-label-md text-primary-fixed-dim">ms</span>
</div>
<div className="font-label-sm text-label-sm text-primary flex items-center gap-0.5">
<span className="material-symbols-outlined text-xs">north</span> +310% baseline drift
            </div>
</div>
</div>
</div>
{/*  Historical Scenario Selector  */}
<div className="bg-surface-container-lowest p-space-md shadow-md">
<div className="flex items-center justify-between mb-space-sm">
<span className="font-label-lg text-label-lg uppercase tracking-wider text-on-surface flex items-center gap-space-xs">
<span className="material-symbols-outlined text-sm text-secondary">alt_route</span>
            SCENARIO RUNBOOK SIMULATOR
          </span>
<span className="font-label-sm text-label-sm text-on-surface-variant">3 DETECTED</span>
</div>
<div className="flex flex-col gap-space-xs">
{/*  Active Scenario  */}
<div onClick={() => onSelectScenario("INC-104")} className={`p-space-sm transition-colors cursor-pointer relative overflow-hidden ${activeScenarioId === "INC-104" ? "bg-surface-container-high ring-1 ring-secondary/50" : "bg-surface-container-low hover:bg-surface-container"}`}>
{activeScenarioId === "INC-104" && <div className="absolute left-0 top-0 bottom-0 w-1 bg-secondary-fixed"></div>}
<div className="absolute left-0 top-0 bottom-0 w-1 bg-secondary-fixed"></div>
<div className="flex items-center justify-between pl-space-xs">
<span className="font-label-md text-label-md text-secondary font-bold">INC-104: PgBouncer Saturation</span>
<span className="px-space-xs py-0.5 bg-secondary/10 text-secondary font-label-sm text-label-sm uppercase">SELECTED</span>
</div>
<div className="font-body-sm text-body-sm text-on-surface-variant pl-space-xs mt-0.5">
              DB client worker pool exhaustion via unreleased connections
            </div>
</div>
{/*  Inactive Scenario 1  */}
<div onClick={() => onSelectScenario("INC-108")} className={`p-space-sm transition-colors cursor-pointer relative overflow-hidden ${activeScenarioId === "INC-108" ? "bg-surface-container-high ring-1 ring-secondary/50" : "bg-surface-container-low hover:bg-surface-container"}`}>
{activeScenarioId === "INC-108" && <div className="absolute left-0 top-0 bottom-0 w-1 bg-secondary-fixed"></div>}
<div className="flex items-center justify-between">
<span className="font-label-md text-label-md text-on-surface">INC-108: Redis TLS Handshake Drift</span>
<span className="font-label-sm text-label-sm text-on-surface-variant">42m ago</span>
</div>
<div className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
              Handshake roundtrip degradation on replica cross-AZ ring
            </div>
</div>
{/*  Inactive Scenario 2  */}
<div onClick={() => onSelectScenario("INC-112")} className={`p-space-sm transition-colors cursor-pointer relative overflow-hidden ${activeScenarioId === "INC-112" ? "bg-surface-container-high ring-1 ring-secondary/50" : "bg-surface-container-low hover:bg-surface-container"}`}>
{activeScenarioId === "INC-112" && <div className="absolute left-0 top-0 bottom-0 w-1 bg-secondary-fixed"></div>}
<div className="flex items-center justify-between">
<span className="font-label-md text-label-md text-on-surface">INC-112: Novel OOMKilled Worker Batch</span>
<span className="font-label-sm text-label-sm text-on-surface-variant">3h ago</span>
</div>
<div className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
              Asynchronous worker pool buffer overflow during batch ingest
            </div>
</div>
</div>
</div>
{/*  Ingest Stream Terminal  */}
<div className="bg-surface-container-lowest p-space-md shadow-md flex flex-col gap-space-sm">
<div className="flex items-center justify-between">
<span className="font-label-lg text-label-lg uppercase tracking-wider text-on-surface flex items-center gap-space-xs">
<span className="material-symbols-outlined text-sm text-on-surface-variant">terminal</span>
            LIVE TELEMETRY INGEST
          </span>
<span className="font-label-sm text-label-sm text-tertiary flex items-center gap-1">
<span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>STREAMING
          </span>
</div>
<div className="bg-surface-container-low p-space-sm mb-space-xs"><div className="flex items-center justify-between mb-2"><span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider flex items-center gap-1"><span className="material-symbols-outlined text-xs text-secondary">hub</span>BLAST RADIUS TOPOLOGY</span><span className="font-label-sm text-label-sm text-primary font-bold">DEGRADATION LOCALIZED</span></div><div className="grid grid-cols-3 gap-2 items-center"><div className="p-1.5 bg-surface-container border border-surface-container-highest flex flex-col gap-0.5 relative"><div className="flex items-center justify-between"><span className="font-label-sm text-label-sm text-on-surface font-bold truncate">Envoy Ingress</span><span className="w-2 h-2 rounded-full bg-tertiary shrink-0 shadow-[0_0_8px_rgba(0,228,121,0.6)]"></span></div><span className="font-label-sm text-label-sm text-tertiary">OK (p99 12ms)</span></div><div className="p-1.5 bg-primary-container/10 border border-primary relative shadow-[0_0_12px_rgba(255,79,115,0.4)] flex flex-col gap-0.5 animate-pulse"><div className="flex items-center justify-between"><span className="font-label-sm text-label-sm text-primary font-bold truncate">PgBouncer Proxy</span><span className="w-2 h-2 rounded-full bg-primary-container shrink-0 ring-2 ring-primary animate-ping"></span></div><span className="font-label-sm text-label-sm text-primary font-bold uppercase">SATURATED 100%</span></div><div className="p-1.5 bg-surface-container border border-surface-container-highest flex flex-col gap-0.5 relative"><div className="flex items-center justify-between"><span className="font-label-sm text-label-sm text-on-surface font-bold truncate">Aurora DB</span><span className="w-2 h-2 rounded-full bg-tertiary shrink-0 shadow-[0_0_8px_rgba(0,228,121,0.6)]"></span></div><span className="font-label-sm text-label-sm text-tertiary">OK (CPU 24%)</span></div></div></div><div className="bg-surface-dim p-space-sm font-body-sm text-body-sm space-y-1.5 overflow-hidden text-on-surface">
<div className="text-on-surface-variant flex items-center justify-between">
<span>[14:22:04.102Z] envoy.ingress.timeout</span>
<span className="text-primary font-bold">504_GATEWAY_TIMEOUT</span>
</div>
<div className="text-primary-fixed-dim pl-2 font-mono">
            &gt; db_pool.go:184: pgx: pool timed out waiting for free connection (exceeded 5000ms threshold)
          </div>
<div className="text-on-surface-variant pl-2">
            metrics::prometheus: pgbouncer_pools_client_waiting{"{db=\"payments\"}"} = 284
          </div>
<div className="text-secondary pl-2">
            hindsight_agent::ingest: 1,536-D vector formulated (hash: d7a19c..)
          </div>
<div className="text-primary pl-2 font-bold animate-pulse">
            CRITICAL_ALARM: max_client_conn reached on listener socket 0.0.0.0:6432
          </div>
</div>
{/*  Inline Sparkline Telemetry Visual  */}
<div className="bg-surface-container-low p-space-sm">
<div className="flex items-center justify-between mb-1">
<span className="font-label-sm text-label-sm text-on-surface-variant uppercase">Connection Queue Velocity</span>
<span className="font-label-sm text-label-sm text-primary">+88 conn/sec</span>
</div>
<svg className="w-full h-12 text-primary" fill="none" preserveAspectRatio="none" viewBox="0 0 300 48">
<path d="M0 40 L30 38 L60 39 L90 35 L120 36 L150 28 L180 26 L210 20 L240 14 L270 6 L300 2" stroke="currentColor" strokeLinecap="square" strokeWidth="2"  />
<path d="M0 40 L30 38 L60 39 L90 35 L120 36 L150 28 L180 26 L210 20 L240 14 L270 6 L300 2 L300 48 L0 48 Z" fill="currentColor" fillOpacity="0.12"  />
</svg>
</div>
</div>
</div>
{/*  CENTER COLUMN: Continuous Memory Pipeline (Cols 4-8.5)  */}
<div className="xl:col-span-5 flex flex-col gap-space-md min-w-0">
{/*  Core Doctrine Banner  */}
<div className="bg-surface-container-lowest p-space-md shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm">
<div className="flex flex-col">
<span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">CONTINUOUS REASONING DOCTRINE</span>
<div className="font-headline-sm text-headline-sm font-bold text-on-surface mt-0.5 tracking-wide flex items-center gap-space-xs">
<span className="text-secondary font-bold">RETRIEVED</span>
<span className="text-outline">≠</span>
<span className="text-primary font-bold">RELEVANT</span>
<span className="text-outline">≠</span>
<span className="text-tertiary font-bold">TRUSTED</span>
</div>
</div>
<div className="px-space-sm py-1 bg-surface-container text-tertiary font-label-sm text-label-sm uppercase tracking-wider self-start sm:self-auto flex items-center gap-1.5">
<span className="material-symbols-outlined text-xs">verified</span>
          ATTRIBUTED PROVENANCE ACTIVE
        </div>
</div>
{/*  4-Stage Visual Execution Pipeline  */}
<div className="bg-surface-container-lowest p-space-md shadow-xl flex flex-col gap-space-md"><div className="flex items-center justify-between"><span className="font-label-lg text-label-lg uppercase tracking-wider text-on-surface flex items-center gap-space-xs"><span className="material-symbols-outlined text-sm text-secondary">device_hub</span>4-STAGE MEMORY PIPELINE EXECUTION</span><span className="font-label-sm text-label-sm text-on-surface-variant">PASS: 4/4 REFINED</span></div><div className="relative flex flex-col gap-space-md pl-6"><div className="absolute left-2.5 top-5 bottom-6 w-0.5 bg-gradient-to-b from-secondary-container via-primary-container to-tertiary shadow-[0_0_8px_rgba(0,238,252,0.3)]"></div>{/*  STAGE 1: Hindsight Recall  */}<div className="relative bg-surface-container-low p-space-md overflow-hidden"><div className="absolute -left-[1.85rem] top-4 w-4 h-4 rounded-full bg-surface-container-lowest border-2 border-secondary-container flex items-center justify-center shadow-[0_0_10px_rgba(0,238,252,0.8)]"><span className="w-1.5 h-1.5 rounded-full bg-secondary-container animate-ping"></span></div><div className="flex items-center justify-between mb-space-sm"><div className="flex items-center gap-space-sm"><span className="px-space-xs py-0.5 bg-surface-container-highest text-secondary font-label-sm text-label-sm font-bold">STAGE 01</span><span className="font-headline-sm text-headline-sm text-on-surface font-semibold">Hindsight High-D Recall</span></div><span className="font-label-sm text-label-sm text-on-surface-variant">Top-k=2 [1536-D]</span></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-space-sm"><div className="bg-surface-container p-space-sm"><div className="flex items-center justify-between mb-1"><span className="font-label-md text-label-md text-on-surface font-bold">Candidate INC-042</span><span className="font-label-sm text-label-sm text-secondary font-bold">COS: 0.994</span></div><p className="font-body-sm text-body-sm text-on-surface-variant">PgBouncer conn starvation under burst ingress load during Flash Sale.</p></div><div className="bg-surface-container p-space-sm"><div className="flex items-center justify-between mb-1"><span className="font-label-md text-label-md text-on-surface font-bold">Candidate INC-071</span><span className="font-label-sm text-label-sm text-secondary font-bold">COS: 0.981</span></div><p className="font-body-sm text-body-sm text-on-surface-variant">Payment gateway 504 timeouts due to external Stripe API webhook lock.</p></div></div></div>{/*  STAGE 2: Relevance Gate  */}<div className="relative bg-surface-container-low p-space-md"><div className="absolute -left-[1.85rem] top-4 w-4 h-4 rounded-full bg-surface-container-lowest border-2 border-primary-container flex items-center justify-center shadow-[0_0_10px_rgba(255,79,115,0.8)]"><span className="material-symbols-outlined text-[10px] text-primary-container font-bold">shield</span></div><div className="flex items-center justify-between mb-space-sm"><div className="flex items-center gap-space-sm"><span className="px-space-xs py-0.5 bg-surface-container-highest text-primary font-label-sm text-label-sm font-bold">STAGE 02</span><span className="font-headline-sm text-headline-sm text-on-surface font-semibold">Causal Relevance Gate</span></div><span className="font-label-sm text-label-sm text-primary font-bold">1 DECOY SUPPRESSED</span></div><div className="bg-surface-container p-space-sm relative"><div className="flex items-center justify-between text-on-surface-variant"><span className="line-through font-label-md text-label-md text-primary font-bold">Candidate INC-071 (Cosine 0.981)</span><span className="px-space-xs py-0.5 bg-primary-container text-on-primary-container font-label-sm text-label-sm uppercase font-bold tracking-wider">SUPPRESSED</span></div><div className="my-space-sm p-space-xs bg-surface-container-lowest border border-outline-variant flex flex-col gap-1.5"><div className="flex items-center justify-between font-label-sm text-label-sm"><span className="text-on-surface-variant">Semantic Overlap</span><span className="text-primary-fixed-dim font-bold">0.901 (Superficial Match)</span></div><div className="w-full bg-surface-container-highest h-2"><div className="bg-outline h-full" style={{ width: '90.1%' }}></div></div><div className="flex items-center justify-between font-label-sm text-label-sm mt-0.5"><span className="text-on-surface-variant">Causal Grounding</span><span className="text-primary font-bold">0.082 (Root Cause Mismatch)</span></div><div className="w-full bg-surface-container-highest h-2"><div className="bg-primary-container h-full" style={{ width: '8.2%' }}></div></div></div><div className="font-body-sm text-body-sm text-on-surface mt-1 pl-space-xs border-l-2 border-primary"><div className="inline-block px-1 py-0.5 bg-error-container text-on-error-container font-label-sm text-label-sm font-bold uppercase mb-1 tracking-wider">FALSE-GROUNDING BLOCKED // RELEVANCE GATE ACTIVE</div><div><span className="text-primary font-bold">ROOT CAUSE MISMATCH:</span> External Provider API webhook latency vs. current internal socket descriptor exhaustion on unix sockets. Semantic similarity was superficial.</div></div></div></div>{/*  STAGE 3: Promoted Trusted Evidence  */}<div className="relative bg-surface-container-low p-space-md"><div className="absolute -left-[1.85rem] top-4 w-4 h-4 rounded-full bg-surface-container-lowest border-2 border-tertiary flex items-center justify-center shadow-[0_0_10px_rgba(0,228,121,0.8)]"><span className="material-symbols-outlined text-[10px] text-tertiary font-bold">verified</span></div><div className="flex items-center justify-between mb-space-sm"><div className="flex items-center gap-space-sm"><span className="px-space-xs py-0.5 bg-surface-container-highest text-tertiary font-label-sm text-label-sm font-bold">STAGE 03</span><span className="font-headline-sm text-headline-sm text-on-surface font-semibold">Promoted Trusted Evidence</span></div><span className="font-label-sm text-label-sm text-tertiary font-bold">99.82% ATTRIBUTED</span></div><div className="bg-surface-container p-space-sm"><div className="flex items-center justify-between mb-1"><div className="flex items-center gap-space-xs"><span className="material-symbols-outlined text-tertiary text-sm">verified_user</span><span className="font-label-md text-label-md text-tertiary font-bold">INC-042 [VERIFIED POSTMORTEM PROVENANCE]</span></div><span className="font-label-sm text-label-sm text-on-surface-variant">HASH: #e82b7c4</span></div><div className="font-body-sm text-body-sm text-on-surface">Validated resolution from 2024-Q3: Increasing PgBouncer client pool size from 120 to 450 alongside transaction pooling eliminated queuing with zero host memory regressions.</div></div></div>{/*  STAGE 4: AI Diagnosis & Runbook Recommendation  */}<div className="relative bg-surface-container-high p-space-md"><div className="absolute -left-[1.85rem] top-4 w-4 h-4 rounded-full bg-surface-container-lowest border-2 border-secondary flex items-center justify-center shadow-[0_0_10px_rgba(211,251,255,0.8)]"><span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span></div><div className="flex items-center justify-between mb-space-sm"><div className="flex items-center gap-space-sm"><span className="px-space-xs py-0.5 bg-surface-container text-secondary font-label-sm text-label-sm font-bold">STAGE 04</span><span className="font-headline-sm text-headline-sm text-on-surface font-semibold">Synthesized Runbook Action</span></div><span className="px-space-xs py-0.5 bg-secondary-container text-on-secondary-container font-label-sm text-label-sm font-bold">RB-PGBOUNCER-POOL-120</span></div><div className="font-body-sm text-body-sm text-on-surface-variant mb-space-sm">Parameter execution diff generated against <span className="text-on-surface font-bold">payments-db-proxy-daemonset</span>:</div>{/*  GitOps Code Diff Terminal  */}<div className="bg-[#020408] border border-surface-container-highest overflow-hidden font-mono text-body-sm"><div className="bg-surface-container-lowest px-space-sm py-1 border-b border-surface-container-highest flex items-center justify-between"><div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-primary-container/80"></span><span className="w-2 h-2 rounded-full bg-secondary-container/80"></span><span className="w-2 h-2 rounded-full bg-tertiary/80"></span><span className="ml-2 font-label-sm text-label-sm text-on-surface-variant font-body-sm">payments-db-proxy-daemonset.yaml (GitOps Diff)</span></div><span className="font-label-sm text-label-sm text-tertiary uppercase">SYNTHESIZED</span></div><div className="p-space-sm space-y-0.5 leading-relaxed"><div className="text-on-surface-variant/70">@@ -14,6 +14,6 @@ spec.template.spec.containers[0].env</div><div className="text-primary bg-primary-container/10 px-1 -mx-1 flex items-center"><span className="w-4 text-primary select-none">-</span><span>max_client_conn: 120</span></div><div className="text-tertiary bg-tertiary/10 px-1 -mx-1 flex items-center font-bold"><span className="w-4 text-tertiary select-none">+</span><span>max_client_conn: 450</span></div><div className="text-primary bg-primary-container/10 px-1 -mx-1 flex items-center"><span className="w-4 text-primary select-none">-</span><span>default_pool_size: 40</span></div><div className="text-tertiary bg-tertiary/10 px-1 -mx-1 flex items-center font-bold"><span className="w-4 text-tertiary select-none">+</span><span>default_pool_size: 80</span></div><div className="text-primary bg-primary-container/10 px-1 -mx-1 flex items-center"><span className="w-4 text-primary select-none">-</span><span>pool_mode: session</span></div><div className="text-secondary bg-secondary/10 px-1 -mx-1 flex items-center font-bold"><span className="w-4 text-secondary select-none">+</span><span>pool_mode: transaction</span></div></div></div></div></div></div>
</div>
{/*  RIGHT COLUMN: Action, Approval & Continuous Learning (Cols 9-12)  */}
<div className="xl:col-span-3 flex flex-col gap-space-md min-w-0">
{/*  Dual-Key Operator Approval Panel  */}
<div className="bg-surface-container-lowest p-space-md shadow-xl flex flex-col gap-space-md">
<div className="flex items-center justify-between">
<span className="font-label-lg text-label-lg uppercase tracking-wider text-on-surface flex items-center gap-space-xs">
<span className="material-symbols-outlined text-sm text-tertiary">lock_open</span>
            DUAL-KEY AIRGAP APPROVAL
          </span>
<span className="font-label-sm text-label-sm text-tertiary">SEALED</span>
</div>
<div className="bg-surface-container-low p-space-sm space-y-2">
<div className="flex items-center justify-between">
<span className="font-label-sm text-label-sm text-on-surface-variant">SESSION SECURITY ROLE</span>
<span className="font-label-sm text-label-sm text-on-surface font-bold">EXEC_RUNBOOK_APPROVED</span>
</div>
<div className="flex items-center justify-between">
<span className="font-label-sm text-label-sm text-on-surface-variant">ENCLAVE SIGNATURE</span>
<span className="font-label-sm text-label-sm text-secondary font-mono">0x9a88..f32d</span>
</div>
<div className="flex items-center justify-between">
<span className="font-label-sm text-label-sm text-on-surface-variant">AIRGAP INTEGRITY</span>
<span className="font-label-sm text-label-sm text-tertiary">ED25519 VALIDATED</span>
</div>
</div>
{/*  High-Impact Call to Action Execution Button  */}
<button
          onClick={onExecuteRunbook}
          disabled={runbookStatus !== 'IDLE'}
          className={`w-full py-space-sm px-space-md font-label-lg text-label-lg uppercase tracking-wider transition-all flex items-center justify-center gap-space-xs cursor-pointer ${
            runbookStatus === 'EXECUTED'
              ? 'bg-tertiary-container text-on-tertiary shadow-[0_0_20px_rgba(0,228,121,0.5)]'
              : runbookStatus === 'EXECUTING'
              ? 'bg-secondary-container text-on-secondary-container animate-pulse'
              : 'bg-tertiary text-on-tertiary hover:bg-tertiary-fixed shadow-[0_0_20px_rgba(0,228,121,0.35)]'
          }`}
          id="approve-btn"
          type="button"
        >
          {runbookStatus === 'EXECUTING' ? (
            <>
              <span className="material-symbols-outlined text-base animate-spin">refresh</span>
              <span>EXECUTING {scenarioRunbook}...</span>
            </>
          ) : runbookStatus === 'EXECUTED' ? (
            <>
              <span className="material-symbols-outlined text-base">verified</span>
              <span>RUNBOOK EXECUTED ({scenarioRunbook})</span>
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-base">play_arrow</span>
              <span>APPROVE RUNBOOK EXECUTION</span>
            </>
          )}
        </button>
<div className="hidden p-space-sm bg-tertiary/10 text-tertiary font-label-sm text-label-sm text-center" id="exec-status">
          DISPATCHING TO CLUSTER AIRGAP ENCLAVE...
        </div>
</div>
{/*  Continuous Retention Engine  */}
<div className="bg-surface-container-lowest p-space-md shadow-md flex flex-col gap-space-md">
<div className="flex items-center justify-between">
<span className="font-label-lg text-label-lg uppercase tracking-wider text-on-surface flex items-center gap-space-xs">
<span className="material-symbols-outlined text-sm text-secondary">neurology</span>
            CONTINUOUS RETENTION
          </span>
<span className="font-label-sm text-label-sm text-secondary">AUTO-SYNCHRONIZED</span>
</div>
<div className="font-body-sm text-body-sm text-on-surface-variant">
          Post-resolution vector retention preserves the validated causal graph, preventing recursive incidents and updating the 1536-D geometric index.
        </div>
<div className="bg-surface-container-low p-space-sm space-y-1">
<div className="flex items-center justify-between font-label-sm text-label-sm">
<span className="text-on-surface-variant">POSTMORTEM PIPELINE</span>
<span className="text-tertiary">STAGED</span>
</div>
<div className="flex items-center justify-between font-label-sm text-label-sm">
<span className="text-on-surface-variant">VECTOR CACHE PREVIEW</span>
<span className="text-on-surface font-mono">hash:c72b..091a</span>
</div>
<div className="flex items-center justify-between font-label-sm text-label-sm">
<span className="text-on-surface-variant">CONFIDENCE INTERVAL</span>
<span className="text-secondary">99.98%</span>
</div>
</div>
<button
          onClick={onCommitRetention}
          disabled={retentionStatus !== 'UNCOMMITTED' || runbookStatus !== 'EXECUTED'}
          className={`w-full py-space-sm px-space-md font-label-md text-label-md uppercase tracking-wider transition-colors flex items-center justify-center gap-space-xs cursor-pointer ${
            retentionStatus === 'RETAINED'
              ? 'bg-secondary text-on-secondary font-bold shadow-[0_0_15px_rgba(0,219,233,0.4)]'
              : retentionStatus === 'COMMITTING'
              ? 'bg-secondary-container text-on-secondary-container animate-pulse'
              : runbookStatus === 'EXECUTED'
              ? 'bg-surface-container text-secondary hover:bg-surface-container-high hover:text-on-surface'
              : 'bg-surface-container-lowest text-outline-variant cursor-not-allowed opacity-50'
          }`}
          type="button"
        >
          {retentionStatus === 'COMMITTING' ? (
            <>
              <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
              <span>SEALING HINDSIGHT POSTMORTEM...</span>
            </>
          ) : retentionStatus === 'RETAINED' ? (
            <>
              <span className="material-symbols-outlined text-sm">lock</span>
              <span>POSTMORTEM SEALED (SHA-256)</span>
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-sm">memory</span>
              <span>COMMIT TO CONTINUOUS MEMORY</span>
            </>
          )}
        </button>
</div>
{/*  Operator Audit Trail Stream  */}
<div className="bg-surface-container-lowest p-space-md shadow-md flex flex-col gap-space-sm">
<div className="flex items-center justify-between">
<span className="font-label-lg text-label-lg uppercase tracking-wider text-on-surface flex items-center gap-space-xs">
<span className="material-symbols-outlined text-sm text-on-surface-variant">history</span>
            OPERATOR AUDIT LOG
          </span>
<span className="font-label-sm text-label-sm text-on-surface-variant">IMMUTABLE</span>
</div>
<div className="space-y-space-xs font-body-sm text-body-sm text-on-surface-variant">
<div className="p-space-xs bg-surface-container-low">
<div className="flex items-center justify-between text-on-surface">
<span className="font-bold">sre.lead@corp</span>
<span className="font-label-sm text-label-sm text-on-surface-variant">14:22:15</span>
</div>
<div className="text-tertiary">Verified causal relevance of INC-042</div>
</div>
<div className="p-space-xs bg-surface-container-low">
<div className="flex items-center justify-between text-on-surface">
<span className="font-bold">system.agent</span>
<span className="font-label-sm text-label-sm text-on-surface-variant">14:21:50</span>
</div>
<div className="text-primary-fixed-dim">Suppressed decoy INC-071 via semantic gate</div>
</div>
<div className="p-space-xs bg-surface-container-low">
<div className="flex items-center justify-between text-on-surface">
<span className="font-bold">security.kernel</span>
<span className="font-label-sm text-label-sm text-on-surface-variant">14:19:02</span>
</div>
<div className="text-secondary">Enclave attestation signature sealed: OK</div>
</div>
</div>
</div>
</div>
</div>
{/*  Interactive script for approval toggle  */}

</div></main>
    </div>
  );
};
