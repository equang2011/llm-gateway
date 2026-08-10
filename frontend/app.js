// Base URL of the gateway API. Same-origin by default; change if the
// frontend is served from somewhere other than the FastAPI app itself.
const GATEWAY_URL = "/invoke";

// ---- Request building -----------------------------------------------

function buildInvokeRequest(model, message) {
  return {
    model,
    messages: [{ role: "user", content: message }],
  };
}

// ---- API call ----------------------------------------------------------

async function callInvoke(requestBody) {
  const response = await fetch(GATEWAY_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Request failed (${response.status}): ${detail}`);
  }

  return response.json();
}

// ---- UI wiring -----------------------------------------------------------

const form = document.getElementById("invoke-form");
const modelSelect = document.getElementById("model");
const messageInput = document.getElementById("message");
const submitButton = document.getElementById("submit-button");
const statusEl = document.getElementById("status");
const responsePanel = document.getElementById("response-panel");
const responseContent = document.getElementById("response-content");
const responseMeta = document.getElementById("response-meta");

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  statusEl.hidden = !isLoading;
  statusEl.textContent = isLoading ? "Waiting for response..." : "";
  statusEl.classList.remove("error");
}

function showError(message) {
  statusEl.hidden = false;
  statusEl.textContent = message;
  statusEl.classList.add("error");
}

function showResponse(invokeResponse) {
  responsePanel.hidden = false;
  responseContent.textContent = invokeResponse.content;
  responseMeta.textContent = `model: ${invokeResponse.model} · finish_reason: ${invokeResponse.finish_reason}`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const model = modelSelect.value;
  const message = messageInput.value.trim();
  if (!message) return;

  responsePanel.hidden = true;
  setLoading(true);

  try {
    const requestBody = buildInvokeRequest(model, message);
    const invokeResponse = await callInvoke(requestBody);
    showResponse(invokeResponse);
    statusEl.hidden = true;
  } catch (err) {
    showError(err.message);
  } finally {
    submitButton.disabled = false;
  }
});
