import { describe, it, expect, vi, afterEach } from "vitest";
import {
  sendMessage,
  makeUserMessage,
  envelopeToMessage,
  getPortfolio,
  toClientInfo,
} from "./chatService.js";

const envelope = {
  text: "Your accounts are worth $292,604.36.",
  interpretation: null,
  sources: [
    { type: "portfolio_snapshot", description: "Latest portfolio snapshot per account", as_of: "2026-09-30" },
  ],
  chart: { type: "bar", x: "account_name", y: "total_value", series: "", rows: [{ account_name: "Roth IRA", total_value: "1" }] },
  log_id: "log_abc",
  verification: null,
  declined: null,
};

const jsonResponse = (status, body) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("chatService — message shaping", () => {
  it("CS-1: makeUserMessage produces a normalized user message", () => {
    const m = makeUserMessage("hello");
    expect(m.role).toBe("user");
    expect(m.text).toBe("hello");
    expect(m.id).toBeTruthy();
    expect(m.createdAt).toBeTruthy();
  });

  it("CS-2: message ids are unique across calls", () => {
    expect(makeUserMessage("a").id).not.toBe(makeUserMessage("b").id);
  });

  it("CS-3: envelope maps to a grounded message with citations, chart and log id", () => {
    const m = envelopeToMessage(envelope);
    expect(m.role).toBe("assistant");
    expect(m.text).toBe(envelope.text);
    expect(m.type).toBe("grounded");
    expect(m.confirmation).toBe("none");
    expect(m.citations).toEqual([
      {
        label: "Portfolio snapshot",
        detail: "Latest portfolio snapshot per account · as of Sep 30, 2026",
        asOf: "2026-09-30",
      },
    ]);
    expect(m.chart).toBe(envelope.chart);
    expect(m.logId).toBe("log_abc");
    expect(m.interpretation).toBeNull();
  });

  it("CS-4: declined envelopes become advice_declined", () => {
    const m = envelopeToMessage({ ...envelope, sources: [], chart: null, declined: { reason: "advice" } });
    expect(m.type).toBe("advice_declined");
    expect(m.citations).toHaveLength(0);
    expect(m.chart).toBeNull();
  });

  it("CS-5: no sources and not declined -> unknown; interpretation kept", () => {
    const m = envelopeToMessage({ ...envelope, sources: [], interpretation: "Read as: all accounts" });
    expect(m.type).toBe("unknown");
    expect(m.interpretation).toBe("Read as: all accounts");
  });
});

describe("chatService — HTTP", () => {
  it("CS-6: sendMessage POSTs /api/chat with message and conversation_id", async () => {
    const fetchMock = vi.fn(async () => jsonResponse(200, envelope));
    vi.stubGlobal("fetch", fetchMock);
    const m = await sendMessage("What are my accounts worth?", "conv-1");
    expect(m.text).toBe(envelope.text);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/chat");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ message: "What are my accounts worth?", conversation_id: "conv-1" });
  });

  it("CS-7: a non-OK response throws the backend's error message", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(502, { error: "AWS error ExpiredToken: x" })));
    await expect(sendMessage("hi", "c")).rejects.toThrow("AWS error ExpiredToken: x");
  });

  it("CS-8: a non-OK response without JSON throws a generic HTTP message", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 500, json: async () => { throw new Error("x"); } })));
    await expect(sendMessage("hi", "c")).rejects.toThrow("HTTP 500");
  });

  it("CS-9: a network failure throws the 'Could not reach' message", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fetch failed"); }));
    await expect(sendMessage("hi", "c")).rejects.toThrow(/Could not reach the portfolio assistant/);
  });

  it("CS-10: getPortfolio GETs /api/portfolio", async () => {
    const fetchMock = vi.fn(async () => jsonResponse(200, { client: { name: "Elena Park" } }));
    vi.stubGlobal("fetch", fetchMock);
    const p = await getPortfolio();
    expect(p.client.name).toBe("Elena Park");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/portfolio");
  });
});

describe("toClientInfo", () => {
  it("CS-11: maps the portfolio payload to header/transcript identity", () => {
    const info = toClientInfo({
      client: { client_id: 1, name: "Elena Park", advisor_name: "Sarah Whitfield" },
      data_as_of: "2026-09-30",
      accounts: [{ account_id: 101 }, { account_id: 102 }],
    });
    expect(info).toEqual({
      name: "Elena Park",
      accountNumber: "Accounts 101, 102",
      advisorName: "Sarah Whitfield",
      advisorFirm: "LPL Financial",
      dataAsOf: "2026-09-30",
    });
  });
});
