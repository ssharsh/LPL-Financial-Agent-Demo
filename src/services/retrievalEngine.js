// Context retrieval engine.
//
// This is the "grounding" layer: given a client's natural-language question, it
// finds the relevant slices of THEIR portfolio data and returns both a composed
// answer and the citations (which data points were used). The chat layer never
// invents numbers — it only renders what this engine retrieves.
//
// This is intentionally a plain, rule-based matcher so the demo runs fully on
// the frontend. It is the clean seam where a real retrieval/LLM backend (the
// `backend` branch) plugs in later: same input (question + portfolio), same
// output shape ({ answer, citations, data }).

import { getClientData } from "../data/mockPortfolio.js";
import {
  formatCurrency,
  formatPercent,
  formatSignedCurrency,
  formatDate,
} from "../utils/format.js";

// Questions that ask for a recommendation / opinion / prediction cross the
// compliance line. We detect them so the chat layer can decline safely.
const ADVICE_PATTERNS = [
  /\bshould i\b/,
  /\bwhat should\b/,
  /\bis .* a good (buy|investment|idea|time)\b/,
  /\brecommend|recommendation\b/,
  /\bwhat do you think\b/,
  /\bwill .* (go up|go down|rise|fall|crash|moon)\b/,
  /\bforecast|predict|prediction\b/,
  /\bbuy or sell\b/,
  /\b(should|shall) i (buy|sell|hold|invest)\b/,
  /\bbest (stock|investment|fund)\b/,
  /\bbeat the market\b/,
];

export function isAdviceQuestion(text) {
  const q = text.toLowerCase();
  return ADVICE_PATTERNS.some((re) => re.test(q));
}

// Each citation points at a labeled piece of the client's data so the UI can
// show "Based on: ...". `asOf` ties every answer to the data snapshot date; it
// is bound to the active client via the handler's `data` argument.
function cite(data, label, detail) {
  return { label, detail, asOf: data.profile.dataAsOf };
}

// --- Intent handlers -------------------------------------------------------
// Each takes the active client's full dataset and returns
// { answer: string, citations: [], data?: {...} } or null if it doesn't apply.
// The first matching handler wins.

function handleTotalValue(q, data) {
  if (!/(total|overall|net worth).*(value|worth)|what('?s| is) my (balance|total|portfolio worth)|how much is my portfolio|portfolio.*(value|worth)/.test(q))
    return null;
  const { summary } = data;
  const dir = summary.dayChangeValue >= 0 ? "up" : "down";
  return {
    answer:
      `Your portfolio is currently worth ${formatCurrency(summary.totalValue)}. ` +
      `That is ${dir} ${formatSignedCurrency(summary.dayChangeValue)} ` +
      `(${formatPercent(summary.dayChangePercent, { signed: true })}) today. ` +
      `Overall, your holdings are up ${formatSignedCurrency(summary.totalGainValue)} ` +
      `(${formatPercent(summary.totalGainPercent, { signed: true })}) since you invested.`,
    citations: [
      cite(data, "Total value", formatCurrency(summary.totalValue)),
      cite(data, "Today's change", `${formatSignedCurrency(summary.dayChangeValue)} (${formatPercent(summary.dayChangePercent, { signed: true })})`),
    ],
    data: { kind: "summary", summary },
  };
}

function handleAllocation(q, data) {
  if (!/(allocat|where.*(money|invested)|breakdown|asset class|diversif|mix|spread|split)/.test(q))
    return null;
  const { allocation } = data;
  const top = [...allocation].sort((a, b) => b.percent - a.percent).slice(0, 3);
  const topText = top
    .map((a) => `${a.name} (${formatPercent(a.percent)}, ${formatCurrency(a.value)})`)
    .join(", ");
  return {
    answer:
      `Your money is spread across ${allocation.length} asset classes. ` +
      `The largest are ${topText}. ` +
      `You can see the full breakdown in the chart on the right.`,
    citations: allocation.map((a) =>
      cite(data, a.name, `${formatPercent(a.percent)} · ${formatCurrency(a.value)}`)
    ),
    data: { kind: "allocation", allocation },
  };
}

function handleSectors(q, data) {
  if (!/(sector|industr|tech|technology|healthcare|energy|financ|which companies|what.*companies)/.test(q))
    return null;
  const { sectors } = data;
  const top = [...sectors].sort((a, b) => b.percent - a.percent).slice(0, 3);
  const topText = top.map((s) => `${s.name} (${formatPercent(s.percent)})`).join(", ");
  const largest = [...sectors].sort((a, b) => b.percent - a.percent)[0];
  return {
    answer:
      `Within your stock holdings, the biggest sector exposures are ${topText}. ` +
      `${largest.name} is your largest at ${formatPercent(largest.percent)}, driven by ` +
      `your fund and direct stock positions.`,
    citations: sectors.map((s) => cite(data, s.name, formatPercent(s.percent))),
    data: { kind: "sectors", sectors },
  };
}

function handleHoldings(q, data) {
  if (!/(holding|position|own|what.*(stocks|funds|etf)|invested in what|list.*(stocks|holdings))/.test(q))
    return null;
  const { holdings } = data;
  const top = [...holdings].sort((a, b) => b.percent - a.percent).slice(0, 3);
  const topText = top
    .map((h) => `${h.ticker} (${formatPercent(h.percent)}, ${formatCurrency(h.value)})`)
    .join(", ");
  return {
    answer:
      `You hold ${holdings.length} positions. Your three largest are ${topText}. ` +
      `The full list with values and gains is in the holdings table on the right.`,
    citations: holdings.map((h) =>
      cite(data, `${h.ticker} — ${h.name}`, `${formatPercent(h.percent)} · ${formatCurrency(h.value)}`)
    ),
    data: { kind: "holdings", holdings },
  };
}

function handlePerformance(q, data) {
  if (!/(perform|return|gain|loss|how.*(did|doing)|growth|over time|past (year|month)|history|change.*(year|month))/.test(q))
    return null;
  const { performance } = data;
  const first = performance[0];
  const last = performance[performance.length - 1];
  const change = last.value - first.value;
  const changePct = (change / first.value) * 100;
  return {
    answer:
      `Over the past 12 months your portfolio went from ${formatCurrency(first.value)} ` +
      `(${formatDate(first.date)}) to ${formatCurrency(last.value)} (${formatDate(last.date)}), ` +
      `a change of ${formatSignedCurrency(change)} (${formatPercent(changePct, { signed: true })}). ` +
      `The performance chart on the right shows the month-by-month path.`,
    citations: [
      cite(data, "12 months ago", `${formatCurrency(first.value)} (${formatDate(first.date)})`),
      cite(data, "Now", `${formatCurrency(last.value)} (${formatDate(last.date)})`),
      cite(data, "12-month change", `${formatSignedCurrency(change)} (${formatPercent(changePct, { signed: true })})`),
    ],
    data: { kind: "performance", performance },
  };
}

function handleActivity(q, data) {
  if (!/(recent|activity|transaction|dividend|deposit|what.*(happened|changed)|last (buy|sell|trade))/.test(q))
    return null;
  const { recentActivity } = data;
  const lines = recentActivity
    .map((a) => `${formatDate(a.date)}: ${a.description} (${formatSignedCurrency(a.amount)})`)
    .join("; ");
  return {
    answer: `Here is your recent account activity — ${lines}.`,
    citations: recentActivity.map((a) =>
      cite(data, `${a.type} · ${formatDate(a.date)}`, `${a.description} (${formatSignedCurrency(a.amount)})`)
    ),
    data: { kind: "activity", recentActivity },
  };
}

function handleCash(q, data) {
  if (!/(cash|available|buying power|liquid|how much.*(cash|available))/.test(q)) return null;
  const { summary } = data;
  return {
    answer:
      `You have ${formatCurrency(summary.cashAvailable)} in available cash and money market ` +
      `holdings, which is about ${formatPercent((summary.cashAvailable / summary.totalValue) * 100)} ` +
      `of your portfolio.`,
    citations: [cite(data, "Available cash", formatCurrency(summary.cashAvailable))],
    data: { kind: "summary", summary },
  };
}

// Order matters: specific handlers run before the broad total-value handler so
// questions like "how much do I have in tech / cash" aren't swallowed.
const HANDLERS = [
  handleCash,
  handleSectors,
  handleAllocation,
  handleHoldings,
  handlePerformance,
  handleActivity,
  handleTotalValue,
];

// Main entry point. Returns a grounded result or a graceful fallback.
// `clientId` selects which client's data to ground in; it defaults to client #1
// so existing single-argument callers (and their assertions) behave unchanged.
export function retrieve(question, clientId) {
  const q = (question || "").toLowerCase().trim();
  const data = getClientData(clientId);

  if (!q) {
    return {
      type: "empty",
      answer: "Ask me anything about your portfolio — where your money is, how it is allocated, or how it has performed.",
      citations: [],
    };
  }

  if (isAdviceQuestion(q)) {
    return {
      type: "advice_declined",
      answer:
        "I can explain what is in your portfolio and how it is invested, but I can't give " +
        "financial advice or recommendations. For guidance like this, please reach out to " +
        `your advisor, ${data.profile.advisorName} at ${data.profile.advisorFirm}.`,
      citations: [],
    };
  }

  for (const handler of HANDLERS) {
    const result = handler(q, data);
    if (result) {
      return { type: "grounded", ...result };
    }
  }

  // No handler matched: stay grounded, don't guess.
  return {
    type: "unknown",
    answer:
      "I couldn't find that in your portfolio data. Try asking about your total value, " +
      "asset allocation, sector exposure, individual holdings, performance over time, " +
      "recent activity, or available cash.",
    citations: [],
  };
}
