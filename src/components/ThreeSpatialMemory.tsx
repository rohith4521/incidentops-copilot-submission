import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import {
  X,
  ShieldCheck,
  Cpu,
  Layers,
  Hash,
  Calendar,
  Database,
  ExternalLink,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

export type NodeType = 'INCIDENT' | 'ROOT_CAUSE' | 'EVIDENCE' | 'RUNBOOK' | 'POSTMORTEM' | 'VERIFIED_MEMORY' | 'DECOY';

export interface SpatialNodeData {
  id: string;
  name: string;
  type: NodeType;
  color: number;
  pos: [number, number, number];
  size: number;
  connectedTo: string[];
  details: {
    summary: string;
    provenanceHash: string;
    retainedDate: string;
    verifier: string;
    cosineScore: number;
    verdict: 'ACCEPTED' | 'REJECTED' | 'VERIFIED' | 'NOVEL';
    runbookId?: string;
  };
}

const DETERMINISTIC_NODES: SpatialNodeData[] = [
  // Cluster 1: INC-104 (PgBouncer)
  {
    id: 'inc-104',
    name: 'INC-104: PgBouncer 504 Spike',
    type: 'INCIDENT',
    color: 0x00ff88,
    pos: [-4.2, 1.8, 1.2],
    size: 0.55,
    connectedTo: ['rc-104', 'ev-104', 'anchor-104'],
    details: {
      summary: 'Checkout microservice experiencing 18.2% HTTP 504 timeouts under peak consumer checkout surge.',
      provenanceHash: 'sha256:7b9f84a1e948c201a0df27b8764098231',
      retainedDate: '2026-03-14 14:22:08 UTC',
      verifier: 'sre-core-team (alex.m)',
      cosineScore: 0.942,
      verdict: 'ACCEPTED',
      runbookId: 'RB-PGBOUNCER-POOL-120',
    },
  },
  {
    id: 'rc-104',
    name: 'Root Cause: Pool Ceiling Saturation',
    type: 'ROOT_CAUSE',
    color: 0x00f0ff,
    pos: [-2.6, 3.2, 0.4],
    size: 0.45,
    connectedTo: ['inc-104', 'rb-104', 'ev-104'],
    details: {
      summary: 'PgBouncer connection pool ceiling hit (100/100 active clients) due to unthrottled worker pod autoscaling.',
      provenanceHash: 'sha256:3a8901fc82b794101e9a22d76504a9190',
      retainedDate: '2026-03-14 14:38:15 UTC',
      verifier: 'hindsight-synthesizer',
      cosineScore: 0.918,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'ev-104',
    name: 'Evidence: 100/100 Active Sockets',
    type: 'EVIDENCE',
    color: 0x38bdf8,
    pos: [-5.5, 3.4, 1.8],
    size: 0.38,
    connectedTo: ['inc-104', 'rc-104'],
    details: {
      summary: 'TCP connection count to PgBouncer pegged at 100 max_client_conn with 450 queued transactions in socket backlog.',
      provenanceHash: 'sha256:4409bb1082fc89012a9128fe761009123',
      retainedDate: '2026-03-14 14:25:30 UTC',
      verifier: 'telemetry-ingestion-agent',
      cosineScore: 0.935,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'rb-104',
    name: 'RB-PGBOUNCER-POOL-120',
    type: 'RUNBOOK',
    color: 0xffffff,
    pos: [-1.2, 4.2, -0.6],
    size: 0.5,
    connectedTo: ['rc-104', 'pm-104'],
    details: {
      summary: 'Hot-scale PgBouncer max_client_conn from 100 to 300, issue SIGHUP reload to pooler, and throttle batch inventory sync.',
      provenanceHash: 'sha256:889ec12a0149021bdfc0028a7e0892214',
      retainedDate: '2026-03-14 14:45:00 UTC',
      verifier: 'human-verifier:alex.m',
      cosineScore: 0.895,
      verdict: 'VERIFIED',
      runbookId: 'RB-PGBOUNCER-POOL-120',
    },
  },
  {
    id: 'pm-104',
    name: 'Postmortem: Checkout Pooler Scaling',
    type: 'POSTMORTEM',
    color: 0x818cf8,
    pos: [-2.0, 1.0, -1.8],
    size: 0.42,
    connectedTo: ['rb-104', 'anchor-104'],
    details: {
      summary: 'Permanent mitigation: Dynamic connection pool scaling rules added to Helm values with circuit breakers on inventory burst.',
      provenanceHash: 'sha256:91823a019ef84201bba291048e7182901',
      retainedDate: '2026-03-15 10:00:00 UTC',
      verifier: 'sre-architect:sarah.t',
      cosineScore: 0.92,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'anchor-104',
    name: 'Verified Anchor: INC-104 Ground Truth',
    type: 'VERIFIED_MEMORY',
    color: 0x10b981,
    pos: [-3.0, 0.0, 0.0],
    size: 0.65,
    connectedTo: ['inc-104', 'pm-104'],
    details: {
      summary: 'Immutable operational memory anchor in Hindsight Cloud. Serves as ground truth for all subsequent pool saturation alerts.',
      provenanceHash: 'sha256:7b9f84a1e948c201a0df27b8764098231',
      retainedDate: '2026-03-15 11:30:00 UTC',
      verifier: 'hindsight-merkle-anchor',
      cosineScore: 1.0,
      verdict: 'VERIFIED',
      runbookId: 'RB-PGBOUNCER-POOL-120',
    },
  },

  // Decoy for INC-104 (Visibly detached, red/faded)
  {
    id: 'dec-884',
    name: 'Decoy #884: Stripe Gateway 504 Outage',
    type: 'DECOY',
    color: 0xef4444,
    pos: [-6.8, -1.2, 3.2],
    size: 0.35,
    connectedTo: [],
    details: {
      summary: 'External vendor outage. Rejected by Relevance Filter: External API timeout does not match internal database pool exhaustion.',
      provenanceHash: 'sha256:d82e11894bfae929841c28f1104e76812',
      retainedDate: '2025-11-02 09:12:44 UTC',
      verifier: 'relevance-filter-engine',
      cosineScore: 0.812,
      verdict: 'REJECTED',
    },
  },

  // Cluster 2: INC-108 (Redis TLS)
  {
    id: 'inc-108',
    name: 'INC-108: Redis TLS Handshake Drop',
    type: 'INCIDENT',
    color: 0x00ff88,
    pos: [3.8, 2.2, -1.0],
    size: 0.55,
    connectedTo: ['rc-108', 'ev-108', 'anchor-108'],
    details: {
      summary: 'Session-cache cluster rejecting client TLS handshakes after certificate rotation.',
      provenanceHash: 'sha256:5502cba0431289fe182049e91823746a8',
      retainedDate: '2026-05-18 20:05:19 UTC',
      verifier: 'oncall-sre:david.k',
      cosineScore: 0.887,
      verdict: 'ACCEPTED',
      runbookId: 'RB-REDIS-TLS-ROTATE',
    },
  },
  {
    id: 'rc-108',
    name: 'Root Cause: mTLS Trust Bundle Desync',
    type: 'ROOT_CAUSE',
    color: 0x00f0ff,
    pos: [5.2, 3.5, 0.2],
    size: 0.45,
    connectedTo: ['inc-108', 'rb-108'],
    details: {
      summary: 'Redis replica nodes failed TLS certificate verification due to incomplete rollout of rotated internal CA trust bundles.',
      provenanceHash: 'sha256:1049ea2387df10bce427a8e992147ac00',
      retainedDate: '2026-05-18 20:15:00 UTC',
      verifier: 'hindsight-synthesizer',
      cosineScore: 0.91,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'ev-108',
    name: 'Evidence: x509 Unknown Authority',
    type: 'EVIDENCE',
    color: 0x38bdf8,
    pos: [2.5, 3.8, -1.8],
    size: 0.38,
    connectedTo: ['inc-108'],
    details: {
      summary: 'Client pods logging x509: certificate signed by unknown authority across 100% of ingress proxy workers.',
      provenanceHash: 'sha256:99810a91024e01928374619a827103841',
      retainedDate: '2026-05-18 20:08:44 UTC',
      verifier: 'telemetry-agent',
      cosineScore: 0.89,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'rb-108',
    name: 'RB-REDIS-TLS-ROTATE',
    type: 'RUNBOOK',
    color: 0xffffff,
    pos: [6.2, 1.5, 1.2],
    size: 0.5,
    connectedTo: ['rc-108', 'anchor-108'],
    details: {
      summary: 'Synchronize refreshed CA certificates across session-cache pods and invoke hot TLS config reload.',
      provenanceHash: 'sha256:1049ea2387df10bce427a8e992147ac00',
      retainedDate: '2026-05-18 20:22:40 UTC',
      verifier: 'human-verifier:david.k',
      cosineScore: 0.871,
      verdict: 'VERIFIED',
      runbookId: 'RB-REDIS-TLS-ROTATE',
    },
  },
  {
    id: 'anchor-108',
    name: 'Verified Anchor: INC-108 CA Sync',
    type: 'VERIFIED_MEMORY',
    color: 0x10b981,
    pos: [3.2, 0.2, 0.2],
    size: 0.65,
    connectedTo: ['inc-108', 'rb-108'],
    details: {
      summary: 'Immutable memory record verifying the root cause and mitigation procedure for Redis cluster TLS rotations.',
      provenanceHash: 'sha256:5502cba0431289fe182049e91823746a8',
      retainedDate: '2026-05-18 21:00:00 UTC',
      verifier: 'hindsight-merkle-anchor',
      cosineScore: 1.0,
      verdict: 'VERIFIED',
      runbookId: 'RB-REDIS-TLS-ROTATE',
    },
  },
  {
    id: 'dec-912',
    name: 'Decoy #912: Redis Memory Eviction',
    type: 'DECOY',
    color: 0xef4444,
    pos: [7.2, 0.0, -2.8],
    size: 0.35,
    connectedTo: [],
    details: {
      summary: 'Key eviction storm symptoms do not match cryptographic TLS certificate rejection. Filtered out before diagnosis.',
      provenanceHash: 'sha256:9901efa882103b4412a8190248a019231',
      retainedDate: '2025-08-11 12:44:19 UTC',
      verifier: 'relevance-filter-engine',
      cosineScore: 0.72,
      verdict: 'REJECTED',
    },
  },

  // Cluster 3: INC-112 (Novel OOMKilled)
  {
    id: 'inc-112',
    name: 'INC-112: Inventory OOMKilled',
    type: 'INCIDENT',
    color: 0x38bdf8,
    pos: [0.0, -2.8, 2.5],
    size: 0.55,
    connectedTo: ['rc-112', 'ev-112', 'rb-112'],
    details: {
      summary: 'Novel pod eviction crash loop caused by unexpected JSON deserialization memory spike. Zero prior historical match.',
      provenanceHash: 'sha256:f489b0227189c4048ea33910c28372481',
      retainedDate: '2026-09-29 18:40:12 UTC',
      verifier: 'oncall-sre (human-in-the-loop)',
      cosineScore: 0.324,
      verdict: 'NOVEL',
      runbookId: 'RB-K8S-SCALE-LIMITS',
    },
  },
  {
    id: 'rc-112',
    name: 'Root Cause: In-Memory JSON Deserialization',
    type: 'ROOT_CAUSE',
    color: 0x00f0ff,
    pos: [1.8, -3.8, 1.8],
    size: 0.45,
    connectedTo: ['inc-112', 'rb-112'],
    details: {
      summary: 'Microservice deserialized unchunked 140MB JSON catalog batches entirely into RAM, exceeding container cgroup limit.',
      provenanceHash: 'sha256:6618901fe84a0192bb381904710294819',
      retainedDate: '2026-09-29 19:10:00 UTC',
      verifier: 'triage-engine-first-principles',
      cosineScore: 0.88,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'ev-112',
    name: 'Evidence: Linux cgroup Exit Code 137',
    type: 'EVIDENCE',
    color: 0x38bdf8,
    pos: [-1.8, -3.5, 3.2],
    size: 0.38,
    connectedTo: ['inc-112'],
    details: {
      summary: 'Kernel OOM killer invoked with exit code 137 on PID 1422; container memory usage recorded 2.14Gi on 2Gi limit.',
      provenanceHash: 'sha256:7710928419a8201bcf8291048a1092381',
      retainedDate: '2026-09-29 18:42:00 UTC',
      verifier: 'k8s-event-collector',
      cosineScore: 0.95,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'rb-112',
    name: 'RB-K8S-SCALE-LIMITS',
    type: 'RUNBOOK',
    color: 0xffffff,
    pos: [0.0, -4.5, 0.8],
    size: 0.5,
    connectedTo: ['inc-112', 'rc-112'],
    details: {
      summary: 'Increase worker memory limit to 4Gi and enable JSON streaming parser feature flag in worker deployment config.',
      provenanceHash: 'sha256:8819024b8192a01490281bcf710284918',
      retainedDate: '2026-09-29 19:25:00 UTC',
      verifier: 'human-verifier:alex.m',
      cosineScore: 0.85,
      verdict: 'VERIFIED',
      runbookId: 'RB-K8S-SCALE-LIMITS',
    },
  },

  // Ambient verified precedents
  {
    id: 'amb-204',
    name: 'INC-204: Kafka Lag Partition 12',
    type: 'INCIDENT',
    color: 0x00ff88,
    pos: [-5.0, -2.0, -2.5],
    size: 0.42,
    connectedTo: ['amb-rb-204'],
    details: {
      summary: 'Consumer group rebalance storm caused by skewed partition key distribution.',
      provenanceHash: 'sha256:119284019a8201948ba10923847109283',
      retainedDate: '2026-02-10 11:20:00 UTC',
      verifier: 'sre-core-team',
      cosineScore: 0.86,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'amb-rb-204',
    name: 'RB-KAFKA-CONSUMER-REBALANCE',
    type: 'RUNBOOK',
    color: 0xffffff,
    pos: [-3.8, -3.0, -3.2],
    size: 0.4,
    connectedTo: ['amb-204'],
    details: {
      summary: 'Assign static consumer group memberships and scale partition count from 16 to 32.',
      provenanceHash: 'sha256:229104819a01948ba1029384710928374',
      retainedDate: '2026-02-10 11:45:00 UTC',
      verifier: 'human-verifier:sarah.t',
      cosineScore: 0.88,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'amb-319',
    name: 'INC-319: Envoy Upstream RST 503',
    type: 'INCIDENT',
    color: 0x00ff88,
    pos: [4.5, -2.2, -3.0],
    size: 0.42,
    connectedTo: [],
    details: {
      summary: 'Upstream HTTP/2 connection pooling keepalive timeout desync between Envoy ingress and backend Go services.',
      provenanceHash: 'sha256:339104819a01948ba1029384710928375',
      retainedDate: '2026-04-02 16:30:00 UTC',
      verifier: 'sre-core-team',
      cosineScore: 0.89,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'amb-402',
    name: 'INC-402: CoreDNS Query Thrashing',
    type: 'INCIDENT',
    color: 0x00ff88,
    pos: [-1.5, 2.5, -4.5],
    size: 0.42,
    connectedTo: [],
    details: {
      summary: 'Kubernetes ndots:5 configuration thrashing CoreDNS replicas during high pod churn.',
      provenanceHash: 'sha256:449104819a01948ba1029384710928376',
      retainedDate: '2026-01-20 08:15:00 UTC',
      verifier: 'sre-core-team',
      cosineScore: 0.87,
      verdict: 'VERIFIED',
    },
  },
  {
    id: 'dec-411',
    name: 'Decoy #411: BGP Flap at Transit AS',
    type: 'DECOY',
    color: 0xef4444,
    pos: [0.0, 5.2, 3.8],
    size: 0.35,
    connectedTo: [],
    details: {
      summary: 'Public transit route flapping. Irrelevant to application runtime exceptions.',
      provenanceHash: 'sha256:559104819a01948ba1029384710928377',
      retainedDate: '2025-09-01 14:00:00 UTC',
      verifier: 'relevance-filter',
      cosineScore: 0.65,
      verdict: 'REJECTED',
    },
  },
];

interface ThreeSpatialMemoryProps {
  onSelectNode?: (node: SpatialNodeData) => void;
  selectedNodeId?: string | null;
  height?: string;
  focusNodeId?: string | null;
}

export const ThreeSpatialMemory: React.FC<ThreeSpatialMemoryProps> = ({
  onSelectNode,
  selectedNodeId,
  height = '100%',
  focusNodeId,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [activeNode, setActiveNode] = useState<SpatialNodeData | null>(null);
  const [filterType, setFilterType] = useState<string>('ALL');

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let width = container.clientWidth || window.innerWidth || 1200;
    let heightPx = container.clientHeight || window.innerHeight - 80 || 700;

    // Check WebGL availability
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) {
      console.warn('WebGL not supported, falling back to 2D representation.');
      return;
    }

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x03060a, 0.045);

    const camera = new THREE.PerspectiveCamera(50, width / heightPx, 0.1, 1000);
    camera.position.set(0, 3, 16);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, heightPx);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x03060a, 1);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Root group for smooth inertia rotation
    const rootGroup = new THREE.Group();
    scene.add(rootGroup);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x0e1726, 3.0);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x00f0ff, 2.5);
    dirLight1.position.set(10, 15, 10);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x00ff88, 2.0);
    dirLight2.position.set(-10, -10, -10);
    scene.add(dirLight2);

    const centerPointLight = new THREE.PointLight(0x00f0ff, 3.5, 25);
    centerPointLight.position.set(0, 0, 0);
    rootGroup.add(centerPointLight);

    // Central Hindsight Memory Core (Signature Anchor)
    const coreGeo = new THREE.IcosahedronGeometry(1.6, 2);
    const coreMat = new THREE.MeshPhongMaterial({
      color: 0x071b2d,
      emissive: 0x003344,
      specular: 0x00f0ff,
      shininess: 90,
      transparent: true,
      opacity: 0.85,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    rootGroup.add(coreMesh);

    const coreWireGeo = new THREE.IcosahedronGeometry(1.66, 1);
    const coreWireMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const coreWireMesh = new THREE.Mesh(coreWireGeo, coreWireMat);
    rootGroup.add(coreWireMesh);

    // Inner glowing sphere
    const innerGeo = new THREE.SphereGeometry(0.8, 24, 24);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x00ff88,
      transparent: true,
      opacity: 0.65,
    });
    const innerOrb = new THREE.Mesh(innerGeo, innerMat);
    rootGroup.add(innerOrb);

    // Orbital Rings around core
    const createRing = (radius: number, tube: number, color: number, rx: number, ry: number) => {
      const geo = new THREE.TorusGeometry(radius, tube, 16, 100);
      const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.35 });
      const ring = new THREE.Mesh(geo, mat);
      ring.rotation.x = rx;
      ring.rotation.y = ry;
      rootGroup.add(ring);
      return ring;
    };
    const ring1 = createRing(3.2, 0.02, 0x00f0ff, Math.PI / 3, 0);
    const ring2 = createRing(4.8, 0.015, 0x00ff88, -Math.PI / 4, Math.PI / 6);

    // Meshes map
    const nodeMeshes: THREE.Mesh[] = [];
    const nodeMap = new Map<string, THREE.Mesh>();

    // Build Node Meshes
    DETERMINISTIC_NODES.forEach((nodeData) => {
      const geo = new THREE.SphereGeometry(nodeData.size, 24, 24);
      const mat = new THREE.MeshStandardMaterial({
        color: nodeData.color,
        emissive: nodeData.color,
        emissiveIntensity: nodeData.type === 'DECOY' ? 0.2 : 0.65,
        roughness: 0.25,
        metalness: 0.7,
        transparent: true,
        opacity: nodeData.type === 'DECOY' ? 0.45 : 0.95,
      });

      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(...nodeData.pos);
      mesh.userData = nodeData;

      // Glow halo ring for verified memories
      if (nodeData.type === 'VERIFIED_MEMORY') {
        const haloGeo = new THREE.RingGeometry(nodeData.size * 1.3, nodeData.size * 1.6, 32);
        const haloMat = new THREE.MeshBasicMaterial({
          color: 0x10b981,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.7,
        });
        const halo = new THREE.Mesh(haloGeo, haloMat);
        halo.rotation.x = Math.PI / 2;
        mesh.add(halo);
      }

      rootGroup.add(mesh);
      nodeMeshes.push(mesh);
      nodeMap.set(nodeData.id, mesh);
    });

    // Build Relationship Lines
    const lineObjects: { line: THREE.Line; fromId: string; toId: string }[] = [];
    DETERMINISTIC_NODES.forEach((nodeData) => {
      nodeData.connectedTo.forEach((targetId) => {
        const targetNode = DETERMINISTIC_NODES.find((n) => n.id === targetId);
        if (targetNode) {
          const points = [new THREE.Vector3(...nodeData.pos), new THREE.Vector3(...targetNode.pos)];
          const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
          const isDecoy = nodeData.type === 'DECOY' || targetNode.type === 'DECOY';
          const lineMat = new THREE.LineBasicMaterial({
            color: isDecoy ? 0xef4444 : 0x00f0ff,
            transparent: true,
            opacity: isDecoy ? 0.15 : 0.4,
            linewidth: 1,
          });
          const line = new THREE.Line(lineGeo, lineMat);
          rootGroup.add(line);
          lineObjects.push({ line, fromId: nodeData.id, toId: targetId });
        }
      });
    });

    // Ambient Space Dust Particles
    const particleCount = 200;
    const particleGeo = new THREE.BufferGeometry();
    const particlePos = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePos[i] = (Math.random() - 0.5) * 35;
      particlePos[i + 1] = (Math.random() - 0.5) * 25;
      particlePos[i + 2] = (Math.random() - 0.5) * 35;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePos, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x00f0ff,
      size: 0.12,
      transparent: true,
      opacity: 0.4,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    rootGroup.add(particles);

    // Raycasting & Interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2(-1000, -1000);
    let hoveredMesh: THREE.Mesh | null = null;
    let targetRotationX = 0;
    let targetRotationY = 0;

    const onMouseMove = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      targetRotationY = mouse.x * 0.35;
      targetRotationX = -mouse.y * 0.25;

      // Raycast for hover
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(nodeMeshes);

      if (intersects.length > 0) {
        const mesh = intersects[0].object as THREE.Mesh;
        if (hoveredMesh !== mesh) {
          if (hoveredMesh) (hoveredMesh.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.65;
          hoveredMesh = mesh;
          (hoveredMesh.material as THREE.MeshStandardMaterial).emissiveIntensity = 1.4;
          renderer.domElement.style.cursor = 'pointer';
        }
      } else {
        if (hoveredMesh) {
          (hoveredMesh.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.65;
          hoveredMesh = null;
          renderer.domElement.style.cursor = 'crosshair';
        }
      }
    };

    const onClick = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(nodeMeshes);

      if (intersects.length > 0) {
        const clickedMesh = intersects[0].object as THREE.Mesh;
        const data = clickedMesh.userData as SpatialNodeData;
        setActiveNode(data);
        if (onSelectNode) onSelectNode(data);

        // Highlight connected lines and dim others
        lineObjects.forEach(({ line, fromId, toId }) => {
          const isConnected = fromId === data.id || toId === data.id;
          const mat = line.material as THREE.LineBasicMaterial;
          mat.opacity = isConnected ? 0.95 : 0.08;
          mat.color.setHex(isConnected ? 0x00ff88 : 0x334155);
        });

        // Highlight connected nodes and dim others
        nodeMeshes.forEach((m) => {
          const nData = m.userData as SpatialNodeData;
          const isConnected = nData.id === data.id || data.connectedTo.includes(nData.id) || nData.connectedTo.includes(data.id);
          const mat = m.material as THREE.MeshStandardMaterial;
          mat.opacity = isConnected ? 1.0 : 0.25;
        });
      }
    };

    renderer.domElement.addEventListener('mousemove', onMouseMove);
    renderer.domElement.addEventListener('click', onClick);

    const onResize = () => {
      if (!container) return;
      width = container.clientWidth || window.innerWidth;
      heightPx = container.clientHeight || window.innerHeight;
      camera.aspect = width / heightPx;
      camera.updateProjectionMatrix();
      renderer.setSize(width, heightPx);
    };
    window.addEventListener('resize', onResize);

    // Animation Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Core rotation & pulse
      coreMesh.rotation.y = elapsedTime * 0.12;
      coreMesh.rotation.x = Math.sin(elapsedTime * 0.15) * 0.08;
      coreWireMesh.rotation.y = -elapsedTime * 0.15;
      const pulse = 1 + Math.sin(elapsedTime * 2.2) * 0.1;
      innerOrb.scale.set(pulse, pulse, pulse);

      // Rings
      ring1.rotation.z = elapsedTime * 0.06;
      ring2.rotation.z = -elapsedTime * 0.04;

      // Particles drift
      particles.rotation.y = elapsedTime * 0.015;

      // Floating drift for nodes
      nodeMeshes.forEach((mesh, idx) => {
        mesh.position.y += Math.sin(elapsedTime * 1.2 + idx) * 0.003;
      });

      // Camera parallax
      rootGroup.rotation.y += (targetRotationY - rootGroup.rotation.y) * 0.05;
      rootGroup.rotation.x += (targetRotationX - rootGroup.rotation.x) * 0.05;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', onResize);
      renderer.domElement.removeEventListener('mousemove', onMouseMove);
      renderer.domElement.removeEventListener('click', onClick);
      renderer.dispose();
      if (container) container.innerHTML = '';
    };
  }, [onSelectNode]);

  // Handle focusNodeId prop change
  useEffect(() => {
    if (focusNodeId) {
      const match = DETERMINISTIC_NODES.find((n) => n.id === focusNodeId);
      if (match) setActiveNode(match);
    }
  }, [focusNodeId]);

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#03060a]">
      {/* 3D Canvas Mount Point */}
      <div ref={containerRef} className="w-full h-full cursor-crosshair block" />

      {/* Top Legend Bar */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-3 px-3.5 py-2 rounded-lg bg-[#0a0f18]/90 border border-slate-800/80 backdrop-blur-md text-[11px] font-mono shadow-lg">
        <span className="text-slate-400 font-semibold tracking-wider uppercase text-[10px]">Living Graph:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#00FF88] shadow-[0_0_8px_#00FF88]" />
          <span className="text-slate-200">Incident</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#00F0FF] shadow-[0_0_8px_#00F0FF]" />
          <span className="text-slate-200">Root Cause</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#38BDF8] shadow-[0_0_8px_#38BDF8]" />
          <span className="text-slate-200">Evidence</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-white shadow-[0_0_8px_#fff]" />
          <span className="text-slate-200">Runbook</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] ring-2 ring-emerald-400/50 shadow-[0_0_10px_#10B981]" />
          <span className="text-emerald-300 font-semibold">Verified Anchor</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500/60 shadow-[0_0_8px_#ef4444]" />
          <span className="text-red-400">Decoy (Detached)</span>
        </div>
      </div>

      {/* Node Inspect Drawer (Right Side) */}
      {activeNode && (
        <div className="absolute right-4 top-4 bottom-4 w-96 max-w-[calc(100%-2rem)] z-20 flex flex-col rounded-xl bg-[#090d16]/95 border border-cyan-500/40 shadow-[0_8px_32px_rgba(0,0,0,0.85)] backdrop-blur-xl p-5 overflow-y-auto animate-in fade-in slide-in-from-right-4 duration-200 font-sans">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: `#${activeNode.color.toString(16).padStart(6, '0')}` }}
              />
              <span className="text-xs uppercase font-mono tracking-wider font-semibold text-cyan-400">
                {activeNode.type.replace('_', ' ')}
              </span>
            </div>
            <button
              onClick={() => setActiveNode(null)}
              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          <div className="mt-4 space-y-4 text-xs">
            <div>
              <h3 className="text-base font-semibold text-white font-mono">{activeNode.name}</h3>
              <p className="mt-1 text-slate-300 leading-relaxed font-sans">{activeNode.details.summary}</p>
            </div>

            {/* Verdict Badge */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-emerald-400" /> Relevance Decision
                </span>
                <span
                  className={`px-2 py-0.5 rounded font-semibold text-[10px] ${
                    activeNode.details.verdict === 'REJECTED'
                      ? 'bg-red-950 text-red-400 border border-red-800/60'
                      : 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                  }`}
                >
                  {activeNode.details.verdict}
                </span>
              </div>
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Cpu size={14} className="text-cyan-400" /> Ground Truth Similarity
                </span>
                <span className="text-slate-200 font-semibold">{activeNode.details.cosineScore}</span>
              </div>
            </div>

            {/* Cryptographic Details */}
            <div className="space-y-3 font-mono text-[11px]">
              <div className="space-y-1">
                <span className="text-slate-400 flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
                  <Hash size={12} className="text-cyan-400" /> Provenance Hash (SHA-256)
                </span>
                <div className="p-2 rounded bg-black/60 border border-slate-800 text-[10px] text-cyan-300 break-all select-all">
                  {activeNode.details.provenanceHash}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
                  <Calendar size={12} className="text-slate-400" /> Retained Date
                </span>
                <div className="p-2 rounded bg-black/60 border border-slate-800 text-[10px] text-slate-200">
                  {activeNode.details.retainedDate}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
                  <Database size={12} className="text-slate-400" /> Signer / Verifier
                </span>
                <div className="p-2 rounded bg-black/60 border border-slate-800 text-[10px] text-slate-200">
                  {activeNode.details.verifier}
                </div>
              </div>

              {activeNode.details.runbookId && (
                <div className="space-y-1">
                  <span className="text-slate-400 flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
                    <Layers size={12} className="text-white" /> Linked Mitigation Runbook
                  </span>
                  <div className="p-2 rounded bg-emerald-950/40 border border-emerald-800/50 text-[10px] text-emerald-300 font-bold">
                    {activeNode.details.runbookId}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-2 text-[10px] text-slate-500 font-mono italic">
              Living memory anchor in Hindsight continuous memory graph.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
