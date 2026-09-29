import React, { useState } from 'react';

export const ProvenanceTraceAuditView: React.FC = () => {
  const [isValidated, setIsValidated] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('all');

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleValidateSignature = () => {
    setIsValidated(true);
    showToast('ED25519 Enclave signature verified against hardware root (AMD SEV-SNP). Airgap intact.');
  };

  return (
    <div className="relative">
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 px-4 py-2 bg-secondary text-on-secondary font-mono text-xs font-bold shadow-2xl flex items-center gap-2 border border-white/20">
          <span className="material-symbols-outlined text-base">verified</span>
          <span>{toastMessage}</span>
        </div>
      )}
<main className="w-full pt-16 bg-[#020408] flex-1 pb-10"><div className="flex flex-col w-full">
<div className="w-full px-margin py-space-lg flex flex-col gap-space-lg">
{/*  TOP NOTIFICATION BANNER / STATUS STRIP  */}
<div className="w-full bg-surface-container-lowest p-space-sm flex flex-wrap items-center justify-between gap-space-md shadow-md border-l-2 border-tertiary">
<div className="flex items-center gap-space-sm">
<span className="w-2 h-2 bg-tertiary animate-pulse"></span>
<span className="font-label-sm text-label-sm text-tertiary tracking-widest uppercase">ENCLAVE ATTESTATION STATE: STRICT_SEALED</span>
<span className="text-outline text-body-sm font-body-sm">/</span>
<span className="font-label-sm text-label-sm text-on-surface-variant uppercase">BLOCK: #94,188,285</span>
<span className="text-outline text-body-sm font-body-sm">/</span>
<span className="font-label-sm text-label-sm text-secondary font-bold uppercase">SECURE PROTOCOL v2.4.0</span>
<span className="text-outline text-body-sm font-body-sm">/</span>
<span className="font-label-sm text-label-sm text-primary uppercase">INCIDENT REF: INC-104 (PGBOUNCER SATURATION)</span>
</div>
<div className="flex items-center gap-space-sm">
<span className="font-label-sm text-label-sm text-on-surface-variant uppercase">HARDWARE ROOT:</span>
<span className="font-label-sm text-label-sm bg-surface-container px-space-xs py-0.5 text-on-surface font-mono">AMD SEV-SNP HARDENED</span>
<span className="font-label-sm text-label-sm bg-tertiary/10 text-tertiary px-space-xs py-0.5 uppercase tracking-wider font-bold">[VERIFIED 0.4s AGO]</span>
</div>
</div>
{/*  1. CRYPTOGRAPHIC ENCLAVE PROOF RECORD & HARDWARE MEMORY BOUNDARY  */}
<div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-gutter">
{/*  Seal Graphic, Isolation Micro-Diagram & Core Attestation Card  */}
<div className="lg:col-span-8 bg-surface-container-low p-space-lg flex flex-col justify-between relative overflow-hidden shadow-xl border border-surface-container-high/60">
<div className="absolute -right-12 -top-12 w-64 h-64 bg-secondary/5 rounded-full blur-3xl pointer-events-none"></div>
<div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-md mb-space-md">
<div className="flex items-center gap-space-md">
{/*  Custom Geometric Enclave Hexagon Token  */}
<div className="relative w-16 h-16 shrink-0 flex items-center justify-center bg-surface-container-lowest shadow-md border border-secondary/30">
<svg className="w-14 h-14" fill="none" viewBox="0 0 100 100">
<polygon fill="#181c22" points="50,4 92,27 92,73 50,96 8,73 8,27" stroke="#00eefc" strokeWidth="2.5"  />
<circle cx="50" cy="50" fill="#101419" r="24" stroke="#00e479" strokeWidth="2.5"  />
<line stroke="#00eefc" strokeDasharray="3,3" strokeWidth="2" x1="50" x2="50" y1="8" y2="28"  />
<line stroke="#00e479" strokeDasharray="3,3" strokeWidth="2" x1="50" x2="50" y1="72" y2="92"  />
<polygon fill="#00e479" points="50,38 62,59 38,59"  />
<circle cx="50" cy="52" fill="#00eefc" r="3.5"  />
<circle cx="8" cy="27" fill="#00eefc" r="3.5"  />
<circle cx="92" cy="27" fill="#00eefc" r="3.5"  />
<circle cx="92" cy="73" fill="#00e479" r="3.5"  />
<circle cx="8" cy="73" fill="#00e479" r="3.5"  />
</svg>
</div>
<div className="flex flex-col">
<div className="flex items-center gap-space-xs">
<span className="font-label-sm text-label-sm text-secondary bg-secondary/10 px-space-xs py-0.5 border border-secondary/20">ED25519 ENCLAVE SEAL</span>
<span className="font-label-sm text-label-sm text-tertiary bg-tertiary/10 px-space-xs py-0.5 border border-tertiary/20">AIRGAP VALID</span>
<span className="font-label-sm text-label-sm text-on-surface bg-surface-container px-space-xs py-0.5">RING-M3 ISOLATION</span>
</div>
<h1 className="font-headline-lg text-headline-lg text-on-surface uppercase tracking-tight mt-1">CONFIDENTIAL COMPUTING ATTESTATION</h1>
<p className="font-body-sm text-body-sm text-on-surface-variant font-mono">Zero-knowledge proof validation trace for real-time incident resolution (INC-104).</p>
</div>
</div>
<button
            onClick={() => handleValidateSignature()}
            className={`px-space-md py-space-sm font-label-md text-label-md tracking-widest uppercase transition-all shrink-0 flex items-center gap-1.5 cursor-pointer ${
              isValidated
                ? 'bg-tertiary text-on-tertiary shadow-[0_0_15px_rgba(0,228,121,0.4)] border border-tertiary'
                : 'bg-secondary/10 hover:bg-secondary text-secondary hover:text-on-secondary border border-secondary/40 shadow-[0_0_12px_rgba(0,238,252,0.15)]'
            }`}
          >
            <span className="material-symbols-outlined text-sm">{isValidated ? 'verified' : 'verified_user'}</span>
            <span>{isValidated ? 'SIGNATURE VALIDATED' : 'VALIDATE SIGNATURE'}</span>
          </button>
</div>
{/*  HARDWARE ENCLAVE MEMORY BOUNDARY MICRO-DIAGRAM (ENHANCEMENT 2)  */}
<div className="w-full my-space-sm p-space-sm bg-surface-container-lowest border border-outline-variant/40 flex flex-col gap-2">
<div className="flex items-center justify-between font-label-sm text-label-sm text-on-surface-variant uppercase">
<span className="flex items-center gap-1"><span className="w-1.5 h-1.5 bg-primary rounded-full"></span>HARDWARE MEMORY DOMAIN BOUNDARY</span>
<span className="text-tertiary font-mono">CONFIDENTIAL VM LAYER [SEV-SNP]</span>
</div>
<div className="grid grid-cols-1 md:grid-cols-11 items-stretch gap-1 text-center font-mono text-[10px]">
{/*  Left: Untrusted Host RAM  */}
<div className="md:col-span-5 hatch-pattern bg-surface-container-high/40 border border-error/30 p-2.5 flex flex-col justify-between">
<div className="flex items-center justify-between text-error font-bold tracking-wider">
<span className="flex items-center gap-1"><span className="material-symbols-outlined text-xs">shield_lock</span> UNTRUSTED HOST RAM</span>
<span className="bg-error-container/40 text-error px-1 py-0.5 text-[9px]">RESTRICTED</span>
</div>
<div className="py-2 text-on-surface-variant text-[11px] text-left">
Hypervisor Space / Ring 0 Prohibited • Host OS, KVM Kernel &amp; DMA devices locked out
</div>
<div className="font-label-sm text-label-sm text-error/80 text-left bg-black/40 px-1.5 py-0.5 border border-error/20 flex items-center justify-between">
<span>ADDR: 0x00000000_00000000 - 0x7FFFFFFF_FFFFFFFF</span>
<span>DMA: INHIBITED</span>
</div>
</div>
{/*  Center: Neon Hardware Isolation Barrier Line  */}
<div className="md:col-span-1 flex flex-col items-center justify-center bg-surface-container py-1 px-0.5 border-y md:border-y-0 md:border-x border-secondary/50 relative overflow-hidden">
<div className="w-full h-full flex flex-col items-center justify-center gap-1 text-secondary">
<span className="material-symbols-outlined text-sm animate-pulse">lock</span>
<span className="text-[8px] font-bold tracking-tighter uppercase writing-mode-vertical rotate-180 md:rotate-0 hidden md:inline text-center leading-tight">AIRGAP HARDWARE ISOLATION // ZERO DMA LEAKAGE</span>
<span className="text-[8px] font-bold tracking-tighter uppercase md:hidden text-center">AIRGAP BARRIER</span>
</div>
</div>
{/*  Right: Encrypted Enclave Memory  */}
<div className="md:col-span-5 bg-surface-container-high/60 border border-tertiary/40 p-2.5 flex flex-col justify-between shadow-[inset_0_0_15px_rgba(0,228,121,0.08)]">
<div className="flex items-center justify-between text-tertiary font-bold tracking-wider">
<span className="flex items-center gap-1"><span className="material-symbols-outlined text-xs">encrypted</span> ENCRYPTED ENCLAVE MEMORY</span>
<span className="bg-tertiary/20 text-tertiary px-1 py-0.5 text-[9px] border border-tertiary/40 glow-emerald">VMSA ACTIVE</span>
</div>
<div className="py-2 text-on-surface text-[11px] text-left">
AMD SEV-SNP / AES-256-XTS Hardware Shielded • Ephemeral C-bit encrypted bus
</div>
<div className="font-label-sm text-label-sm text-tertiary/90 text-left bg-black/40 px-1.5 py-0.5 border border-tertiary/20 flex items-center justify-between">
<span>ADDR: 0x80000000_00000000 [ISOLATED]</span>
<span className="font-bold text-secondary">C-BIT: ENABLED</span>
</div>
</div>
</div>
</div>
{/*  Attestation Parameter Grid  */}
<div className="grid grid-cols-1 md:grid-cols-2 gap-space-md pt-space-md bg-surface-container-lowest/80 p-space-md border border-surface-container-high/40">
<div className="flex flex-col gap-1">
<span className="font-label-sm text-label-sm text-on-surface-variant uppercase">PUBLIC KEY FINGERPRINT</span>
<div className="font-label-md text-label-md text-secondary tracking-wider flex items-center justify-between font-mono-code">
<span>ed25519:9f8a:4b21:c0de:7712:e82b7</span>
<span className="text-tertiary font-label-sm text-label-sm">[SECURE]</span>
</div>
</div>
<div className="flex flex-col gap-1">
<span className="font-label-sm text-label-sm text-on-surface-variant uppercase">ENCLAVE PCR0 HASH (SHA-384)</span>
<div className="font-label-md text-label-md text-on-surface tracking-wider truncate font-mono-code" title="a3b8c9d09f71295b9c08d132fa692b11e2f38d99c4a8f9435b80">
              a3b8c9d09f71295b9c08d132fa692b11e2f38d...
            </div>
</div>
<div className="flex flex-col gap-1">
<span className="font-label-sm text-label-sm text-on-surface-variant uppercase">HARDWARE SEED IDENTITY</span>
<div className="font-label-md text-label-md text-on-surface tracking-wider font-mono-code">
              HSM-TPM2.0-AMD-EPYC-9654-V7
            </div>
</div>
<div className="flex flex-col gap-1">
<span className="font-label-sm text-label-sm text-on-surface-variant uppercase">LEDGER BLOCK HEIGHT</span>
<div className="font-label-md text-label-md text-tertiary tracking-wider flex items-center gap-space-xs font-mono-code">
<span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
              #94,188,285 <span className="text-on-surface-variant font-label-sm text-label-sm">(FINALITY: 100%)</span>
</div>
</div>
</div>
</div>
{/*  Quick Metrics HUD Panel + ZK-SNARK GROTH16 PROOF VERIFICATION HUD (ENHANCEMENT 3)  */}
<div className="lg:col-span-4 bg-surface-container-low p-space-lg flex flex-col justify-between shadow-xl border border-surface-container-high/60">
<div>
<div className="flex items-center justify-between mb-space-md pb-space-xs border-b border-surface-container">
<div className="flex items-center gap-1.5">
<span className="material-symbols-outlined text-secondary text-sm">enhanced_encryption</span>
<span className="font-label-sm text-label-sm text-on-surface uppercase tracking-wider font-bold">TRUST &amp; ZK-SNARK HUD</span>
</div>
<span className="font-label-sm text-label-sm text-tertiary bg-tertiary/10 px-space-xs py-0.5 uppercase border border-tertiary/30 font-bold">SEAL_INTEGRITY: 99.999%</span>
</div>
{/*  Mathematical Bilinear Pairing Groth16 Card  */}
<div className="bg-surface-container-lowest p-space-sm border border-secondary/30 mb-space-md">
<div className="flex items-center justify-between text-[10px] font-label-sm text-on-surface-variant uppercase pb-1">
<span>ZK-SNARK GROTH16 PAIRING TEST</span>
<span className="text-tertiary font-bold">[VERIFIED]</span>
</div>
<div className="p-2 bg-black/60 border border-secondary/20 text-center font-mono text-[12px] text-secondary tracking-wide shadow-inner">
  e(A, B) = e(α, β) · e(C, δ) <span className="text-tertiary font-bold ml-1.5">[PASS]</span>
</div>
<div className="flex items-center justify-between text-[10px] font-mono text-on-surface-variant mt-1.5 px-0.5">
<span>Curve: <span className="text-on-surface">BN254 (alt_bn128)</span></span>
<span>Gas Equiv: <span className="text-secondary font-mono">194,220 gwei</span></span>
</div>
</div>
{/*  Cryptographic Telemetry Specs List  */}
<div className="flex flex-col gap-space-xs font-mono text-[11px]">
<div className="bg-surface-container p-2 flex items-center justify-between border-l-2 border-secondary">
<span className="text-on-surface-variant">QAP Constraints:</span>
<span className="text-secondary font-bold">42,109 Satisfied</span>
</div>
<div className="bg-surface-container p-2 flex items-center justify-between border-l-2 border-tertiary">
<span className="text-on-surface-variant">Verification Time:</span>
<span className="text-tertiary font-bold">1.1ms (BN254 curve)</span>
</div>
<div className="bg-surface-container p-2 flex items-center justify-between">
<span className="text-on-surface-variant">Signature Entropy:</span>
<span className="text-on-surface font-bold">7.9984 bits/byte</span>
</div>
<div className="bg-surface-container p-2 flex items-center justify-between">
<span className="text-on-surface-variant">Attestation Nonce:</span>
<span className="text-secondary font-mono font-bold">0x7F912EAA08B4</span>
</div>
<div className="bg-surface-container p-2 flex items-center justify-between">
<span className="text-on-surface-variant">Zero-Knowledge Root:</span>
<span className="text-tertiary font-bold">ZK-SNARK-GROTH16</span>
</div>
</div>
</div>
<div className="mt-space-md pt-space-sm border-t border-surface-container-high flex items-center justify-between font-label-sm text-label-sm">
<div className="flex items-center gap-1.5">
<span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
<span className="text-on-surface-variant">PROOF EMITTED</span>
</div>
<span className="font-label-md text-label-md text-on-surface font-mono">14:22:01.140 UTC</span>
</div>
</div>
</div>
{/*  2. SUB-500MS END-TO-END LATENCY BUDGET BAR WITH P99 VARIANCE SPARKLINES (ENHANCEMENT 4)  */}
<div className="w-full bg-surface-container-low p-space-lg shadow-xl flex flex-col gap-space-md border border-surface-container-high/60">
<div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-sm">
<div className="flex items-center gap-space-sm">
<span className="material-symbols-outlined text-secondary text-base">speed</span>
<span className="font-headline-sm text-headline-sm text-on-surface uppercase tracking-wider">SUB-500MS E2E LATENCY BUDGET VERIFICATION</span>
<span className="font-label-sm text-label-sm bg-tertiary/10 text-tertiary px-space-xs py-0.5 uppercase font-bold border border-tertiary/30">BUDGET MARGIN: 71.6%</span>
</div>
<div className="flex items-center gap-space-md">
<span className="font-label-md text-label-md text-on-surface-variant">ACTUAL: <span className="text-tertiary font-bold text-headline-sm font-headline-sm">142ms</span> / 500ms</span>
<span className="font-label-sm text-label-sm text-secondary bg-surface-container px-space-sm py-1 font-bold border border-secondary/30 glow-cyan">HEADROOM: +358ms (71.6% SAFE)</span>
</div>
</div>
{/*  Segmented Bar Visualization  */}
<div className="w-full bg-surface-container-lowest p-1.5 shadow-inner border border-surface-container-high/50">
<div className="w-full flex h-8 bg-surface-container-high overflow-hidden relative">
{/*  4ms / 500ms = 0.8% -> minimum width for visibility: 2.5%  */}
<div className="h-full bg-secondary flex items-center justify-center group relative cursor-pointer" style={{ width: '2.5%' }} title="Ingest: 4ms">
<span className="font-label-sm text-label-sm text-on-secondary hidden sm:inline font-bold">4</span>
</div>
{/*  48ms / 500ms = 9.6%  */}
<div className="h-full bg-secondary-fixed flex items-center justify-center group relative cursor-pointer" style={{ width: '10.5%' }} title="Hindsight Vector Recall: 48ms">
<span className="font-label-sm text-label-sm text-on-secondary hidden sm:inline font-bold">48ms</span>
</div>
{/*  32ms / 500ms = 6.4%  */}
<div className="h-full bg-tertiary-fixed flex items-center justify-center group relative cursor-pointer" style={{ width: '7.5%' }} title="Relevance Gate: 32ms">
<span className="font-label-sm text-label-sm text-on-tertiary hidden sm:inline font-bold">32ms</span>
</div>
{/*  54ms / 500ms = 10.8%  */}
<div className="h-full bg-primary flex items-center justify-center group relative cursor-pointer" style={{ width: '11.5%' }} title="Diagnosis &amp; Runbook: 54ms">
<span className="font-label-sm text-label-sm text-on-primary font-bold hidden sm:inline font-bold">54ms</span>
</div>
{/*  4ms / 500ms = 0.8% -> 2%  */}
<div className="h-full bg-tertiary flex items-center justify-center group relative cursor-pointer" style={{ width: '2%' }} title="Operator Approval: 4ms">
<span className="font-label-sm text-label-sm text-on-tertiary hidden sm:inline font-bold">4</span>
</div>
{/*  Remaining Budget Void (358ms = 71.6%)  */}
<div className="h-full bg-surface-container flex items-center justify-end px-space-sm relative" style={{ width: '66%' }}>
<div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,transparent,transparent_6px,rgba(255,255,255,0.02)_6px,rgba(255,255,255,0.02)_12px)]"></div>
<span className="font-label-sm text-label-sm text-on-surface-variant z-10 hidden md:inline font-mono">UNEXHAUSTED BUDGET: 358ms (71.6% SAFE)</span>
</div>
</div>
</div>
{/*  Segment Legend & Breakdown with Sub-Millisecond P99 Jitter Sparklines (ENHANCEMENT 4)  */}
<div className="grid grid-cols-2 md:grid-cols-5 gap-space-sm pt-space-xs font-label-sm text-label-sm">
{/*  1. Ingest  */}
<div className="bg-surface-container p-space-sm flex flex-col gap-1 border border-surface-container-high">
<div className="flex items-center gap-1.5">
<span className="w-2.5 h-2.5 bg-secondary"></span>
<span className="text-on-surface-variant uppercase font-bold">1. Ingest</span>
</div>
<div className="flex items-baseline justify-between">
<span className="text-on-surface font-bold text-headline-sm font-headline-sm">4ms</span>
<span className="text-[9px] font-mono text-tertiary">p99: 4.2ms (±0.2ms)</span>
</div>
<span className="text-on-surface-variant text-[10px] font-mono truncate">HMAC &amp; Payload Sanitize</span>
{/*  Sparkline 1: Flat low-variance line  */}
<div className="w-full h-5 mt-1 bg-surface-container-lowest p-0.5 border border-surface-container-high/40 flex items-center">
<svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 20">
<path d="M0,10 L15,10 L25,9 L35,11 L45,10 L60,10 L75,9.5 L85,10.5 L100,10" fill="none" stroke="#d3fbff" strokeWidth="1.8"  />
<circle cx="100" cy="10" fill="#d3fbff" r="2"  />
</svg>
</div>
</div>
{/*  2. Recall  */}
<div className="bg-surface-container p-space-sm flex flex-col gap-1 border border-surface-container-high">
<div className="flex items-center gap-1.5">
<span className="w-2.5 h-2.5 bg-secondary-fixed"></span>
<span className="text-on-surface-variant uppercase font-bold">2. Recall</span>
</div>
<div className="flex items-baseline justify-between">
<span className="text-on-surface font-bold text-headline-sm font-headline-sm">48ms</span>
<span className="text-[9px] font-mono text-secondary">p99: 49.8ms</span>
</div>
<span className="text-on-surface-variant text-[10px] font-mono truncate">1536-D Vector Lookup</span>
{/*  Sparkline 2: 1536-D Vector indexing curve  */}
<div className="w-full h-5 mt-1 bg-surface-container-lowest p-0.5 border border-surface-container-high/40 flex items-center">
<svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 20">
<path d="M0,17 Q25,16 45,8 T80,4 L100,4" fill="none" stroke="#7df4ff" strokeWidth="1.8"  />
<circle cx="100" cy="4" fill="#7df4ff" r="2"  />
</svg>
</div>
</div>
{/*  3. Rel Gate  */}
<div className="bg-surface-container p-space-sm flex flex-col gap-1 border border-surface-container-high">
<div className="flex items-center gap-1.5">
<span className="w-2.5 h-2.5 bg-tertiary-fixed"></span>
<span className="text-on-surface-variant uppercase font-bold">3. Rel Gate</span>
</div>
<div className="flex items-baseline justify-between">
<span className="text-on-surface font-bold text-headline-sm font-headline-sm">32ms</span>
<span className="text-[9px] font-mono text-tertiary">p99: 33.1ms</span>
</div>
<span className="text-on-surface-variant text-[10px] font-mono truncate">Cross-Attention Scorer</span>
{/*  Sparkline 3: Attention cycle waveform  */}
<div className="w-full h-5 mt-1 bg-surface-container-lowest p-0.5 border border-surface-container-high/40 flex items-center">
<svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 20">
<path d="M0,14 L20,13 L35,5 L50,15 L65,7 L80,10 L100,10" fill="none" stroke="#60ff99" strokeWidth="1.8"  />
<circle cx="100" cy="10" fill="#60ff99" r="2"  />
</svg>
</div>
</div>
{/*  4. Diagnosis  */}
<div className="bg-surface-container p-space-sm flex flex-col gap-1 border border-surface-container-high">
<div className="flex items-center gap-1.5">
<span className="w-2.5 h-2.5 bg-primary"></span>
<span className="text-on-surface-variant uppercase font-bold">4. Diagnosis</span>
</div>
<div className="flex items-baseline justify-between">
<span className="text-on-surface font-bold text-headline-sm font-headline-sm">54ms</span>
<span className="text-[9px] font-mono text-primary">p99: 55.4ms</span>
</div>
<span className="text-on-surface-variant text-[10px] font-mono truncate">Runbook Mapping &amp; Eval</span>
{/*  Sparkline 4: Canary validation step curve  */}
<div className="w-full h-5 mt-1 bg-surface-container-lowest p-0.5 border border-surface-container-high/40 flex items-center">
<svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 20">
<path d="M0,18 L30,18 L30,10 L65,10 L65,4 L100,4" fill="none" stroke="#ffb2ba" strokeWidth="1.8"  />
<circle cx="100" cy="4" fill="#ffb2ba" r="2"  />
</svg>
</div>
</div>
{/*  5. Approval  */}
<div className="bg-surface-container p-space-sm flex flex-col gap-1 border border-surface-container-high">
<div className="flex items-center gap-1.5">
<span className="w-2.5 h-2.5 bg-tertiary"></span>
<span className="text-on-surface-variant uppercase font-bold">5. Approval</span>
</div>
<div className="flex items-baseline justify-between">
<span className="text-on-surface font-bold text-headline-sm font-headline-sm">4ms</span>
<span className="text-[9px] font-mono text-tertiary">p99: 4.1ms</span>
</div>
<span className="text-on-surface-variant text-[10px] font-mono truncate">Airgap Ed25519 Sign</span>
{/*  Sparkline 5: Instant cryptographic lock pulse  */}
<div className="w-full h-5 mt-1 bg-surface-container-lowest p-0.5 border border-surface-container-high/40 flex items-center">
<svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 20">
<path d="M0,10 L45,10 L50,2 L55,18 L60,10 L100,10" fill="none" stroke="#00e479" strokeWidth="1.8"  />
<circle cx="100" cy="10" fill="#00e479" r="2"  />
</svg>
</div>
</div>
</div>
</div>
{/*  3. FIVE-STAGE DECISION MATRIX PIPELINE WITH MERKLE HASH-CHAINING (ENHANCEMENT 1)  */}
<div className="w-full bg-surface-container-low p-space-lg shadow-xl flex flex-col gap-space-lg border border-surface-container-high/60 relative overflow-hidden">
<div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-sm">
<div>
<div className="flex items-center gap-2">
<span className="font-label-sm text-label-sm text-secondary uppercase tracking-widest font-mono">ZERO-TRUST PIPELINE GRAPH</span>
<span className="font-label-sm text-label-sm px-space-xs py-0.5 bg-tertiary/10 text-tertiary border border-tertiary/30 font-bold uppercase glow-emerald">🔒 MERKLE CHAIN SEALED // ZERO-TAMPER LINK</span>
</div>
<h2 className="font-headline-md text-headline-md text-on-surface uppercase tracking-tight mt-1">5-STAGE CRYPTOGRAPHIC DECISION MATRIX</h2>
</div>
<div className="flex items-center gap-space-xs font-label-sm text-label-sm bg-surface-container px-space-sm py-1 border border-tertiary/30">
<span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
<span className="text-on-surface font-bold">ALL 5 MERKLE GATES ATTESTED</span>
</div>
</div>
{/*  Illuminated Merkle Conduit Bar (Horizontal Flow)  */}
<div className="hidden md:flex items-center justify-between px-space-md py-1 bg-surface-container-lowest border border-surface-container-high font-mono text-[10px] text-on-surface-variant relative">
<div className="absolute left-6 right-6 top-1/2 h-[2px] bg-gradient-to-r from-secondary via-tertiary to-secondary -translate-y-1/2 pointer-events-none opacity-40"></div>
<span className="bg-surface-container-lowest px-2 py-0.5 border border-secondary/40 text-secondary z-10 flex items-center gap-1"><span className="w-1.5 h-1.5 bg-secondary rounded-full"></span>ROOT: SHA256: 44e8bc19...</span>
<span className="material-symbols-outlined text-secondary text-xs z-10">east</span>
<span className="bg-surface-container-lowest px-2 py-0.5 border border-secondary/40 text-secondary z-10 font-bold">NODE 02: b71940ac...</span>
<span className="material-symbols-outlined text-tertiary text-xs z-10">east</span>
<span className="bg-surface-container-lowest px-2 py-0.5 border border-tertiary/40 text-tertiary z-10 font-bold">NODE 03: α = 0.987</span>
<span className="material-symbols-outlined text-primary text-xs z-10">east</span>
<span className="bg-surface-container-lowest px-2 py-0.5 border border-primary/40 text-primary z-10 font-bold">NODE 04: RB-PGBOUNCER-120</span>
<span className="material-symbols-outlined text-tertiary text-xs z-10">east</span>
<span className="bg-surface-container-lowest px-2 py-0.5 border border-tertiary/40 text-tertiary z-10 flex items-center gap-1"><span className="w-1.5 h-1.5 bg-tertiary rounded-full animate-pulse"></span>LEAF: SIG_ED25519_VALID</span>
</div>
{/*  Decision Matrix Horizontal Grid with Merkle Parent Chaining  */}
<div className="grid grid-cols-1 md:grid-cols-5 gap-gutter relative">
{/*  Stage 1  */}
<div className="bg-surface-container p-space-md flex flex-col justify-between relative shadow-md border-t-2 border-secondary">
<div className="flex flex-col gap-space-xs">
<div className="flex items-center justify-between">
<span className="font-label-sm text-label-sm text-secondary bg-surface-container-lowest px-1 py-0.5 font-bold">STAGE 01</span>
<span className="font-label-sm text-label-sm text-tertiary font-mono">4ms</span>
</div>
<h3 className="font-headline-sm text-headline-sm text-on-surface uppercase mt-space-xs">Ingestion</h3>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">Alert Intake Webhook</span>
<div className="mt-space-sm p-space-xs bg-surface-container-lowest flex flex-col gap-1 border border-surface-container-high">
<span className="font-label-sm text-label-sm text-on-surface-variant">INPUT PAYLOAD:</span>
<p className="font-label-sm text-label-sm text-on-surface font-mono truncate">p99_latency &gt; 2500ms pool=pg</p>
<span className="font-label-sm text-label-sm text-on-surface-variant mt-1">HMAC SHA256:</span>
<p className="font-label-sm text-label-sm text-secondary font-mono truncate">44e8bc19ff42...</p>
</div>
{/*  Merkle Parent Link Connector  */}
<div className="mt-space-xs p-1 bg-secondary/10 border-l border-secondary font-mono text-[9px] text-secondary flex items-center justify-between">
<span>MERKLE: GENESIS ROOT</span>
<span className="text-tertiary font-bold">[OK]</span>
</div>
</div>
<div className="mt-space-md pt-space-xs flex items-center justify-between border-t border-surface-container-high/60">
<span className="font-label-sm text-label-sm text-tertiary uppercase font-bold">[VERIFIED]</span>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">14:22:01.002</span>
</div>
</div>
{/*  Stage 2  */}
<div className="bg-surface-container p-space-md flex flex-col justify-between relative shadow-md border-t-2 border-secondary-fixed">
<div className="flex flex-col gap-space-xs">
<div className="flex items-center justify-between">
<span className="font-label-sm text-label-sm text-secondary bg-surface-container-lowest px-1 py-0.5 font-bold">STAGE 02</span>
<span className="font-label-sm text-label-sm text-tertiary font-mono">48ms</span>
</div>
<h3 className="font-headline-sm text-headline-sm text-on-surface uppercase mt-space-xs">Hindsight Query</h3>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">Vector Space Recall</span>
<div className="mt-space-sm p-space-xs bg-surface-container-lowest flex flex-col gap-1 border border-surface-container-high">
<span className="font-label-sm text-label-sm text-on-surface-variant">TARGET VECTOR:</span>
<p className="font-label-sm text-label-sm text-on-surface font-mono truncate">INC-042 (Cosine: 0.994)</p>
<span className="font-label-sm text-label-sm text-on-surface-variant mt-1">EMBED CHECKSUM:</span>
<p className="font-label-sm text-label-sm text-secondary font-mono truncate">b71940ac29d1...</p>
</div>
{/*  Merkle Parent Link Connector  */}
<div className="mt-space-xs p-1 bg-secondary/10 border-l border-secondary font-mono text-[9px] text-secondary flex items-center justify-between">
<span className="truncate">PARENT: 44e8bc19 → b71940ac</span>
<span className="text-tertiary font-bold">√</span>
</div>
</div>
<div className="mt-space-md pt-space-xs flex items-center justify-between border-t border-surface-container-high/60">
<span className="font-label-sm text-label-sm text-tertiary uppercase font-bold">[RETRIEVED]</span>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">14:22:01.050</span>
</div>
</div>
{/*  Stage 3  */}
<div className="bg-surface-container p-space-md flex flex-col justify-between relative shadow-md border-t-2 border-tertiary-fixed">
<div className="flex flex-col gap-space-xs">
<div className="flex items-center justify-between">
<span className="font-label-sm text-label-sm text-secondary bg-surface-container-lowest px-1 py-0.5 font-bold">STAGE 03</span>
<span className="font-label-sm text-label-sm text-tertiary font-mono">32ms</span>
</div>
<h3 className="font-headline-sm text-headline-sm text-on-surface uppercase mt-space-xs">Relevance Gate</h3>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">Decoy Suppression</span>
<div className="mt-space-sm p-space-xs bg-surface-container-lowest flex flex-col gap-1 border border-surface-container-high">
<span className="font-label-sm text-label-sm text-on-surface-variant">FILTER VERDICT:</span>
<p className="font-label-sm text-label-sm text-tertiary font-mono truncate">1 Passed / 3 Suppressed</p>
<span className="font-label-sm text-label-sm text-on-surface-variant mt-1">ATTENTION COEF:</span>
<p className="font-label-sm text-label-sm text-secondary font-mono truncate">α = 0.987 (Safe)</p>
</div>
{/*  Merkle Parent Link Connector  */}
<div className="mt-space-xs p-1 bg-tertiary/10 border-l border-tertiary font-mono text-[9px] text-tertiary flex items-center justify-between">
<span className="truncate">PARENT: b71940ac → α=0.987</span>
<span className="text-tertiary font-bold">√</span>
</div>
</div>
<div className="mt-space-md pt-space-xs flex items-center justify-between border-t border-surface-container-high/60">
<span className="font-label-sm text-label-sm text-tertiary uppercase font-bold">[CONFIRMED]</span>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">14:22:01.082</span>
</div>
</div>
{/*  Stage 4  */}
<div className="bg-surface-container p-space-md flex flex-col justify-between relative shadow-md border-t-2 border-primary">
<div className="flex flex-col gap-space-xs">
<div className="flex items-center justify-between">
<span className="font-label-sm text-label-sm text-secondary bg-surface-container-lowest px-1 py-0.5 font-bold">STAGE 04</span>
<span className="font-label-sm text-label-sm text-tertiary font-mono">54ms</span>
</div>
<h3 className="font-headline-sm text-headline-sm text-on-surface uppercase mt-space-xs">Diagnosis</h3>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">Runbook Resolver</span>
<div className="mt-space-sm p-space-xs bg-surface-container-lowest flex flex-col gap-1 border border-surface-container-high">
<span className="font-label-sm text-label-sm text-on-surface-variant">ACTION SPEC:</span>
<p className="font-label-sm text-label-sm text-on-surface font-mono truncate">RB-PGBOUNCER-120</p>
<span className="font-label-sm text-label-sm text-on-surface-variant mt-1">CANARY SIMULATION:</span>
<p className="font-label-sm text-label-sm text-tertiary font-mono truncate">0 Collisions / Pass</p>
</div>
{/*  Merkle Parent Link Connector  */}
<div className="mt-space-xs p-1 bg-primary/10 border-l border-primary font-mono text-[9px] text-primary flex items-center justify-between">
<span className="truncate">PARENT: α=0.987 → RB-PGB-120</span>
<span className="text-tertiary font-bold">√</span>
</div>
</div>
<div className="mt-space-md pt-space-xs flex items-center justify-between border-t border-surface-container-high/60">
<span className="font-label-sm text-label-sm text-tertiary uppercase font-bold">[SYNTHESIZED]</span>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">14:22:01.136</span>
</div>
</div>
{/*  Stage 5  */}
<div className="bg-surface-container p-space-md flex flex-col justify-between relative shadow-md border-t-2 border-tertiary">
<div className="flex flex-col gap-space-xs">
<div className="flex items-center justify-between">
<span className="font-label-sm text-label-sm text-tertiary bg-surface-container-lowest px-1 py-0.5 font-bold">STAGE 05</span>
<span className="font-label-sm text-label-sm text-tertiary font-mono">4ms</span>
</div>
<h3 className="font-headline-sm text-headline-sm text-on-surface uppercase mt-space-xs">Approval</h3>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">Operator Handshake</span>
<div className="mt-space-sm p-space-xs bg-surface-container-lowest flex flex-col gap-1 border border-surface-container-high">
<span className="font-label-sm text-label-sm text-on-surface-variant">ENCLAVE COMMIT:</span>
<p className="font-label-sm text-label-sm text-tertiary font-mono truncate">SIG_ED25519_VALID</p>
<span className="font-label-sm text-label-sm text-on-surface-variant mt-1">LEDGER TX:</span>
<p className="font-label-sm text-label-sm text-secondary font-mono truncate">0x9c41...ff01a</p>
</div>
{/*  Merkle Parent Link Connector  */}
<div className="mt-space-xs p-1 bg-tertiary/10 border-l border-tertiary font-mono text-[9px] text-tertiary flex items-center justify-between">
<span className="truncate">PARENT: RB-120 → SEAL_ED25519</span>
<span className="text-tertiary font-bold glow-emerald">√ SEALED</span>
</div>
</div>
<div className="mt-space-md pt-space-xs flex items-center justify-between border-t border-surface-container-high/60">
<span className="font-label-sm text-label-sm text-tertiary uppercase font-bold">[EXECUTED]</span>
<span className="font-label-sm text-label-sm text-on-surface-variant font-mono">14:22:01.140</span>
</div>
</div>
</div>
</div>
{/*  4. MONOSPACE ATTESTED PROVENANCE AUDIT LOG WITH HEX OFFSETS & CATEGORY TABS (ENHANCEMENT 5)  */}
<div className="w-full bg-surface-container-low p-space-lg shadow-xl flex flex-col gap-space-md border border-surface-container-high/60">
{/*  Log Controls and Header  */}
<div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-space-md">
<div>
<div className="flex items-center gap-space-xs">
<span className="font-label-sm text-label-sm text-on-surface-variant uppercase font-mono">RAW ATTESTATION RECORD</span>
<span className="w-1.5 h-1.5 bg-tertiary rounded-full animate-pulse"></span>
<span className="font-label-sm text-label-sm text-tertiary uppercase font-bold">IMMUTABLE LOG // KERNEL eBPF PROVE</span>
</div>
<h2 className="font-headline-md text-headline-md text-on-surface uppercase tracking-tight">ENCLAVE PROVENANCE AUDIT TRAIL</h2>
</div>
{/*  Action Buttons  */}
<div className="flex flex-wrap items-center gap-space-sm">
<button className="bg-surface-container hover:bg-surface-container-high text-on-surface px-space-sm py-1.5 font-label-sm text-label-sm uppercase tracking-wider transition-colors flex items-center gap-1 border border-surface-container-high" id="downloadBundleBtn">
<span className="material-symbols-outlined text-sm">download</span>
            Bundle .tar.gz
          </button>
<button className="bg-secondary/10 hover:bg-secondary text-secondary hover:text-on-secondary border border-secondary/40 px-space-sm py-1.5 font-label-sm text-label-sm uppercase tracking-wider transition-colors flex items-center gap-1 glow-cyan" id="verifySigBtn">
<span className="material-symbols-outlined text-sm">verified_user</span>
            Verify Signature
          </button>
<button className="bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface px-space-sm py-1.5 font-label-sm text-label-sm uppercase tracking-wider transition-colors flex items-center gap-1 border border-surface-container-high" id="exportJsonBtn">
<span className="material-symbols-outlined text-sm">data_object</span>
            Export JSON
          </button>
</div>
</div>
{/*  Terminal Category Tabs (ENHANCEMENT 5)  */}
<div className="flex items-center gap-2 border-b border-surface-container pb-2 pt-1 font-mono text-xs overflow-x-auto">
<button className="px-space-sm py-1 bg-surface-container-high text-tertiary border-b-2 border-tertiary font-bold tracking-wider">[ALL (8)]</button>
<button className="px-space-sm py-1 bg-surface-container-lowest text-on-surface-variant hover:text-on-surface transition-colors tracking-wider">[SECURITY ATTESTATIONS (3)]</button>
<button className="px-space-sm py-1 bg-surface-container-lowest text-on-surface-variant hover:text-on-surface transition-colors tracking-wider">[RUNBOOK EXECUTION (2)]</button>
<button className="px-space-sm py-1 bg-surface-container-lowest text-on-surface-variant hover:text-on-surface transition-colors tracking-wider">[EXPORTS (1)]</button>
<span className="ml-auto text-[10px] text-on-surface-variant font-mono hidden sm:inline">RING BUFFER: 8/1024 FRAMES CAPTURED</span>
</div>
{/*  High-Density Terminal Audit Frame with Hex Offsets (ENHANCEMENT 5)  */}
<div className="w-full bg-surface-container-lowest p-space-md font-mono text-body-sm leading-relaxed overflow-x-auto shadow-inner flex flex-col gap-2.5 border border-surface-container-high/40">
<div className="flex items-center justify-between pb-space-xs text-on-surface-variant font-label-sm text-label-sm border-b border-surface-container">
<span className="text-secondary font-mono">STREAM ID: audit-stream-us-east-prod-20250228-0941 // eBPF ATTESTOR 4.19</span>
<span className="text-on-surface-variant font-mono">FORMAT: ED25519-ENCLAVE-V2 // SEV-SNP C-BIT=1</span>
</div>
{/*  Entry 0x0000  */}
<div className="flex items-start justify-between gap-space-sm group hover:bg-surface-container/40 p-1 rounded transition-colors">
<div className="flex items-start gap-space-sm">
<span className="text-secondary/60 shrink-0 font-mono text-[11px] select-none">0x0000</span>
<span className="text-on-surface-variant shrink-0 font-label-sm text-label-sm">[14:22:01.002]</span>
<span className="text-secondary shrink-0 font-label-sm text-label-sm font-bold">INGEST:</span>
<span className="text-on-surface">HMAC alert payload validated (SHA-256: 44e8bc19...8831). Source: Prometheus-Alertmanager-03 via TLS 1.3 mutual auth.</span>
</div>
<div className="shrink-0 flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
<button className="px-1.5 py-0.5 bg-surface-container-high hover:bg-surface-container text-[9px] text-secondary font-mono border border-secondary/30">+ JSON PAYLOAD</button>
<span className="px-1 py-0.5 bg-tertiary/10 text-tertiary text-[9px] font-mono border border-tertiary/20">VERIFIED OK</span>
</div>
</div>
{/*  Entry 0x0010  */}
<div className="flex items-start justify-between gap-space-sm group hover:bg-surface-container/40 p-1 rounded transition-colors">
<div className="flex items-start gap-space-sm">
<span className="text-secondary/60 shrink-0 font-mono text-[11px] select-none">0x0010</span>
<span className="text-on-surface-variant shrink-0 font-label-sm text-label-sm">[14:22:01.018]</span>
<span className="text-secondary shrink-0 font-label-sm text-label-sm font-bold">VECTORIZE:</span>
<span className="text-on-surface">Telemetry tokenized (384 tokens). Vector projection generated in SGX enclave memory buffer.</span>
</div>
<div className="shrink-0 flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
<button className="px-1.5 py-0.5 bg-surface-container-high hover:bg-surface-container text-[9px] text-secondary font-mono border border-secondary/30">+ JSON PAYLOAD</button>
<span className="px-1 py-0.5 bg-tertiary/10 text-tertiary text-[9px] font-mono border border-tertiary/20">VERIFIED OK</span>
</div>
</div>
{/*  Entry 0x0020  */}
<div className="flex items-start justify-between gap-space-sm group hover:bg-surface-container/40 p-1 rounded transition-colors">
<div className="flex items-start gap-space-sm">
<span className="text-secondary/60 shrink-0 font-mono text-[11px] select-none">0x0020</span>
<span className="text-on-surface-variant shrink-0 font-label-sm text-label-sm">[14:22:01.050]</span>
<span className="text-tertiary shrink-0 font-label-sm text-label-sm font-bold">HINDSIGHT:</span>
<span className="text-on-surface">Cosine similarity match found: <span className="text-secondary font-bold">INC-042 (Cosine: 0.9942)</span> in partition `prod-db-us-east-1`. Secondary candidate INC-019 (Cosine: 0.8124).</span>
</div>
<div className="shrink-0 flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
<button className="px-1.5 py-0.5 bg-surface-container-high hover:bg-surface-container text-[9px] text-secondary font-mono border border-secondary/30">+ JSON PAYLOAD</button>
<span className="px-1 py-0.5 bg-tertiary/10 text-tertiary text-[9px] font-mono border border-tertiary/20">VERIFIED OK</span>
</div>
</div>
{/*  Entry 0x0030  */}
<div className="flex items-start justify-between gap-space-sm group hover:bg-surface-container/40 p-1 rounded transition-colors">
<div className="flex items-start gap-space-sm">
<span className="text-secondary/60 shrink-0 font-mono text-[11px] select-none">0x0030</span>
<span className="text-on-surface-variant shrink-0 font-label-sm text-label-sm">[14:22:01.082]</span>
<span className="text-primary shrink-0 font-label-sm text-label-sm font-bold">REL_GATE:</span>
<span className="text-on-surface">Decoy Candidate #0884 suppressed (Cross-attention mismatch score: 0.880 &gt; threshold 0.150). False positive filtered.</span>
</div>
<div className="shrink-0 flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
<button className="px-1.5 py-0.5 bg-surface-container-high hover:bg-surface-container text-[9px] text-secondary font-mono border border-secondary/30">+ JSON PAYLOAD</button>
<span className="px-1 py-0.5 bg-tertiary/10 text-tertiary text-[9px] font-mono border border-tertiary/20">VERIFIED OK</span>
</div>
</div>
{/*  Entry 0x0040  */}
<div className="flex items-start justify-between gap-space-sm group hover:bg-surface-container/40 p-1 rounded transition-colors">
<div className="flex items-start gap-space-sm">
<span className="text-secondary/60 shrink-0 font-mono text-[11px] select-none">0x0040</span>
<span className="text-on-surface-variant shrink-0 font-label-sm text-label-sm">[14:22:01.096]</span>
<span className="text-secondary shrink-0 font-label-sm text-label-sm font-bold">RUNBOOK_MAP:</span>
<span className="text-on-surface">Candidate remediation loaded: <span className="text-tertiary font-bold">RB-PGBOUNCER-POOL-120</span>. Hash: 3e9d81fc20b... Canary rollback safe.</span>
</div>
<div className="shrink-0 flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
<button className="px-1.5 py-0.5 bg-surface-container-high hover:bg-surface-container text-[9px] text-secondary font-mono border border-secondary/30">+ JSON PAYLOAD</button>
<span className="px-1 py-0.5 bg-tertiary/10 text-tertiary text-[9px] font-mono border border-tertiary/20">VERIFIED OK</span>
</div>
</div>
{/*  Entry 0x0050  */}
<div className="flex items-start justify-between gap-space-sm group hover:bg-surface-container/40 p-1 rounded transition-colors">
<div className="flex items-start gap-space-sm">
<span className="text-secondary/60 shrink-0 font-mono text-[11px] select-none">0x0050</span>
<span className="text-on-surface-variant shrink-0 font-label-sm text-label-sm">[14:22:01.136]</span>
<span className="text-secondary shrink-0 font-label-sm text-label-sm font-bold">DIAGNOSIS:</span>
<span className="text-on-surface">Automated execution parameters compiled. Target pods: `pgbouncer-rw-pool-[a,b,c]`. Connection ceiling dynamically lifted +150 conns.</span>
</div>
<div className="shrink-0 flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
<button className="px-1.5 py-0.5 bg-surface-container-high hover:bg-surface-container text-[9px] text-secondary font-mono border border-secondary/30">+ JSON PAYLOAD</button>
<span className="px-1 py-0.5 bg-tertiary/10 text-tertiary text-[9px] font-mono border border-tertiary/20">VERIFIED OK</span>
</div>
</div>
{/*  Entry 0x0060  */}
<div className="flex items-start justify-between gap-space-sm group hover:bg-surface-container/40 p-1 rounded transition-colors">
<div className="flex items-start gap-space-sm">
<span className="text-secondary/60 shrink-0 font-mono text-[11px] select-none">0x0060</span>
<span className="text-on-surface-variant shrink-0 font-label-sm text-label-sm">[14:22:01.138]</span>
<span className="text-tertiary shrink-0 font-label-sm text-label-sm font-bold">OPERATOR_ACK:</span>
<span className="text-on-surface">Autonomous enclave gate verified clearance. Policy ID: `POL-ZERO-DOWNTIME-INFRA` matches criteria.</span>
</div>
<div className="shrink-0 flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
<button className="px-1.5 py-0.5 bg-surface-container-high hover:bg-surface-container text-[9px] text-secondary font-mono border border-secondary/30">+ JSON PAYLOAD</button>
<span className="px-1 py-0.5 bg-tertiary/10 text-tertiary text-[9px] font-mono border border-tertiary/20">VERIFIED OK</span>
</div>
</div>
{/*  Entry 0x0070 (Final Seal)  */}
<div className="flex items-start justify-between gap-space-sm bg-tertiary/10 p-1.5 border border-tertiary/40 group">
<div className="flex items-start gap-space-sm">
<span className="text-tertiary shrink-0 font-mono text-[11px] font-bold">0x0070</span>
<span className="text-on-surface-variant shrink-0 font-label-sm text-label-sm">[14:22:01.140]</span>
<span className="text-tertiary shrink-0 font-label-sm text-label-sm font-bold">ENCLAVE_SEAL:</span>
<span className="text-tertiary font-bold font-mono">ED25519 signature committed to ledger at Block #94,188,285. Audit digest: `0x8fba...411e`. Cycle completed in 142ms.</span>
</div>
<div className="shrink-0 flex items-center gap-1">
<button className="px-1.5 py-0.5 bg-surface-container-high hover:bg-surface-container text-[9px] text-secondary font-mono border border-secondary/30">+ JSON PAYLOAD</button>
<span className="px-1.5 py-0.5 bg-tertiary text-on-tertiary text-[9px] font-mono font-bold glow-emerald">SIG SEALED</span>
</div>
</div>
</div>
{/*  Log Micro-Summary Footer  */}
<div className="flex flex-wrap items-center justify-between text-on-surface-variant font-label-sm text-label-sm gap-space-sm pt-space-xs border-t border-surface-container">
<div className="flex items-center gap-space-md">
<span>ENTRIES: 8 RECORDED</span>
<span className="text-outline">|</span>
<span>TAMPER STATUS: <span className="text-tertiary font-bold">SEALED / ZERO COMPROMISE</span></span>
<span className="text-outline">|</span>
<span>PROOF EXPIRY: 71h 59m REMAINING</span>
<span className="text-outline">|</span>
<span>eBPF KERNEL PROBES: <span className="text-secondary font-mono font-bold">ACTIVE (0 DROPS)</span></span>
</div>
<div className="text-on-surface-variant">
          NODE: <span className="text-on-surface font-mono">enclave-worker-us-east-4a</span>
</div>
</div>
</div>
</div>

</div></main>
    </div>
  );
};
