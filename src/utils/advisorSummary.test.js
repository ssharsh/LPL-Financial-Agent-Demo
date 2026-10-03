import { vi } from "vitest";

const saved = [];
vi.mock("jspdf", async () => {
  const real = await vi.importActual("jspdf");
  function SpyPDF(opts) {
    const doc = new real.jsPDF(opts);
    doc.save = (name) => saved.push({ name, text: doc.output() });
    return doc;
  }
  return { jsPDF: SpyPDF };
});

import { downloadAdvisorSummary } from "./advisorSummary.js";

test("builds an advisor meeting PDF with the advice question and transcript", () => {
  const t = "2026-10-02T15:00:00.000Z";
  const messages = [
    { id: "1", role: "user", text: "What is my total value?", createdAt: t },
    { id: "2", role: "assistant", type: "grounded", text: "Your total is **$89,163.45**.", createdAt: t },
    { id: "3", role: "user", text: "Should I sell BND and buy VOO?", createdAt: t },
    {
      id: "4",
      role: "assistant",
      type: "advice_declined",
      declinedReason: "Whether to sell BND and buy VOO.",
      text: "I can't advise on that — your advisor can help.",
      createdAt: t,
    },
  ];
  const client = { name: "James Walker", accountNumber: "Accounts 1, 2", advisorName: "Sarah Chen", advisorFirm: "LPL Financial", dataAsOf: "2026-10-31" };
  downloadAdvisorSummary(messages, client);
  expect(saved).toHaveLength(1);
  expect(saved[0].name).toMatch(/^advisor-meeting-James-Walker-.*\.pdf$/);
  const pdf = saved[0].text;
  expect(pdf.startsWith("%PDF")).toBe(true);
  expect(pdf).toContain("Should I sell BND and buy VOO?");
  expect(pdf).toContain("Whether to sell BND and buy VOO.");
  expect(pdf).toContain("What is my total value?");
  expect(pdf).toContain("Sarah Chen");
});
