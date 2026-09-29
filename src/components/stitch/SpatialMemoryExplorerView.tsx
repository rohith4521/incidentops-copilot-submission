import React, { useState } from 'react';

interface NodeDetails {
  id: string;
  type: string;
  title: string;
  hash: string;
  frequency: string;
  recallRate: string;
  blastRadius: string;
  embedding: string;
  runbook: string;
  mttd: string;
  status: string;
}

export const SpatialMemoryExplorerView: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<NodeDetails>({
    id: 'INC-104',
    type: 'VERIFIED INCIDENT',
    title: 'PostgreSQL Socket Saturation & Thread Starvation',
    hash: 'mem_sha256_88190c',
    frequency: '4 Times',
    recallRate: '100%',
    blastRadius: '7 Blocked',
    embedding: '1536-D (Norm: 1.000)',
    runbook: 'RB-PGBOUNCER-POOL-120',
    mttd: '4m 12s',
    status: 'ACTIVE'
  });

  const [zoom, setZoom] = useState<number>(100);
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isProjection3D, setIsProjection3D] = useState<boolean>(true);
  const [isPhysicsActive, setIsPhysicsActive] = useState<boolean>(true);

  const selectNode = (
    id: string,
    type: string,
    title: string,
    hash: string,
    frequency: string,
    recallRate: string,
    blastRadius: string,
    embedding: string,
    runbook: string,
    mttd: string,
    status: string
  ) => {
    setSelectedNode({ id, type, title, hash, frequency, recallRate, blastRadius, embedding, runbook, mttd, status });
  };

  const adjustZoom = (delta: number) => {
    setZoom(prev => Math.max(50, Math.min(200, prev + delta)));
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const toggleProjection = () => {
    setIsProjection3D(prev => !prev);
    showToast(!isProjection3D ? 'Projection switched to 3D Manifold' : 'Projection switched to 2D Orthographic');
  };

  const togglePhysics = () => {
    setIsPhysicsActive(prev => !prev);
    showToast(!isPhysicsActive ? 'RK4 Spring Integrator: RUNNING' : 'RK4 Spring Integrator: PAUSED');
  };

  return (
    <div className="relative">
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 px-4 py-2 bg-secondary text-on-secondary font-mono text-xs font-bold shadow-2xl flex items-center gap-2 border border-white/20">
          <span className="material-symbols-outlined text-base">info</span>
          <span>{toastMessage}</span>
        </div>
      )}
<main className="w-full pt-16 bg-[#020408] flex-1 pb-10"><div className="flex flex-col w-full text-on-surface select-none">
{/*  Sub-header HUD Coordinate Banner  */}
<div className="w-full bg-surface-container-lowest/80 px-margin py-space-xs flex flex-wrap items-center justify-between text-on-surface-variant font-label-sm text-label-sm tracking-wider">
<div className="flex items-center gap-space-md">
<div className="flex items-center gap-space-xs text-secondary">
<span className="material-symbols-outlined text-sm animate-spin">cyclone</span>
<span>TOPOLOGICAL EMBEDDING ENGINE: RK4-T-SNE</span>
</div>
<span className="text-surface-variant">/</span>
<span className="text-tertiary">EPSILON: 0.0418</span>
<span className="text-surface-variant">/</span>
<span>PERPLEXITY: 34.0</span>
<span className="text-surface-variant">/</span>
<span>MANIFOLD: 1536-D → ℝ³</span>
</div>
<div className="flex items-center gap-space-md font-mono">
<span>GRID: [X: -412.00 Y: +189.54 Z: +882.11]</span>
<span className="px-1.5 py-0.5 bg-primary/20 text-primary uppercase font-bold tracking-widest text-[8px]">PROJECTION ACTIVE</span>
</div>
</div>
{/*  Primary Canvas Stage & Floating HUD Panels  */}
<div className="relative w-full h-[calc(100vh-8.5rem)] overflow-hidden bg-[#020408]">
{/*  Ambient Coordinate Matrix Overlay (Synthetic SVG Grid & Reticles)  */}
<svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20" xmlns="http://www.w3.org/2000/svg">
<defs>
<pattern height="80" id="reticle-grid" patternUnits="userSpaceOnUse" width="80">
<path d="M 80 0 L 0 0 0 80" fill="none" stroke="#7df4ff" strokeDasharray="2,6" strokeWidth="0.5"  />
<circle cx="80" cy="80" fill="#00eefc" opacity="0.4" r="1.5"  />
<path d="M 40 36 L 40 44 M 36 40 L 44 40" opacity="0.3" stroke="#ffb2ba" strokeWidth="0.5"  />
</pattern>
{/*  Gradients for Catenary Tension Cords  */}
<linearGradient id="cord-emerald" x1="0%" x2="100%" y1="0%" y2="100%">
<stop offset="0%" stopColor="#00e479" stopOpacity="0.8"  />
<stop offset="100%" stopColor="#00eefc" stopOpacity="0.2"  />
</linearGradient>
<linearGradient id="cord-alert" x1="0%" x2="100%" y1="0%" y2="100%">
<stop offset="0%" stopColor="#ff4f73" stopOpacity="0.7"  />
<stop offset="100%" stopColor="#ffb4ab" stopOpacity="0.1"  />
</linearGradient>
</defs>
<rect fill="url(#reticle-grid)" height="100%" width="100%"  />
</svg>
{/*  Top Left Canvas Status & Cluster Diagnostics  */}
<div className="absolute top-space-md left-space-md z-20 flex flex-col gap-space-xs pointer-events-auto">
<div className="bg-surface-container-lowest/90 px-space-md py-space-sm backdrop-blur-md shadow-2xl flex flex-col">
<div className="flex items-center justify-between gap-space-md mb-1">
<span className="font-headline-sm text-headline-sm text-secondary uppercase tracking-tight flex items-center gap-1.5">
<span className="w-2 h-2 bg-secondary animate-ping"></span>
            Substrate Graph v2.4
          </span>
<span className="font-label-sm text-label-sm text-on-surface-variant bg-surface-container px-1.5 py-0.5">MANIFOLD//LIVE</span>
</div>
<div className="font-label-sm text-label-sm text-on-surface-variant flex flex-col gap-0.5">
<span>GRAPH DENSITY: <span className="text-tertiary">0.842 COHESION</span></span>
<span>STOCHASTIC DRIFT: <span className="text-on-surface">±0.003 σ</span></span>
<span>CLUSTER ENTROPY: <span className="text-primary">SEV-1 UNSTABLE</span></span>
</div>
</div>
{/*  Quick Legend HUD Micro-strip  */}
<div className="bg-surface-container-lowest/70 backdrop-blur-sm px-space-sm py-1 flex items-center gap-space-md font-label-sm text-[9px] uppercase tracking-wider text-on-surface-variant">
<span className="flex items-center gap-1 text-tertiary"><span className="w-2 h-2 bg-tertiary rotate-45 inline-block"></span> Verified</span>
<span className="flex items-center gap-1 text-secondary"><span className="w-2 h-2 bg-secondary inline-block"></span> Root Cause</span>
<span className="flex items-center gap-1 text-secondary-fixed"><span className="w-2 h-2 rounded-full bg-secondary-fixed inline-block"></span> Runbook</span>
<span className="flex items-center gap-1 text-primary"><span className="w-2 h-2 bg-primary-container inline-block"></span> Decoy</span>
<span className="flex items-center gap-1 text-[#ffb2ba]"><span className="w-2 h-2 bg-[#ffb2ba] rotate-45 inline-block animate-pulse"></span> Novel</span>
</div>
</div>
{/*  Central Interactive Vector Topological Viewport (SVG + DOM hybrid nodes)  */}
<div className="absolute inset-0 w-full h-full cursor-crosshair overflow-hidden" id="viewport-stage">
{/*  Catenary / Spring Tension Lines  */}
<svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg"><style>{`@keyframes dashTravel{0%{stroke-dashoffset:48;}100%{stroke-dashoffset:0;}}@keyframes stressPulse{0%,100%{opacity:0.9;filter:drop-shadow(0 0 2px rgba(255,79,115,0.8));}50%{opacity:0.4;filter:drop-shadow(0 0 8px rgba(255,79,115,1));}}@keyframes packetMotion1{0%{cx:42%;cy:38%;r:3;opacity:1;}100%{cx:38%;cy:52%;r:1.5;opacity:0.2;}}@keyframes packetMotion2{0%{cx:42%;cy:38%;r:3;opacity:1;}100%{cx:52%;cy:44%;r:1.5;opacity:0.2;}}@keyframes packetMotion3{0%{cx:42%;cy:38%;r:3;opacity:1;}100%{cx:35%;cy:28%;r:1.5;opacity:0.2;}}`}</style><defs><pattern height="80" id="reticle-grid" patternUnits="userSpaceOnUse" width="80"><path d="M 80 0 L 0 0 0 80" fill="none" stroke="#7df4ff" strokeDasharray="2,6" strokeWidth="0.5"  /><circle cx="80" cy="80" fill="#00eefc" opacity="0.4" r="1.5"  /><path d="M 40 36 L 40 44 M 36 40 L 44 40" opacity="0.3" stroke="#ffb2ba" strokeWidth="0.5"  /></pattern><linearGradient id="cord-emerald" x1="0%" x2="100%" y1="0%" y2="100%"><stop offset="0%" stopColor="#00e479" stopOpacity="0.9"  /><stop offset="100%" stopColor="#00eefc" stopOpacity="0.3"  /></linearGradient><linearGradient id="cord-alert" x1="0%" x2="100%" y1="0%" y2="100%"><stop offset="0%" stopColor="#ff4f73" stopOpacity="0.9"  /><stop offset="100%" stopColor="#ffb4ab" stopOpacity="0.2"  /></linearGradient><linearGradient id="contour-glow" x1="0%" x2="100%" y1="0%" y2="100%"><stop offset="0%" stopColor="#00eefc" stopOpacity="0.4"  /><stop offset="100%" stopColor="#00e479" stopOpacity="0.1"  /></linearGradient></defs><g opacity="0.25"><ellipse cx="38%" cy="38%" rx="260" ry="170" stroke="#00eefc" strokeDasharray="4,8" strokeWidth="1"  /><ellipse cx="38%" cy="38%" rx="200" ry="130" stroke="#00eefc" strokeDasharray="8,6" strokeWidth="1.2"  /><ellipse cx="38%" cy="38%" rx="140" ry="90" stroke="#00e479" strokeDasharray="3,5" strokeWidth="1.5"  /><ellipse cx="30%" cy="74%" rx="190" ry="120" stroke="#00eefc" strokeDasharray="4,8" strokeWidth="1"  /><ellipse cx="30%" cy="74%" rx="140" ry="85" stroke="#00e479" strokeDasharray="8,6" strokeWidth="1.2"  /><ellipse cx="30%" cy="74%" rx="90" ry="55" stroke="#00e479" strokeDasharray="3,5" strokeWidth="1.4"  /><ellipse cx="74%" cy="62%" rx="170" ry="115" stroke="#00e479" strokeDasharray="6,6" strokeWidth="1"  /></g><g strokeLinecap="round"><line stroke="url(#cord-emerald)" strokeDasharray="3,3" strokeWidth="1.5" x1="28%" x2="35%" y1="36%" y2="28%"  /><line stroke="url(#cord-emerald)" strokeWidth="2" x1="35%" x2="42%" y1="28%" y2="38%"  /><line stroke="url(#cord-emerald)" strokeWidth="1" x1="28%" x2="42%" y1="36%" y2="38%"  /><line stroke="#00eefc" strokeWidth="2" x1="42%" x2="52%" y1="38%" y2="44%"  /><line stroke="#7df4ff" strokeDasharray="6,6" strokeWidth="1.5" style={{ animation: 'dashTravel 1.5s linear infinite' }} x1="42%" x2="52%" y1="38%" y2="44%"  /><line stroke="url(#cord-emerald)" strokeWidth="2" x1="42%" x2="38%" y1="38%" y2="52%"  /><line stroke="#00e479" strokeDasharray="8,4" strokeWidth="2" style={{ animation: 'dashTravel 1.2s linear infinite' }} x1="42%" x2="38%" y1="38%" y2="52%"  /><line stroke="#7df4ff" strokeDasharray="1,4" strokeWidth="1" x1="35%" x2="26%" y1="28%" y2="22%"  /><line stroke="#00eefc" strokeWidth="1.5" x1="52%" x2="62%" y1="44%" y2="32%"  /><circle fill="#00e479" style={{ animation: 'packetMotion1 1.6s ease-in-out infinite' }}  /><circle fill="#7df4ff" style={{ animation: 'packetMotion2 2.1s ease-in-out infinite' }}  /><circle fill="#60ff99" style={{ animation: 'packetMotion3 1.8s ease-in-out infinite' }}  /><path d="M 42% 38% Q 44% 30%, 46% 29% T 48% 20%" fill="none" stroke="#ff4f73" strokeDasharray="4,5" strokeWidth="1.8" style={{ animation: 'stressPulse 1.8s ease-in-out infinite' }}  /><path d="M 42% 38% L 45% 34% L 47% 35% L 50% 28% L 52% 30% L 55% 24% L 58% 18%" fill="none" stroke="#ff4f73" strokeDasharray="3,3" strokeWidth="2.5" style={{ animation: 'stressPulse 1s ease-in-out infinite' }}  /><line stroke="#ff4f73" strokeDasharray="2,5" strokeWidth="1" x1="35%" x2="48%" y1="28%" y2="20%"  /><line stroke="#ff4f73" strokeDasharray="4,3" strokeWidth="2" x1="48%" x2="58%" y1="20%" y2="18%"  /><line stroke="#00e479" strokeWidth="1.5" x1="68%" x2="74%" y1="62%" y2="52%"  /><line stroke="#00eefc" strokeWidth="1.5" x1="74%" x2="82%" y1="52%" y2="58%"  /><line stroke="#00e479" strokeWidth="1" x1="68%" x2="82%" y1="62%" y2="58%"  /><line stroke="#7df4ff" strokeWidth="1.2" x1="82%" x2="78%" y1="58%" y2="72%"  /><line stroke="#00eefc" strokeDasharray="3,3" strokeWidth="1" x1="68%" x2="60%" y1="62%" y2="70%"  /><line stroke="#00e479" strokeWidth="1.5" x1="22%" x2="30%" y1="68%" y2="76%"  /><line stroke="#00eefc" strokeWidth="1.5" x1="30%" x2="38%" y1="76%" y2="70%"  /><line stroke="#7df4ff" strokeWidth="1" x1="22%" x2="38%" y1="68%" y2="70%"  /><line stroke="url(#cord-alert)" strokeDasharray="2,3" strokeWidth="1" x1="38%" x2="44%" y1="70%" y2="82%"  /><line opacity="0.4" stroke="#7df4ff" strokeDasharray="2,8" strokeWidth="0.75" x1="52%" x2="68%" y1="44%" y2="62%"  /><line opacity="0.3" stroke="#00eefc" strokeDasharray="4,6" strokeWidth="0.75" x1="42%" x2="38%" y1="38%" y2="70%"  /></g></svg>
{/*  Zone Monospaced Structural Labels in Field  */}
<div className="absolute top-[16%] left-[23%] text-secondary/50 font-label-sm text-[9px] tracking-widest pointer-events-none flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-secondary-fixed/40 rounded-full"></span>Z-PLANE: -12.4nm</div><div className="absolute top-[77%] left-[17%] text-tertiary/50 font-label-sm text-[9px] tracking-widest pointer-events-none flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-tertiary/40 rounded-full"></span>CURVATURE TENSOR: κ = 0.842</div><div className="absolute top-[24%] left-[51%] -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none whitespace-nowrap bg-surface-container-lowest/90 border border-primary/40 px-1.5 py-0.5 font-label-sm text-[8px] text-primary flex items-center gap-1 shadow-lg"><span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-ping"></span>[TOPOLOGICAL STRESS: 84.2%]</div><div className="absolute top-[21%] left-[27%] text-on-surface-variant/40 font-label-sm text-[10px] tracking-[0.25em] pointer-events-none uppercase">
        // REGION: [DATABASE POOL CLUSTERING]
      </div>
<div className="absolute top-[48%] left-[71%] text-on-surface-variant/40 font-label-sm text-[10px] tracking-[0.25em] pointer-events-none uppercase">
        // REGION: [NETWORK MESH SATURATION]
      </div>
<div className="absolute top-[82%] left-[23%] text-on-surface-variant/40 font-label-sm text-[10px] tracking-[0.25em] pointer-events-none uppercase">
        // REGION: [MEMORY EXHAUSTION ZONE]
      </div>
{/*  32 TOPOLOGICAL NODES (Accurately Clustered & Interactive)  */}
{/*  ==================== CLUSTER 1: DB POOL EXHAUSTION (Core Focus) ====================  */}
{/*  Node: INC-104 (PRIMARY TARGET / HIGHLIGHTED)  */}
<div className="group absolute top-[38%] left-[42%] -translate-x-1/2 -translate-y-1/2 z-30 cursor-pointer transition-transform duration-200 hover:scale-110" onClick={() => selectNode('INC-104', 'VERIFIED INCIDENT', 'PostgreSQL Socket Saturation &amp; Thread Starvation', 'mem_sha256_88190c', '4 Times', '100%', '7 Blocked', '1536-D (Norm: 1.000)', 'RB-PGBOUNCER-POOL-120', '4m 12s', 'ACTIVE')}>
{/*  Coordinate Reticle Rings  */}
<div className="relative flex items-center justify-center">
<div className="absolute -inset-4 bg-tertiary/10 rounded-full animate-ping pointer-events-none"></div>
<div className="absolute -inset-3 bg-secondary/20 rounded-full blur-sm pointer-events-none"></div>
{/*  Hexagonal Visual Element Inspired by Style Icon  */}
<div className="w-14 h-14 bg-surface-container-lowest flex items-center justify-center shadow-xl relative transition-colors duration-200 group-hover:bg-surface-container">
<svg className="w-12 h-12 text-tertiary drop-shadow-[0_0_8px_rgba(0,228,121,0.6)]" fill="none" stroke="currentColor" viewBox="0 0 100 100">
<polygon fill="#0b0e14" points="50,3 93,25 93,75 50,97 7,75 7,25" strokeWidth="4"  />
<circle cx="50" cy="50" r="22" stroke="#00eefc" strokeWidth="3"  />
<polygon fill="#00e479" points="50,34 64,58 36,58"  />
<circle cx="50" cy="50" fill="#7df4ff" r="4"  />
</svg>
</div>
{/*  Reticle Ticks on Target  */}
<div className="absolute -top-1 -left-1 w-2 h-2 border-t-2 border-l-2 border-secondary pointer-events-none"></div>
<div className="absolute -top-1 -right-1 w-2 h-2 border-t-2 border-r-2 border-secondary pointer-events-none"></div>
<div className="absolute -bottom-1 -left-1 w-2 h-2 border-b-2 border-l-2 border-secondary pointer-events-none"></div>
<div className="absolute -bottom-1 -right-1 w-2 h-2 border-b-2 border-r-2 border-secondary pointer-events-none"></div>
{/*  Node Tag Label  */}
<div className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap bg-surface-container-high px-2 py-0.5 text-tertiary font-label-sm text-label-sm font-bold flex items-center gap-1">
<span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
            INC-104 [CORE]
          </div>
</div>
</div>
{/*  Node: INC-042 (Verified Incident Hexagon)  */}
<div className="absolute top-[28%] left-[35%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('INC-042', 'VERIFIED INCIDENT', 'RDS Reader Replica Thread Lock', 'mem_sha256_33b8a1', '12 Times', '98.4%', '14 Blocked', '1536-D (Norm: 0.942)', 'RB-RDS-FAILOVER-V2', '6m 02s', 'NOMINAL')}>
<div className="w-10 h-10 bg-surface-container-lowest flex items-center justify-center relative">
<svg className="w-9 h-9 text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 100 100">
<polygon fill="#101419" points="50,4 92,26 92,74 50,96 8,74 8,26" strokeWidth="5"  />
<polygon fill="#00e479" points="50,38 60,56 40,56"  />
</svg>
<span className="absolute -top-5 left-1/2 -translate-x-1/2 font-label-sm text-[9px] text-tertiary whitespace-nowrap bg-surface-container-lowest/80 px-1">INC-042</span>
</div>
</div>
{/*  Node: INC-088 (Verified Incident Hexagon)  */}
<div className="absolute top-[36%] left-[28%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('INC-088', 'VERIFIED INCIDENT', 'PgBouncer Max Client Exhaustion in us-east-1', 'mem_sha256_711ca9', '8 Times', '100%', '5 Blocked', '1536-D (Norm: 0.918)', 'RB-PGBOUNCER-POOL-120', '3m 44s', 'NOMINAL')}>
<div className="w-10 h-10 bg-surface-container-lowest flex items-center justify-center relative">
<svg className="w-9 h-9 text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 100 100">
<polygon fill="#101419" points="50,4 92,26 92,74 50,96 8,74 8,26" strokeWidth="5"  />
<polygon fill="#00e479" points="50,38 60,56 40,56"  />
</svg>
<span className="absolute -bottom-5 left-1/2 -translate-x-1/2 font-label-sm text-[9px] text-tertiary whitespace-nowrap bg-surface-container-lowest/80 px-1">INC-088</span>
</div>
</div>
{/*  Node: Root Cause - DB Pool (Cyan Square)  */}
<div className="absolute top-[44%] left-[52%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('RC-DB-POOL', 'ROOT CAUSE', 'HikariCP Global Connection Leak in Auth Service', 'mem_sha256_44ef10', '19 Times', '99.1%', '22 Filtered', '1536-D (Norm: 0.991)', 'RB-HIKARI-LEAK-PATCH', '8m 10s', 'RESOLVED')}>
<div className="w-9 h-9 bg-secondary/10 border-2 border-secondary flex items-center justify-center shadow-[0_0_12px_rgba(0,238,252,0.3)]">
<span className="material-symbols-outlined text-secondary text-base">database</span>
</div>
<span className="absolute -top-5 left-1/2 -translate-x-1/2 font-label-sm text-[9px] text-secondary font-bold whitespace-nowrap bg-surface-container-lowest px-1">RC: DB POOL</span>
</div>
{/*  Node: Runbook - RB-PGBOUNCER-120 (Neon Blue Circle)  */}
<div className="absolute top-[52%] left-[38%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('RB-PGBOUNCER-120', 'RUNBOOK ACTION', 'Dynamic Scale &amp; Kill Idle Transactions Script', 'mem_sha256_bb9912', '41 Invocations', '100%', '0 Failures', '1536-D (Deterministic)', 'AUTOMATED_DISPATCH', '1m 20s', 'ACTIVE')}>
<div className="w-8 h-8 rounded-full bg-secondary-fixed/20 border-2 border-secondary-fixed flex items-center justify-center shadow-[0_0_10px_rgba(125,244,255,0.4)]">
<span className="material-symbols-outlined text-secondary-fixed text-sm">play_arrow</span>
</div>
<span className="absolute -bottom-5 left-1/2 -translate-x-1/2 font-label-sm text-[8px] text-secondary-fixed whitespace-nowrap bg-surface-container-lowest px-1">RB-PGBOUNCER-120</span>
</div>
{/*  Node: Runbook Auxiliary  */}
<div className="absolute top-[22%] left-[26%] -translate-x-1/2 -translate-y-1/2 z-10 cursor-pointer group hover:scale-110 transition-transform">
<div className="w-6 h-6 rounded-full bg-surface-container-high border border-secondary-fixed-dim flex items-center justify-center">
<span className="w-1.5 h-1.5 bg-secondary-fixed rounded-full"></span>
</div>
<span className="absolute -top-4 left-1/2 -translate-x-1/2 font-label-sm text-[8px] text-on-surface-variant whitespace-nowrap">RB-POOL-FLUSH</span>
</div>
{/*  Node: Decoy Ghost Cross - INC-071  */}
<div className="absolute top-[20%] left-[48%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('INC-071 [DECOY]', 'DECOY ARTIFACT', 'False Positive: Frontend Client-Side Disconnect Bursts', 'mem_sha256_001fe2', '12 Intercepts', '0% Relevant', '12 Suppressed', '1536-D (Cosine Drift: 0.41)', 'N/A (Filtered Out)', '0s', 'REJECTED')}>
<div className="relative w-8 h-8 flex items-center justify-center bg-surface-container-lowest border border-primary/40">
<span className="material-symbols-outlined text-primary text-base">close</span>
<div className="absolute inset-0 bg-primary/10"></div>
</div>
<span className="absolute -bottom-5 left-1/2 -translate-x-1/2 font-label-sm text-[8px] text-primary whitespace-nowrap line-through bg-surface-container-lowest px-1">DEC-071</span><div className="absolute -top-7 left-1/2 -translate-x-1/2 z-30 whitespace-nowrap bg-surface-container-lowest/95 border border-primary/40 px-1.5 py-0.5 font-label-sm text-[8px] text-primary flex items-center gap-1 pointer-events-none shadow-lg"><span className="material-symbols-outlined text-[10px] text-primary">shield_with_heart</span>BLOCKED BY CAUSAL GATE // 0 FALSE GROUNDING</div>
</div>
{/*  Node: Novel Alert (Amber Pulsing Star: INC-112)  */}
<div className="absolute top-[18%] left-[58%] -translate-x-1/2 -translate-y-1/2 z-30 cursor-pointer group hover:scale-125 transition-transform" onClick={() => selectNode('INC-112 [NOVEL]', 'CRITICAL NOVEL DETECT', 'Zero-Precedent Latency Spike in Vector Indexer', 'mem_sha256_ff0019', '1 (First Instance)', '0% Match', '0 Precedents Found', '1536-D (Singularity: 0.118)', 'UNASSIGNED_INVESTIGATION', 'TBD', 'ACTIVE ALERT')}>
<div className="relative flex items-center justify-center">
<div className="absolute -inset-3 bg-primary-container/30 rounded-full animate-ping"></div>
<div className="w-10 h-10 bg-primary-container flex items-center justify-center shadow-[0_0_20px_rgba(255,79,115,0.7)]">
<span className="material-symbols-outlined text-on-primary-container text-xl animate-spin">emergency</span>
</div>
<div className="absolute -top-6 left-1/2 -translate-x-1/2 font-label-sm text-[9px] font-bold text-on-error-container bg-error-container px-1.5 py-0.5 whitespace-nowrap flex items-center gap-1 shadow-lg">
<span className="w-1.5 h-1.5 bg-primary rounded-full animate-ping"></span>
            INC-112 [NOVEL 0%]
          </div>
</div>
</div>
{/*  ==================== CLUSTER 2: NETWORK MESH SATURATION ====================  */}
{/*  Node: INC-019 (Verified Incident Hexagon)  */}
<div className="absolute top-[62%] left-[68%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('INC-019', 'VERIFIED INCIDENT', 'Envoy Mesh Proxy Conntrack Table Full', 'mem_sha256_199df4', '6 Times', '97.2%', '9 Blocked', '1536-D (Norm: 0.931)', 'RB-ENVOY-CONNTRACK-MAX', '5m 19s', 'NOMINAL')}>
<div className="w-10 h-10 bg-surface-container-lowest flex items-center justify-center relative">
<svg className="w-9 h-9 text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 100 100">
<polygon fill="#101419" points="50,4 92,26 92,74 50,96 8,74 8,26" strokeWidth="5"  />
<polygon fill="#00e479" points="50,38 60,56 40,56"  />
</svg>
<span className="absolute -bottom-5 left-1/2 -translate-x-1/2 font-label-sm text-[9px] text-tertiary whitespace-nowrap bg-surface-container-lowest/80 px-1">INC-019</span>
</div>
</div>
{/*  Node: Root Cause - Kafka Drift (Cyan Square)  */}
<div className="absolute top-[52%] left-[74%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('RC-KAFKA-DRIFT', 'ROOT CAUSE', 'Consumer Group Lag Partition Offset Desync', 'mem_sha256_aa77b3', '15 Times', '99.8%', '19 Filtered', '1536-D (Norm: 0.985)', 'RB-KAFKA-SCALE', '7m 45s', 'RESOLVED')}>
<div className="w-9 h-9 bg-secondary/10 border-2 border-secondary flex items-center justify-center shadow-[0_0_12px_rgba(0,238,252,0.3)]">
<span className="material-symbols-outlined text-secondary text-base">hub</span>
</div>
<span className="absolute -top-5 left-1/2 -translate-x-1/2 font-label-sm text-[9px] text-secondary font-bold whitespace-nowrap bg-surface-container-lowest px-1">RC: KAFKA DRIFT</span>
</div>
{/*  Node: Runbook - RB-KAFKA-SCALE (Neon Blue Circle)  */}
<div className="absolute top-[58%] left-[82%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('RB-KAFKA-SCALE', 'RUNBOOK ACTION', 'Auto-partition Reassignment &amp; Replica Expansion', 'mem_sha256_4431e0', '28 Invocations', '100%', '0 Regressions', '1536-D (Deterministic)', 'KAFKA_DISPATCH_ORCH', '2m 10s', 'STANDBY')}>
<div className="w-8 h-8 rounded-full bg-secondary-fixed/20 border-2 border-secondary-fixed flex items-center justify-center shadow-[0_0_10px_rgba(125,244,255,0.4)]">
<span className="material-symbols-outlined text-secondary-fixed text-sm">tune</span>
</div>
<span className="absolute -bottom-5 left-1/2 -translate-x-1/2 font-label-sm text-[8px] text-secondary-fixed whitespace-nowrap bg-surface-container-lowest px-1">RB-KAFKA-SCALE</span>
</div>
{/*  Auxiliary Mesh Nodes  */}
<div className="absolute top-[72%] left-[78%] -translate-x-1/2 -translate-y-1/2 z-10 cursor-pointer group hover:scale-110 transition-transform">
<div className="w-6 h-6 bg-surface-container-high border border-tertiary flex items-center justify-center">
<span className="w-1.5 h-1.5 bg-tertiary"></span>
</div>
<span className="absolute -bottom-4 left-1/2 -translate-x-1/2 font-label-sm text-[8px] text-tertiary">INC-055</span>
</div>
<div className="absolute top-[70%] left-[60%] -translate-x-1/2 -translate-y-1/2 z-10 cursor-pointer group hover:scale-110 transition-transform">
<div className="w-6 h-6 rounded-full border border-secondary-fixed-dim flex items-center justify-center">
<span className="w-1 h-1 bg-secondary-fixed"></span>
</div>
<span className="absolute -bottom-4 left-1/2 -translate-x-1/2 font-label-sm text-[8px] text-on-surface-variant">RB-EGRESS-REROUTE</span>
</div>
<div className="absolute top-[46%] left-[84%] -translate-x-1/2 -translate-y-1/2 z-10 cursor-pointer group hover:scale-110 transition-transform">
<div className="w-5 h-5 border border-primary/30 flex items-center justify-center text-primary text-[10px]">✕</div>
<span className="absolute -top-4 left-1/2 -translate-x-1/2 font-label-sm text-[7px] text-primary/70 line-through">DEC-884</span>
</div>
{/*  ==================== CLUSTER 3: MEMORY EXHAUSTION ZONE ====================  */}
{/*  Node: INC-063 (Verified Incident Hexagon)  */}
<div className="absolute top-[68%] left-[22%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('INC-063', 'VERIFIED INCIDENT', 'Go Runtime Memory Allocator Fragmentation', 'mem_sha256_662d77', '9 Times', '100%', '3 Blocked', '1536-D (Norm: 0.955)', 'RB-POD-RECYCLE-GRACEFUL', '3m 15s', 'NOMINAL')}>
<div className="w-9 h-9 bg-surface-container-lowest flex items-center justify-center relative">
<svg className="w-8 h-8 text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 100 100">
<polygon fill="#101419" points="50,4 92,26 92,74 50,96 8,74 8,26" strokeWidth="5"  />
<polygon fill="#00e479" points="50,38 60,56 40,56"  />
</svg>
<span className="absolute -top-5 left-1/2 -translate-x-1/2 font-label-sm text-[9px] text-tertiary whitespace-nowrap bg-surface-container-lowest/80 px-1">INC-063</span>
</div>
</div>
{/*  Node: Root Cause - Mem Leak (Cyan Square)  */}
<div className="absolute top-[76%] left-[30%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('RC-MEM-LEAK', 'ROOT CAUSE', 'Unbounded In-Memory Telemetry Ring Buffer Allocation', 'mem_sha256_55e100', '11 Times', '100%', '8 Filtered', '1536-D (Norm: 0.979)', 'RB-BUFFER-COMPACT', '4m 30s', 'RESOLVED')}>
<div className="w-8 h-8 bg-secondary/10 border-2 border-secondary flex items-center justify-center">
<span className="material-symbols-outlined text-secondary text-sm">memory</span>
</div>
<span className="absolute -bottom-5 left-1/2 -translate-x-1/2 font-label-sm text-[9px] text-secondary font-bold whitespace-nowrap bg-surface-container-lowest px-1">RC: MEM LEAK</span>
</div>
{/*  Node: INC-078  */}
<div className="absolute top-[70%] left-[38%] -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer group hover:scale-110 transition-transform" onClick={() => selectNode('INC-078', 'VERIFIED INCIDENT', 'Redis Cluster OOM Command Eviction Storm', 'mem_sha256_7781b2', '5 Times', '94.0%', '4 Blocked', '1536-D (Norm: 0.892)', 'RB-REDIS-MEM-SHARD', '5m 50s', 'NOMINAL')}>
<div className="w-8 h-8 bg-surface-container-lowest flex items-center justify-center relative">
<svg className="w-7 h-7 text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 100 100">
<polygon fill="#101419" points="50,4 92,26 92,74 50,96 8,74 8,26" strokeWidth="5"  />
</svg>
<span className="absolute -top-4 left-1/2 -translate-x-1/2 font-label-sm text-[8px] text-tertiary whitespace-nowrap">INC-078</span>
</div>
</div>
{/*  Additional Ambient Background Cluster Nodes (Totaling 32 in topology)  */}
<div className="absolute top-[32%] left-[62%] w-5 h-5 bg-surface-container border border-secondary-fixed flex items-center justify-center cursor-pointer opacity-70 hover:opacity-100"><span className="w-1 h-1 bg-secondary-fixed"></span></div>
<div className="absolute top-[82%] left-[44%] w-5 h-5 bg-surface-container border border-primary/40 flex items-center justify-center cursor-pointer text-[9px] text-primary">✕</div>
<div className="absolute top-[48%] left-[22%] w-4 h-4 bg-tertiary/20 rounded-full cursor-pointer"></div>
<div className="absolute top-[14%] left-[38%] w-4 h-4 bg-secondary/20 cursor-pointer"></div>
<div className="absolute top-[26%] left-[72%] w-4 h-4 bg-tertiary/30 cursor-pointer"></div>
<div className="absolute top-[76%] left-[65%] w-4 h-4 bg-primary/20 cursor-pointer"></div>
<div className="absolute top-[60%] left-[48%] w-5 h-5 border border-tertiary/40 rotate-45 cursor-pointer"></div>
<div className="absolute top-[42%] left-[60%] w-4 h-4 rounded-full bg-secondary-fixed/30 cursor-pointer"></div>
<div className="absolute top-[85%] left-[32%] w-4 h-4 border border-tertiary cursor-pointer"></div>
<div className="absolute top-[34%] left-[48%] w-4 h-4 bg-surface-container-highest cursor-pointer"></div>
<div className="absolute top-[18%] left-[70%] w-4 h-4 border border-secondary cursor-pointer"></div>
<div className="absolute top-[64%] left-[34%] w-5 h-5 border border-primary/30 flex items-center justify-center text-[8px] text-primary">✕</div>
<div className="absolute top-[56%] left-[26%] w-4 h-4 bg-tertiary/20 cursor-pointer"></div>
<div className="absolute top-[78%] left-[86%] w-4 h-4 bg-secondary/30 cursor-pointer"></div>
<div className="absolute top-[22%] left-[82%] w-4 h-4 border border-tertiary cursor-pointer"></div>
{/*  HUD Interaction Reticle Indicator (Follows focus point)  */}
<div className="absolute top-[38%] left-[42%] -translate-x-1/2 -translate-y-1/2 w-48 h-48 pointer-events-none border border-secondary/20 rounded-full flex items-center justify-center animate-spin" style={{ animationDuration: '24s' }}>
<div className="w-full h-0.5 bg-secondary/10"></div>
</div>
</div>
{/*  2. NODE INSPECTOR HUD (Right Floating Panel)  */}
<div className="absolute top-space-md right-space-md bottom-20 w-80 md:w-96 z-40 bg-surface-container-lowest/85 backdrop-blur-xl border border-secondary/30 flex flex-col justify-between shadow-[0_0_30px_rgba(0,0,0,0.8)] overflow-hidden" id="inspector-panel">
{/*  Panel Header Bar with Specular Accent  */}
<div className="bg-surface-container-low px-space-md py-space-sm flex items-center justify-between border-b border-surface-variant">
<div className="flex items-center gap-space-xs">
<span className="w-2 h-2 bg-secondary animate-pulse"></span>
<span className="font-headline-sm text-headline-sm text-secondary uppercase tracking-wider" id="inspector-node-title">NODE INSPECTION // INC-104</span>
</div>
<span className="px-1.5 py-0.5 font-label-sm text-label-sm bg-tertiary/20 text-tertiary border border-tertiary uppercase" id="inspector-status-badge">[VERIFIED]</span>
</div>
{/*  Panel Body Content  */}
<div className="p-space-md flex-1 overflow-y-auto flex flex-col gap-space-md">
{/*  Node Type & Description  */}
<div className="flex flex-col gap-1 bg-surface-container-low p-space-sm">
<span className="font-label-sm text-[9px] uppercase tracking-widest text-on-surface-variant">Cluster Context</span>
<span className="font-label-md text-label-md text-tertiary font-bold tracking-wide" id="inspector-type">VERIFIED INCIDENT</span>
<p className="font-body-sm text-body-sm text-on-surface leading-snug" id="inspector-summary">
            PostgreSQL Socket Saturation &amp; Thread Starvation resulting in API Gateway 504 timeouts across core microservices.
          </p>
</div>
{/*  Provenance Cryptographic Attestation  */}
<div className="flex flex-col gap-1">
<span className="font-label-sm text-[9px] uppercase tracking-widest text-on-surface-variant flex items-center justify-between">
<span>Provenance Hash</span>
<span className="text-tertiary">SEALED (ED25519)</span>
</span>
<div className="p-space-xs bg-surface-container-highest font-mono text-[10px] text-secondary select-all flex items-center justify-between">
<span id="inspector-hash">mem_sha256_88190c1f4e098a</span>
<span className="material-symbols-outlined text-xs text-on-surface-variant cursor-pointer hover:text-on-surface">content_copy</span>
</div>
</div>
{/*  Telemetry & Performance Metrics Matrix  */}
<div className="grid grid-cols-2 gap-space-xs font-label-sm text-label-sm">
<div className="bg-surface-container-low p-space-sm flex flex-col">
<span className="text-on-surface-variant text-[9px] uppercase">Invocations</span>
<span className="font-headline-sm text-headline-sm text-on-surface font-mono mt-0.5" id="inspector-invocations">4 Times</span>
</div>
<div className="bg-surface-container-low p-space-sm flex flex-col">
<span className="text-on-surface-variant text-[9px] uppercase">Accuracy Rating</span>
<span className="font-headline-sm text-headline-sm text-tertiary font-mono mt-0.5" id="inspector-accuracy">100%</span>
</div>
<div className="bg-surface-container-low p-space-sm flex flex-col">
<span className="text-on-surface-variant text-[9px] uppercase">Decoys Blocked</span>
<span className="font-headline-sm text-headline-sm text-primary font-mono mt-0.5" id="inspector-decoys">7 Prevented</span>
</div>
<div className="bg-surface-container-low p-space-sm flex flex-col">
<span className="text-on-surface-variant text-[9px] uppercase">MTTR Benchmark</span>
<span className="font-headline-sm text-headline-sm text-secondary-fixed font-mono mt-0.5" id="inspector-mttr">4m 12s</span>
</div>
</div>
{/*  Similarity Vector Norm Spec  */}
<div className="bg-surface-container-low p-space-sm flex flex-col gap-2 border border-secondary/20"><div className="flex justify-between items-center text-[10px] font-label-sm"><span className="text-on-surface-variant uppercase flex items-center gap-1"><span className="w-1.5 h-1.5 bg-secondary-fixed rounded-full"></span>1536-D HYPERPLANE RADAR</span><span className="text-secondary font-mono" id="inspector-vector">1536-D (Norm: 1.000)</span></div><div className="relative w-full h-36 flex items-center justify-center bg-surface-container-lowest/90 p-1 border border-surface-variant"><svg className="w-full h-full" viewBox="0 0 200 130"><polygon fill="none" opacity="0.2" points="100,10 180,38 150,118 50,118 20,38" stroke="#7df4ff" strokeWidth="0.75"  /><polygon fill="none" opacity="0.35" points="100,25 160,47 137,105 63,105 40,47" stroke="#7df4ff" strokeWidth="0.75"  /><polygon fill="none" opacity="0.5" points="100,42 140,56 125,93 75,93 60,56" stroke="#7df4ff" strokeDasharray="2,2" strokeWidth="0.75"  /><line opacity="0.3" stroke="#7df4ff" strokeWidth="0.75" x1="100" x2="100" y1="65" y2="10"  /><line opacity="0.3" stroke="#7df4ff" strokeWidth="0.75" x1="100" x2="180" y1="65" y2="38"  /><line opacity="0.3" stroke="#7df4ff" strokeWidth="0.75" x1="100" x2="150" y1="65" y2="118"  /><line opacity="0.3" stroke="#7df4ff" strokeWidth="0.75" x1="100" x2="50" y1="65" y2="118"  /><line opacity="0.3" stroke="#7df4ff" strokeWidth="0.75" x1="100" x2="20" y1="65" y2="38"  /><polygon fill="#00eefc" fillOpacity="0.2" points="100,12 170,41 146,115 56,114 26,43" stroke="#00e479" strokeWidth="1.75"  /><circle cx="100" cy="12" fill="#60ff99" r="2.5"  /><circle cx="170" cy="41" fill="#7df4ff" r="2.5"  /><circle cx="146" cy="115" fill="#00eefc" r="2.5"  /><circle cx="56" cy="114" fill="#60ff99" r="2.5"  /><circle cx="26" cy="43" fill="#7df4ff" r="2.5"  /><text fill="#00e479" fontFamily="Space Mono" fontSize="7" textAnchor="middle" x="100" y="8">Cosine: 0.994</text><text fill="#7df4ff" fontFamily="Space Mono" fontSize="6.5" textAnchor="start" x="152" y="32">Density: 0.88</text><text fill="#e0e2eb" fontFamily="Space Mono" fontSize="6.5" textAnchor="start" x="122" y="126">Entropy: 0.14</text><text fill="#00e479" fontFamily="Space Mono" fontSize="6.5" textAnchor="end" x="78" y="126">Causal: 99.8%</text><text fill="#7df4ff" fontFamily="Space Mono" fontSize="6.5" textAnchor="end" x="48" y="32">Cohesion: 0.92</text></svg></div><div className="grid grid-cols-2 gap-1 text-[8px] font-label-sm text-on-surface-variant"><span className="flex items-center gap-1"><span className="w-1 h-1 bg-tertiary rounded-full"></span>CONFIDENCE: <b className="text-tertiary">99.8%</b></span><span className="flex items-center gap-1"><span className="w-1 h-1 bg-secondary rounded-full"></span>COSINE: <b className="text-secondary">0.994</b></span></div></div>
{/*  Linked Runbook Module  */}
<div className="bg-surface-container-high p-space-sm flex flex-col gap-1 border-l-2 border-secondary-fixed">
<span className="font-label-sm text-[9px] uppercase text-on-surface-variant">Linked Runbook Enactment</span>
<div className="flex items-center justify-between">
<span className="font-label-md text-label-md text-secondary-fixed font-bold font-mono" id="inspector-runbook">RB-PGBOUNCER-POOL-120</span>
<span className="material-symbols-outlined text-sm text-secondary-fixed">bolt</span>
</div>
<p className="font-body-sm text-[10px] text-on-surface-variant leading-tight">
            Executes connection pool drainage, rotates dormant workers, and allocates ephemeral buffer cache.
          </p>
</div>
</div>
{/*  Quick Action Commands Footnote  */}
<div className="p-space-sm bg-surface-container-lowest border-t border-surface-variant flex gap-space-xs">
<button className="flex-1 py-2 bg-secondary/10 border border-secondary text-secondary font-label-sm text-[10px] uppercase font-bold hover:bg-secondary hover:text-on-secondary transition-colors flex items-center justify-center gap-1" onClick={() => showToast('Attestation verified in secure enclave!')}>
<span className="material-symbols-outlined text-xs">verified_user</span>
          Re-verify Enclave
        </button>
<button className="flex-1 py-2 bg-surface-container-high text-on-surface font-label-sm text-[10px] uppercase font-bold hover:bg-surface-container-highest transition-colors flex items-center justify-center gap-1" onClick={() => showToast('Vectors exported to tensor payload.')}>
<span className="material-symbols-outlined text-xs">download</span>
          Export Vectors
        </button>
</div>
</div>
{/*  3. BOTTOM FLOATING FILTER & SPATIAL CONTROL BAR  */}
<div className="absolute bottom-4 left-space-md right-space-md z-40 flex flex-wrap items-center justify-between gap-space-md pointer-events-none">
{/*  Pill Filter Cluster  */}
<div className="pointer-events-auto bg-surface-container-lowest/90 backdrop-blur-md p-1 border border-surface-variant flex items-center gap-1 shadow-2xl">
<button className="px-space-sm py-1.5 font-label-sm text-label-sm uppercase font-bold bg-secondary text-on-secondary flex items-center gap-1.5 shadow-sm transition-all" id="btn-filter-all" onClick={() => setActiveFilter('all')}>
<span className="w-1.5 h-1.5 bg-on-secondary rounded-full"></span>
          All Nodes (32)
        </button>
<button className="px-space-sm py-1.5 font-label-sm text-label-sm uppercase font-bold text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all flex items-center gap-1.5" id="btn-filter-verified" onClick={() => setActiveFilter('verified')}>
<span className="w-1.5 h-1.5 bg-tertiary rounded-full"></span>
          Verified Only (18)
        </button>
<button className="px-space-sm py-1.5 font-label-sm text-label-sm uppercase font-bold text-on-surface-variant hover:text-primary hover:bg-surface-container transition-all flex items-center gap-1.5" id="btn-filter-decoys" onClick={() => setActiveFilter('decoys')}>
<span className="w-1.5 h-1.5 bg-primary rounded-full"></span>
          Show Decoys (7)
        </button>
<button className="px-space-sm py-1.5 font-label-sm text-label-sm uppercase font-bold text-on-surface-variant hover:text-primary-container hover:bg-surface-container transition-all flex items-center gap-1.5" id="btn-filter-novel" onClick={() => setActiveFilter('novel')}>
<span className="w-1.5 h-1.5 bg-primary-container rounded-full animate-ping"></span>
          Novel Alerts (1)
        </button>
</div>
{/*  Spatial Canvas & Camera Controls  */}
<div className="pointer-events-auto bg-surface-container-lowest/90 backdrop-blur-md p-1 border border-surface-variant flex items-center gap-space-xs shadow-2xl">
<button className="px-space-sm py-1.5 font-label-sm text-label-sm text-secondary bg-surface-container uppercase font-bold hover:bg-surface-container-high transition-colors flex items-center gap-1" id="proj-toggle" onClick={() => toggleProjection()}>
<span className="material-symbols-outlined text-xs">view_in_ar</span>
<span id="proj-label">3D PROJECTION</span>
</button>
<div className="h-4 w-[1px] bg-surface-variant"></div>
<button className="px-space-sm py-1.5 font-label-sm text-label-sm text-tertiary bg-surface-container uppercase font-bold hover:bg-surface-container-high transition-colors flex items-center gap-1" id="physics-toggle" onClick={() => togglePhysics()}>
<span className="w-1.5 h-1.5 bg-tertiary rounded-full animate-pulse"></span>
<span id="physics-label">PHYSICS: ACTIVE</span>
</button>
<div className="h-4 w-[1px] bg-surface-variant"></div>
<div className="flex items-center px-space-xs text-on-surface-variant font-label-sm text-label-sm gap-1">
<button className="p-1 hover:text-on-surface" onClick={() => adjustZoom(-10)}><span className="material-symbols-outlined text-xs">remove</span></button>
<span className="font-mono text-on-surface font-bold" id="zoom-indicator">100%</span>
<button className="p-1 hover:text-on-surface" onClick={() => adjustZoom(10)}><span className="material-symbols-outlined text-xs">add</span></button>
</div>
</div>
</div>
{/*  Micro-Notification Toast Overlay  */}
<div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-50 bg-secondary text-on-secondary px-space-md py-space-xs font-label-sm text-label-sm font-bold uppercase shadow-2xl pointer-events-none opacity-0 transition-opacity duration-300" id="toast-notify">
      Vector Engine Synced
    </div>
</div>
</div>
</main>
    </div>
  );
};
