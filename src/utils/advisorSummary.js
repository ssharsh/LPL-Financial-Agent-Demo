import { jsPDF } from "jspdf";
import {
  formatCurrency,
  formatDate,
  formatPercent,
  formatSignedCurrency,
  formatTime,
} from "./format.js";
import { humanizeKey } from "./chartSpec.js";
import { drawChart } from "./pdfCharts.js";

// Strip **bold** markdown and characters the built-in PDF font can't draw.
function clean(text) {
  return String(text ?? "")
    .replace(/\*\*/g, "")
    .replace(/[→]/g, "->")
    .replace(/[—–]/g, "-")
    .replace(/[^\x09\x0A\x0D\x20-\x7E\u00A0-\u00FF]/g, "");
}

// Build and download a PDF summary of the chat for the client's advisor:
// what they asked for advice on (the questions that triggered the
// "no investment advice" reply), what else they looked into, and the full transcript.
export function downloadAdvisorSummary(messages, client, portfolio = null) {
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  const margin = 50;
  const width = doc.internal.pageSize.getWidth() - margin * 2;
  const pageBottom = doc.internal.pageSize.getHeight() - margin;
  let y = margin;

  const write = (text, { size = 10, bold = false, color = [40, 40, 40], gap = 4 } = {}) => {
    doc.setFont("helvetica", bold ? "bold" : "normal");
    doc.setFontSize(size);
    doc.setTextColor(...color);
    for (const line of doc.splitTextToSize(clean(text), width)) {
      if (y + size > pageBottom) {
        doc.addPage();
        y = margin;
      }
      doc.text(line, margin, y);
      y += size + 3;
    }
    y += gap;
  };

  const now = new Date().toISOString();
  const questions = messages.filter((m) => m.role === "user");
  // The user question right before each declined answer is what triggered it.
  const adviceRequests = [];
  messages.forEach((m, i) => {
    if (m.role === "assistant" && m.type === "advice_declined") {
      const q = [...messages.slice(0, i)].reverse().find((p) => p.role === "user");
      adviceRequests.push({ question: q?.text ?? "", topic: m.declinedReason, at: m.createdAt });
    }
  });
  const otherQuestions = questions.filter((q) => !adviceRequests.some((a) => a.question === q.text));

  write("Advisor Meeting Request - Conversation Summary", { size: 16, bold: true, color: [0, 94, 64] });
  write(`Client: ${client.name}`, { gap: 0 });
  if (client.accountNumber) write(client.accountNumber, { gap: 0 });
  write(`Advisor: ${client.advisorName}, ${client.advisorFirm}`, { gap: 0 });
  write(`Portfolio data as of: ${formatDate(client.dataAsOf)}`, { gap: 0 });
  write(`Requested: ${formatDate(now)} ${formatTime(now)}`, { gap: 12 });

  // Draw a chart, starting a new page first if it won't fit.
  const chart = (spec, title) => {
    if (y + 200 > pageBottom) {
      doc.addPage();
      y = margin;
    }
    if (title) write(title, { size: 9, bold: true, color: [90, 90, 90], gap: 2 });
    const used = drawChart(doc, spec, margin, y, width, 170);
    y += used + 10;
  };

  // Small portfolio summary (same data as the Portfolio panel).
  const portfolioSection = () => {
    if (!portfolio) return;
    write("Portfolio summary", { size: 12, bold: true });
    const t = portfolio.totals ?? {};
    write(
      `Total value: ${formatCurrency(Number(t.total_value))}   |   Cash: ${formatCurrency(Number(t.cash_balance))}` +
        `   |   Accounts: ${t.account_count ?? (portfolio.accounts ?? []).length}`,
      { gap: 2 }
    );
    (portfolio.accounts ?? []).forEach((a) =>
      write(`- ${a.account_name || a.account_id} (${humanizeKey(a.account_type)}): ${formatCurrency(Number(a.total_value))}`, {
        size: 9,
        gap: 0,
      })
    );
    const p = portfolio.performance;
    if (p) {
      y += 4;
      write(
        `Since ${formatDate(p.start_month)}: ${formatCurrency(Number(p.start_value))} -> ${formatCurrency(Number(p.end_value))}, ` +
          `net deposits/withdrawals ${formatSignedCurrency(Number(p.net_flows))}, investment gain ${formatSignedCurrency(Number(p.investment_gain))}` +
          (p.time_weighted_return_pct != null
            ? `, ${formatPercent(Number(p.time_weighted_return_pct), { signed: true })} ${p.return_label}`
            : ""),
        { size: 9, gap: 4 }
      );
    }
    const holdings = portfolio.holdings ?? [];
    if (holdings.length) {
      write("Top holdings", { size: 9, bold: true, gap: 0 });
      holdings.slice(0, 8).forEach((h) =>
        write(
          `- ${h.ticker} (${h.name}): ${formatCurrency(Number(h.market_value))}` +
            (h.weight_pct != null ? `, ${formatPercent(Number(h.weight_pct))} of portfolio` : ""),
          { size: 9, gap: 0 }
        )
      );
      y += 6;
    }
    if (portfolio.charts?.allocation) chart(portfolio.charts.allocation, "Asset allocation");
    if (portfolio.charts?.performance) chart(portfolio.charts.performance, "Value over time");
    y += 4;
  };

  write("Why the client wants to meet", { size: 12, bold: true });
  write(
    "The client asked for investment advice, which the portfolio assistant does not provide. " +
      "They would like to discuss the following with you:",
    { gap: 6 }
  );
  adviceRequests.forEach((a, i) => {
    write(`${i + 1}. "${a.question}"`, { bold: true, gap: 0 });
    if (a.topic) write(`   Topic: ${a.topic}`, { color: [90, 90, 90], gap: 6 });
  });
  y += 6;

  write("Other things the client looked into", { size: 12, bold: true });
  if (otherQuestions.length === 0) write("(None)");
  otherQuestions.forEach((q) => write(`- ${q.text}`, { gap: 2 }));
  y += 10;

  portfolioSection();

  // Every chart the assistant produced in this conversation, with the question behind it.
  const charted = messages
    .map((m, i) => ({ m, q: [...messages.slice(0, i)].reverse().find((p) => p.role === "user") }))
    .filter(({ m }) => m.role === "assistant" && m.chart);
  if (charted.length) {
    write("Charts from this conversation", { size: 12, bold: true });
    charted.forEach(({ m, q }) => chart(m.chart, `"${q?.text ?? ""}" (${formatTime(m.createdAt)})`));
    y += 4;
  }

  write("Full conversation", { size: 12, bold: true });
  messages.forEach((m) => {
    const who = m.role === "user" ? "Client" : "Assistant";
    write(`[${formatTime(m.createdAt)}] ${who}${m.type === "advice_declined" ? " (advice declined)" : ""}`, {
      bold: true,
      size: 9,
      color: m.role === "user" ? [40, 40, 40] : [0, 94, 64],
      gap: 0,
    });
    write(m.text, { size: 9, gap: 8 });
  });

  const safeName = String(client.name || "client").replace(/[^a-z0-9]+/gi, "-");
  doc.save(`advisor-meeting-${safeName}-${now.slice(0, 10)}.pdf`);
}
