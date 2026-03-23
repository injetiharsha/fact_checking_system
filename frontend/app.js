const tabs = document.querySelectorAll(".tab");
const blocks = document.querySelectorAll(".mode-block");
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

let mode = "claim";
let currentController = null;
let progressTimer = null;
let detailPulseTimer = null;
let elapsedTimer = null;
let progressIndex = 0;
let progressStartedAt = null;
let activeSteps = [];
let stepDetails = [];
let stepFlowQueues = [];
let stepFlowPos = [];
let basePreview = "";
let originalReport = null;
let renderedReport = null;
let reportLanguageOverride = null;

function setActiveInputLocked(locked) {
  if (mode === "claim") {
    const node = document.getElementById("claim-text");
    if (node) node.readOnly = locked;
    return;
  }
  if (mode === "url") {
    const node = document.getElementById("url-text");
    if (node) node.readOnly = locked;
    return;
  }
  if (mode === "pdf") {
    const node = document.getElementById("pdf-file");
    if (node) node.disabled = locked;
    return;
  }
  const node = document.getElementById("image-file");
  if (node) node.disabled = locked;
}

function getProgressPreviewLabel() {
  if (mode === "claim") return "Claim analysis in progress";
  if (mode === "url") return "URL analysis in progress";
  if (mode === "pdf") return "PDF analysis in progress";
  return "Image analysis in progress";
}

const stepTitles = {
  claim: [
    "Validating claim text",
    "Detecting language and normalizing",
    "Retrieving evidence sources",
    "Scoring relevance and quality",
    "Stance analysis and verdict aggregation",
  ],
  url: [
    "Fetching article content",
    "Extracting main claim",
    "Retrieving evidence sources",
    "Scoring relevance and quality",
    "Stance analysis and verdict aggregation",
  ],
  pdf: [
    "Extracting text from PDF",
    "Selecting main content claim",
    "Retrieving evidence sources",
    "Scoring relevance and quality",
    "Stance analysis and verdict aggregation",
  ],
  image: [
    "Running OCR on image",
    "Selecting main content claim",
    "Retrieving evidence sources",
    "Scoring relevance and quality",
    "Stance analysis and verdict aggregation",
  ],
};

for (const tab of tabs) {
  tab.addEventListener("click", () => {
    mode = tab.dataset.mode;
    tabs.forEach((t) => t.classList.toggle("active", t === tab));
    blocks.forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
    resultsNode.innerHTML = "";
    statusNode.textContent = "";
    renderTopAdvisory(null);
    hideReportTools();
    resetProgressPanel();
  });
}

cancelBtn.addEventListener("click", () => {
  if (currentController) {
    currentController.abort();
    statusNode.textContent = "Cancelled.";
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
  const localWarnings = getLocalClaimWarnings();
  const blockingWarning = localWarnings.find((warning) => warning?.block);
  statusNode.textContent = "Analyzing...";
  resultsNode.innerHTML = "";
  renderTopAdvisory({ ux_warnings: localWarnings });
  hideReportTools();

  if (blockingWarning) {
    statusNode.textContent = "Add a little more context before analysis.";
    resetProgressPanel();
    runBtn.disabled = false;
    cancelBtn.hidden = true;
    setActiveInputLocked(false);
    return;
  }

  startProgressForCurrentInput();
  currentController = new AbortController();

  try {
    const data = await callApiForMode(currentController.signal);
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
      stepsNode.insertAdjacentHTML("beforeend", '<li><div class="step-title">Process cancelled by user</div></li>');
    } else {
      statusNode.textContent = "Failed.";
      stepsNode.insertAdjacentHTML("beforeend", `<li><div class="step-title">Error</div><div class="step-detail">${escapeHtml(error.message)}</div></li>`);
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
  if (mode === "url") {
    const url = document.getElementById("url-text").value.trim();
    return url ? `URL: ${truncate(url, 240)}` : "URL: No URL entered";
  }
  if (mode === "pdf") {
    const file = document.getElementById("pdf-file").files[0];
    return file ? `PDF: ${file.name} (${formatKb(file.size)})` : "PDF: No file selected";
  }
  const file = document.getElementById("image-file").files[0];
  return file ? `Image: ${file.name} (${formatKb(file.size)})` : "Image: No file selected";
}

function initialFlowQueues(preview) {
  const langGuess = guessLanguageFromPreview(preview);
  const sourceGuess = guessTopSources(preview).join(", ");

  return [
    [
      "Input accepted",
      "Parsing sentence boundaries",
      "Preparing claim payload",
    ],
    [
      `Detected language (estimated): ${langGuess}`,
      "Normalizing claim tokens",
      "Applying translation if needed",
    ],
    [
      `Top sources (estimated): ${sourceGuess}`,
      "Querying trusted evidence providers",
      "Collecting high-credibility candidates",
    ],
    [
      "Computing relevance score",
      "Computing evidence quality score",
      "Selecting strongest support/refute snippets",
    ],
    [
      "Running stance detection",
      "Aggregating weighted verdict",
      "Preparing explanation and citations",
    ],
  ];
}

function startProgressForCurrentInput() {
  processPanel.hidden = false;
  progressStartedAt = Date.now();
  activeSteps = [...(stepTitles[mode] || stepTitles.claim)];
  basePreview = getProgressPreviewLabel();
  const advisoryMessage = getPrimaryAdvisoryMessage();
  previewNode.textContent = advisoryMessage ? `${basePreview} | Advisory: ${advisoryMessage}` : basePreview;

  stepFlowQueues = initialFlowQueues(getCurrentInputPreview());
  stepFlowPos = stepFlowQueues.map(() => 0);
  stepDetails = stepFlowQueues.map((q) => q[0]);

  progressIndex = 0;
  renderSteps();
  setStepState(progressIndex, "active");

  stopProgressTimers();
  updateElapsedTimer();
  elapsedTimer = setInterval(updateElapsedTimer, 1000);
  progressTimer = setInterval(() => {
    if (progressIndex >= activeSteps.length - 1) {
      return;
    }
    setStepState(progressIndex, "done");
    progressIndex += 1;
    setStepState(progressIndex, "active");
    previewNode.textContent = `${basePreview} | Stage: ${activeSteps[progressIndex]}`;
    renderSteps();
  }, 2300);

  detailPulseTimer = setInterval(() => {
    const idx = progressIndex;
    const queue = stepFlowQueues[idx] || [];
    if (queue.length < 2) return;
    stepFlowPos[idx] = (stepFlowPos[idx] + 1) % queue.length;
    stepDetails[idx] = queue[stepFlowPos[idx]];
    renderSteps();
    setStepState(idx, "active");
  }, 900);
}

function enrichProgressWithResponse(data) {
  const lang = normalizeLanguageLabel(extractLanguage(data));
  const sources = extractTopSources(data);
  const verdict = extractVerdict(data);

  if (activeSteps[1]) stepDetails[1] = `Detected language: ${lang}`;
  if (activeSteps[2]) stepDetails[2] = `Top sources: ${sources.length ? sources.join(", ") : "No strong sources returned"}`;
  if (activeSteps[4]) stepDetails[4] = `Final verdict: ${verdict}`;

  previewNode.textContent = `${basePreview} | Final verdict: ${verdict}`;
  renderSteps();
}

function renderSteps() {
  if (!activeSteps.length) {
    stepsNode.innerHTML = "";
    return;
  }
  const idx = Math.min(progressIndex, activeSteps.length - 1);
  const title = activeSteps[idx];
  const detail = stepDetails[idx] ? `<div class="step-detail">${escapeHtml(stepDetails[idx])}</div>` : "";
  stepsNode.innerHTML = `<li class="active current-step" data-step-idx="${idx}"><div class="step-title">${escapeHtml(title)}</div>${detail}</li>`;
}

function completeProgress() {
  stopProgressTimers();
  const elapsedLabel = formatElapsedDuration();
  stepsNode.innerHTML = `<li class="done"><div class="step-title">Completed</div><div class="step-detail">Report generated successfully. Total time: ${escapeHtml(elapsedLabel)}.</div></li>`;
  progressTimerNode.textContent = `Time: ${elapsedLabel}`;
}

function resetProgressPanel() {
  stopProgressTimers();
  processPanel.hidden = true;
  renderTopAdvisory(null);
  previewNode.textContent = "Submit a claim, URL, PDF, or image to start.";
  progressTimerNode.textContent = "Time: 00:00";
  stepsNode.innerHTML = "";
  activeSteps = [];
  stepDetails = [];
  stepFlowQueues = [];
  stepFlowPos = [];
  basePreview = "";
}

function stopProgressTimers() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  if (detailPulseTimer) {
    clearInterval(detailPulseTimer);
    detailPulseTimer = null;
  }
  if (elapsedTimer) {
    clearInterval(elapsedTimer);
    elapsedTimer = null;
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

function setStepState(index, state) {
  const item = stepsNode.querySelector(`li[data-step-idx="${index}"]`);
  if (!item) return;
  item.classList.remove("active", "done");
  if (state) item.classList.add(state);
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

async function callApiForMode(signal) {
  if (mode === "claim") {
    const claim = document.getElementById("claim-text").value.trim();
    if (!claim) throw new Error("Please enter a claim.");
    return postJson("/check", { claim }, signal);
  }
  if (mode === "url") {
    const url = document.getElementById("url-text").value.trim();
    if (!url) throw new Error("Please enter a URL.");
    return postJson("/analyze_url", { url }, signal);
  }
  if (mode === "pdf") {
    const file = document.getElementById("pdf-file").files[0];
    if (!file) throw new Error("Please choose a PDF.");
    return postFile("/analyze_pdf", file, signal);
  }
  const file = document.getElementById("image-file").files[0];
  if (!file) throw new Error("Please choose an image.");
  return postFile("/analyze_image", file, signal);
}

async function postJson(url, body, signal = null) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  return handleResponse(response);
}

async function postFile(url, file, signal = null) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(url, {
    method: "POST",
    body: formData,
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
  const summary = `
    <div class="kpi">
      <div class="tile"><span>Document verdict</span><strong>${escapeHtml(data.document_verdict || "Unknown")}</strong></div>
      <div class="tile"><span>Credibility score</span><strong>${formatPct(data.document_credibility_score)}</strong></div>
      <div class="tile"><span>Claims analyzed</span><strong>${num(data.claims_analyzed)}</strong></div>
      <div class="tile"><span>True / False / Neutral</span><strong>${num(data.true_claims)} / ${num(data.false_claims)} / ${num(data.neutral_claims)}</strong></div>
    </div>
  `;

  const sourceUrl = data.source_url ? `<p class="meta">Source: <a href="${escapeAttr(data.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(data.source_url)}</a></p>` : "";
  const primaryClaim = Array.isArray(data.results) && data.results[0] ? data.results[0] : null;
  const primary = primaryClaim ? claimResultHtml(primaryClaim, null, false) : "<p>No claim result returned.</p>";
  const sourceEvidence = primaryClaim ? getDisplayEvidence(primaryClaim) : [];
  renderInlineSourcePreview(sourceEvidence);
  resultsNode.innerHTML = [
    cardHtml("Document Summary", `${sourceUrl}${summary}`),
    primary,
  ].join("");
}


function getLocalCheckabilityBlock() {
  if (mode !== "claim" || !claimTextNode) return null;
  const claim = String(claimTextNode.value || "").trim();
  if (!claim) {
    return {
      code: "empty_claim",
      severity: "error",
      block: true,
      message: "Enter a fact-checkable claim before analysis.",
    };
  }

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
  const filteredEvidence = getDisplayEvidence(data);
  renderInlineSourcePreview(filteredEvidence);
  resultsNode.innerHTML = [
    claimResultHtml(data, null, false),
  ].join("");
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

function claimResultHtml(data, index = null, includeSourcePreview = false) {
  const filteredEvidence = getDisplayEvidence(data);
  const transparency = (data && data.transparency) || {};
  const verdict = (data.final_verdict || "NEUTRAL").toUpperCase();
  const verdictClass = verdict === "SUPPORT" ? "support" : verdict === "REFUTE" ? "refute" : "neutral";
  const header = index ? `Claim ${index}` : "Claim Result";
  const cleanExplanationText = sanitizeNarrative(data.explanation || "");
  const cleanConflictText = sanitizeNarrative(data.conflict_analysis || "N/A");
  const explanationDetails = buildExplanationDetails(data, filteredEvidence, cleanExplanationText);
  const claimTextLine = data.claim ? escapeHtml(data.claim) : "N/A";
  const summaryDetails = buildSummaryDetails(data, filteredEvidence, cleanConflictText);
  const transparencyBlock = renderTransparency(transparency);
  const warningBlock = renderUxWarnings(data);
  const citations = (data.citations || [])
    .filter((c) => !String(c).includes("internal://logic_engine") && !String(c).includes("logic_engine"))
    .map((c) => `<li>${escapeHtml(String(c))}</li>`)
    .join("");

  const evidenceItems = filteredEvidence
    .map((ev) => {
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
          <p>${escapeHtml(ev.text || "")}</p>
          <p class="meta">
            Source: ${escapeHtml(ev.source || "Unknown")} |
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
    `
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
    return `
      <a class="source-media-item" href="${escapeAttr(ev.url)}" target="_blank" rel="noopener noreferrer">
        <img src="${escapeAttr(logo)}" alt="${escapeHtml(domain)} logo" loading="lazy" onerror="this.src='https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64'">
        <div>
          <div>${escapeHtml(ev.source || domain)}</div>
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

function normalizeLanguageLabel(code) {
  const v = String(code || "unknown").trim().toLowerCase();
  const map = {
    en: "English",
    hi: "Hindi",
    ta: "Tamil",
    te: "Telugu",
    bn: "Bengali",
    mr: "Marathi",
    gu: "Gujarati",
    kn: "Kannada",
    ml: "Malayalam",
    pa: "Punjabi",
    ur: "Urdu",
    unknown: "Unknown",
  };
  if (map[v]) return map[v];
  if (/^[a-z]{2}(-[a-z]{2})?$/.test(v)) return v.toUpperCase();
  return "Unknown";
}

function sanitizeNarrative(text) {
  if (!text) return "";
  return String(text)
    .replace(/logic_engine/gi, "reasoning engine")
    .replace(/\binternal:\/\/logic_engine\b/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
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

  return `
    <div class="explanation-block">
      <p>${escapeHtml(intro.join(" "))}</p>
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
  const context = pickEvidenceContext(item, 520) || "No detailed evidence text available.";
  const source = item && item.source ? String(item.source).trim() : "Unknown source";
  return `<li><p>${escapeHtml(context)}</p><p class="meta">Source: ${escapeHtml(source)}</p></li>`;
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
    if (String(ev.source || "") === "logic_engine") return;
    const val = String(ev.source || "").trim();
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

function cardHtml(title, body) {
  return `<section class="card"><h3>${escapeHtml(title)}</h3>${body}</section>`;
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

