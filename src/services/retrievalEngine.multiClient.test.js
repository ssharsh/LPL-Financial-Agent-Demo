import { describe, it, expect } from "vitest";
import { retrieve } from "./retrievalEngine.js";
import { getClientData } from "../data/mockPortfolio.js";

// -----------------------------------------------------------------------------
// Multi-client grounding: retrieve(question, clientId) must ground answers in
// the SELECTED client's data, so different clients get different numbers.
// -----------------------------------------------------------------------------

function currency2(value) {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

describe("retrieve(question, clientId) — grounds in the selected client", () => {
  const ids = [2, 5, 7];

  it.each(ids)(
    "MC-TOTAL: total-value answer for client %s uses that client's total",
    (id) => {
      const r = retrieve("what is my total value", id);
      expect(r.type).toBe("grounded");
      expect(r.answer).toContain(currency2(getClientData(id).summary.totalValue));
    }
  );

  it("MC-DISTINCT: the three clients return different grounded totals", () => {
    const answers = ids.map((id) => retrieve("what is my total value", id).answer);
    // Each answer contains its own client's total.
    ids.forEach((id, i) => {
      expect(answers[i]).toContain(currency2(getClientData(id).summary.totalValue));
    });
    // No two of the selected clients' totals collide, and none equals #1's.
    const totals = ids.map((id) => getClientData(id).summary.totalValue);
    const withClient1 = [getClientData(1).summary.totalValue, ...totals];
    expect(new Set(withClient1).size).toBe(withClient1.length);
    // And the client #1 total string does NOT appear in the other clients'
    // answers (proves we are not falling back to #1).
    const client1Total = currency2(getClientData(1).summary.totalValue);
    for (const a of answers) {
      expect(a).not.toContain(client1Total);
    }
  });

  it("MC-ALLOC: allocation citations match the selected client's allocation length", () => {
    const id = 5; // William Foster (5 asset classes, different from #1's 6)
    const r = retrieve("what is my allocation", id);
    expect(r.type).toBe("grounded");
    expect(r.citations).toHaveLength(getClientData(id).allocation.length);
  });

  it("MC-ADVICE: advice decline names the selected client's advisor", () => {
    const id = 3; // Robert Nguyen — advisor Priya Nair
    const advisor = getClientData(id).profile.advisorName;
    const firm = getClientData(id).profile.advisorFirm;
    const r = retrieve("should i buy more NVDA", id);
    expect(r.type).toBe("advice_declined");
    expect(r.answer).toContain(advisor);
    expect(r.answer).toContain(firm);
  });

  it("MC-DEFAULT: omitting clientId still grounds in client #1", () => {
    const r = retrieve("what is my total value");
    expect(r.type).toBe("grounded");
    expect(r.answer).toContain(currency2(getClientData(1).summary.totalValue));
  });
});
