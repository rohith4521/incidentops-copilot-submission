import React from 'react';

interface SpatialHeroTheaterViewProps {
  onNavigate: (view: string) => void;
}

export const SpatialHeroTheaterView: React.FC<SpatialHeroTheaterViewProps> = ({ onNavigate }) => {
  return (
    <main className="w-full pt-16 bg-[#020408] flex-1 pb-10"><div className="flex flex-col w-full text-on-surface overflow-x-hidden selection:bg-secondary selection:text-on-secondary">
<div className="relative w-full min-h-[942px] flex flex-col justify-between py-space-xl px-margin overflow-hidden bg-radial from-secondary-container/10 via-tertiary-container/5 to-transparent">
<div className="pointer-events-none absolute inset-0 z-0">
<div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:4rem_4rem]"></div>
<div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-secondary-fixed-dim/5 rounded-full blur-[140px] pointer-events-none"></div>
<div className="absolute bottom-1/3 left-1/3 w-[500px] h-[500px] bg-tertiary/5 rounded-full blur-[160px] pointer-events-none"></div>
<span className="absolute top-16 left-24 text-outline-variant font-label-sm text-label-sm opacity-60">+</span>
<span className="absolute top-16 right-24 text-outline-variant font-label-sm text-label-sm opacity-60">+</span>
<span className="absolute bottom-24 left-32 text-outline-variant font-label-sm text-label-sm opacity-60">+</span>
<span className="absolute bottom-24 right-32 text-outline-variant font-label-sm text-label-sm opacity-60">+</span>
<span className="absolute top-1/2 left-12 text-outline-variant font-label-sm text-label-sm opacity-60">+</span>
<span className="absolute top-1/2 right-12 text-outline-variant font-label-sm text-label-sm opacity-60">+</span>
<div className="hidden xl:block absolute top-6 left-8 font-label-sm text-label-sm text-outline tracking-widest uppercase">
        LOC://0x7F4B.US-EAST-1 // STAGE.ORBITAL
      </div>
<div className="hidden xl:block absolute top-6 right-8 font-label-sm text-label-sm text-outline tracking-widest uppercase text-right">
        DIM_SPACE://1536D // AIRGAP.VERIFIED
      </div>
</div>
<div className="relative z-10 w-full max-w-6xl mx-auto flex flex-col items-center text-center mt-2">
<div className="inline-flex items-center gap-space-sm px-space-md py-1.5 bg-surface-container-lowest/80 backdrop-blur-md shadow-md mb-space-lg border border-white/5">
<span className="relative flex h-2 w-2">
<span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-tertiary opacity-75"></span>
<span className="relative inline-flex rounded-full h-2 w-2 bg-tertiary"></span>
</span>
<span className="font-label-sm text-label-sm text-secondary tracking-widest uppercase">
          AUTONOMOUS REASONING KERNEL // AIRGAP COCKPIT v2.4 // 1536-D EMBEDDINGS
        </span>
</div>
<h1 className="font-headline-xl text-headline-xl uppercase tracking-tighter leading-[1.05] max-w-4xl text-on-surface">
        Incidents Remembered.
        <span className="block bg-gradient-to-r from-secondary-fixed-dim via-secondary to-tertiary bg-clip-text text-transparent drop-shadow-[0_0_24px_rgba(0,219,233,0.35)]">
          Resolution Repeated.
        </span>
</h1>
<p className="mt-space-md font-body-lg text-body-lg text-on-surface-variant max-w-2xl text-center leading-relaxed">
        Traditional incident AI is amnesic. IncidentOps Copilot retains, evaluates, and verifies operational memory through Hindsight so distributed outages are never solved twice.
      </p>
<div className="mt-space-lg flex flex-wrap items-center justify-center gap-space-md">
<button onClick={() => onNavigate("incident-command-center")} className="group relative px-space-lg py-space-sm bg-secondary-container/15 hover:bg-secondary-container/25 text-secondary font-label-lg text-label-lg uppercase tracking-wider backdrop-blur-md shadow-lg transition-all duration-200 border-t border-white/20 border-b border-black/80 cursor-pointer" type="button">
<span className="flex items-center gap-2">
            Launch Command Center
            <span className="material-symbols-outlined text-[16px] transition-transform group-hover:translate-x-1">arrow_forward</span>
</span>
</button>
<button onClick={() => onNavigate("spatial-memory-explorer")} className="px-space-lg py-space-sm bg-surface-container-high/60 hover:bg-surface-container-highest text-on-surface font-label-lg text-label-lg uppercase tracking-wider backdrop-blur-md shadow-sm transition-all duration-200 border-t border-white/15 border-b border-black/80 cursor-pointer" type="button">
<span className="flex items-center gap-2">
<span className="material-symbols-outlined text-[16px] text-tertiary">view_in_ar</span>
            Explore 3D Memory Graph
          </span>
</button>
</div>
</div>
<div className="relative z-10 w-full max-w-7xl mx-auto my-space-xl flex-1 flex items-center justify-center min-h-[460px]">
<svg className="absolute inset-0 w-full h-full pointer-events-none z-0 overflow-visible" preserveAspectRatio="none" viewBox="0 0 1000 500" xmlns="http://www.w3.org/2000/svg">
<defs>
<filter height="140%" id="glow-teal" width="140%" x="-20%" y="-20%">
<feGaussianBlur in="SourceGraphic" result="blur" stdDeviation="3.5"></feGaussianBlur>
<feMerge>
<feMergeNode in="blur"></feMergeNode>
<feMergeNode in="SourceGraphic"></feMergeNode>
</feMerge>
</filter>
<filter height="140%" id="glow-cyan" width="140%" x="-20%" y="-20%">
<feGaussianBlur in="SourceGraphic" result="blur" stdDeviation="3.5"></feGaussianBlur>
<feMerge>
<feMergeNode in="blur"></feMergeNode>
<feMergeNode in="SourceGraphic"></feMergeNode>
</feMerge>
</filter>
<filter height="140%" id="glow-amber" width="140%" x="-20%" y="-20%">
<feGaussianBlur in="SourceGraphic" result="blur" stdDeviation="3.5"></feGaussianBlur>
<feMerge>
<feMergeNode in="blur"></feMergeNode>
<feMergeNode in="SourceGraphic"></feMergeNode>
</feMerge>
</filter>
<filter height="140%" id="glow-severed" width="140%" x="-20%" y="-20%">
<feGaussianBlur in="SourceGraphic" result="blur" stdDeviation="4"></feGaussianBlur>
<feMerge>
<feMergeNode in="blur"></feMergeNode>
<feMergeNode in="SourceGraphic"></feMergeNode>
</feMerge>
</filter>
<linearGradient id="catenary-teal-base" x1="0%" x2="100%" y1="0%" y2="100%">
<stop offset="0%" stopColor="#00e479" stopOpacity="0.95"  />
<stop offset="60%" stopColor="#00e479" stopOpacity="0.45"  />
<stop offset="100%" stopColor="#00e479" stopOpacity="0.1"  />
</linearGradient>
<linearGradient id="catenary-cyan-base" x1="100%" x2="0%" y1="0%" y2="100%">
<stop offset="0%" stopColor="#00dbe9" stopOpacity="0.95"  />
<stop offset="60%" stopColor="#00dbe9" stopOpacity="0.45"  />
<stop offset="100%" stopColor="#00dbe9" stopOpacity="0.1"  />
</linearGradient>
<linearGradient id="catenary-amber-base" x1="0%" x2="100%" y1="100%" y2="0%">
<stop offset="0%" stopColor="#ffb2ba" stopOpacity="0.85"  />
<stop offset="60%" stopColor="#ff4f73" stopOpacity="0.4"  />
<stop offset="100%" stopColor="#ffb2ba" stopOpacity="0.1"  />
</linearGradient>
<linearGradient id="severed-stub-grad" x1="0%" x2="100%" y1="0%" y2="100%">
<stop offset="0%" stopColor="#ff3366" stopOpacity="0.7"  />
<stop offset="100%" stopColor="#ff3366" stopOpacity="0.05"  />
</linearGradient>
</defs>
{/*  Static underlying tension cables  */}
<path d="M 500 240 C 400 220, 260 140, 160 85" fill="none" stroke="#00e479" strokeOpacity="0.22" strokeWidth="1.5"  />
<path d="M 500 240 C 600 220, 740 140, 840 85" fill="none" stroke="#00dbe9" strokeOpacity="0.22" strokeWidth="1.5"  />
<path d="M 500 260 C 400 280, 260 360, 160 415" fill="none" stroke="#ffb2ba" strokeOpacity="0.2" strokeWidth="1.5"  />
{/*  Dynamic Kinetic Flow Pulses (stroke-dashoffset bezier catenary cables)  */}
<path className="catenary-pulse-teal" d="M 500 240 C 400 220, 260 140, 160 85" fill="none" filter="url(#glow-teal)" stroke="#00e479" strokeLinecap="round" strokeWidth="2.5"  />
<path className="catenary-pulse-cyan" d="M 500 240 C 600 220, 740 140, 840 85" fill="none" filter="url(#glow-cyan)" stroke="#00eefc" strokeLinecap="round" strokeWidth="2.5"  />
<path className="catenary-pulse-amber" d="M 500 260 C 400 280, 260 360, 160 415" fill="none" filter="url(#glow-amber)" stroke="#ffb2ba" strokeLinecap="round" strokeWidth="2.5"  />
{/*  SEVERED CORD TO DECOY_MEM_0884 (Dashed red stroke, broken segment, severed visual indicator)  */}
{/*  Severed stub from center  */}
<path className="severed-cord" d="M 500 260 C 580 275, 650 310, 700 335" fill="none" filter="url(#glow-severed)" stroke="#ff3366" strokeDasharray="6,6" strokeLinecap="round" strokeWidth="2"  />
{/*  Disconnected hanging tail near card  */}
<path className="severed-cord" d="M 760 370 C 785 385, 810 400, 840 415" fill="none" stroke="#ff3366" strokeDasharray="4,6" strokeOpacity="0.4" strokeWidth="1.5"  />
{/*  Severed break / spark burst markers  */}
<g className="severed-cord" transform="translate(705, 338)">
<circle cx="0" cy="0" fill="#ff3366" r="4"  />
<circle cx="0" cy="0" fill="none" r="8" stroke="#ff3366" strokeOpacity="0.6" strokeWidth="1.2"  />
<line stroke="#ffdad6" strokeWidth="1.5" x1="-6" x2="6" y1="-6" y2="6"  />
<line stroke="#ffdad6" strokeWidth="1.5" x1="-6" x2="6" y1="6" y2="-6"  />
<text fill="#ff4f73" fontFamily="'Space Mono', monospace" fontSize="9" fontWeight="700" letterSpacing="0.1em" x="12" y="4">[LINK SEVERED]</text>
</g>
{/*  Anchor attachment nodes  */}
<circle cx="160" cy="85" fill="#00e479" filter="url(#glow-teal)" r="4.5"  />
<circle cx="160" cy="85" fill="#ffffff" r="2"  />
<circle cx="840" cy="85" fill="#00eefc" filter="url(#glow-cyan)" r="4.5"  />
<circle cx="840" cy="85" fill="#ffffff" r="2"  />
<circle cx="160" cy="415" fill="#ffb2ba" filter="url(#glow-amber)" r="4.5"  />
<circle cx="160" cy="415" fill="#ffffff" r="2"  />
<circle cx="840" cy="415" fill="#ff3366" opacity="0.6" r="4"  />
<circle cx="500" cy="250" fill="#00e479" filter="url(#glow-teal)" r="5"  />
</svg>
<div className="relative z-10 flex flex-col items-center justify-center p-space-lg bg-[#0b0e14]/90 backdrop-blur-xl max-w-sm border-t border-white/20 border-b border-black/90 shadow-[0_24px_50px_rgba(0,0,0,0.85)]">
{/*  Ambient emerald/cyan radial bloom behind the central engine  */}
<div className="pointer-events-none absolute -inset-16 -z-10 rounded-full bg-[radial-gradient(circle,rgba(0,255,136,0.22)_0%,rgba(0,240,255,0.15)_45%,transparent_72%)] blur-2xl"></div>
{/*  Central Interactive Engine with Rotating Radar Scan Ring & Crosshair Reticle  */}
<div className="relative w-36 h-36 flex items-center justify-center">
{/*  Deep ambient pulse ring  */}
<div className="absolute inset-0 rounded-full bg-tertiary/10 animate-ping duration-1000"></div>
<div className="absolute -inset-4 rounded-full bg-gradient-to-tr from-tertiary/20 to-secondary-container/20 blur-md"></div>
{/*  Crosshair Reticle Lines  */}
<div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-[1px] bg-gradient-to-r from-transparent via-tertiary/40 to-transparent pointer-events-none"></div>
<div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-[1px] bg-gradient-to-b from-transparent via-secondary/40 to-transparent pointer-events-none"></div>
<span className="absolute -top-1 left-1/2 -translate-x-1/2 font-label-sm text-[8px] text-tertiary tracking-widest pointer-events-none">000°</span>
<span className="absolute -bottom-1 left-1/2 -translate-x-1/2 font-label-sm text-[8px] text-tertiary tracking-widest pointer-events-none">180°</span>
<span className="absolute -left-1 top-1/2 -translate-y-1/2 font-label-sm text-[8px] text-secondary tracking-widest pointer-events-none">270°</span>
<span className="absolute -right-1 top-1/2 -translate-y-1/2 font-label-sm text-[8px] text-secondary tracking-widest pointer-events-none">090°</span>
{/*  Outer Rotating 360-Degree Radar Scan Ring & Sweep Trail  */}
<div className="radar-sweep absolute inset-0 rounded-full border border-tertiary/30 pointer-events-none">
<div className="w-full h-full rounded-full bg-[conic-gradient(from_0deg,transparent_0deg,transparent_270deg,rgba(0,255,136,0.05)_320deg,rgba(0,240,255,0.28)_360deg)]"></div>
<div className="absolute top-0 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-secondary-fixed shadow-[0_0_8px_#00eefc]"></div>
</div>
{/*  Secondary counter-rotating calibrated ring with tick marks  */}
<div className="radar-counter absolute inset-2 rounded-full border border-dashed border-secondary/25 pointer-events-none"></div>
{/*  Core Polygon Emblem  */}
<svg className="w-24 h-24 relative z-10 transition-transform hover:scale-105 duration-300 drop-shadow-[0_0_16px_rgba(0,228,121,0.4)]" fill="none" viewBox="0 0 100 100">
<polygon fill="#181c22" points="50,5 90,27.5 90,72.5 50,95 10,72.5 10,27.5" stroke="#00eefc" strokeWidth="2.5"  />
<polygon fill="#0b0e14" points="50,15 80,32 80,68 50,85 20,68 20,32"  />
<circle cx="50" cy="50" r="22" stroke="#00e479" strokeWidth="2"  />
<polygon fill="#00e479" points="50,33 63,57 37,57"  />
<circle cx="50" cy="49" fill="#00eefc" r="3.5"  />
<line stroke="#00eefc" strokeDasharray="2 2" strokeWidth="2" x1="50" x2="50" y1="5" y2="28"  />
<line stroke="#00e479" strokeDasharray="2 2" strokeWidth="2" x1="50" x2="50" y1="72" y2="95"  />
<circle cx="10" cy="27.5" fill="#00eefc" r="3.5"  />
<circle cx="90" cy="27.5" fill="#00eefc" r="3.5"  />
<circle cx="10" cy="72.5" fill="#00e479" r="3.5"  />
<circle cx="90" cy="72.5" fill="#00e479" r="3.5"  />
</svg>
</div>
<div className="mt-space-sm text-center">
<span className="font-label-sm text-label-sm text-tertiary uppercase tracking-widest block">
            [HINDSIGHT KERNEL v2.4.0 ENGINE]
          </span>
<div className="font-headline-sm text-headline-sm text-on-surface mt-1 flex items-center justify-center gap-2">
            MEM-CONFIDENCE: <span className="text-secondary font-bold">99.82%</span>
</div>
<p className="font-body-sm text-body-sm text-outline mt-1">
            CONTINUOUS VECTOR PROVENANCE // RK4 HYPERPLANE
          </p>
</div>
</div>
{/*  Floating Card 1: Top-Left PgBouncer  */}
<div className="absolute top-4 left-4 md:left-12 max-w-xs p-space-sm bg-surface-container-lowest/90 backdrop-blur-xl border-t border-white/[0.22] border-b border-black/[0.8] shadow-[0_20px_40px_rgba(0,0,0,0.85)] ring-1 ring-white/5 transition-all duration-300 hover:border-t-tertiary/60">
<div className="flex items-center justify-between gap-space-sm pb-1">
<span className="font-label-sm text-label-sm text-tertiary flex items-center gap-1">
<span className="w-1.5 h-1.5 bg-tertiary rounded-full animate-pulse"></span>
            NODE_MEM_0104
          </span>
<span className="font-label-sm text-label-sm text-outline">RB-PGBOUNCER-120</span>
</div>
<div className="font-headline-sm text-headline-sm text-on-surface">PgBouncer Saturation</div>
<div className="mt-2 flex items-center justify-between font-label-sm text-label-sm">
<span className="text-outline">Vector Cosine:</span>
<span className="text-tertiary font-bold">0.994 (Direct Match)</span>
</div>
<div className="w-full bg-surface-container h-1 mt-1.5 overflow-hidden">
<div className="bg-tertiary h-full w-[99.4%] shadow-[0_0_8px_#00e479]"></div>
</div>
</div>
{/*  Floating Card 2: Top-Right Kafka Lag  */}
<div className="absolute top-4 right-4 md:right-12 max-w-xs p-space-sm bg-surface-container-lowest/90 backdrop-blur-xl border-t border-white/[0.22] border-b border-black/[0.8] shadow-[0_20px_40px_rgba(0,0,0,0.85)] ring-1 ring-white/5 transition-all duration-300 hover:border-t-secondary/60">
<div className="flex items-center justify-between gap-space-sm pb-1">
<span className="font-label-sm text-label-sm text-secondary flex items-center gap-1">
<span className="w-1.5 h-1.5 bg-secondary rounded-full"></span>
            NODE_MEM_0892
          </span>
<span className="font-label-sm text-label-sm text-outline">KAFKA_CLUSTER_03</span>
</div>
<div className="font-headline-sm text-headline-sm text-on-surface">Kafka Partition Lag</div>
<div className="mt-2 flex items-center justify-between font-label-sm text-label-sm">
<span className="text-outline">Offset Drift:</span>
<span className="text-secondary font-bold">+42,890 (Absorbed)</span>
</div>
<div className="w-full bg-surface-container h-1 mt-1.5 overflow-hidden">
<div className="bg-secondary h-full w-[84%] shadow-[0_0_8px_#00dbe9]"></div>
</div>
</div>
{/*  Floating Card 3: Bottom-Left Inventory Worker  */}
<div className="absolute bottom-4 left-4 md:left-12 max-w-xs p-space-sm bg-surface-container-lowest/90 backdrop-blur-xl border-t border-white/[0.22] border-b border-black/[0.8] shadow-[0_20px_40px_rgba(0,0,0,0.85)] ring-1 ring-white/5 transition-all duration-300 hover:border-t-primary/60">
<div className="flex items-center justify-between gap-space-sm pb-1">
<span className="font-label-sm text-label-sm text-primary flex items-center gap-1">
<span className="w-1.5 h-1.5 bg-primary rounded-full animate-ping"></span>
            NODE_NEW_0112
          </span>
<span className="font-label-sm text-label-sm px-1 bg-primary/20 text-primary">NOVEL PATTERN</span>
</div>
<div className="font-headline-sm text-headline-sm text-on-surface">Inventory Worker OOM</div>
<div className="mt-2 flex items-center justify-between font-label-sm text-label-sm">
<span className="text-outline">Precedent:</span>
<span className="text-primary font-bold">0% [Postmortem Active]</span>
</div>
<div className="w-full bg-surface-container h-1 mt-1.5 overflow-hidden">
<div className="bg-primary-container h-full w-[12%] shadow-[0_0_8px_#ff4f73]"></div>
</div>
</div>
{/*  Floating Card 4: Bottom-Right Stripe Gateway (Severed / Decoy)  */}
<div className="absolute bottom-4 right-4 md:right-12 max-w-xs p-space-sm bg-surface-container-lowest/90 backdrop-blur-xl border-t border-white/[0.22] border-b border-black/[0.8] shadow-[0_20px_40px_rgba(0,0,0,0.85)] ring-1 ring-white/5 opacity-90 transition-all duration-300 hover:border-t-error/60">
<div className="flex items-center justify-between gap-space-sm pb-1">
<span className="font-label-sm text-label-sm text-error flex items-center gap-1">
<span className="material-symbols-outlined text-[13px]">block</span>
            DECOY_MEM_0884
          </span>
<span className="font-label-sm text-label-sm px-1 bg-error-container text-on-error-container uppercase">PURGED</span>
</div>
<div className="font-headline-sm text-headline-sm text-outline line-through">Stripe Gateway 504</div>
<div className="mt-2 flex items-center justify-between font-label-sm text-label-sm">
<span className="text-outline">Relevance:</span>
<span className="text-error font-bold">0.12 (False Grounding)</span>
</div>
<div className="w-full bg-surface-container h-1 mt-1.5 overflow-hidden">
<div className="bg-error-container h-full w-[12%]"></div>
</div>
</div>
</div>
<div className="relative z-10 w-full grid grid-cols-2 lg:grid-cols-4 gap-space-sm pt-space-md max-w-6xl mx-auto">
<div className="p-space-sm bg-surface-container-lowest/60 backdrop-blur-sm border-t border-white/10 border-b border-black/60 shadow-md">
<span className="font-label-sm text-label-sm text-outline block">SIM_ENGINE</span>
<span className="font-body-md text-body-md text-on-surface font-bold">RK4_SOLVER [Δt 0.002]</span>
<span className="font-label-sm text-label-sm text-tertiary block mt-0.5">GRAVITY: [0.0, 0.0, 0.0]</span>
</div>
<div className="p-space-sm bg-surface-container-lowest/60 backdrop-blur-sm border-t border-white/10 border-b border-black/60 shadow-md">
<span className="font-label-sm text-label-sm text-outline block">TENSION_HARMONIC</span>
<span className="font-body-md text-body-md text-secondary font-bold">1.042 N @ 440.12 Hz</span>
<span className="font-label-sm text-label-sm text-outline block mt-0.5">VERLET 60 FPS SYNC</span>
</div>
<div className="p-space-sm bg-surface-container-lowest/60 backdrop-blur-sm border-t border-white/10 border-b border-black/60 shadow-md">
<span className="font-label-sm text-label-sm text-outline block">MEMORY_RECALL</span>
<span className="font-body-md text-body-md text-on-surface font-bold">1.84M VECTORS</span>
<span className="font-label-sm text-label-sm text-tertiary block mt-0.5">AIRGAP INTEGRITY: SEALED</span>
</div>
<div className="p-space-sm bg-surface-container-lowest/60 backdrop-blur-sm border-t border-white/10 border-b border-black/60 shadow-md">
<span className="font-label-sm text-label-sm text-outline block">SPATIAL_RELAXATION</span>
<span className="font-body-md text-body-md text-on-surface font-bold">STABLE CO-PLANAR</span>
<span className="font-label-sm text-label-sm text-secondary block mt-0.5">ENTROPY: -0.0418</span>
</div>
</div>
<div className="relative z-10 w-full mt-space-lg overflow-hidden bg-surface-container-lowest/80 backdrop-blur-md py-2 border-y border-white/5">
<div className="flex items-center whitespace-nowrap gap-space-xl font-label-sm text-label-sm animate-pulse">
<span className="text-tertiary">▸ [INGEST] Alertmanager HMAC: VALID</span>
<span className="text-outline">/</span>
<span className="text-secondary">▸ [HINDSIGHT] Query 1536-D Vector Cosine 0.994</span>
<span className="text-outline">/</span>
<span className="text-primary">▸ [RELEVANCE GATE] Decoy #0884 Suppressed</span>
<span className="text-outline">/</span>
<span className="text-on-surface">▸ [EVIDENCE] INC-042 Promoted to Tier-1</span>
<span className="text-outline">/</span>
<span className="text-tertiary">▸ [CIRCUIT BREAKER] 0 Drift</span>
<span className="text-outline">/</span>
<span className="text-secondary">▸ [ED25519] Enclave Seal Attested</span>
</div>
</div>
</div>
</div></main>
  );
};
