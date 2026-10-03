import { describe, it, expect } from "vitest";
import { clientRoster } from "./mockPortfolio.js";

// -----------------------------------------------------------------------------
// Client roster — the data behind the top-right client selector dropdown.
// -----------------------------------------------------------------------------

describe("clientRoster — shape & integrity", () => {
  it("ROST-1: contains exactly the 10 provided clients", () => {
    expect(clientRoster).toHaveLength(10);
  });

  it("ROST-2: includes every expected client name", () => {
    const names = clientRoster.map((c) => c.name);
    expect(names).toEqual([
      "James Walker",
      "Linda Martinez",
      "Robert Nguyen",
      "Jennifer Brooks",
      "William Foster",
      "Maria Garcia",
      "Christopher Lee",
      "Ashley Davis",
      "Daniel Kim",
      "Patricia Sullivan",
    ]);
  });

  it("ROST-3: every client has id, name, accountNumber", () => {
    for (const c of clientRoster) {
      expect(c).toHaveProperty("id");
      expect(c).toHaveProperty("name");
      expect(c).toHaveProperty("accountNumber");
    }
  });

  it("ROST-4: ids are unique (dropdown keys / selection won't collide)", () => {
    const ids = clientRoster.map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("ROST-5: names are unique", () => {
    const names = clientRoster.map((c) => c.name);
    expect(new Set(names).size).toBe(names.length);
  });

  it("ROST-6: no empty or whitespace-only names (dropdown never shows a blank row)", () => {
    for (const c of clientRoster) {
      expect(typeof c.name).toBe("string");
      expect(c.name.trim().length).toBeGreaterThan(0);
    }
  });

  it("ROST-7: account numbers look masked (no full digits exposed)", () => {
    for (const c of clientRoster) {
      // Masked format uses bullet characters; should never be all plain digits.
      expect(c.accountNumber).toMatch(/•/);
      expect(c.accountNumber).not.toMatch(/^\d{6,}$/);
    }
  });

  it("ROST-EDGE: ids are usable as a lookup key (find by id returns the right client)", () => {
    const found = clientRoster.find((c) => c.id === 6);
    expect(found?.name).toBe("Maria Garcia");
  });

  it("ROST-EDGE: a non-existent id lookup returns undefined (handled by fallback in UI)", () => {
    expect(clientRoster.find((c) => c.id === 999)).toBeUndefined();
  });
});
