import { formatDate, formatTime } from "./format.js";

// Build a clean, human-readable transcript of the whole conversation that a
// client can send to LPL to have the chatbot's answers confirmed by an advisor.
export function buildTranscript(messages, client) {
  const lines = [];
  lines.push("LPL PORTFOLIO ASSISTANT — CONVERSATION TRANSCRIPT");
  lines.push("=".repeat(52));
  lines.push(`Client:        ${client.name}`);
  lines.push(`Account:       ${client.accountNumber}`);
  lines.push(`Advisor:       ${client.advisorName}, ${client.advisorFirm}`);
  lines.push(`Portfolio data as of: ${formatDate(client.dataAsOf)}`);
  lines.push(`Exported:      ${formatDate(new Date().toISOString())} ${formatTime(new Date().toISOString())}`);
  lines.push("");
  lines.push("NOTE: This assistant explains the client's portfolio using their own");
  lines.push("account data. It does not provide financial advice. Answers below are");
  lines.push("provided for advisor review and confirmation.");
  lines.push("=".repeat(52));
  lines.push("");

  if (messages.length === 0) {
    lines.push("(No conversation yet.)");
  }

  messages.forEach((m) => {
    const who = m.role === "user" ? "CLIENT" : "ASSISTANT";
    const time = formatTime(m.createdAt);
    lines.push(`[${time}] ${who}:`);
    lines.push(m.text);

    if (m.role === "assistant") {
      if (m.citations?.length) {
        lines.push("  Based on portfolio data:");
        m.citations.forEach((c) => lines.push(`    - ${c.label}: ${c.detail}`));
      }
      if (m.confirmation === "requested") {
        lines.push("  >> FLAGGED BY CLIENT FOR ADVISOR CONFIRMATION");
      }
    }
    lines.push("");
  });

  return lines.join("\n");
}

// Trigger a browser download of the transcript as a .txt file.
export function downloadTranscript(messages, client) {
  const text = buildTranscript(messages, client);
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const stamp = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `lpl-portfolio-transcript-${stamp}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
