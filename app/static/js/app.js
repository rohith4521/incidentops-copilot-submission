/**
 * IncidentOps Copilot - SRE Continuous Memory Command Center Client
 * Phase 3 Production Implementation
 */

let currentTriageResponse = null;
let currentRunbookRecommendation = null;
let activePresets = [];
let isMemoryEnabled = true;

// 3D Pipeline Visualizer Globals
let scene, camera, renderer, animationFrameId;
let pipelineNodes = [];
let pipelineConnections = [];
let flowParticles = [];
let isReducedMotion = false;
let isTriageRunning = false;

// Initialize dashboard on DOM load
document.addEventListener("DOMContentLoaded", () => {
  isReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  checkSystemHealth();
  loadPresets();
  setupEventListeners();
  setupMemoryToggle();
  setupMemoryTraceDrawer();
  init3DPipeline();
});

// Periodic health poll (every 30s)
setInterval(checkSystemHealth, 30000);

async function checkSystemHealth() {
  try {
    const res = await fetch("/api/v1/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();

    const dot = document.getElementById("hindsight-dot");
    const statusText = document.getElementById("hindsight-status-text");
    const bankText = document.getElementById("hindsight-bank-text");
    const groqText = document.getElementById("groq-model-text");

    if (bankText) bankText.textContent = data.bank_id || "sre-incidentops-production";
    if (groqText) groqText.textContent = data.groq.default_model || "Llama 3.3 70B";

    if (data.hindsight.status === "connected") {
      dot.className = "pulse-dot";
      statusText.textContent = "Live (v" + (data.hindsight.api_version || "0.10.1") + ")";
      statusText.style.color = "var(--accent-emerald)";
    } else if (data.hindsight.status === "unauthorized") {
      dot.className = "pulse-dot warning";
      statusText.textContent = "API Key Required";
      statusText.style.color = "var(--accent-amber)";
    } else {
      dot.className = "pulse-dot danger";
      statusText.textContent = "Offline";
      statusText.style.color = "var(--accent-rose)";
    }
  } catch (err) {
    console.error("Error checking health:", err);
  }
}

async function loadPresets() {
  try {
    const res = await fetch("/api/alerts/presets");
    if (!res.ok) return;
    activePresets = await res.json();
    renderPresetButtons();
  } catch (err) {
    console.error("Error loading presets:", err);
  }
}

function renderPresetButtons() {
  const container = document.getElementById("preset-container");
  if (!container || !activePresets || activePresets.length === 0) return;

  container.innerHTML = "";
  activePresets.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = p.type === "known" ? "btn btn-preset-known" : "btn btn-preset-novel";
    btn.setAttribute("data-scenario", p.id);
    btn.innerHTML = `<span>${p.type === "known" ? "🚨" : "⚡"}</span> ${p.name}`;
    btn.addEventListener("click", () => applyPresetScenario(p.id));
    container.appendChild(btn);
  });
}

function setupEventListeners() {
  // Triage trigger button
  document.getElementById("btn-trigger-triage").addEventListener("click", executeTriage);

  // Seed Hindsight button
  document.getElementById("btn-seed-hindsight").addEventListener("click", seedHindsightMemory);

  // Runbook approval buttons
  document.getElementById("btn-approve-runbook").addEventListener("click", approveCurrentRunbook);
  document.getElementById("btn-reject-runbook").addEventListener("click", rejectCurrentRunbook);
  document.getElementById("btn-simulate-runbook").addEventListener("click", simulateCurrentRunbook);

  // Commit Post-Mortem button
  document.getElementById("btn-commit-postmortem").addEventListener("click", commitPostMortem);

  // Simulate Repeat Alert button
  const repeatBtn = document.getElementById("btn-simulate-repeat");
  if (repeatBtn) {
    repeatBtn.addEventListener("click", () => {
      const toggle = document.getElementById("memory-toggle");
      if (toggle && !toggle.checked) {
        toggle.checked = true;
        isMemoryEnabled = true;
        toggle.dispatchEvent(new Event("change"));
      } else {
        isMemoryEnabled = true;
      }
      executeTriage();
    });
  }

  // Window resize handler for 3D canvas
  window.addEventListener("resize", onWindowResize);
}

function setupMemoryToggle() {
  const toggle = document.getElementById("memory-toggle");
  const box = document.getElementById("memory-toggle-box");
  const heading = document.getElementById("memory-toggle-heading");
  const sub = document.getElementById("memory-toggle-sub");
  const indicator = document.getElementById("memory-toggle-indicator");
  const modePill = document.getElementById("memory-mode-text");
  const pipelineMemStatus = document.getElementById("pipeline-memory-status");

  toggle.addEventListener("change", (e) => {
    isMemoryEnabled = e.target.checked;
    updateMemoryUIState();
  });

  function updateMemoryUIState() {
    if (isMemoryEnabled) {
      box.className = "memory-toggle-container active";
      indicator.textContent = "🟢";
      heading.textContent = "Hindsight Continuous Memory: ACTIVE";
      sub.textContent = "Queries real Hindsight vector/graph memory bank to recall verified post-mortems and failed mitigations.";
      modePill.textContent = "ACTIVE";
      modePill.style.color = "var(--accent-emerald)";
      if (pipelineMemStatus) {
        pipelineMemStatus.innerHTML = "Memory Node: <strong style='color: var(--accent-cyan);'>Hindsight Connected</strong>";
      }
    } else {
      box.className = "memory-toggle-container stateless";
      indicator.textContent = "🟡";
      heading.textContent = "Hindsight Continuous Memory: BYPASSED (Stateless Mode)";
      sub.textContent = "Continuous memory layer is bypassed entirely. Generates first-principles SRE reasoning from current telemetry only.";
      modePill.textContent = "STATELESS";
      modePill.style.color = "var(--accent-amber)";
      if (pipelineMemStatus) {
        pipelineMemStatus.innerHTML = "Memory Node: <strong style='color: var(--accent-amber);'>Bypassed (Stateless)</strong>";
      }
    }
    update3DPipelineMemoryMode(isMemoryEnabled);
  }
}

function setupMemoryTraceDrawer() {
  const drawer = document.getElementById("memory-trace-drawer");
  const backdrop = document.getElementById("drawer-backdrop");
  const btnOpen = document.getElementById("btn-open-trace");
  const btnClose = document.getElementById("btn-close-drawer");

  btnOpen.addEventListener("click", () => {
    drawer.classList.add("open");
    backdrop.classList.remove("hidden");
  });

  const closeDrawer = () => {
    drawer.classList.remove("open");
    backdrop.classList.add("hidden");
  };

  btnClose.addEventListener("click", closeDrawer);
  backdrop.addEventListener("click", closeDrawer);
}

function applyPresetScenario(scenarioId) {
  const scenario = activePresets.find((s) => s.id === scenarioId);
  if (!scenario) return;

  const a = scenario.alert;
  document.getElementById("alert-service").value = a.service;
  document.getElementById("alert-environment").value = `${a.environment} (${a.cluster || "k8s-prod"})`;
  document.getElementById("alert-title").value = a.title;
  document.getElementById("alert-description").value = a.description;
  document.getElementById("alert-symptoms").value = a.symptoms.join(", ");

  const badge = document.getElementById("alert-severity-badge");
  badge.textContent = a.severity;
  badge.className = a.severity === "CRITICAL" ? "badge badge-critical" : "badge badge-moderate";

  // Trigger triage automatically
  executeTriage();
}

async function executeTriage() {
  const btn = document.getElementById("btn-trigger-triage");
  const spinner = document.getElementById("triage-spinner");
  const btnText = document.getElementById("triage-btn-text");
  const pipelineStatus = document.getElementById("pipeline-status-text");

  btn.disabled = true;
  spinner.classList.remove("hidden");
  btnText.textContent = isMemoryEnabled ? "Querying Hindsight Memory & SRE Inference..." : "Executing Stateless SRE Reasoning...";

  if (pipelineStatus) {
    pipelineStatus.innerHTML = "Pipeline Status: <strong style='color: var(--accent-cyan);'>Processing Alert...</strong>";
  }
  isTriageRunning = true;
  triggerPipelinePulse();

  const service = document.getElementById("alert-service").value.trim();
  const title = document.getElementById("alert-title").value.trim();
  const description = document.getElementById("alert-description").value.trim();
  const symptomsRaw = document.getElementById("alert-symptoms").value.trim();
  const symptoms = symptomsRaw ? symptomsRaw.split(",").map((s) => s.trim()).filter(Boolean) : [];
  const severity = document.getElementById("alert-severity-badge").textContent;

  const payload = {
    service: service,
    alert: title,
    signature: title,
    symptoms: symptoms,
    severity: severity,
    description: description,
    context: {
      environment: document.getElementById("alert-environment").value.trim(),
      timestamp: new Date().toISOString(),
    },
    enable_memory: isMemoryEnabled,
  };

  try {
    // REAL CANONICAL POST /api/v1/triage endpoint
    const res = await fetch("/api/v1/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Triage execution failed");
    }

    const data = await res.json();
    currentTriageResponse = data;
    renderTriageResponse(data, payload);

    if (pipelineStatus) {
      const statusColor = data.novelty ? "var(--accent-purple)" : "var(--accent-emerald)";
      const statusLabel = data.novelty ? (data.memory_used ? "Novel Incident Diagnosed" : "Stateless Triage Complete") : "Precedent Matched";
      pipelineStatus.innerHTML = `Pipeline Status: <strong style="color: ${statusColor};">${statusLabel}</strong>`;
    }
  } catch (err) {
    alert("Triage error: " + err.message);
    if (pipelineStatus) {
      pipelineStatus.innerHTML = `Pipeline Status: <strong style="color: var(--accent-rose);">Error</strong>`;
    }
  } finally {
    btn.disabled = false;
    spinner.classList.add("hidden");
    btnText.textContent = "⚡ Run SRE Incident Triage (/api/v1/triage)";
    isTriageRunning = false;
  }
}

function renderTriageResponse(data, payload) {
  // Incident Ref Display
  const incDisplay = document.getElementById("incident-id-display");
  if (data.historical_matches && data.historical_matches.length > 0) {
    incDisplay.textContent = `Precedent: ${data.historical_matches[0].incident_id}`;
  } else {
    incDisplay.textContent = `Ref: ALT-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
  }

  // Truthful Match Strength Badge
  const strengthBadge = document.getElementById("match-strength-badge");
  const matchStr = data.match_strength || (data.historical_matches && data.historical_matches.length > 0 ? "High" : "None");
  strengthBadge.textContent = matchStr.toUpperCase();
  if (matchStr === "High") {
    strengthBadge.className = "badge badge-high";
  } else if (matchStr === "Moderate") {
    strengthBadge.className = "badge badge-moderate";
  } else {
    strengthBadge.className = "badge badge-none";
  }

  // Verifiable Evidence Bullets
  const bulletList = document.getElementById("evidence-bullet-list");
  bulletList.innerHTML = "";
  if (data.supporting_evidence && data.supporting_evidence.length > 0) {
    data.supporting_evidence.forEach((bullet) => {
      const li = document.createElement("li");
      li.textContent = bullet;
      bulletList.appendChild(li);
    });
  } else {
    bulletList.innerHTML = "<li>No direct evidence bullets recorded.</li>";
  }

  // Recalled Historical Matches
  const memoriesContainer = document.getElementById("recalled-memories-container");
  memoriesContainer.innerHTML = "";

  if (data.historical_matches && data.historical_matches.length > 0) {
    document.getElementById("recall-meta").textContent = 
      `Recalled ${data.historical_matches.length} verified historical incident(s) from Hindsight Continuous Memory.`;

    data.historical_matches.forEach((mem) => {
      const card = document.createElement("div");
      card.className = "memory-card";
      card.style.border = "1px solid rgba(16, 185, 129, 0.45)";
      card.style.background = "rgba(16, 185, 129, 0.06)";
      card.innerHTML = `
        <div class="memory-header">
          <span class="memory-id" style="color: #34d399; font-size: 0.88rem; font-weight: 700;">${mem.incident_id}</span>
          <span class="badge badge-high" style="font-size: 0.65rem; background: rgba(16, 185, 129, 0.25); border: 1px solid #10b981; color: #34d399;">
            VERIFIED HISTORICAL EVIDENCE
          </span>
        </div>
        <div class="memory-title" style="color: #f8fafc; font-weight: 600;">${mem.title || `${mem.service} Historical Precedent`}</div>
        <div class="memory-detail" style="margin-top: 0.35rem;">
          <strong style="color: #94a3b8;">Recalled Root Cause:</strong> <span style="color: #e2e8f0;">${mem.root_cause || "Detailed in post-mortem record"}</span>
        </div>
        <div class="memory-detail" style="margin-top: 0.35rem;">
          <strong style="color: #94a3b8;">Recalled Verified Runbook:</strong> <code style="color: var(--accent-cyan); font-weight: 700;">${mem.verified_runbook || "N/A"}</code>
        </div>
        ${mem.failed_mitigations && mem.failed_mitigations.length > 0 ? `
          <div class="memory-detail" style="margin-top: 0.35rem; color: #f87171;">
            <strong>Warning - Failed Mitigation:</strong> ${mem.failed_mitigations[0]}
          </div>
        ` : ''}
      `;
      memoriesContainer.appendChild(card);
    });
  } else {
    if (!data.memory_used) {
      document.getElementById("recall-meta").textContent = "Continuous memory disabled (Stateless Mode). Zero memory queries executed.";
      memoriesContainer.innerHTML = `
        <div style="font-size: 0.8rem; color: var(--accent-amber); font-style: italic; padding: 0.5rem 0;">
          Continuous memory recall was explicitly bypassed. Analysis generated statelessly without historical evidence.
        </div>
      `;
    } else {
      document.getElementById("recall-meta").textContent = "0 prior incident matches found in Hindsight memory bank. Truthful metrics: No fabricated history.";
      memoriesContainer.innerHTML = `
        <div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic; padding: 0.5rem 0;">
          No sufficiently relevant historical incidents match this failure pattern in Hindsight.
        </div>
      `;
    }
  }

  // Novelty vs Known Status Banners
  const noveltyBanner = document.getElementById("novelty-banner");
  const knownBanner = document.getElementById("known-banner");

  if (data.novelty) {
    noveltyBanner.classList.remove("hidden");
    knownBanner.classList.add("hidden");
    const bannerTitle = document.getElementById("novelty-banner-title");
    const bannerText = document.getElementById("novelty-text");
    if (!data.memory_used) {
      bannerTitle.textContent = "STATELESS SRE TRIAGE MODE:";
      bannerText.textContent = "Continuous memory recall bypassed by operator. Triage reasoning generated strictly from incoming alert telemetry.";
    } else {
      bannerTitle.textContent = "NOVEL FAILURE PATTERN DETECTED:";
      bannerText.textContent = "No sufficiently relevant historical incident found in Hindsight memory. Executed fresh first-principles reasoning without fabricating history.";
    }
  } else {
    noveltyBanner.classList.add("hidden");
    knownBanner.classList.remove("hidden");
    const firstMatch = data.historical_matches[0];
    document.getElementById("known-banner-title").innerHTML = `
      <span style="display: inline-flex; align-items: center; gap: 0.4rem;">
        <span class="badge badge-high" style="font-size: 0.68rem; background: rgba(16, 185, 129, 0.25); border: 1px solid #10b981; color: #34d399;">RECALLED FROM HINDSIGHT</span>
        HISTORICAL PRECEDENT MATCHED: ${firstMatch.incident_id}
      </span>
    `;
    document.getElementById("known-banner-text").innerHTML = `
      <div style="margin-top: 0.35rem; display: flex; flex-direction: column; gap: 0.25rem;">
        <div><strong>Recalled Root Cause:</strong> <span style="color: #f1f5f9;">${firstMatch.root_cause || data.likely_root_cause}</span></div>
        <div><strong>Verified Runbook:</strong> <code style="color: var(--accent-cyan); font-weight: 700;">${firstMatch.verified_runbook || (data.recommended_runbook ? data.recommended_runbook.runbook_id : 'N/A')}</code></div>
        <div><strong>Match Strength:</strong> <span class="badge ${matchStr === 'High' ? 'badge-high' : 'badge-moderate'}" style="font-size: 0.68rem;">${(data.match_strength || 'High').toUpperCase()}</span></div>
      </div>
    `;
  }

  // Diagnosis Panel - Visually distinguish Recalled Historical Evidence from Current AI Reasoning
  document.getElementById("triage-summary-text").textContent = data.incident_summary;

  if (data.historical_matches && data.historical_matches.length > 0) {
    const firstMatch = data.historical_matches[0];
    document.getElementById("rca-hypothesis").innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 0.35rem;">
        <div style="display: flex; align-items: center; gap: 0.4rem;">
          <span class="badge badge-high" style="font-size: 0.65rem; background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #34d399;">RECALLED HISTORICAL EVIDENCE</span>
          <span style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">${firstMatch.incident_id}</span>
        </div>
        <div style="color: #f8fafc; line-height: 1.5;">${firstMatch.root_cause || data.likely_root_cause}</div>
      </div>
    `;
  } else {
    document.getElementById("rca-hypothesis").innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 0.35rem;">
        <div style="display: flex; align-items: center; gap: 0.4rem;">
          <span class="badge" style="font-size: 0.65rem; background: rgba(168, 85, 247, 0.2); border: 1px solid #a855f7; color: #c084fc;">FIRST-PRINCIPLES HYPOTHESIS (NOVEL)</span>
        </div>
        <div style="color: #f8fafc; line-height: 1.5;">${data.likely_root_cause}</div>
      </div>
    `;
  }

  document.getElementById("sre-reasoning-summary").innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 0.35rem;">
      <div style="display: flex; align-items: center; gap: 0.4rem;">
        <span class="badge" style="font-size: 0.65rem; background: rgba(56, 189, 248, 0.2); border: 1px solid #38bdf8; color: #38bdf8;">ACTIVE AI COMMANDER REASONING</span>
      </div>
      <div style="color: #cbd5e1; line-height: 1.5;">${data.reasoning_summary}</div>
    </div>
  `;

  // Failed Mitigations to Avoid
  const failedList = document.getElementById("failed-mitigations-list");
  failedList.innerHTML = "";
  if (data.failed_mitigations_to_avoid && data.failed_mitigations_to_avoid.length > 0) {
    data.failed_mitigations_to_avoid.forEach((fm) => {
      const li = document.createElement("li");
      li.className = "failed-mitigation-item";
      li.innerHTML = `<span>⚠️</span> <span>${fm}</span>`;
      failedList.appendChild(li);
    });
  } else {
    failedList.innerHTML = `<li class="failed-mitigation-item"><span>ℹ️</span> <span>No specific historical anti-patterns recorded for this failure mode.</span></li>`;
  }

  // Recommended Runbook
  if (data.recommended_runbook) {
    currentRunbookRecommendation = data.recommended_runbook;
    renderRunbook(data.recommended_runbook);
  }

  // Update Memory Trace Drawer contents
  updateMemoryTraceDrawer(data, payload);

  // Draft Post-Mortem Preview
  draftPostMortemPreview(data);
}

function renderRunbook(rb) {
  document.getElementById("runbook-title").textContent = `${rb.runbook_id}: ${rb.title}`;
  document.getElementById("runbook-justification").textContent = `Justification: ${rb.justification}`;

  const statusBadge = document.getElementById("runbook-status-badge");
  statusBadge.textContent = rb.status || "PENDING_APPROVAL";
  if (rb.status === "APPROVED") {
    statusBadge.className = "badge badge-approved";
  } else if (rb.status === "REJECTED") {
    statusBadge.className = "badge badge-rejected";
  } else {
    statusBadge.className = "badge badge-pending";
  }

  // Render Action Steps
  const actionsList = document.getElementById("runbook-actions-list");
  actionsList.innerHTML = "";
  if (rb.actions && rb.actions.length > 0) {
    rb.actions.forEach((act) => {
      const item = document.createElement("div");
      item.style.background = "rgba(0,0,0,0.25)";
      item.style.padding = "0.6rem 0.8rem";
      item.style.borderRadius = "6px";
      item.style.border = "1px solid var(--border-color)";
      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
          <span style="font-weight: 600; font-size: 0.85rem;">Step ${act.step_number}: ${act.name}</span>
          <span class="badge ${act.is_safe_simulation ? 'badge-high' : 'badge-moderate'}" style="font-size: 0.65rem;">
            ${act.is_safe_simulation ? 'SAFE SIMULATION' : 'STATE CHANGING'}
          </span>
        </div>
        <div style="font-family: var(--font-mono); font-size: 0.8rem; color: #fbbf24; background: #000; padding: 0.4rem; border-radius: 4px;">
          ${act.command}
        </div>
        <div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 0.3rem;">
          ${act.description || ''}
        </div>
      `;
      actionsList.appendChild(item);
    });
  } else {
    actionsList.innerHTML = `<div style="font-size: 0.82rem; color: var(--text-muted);">No actionable steps loaded.</div>`;
  }

  // Reset console
  const consoleEl = document.getElementById("terminal-console");
  consoleEl.innerHTML = `
    <div class="terminal-line">[SYSTEM] Runbook '${rb.runbook_id}' loaded. Status: ${rb.status || 'PENDING_APPROVAL'}.</div>
    <div class="terminal-line audit">[INVARIANT 4] Simulation execution strictly requires explicit human approval.</div>
  `;
}

async function approveCurrentRunbook() {
  if (!currentRunbookRecommendation) {
    alert("No runbook recommendation active to approve.");
    return;
  }
  const approver = prompt("Enter SRE Approver Name/Email:", "lead-sre@company.internal");
  if (!approver) return;

  try {
    const res = await fetch(`/api/runbooks/${currentRunbookRecommendation.id}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": "sre-key-oncall",
      },
      body: JSON.stringify({ notes: "Approved for simulation by Lead SRE" }),
    });
    if (!res.ok) throw new Error("Approval failed");
    const updated = await res.json();
    currentRunbookRecommendation = updated;
    renderRunbook(updated);

    const consoleEl = document.getElementById("terminal-console");
    consoleEl.innerHTML += `
      <div class="terminal-line ok">[AUTHORIZATION APPROVED] Runbook '${updated.runbook_id}' approved by '${updated.approver}'.</div>
      <div class="terminal-line">[INFO] Safety harness unlocked. You may now execute dry-run simulation.</div>
    `;
    consoleEl.scrollTop = consoleEl.scrollHeight;
  } catch (err) {
    alert("Approval error: " + err.message);
  }
}

async function rejectCurrentRunbook() {
  if (!currentRunbookRecommendation) return;
  const reason = prompt("Enter Rejection Reason:", "Alternative mitigation selected; blast radius unacceptable.");
  if (!reason) return;

  try {
    const res = await fetch(`/api/runbooks/${currentRunbookRecommendation.id}/reject`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": "sre-key-oncall",
      },
      body: JSON.stringify({ reason: reason }),
    });
    const updated = await res.json();
    currentRunbookRecommendation = updated;
    renderRunbook(updated);

    const consoleEl = document.getElementById("terminal-console");
    consoleEl.innerHTML += `
      <div class="terminal-line err">[REJECTED] Runbook rejected: ${reason}</div>
    `;
    consoleEl.scrollTop = consoleEl.scrollHeight;
  } catch (err) {
    alert("Rejection error: " + err.message);
  }
}

async function simulateCurrentRunbook() {
  if (!currentRunbookRecommendation) {
    alert("No active runbook recommendation.");
    return;
  }

  const consoleEl = document.getElementById("terminal-console");
  consoleEl.innerHTML += `
    <div class="terminal-line cmd">> Initiating dry-run simulation request...</div>
  `;

  try {
    const res = await fetch(`/api/runbooks/${currentRunbookRecommendation.id}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ executor: "lead-sre" }),
    });

    if (!res.ok) {
      const err = await res.json();
      consoleEl.innerHTML += `
        <div class="terminal-line err">[BLOCKED - INVARIANT 4 VIOLATION] ${err.detail}</div>
        <div class="terminal-line err">>> You must click 'Approve Runbook' before dry-run execution is permitted.</div>
      `;
      consoleEl.scrollTop = consoleEl.scrollHeight;
      return;
    }

    const sim = await res.json();
    sim.logs.forEach((log) => {
      let cls = "terminal-line";
      if (log.includes("[AUDIT]")) cls += " audit";
      else if (log.includes("[STEP")) cls += " step";
      else if (log.includes(">>")) cls += " ok";
      else if (log.includes("$")) cls += " cmd";
      else if (log.includes("[SUCCESS]")) cls += " ok";

      consoleEl.innerHTML += `<div class="${cls}">${log}</div>`;
    });
    consoleEl.scrollTop = consoleEl.scrollHeight;
  } catch (err) {
    consoleEl.innerHTML += `<div class="terminal-line err">[ERROR] ${err.message}</div>`;
  }
}

function updateMemoryTraceDrawer(data, payload) {
  document.getElementById("trace-bank-id").textContent = "sre-incidentops-production";
  document.getElementById("trace-memory-mode").textContent = data.memory_used ? "Active (Genuine Hindsight API)" : "Bypassed (Stateless Mode)";
  document.getElementById("trace-match-strength").textContent = data.match_strength || (data.historical_matches.length > 0 ? "High" : "None");

  // Ground Truth Facts List
  const factsList = document.getElementById("trace-historical-facts");
  factsList.innerHTML = "";
  if (data.historical_matches && data.historical_matches.length > 0) {
    data.historical_matches.forEach((m) => {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${m.incident_id} (${m.service}):</strong> ${m.root_cause || m.title} | Runbook: <code>${m.verified_runbook || 'N/A'}</code>`;
      factsList.appendChild(li);
    });
    if (data.failed_mitigations_to_avoid && data.failed_mitigations_to_avoid.length > 0) {
      data.failed_mitigations_to_avoid.forEach((fm) => {
        const li = document.createElement("li");
        li.style.color = "#fecdd3";
        li.innerHTML = `<strong>Documented Failure:</strong> ${fm}`;
        factsList.appendChild(li);
      });
    }
  } else {
    factsList.innerHTML = `<li>Zero historical memories recalled (Novel failure mode or memory disabled).</li>`;
  }

  // AI Reasoning
  document.getElementById("trace-ai-reasoning").textContent = data.reasoning_summary || data.likely_root_cause;

  // Raw JSON Inspector
  document.getElementById("trace-raw-json").textContent = JSON.stringify(data, null, 2);
}

async function draftPostMortemPreview(triageData) {
  try {
    const previewEl = document.getElementById("postmortem-preview");
    if (!previewEl) return;

    const service = document.getElementById("alert-service").value.trim();
    const title = document.getElementById("alert-title").value.trim();
    const symptomsRaw = document.getElementById("alert-symptoms").value.trim();
    const symptoms = symptomsRaw ? symptomsRaw.split(",").map((s) => s.trim()).filter(Boolean) : [];
    const severity = document.getElementById("alert-severity-badge").textContent;

    const existingMatch = triageData.historical_matches && triageData.historical_matches.length > 0 ? triageData.historical_matches[0].incident_id : null;
    const incidentId = existingMatch || `INC-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;

    const verifiedRunbook = triageData.recommended_runbook ? triageData.recommended_runbook.runbook_id : `RB-${service.toUpperCase().replace(/[^A-Z0-9]/g, '-')}-RESOLVE`;

    const draft = {
      bank_id: "sre-incidentops-production",
      incident_id: incidentId,
      service: service,
      severity: severity,
      alert_signature: title,
      title: `${incidentId}: ${title}`,
      symptoms: symptoms,
      root_cause: triageData.likely_root_cause,
      failed_mitigations: triageData.failed_mitigations_to_avoid && triageData.failed_mitigations_to_avoid.length > 0 ? triageData.failed_mitigations_to_avoid : [
        `Restarting ${service} pods alone causes immediate retry storm on degraded resources.`,
        `Increasing replica count aggravates upstream dependency connection pool limits.`
      ],
      verified_runbook: verifiedRunbook,
      postmortem_summary: triageData.incident_summary,
      resolution: `Applied ${verifiedRunbook} to mitigate root cause and restore normal metrics.`,
      tags: [service, severity, verifiedRunbook, incidentId],
      created_at: new Date().toISOString(),
      // Provenance: Initial AI draft is strictly DRAFT / AI_DRAFT
      memory_status: "DRAFT",
      source_type: "AI_DRAFT",
      verified_by: null,
      verified_at: null,
      source_incident_id: incidentId,
    };
    triageData._draft_postmortem = draft;
    previewEl.textContent = JSON.stringify(draft, null, 2);
  } catch (err) {
    console.error("Error drafting postmortem preview:", err);
  }
}

async function commitPostMortem() {
  if (!currentTriageResponse || !currentTriageResponse._draft_postmortem) {
    alert("Please execute alert triage first before committing a post-mortem.");
    return;
  }

  const btn = document.getElementById("btn-commit-postmortem");
  const statusEl = document.getElementById("postmortem-status");
  btn.disabled = true;
  const originalBtnHTML = btn.innerHTML;
  btn.innerHTML = `<span class="spinner" style="display:inline-block; width:12px; height:12px; margin-right:6px;"></span> Committing to Hindsight...`;

  try {
    // Authenticated Human SRE verification and commit action: promotes DRAFT -> VERIFIED
    const draft = currentTriageResponse._draft_postmortem;
    const commitPayload = {
      incident_id: draft.incident_id,
      title: draft.title,
      service: draft.service,
      severity: draft.severity,
      trigger: (draft.symptoms && draft.symptoms.length > 0) ? draft.symptoms.join(", ") : draft.title,
      root_cause: draft.root_cause,
      impact_summary: draft.postmortem_summary,
      timeline: draft.timeline || [],
      resolution_steps: [draft.resolution],
      runbook_executed: draft.verified_runbook,
      preventative_actions: draft.lessons_learned || [],
      tags: draft.tags || [],
      source_incident_id: draft.incident_id,
    };

    // Authenticated POST /api/postmortems/commit endpoint with verified SRE credential
    const res = await fetch("/api/postmortems/commit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": "sre-key-oncall",
      },
      body: JSON.stringify(commitPayload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed committing to Hindsight");
    }

    const data = await res.json();
    const draft = currentTriageResponse._draft_postmortem;
    statusEl.classList.remove("hidden");
    statusEl.innerHTML = `
      <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 8px; padding: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.8rem;">
          <div>
            <div style="font-weight: 700; color: #34d399; font-size: 0.95rem; display: flex; align-items: center; gap: 0.4rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              Memory Verified & Retained in Hindsight
            </div>
            <div style="font-size: 0.82rem; color: #cbd5e1; margin-top: 0.35rem;">
              Incident <code style="color: var(--accent-cyan); font-weight: 700;">${data.incident_id}</code> (${draft.service}) verified by <code style="color: #34d399; font-weight: 600;">${data.verified_by || 'oncall-sre'}</code> and committed to memory bank <code style="color: #a78bfa;">'${data.bank_id}'</code>.<br>
              Verified runbook: <code style="color: #fbbf24; font-weight: 600;">${draft.verified_runbook}</code>.
            </div>
          </div>
          <button class="btn btn-primary" id="btn-simulate-repeat" style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); border: none; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.65rem 1.25rem; border-radius: 6px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
            Simulate Repeat Alert
          </button>
        </div>
      </div>
    `;

    // Attach click listener for Simulate Repeat Alert button
    const repeatBtn = document.getElementById("btn-simulate-repeat");
    if (repeatBtn) {
      repeatBtn.addEventListener("click", () => {
        // Ensure memory toggle is explicitly enabled
        const toggle = document.getElementById("memory-toggle");
        if (toggle && !toggle.checked) {
          toggle.checked = true;
          isMemoryEnabled = true;
          toggle.dispatchEvent(new Event("change"));
        } else {
          isMemoryEnabled = true;
        }

        // Re-execute triage on the current/same alert
        executeTriage();
      });
    }
  } catch (err) {
    alert("Commit error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalBtnHTML;
  }
}

async function seedHindsightMemory() {
  const btn = document.getElementById("btn-seed-hindsight");
  btn.disabled = true;
  btn.textContent = "Seeding Hindsight...";

  try {
    const res = await fetch("/api/memory/seed", { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Seeding failed");
    }
    const data = await res.json();
    alert(`Seeded ${data.total_seeded} realistic historical SRE incidents (including INC-104 & INC-108) directly into Hindsight memory bank '${data.bank_id}'!`);
    checkSystemHealth();
  } catch (err) {
    alert("Seeding error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      Seed Hindsight
    `;
  }
}

/* ==========================================================================
   3D REALTIME PIPELINE VISUALIZATION (THREE.JS)
   ========================================================================== */

function init3DPipeline() {
  const canvas = document.getElementById("pipeline-canvas");
  const wrapper = document.getElementById("pipeline-wrapper");
  const fallback = document.getElementById("pipeline-fallback");

  if (!canvas || typeof THREE === "undefined") {
    if (fallback) fallback.classList.remove("hidden");
    if (canvas) canvas.classList.add("hidden");
    return;
  }

  try {
    const width = wrapper.clientWidth || 900;
    const height = wrapper.clientHeight || 180;

    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x07090e, 0.025);

    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0, 24);

    renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Ambient and Directional Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x38bdf8, 2, 50);
    pointLight.position.set(0, 5, 10);
    scene.add(pointLight);

    // Build Pipeline Nodes: ALERT -> HINDSIGHT -> EVIDENCE -> DIAGNOSIS -> RUNBOOK
    const nodeSpecs = [
      { id: "alert", name: "ALERT", x: -14, color: 0xf43f5e, emissive: 0xf43f5e },
      { id: "hindsight", name: "HINDSIGHT", x: -7, color: 0x10b981, emissive: 0x10b981 },
      { id: "evidence", name: "EVIDENCE", x: 0, color: 0x38bdf8, emissive: 0x38bdf8 },
      { id: "diagnosis", name: "DIAGNOSIS", x: 7, color: 0xa855f7, emissive: 0xa855f7 },
      { id: "runbook", name: "RUNBOOK", x: 14, color: 0xf59e0b, emissive: 0xf59e0b },
    ];

    const sphereGeom = new THREE.SphereGeometry(1.2, 32, 32);
    const ringGeom = new THREE.RingGeometry(1.6, 1.85, 32);

    pipelineNodes = nodeSpecs.map((spec) => {
      const mat = new THREE.MeshStandardMaterial({
        color: spec.color,
        emissive: spec.emissive,
        emissiveIntensity: 0.6,
        roughness: 0.3,
        metalness: 0.2,
      });
      const mesh = new THREE.Mesh(sphereGeom, mat);
      mesh.position.set(spec.x, 0, 0);

      // Orbital Glow Ring
      const ringMat = new THREE.MeshBasicMaterial({ color: spec.color, side: THREE.DoubleSide, transparent: true, opacity: 0.4 });
      const ring = new THREE.Mesh(ringGeom, ringMat);
      mesh.add(ring);

      scene.add(mesh);
      return { id: spec.id, mesh: mesh, ring: ring, baseColor: spec.color, origX: spec.x };
    });

    // Connecting Tubes/Lines
    createPipelineConnections();

    // Particle Streams
    createFlowParticles();

    if (!isReducedMotion) {
      animate3DPipeline();
    } else {
      renderer.render(scene, camera);
    }
  } catch (err) {
    console.warn("WebGL initialization failed, switching to graceful fallback:", err);
    if (fallback) fallback.classList.remove("hidden");
    if (canvas) canvas.classList.add("hidden");
  }
}

function createPipelineConnections() {
  pipelineConnections.forEach((c) => scene.remove(c));
  pipelineConnections = [];

  const lineMat = new THREE.LineBasicMaterial({ color: 0x334155, transparent: true, opacity: 0.7 });

  for (let i = 0; i < pipelineNodes.length - 1; i++) {
    const p1 = pipelineNodes[i].mesh.position;
    const p2 = pipelineNodes[i + 1].mesh.position;
    const geom = new THREE.BufferGeometry().setFromPoints([p1, p2]);
    const line = new THREE.Line(geom, lineMat);
    scene.add(line);
    pipelineConnections.push(line);
  }
}

function createFlowParticles() {
  flowParticles.forEach((p) => scene.remove(p.mesh));
  flowParticles = [];

  const particleGeom = new THREE.SphereGeometry(0.25, 16, 16);
  const particleCount = 18;

  for (let i = 0; i < particleCount; i++) {
    const mat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.9 });
    const mesh = new THREE.Mesh(particleGeom, mat);
    mesh.position.set(-14 + (i / particleCount) * 28, (Math.random() - 0.5) * 0.4, 0);
    scene.add(mesh);
    flowParticles.push({
      mesh: mesh,
      speed: 0.12 + Math.random() * 0.08,
      progress: i / particleCount,
    });
  }
}

function update3DPipelineMemoryMode(enabled) {
  const hindsightNode = pipelineNodes.find((n) => n.id === "hindsight");
  if (!hindsightNode) return;

  if (enabled) {
    hindsightNode.mesh.material.color.setHex(0x10b981);
    hindsightNode.mesh.material.emissive.setHex(0x10b981);
    hindsightNode.mesh.material.emissiveIntensity = 0.6;
    hindsightNode.ring.material.color.setHex(0x10b981);
    hindsightNode.ring.material.opacity = 0.4;
  } else {
    // Dimmed / Bypassed in stateless mode
    hindsightNode.mesh.material.color.setHex(0x475569);
    hindsightNode.mesh.material.emissive.setHex(0x334155);
    hindsightNode.mesh.material.emissiveIntensity = 0.2;
    hindsightNode.ring.material.color.setHex(0x475569);
    hindsightNode.ring.material.opacity = 0.15;
  }
}

function triggerPipelinePulse() {
  pipelineNodes.forEach((node) => {
    node.mesh.scale.set(1.4, 1.4, 1.4);
    setTimeout(() => {
      node.mesh.scale.set(1, 1, 1);
    }, 450);
  });
}

function animate3DPipeline() {
  animationFrameId = requestAnimationFrame(animate3DPipeline);

  const time = Date.now() * 0.002;

  // Gentle node rotation
  pipelineNodes.forEach((node, idx) => {
    node.ring.rotation.z += 0.02;
    node.ring.rotation.x = Math.sin(time + idx) * 0.3;
    node.mesh.position.y = Math.sin(time + idx * 0.8) * 0.35;
  });

  // Flow particles along the pipeline
  flowParticles.forEach((p) => {
    p.progress += (isTriageRunning ? 0.025 : 0.008);
    if (p.progress > 1) p.progress = 0;

    let x = -14 + p.progress * 28;

    // In stateless mode, skip through or dip around Hindsight node
    let y = 0;
    if (!isMemoryEnabled && x > -9 && x < -5) {
      y = Math.sin((x + 7) * Math.PI / 2) * 1.8; // arc over bypassed memory node
    }
    p.mesh.position.set(x, y + Math.sin(time * 3 + x) * 0.15, 0);
  });

  renderer.render(scene, camera);
}

function onWindowResize() {
  const wrapper = document.getElementById("pipeline-wrapper");
  if (!wrapper || !renderer || !camera) return;

  const width = wrapper.clientWidth || 900;
  const height = wrapper.clientHeight || 180;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}
