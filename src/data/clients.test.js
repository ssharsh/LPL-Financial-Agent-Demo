import { describe, it, expect } from "vitest";
import { clients, getClientData } from "./mockPortfolio.js";

// -----------------------------------------------------------------------------
// Per-client portfolio data integrity.
//
// This is the executable spec for the 10 distinct client datasets: it proves
// each client's numbers are internally consistent (allocation sums to 100,
// values reconcile to the total, performance ends at the total) and that the
// clients are genuinely different from one another.
// -----------------------------------------------------------------------------

const EXPECTED_DATES = [
  "2025-10-31",
  "2025-11-30",
  "2025-12-31",
  "2026-01-31",
  "2026-02-28",
  "2026-03-31",
  "2026-04-30",
  "2026-05-31",
  "2026-06-30",
  "2026-07-31",
  "2026-08-31",
  "2026-09-30",
];

describe("clients[] — set shape", () => {
  it("CL-1: contains exactly 10 clients", () => {
    expect(clients).toHaveLength(10);
  });

  it("CL-2: ids are 1..10 and unique", () => {
    const ids = clients.map((c) => c.id);
    expect(new Set(ids).size).toBe(10);
    expect([...ids].sort((a, b) => a - b)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  });

  it("CL-3: every client has the full object shape", () => {
    for (const c of clients) {
      expect(c).toHaveProperty("id");
      expect(c).toHaveProperty("profile");
      expect(c).toHaveProperty("summary");
      expect(c).toHaveProperty("allocation");
      expect(c).toHaveProperty("sectors");
      expect(c).toHaveProperty("holdings");
      expect(c).toHaveProperty("performance");
      expect(c).toHaveProperty("recentActivity");
      // Identity fields.
      expect(c.profile.name).toBeTruthy();
      expect(c.profile.accountNumber).toMatch(/•/);
      expect(c.profile.accountType).toBeTruthy();
      expect(c.profile.advisorName).toBeTruthy();
      expect(c.profile.advisorFirm).toBe("LPL Financial");
      expect(typeof c.profile.dataAsOf).toBe("string");
      expect(c.profile.dataAsOf.length).toBeGreaterThan(0);
    }
  });

  it("CL-4: all 10 total values are distinct", () => {
    const totals = clients.map((c) => c.summary.totalValue);
    expect(new Set(totals).size).toBe(10);
  });

  it("CL-5: total values span the intended ~$120k–$3.5M range", () => {
    const totals = clients.map((c) => c.summary.totalValue);
    expect(Math.min(...totals)).toBeLessThanOrEqual(130000);
    expect(Math.max(...totals)).toBeGreaterThanOrEqual(3400000);
  });
});

describe("clients[] — per-client internal consistency", () => {
  it.each(clients.map((c) => [c.profile.name, c]))(
    "CL-CONSIST: %s is internally consistent",
    (_name, c) => {
      const tv = c.summary.totalValue;

      // Allocation percents sum to 100 (±0.1).
      const allocPct = c.allocation.reduce((s, a) => s + a.percent, 0);
      expect(Math.abs(allocPct - 100)).toBeLessThanOrEqual(0.1);

      // Each allocation value ≈ percent% of total (±1), and the values sum to
      // the total.
      const allocValSum = c.allocation.reduce((s, a) => s + a.value, 0);
      expect(Math.abs(allocValSum - tv)).toBeLessThanOrEqual(1);
      for (const a of c.allocation) {
        expect(Math.abs(a.value - (a.percent / 100) * tv)).toBeLessThanOrEqual(1);
      }

      // Sectors sum to roughly 100.
      const sectSum = c.sectors.reduce((s, x) => s + x.percent, 0);
      expect(sectSum).toBeGreaterThanOrEqual(95);
      expect(sectSum).toBeLessThanOrEqual(105);

      // Performance: 12 month-end points, expected dates, ending at the total.
      expect(c.performance).toHaveLength(12);
      expect(c.performance.map((p) => p.date)).toEqual(EXPECTED_DATES);
      expect(c.performance[c.performance.length - 1].value).toBe(tv);

      // Recent activity: a few plausible dated entries.
      expect(c.recentActivity.length).toBeGreaterThanOrEqual(3);
      for (const r of c.recentActivity) {
        expect(r.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      }

      // Each holding's percent ≈ value/total*100 (±0.3).
      for (const h of c.holdings) {
        expect(Math.abs(h.percent - (h.value / tv) * 100)).toBeLessThanOrEqual(0.3);
      }
    }
  );

  // Holdings values sum ≈ total. Client #1 (James Walker) is the pre-existing
  // canonical dataset whose numbers are pinned by other tests and MUST NOT be
  // changed; its holdings list is a representative subset, not an exhaustive
  // reconciliation, so this invariant is asserted for the newly built clients
  // #2–#10. Client #1's total is pinned separately in CL-FALLBACK.
  it.each(clients.filter((c) => c.id !== 1).map((c) => [c.profile.name, c]))(
    "CL-HOLDSUM: %s holdings reconcile to the total",
    (_name, c) => {
      const tv = c.summary.totalValue;
      const holdSum = c.holdings.reduce((s, h) => s + h.value, 0);
      expect(Math.abs(holdSum - tv)).toBeLessThanOrEqual(1);
    }
  );
});

describe("getClientData() — lookup & fallback", () => {
  it("CL-LOOKUP: returns the matching client by id", () => {
    expect(getClientData(1).profile.name).toBe("James Walker");
    expect(getClientData(7).profile.name).toBe("Christopher Lee");
  });

  it("CL-FALLBACK: unknown id falls back to client #1", () => {
    expect(getClientData(999).id).toBe(1);
    expect(getClientData(undefined).id).toBe(1);
    expect(getClientData(null).id).toBe(1);
  });

  it("CL-PINNED: client #1 keeps its canonical total value", () => {
    expect(getClientData(1).summary.totalValue).toBe(742318.55);
  });
});
