// Chat service: the single async entry point the UI calls to "send" a message.
//
// Right now it runs the local retrieval engine behind a small artificial delay
// so the UI feels live (typing indicator, etc.). This is the ONE place that
// talks to the "backend" — swap the body of sendMessage for a real fetch to
// the backend branch later and the rest of the UI is unchanged.

import { retrieve } from "./retrievalEngine.js";
import { client } from "../data/mockPortfolio.js";

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

function makeBotMessage(result) {
  return {
    id: nextId(),
    role: "assistant",
    text: result.answer,
    type: result.type, // grounded | advice_declined | unknown | empty
    citations: result.citations || [],
    data: result.data || null, // optional structured payload (chart/table)
    createdAt: new Date().toISOString(),
    // confirmation workflow (used in Step 5): clients can flag an answer for
    // advisor review. Starts unflagged.
    confirmation: "none", // none | requested
  };
}

// Simulate network/compute latency so the typing indicator is visible.
function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Main call. Returns a bot message grounded in the client's portfolio data.
export async function sendMessage(text) {
  await delay(600 + Math.random() * 500);
  const result = retrieve(text);
  return makeBotMessage(result);
}

// Expose client metadata (name, advisor, data-as-of) for headers/badges.
export function getClientInfo() {
  return client;
}
