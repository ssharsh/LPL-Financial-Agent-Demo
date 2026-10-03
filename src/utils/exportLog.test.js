import { describe, it, expect } from "vitest";
import { buildTranscript } from "./exportLog.js";

const client = {
  name: "Jordan Avery",
  accountNumber: "LPL-••••-4821",
  advisorName: "Dana Whitfield, CFP®",
  advisorFirm: "LPL Financial",
  dataAsOf: "2026-10-01T20:00:00.000Z",
};

const messages = [
  {
    id: "m1",
    role: "user",
    text: "What is my total value?",
    createdAt: "2026-10-02T14:00:00.000Z",
  },
  {
    id: "m2",
    role: "assistant",
    text: "Your portfolio is worth $742,318.55.",
    type: "grounded",
    citations: [{ label: "Total value", detail: "$742,318.55", asOf: client.dataAsOf }],
    confirmation: "requested",
    createdAt: "2026-10-02T14:00:02.000Z",
  },
];

describe("buildTranscript (export log for advisor review)", () => {
  it("EXP-1: includes client identity header", () => {
    const t = buildTranscript(messages, client);
    expect(t).toContain("Jordan Avery");
    expect(t).toContain("LPL-••••-4821");
    expect(t).toContain("Dana Whitfield, CFP®");
  });

  it("EXP-2: includes the not-advice compliance note", () => {
    const t = buildTranscript(messages, client);
    expect(t.toLowerCase()).toContain("does not provide financial advice");
  });

  it("EXP-3: renders both client and assistant turns", () => {
    const t = buildTranscript(messages, client);
    expect(t).toContain("CLIENT:");
    expect(t).toContain("ASSISTANT:");
    expect(t).toContain("What is my total value?");
    expect(t).toContain("Your portfolio is worth $742,318.55.");
  });

  it("EXP-4: shows citations under the assistant answer", () => {
    const t = buildTranscript(messages, client);
    expect(t).toContain("Based on portfolio data:");
    expect(t).toContain("Total value: $742,318.55");
  });

  it("EXP-5: marks answers the client flagged for confirmation", () => {
    const t = buildTranscript(messages, client);
    expect(t).toContain("FLAGGED BY CLIENT FOR ADVISOR CONFIRMATION");
  });

  it("EXP-6: includes the backend log id under assistant answers", () => {
    const withLog = [messages[0], { ...messages[1], logId: "log_abc123" }];
    expect(buildTranscript(withLog, client)).toContain("  Log ID: log_abc123");
    expect(buildTranscript(messages, client)).not.toContain("Log ID:");
  });

  it("EXP-EDGE: an empty conversation still produces a valid transcript", () => {
    const t = buildTranscript([], client);
    expect(t).toContain("No conversation yet");
    expect(t).toContain("Jordan Avery");
  });
});
