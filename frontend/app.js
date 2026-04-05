const tabs = document.querySelectorAll(".tab");
const tabsContainer = document.querySelector(".tabs");
const tabIndicator = document.querySelector(".tab-indicator");
const blocks = document.querySelectorAll(".mode-block");
const modeTipNode = document.getElementById("mode-tip");
const controlsPanel = document.querySelector(".controls");
const form = document.getElementById("analyzer-form");
const runBtn = document.getElementById("run-btn");
const cancelBtn = document.getElementById("cancel-btn");
const statusNode = document.getElementById("status");
const resultsNode = document.getElementById("results");
const processPanel = document.getElementById("process-panel");
const previewNode = document.getElementById("process-preview");
const stepsNode = document.getElementById("process-steps");
const progressTimerNode = document.createElement("p");
progressTimerNode.className = "process-timer";
progressTimerNode.textContent = "Time: 00:00";
const processHeading = processPanel ? processPanel.querySelector("h3") : null;
if (processHeading && processHeading.parentNode) {
  processHeading.insertAdjacentElement("afterend", progressTimerNode);
}
const reportTools = document.getElementById("report-tools");
const reportLang = document.getElementById("report-lang");
const translateBtn = document.getElementById("translate-btn");
const resetTranslateBtn = document.getElementById("reset-translate-btn");
const translateStatus = document.getElementById("translate-status");
const inlineSourcePreview = document.getElementById("inline-source-preview");
const inlineSourcePreviewBody = document.getElementById("inline-source-preview-body");
const claimAdvisoryNode = document.getElementById("claim-advisory");
const claimTextNode = document.getElementById("claim-text");
const appMainNode = document.getElementById("app-main");
const welcomeNode = document.getElementById("welcome-screen");
const enterAppBtn = document.getElementById("enter-app-btn");
const pdfPageRangeInput = document.getElementById("pdf-page-range");
const pdfPageWarningNode = document.getElementById("pdf-page-warning");

let mode = "claim";
let currentController = null;
let progressTimer = null;
let elapsedTimer = null;
let progressStartedAt = null;
let basePreview = "";
let progressPollTimer = null;
let currentProgressId = null;
let currentProgressSnapshot = null;
let originalReport = null;
let renderedReport = null;
let reportLanguageOverride = null;
let modeSwitchTimeout = null;
let currentImagePreviewUrl = null;
let currentImageClaimSelectionState = null;

const modeTips = {
  claim: "Tip: include a concrete subject, timeframe, and measurable fact for better evidence retrieval.",
  pdf: "Tip: scanned and text-layer PDFs are supported. Long technical pages may use hybrid selection.",
  image: "Tip: clearer text and tighter crops improve OCR precision and evidence ranking quality.",
};

function moveTabIndicatorToActive() {
  if (!tabsContainer || !tabIndicator) return;
  const activeTab = tabsContainer.querySelector(".tab.active");
  if (!activeTab) return;

  const containerRect = tabsContainer.getBoundingClientRect();
  const activeRect = activeTab.getBoundingClientRect();
  const left = activeRect.left - containerRect.left;
  const width = activeRect.width;

  tabIndicator.style.width = `${width}px`;
  tabIndicator.style.transform = `translateX(${left}px)`;
}

function setMode(nextMode) {
  mode = nextMode;
  tabs.forEach((t) => t.classList.toggle("active", t.dataset.mode === mode));
  blocks.forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  if (modeTipNode) modeTipNode.textContent = modeTips[mode] || modeTips.claim;
  moveTabIndicatorToActive();

  if (controlsPanel) {
    controlsPanel.classList.add("is-switching");
    if (modeSwitchTimeout) clearTimeout(modeSwitchTimeout);
    modeSwitchTimeout = setTimeout(() => {
      controlsPanel.classList.remove("is-switching");
    }, 220);
  }
}

function enterMainApp() {
  document.body.classList.remove("home-mode");
  document.body.classList.add("app-mode");

  if (welcomeNode) {
    welcomeNode.style.pointerEvents = "none";
    welcomeNode.classList.add("is-leaving");
  }

  if (appMainNode) {
    appMainNode.hidden = false;
    appMainNode.classList.add("app-preenter");
    requestAnimationFrame(() => {
      appMainNode.classList.remove("app-preenter");
      appMainNode.classList.add("app-enter");
    });
    appMainNode.scrollTop = 0;
  }

  window.scrollTo({ top: 0, left: 0, behavior: "auto" });

  const finalizeHideWelcome = () => {
    if (!welcomeNode) return;
    welcomeNode.hidden = true;
    welcomeNode.classList.remove("is-leaving");
    welcomeNode.style.pointerEvents = "";
  };

  if (welcomeNode) {
    welcomeNode.addEventListener("transitionend", finalizeHideWelcome, { once: true });
  }
  setTimeout(finalizeHideWelcome, 320);

  moveTabIndicatorToActive();
}

function initWelcomeFlow() {
  if (!appMainNode) return;
  document.body.classList.add("home-mode");
  appMainNode.hidden = true;
  if (welcomeNode) welcomeNode.hidden = false;

  if (enterAppBtn) {
    enterAppBtn.addEventListener("click", () => {
      enterMainApp();
    });
  }
}

function setActiveInputLocked(locked) {
  if (mode === "claim") {
    const node = document.getElementById("claim-text");
    if (node) node.readOnly = locked;
    return;
  }
  if (mode === "pdf") {
    const fileNode = document.getElementById("pdf-file");
    const rangeNode = document.getElementById("pdf-page-range");
    if (fileNode) fileNode.disabled = locked;
    if (rangeNode) rangeNode.disabled = locked;
    return;
  }
  const node = document.getElementById("image-file");
  if (node) node.disabled = locked;
}

function getProgressPreviewLabel() {
  if (mode === "claim") return "Claim analysis in progress";
  if (mode === "pdf") return "PDF analysis in progress";
  return "Image analysis in progress";
}

const defaultWorkflowStages = {
  claim: ["Input", "Language", "Structured APIs", "Web Search", "Extraction", "Relevance", "Stance", "Verdict"],
  pdf: ["Input", "Document Parsing", "Claim Selection", "Language", "Structured APIs", "Web Search", "Extraction", "Relevance", "Stance", "Verdict"],
  image: ["Input", "OCR", "Claim Selection", "Language", "Structured APIs", "Web Search", "Extraction", "Relevance", "Stance", "Verdict"],
};

for (const tab of tabs) {
  tab.addEventListener("click", () => {
    setMode(tab.dataset.mode);
    resultsNode.innerHTML = "";
    statusNode.textContent = "";
    renderTopAdvisory(null);
    hideReportTools();
    resetProgressPanel();
  });
}

window.addEventListener("resize", moveTabIndicatorToActive);

initWelcomeFlow();
setMode(mode);

const imageFileInput = document.getElementById("image-file");
if (imageFileInput) {
  imageFileInput.addEventListener("change", () => {
    if (currentImagePreviewUrl) {
      URL.revokeObjectURL(currentImagePreviewUrl);
      currentImagePreviewUrl = null;
    }
    const file = imageFileInput.files && imageFileInput.files[0];
    if (file) {
      currentImagePreviewUrl = URL.createObjectURL(file);
    }
  });
}

if (pdfPageRangeInput) {
  pdfPageRangeInput.addEventListener("input", () => {
    renderPdfPageRangeWarning();
  });
}

function getPdfPageRangeWarning() {
  const raw = String(pdfPageRangeInput?.value || "").trim();
  if (!raw) return "";
  const match = raw.match(/^(\d+)(?:\s*-\s*(\d+))?$/);
  if (!match) return "Use page format like 1 or 1-2.";
  const start = Number(match[1]);
  const end = Number(match[2] || match[1]);
  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 1 || end < start) {
    return "Enter a valid page selection.";
  }
  if ((end - start + 1) > 5) {
    return "Select up to 5 pages at a time.";
  }
  return "";
}

function renderPdfPageRangeWarning() {
  if (!pdfPageWarningNode) return;
  const warning = getPdfPageRangeWarning();
  pdfPageWarningNode.textContent = warning;
  pdfPageWarningNode.hidden = !warning;
}

cancelBtn.addEventListener("click", () => {
  if (currentController) {
    currentController.abort();
    statusNode.textContent = "Cancelled.";
  }
});

resultsNode.addEventListener("click", async (event) => {
  const trigger = event.target.closest("[data-image-claim-translate]");
  if (!trigger) return;
  if (!currentImageClaimSelectionState) return;

  const bodyNode = resultsNode.querySelector("[data-image-claim-selection-body]");
  if (!bodyNode) return;

  const wantsOriginal = trigger.dataset.state === "translated";
  if (wantsOriginal) {
    bodyNode.innerHTML = renderImageClaimSelectionBody(currentImageClaimSelectionState.original);
    trigger.textContent = "Translate";
    trigger.dataset.state = "original";
    return;
  }

  trigger.disabled = true;
  const priorText = trigger.textContent;
  trigger.textContent = "Translating...";
  try {
    if (!currentImageClaimSelectionState.translated) {
      const payload = await postJson("/translate_report", {
        report: currentImageClaimSelectionState.original,
        target_lang: "en",
      });
      currentImageClaimSelectionState.translated = payload.report || null;
    }
    const translated = currentImageClaimSelectionState.translated;
    if (translated) {
      bodyNode.innerHTML = renderImageClaimSelectionBody(translated, { label: "English translation" });
      trigger.textContent = "Original";
      trigger.dataset.state = "translated";
    } else {
      trigger.textContent = priorText;
    }
  } catch (_) {
    trigger.textContent = priorText;
  } finally {
    trigger.disabled = false;
  }
});

translateBtn.addEventListener("click", async () => {
  if (!originalReport) return;
  translateBtn.disabled = true;
  translateStatus.textContent = "Translating...";
  try {
    const payload = await postJson("/translate_report", {
      report: originalReport,
      target_lang: reportLang.value,
    });
    renderedReport = payload.report;
    reportLanguageOverride = payload.target_lang || reportLang.value;
    renderResult(renderedReport);
    resetTranslateBtn.hidden = false;
    translateStatus.textContent = `Translated to ${reportLang.value}.`;
  } catch (error) {
    translateStatus.textContent = `Translation failed: ${error.message}`;
  } finally {
    translateBtn.disabled = false;
  }
});

resetTranslateBtn.addEventListener("click", () => {
  if (!originalReport) return;
  renderedReport = originalReport;
  reportLanguageOverride = null;
  renderResult(renderedReport);
  translateStatus.textContent = "Showing original report.";
  resetTranslateBtn.hidden = true;
  reportLang.value = "en";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  runBtn.disabled = true;
  cancelBtn.hidden = false;
  setActiveInputLocked(true);
  const claimInput = claimTextNode ? String(claimTextNode.value || "").trim() : "";
  if (mode === "claim" && !claimInput) {
    statusNode.textContent = "Please enter a claim.";
    resultsNode.innerHTML = "";
    renderTopAdvisory(null);
    runBtn.disabled = false;
    cancelBtn.hidden = true;
    setActiveInputLocked(false);
    return;
  }

  const localWarnings = getLocalClaimWarnings();
  const blockingWarning = localWarnings.find((warning) => warning?.block);
  const pdfPageRangeWarning = mode === "pdf" ? getPdfPageRangeWarning() : "";
  statusNode.textContent = "Analyzing...";
  resultsNode.innerHTML = "";
  renderTopAdvisory({ ux_warnings: localWarnings });
  hideReportTools();

  if (blockingWarning || pdfPageRangeWarning) {
    statusNode.textContent = pdfPageRangeWarning || "Add a little more context before analysis.";
    renderPdfPageRangeWarning();
    resetProgressPanel();
    runBtn.disabled = false;
    cancelBtn.hidden = true;
    setActiveInputLocked(false);
    return;
  }

  const progressId = createProgressId();
  startProgressForCurrentInput(progressId);
  currentController = new AbortController();

  try {
    const data = await callApiForMode(currentController.signal, progressId);
    originalReport = data;
    renderedReport = data;
    enrichProgressWithResponse(data);
    completeProgress();
    renderResult(renderedReport);
    renderTopAdvisory(renderedReport);
    showReportTools();
    statusNode.textContent = "Done.";
  } catch (error) {
    if (error.name === "AbortError") {
      statusNode.textContent = "Cancelled.";
      renderWorkflow({
        status: "cancelled",
        stages: [{
          id: "cancelled",
          label: "Cancelled",
          status: "cancelled",
          detail: "Process cancelled by user.",
          substeps: [],
        }],
      });
    } else {
      statusNode.textContent = "Failed.";
      renderWorkflow({
        status: "error",
        stages: [{
          id: "error",
          label: "Error",
          status: "error",
          detail: error.message,
          substeps: [],
        }],
      });
      renderTopAdvisory(null);
      resultsNode.innerHTML = cardHtml("Error", `<p>${escapeHtml(error.message)}</p>`);
    }
  } finally {
    stopProgressTimers();
    currentController = null;
    runBtn.disabled = false;
    cancelBtn.hidden = true;
    setActiveInputLocked(false);
  }
});

function getCurrentInputPreview() {
  if (mode === "claim") {
    const claim = document.getElementById("claim-text").value.trim();
    return claim ? `Claim: ${truncate(claim, 240)}` : "Claim: No claim entered";
  }
  if (mode === "pdf") {
    const file = document.getElementById("pdf-file").files[0];
    const pageRange = String(document.getElementById("pdf-page-range")?.value || "").trim();
    return file ? `PDF: ${file.name} (${formatKb(file.size)})${pageRange ? ` | Pages: ${pageRange}` : ""}` : "PDF: No file selected";
  }
  const file = document.getElementById("image-file").files[0];
  return file ? `Image: ${file.name} (${formatKb(file.size)})` : "Image: No file selected";
}

function createProgressId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `progress-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function buildPlaceholderWorkflow() {
  return {
    status: "running",
    stages: (defaultWorkflowStages[mode] || defaultWorkflowStages.claim).map((label, index) => ({
      id: `${mode}-${index}`,
      label,
      status: index === 0 ? "active" : "pending",
      detail: index === 0 ? "Queued for analysis" : "",
      substeps: [],
    })),
  };
}

function startProgressForCurrentInput(progressId) {
  processPanel.hidden = false;
  progressStartedAt = Date.now();
  basePreview = getProgressPreviewLabel();
  currentProgressId = progressId;
  currentProgressSnapshot = buildPlaceholderWorkflow();
  const advisoryMessage = getPrimaryAdvisoryMessage();
  previewNode.textContent = advisoryMessage ? `${basePreview} | Advisory: ${advisoryMessage}` : basePreview;
  renderWorkflow(currentProgressSnapshot);

  stopProgressTimers();
  updateElapsedTimer();
  elapsedTimer = setInterval(updateElapsedTimer, 1000);
  startProgressPolling(progressId);
}

function enrichProgressWithResponse(data) {
  const verdict = extractVerdict(data);
  previewNode.textContent = `${basePreview} | Final verdict: ${verdict}`;
  if (currentProgressSnapshot) {
    finalizeWorkflowSnapshot(verdict);
  }
}

function finalizeWorkflowSnapshot(verdictLabel = "Completed") {
  if (!currentProgressSnapshot || !Array.isArray(currentProgressSnapshot.stages)) return;
  currentProgressSnapshot.status = "done";
  currentProgressSnapshot.final_detail = verdictLabel;
  currentProgressSnapshot.stages = currentProgressSnapshot.stages.map((stage) => {
    const nextStage = {
      ...stage,
      status: stage.status === "error" || stage.status === "cancelled" ? stage.status : "done",
      substeps: Array.isArray(stage.substeps)
        ? stage.substeps.map((substep) => ({
          ...substep,
          status: substep.status === "error" ? "error" : "done",
        }))
        : [],
    };
    if (nextStage.id === "verdict") {
      nextStage.detail = verdictLabel;
    } else if (!nextStage.detail) {
      nextStage.detail = "Completed";
    }
    return nextStage;
  });
  renderWorkflow(currentProgressSnapshot);
}

function renderWorkflow(payload) {
  const allStages = Array.isArray(payload?.stages) ? payload.stages : [];
  const stages = allStages.filter((stage) => {
    const status = String(stage?.status || "pending");
    return status !== "pending";
  });
  if (!stages.length) {
    stepsNode.innerHTML = "";
    return;
  }
  stepsNode.innerHTML = stages.map((stage, index) => {
    const stageStatus = escapeAttr(stage.status || "pending");
    const detail = stage.detail ? `<div class="step-detail">${escapeHtml(stage.detail)}</div>` : "";
    const visibleSubsteps = Array.isArray(stage.substeps)
      ? stage.substeps.filter((substep) => ["active", "done", "error"].includes(substep.status || ""))
      : [];
    const substeps = visibleSubsteps.length
      ? `<div class="step-substeps">${visibleSubsteps.map((substep) => `
          <div class="step-substep ${escapeAttr(substep.status || "pending")}">
            <span class="substep-dot"></span>
            <span class="substep-label">${escapeHtml(substep.label || substep.id || "Step")}</span>
            ${substep.detail ? `<span class="substep-detail">${escapeHtml(substep.detail)}</span>` : ""}
          </div>
        `).join("")}</div>`
      : "";
    const connector = index < stages.length - 1 ? '<span class="step-connector" aria-hidden="true"></span>' : "";
    const isParallel = ["structured_api", "web_search", "extraction"].includes(stage.id) && visibleSubsteps.length > 1;
    const isIterative = ["claim_selection", "document_parse"].includes(stage.id) && visibleSubsteps.length > 1;
    const summaryMeta = [
      isParallel ? '<span class="workflow-chip">Parallel</span>' : "",
      isIterative ? '<span class="workflow-chip workflow-chip-soft">Loop</span>' : "",
    ].filter(Boolean).join("");
    const disclosureOpen = stage.status === "active" ? " open" : "";
    return `
      <li class="workflow-step ${stageStatus}${isParallel ? " parallel-stage" : ""}${isIterative ? " iterative-stage" : ""}">
        <div class="step-node-wrap">
          <span class="step-node" aria-hidden="true"></span>
          ${connector}
        </div>
        <details class="step-body"${disclosureOpen}>
          <summary class="step-summary">
            <span class="step-title">${escapeHtml(stage.label || stage.id || "Stage")}</span>
            ${summaryMeta}
          </summary>
          ${detail}
          ${substeps}
        </details>
      </li>
    `;
  }).join("");
}

function applyProgressPayload(payload) {
  currentProgressSnapshot = payload;
  if (payload?.status === "done") {
    const finalDetail = payload.final_detail || extractVerdict(renderedReport || originalReport || {}) || "Completed";
    finalizeWorkflowSnapshot(finalDetail);
    return;
  }
  const activeStage = (payload.stages || []).find((stage) => stage.status === "active");
  if (activeStage) {
    previewNode.textContent = `${basePreview} | Stage: ${activeStage.label}${activeStage.detail ? ` - ${activeStage.detail}` : ""}`;
  } else if (payload.final_detail) {
    previewNode.textContent = `${basePreview} | ${payload.final_detail}`;
  }
  renderWorkflow(payload);
}

function startProgressPolling(progressId) {
  const fetchProgress = async () => {
    if (!progressId || progressId !== currentProgressId) return;
    try {
      const response = await fetch(`/progress/${encodeURIComponent(progressId)}`);
      const payload = await response.json();
      if (!response.ok || payload.error) return;
      applyProgressPayload(payload);
      if (["done", "error", "cancelled"].includes(payload.status)) {
        stopProgressTimers();
        updateElapsedTimer();
      }
    } catch (_error) {
      return;
    }
  };

  fetchProgress();
  progressPollTimer = setInterval(fetchProgress, 700);
}

function completeProgress() {
  stopProgressTimers();
  const elapsedLabel = formatElapsedDuration();
  progressTimerNode.textContent = `Time: ${elapsedLabel}`;
  if (currentProgressSnapshot) {
    finalizeWorkflowSnapshot(extractVerdict(renderedReport || originalReport || {}));
  } else {
    renderWorkflow({
      status: "done",
      stages: [{
        id: "complete",
        label: "Completed",
        status: "done",
        detail: `Report generated successfully in ${elapsedLabel}.`,
        substeps: [],
      }],
    });
  }
}

function resetProgressPanel() {
  stopProgressTimers();
  processPanel.hidden = true;
  renderTopAdvisory(null);
  previewNode.textContent = "Submit a claim, PDF, or image to start.";
  progressTimerNode.textContent = "Time: 00:00";
  stepsNode.innerHTML = "";
  basePreview = "";
  currentProgressId = null;
  currentProgressSnapshot = null;
}

function stopProgressTimers() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  if (elapsedTimer) {
    clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
  if (progressPollTimer) {
    clearInterval(progressPollTimer);
    progressPollTimer = null;
  }
}

function updateElapsedTimer() {
  progressTimerNode.textContent = `Time: ${formatElapsedDuration()}`;
}

function formatElapsedDuration() {
  if (!progressStartedAt) return "00:00";
  const totalSeconds = Math.max(0, Math.floor((Date.now() - progressStartedAt) / 1000));
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function showReportTools() {
  reportTools.hidden = false;
  reportLang.value = "en";
  resetTranslateBtn.hidden = true;
  translateStatus.textContent = "";
}

function hideReportTools() {
  reportTools.hidden = true;
  translateStatus.textContent = "";
  originalReport = null;
  renderedReport = null;
  reportLanguageOverride = null;
  inlineSourcePreview.hidden = true;
  inlineSourcePreviewBody.innerHTML = "";
}

async function callApiForMode(signal, progressId = null) {
  if (mode === "claim") {
    const claim = document.getElementById("claim-text").value.trim();
    if (!claim) throw new Error("Please enter a claim.");
    return postJson("/check", { claim }, signal, { "X-Progress-Id": currentProgressId });
  }
  if (mode === "pdf") {
    const file = document.getElementById("pdf-file").files[0];
    if (!file) throw new Error("Please choose a PDF.");
    const pageRange = String(document.getElementById("pdf-page-range")?.value || "").trim();
    return postFile("/analyze_pdf", file, signal, { "X-Progress-Id": currentProgressId }, { page_range: pageRange });
  }
  const file = document.getElementById("image-file").files[0];
  if (!file) throw new Error("Please choose an image.");
  return postFile("/analyze_image", file, signal, { "X-Progress-Id": currentProgressId });
}

async function postJson(url, body, signal = null, headers = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
    signal,
  });
  return handleResponse(response);
}

async function postFile(url, file, signal = null, headers = {}, fields = {}) {
  const formData = new FormData();
  formData.append("file", file);
  Object.entries(fields || {}).forEach(([key, value]) => {
    if (value != null && String(value).trim()) formData.append(key, String(value).trim());
  });
  const response = await fetch(url, {
    method: "POST",
    body: formData,
    headers,
    signal,
  });
  return handleResponse(response);
}

async function handleResponse(response) {
  let payload = {};
  try {
    payload = await response.json();
  } catch (err) {
    throw new Error("Server returned an invalid response.");
  }
  if (!response.ok || payload.error) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function renderResult(data) {
  if (data.results && Array.isArray(data.results)) {
    renderDocumentResult(data);
    return;
  }
  renderClaimResult(data);
}

function renderDocumentResult(data) {
  resultsNode.classList.add("document-mode");
  resultsNode.classList.remove("claim-mode");

  if (data.ocr_details && !data.page_results && !data.section_overview && !data.pages_analyzed) {
    renderImageDocumentResult(data);
    return;
  }

  const verdictLabel = escapeHtml(data.document_verdict || "Unknown");
  const credibilityLabel = formatPct(data.document_credibility_score);
  const claimsLabel = num(data.claims_analyzed);
  const verdictBreakdown = `${num(data.true_claims)} / ${num(data.false_claims)} / ${num(data.neutral_claims)}`;
  const warningBlock = data.analysis_warning
    ? `<p class="meta document-warning"><strong>Note:</strong> ${escapeHtml(data.analysis_warning)}</p>`
    : "";
  const summary = `
    <div class="document-topline">
      <div class="document-title-stack">
        <p class="document-kicker">Document Overview</p>
        <h4>Overall Assessment</h4>
      </div>
      <span class="pill neutral">${verdictLabel}</span>
    </div>
    <div class="kpi">
      <div class="tile"><span>Document verdict</span><strong>${verdictLabel}</strong></div>
      <div class="tile"><span>Credibility score</span><strong>${credibilityLabel}</strong></div>
      <div class="tile"><span>Claims analyzed</span><strong>${claimsLabel}</strong></div>
      <div class="tile"><span>True / False / Neutral</span><strong>${verdictBreakdown}</strong></div>
    </div>
    <div class="document-stat-strip">
      <p><strong>Signal:</strong> ${credibilityLabel} credibility across ${claimsLabel} extracted claims.</p>
      <p><strong>Mix:</strong> ${verdictBreakdown} (true / false / neutral).</p>
    </div>
    ${warningBlock}
  `;

  const sourceUrl = data.source_url ? `<p class="meta">Source: <a href="${escapeAttr(data.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(data.source_url)}</a></p>` : "";
  const primaryClaim = Array.isArray(data.results) && data.results[0] ? data.results[0] : null;
  const pdfAnalysisSentence = buildPdfAnalysisSentence(data);
  const primaryView = primaryClaim
    ? {
      ...primaryClaim,
      claim: pdfAnalysisSentence,
    }
    : null;
  const primary = primaryClaim
    ? claimResultHtml(primaryView, null, false, {
      header: "Representative Claim Snapshot",
      extraClass: "document-primary-claim-card",
      introNote: "This card shows the first extracted claim only. Use the document overview above as the actual PDF verdict.",
    })
    : "<p>No claim result returned.</p>";
  const sourceEvidence = primaryClaim ? getDisplayEvidence(primaryClaim) : [];
  const analyzedContext = renderPdfAnalyzedContext(data);
  renderInlineSourcePreview(sourceEvidence);
  resultsNode.innerHTML = [
    cardHtml("Document Summary", `${sourceUrl}${summary}`, "document-summary-card"),
    analyzedContext,
    primary,
  ].join("");
}

function renderImageDocumentResult(data) {
  const primaryClaim = Array.isArray(data.results) && data.results[0] ? data.results[0] : null;
  const primary = primaryClaim
    ? claimResultHtml(primaryClaim, null, false, {
      header: "Image Analysis Result",
      extraClass: "document-primary-claim-card",
    })
    : "<p>No claim result returned.</p>";
  const sourceEvidence = primaryClaim ? getDisplayEvidence(primaryClaim) : [];
  const analyzedContext = renderImageAnalyzedContext(data);
  renderInlineSourcePreview(sourceEvidence);
  resultsNode.innerHTML = [
    analyzedContext,
    primary,
  ].filter(Boolean).join("");
}

function buildPdfAnalysisSentence(data) {
  const pages = Number(data.pages_analyzed || data.claims_analyzed || 0);
  const sections = Array.isArray(data.section_overview) ? data.section_overview.length : 0;
  if (pages > 0 && sections > 0) {
    return `PDF analyzed page-by-page across ${pages} pages and ${sections} sections.`;
  }
  if (pages > 0) {
    return `PDF analyzed page-by-page across ${pages} pages.`;
  }
  return "PDF analyzed section-by-section for evidence-backed verification.";
}

function renderPdfAnalyzedContext(data) {
  const sections = Array.isArray(data.section_overview) ? data.section_overview : [];
  const pages = Array.isArray(data.page_results) ? data.page_results : [];

  const sectionItems = sections.length
    ? `<ul class="summary-list">${sections.slice(0, 8).map((section) => {
      const topic = escapeHtml(section.section_topic || "Document section");
      const verdict = escapeHtml(section.section_verdict || "Mixed / Needs Review");
      const sectionPages = Array.isArray(section.pages) && section.pages.length ? section.pages.join(", ") : "N/A";
      const context = escapeHtml(String(section.section_context_summary || "").trim() || "No section context summary available.");
      return `<li><strong>${topic}</strong> (pages: ${escapeHtml(String(sectionPages))}) - ${verdict}<br>${context}</li>`;
    }).join("")}</ul>`
    : "<p>No section-level context returned.</p>";

  const pageItems = pages.length
    ? `<ul class="summary-list">${pages.slice(0, 8).map((page) => {
      const pageNumber = escapeHtml(String(page.page_number ?? "?"));
      const topic = escapeHtml(page.section_topic || "Document Overview");
      const context = escapeHtml(String(page.page_context_summary || page.text_preview || "").trim() || "No page context summary available.");
      return `<li><strong>Page ${pageNumber}</strong> - ${topic}<br>${context}</li>`;
    }).join("")}</ul>`
    : "<p>No page-level context returned.</p>";

  return cardHtml(
    "Analyzed Context",
    `
      <details class="analysis-collapse">
        <summary>Sections analyzed</summary>
        <div class="analysis-collapse-body">
          ${sectionItems}
        </div>
      </details>
      <details class="analysis-collapse">
        <summary>Page context analyzed</summary>
        <div class="analysis-collapse-body">
          ${pageItems}
        </div>
      </details>
    `,
    "document-context-card",
  );
}


function getLocalCheckabilityBlock() {
  if (mode !== "claim" || !claimTextNode) return null;
  const claim = String(claimTextNode.value || "").trim();
  if (!claim) return null;

  const lowered = claim.toLowerCase();
  const personalPatterns = [
    /^this is me$/,
    /^this is us$/,
    /^this is mine$/,
    /^my name is/,
    /^i am/,
    /^i'm/,
    /^i feel/,
    /^i love/,
    /^i hate/,
    /^this is my/,
  ];
  if (personalPatterns.some((pattern) => pattern.test(lowered))) {
    return {
      code: "not_checkable_personal_statement",
      severity: "error",
      block: true,
      message: "This looks like a personal statement, not a fact-checkable claim.",
    };
  }

  if (claim.endsWith("?")) {
    return {
      code: "question_input",
      severity: "error",
      block: true,
      message: "Questions are not directly fact-checked. Rephrase it as a claim.",
    };
  }

  return null;
}

function getPrimaryAdvisoryMessage() {
  const warnings = getLocalClaimWarnings();
  if (!warnings.length) return "";
  return String(warnings[0].message || "");
}

function getLocalClaimWarnings() {
  if (mode !== "claim" || !claimTextNode) return [];
  const block = getLocalCheckabilityBlock();
  if (block) return [block];
  const claim = String(claimTextNode.value || "").trim();
  if (!claim) return [];
  const wordCount = claim.split(/\s+/).filter(Boolean).length;
  if (wordCount < 5) {
    return [{
      code: "short_claim_block",
      severity: "error",
      block: true,
      message: "Claims under 5 words are too short to verify reliably. Add more context to continue.",
      word_count: wordCount,
    }];
  }
  if (wordCount <= 7) {
    return [{
      code: "short_claim",
      severity: "warn",
      block: false,
      message: "Short claim detected. Adding a little more context may improve search quality.",
      word_count: wordCount,
    }];
  }
  return [];
}

function renderTopAdvisory(data) {
  if (!claimAdvisoryNode) return;
  const responseWarnings = Array.isArray(data?.ux_warnings) ? data.ux_warnings : [];
  const warnings = responseWarnings.length ? responseWarnings : getLocalClaimWarnings();
  if (!warnings.length) {
    claimAdvisoryNode.hidden = true;
    claimAdvisoryNode.className = "claim-advisory";
    claimAdvisoryNode.innerHTML = "";
    return;
  }

  const severity = warnings.some((warning) => warning?.severity === "error" || warning?.block)
    ? "error"
    : "warn";
  const items = warnings
    .map((warning) => `<li>${escapeHtml(String(warning?.message || "This claim may need more context."))}</li>`)
    .join("");

  claimAdvisoryNode.className = `claim-advisory ${severity}`;
  claimAdvisoryNode.innerHTML = `
    <strong>Claim advisory</strong>
    <ul>${items}</ul>
  `;
  claimAdvisoryNode.hidden = false;
}

function renderClaimResult(data) {
  resultsNode.classList.add("claim-mode");
  resultsNode.classList.remove("document-mode");
  const filteredEvidence = getDisplayEvidence(data);
  renderInlineSourcePreview(filteredEvidence);
  resultsNode.innerHTML = [
    claimResultHtml(data, null, false),
  ].join("");
}

function renderImageAnalyzedContext(data) {
  const ocr = data && data.ocr_details && typeof data.ocr_details === "object" ? data.ocr_details : null;
  if (!ocr) return "";

  const claimLanguage = normalizeLanguageLabel(
    extractLanguage(data)
      || ocr.language
      || guessLanguageFromPreview(ocr.selected_claim || data.claim || ocr.text_preview || "")
      || "unknown"
  );
  const candidates = Array.isArray(ocr.selected_claim_candidates) ? ocr.selected_claim_candidates : [];
  currentImageClaimSelectionState = {
    original: {
      claim_language: claimLanguage,
      selected_claim: String(ocr.selected_claim || data.claim || "").trim() || "No selected claim returned.",
      candidates: candidates.slice(0, 3).map((row) => ({
        text: String(row.text || row.claim || "").trim() || "Candidate",
        score: row.score,
      })),
    },
    translated: null,
  };
  const imagePreview = currentImagePreviewUrl
    ? `
      <figure class="image-context-preview">
        <img src="${escapeAttr(currentImagePreviewUrl)}" alt="Uploaded image preview">
        <figcaption>Source image preview</figcaption>
      </figure>
    `
    : `<p class="meta"><strong>Image preview:</strong> No image preview available.</p>`;
  return cardHtml(
    "Analyzed Context",
    `
      <details class="analysis-collapse" open>
        <summary>OCR context analyzed</summary>
        <div class="analysis-collapse-body">
          <ul class="summary-list">
            <li><strong>OCR language detected:</strong> ${escapeHtml(claimLanguage)}</li>
          </ul>
          ${imagePreview}
        </div>
      </details>
      <details class="analysis-collapse">
        <summary>Claim selection analyzed</summary>
        <div class="analysis-collapse-body">
          <div class="analysis-action-row">
            <button type="button" class="analysis-mini-btn" data-image-claim-translate data-state="original">Translate</button>
          </div>
          <div data-image-claim-selection-body>
            ${renderImageClaimSelectionBody(currentImageClaimSelectionState.original)}
          </div>
        </div>
      </details>
    `,
    "document-context-card image-context-card",
  );
}


function renderUxWarnings(data) {
  const warnings = Array.isArray(data?.ux_warnings) ? data.ux_warnings : [];
  if (!warnings.length) return "";

  const items = warnings
    .map((warning) => {
      const message = warning?.message ? String(warning.message) : "This claim may need more context.";
      return `<li>${escapeHtml(message)}</li>`;
    })
    .join("");

  return `
    <div class="ux-warning-card" role="note" aria-label="Claim advisory">
      <strong>Claim advisory</strong>
      <ul>${items}</ul>
    </div>
  `;
}

function claimResultHtml(data, index = null, includeSourcePreview = false, options = {}) {
  const filteredEvidence = getDisplayEvidence(data);
  const transparency = (data && data.transparency) || {};
  const verdict = (data.final_verdict || "NEUTRAL").toUpperCase();
  const verdictClass = verdict === "SUPPORT" ? "support" : verdict === "REFUTE" ? "refute" : "neutral";
  const header = options.header || (index ? `Claim ${index}` : "Claim Result");
  const extraClass = options.extraClass || "";
  const introNote = options.introNote ? `<p class="meta subtle-note">${escapeHtml(options.introNote)}</p>` : "";
  const cleanExplanationText = sanitizeNarrative(data.explanation || "");
  const cleanConflictText = sanitizeNarrative(data.conflict_analysis || "N/A");
  const explanationDetails = buildExplanationDetails(data, filteredEvidence, cleanExplanationText);
  const claimTextLine = data.claim ? escapeHtml(data.claim) : "N/A";
  const summaryDetails = buildSummaryDetails(data, filteredEvidence, cleanConflictText);
  const transparencyBlock = renderTransparency(transparency);
  const warningBlock = renderUxWarnings(data);
  const citations = (data.citations || [])
    .filter((c) => !String(c).includes("internal://logic_engine") && !String(c).includes("logic_engine"))
    .map((c) => `<li>${escapeHtml(cleanCitationText(c))}</li>`)
    .join("");

  const evidenceItems = filteredEvidence
    .map((ev) => {
      const sourceLabel = sourceLabelForEvidence(ev);
      const stanceClass = (ev.stance || "NEUTRAL").toUpperCase() === "SUPPORT"
        ? "support"
        : (ev.stance || "NEUTRAL").toUpperCase() === "REFUTE"
          ? "refute"
          : "neutral";
      return `
        <article class="evidence-item">
          <div>
            <span class="pill ${stanceClass}">${escapeHtml(ev.stance || "NEUTRAL")}</span>
          </div>
          <p>${escapeHtml(getDisplaySnippetText(ev))}</p>
          <p class="meta">
            Source: ${escapeHtml(sourceLabel)} |
            Confidence: ${formatPct(ev.confidence)} |
            Weight: ${num(ev.weight)}
          </p>
          ${ev.stance === "UNSCORED" ? `<p class="meta">Retrieved and cleaned, but not strong enough to use for final scoring.</p>` : ""}\n          ${ev.url ? `<a href="${escapeAttr(ev.url)}" target="_blank" rel="noopener noreferrer">Open source</a>` : ""}
        </article>
      `;
    })
    .join("");

  const languageLabel = normalizeLanguageLabel(
    reportLanguageOverride || data.language || "unknown"
  );

  return cardHtml(
    header,
    `
      <div class="quick-lines">
        ${introNote}
        <p><strong>Claim:</strong> ${claimTextLine}</p>
        <p><strong>Verdict:</strong> ${escapeHtml(verdict)}</p>
        <p><strong>Confidence:</strong> ${formatPct(data.confidence)}</p>
        <p><strong>Summary:</strong></p>
        ${summaryDetails}
      </div>
      ${warningBlock}
      <div class="kpi">
        <div class="tile"><span>Verdict</span><strong><span class="pill ${verdictClass}">${escapeHtml(verdict)}</span></strong></div>
        <div class="tile"><span>Confidence</span><strong>${formatPct(data.confidence)}</strong></div>
        <div class="tile"><span>Language</span><strong>${escapeHtml(languageLabel)}</strong></div>
      </div>
      <h4>Explanation</h4>
      ${explanationDetails}
      <h4>Decision Transparency</h4>
      ${transparencyBlock}
      ${includeSourcePreview ? `<h4>Strong Source Preview</h4>${renderSourceMedia(filteredEvidence)}` : ""}
      <h4>Evidence</h4>
      <div class="evidence-list">${evidenceItems || "<p>No evidence returned.</p>"}</div>
      <h4>Conflict Analysis</h4>
      <p>${escapeHtml(cleanConflictText)}</p>
      <h4>Citations</h4>
      ${citations ? `<ol>${citations}</ol>` : "<p>No citations returned.</p>"}
    `,
    extraClass,
  );
}

function renderTransparency(meta) {
  if (!meta || typeof meta !== "object" || !Object.keys(meta).length) {
    return "<p>No transparency metadata returned.</p>";
  }

  const claimType = meta.claim_type || {};
  const stats = meta.evidence_stats || {};
  const flags = meta.policy_flags || {};

  const lines = [];
  if (meta.language_detected) lines.push(`<p><strong>Detected language:</strong> ${escapeHtml(normalizeLanguageLabel(meta.language_detected))}</p>`);
  if (claimType.label) {
    const source = claimType.decision_source ? ` (${escapeHtml(claimType.decision_source)})` : "";
    lines.push(`<p><strong>Claim type:</strong> ${escapeHtml(claimType.label)}${source}</p>`);
  }
  if (typeof claimType.confidence === "number") {
    lines.push(`<p><strong>Claim-type confidence:</strong> ${formatPct(claimType.confidence)}</p>`);
  }

  const statLine = [
    `retrieved ${num(stats.retrieved)}`,
    `cleaned ${num(stats.cleaned)}`,
    `scored ${num(stats.scored)}`,
    `strong ${num(stats.strong)}`,
    `soft ${num(stats.soft)}`,
  ].join(" | ");
  if (stats.retrieved !== undefined) {
    lines.push(`<p><strong>Evidence flow:</strong> ${escapeHtml(statLine)}</p>`);
  }

  const stanceSourcePairs = Object.entries(meta.stance_sources || {});
  if (stanceSourcePairs.length) {
    const src = stanceSourcePairs.map(([k, v]) => `${k}: ${v}`).join(", ");
    lines.push(`<p><strong>Stance source usage:</strong> ${escapeHtml(src)}</p>`);
  }

  if (flags.forced_neutral_due_to_weak_evidence !== undefined) {
    lines.push(
      `<p><strong>Policy flag:</strong> forced neutral due to weak evidence = ${escapeHtml(String(flags.forced_neutral_due_to_weak_evidence))}</p>`
    );
  }

  return lines.join("") || "<p>No transparency metadata returned.</p>";
}

function sourcePreviewCard(filteredEvidence) {
  return cardHtml("Strong Source Preview", renderSourceMedia(filteredEvidence));
}

function renderInlineSourcePreview(filteredEvidence) {
  const html = renderSourceMedia(filteredEvidence);
  inlineSourcePreviewBody.innerHTML = html;
  inlineSourcePreview.hidden = false;
}

function filterEvidence(evidence) {
  return (evidence || []).filter((ev) => {
    if (!ev) return false;
    const source = String(ev.source || "");
    const url = String(ev.url || "");
    if (source === "logic_engine") return false;
    if (url.startsWith("internal://")) return false;
    return true;
  });
}

function getDisplayEvidence(data) {
  const primary = filterEvidence((data && data.evidence) || []);
  if (primary.length) return primary;
  return filterEvidence((((data || {}).transparency || {}).fallback_evidence_preview) || []);
}

function renderSourceMedia(evidence) {
  const ranked = (evidence || [])
    .filter((ev) => ev && ev.url && !String(ev.url).startsWith("internal://"))
    .sort((a, b) => (Number(b.weight || 0) * Number(b.confidence || 0)) - (Number(a.weight || 0) * Number(a.confidence || 0)));

  let chosen = ranked.filter((ev) => Number(ev.weight) >= 0.6).slice(0, 6);
  if (!chosen.length) {
    chosen = ranked.slice(0, 6);
  }

  if (!chosen.length) return "<p class=\"meta\">No source preview available for this claim.</p>";

  const items = chosen.map((ev) => {
    const domain = extractDomain(ev.url || "");
    if (!domain) return "";
    const logo = `https://logo.clearbit.com/${domain}`;
    const sourceLabel = sourceLabelForEvidence(ev);
    return `
      <a class="source-media-item" href="${escapeAttr(ev.url)}" target="_blank" rel="noopener noreferrer">
        <img src="${escapeAttr(logo)}" alt="${escapeHtml(domain)} logo" loading="lazy" onerror="this.src='https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64'">
        <div>
          <div>${escapeHtml(sourceLabel || domain)}</div>
          <p class="meta">${escapeHtml(domain)}</p>
        </div>
      </a>
    `;
  }).join("");

  return `<div class="source-media">${items}</div>`;
}

function extractDomain(url) {
  try {
    const u = new URL(url);
    return u.hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function extractLanguage(data) {
  if (data.language) return data.language;
  if (Array.isArray(data.results) && data.results[0] && data.results[0].language) return data.results[0].language;
  return null;
}

function renderImageClaimSelectionBody(payload, options = {}) {
  const selectedClaim = escapeHtml(String(payload?.selected_claim || "").trim() || "No selected claim returned.");
  const claimLanguage = escapeHtml(String(payload?.claim_language || "Unknown"));
  const label = options.label ? `<p class="meta"><strong>${escapeHtml(options.label)}:</strong></p>` : "";
  const candidates = Array.isArray(payload?.candidates) ? payload.candidates : [];
  const candidateItems = candidates.length
    ? `<ul class="summary-list">${candidates.map((row) => {
      const text = escapeHtml(String(row.text || row.claim || "").trim() || "Candidate");
      const score = row.score != null ? ` (${num(row.score)})` : "";
      return `<li><strong>${text}</strong>${escapeHtml(score)}</li>`;
    }).join("")}</ul>`
    : "<p>No alternate claim candidates returned.</p>";
  return `
    ${label}
    <p class="meta"><strong>Claim language:</strong> ${claimLanguage}</p>
    <p class="meta"><strong>Selected claim:</strong> ${selectedClaim}</p>
    ${candidateItems}
  `;
}

function normalizeClaimComparison(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeLanguageLabel(code) {
  const v = String(code || "unknown").trim().toLowerCase();
  const map = {
    en: "English",
    eng: "English",
    hi: "Hindi",
    hin: "Hindi",
    ta: "Tamil",
    tam: "Tamil",
    te: "Telugu",
    tel: "Telugu",
    bn: "Bengali",
    ben: "Bengali",
    mr: "Marathi",
    mar: "Marathi",
    gu: "Gujarati",
    guj: "Gujarati",
    kn: "Kannada",
    kan: "Kannada",
    ml: "Malayalam",
    mal: "Malayalam",
    pa: "Punjabi",
    pan: "Punjabi",
    ur: "Urdu",
    urd: "Urdu",
    ori: "Odia",
    or: "Odia",
    osd: "Orientation Script Detection",
    unknown: "Unknown",
  };
  if (map[v]) return map[v];
  if (/^[a-z]{2}(-[a-z]{2})?$/.test(v)) return v.toUpperCase();
  return "Unknown";
}

function sanitizeNarrative(text) {
  if (!text) return "";
  return maybeFixMojibake(String(text))
    .replace(/logic_engine/gi, "reasoning engine")
    .replace(/\binternal:\/\/logic_engine\b/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function cleanCitationText(value) {
  return maybeFixMojibake(String(value || ""))
    .replace(/^\s*\[\d+\]\s*/u, "")
    .trim();
}

function maybeFixMojibake(text) {
  const raw = String(text || "");
  if (!looksLikeMojibake(raw)) return raw;
  try {
    const bytes = Uint8Array.from(Array.from(raw, (ch) => ch.charCodeAt(0) & 0xff));
    const decoded = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
    if (isBetterDecodedText(raw, decoded)) return decoded;
  } catch (_) {
    return raw;
  }
  return raw;
}

function looksLikeMojibake(text) {
  return /(?:Ã.|Â.|â.|à.|Ð.|Ñ.)/.test(text);
}

function isBetterDecodedText(original, decoded) {
  if (!decoded || decoded.includes("\uFFFD")) return false;
  const mojibakePenalty = countRegex(original, /(?:Ã.|Â.|â.|à.|Ð.|Ñ.)/g) - countRegex(decoded, /(?:Ã.|Â.|â.|à.|Ð.|Ñ.)/g);
  const scriptGain = countRegex(decoded, /[\u0900-\u0D7F]/g) - countRegex(original, /[\u0900-\u0D7F]/g);
  const latinDrop = countRegex(original, /[A-Za-z]{2,}/g) - countRegex(decoded, /[A-Za-z]{2,}/g);
  return mojibakePenalty > 0 && (scriptGain > 0 || latinDrop <= 0);
}

function countRegex(text, regex) {
  const matches = String(text || "").match(regex);
  return matches ? matches.length : 0;
}

function formatSourceList(items) {
  const names = (items || []).filter(Boolean);
  if (!names.length) return "";
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
}

function buildSummaryDetails(data, filteredEvidence, fallbackText) {
  const evidenceGroups = getEvidenceGroups(filteredEvidence);
  const verdict = String(data.final_verdict || "NEUTRAL").toUpperCase();
  const sourceNames = extractTopSources(data);
  const claimText = String(data.claim || "");
  const leadSupport = pickBestEvidenceContext(evidenceGroups.support, claimText);
  const leadRefute = pickBestEvidenceContext(evidenceGroups.refute, claimText);
  const leadNeutral = pickBestEvidenceContext(evidenceGroups.neutral, claimText);

  const lines = [];
  lines.push(`Evidence reviewed: ${evidenceGroups.support.length} supporting, ${evidenceGroups.refute.length} contradicting, and ${evidenceGroups.neutral.length} neutral items.`);

  if (sourceNames.length) {
    lines.push(`Main sources: ${formatSourceList(sourceNames.slice(0, 3))}.`);
  }

  if (verdict === "TRUE" && leadSupport) {
    lines.push(`Why it was marked TRUE: the strongest supporting evidence directly matches the claim.`);
  } else if (verdict === "FALSE" && leadRefute) {
    lines.push(`Why it was marked FALSE: the strongest contradictory evidence directly conflicts with the claim.`);
  } else if (verdict === "NEUTRAL") {
    lines.push("Why it was marked NEUTRAL: the evidence was mixed, weak, or not decisive enough.");
  }

  if (leadSupport) {
    lines.push(`Supporting context available: yes.`);
  }
  if (leadRefute) {
    lines.push(`Contradicting context available: yes.`);
  }
  if (leadNeutral) {
    lines.push(`Neutral background context available: yes.`);
  }

  if (!lines.length && fallbackText) {
    lines.push(fallbackText);
  }

  if (!lines.length) {
    lines.push("No summary data available.");
  }

  return `<ul class="summary-list">${lines.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
}

function buildExplanationDetails(data, filteredEvidence, fallbackText) {
  const evidenceGroups = getEvidenceGroups(filteredEvidence);
  const verdict = String(data.final_verdict || "NEUTRAL").toUpperCase();
  const confidence = formatPct(data.confidence);
  const sourceNames = extractTopSources(data);
  const intro = [];

  if (verdict === "TRUE") {
    intro.push("Most evidence aligns with the claim.");
  } else if (verdict === "FALSE") {
    intro.push("Most evidence contradicts the claim.");
  } else {
    intro.push("The available evidence does not lead to a decisive conclusion.");
  }

  intro.push(`Evidence mix: ${evidenceGroups.support.length} supporting, ${evidenceGroups.refute.length} contradicting, and ${evidenceGroups.neutral.length} neutral.`);
  intro.push(`Confidence: ${confidence}.`);

  if (sourceNames.length) {
    intro.push(`Main sources reviewed: ${formatSourceList(sourceNames.slice(0, 4))}.`);
  }

  const claimText = String(data.claim || "");
  const supportHtml = renderExplanationSection("Supporting", evidenceGroups.support, claimText);
  const refuteHtml = renderExplanationSection("Contradicting", evidenceGroups.refute, claimText);
  const neutralHtml = renderExplanationSection("Neutral", evidenceGroups.neutral, claimText);
  const notes = [];

  if (!filteredEvidence.length && fallbackText) {
    notes.push(`<p>${escapeHtml(fallbackText)}</p>`);
  }

  const introList = `<ul class="explanation-intro-list">${intro.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;

  return `
    <div class="explanation-block">
      ${introList}
      ${supportHtml}
      ${refuteHtml}
      ${neutralHtml}
      ${notes.join("")}
    </div>
  `;
}

function renderExplanationSection(title, items, claimText = "") {
  const picked = pickTopEvidenceItems(items, claimText, 1);
  const body = picked.length
    ? `<ul class="explanation-list">${picked.map((item) => renderExplanationItem(item)).join("")}</ul>`
    : `<p class="explanation-none">None.</p>`;
  return `
    <section class="explanation-section">
      <p><strong>${escapeHtml(title)}:</strong></p>
      ${body}
    </section>
  `;
}

function renderExplanationItem(item) {
  const context = getDisplaySnippetText({
    text: pickEvidenceContext(item, 520) || item?.text || "",
  }) || "No detailed evidence text available.";
  const source = sourceLabelForEvidence(item);
  return `<li><p class="explanation-context">${escapeHtml(context)}</p><p class="meta explanation-source">Source: ${escapeHtml(source)}</p></li>`;
}

function getEvidenceGroups(filteredEvidence) {
  return {
    support: filteredEvidence.filter((ev) => String(ev.stance || "").toUpperCase() === "SUPPORT"),
    refute: filteredEvidence.filter((ev) => String(ev.stance || "").toUpperCase() === "REFUTE"),
    neutral: filteredEvidence.filter((ev) => String(ev.stance || "").toUpperCase() === "NEUTRAL"),
  };
}

function pickTopEvidenceItems(items, claimText = "", limit = 1) {
  if (!items || !items.length) return [];
  return [...items]
    .sort((a, b) => scoreEvidenceItem(b, claimText) - scoreEvidenceItem(a, claimText))
    .slice(0, limit);
}

function scoreEvidenceItem(item, claimText = "") {
  const relevance = Number(item?.relevance_score ?? 0);
  const quality = Number(item?.quality_score ?? 0);
  const confidence = Number(item?.confidence ?? 0);
  const weight = Number(item?.weight ?? 0);
  const overlap = computeClaimOverlap(item, claimText);
  const numberBonus = computeNumberAlignmentBonus(item, claimText);
  return (relevance * 3) + (quality * 2) + confidence + weight + overlap + numberBonus;
}

function computeClaimOverlap(item, claimText = "") {
  const claimTokens = tokenizeForMatch(claimText);
  if (!claimTokens.length) return 0;
  const evidenceTokens = new Set(tokenizeForMatch(pickEvidenceContext(item, 900) || item?.text || ""));
  let matches = 0;
  for (const token of claimTokens) {
    if (evidenceTokens.has(token)) matches += 1;
  }
  return matches / claimTokens.length;
}

function computeNumberAlignmentBonus(item, claimText = "") {
  const claimNumbers = extractNumericTokens(claimText);
  if (!claimNumbers.length) return 0;
  const evidenceText = `${pickEvidenceContext(item, 900) || ""} ${String(item?.text || "")}`;
  const evidenceNumbers = new Set(extractNumericTokens(evidenceText));
  let matched = 0;
  for (const num of claimNumbers) {
    if (evidenceNumbers.has(num)) matched += 1;
  }
  return matched ? matched * 2.5 : -1.5;
}

function tokenizeForMatch(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 2);
}

function extractNumericTokens(text) {
  return (String(text || "").match(/\b\d+[\d,]*\b/g) || []).map((value) => value.replace(/,/g, ""));
}

function pickBestEvidenceContext(items, claimText = "", maxLen = 280) {
  const picked = pickTopEvidenceItems(items, claimText, 1);
  return picked.length ? pickEvidenceContext(picked[0], maxLen) : null;
}

function pickEvidenceContext(item, maxLen = 280) {
  if (!item) return null;
  const passages = Array.isArray(item.retained_passages)
    ? item.retained_passages.filter(Boolean).map((part) => String(part).trim())
    : [];
  const candidates = [
    item.context_text,
    passages.length ? passages.slice(0, 2).join(" ") : "",
    item.text,
  ]
    .filter(Boolean)
    .map((value) => sanitizeNarrative(String(value)).replace(/\s+/g, " ").trim())
    .filter(Boolean);

  if (!candidates.length) return null;

  const best = candidates.sort((a, b) => b.length - a.length)[0];
  return truncateAtSentence(best, maxLen);
}

function truncateAtSentence(text, maxLen) {
  if (!text) return "";
  if (!maxLen || text.length <= maxLen) return text;
  const trimmed = text.slice(0, maxLen);
  const boundary = Math.max(trimmed.lastIndexOf(". "), trimmed.lastIndexOf("? "), trimmed.lastIndexOf("! "));
  if (boundary >= 80) {
    return `${trimmed.slice(0, boundary + 1).trim()}`;
  }
  return `${trimmed.trim()}...`;
}

function extractVerdict(data) {
  if (data.final_verdict) return data.final_verdict;
  if (data.document_verdict) return data.document_verdict;
  if (Array.isArray(data.results) && data.results[0] && data.results[0].final_verdict) return data.results[0].final_verdict;
  return "UNKNOWN";
}

function extractTopSources(data) {
  const names = [];
  const pushSource = (ev) => {
    if (!ev) return;
    const val = normalizeSourceName(ev.source || "", "");
    if (!val) return;
    if (!names.includes(val)) names.push(val);
  };

  if (Array.isArray(data.evidence)) data.evidence.forEach(pushSource);
  if (Array.isArray(data.results)) {
    data.results.forEach((r) => {
      if (Array.isArray(r.evidence)) r.evidence.forEach(pushSource);
    });
  }
  return names.slice(0, 3);
}

function normalizeSourceName(value, fallback = "Unknown source") {
  const raw = maybeFixMojibake(String(value || "")).trim();
  if (!raw) return fallback;
  const compact = raw.toLowerCase().replace(/[_\-]+/g, " ").replace(/\s+/g, " ").trim();
  if (compact === "logic engine" || compact === "logic_engine") return fallback;
  if (/^ocr( context| text| extraction)?$/.test(compact)) return fallback;
  if (compact.includes("ocr context")) return fallback;
  if (compact.includes("internal://")) return fallback;
  return raw;
}

function sourceLabelForEvidence(ev) {
  const cleaned = normalizeSourceName(ev && ev.source, "");
  if (cleaned) return cleaned;
  const domain = extractDomain((ev && ev.url) || "");
  return domain || "Unknown source";
}

function cleanEvidenceContext(text) {
  if (!text) return "";
  let out = sanitizeNarrative(String(text));
  out = out.replace(/[\r\n]+/g, " ");
  out = out.replace(/^\s*[-*•–—]+\s*/u, "");
  out = out.replace(/\s+[\-–—]\s+/gu, "; ");
  out = out.replace(/\s{2,}/g, " ").trim();
  return out;
}

function getDisplaySnippetText(item) {
  const raw = cleanEvidenceContext(String(item?.text || ""));
  if (!raw) return "Source snippet unavailable.";

  let out = raw;
  const suspicious = looksLikeMojibake(out) || /\bIN US English\b/i.test(out);

  if (suspicious) {
    out = out.replace(/^\s*IN US English\s*/i, "").trim();

    const headlineMatch = out.match(/(['"“][^'"”]{20,}['"”])/u);
    if (headlineMatch && typeof headlineMatch.index === "number" && headlineMatch.index > 12) {
      out = out.slice(headlineMatch.index).trim();
    }

    out = out.replace(/^(?:News\s+|City\s+|amaravati\s+){2,}/i, "").trim();

    if (looksLikeMojibake(out) && countRegex(out, /(?:Ã.|Â.|â.|à.|Ð.|Ñ.)/g) >= 3 && !/[\u0900-\u0D7F]/.test(out)) {
      return "Source snippet omitted because it contained unreadable encoded text.";
    }
  }

  return truncateAtSentence(out, 420);
}

function guessTopSources(preview) {
  const text = (preview || "").toLowerCase();
  if (text.includes("earth") || text.includes("space") || text.includes("planet")) return ["NASA", "Britannica", "Wikipedia"];
  if (text.includes("india") || text.includes("rbi") || text.includes("gdp")) return ["RBI", "MOSPI", "World Bank"];
  if (text.includes("health") || text.includes("covid") || text.includes("vaccine")) return ["WHO", "CDC", "UN Data"];
  return ["Trusted News", "World Bank", "WHO"];
}

function guessLanguageFromPreview(preview) {
  const text = preview || "";
  if (/[\u0B80-\u0BFF]/.test(text)) return "ta";
  if (/[\u0900-\u097F]/.test(text)) return "hi";
  if (/[\u0980-\u09FF]/.test(text)) return "bn";
  return "en";
}

function cardHtml(title, body, extraClass = "") {
  const className = ["card", extraClass].filter(Boolean).join(" ");
  return `<section class="${className}"><h3>${escapeHtml(title)}</h3>${body}</section>`;
}

function formatPct(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";
  if (value <= 1) return `${(value * 100).toFixed(1)}%`;
  return `${value.toFixed(1)}%`;
}

function num(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";
  return value.toFixed(2);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function truncate(text, maxLen) {
  if (!text || text.length <= maxLen) return text;
  return `${text.slice(0, maxLen)}...`;
}

function formatKb(bytes) {
  if (typeof bytes !== "number") return "unknown size";
  return `${(bytes / 1024).toFixed(1)} KB`;
}

