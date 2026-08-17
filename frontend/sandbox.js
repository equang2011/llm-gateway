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
        refreshVariablesPanel();
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
      refreshVariablesPanel();
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
  refreshVariablesPanel();
});

// ---- Prompt variables ------------------------------------------------------
// Everything in this section is pure (no DOM access, no module state) so it can
// be verified directly. The sandbox is deliberately ignorant of what any
// variable means — it only detects `{simple_identifier}` placeholders, collects
// text for them, and substitutes that text literally.

// A fresh regex per call on purpose: /g patterns carry lastIndex between uses,
// and sharing one instance across .replace() and .exec() loops silently skips
// matches.
//
// The {{ }} branch is listed FIRST deliberately. Scanning runs left to right,
// so in a literal "{{topic}}" the opening "{{" is consumed before the
// placeholder branch can treat it as a variable — Python-style escaped braces
// in prompts survive untouched.
//
// The identifier pattern is intentionally strict: {user.name}, {foo-bar},
// {hello world} and {"foo": "bar"} all fail to match and are left as literal
// text rather than being treated as variables or as errors.
function placeholderScanner() {
  return /(\{\{|\}\})|\{([A-Za-z_][A-Za-z0-9_]*)\}/g;
}

// Unique variable names across all message templates, in first-appearance
// order. Callers pass the templates in, so this never reads the DOM.
function discoverVariables(messageList) {
  const names = [];
  const seen = new Set();

  messageList.forEach((message) => {
    const scanner = placeholderScanner();
    let match;
    while ((match = scanner.exec(message.content)) !== null) {
      const name = match[2];
      if (name !== undefined && !seen.has(name)) {
        seen.add(name);
        names.push(name);
      }
    }
  });

  return names;
}

// Single-pass substitution over the original template. Values are supplied by
// a callback, which means (a) they are never rescanned, so a value containing
// "{topic}" stays literal, and (b) "$&"-style sequences inside pasted JSON are
// inserted as-is rather than interpreted as replacement patterns.
//
// `values` is a Map, not a plain object, on purpose. Variable names are
// arbitrary developer input, and a template containing {__proto__},
// {constructor} or {toString} would resolve against Object.prototype on a plain
// object and splice a function or "[object Object]" into the prompt.
//
// A placeholder with no entry in `values` is an internal bug, not a blank
// value: callers derive `values` from discoverVariables(), so every detected
// name must be present. Throwing beats silently shipping a raw {placeholder}
// to the provider.
function renderTemplate(template, values) {
  return template.replace(placeholderScanner(), (match, doubled, name) => {
    if (doubled !== undefined) return match;
    if (!values.has(name)) {
      throw new Error(`Internal error: no value entry for {${name}}.`);
    }
    return values.get(name);
  });
}

// Renders every message against the same values, dropping any that come out
// empty. Rendering happens before trimming so a message consisting only of a
// blank variable correctly drops out.
function renderAllMessages(messageList, values) {
  return messageList
    .map((message) => ({
      role: message.role,
      content: renderTemplate(message.content, values).trim(),
    }))
    .filter((message) => message.content.length > 0);
}

// ---- Request building ------------------------------------------------------

// In-memory only, for this page session. Deliberately NOT persisted: values may
// hold curricula, contracts, learner context or other proprietary text. Keyed
// by variable name; entries survive a variable disappearing from the panel so
// switching prompts back and forth does not lose work.
const variableValues = new Map();

// One entry per currently-referenced variable, defaulting to "" for names the
// developer has not filled in yet.
function readVariableValues(names) {
  const values = new Map();
  names.forEach((name) => {
    values.set(name, variableValues.get(name) ?? "");
  });
  return values;
}

// The single source of truth for "what the gateway will receive". Both the
// preview and the request payload go through this, so they cannot diverge.
function renderedMessages() {
  const names = discoverVariables(messages);
  return renderAllMessages(messages, readVariableValues(names));
}

function buildInvokeRequest(model) {
  return { model, messages: renderedMessages() };
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

// History holds RENDERED messages, so substituted variable values (curricula,
// contracts, learner context) land in localStorage. That is pre-existing
// behaviour, kept because history is only useful if it shows what was actually
// sent — but it does mean "Clear" is the way to purge injected data.
//
// A large pasted value can also exceed the ~5MB quota. Failing to persist must
// not break a run that already succeeded, so quota errors are swallowed and the
// in-memory results stay intact.
function persistResults() {
  try {
    localStorage.setItem(HISTORY_STORAGE_NAME, JSON.stringify(history));
    if (current) {
      localStorage.setItem(CURRENT_STORAGE_NAME, JSON.stringify(current));
    } else {
      localStorage.removeItem(CURRENT_STORAGE_NAME);
    }
  } catch {
    // Most likely QuotaExceededError from a large rendered prompt.
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
  refreshVariablesPanel();
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
const previewButton = document.getElementById("preview-button");
const variablesFieldsEl = document.getElementById("variables-fields");

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

// ---- Dynamic variables panel -----------------------------------------------

// Tracks which field set is currently on screen so the panel is only rebuilt
// when the discovered names actually change. Without this, every keystroke in a
// message textarea would tear down and recreate every variable field.
let renderedVariableKey = null;

function buildVariableField(name) {
  const field = document.createElement("div");
  field.className = "var-field";

  const label = document.createElement("label");
  const fieldId = `var-${name}`;
  label.setAttribute("for", fieldId);
  // Literal placeholder, so there is never ambiguity about which variable a
  // field populates. No name-prettifying heuristics.
  label.textContent = `{${name}}`;
  field.appendChild(label);

  const textarea = document.createElement("textarea");
  textarea.id = fieldId;
  textarea.rows = 3;
  textarea.value = variableValues.get(name) ?? "";
  textarea.addEventListener("input", (event) => {
    variableValues.set(name, event.target.value);
  });
  field.appendChild(textarea);

  return field;
}

function refreshVariablesPanel() {
  const names = discoverVariables(messages);

  // A space cannot appear inside an identifier, so it is a safe joiner.
  const key = names.join(" ");
  if (key === renderedVariableKey) return;
  renderedVariableKey = key;

  variablesFieldsEl.replaceChildren();

  // Every discovered name gets an entry immediately, so renderTemplate's
  // missing-entry guard only ever fires on a genuine bug.
  names.forEach((name) => {
    if (!variableValues.has(name)) variableValues.set(name, "");
  });

  if (names.length === 0) {
    const empty = document.createElement("p");
    empty.className = "variables-empty";
    empty.textContent = "No variables detected in the current messages.";
    variablesFieldsEl.appendChild(empty);
    return;
  }

  names.forEach((name) => {
    variablesFieldsEl.appendChild(buildVariableField(name));
  });
}

// Opens the fully rendered messages in a separate window so the main sandbox
// stays uncluttered. Content is set via textContent, never innerHTML.
function openPreviewWindow() {
  let rendered;
  try {
    rendered = renderedMessages();
  } catch (err) {
    showError(err.message);
    return;
  }

  if (rendered.length === 0) {
    showError("Nothing to preview — all messages are empty.");
    return;
  }

  const separator = `\n\n${"-".repeat(60)}\n\n`;
  const text = rendered
    .map((m) => `[${m.role}]\n${m.content}`)
    .join(separator);

  const win = window.open(
    "",
    "sandbox-preview",
    "width=900,height=700,scrollbars=yes",
  );
  if (!win) {
    showError("Preview window was blocked. Allow popups for this page.");
    return;
  }

  // Static shell only — no user content goes through document.write().
  win.document.open();
  win.document.write(
    "<!doctype html><html><head><title>Rendered messages</title></head><body></body></html>",
  );
  win.document.close();

  const pre = win.document.createElement("pre");
  pre.textContent = text;
  pre.style.cssText =
    "white-space: pre-wrap; word-break: break-word; margin: 0; padding: 1rem; " +
    "font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px;";
  win.document.body.appendChild(pre);
  win.focus();
}

previewButton.addEventListener("click", openPreviewWindow);

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

  // No required/optional distinction: the sandbox cannot know the semantics of
  // an arbitrary variable, so a deliberately blank value is legitimate and
  // renders to an empty string.
  let requestBody;
  try {
    requestBody = buildInvokeRequest(model);
  } catch (err) {
    showError(err.message);
    return;
  }

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
refreshVariablesPanel();
renderHistory();
renderCurrentResponse();
showResultsColumnIfNeeded();
