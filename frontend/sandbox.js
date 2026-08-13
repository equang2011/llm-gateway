// Prompt-testing sandbox. Talks to the same /invoke endpoint as the main
// demo — no backend changes needed, since InvokeRequest already accepts an
// ordered list of {role, content} messages.
const GATEWAY_URL = "/invoke";
const MAX_MESSAGES = 10;
const MAX_HISTORY = 4;
const KEY_STORAGE_NAME = "llmGatewaySandboxKey";
const HISTORY_STORAGE_NAME = "llmGatewaySandboxHistory";
const CURRENT_STORAGE_NAME = "llmGatewaySandboxCurrent";
// Matches the "deepseek-v4-flash" entry in app/model_catalog.py. Update
// both places together if the provider ID changes.
const DEFAULT_MODEL = "deepseek/deepseek-v4-flash";

const COPY_ICON_SVG = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
const EXPORT_ICON_SVG = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>`;

// ---- Message-builder state -------------------------------------------------
// messages[0] is always the fixed system prompt. Everything after it is a
// user/assistant turn the user can add, flip role on, or remove.
let messages = [{ role: "system", content: "" }];

function nextDefaultRole(index) {
  return index % 2 === 1 ? "user" : "assistant";
}

const messageListEl = document.getElementById("message-list");
const addMessageButton = document.getElementById("add-message-button");

function renderMessages() {
  messageListEl.innerHTML = "";

  messages.forEach((msg, index) => {
    const block = document.createElement("div");
    block.className = "msg-block";

    const header = document.createElement("div");
    header.className = "msg-block-header";

    if (index === 0) {
      const label = document.createElement("span");
      label.className = "msg-role-label";
      label.textContent = "system (prompt)";
      header.appendChild(label);
    } else {
      const roleSelect = document.createElement("select");
      roleSelect.className = "msg-role";
      ["user", "assistant"].forEach((role) => {
        const option = document.createElement("option");
        option.value = role;
        option.textContent = role;
        if (role === msg.role) option.selected = true;
        roleSelect.appendChild(option);
      });
      roleSelect.addEventListener("change", (event) => {
        messages[index].role = event.target.value;
      });
      header.appendChild(roleSelect);

      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.className = "msg-remove";
      removeButton.textContent = "×";
      removeButton.addEventListener("click", () => {
        messages.splice(index, 1);
        renderMessages();
      });
      header.appendChild(removeButton);
    }

    block.appendChild(header);

    const textarea = document.createElement("textarea");
    textarea.className = "msg-content";
    textarea.rows = index === 0 ? 4 : 3;
    textarea.placeholder =
      index === 0 ? "System prompt..." : `${msg.role} message...`;
    textarea.value = msg.content;
    textarea.addEventListener("input", (event) => {
      messages[index].content = event.target.value;
    });
    block.appendChild(textarea);

    messageListEl.appendChild(block);
  });

  addMessageButton.disabled = messages.length >= MAX_MESSAGES;
}

addMessageButton.addEventListener("click", () => {
  if (messages.length >= MAX_MESSAGES) return;
  messages.push({ role: nextDefaultRole(messages.length), content: "" });
  renderMessages();
});

// ---- Request building ------------------------------------------------------

function buildInvokeRequest(model) {
  const nonEmpty = messages
    .map((m) => ({ role: m.role, content: m.content.trim() }))
    .filter((m) => m.content.length > 0);

  return { model, messages: nonEmpty };
}

// ---- API call ----------------------------------------------------------

async function callInvoke(requestBody, gatewayKey) {
  const headers = { "Content-Type": "application/json" };
  if (gatewayKey) {
    headers["Authorization"] = `Bearer ${gatewayKey}`;
  }

  const response = await fetch(GATEWAY_URL, {
    method: "POST",
    headers,
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status})`;
    try {
      const body = await response.json();
      const err = body?.detail?.error;
      if (err?.message) message = `${err.code}: ${err.message}`;
    } catch {
      // response wasn't JSON — fall back to the generic message above
    }
    throw new Error(message);
  }

  return response.json();
}

// ---- History / current-result state ----------------------------------------
// `current` is the most recent completed run. `history` holds up to the
// previous MAX_HISTORY runs (newest first). Both persist to localStorage so
// a page reload doesn't lose your last few iterations.

function loadJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

let history = loadJSON(HISTORY_STORAGE_NAME, []);
let current = loadJSON(CURRENT_STORAGE_NAME, null);

function persistResults() {
  localStorage.setItem(HISTORY_STORAGE_NAME, JSON.stringify(history));
  if (current) {
    localStorage.setItem(CURRENT_STORAGE_NAME, JSON.stringify(current));
  } else {
    localStorage.removeItem(CURRENT_STORAGE_NAME);
  }
}

function truncate(text, n) {
  return text.length > n ? `${text.slice(0, n)}…` : text;
}

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function copyText(text) {
  navigator.clipboard.writeText(text).catch(() => {});
}

function exportTranscript(entry) {
  const lines = [
    `model: ${entry.model}`,
    `timestamp: ${new Date(entry.timestamp).toISOString()}`,
    "",
  ];
  entry.messages.forEach((m) => {
    lines.push(`[${m.role}]`, m.content, "");
  });
  lines.push("[response]", entry.response.content);

  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `sandbox-${entry.timestamp}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

function loadEntryIntoForm(entry) {
  const systemMsg = entry.messages.find((m) => m.role === "system");
  const others = entry.messages.filter((m) => m !== systemMsg);

  messages = [
    { role: "system", content: systemMsg ? systemMsg.content : "" },
    ...others.map((m) => ({ role: m.role, content: m.content })),
  ];

  if (entry.model === DEFAULT_MODEL) {
    modelModeSelect.value = "default";
    modelCustomInput.hidden = true;
    modelCustomInput.required = false;
  } else {
    modelModeSelect.value = "custom";
    modelCustomInput.hidden = false;
    modelCustomInput.required = true;
    modelCustomInput.value = entry.model;
  }

  renderMessages();
  document
    .getElementById("sandbox-form")
    .scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderHistory() {
  const listEl = document.getElementById("history-list");
  listEl.innerHTML = "";

  if (history.length === 0) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = "No previous runs yet.";
    listEl.appendChild(empty);
    return;
  }

  history.forEach((entry) => {
    const details = document.createElement("details");
    details.className = "history-entry";

    const summary = document.createElement("summary");
    const lastUser = [...entry.messages].reverse().find((m) => m.role === "user");
    const preview = lastUser ? truncate(lastUser.content, 40) : "(no user message)";
    summary.textContent = `${formatTime(entry.timestamp)} · ${preview}`;
    details.appendChild(summary);

    const body = document.createElement("div");
    body.className = "history-entry-body";

    const modelLine = document.createElement("p");
    modelLine.className = "history-meta";
    modelLine.textContent = `model: ${entry.model}${formatLatency(entry.latencyMs)}`;
    body.appendChild(modelLine);

    entry.messages.forEach((m) => {
      const p = document.createElement("p");
      p.className = "history-msg";
      const label = document.createElement("strong");
      label.textContent = `${m.role}: `;
      p.appendChild(label);
      p.appendChild(document.createTextNode(m.content));
      body.appendChild(p);
    });

    const outputP = document.createElement("p");
    outputP.className = "history-msg history-output";
    const outLabel = document.createElement("strong");
    outLabel.textContent = "output: ";
    outputP.appendChild(outLabel);
    outputP.appendChild(document.createTextNode(entry.response.content));
    body.appendChild(outputP);

    const actions = document.createElement("div");
    actions.className = "history-entry-actions";

    const loadButton = document.createElement("button");
    loadButton.type = "button";
    loadButton.className = "link-button";
    loadButton.textContent = "Load into form";
    loadButton.addEventListener("click", () => loadEntryIntoForm(entry));
    actions.appendChild(loadButton);

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "icon-button";
    copyBtn.title = "Copy response";
    copyBtn.innerHTML = COPY_ICON_SVG;
    copyBtn.addEventListener("click", () => copyText(entry.response.content));
    actions.appendChild(copyBtn);

    const exportBtn = document.createElement("button");
    exportBtn.type = "button";
    exportBtn.className = "icon-button";
    exportBtn.title = "Export as .txt";
    exportBtn.innerHTML = EXPORT_ICON_SVG;
    exportBtn.addEventListener("click", () => exportTranscript(entry));
    actions.appendChild(exportBtn);

    body.appendChild(actions);
    details.appendChild(body);
    listEl.appendChild(details);
  });
}

function formatLatency(latencyMs) {
  return typeof latencyMs === "number" ? ` · ${Math.round(latencyMs)} ms` : "";
}

function renderCurrentResponse() {
  if (!current) {
    responseContent.textContent = "";
    responseMeta.textContent = "";
    return;
  }
  responseContent.textContent = current.response.content;
  responseMeta.textContent =
    `model: ${current.response.model} · finish_reason: ${current.response.finish_reason}` +
    formatLatency(current.latencyMs);
}

function showResultsColumnIfNeeded() {
  if (current || history.length > 0) {
    resultsColumn.hidden = false;
    pageEl.classList.add("has-results");
  }
}

// ---- UI wiring -----------------------------------------------------------

const form = document.getElementById("sandbox-form");
const modelModeSelect = document.getElementById("model-mode");
const modelCustomInput = document.getElementById("model-custom");
const keyInput = document.getElementById("gateway-key");
const submitButton = document.getElementById("submit-button");
const statusEl = document.getElementById("status");
const pageEl = document.getElementById("page");
const resultsColumn = document.getElementById("results-column");
const responseContent = document.getElementById("response-content");
const responseMeta = document.getElementById("response-meta");
const copyResponseButton = document.getElementById("copy-response-button");
const exportResponseButton = document.getElementById("export-response-button");
const clearHistoryButton = document.getElementById("clear-history-button");

copyResponseButton.innerHTML = COPY_ICON_SVG;
exportResponseButton.innerHTML = EXPORT_ICON_SVG;

copyResponseButton.addEventListener("click", () => {
  if (current) copyText(current.response.content);
});
exportResponseButton.addEventListener("click", () => {
  if (current) exportTranscript(current);
});
clearHistoryButton.addEventListener("click", () => {
  history = [];
  current = null;
  localStorage.removeItem(HISTORY_STORAGE_NAME);
  localStorage.removeItem(CURRENT_STORAGE_NAME);
  renderHistory();
  renderCurrentResponse();
  resultsColumn.hidden = true;
  pageEl.classList.remove("has-results");
});

const savedKey = localStorage.getItem(KEY_STORAGE_NAME);
if (savedKey) keyInput.value = savedKey;

modelModeSelect.addEventListener("change", () => {
  const isCustom = modelModeSelect.value === "custom";
  modelCustomInput.hidden = !isCustom;
  modelCustomInput.required = isCustom;
  if (isCustom) modelCustomInput.focus();
});

function resolveModel() {
  return modelModeSelect.value === "default"
    ? DEFAULT_MODEL
    : modelCustomInput.value.trim();
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  statusEl.hidden = !isLoading;
  statusEl.textContent = isLoading ? "Request sent — waiting on provider..." : "";
  statusEl.classList.remove("error");
}

function showError(message) {
  statusEl.hidden = false;
  statusEl.textContent = message;
  statusEl.classList.add("error");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const model = resolveModel();
  const gatewayKey = keyInput.value.trim();
  if (!model) {
    showError("Enter a model ID (Custom mode requires one).");
    return;
  }

  if (gatewayKey) {
    localStorage.setItem(KEY_STORAGE_NAME, gatewayKey);
  }

  const requestBody = buildInvokeRequest(model);
  if (requestBody.messages.length === 0) {
    showError("Add at least one non-empty message.");
    return;
  }

  setLoading(true);
  const requestStart = performance.now();

  try {
    const invokeResponse = await callInvoke(requestBody, gatewayKey);
    const latencyMs = performance.now() - requestStart;

    if (current) {
      history.unshift(current);
      if (history.length > MAX_HISTORY) history.length = MAX_HISTORY;
    }
    current = {
      model: requestBody.model,
      messages: requestBody.messages,
      response: invokeResponse,
      timestamp: Date.now(),
      latencyMs,
    };
    persistResults();
    renderHistory();
    renderCurrentResponse();
    showResultsColumnIfNeeded();

    statusEl.hidden = true;
  } catch (err) {
    showError(err.message);
  } finally {
    submitButton.disabled = false;
  }
});

// ---- Initial render --------------------------------------------------------

renderMessages();
renderHistory();
renderCurrentResponse();
showResultsColumnIfNeeded();
