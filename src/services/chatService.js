// Chat service: the one place the UI talks to the backend.
//
// The Vite dev server proxies /api to the Python backend on 127.0.0.1:8000
// (see vite.config.js). The backend returns a response "envelope"
// {text, interpretation, sources, chart, log_id, verification, declined};
// envelopeToMessage maps it to the message shape the UI renders.
import { formatDate } from "../utils/format.js";
import { humanizeKey } from "../utils/chartSpec.js";

// Slightly longer than the backend's own 90 s chat timeout so its JSON error wins.
export const API_TIMEOUT_MS = 100000;

let idCounter = 0;
function nextId() {
  idCounter += 1;
  return `msg-${Date.now()}-${idCounter}`;
}

// Build a normalized message object the UI renders.
export function makeUserMessage(text) {
  return {
    id: nextId(),
    role: "user",
    text,
    createdAt: new Date().toISOString(),
  };
}

// Optional ?client=N in the page URL picks the demo client (1, 2 or 3).
export function clientParam() {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("client");
}

// One id per page load so the backend keeps the conversation history.
export function newConversationId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `conv-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function requestJson(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  let response;
  try {
    response = await fetch(path, { ...options, signal: controller.signal });
  } catch (err) {
    if (err?.name === "AbortError") {
      throw new Error("The assistant took too long to answer. Please try again.");
    }
    throw new Error("Could not reach the portfolio assistant. Is the backend running on port 8000?");
  } finally {
    clearTimeout(timer);
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) {
    throw new Error(body?.error || `The assistant service returned an error (HTTP ${response.status}).`);
  }
  if (body === null) {
    throw new Error("The assistant service returned an unreadable response.");
  }
  return body;
}

// Backend envelope -> UI message.
export function envelopeToMessage(env) {
  const sources = Array.isArray(env?.sources) ? env.sources : [];
  return {
    id: nextId(),
    role: "assistant",
    text: env?.text ?? "",
    type: env?.declined ? "advice_declined" : sources.length ? "grounded" : "unknown",
    citations: sources.map((s) => ({
      label: humanizeKey(s.type),
      detail: `${s.description} · as of ${formatDate(s.as_of)}`,
      asOf: s.as_of,
    })),
    chart: env?.chart ?? null,
    interpretation: env?.interpretation ?? null,
    logId: env?.log_id ?? null,
    createdAt: new Date().toISOString(),
    // Clients can flag an answer for advisor review. Starts unflagged.
    confirmation: "none", // none | requested
  };
}

// Send one question; resolves to an assistant message or throws an Error with
// a message that is safe to show the user.
export async function sendMessage(text, conversationId) {
  const env = await requestJson("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: text,
      conversation_id: conversationId,
      client_id: clientParam() ?? undefined,
    }),
  });
  return envelopeToMessage(env);
}

// Portfolio panel + header data, from the same fact tools the chat uses.
export async function getPortfolio() {
  const client = clientParam();
  const query = client ? `?client_id=${encodeURIComponent(client)}` : "";
  return requestJson(`/api/portfolio${query}`);
}

// Header / transcript identity shown while the portfolio is loading.
export const PLACEHOLDER_CLIENT = {
  name: "Loading…",
  accountNumber: "",
  advisorName: "—",
  advisorFirm: "LPL Financial",
  dataAsOf: null,
};

export function toClientInfo(portfolio) {
  const ids = (portfolio?.accounts ?? []).map((a) => a.account_id);
  return {
    name: portfolio?.client?.name ?? "—",
    accountNumber: ids.length ? `Accounts ${ids.join(", ")}` : "",
    advisorName: portfolio?.client?.advisor_name ?? "—",
    advisorFirm: "LPL Financial",
    dataAsOf: portfolio?.data_as_of ?? null,
  };
}
