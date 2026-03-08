const tabs = document.querySelectorAll(".tab");
const blocks = document.querySelectorAll(".mode-block");
const form = document.getElementById("analyzer-form");
const runBtn = document.getElementById("run-btn");
const cancelBtn = document.getElementById("cancel-btn");
const statusNode = document.getElementById("status");
const resultsNode = document.getElementById("results");
const previewNode = document.getElementById("process-preview");
const stepsNode = document.getElementById("process-steps");

let mode = "claim";
let currentController = null;
let progressTimer = null;
let progressIndex = 0;
let activeSteps = [];

const stageTemplates = {
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
    resetProgressPanel();
  });
}

cancelBtn.addEventListener("click", () => {
  if (currentController) {
    currentController.abort();
    statusNode.textContent = "Cancelled.";
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  runBtn.disabled = true;
  cancelBtn.hidden = false;
  statusNode.textContent = "Analyzing...";
  resultsNode.innerHTML = "";

  startProgressForCurrentInput();
  currentController = new AbortController();

  try {
    const data = await callApiForMode(currentController.signal);
    completeProgress();
    renderResult(data);
    statusNode.textContent = "Done.";
  } catch (error) {
    if (error.name === "AbortError") {
      statusNode.textContent = "Cancelled.";
      setStepState(progressIndex, "done");
      stepsNode.insertAdjacentHTML("beforeend", `<li>Process cancelled by user</li>`);
    } else {
      statusNode.textContent = "Failed.";
      stepsNode.insertAdjacentHTML("beforeend", `<li>${escapeHtml(error.message)}</li>`);
      resultsNode.innerHTML = cardHtml("Error", `<p>${escapeHtml(error.message)}</p>`);
    }
  } finally {
    stopProgressTimer();
    currentController = null;
    runBtn.disabled = false;
    cancelBtn.hidden = true;
  }
});

function getCurrentInputPreview() {
  if (mode === "claim") {
    const claim = document.getElementById("claim-text").value.trim();
    return claim || "No claim entered";
  }
  if (mode === "url") {
    const url = document.getElementById("url-text").value.trim();
    return url || "No URL entered";
  }
  if (mode === "pdf") {
    const file = document.getElementById("pdf-file").files[0];
    return file ? `PDF: ${file.name}` : "No PDF selected";
  }
  const file = document.getElementById("image-file").files[0];
  return file ? `Image: ${file.name}` : "No image selected";
}

function startProgressForCurrentInput() {
  previewNode.textContent = `Preview: ${getCurrentInputPreview()}`;
  activeSteps = [...(stageTemplates[mode] || stageTemplates.claim)];
  stepsNode.innerHTML = activeSteps.map((step) => `<li>${escapeHtml(step)}</li>`).join("");
  progressIndex = 0;
  setStepState(progressIndex, "active");

  stopProgressTimer();
  progressTimer = setInterval(() => {
    if (progressIndex >= activeSteps.length - 1) {
      return;
    }
    setStepState(progressIndex, "done");
    progressIndex += 1;
    setStepState(progressIndex, "active");
  }, 2500);
}

function completeProgress() {
  stopProgressTimer();
  const items = stepsNode.querySelectorAll("li");
  items.forEach((item) => {
    item.classList.remove("active");
    item.classList.add("done");
  });
  stepsNode.insertAdjacentHTML("beforeend", "<li class=\"done\">Completed</li>");
}

function resetProgressPanel() {
  stopProgressTimer();
  previewNode.textContent = "Submit a claim, URL, PDF, or image to start.";
  stepsNode.innerHTML = "";
}

function stopProgressTimer() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

function setStepState(index, state) {
  const items = stepsNode.querySelectorAll("li");
  if (!items[index]) {
    return;
  }
  items[index].classList.remove("active", "done");
  if (state) {
    items[index].classList.add(state);
  }
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

async function postJson(url, body, signal) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  return handleResponse(response);
}

async function postFile(url, file, signal) {
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

  const claimCards = data.results.map((result, idx) => claimResultHtml(result, idx + 1)).join("");
  const sourceUrl = data.source_url ? `<p class="meta">Source: <a href="${escapeAttr(data.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(data.source_url)}</a></p>` : "";
  resultsNode.innerHTML = [
    cardHtml("Document Summary", `${sourceUrl}${summary}`),
    cardHtml("Claim-Level Results", claimCards),
  ].join("");
}

function renderClaimResult(data) {
  resultsNode.innerHTML = claimResultHtml(data);
}

function claimResultHtml(data, index = null) {
  const verdict = (data.final_verdict || "NEUTRAL").toUpperCase();
  const verdictClass = verdict === "SUPPORT" ? "support" : verdict === "REFUTE" ? "refute" : "neutral";
  const header = index ? `Claim ${index}` : "Claim Result";
  const claimText = data.claim ? `<p><strong>Claim:</strong> ${escapeHtml(data.claim)}</p>` : "";
  const explanation = data.explanation ? `<p>${escapeHtml(data.explanation)}</p>` : "<p>No explanation provided.</p>";
  const citations = (data.citations || []).map((c) => `<li>${escapeHtml(String(c))}</li>`).join("");

  const evidenceItems = (data.evidence || [])
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
          ${ev.url ? `<a href="${escapeAttr(ev.url)}" target="_blank" rel="noopener noreferrer">Open source</a>` : ""}
        </article>
      `;
    })
    .join("");

  return cardHtml(
    header,
    `
      ${claimText}
      <div class="kpi">
        <div class="tile"><span>Verdict</span><strong><span class="pill ${verdictClass}">${escapeHtml(verdict)}</span></strong></div>
        <div class="tile"><span>Confidence</span><strong>${formatPct(data.confidence)}</strong></div>
        <div class="tile"><span>Language</span><strong>${escapeHtml(data.language || "Unknown")}</strong></div>
      </div>
      <h4>Explanation</h4>
      ${explanation}
      <h4>Evidence</h4>
      <div class="evidence-list">${evidenceItems || "<p>No evidence returned.</p>"}</div>
      <h4>Conflict Analysis</h4>
      <p>${escapeHtml(data.conflict_analysis || "N/A")}</p>
      <h4>Citations</h4>
      ${citations ? `<ol>${citations}</ol>` : "<p>No citations returned.</p>"}
    `
  );
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
