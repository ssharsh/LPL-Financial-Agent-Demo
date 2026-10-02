import { describe, it, expect } from "vitest";
import { sendMessage, makeUserMessage, getClientInfo } from "./chatService.js";

describe("chatService — message shaping & async flow", () => {
  it("CS-1: makeUserMessage produces a normalized user message", () => {
    const m = makeUserMessage("hello");
    expect(m.role).toBe("user");
    expect(m.text).toBe("hello");
    expect(m.id).toBeTruthy();
    expect(m.createdAt).toBeTruthy();
  });

  it("CS-2: message ids are unique across calls", () => {
    const a = makeUserMessage("a");
    const b = makeUserMessage("b");
    expect(a.id).not.toBe(b.id);
  });

  it("CS-3: sendMessage resolves a grounded assistant message with confirmation=none", async () => {
    const m = await sendMessage("What is my total value?");
    expect(m.role).toBe("assistant");
    expect(m.type).toBe("grounded");
    expect(m.confirmation).toBe("none");
    expect(Array.isArray(m.citations)).toBe(true);
  });

  it("CS-4: sendMessage declines advice questions", async () => {
    const m = await sendMessage("Should I buy Apple?");
    expect(m.type).toBe("advice_declined");
    expect(m.citations).toHaveLength(0);
  });

  it("CS-5: getClientInfo returns the client identity used by the UI", () => {
    const c = getClientInfo();
    expect(c.name).toBeTruthy();
    expect(c.advisorFirm).toBe("LPL Financial");
  });
});
