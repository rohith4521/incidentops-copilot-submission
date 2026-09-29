import React, { useEffect, useRef, useState } from 'react';
import { X, ShieldCheck, Database, Hash, Calendar, Cpu, Layers } from 'lucide-react';

export interface MemoryNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  label: string;
  type: 'incident' | 'cause' | 'runbook' | 'decoy';
  details?: {
    summary: string;
    provenanceHash: string;
    retainedDate: string;
    author: string;
    cosineScore: number;
    relevanceVerdict: 'ACCEPTED' | 'REJECTED' | 'PROVEN';
    runbookRef?: string;
  };
}

interface SpatialMemoryCanvasProps {
  onSelectNode?: (node: MemoryNode) => void;
  selectedNodeId?: string | null;
}

export const SpatialMemoryCanvas: React.FC<SpatialMemoryCanvasProps> = ({ onSelectNode, selectedNodeId }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [activeNode, setActiveNode] = useState<MemoryNode | null>(null);
  const nodesRef = useRef<MemoryNode[]>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || window.innerWidth || 1200);
    let height = (canvas.height = canvas.parentElement?.clientHeight || window.innerHeight - 80 || 700);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth || 1200;
      height = canvas.height = canvas.parentElement.clientHeight || 700;
    };
    window.addEventListener('resize', handleResize);

    const mouse = { x: -1000, y: -1000, radius: 120 };

    // Initial curated nodes
    const initialNodes: MemoryNode[] = [
      {
        id: 'inc-104',
        x: width * 0.45,
        y: height * 0.35,
        vx: 0.15,
        vy: -0.08,
        radius: 9,
        label: 'INC-104: PgBouncer 504',
        type: 'incident',
        details: {
          summary: 'Client connections exhausted under peak traffic. Default pool_size=20 saturated.',
          provenanceHash: 'sha256:7b9f84a1e948c201a0df27b8764098231',
          retainedDate: '2026-03-14 14:22:08 UTC',
          author: 'sre-incidentops-core',
          cosineScore: 0.942,
          relevanceVerdict: 'ACCEPTED',
          runbookRef: 'RB-PGBOUNCER-POOL-120',
        },
      },
      {
        id: 'rc-104',
        x: width * 0.38,
        y: height * 0.52,
        vx: -0.1,
        vy: 0.12,
        radius: 7,
        label: 'Cause: Pool Ceiling Saturation',
        type: 'cause',
        details: {
          summary: 'PgBouncer connection pool ceiling hit during spike in API checkout workers.',
          provenanceHash: 'sha256:3a8901fc82b794101e9a22d76504a9190',
          retainedDate: '2026-03-14 14:38:15 UTC',
          author: 'hindsight-synthesizer',
          cosineScore: 0.918,
          relevanceVerdict: 'PROVEN',
        },
      },
      {
        id: 'rb-104',
        x: width * 0.55,
        y: height * 0.55,
        vx: 0.08,
        vy: 0.09,
        radius: 7,
        label: 'RB-PGBOUNCER-POOL-120',
        type: 'runbook',
        details: {
          summary: 'Dynamically scale PgBouncer max_client_conn from 100 to 300 and bounce pooler daemon.',
          provenanceHash: 'sha256:889ec12a0149021bdfc0028a7e0892214',
          retainedDate: '2026-03-14 14:45:00 UTC',
          author: 'human-verifier:alex.m',
          cosineScore: 0.895,
          relevanceVerdict: 'PROVEN',
          runbookRef: 'RB-PGBOUNCER-POOL-120',
        },
      },
      {
        id: 'decoy-884',
        x: width * 0.68,
        y: height * 0.28,
        vx: -0.14,
        vy: -0.07,
        radius: 6,
        label: 'Decoy #884: Stripe Gateway 504',
        type: 'decoy',
        details: {
          summary: 'External payment partner outage. High semantic similarity (504 gateway) but zero internal pool saturation correlation.',
          provenanceHash: 'sha256:d82e11894bfae929841c28f1104e76812',
          retainedDate: '2025-11-02 09:12:44 UTC',
          author: 'external-decoy-generator',
          cosineScore: 0.812,
          relevanceVerdict: 'REJECTED',
        },
      },
      {
        id: 'inc-108',
        x: width * 0.25,
        y: height * 0.32,
        vx: 0.12,
        vy: -0.11,
        radius: 8,
        label: 'INC-108: Redis TLS Handshake',
        type: 'incident',
        details: {
          summary: 'Cache nodes rejecting TLS handshakes after CA certificate auto-rotation expired.',
          provenanceHash: 'sha256:5502cba0431289fe182049e91823746a8',
          retainedDate: '2026-05-18 20:05:19 UTC',
          author: 'sre-incidentops-core',
          cosineScore: 0.887,
          relevanceVerdict: 'ACCEPTED',
          runbookRef: 'RB-REDIS-TLS-ROTATE',
        },
      },
      {
        id: 'rb-108',
        x: width * 0.20,
        y: height * 0.48,
        vx: -0.09,
        vy: 0.08,
        radius: 6,
        label: 'RB-REDIS-TLS-ROTATE',
        type: 'runbook',
        details: {
          summary: 'Reload Redis TLS trust bundles across all cluster replicas and issue client sync.',
          provenanceHash: 'sha256:1049ea2387df10bce427a8e992147ac00',
          retainedDate: '2026-05-18 20:22:40 UTC',
          author: 'human-verifier:david.k',
          cosineScore: 0.871,
          relevanceVerdict: 'PROVEN',
          runbookRef: 'RB-REDIS-TLS-ROTATE',
        },
      },
      {
        id: 'inc-112',
        x: width * 0.78,
        y: height * 0.62,
        vx: 0.08,
        vy: -0.09,
        radius: 8,
        label: 'INC-112: Inventory OOMKilled',
        type: 'incident',
        details: {
          summary: 'Novel pod eviction crash loop caused by unexpected JSON deserialization memory spike.',
          provenanceHash: 'sha256:f489b0227189c4048ea33910c28372481',
          retainedDate: '2026-09-29 18:40:12 UTC',
          author: 'oncall-sre',
          cosineScore: 0.324,
          relevanceVerdict: 'ACCEPTED',
          runbookRef: 'RB-K8S-SCALE-LIMITS',
        },
      },
    ];

    // Add 20 extra realistic ambient memory nodes to reach ~28 nodes
    const topics = [
      { label: 'Mem #204: Kafka Lag Partition 12', type: 'cause' as const },
      { label: 'Mem #319: Envoy Upstream RST', type: 'cause' as const },
      { label: 'Mem #402: DNS Thrashing CoreDNS', type: 'cause' as const },
      { label: 'Mem #518: Gunicorn Worker Timeout', type: 'cause' as const },
      { label: 'Mem #611: Postgres WAL Disk Spill', type: 'cause' as const },
      { label: 'RB-K8S-ROLLOUT-RESTART', type: 'runbook' as const },
      { label: 'RB-INGRESS-DRAIN-503', type: 'runbook' as const },
      { label: 'RB-KAFKA-CONSUMER-REBALANCE', type: 'runbook' as const },
      { label: 'Decoy #411: BGP Flap at Transit', type: 'decoy' as const },
      { label: 'Decoy #702: Third-Party Auth Downtime', type: 'decoy' as const },
      { label: 'Decoy #921: Cloudflare RayID Spike', type: 'decoy' as const },
      { label: 'Mem #733: Memcached Out of Slabs', type: 'cause' as const },
      { label: 'Mem #820: JVM GC Pause 14s', type: 'cause' as const },
      { label: 'Mem #909: Istio Sidecar Leak', type: 'cause' as const },
      { label: 'RB-JVM-HEAP-DUMP-RESTART', type: 'runbook' as const },
      { label: 'RB-POSTGRES-VACUUM-ANALYZE', type: 'runbook' as const },
      { label: 'Mem #102: Elasticsearch Shard Limit', type: 'cause' as const },
      { label: 'Decoy #633: Client-Side Adblock Reject', type: 'decoy' as const },
      { label: 'Mem #445: Nginx File Descriptor Exhaustion', type: 'cause' as const },
      { label: 'RB-NGINX-WORKER-RELOAD', type: 'runbook' as const },
    ];

    topics.forEach((t, i) => {
      initialNodes.push({
        id: `ambient-${i}`,
        x: Math.random() * (width - 100) + 50,
        y: Math.random() * (height - 100) + 50,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: t.type === 'runbook' ? 5 : t.type === 'decoy' ? 4 : 5,
        label: t.label,
        type: t.type,
        details: {
          summary: `Continuous memory artifact retained from historical telemetry. Classified as ${t.type.toUpperCase()}.`,
          provenanceHash: `sha256:${Math.random().toString(16).substring(2, 10)}${Math.random().toString(16).substring(2, 10)}`,
          retainedDate: `2026-0${(i % 8) + 1}-1${(i % 9)} 1${i}:22:00 UTC`,
          author: t.type === 'decoy' ? 'decoy-rejection-filter' : 'hindsight-engine',
          cosineScore: t.type === 'decoy' ? 0.76 : 0.88,
          relevanceVerdict: t.type === 'decoy' ? 'REJECTED' : 'ACCEPTED',
          runbookRef: t.type === 'runbook' ? t.label : undefined,
        },
      });
    });

    nodesRef.current = initialNodes;

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    };

    const onClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      let clicked: MemoryNode | null = null;
      for (const node of nodesRef.current) {
        const d = Math.hypot(node.x - clickX, node.y - clickY);
        if (d <= node.radius + 8) {
          clicked = node;
          break;
        }
      }

      if (clicked) {
        setActiveNode(clicked);
        if (onSelectNode) onSelectNode(clicked);
      }
    };

    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('click', onClick);

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Deep subtle space grid
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
      ctx.lineWidth = 1;
      const gridSize = 60;
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      const nodes = nodesRef.current;

      // Connect nodes with elastic catenary strings
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 190) {
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);

            // Cursor deflection on string midpoint
            const midX = (nodes[i].x + nodes[j].x) / 2;
            const midY = (nodes[i].y + nodes[j].y) / 2;
            const mDist = Math.hypot(mouse.x - midX, mouse.y - midY);

            if (mDist < mouse.radius) {
              const angle = Math.atan2(midY - mouse.y, midX - mouse.x);
              const force = (mouse.radius - mDist) * 0.55;
              ctx.quadraticCurveTo(midX + Math.cos(angle) * force, midY + Math.sin(angle) * force, nodes[j].x, nodes[j].y);
            } else {
              ctx.lineTo(nodes[j].x, nodes[j].y);
            }

            const isDecoy = nodes[i].type === 'decoy' || nodes[j].type === 'decoy';
            const opacity = Math.max(0.04, (1 - dist / 190) * (isDecoy ? 0.22 : 0.35));
            ctx.strokeStyle = isDecoy ? `rgba(239, 68, 68, ${opacity})` : `rgba(0, 240, 255, ${opacity})`;
            ctx.lineWidth = isDecoy ? 1 : 1.4;
            ctx.stroke();
          }
        }
      }

      // Update and draw nodes
      nodes.forEach((node) => {
        node.x += node.vx;
        node.y += node.vy;

        // Soft elastic boundaries
        if (node.x < 30) {
          node.x = 30;
          node.vx *= -1;
        } else if (node.x > width - 30) {
          node.x = width - 30;
          node.vx *= -1;
        }

        if (node.y < 30) {
          node.y = 30;
          node.vy *= -1;
        } else if (node.y > height - 30) {
          node.y = height - 30;
          node.vy *= -1;
        }

        const isHovered = Math.hypot(node.x - mouse.x, node.y - mouse.y) < node.radius + 8;
        const isSelected = activeNode?.id === node.id || selectedNodeId === node.id;

        ctx.beginPath();
        const displayRadius = isHovered || isSelected ? node.radius + 3 : node.radius;
        ctx.arc(node.x, node.y, displayRadius, 0, Math.PI * 2);

        if (node.type === 'incident') ctx.fillStyle = '#00FF88';
        else if (node.type === 'cause') ctx.fillStyle = '#00F0FF';
        else if (node.type === 'runbook') ctx.fillStyle = '#FFFFFF';
        else ctx.fillStyle = 'rgba(239, 68, 68, 0.75)';

        ctx.shadowColor = ctx.fillStyle;
        ctx.shadowBlur = isHovered || isSelected ? 18 : 10;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Outer halo on selected
        if (isSelected) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, displayRadius + 5, 0, Math.PI * 2);
          ctx.strokeStyle = '#00F0FF';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        // Label rendering
        ctx.fillStyle = isHovered || isSelected ? '#FFFFFF' : 'rgba(255, 255, 255, 0.65)';
        ctx.font = isHovered || isSelected ? '600 11px JetBrains Mono, monospace' : '400 10px JetBrains Mono, monospace';
        ctx.fillText(node.label, node.x + displayRadius + 6, node.y + 4);
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      canvas.removeEventListener('mousemove', onMouseMove);
      canvas.removeEventListener('click', onClick);
    };
  }, [activeNode?.id, onSelectNode, selectedNodeId]);

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#03060a]">
      <canvas ref={canvasRef} className="w-full h-full cursor-crosshair block" />

      {/* Legend overlay */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-3 px-3.5 py-2 rounded-lg bg-[#0a0f18]/90 border border-slate-800/80 backdrop-blur-md text-[11px] font-mono">
        <span className="text-slate-400 font-semibold tracking-wider uppercase text-[10px]">Entity Nodes:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#00FF88] shadow-[0_0_8px_#00FF88]" />
          <span className="text-slate-200">Incident (Verified)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#00F0FF] shadow-[0_0_8px_#00F0FF]" />
          <span className="text-slate-200">Root Cause</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-white shadow-[0_0_8px_#fff]" />
          <span className="text-slate-200">Runbook</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 shadow-[0_0_8px_#ef4444]" />
          <span className="text-red-300">Decoy (Filtered)</span>
        </div>
        <div className="h-3 w-[1px] bg-slate-700 mx-1 hidden sm:block" />
        <span className="text-cyan-400/80 text-[10px] hidden md:inline">Click node to inspect cryptographic provenance</span>
      </div>

      {/* Node Inspect Drawer */}
      {activeNode && (
        <div className="absolute right-4 top-4 bottom-4 w-96 max-w-[calc(100%-2rem)] z-20 flex flex-col rounded-xl bg-[#090d16]/95 border border-cyan-500/30 shadow-[0_8px_32px_rgba(0,0,0,0.8)] backdrop-blur-xl p-5 overflow-y-auto animate-in fade-in slide-in-from-right-4 duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span
                className={`w-3 h-3 rounded-full ${
                  activeNode.type === 'incident'
                    ? 'bg-[#00FF88] shadow-[0_0_8px_#00FF88]'
                    : activeNode.type === 'cause'
                    ? 'bg-[#00F0FF] shadow-[0_0_8px_#00F0FF]'
                    : activeNode.type === 'runbook'
                    ? 'bg-white shadow-[0_0_8px_#fff]'
                    : 'bg-red-500 shadow-[0_0_8px_#ef4444]'
                }`}
              />
              <span className="text-xs uppercase font-mono tracking-wider font-semibold text-cyan-400">
                {activeNode.type} Node
              </span>
            </div>
            <button
              onClick={() => setActiveNode(null)}
              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          <div className="mt-4 space-y-4 text-xs font-sans">
            <div>
              <h3 className="text-base font-semibold text-white font-mono">{activeNode.label}</h3>
              <p className="mt-1 text-slate-300 leading-relaxed">{activeNode.details?.summary}</p>
            </div>

            {/* Verdict Badge */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-emerald-400" /> Relevance Decision
                </span>
                <span
                  className={`px-2 py-0.5 rounded font-semibold text-[10px] ${
                    activeNode.details?.relevanceVerdict === 'REJECTED'
                      ? 'bg-red-950 text-red-400 border border-red-800/60'
                      : 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                  }`}
                >
                  {activeNode.details?.relevanceVerdict}
                </span>
              </div>
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Cpu size={14} className="text-cyan-400" /> Cosine Similarity
                </span>
                <span className="text-slate-200 font-semibold">{activeNode.details?.cosineScore}</span>
              </div>
            </div>

            {/* Cryptographic Provenance Details */}
            <div className="space-y-3 font-mono text-[11px]">
              <div className="space-y-1">
                <span className="text-slate-400 flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
                  <Hash size={12} className="text-cyan-400" /> Provenance Hash (SHA-256)
                </span>
                <div className="p-2 rounded bg-black/60 border border-slate-800 text-[10px] text-cyan-300 break-all select-all">
                  {activeNode.details?.provenanceHash}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
                  <Calendar size={12} className="text-slate-400" /> Retained Date
                </span>
                <div className="p-2 rounded bg-black/60 border border-slate-800 text-[10px] text-slate-200">
                  {activeNode.details?.retainedDate}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
                  <Database size={12} className="text-slate-400" /> Author / Signer
                </span>
                <div className="p-2 rounded bg-black/60 border border-slate-800 text-[10px] text-slate-200">
                  {activeNode.details?.author}
                </div>
              </div>

              {activeNode.details?.runbookRef && (
                <div className="space-y-1">
                  <span className="text-slate-400 flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
                    <Layers size={12} className="text-white" /> Linked Mitigation Runbook
                  </span>
                  <div className="p-2 rounded bg-emerald-950/40 border border-emerald-800/50 text-[10px] text-emerald-300 font-bold">
                    {activeNode.details?.runbookRef}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-2 text-[10px] text-slate-500 font-mono italic">
              Invariant: AI proposals require explicit human-verifier signature before promotion to verified operational memory.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
