// Mock portfolio data for a single LPL client.
// This is the ONLY source of truth the retrieval engine reads from, so every
// grounded answer traces back to numbers defined here (no fabricated figures).
//
// When the real backend (see the `backend` branch) is ready, this module is
// replaced by a fetch to the client's actual account data; the shape should
// stay the same so the retrieval engine and UI keep working.

export const client = {
  name: "Jordan Avery",
  accountNumber: "LPL-••••-4821",
  accountType: "Individual Brokerage",
  advisorName: "Dana Whitfield, CFP®",
  advisorFirm: "LPL Financial",
  dataAsOf: "2026-10-01T20:00:00.000Z",
};

// Current total value and day change.
export const summary = {
  totalValue: 742318.55,
  dayChangeValue: 3184.22,
  dayChangePercent: 0.43,
  totalGainValue: 128740.1,
  totalGainPercent: 20.98,
  cashAvailable: 18420.33,
};

// Allocation by asset class. Percentages sum to 100.
export const allocation = [
  { name: "US Stocks", percent: 48.5, value: 360024.5, color: "#0b5c3f" },
  { name: "International Stocks", percent: 16.0, value: 118770.97, color: "#13a06b" },
  { name: "Bonds", percent: 22.0, value: 163310.08, color: "#2f8fd6" },
  { name: "Real Estate (REITs)", percent: 6.0, value: 44539.11, color: "#c98a1b" },
  { name: "Cash", percent: 2.5, value: 18557.96, color: "#9aa5b1" },
  { name: "Alternatives", percent: 5.0, value: 37115.93, color: "#7b61a6" },
];

// Sector exposure within the stock portion (for "where is my money / why tech" type questions).
export const sectors = [
  { name: "Technology", percent: 28.4 },
  { name: "Healthcare", percent: 14.1 },
  { name: "Financials", percent: 12.7 },
  { name: "Consumer Discretionary", percent: 10.3 },
  { name: "Industrials", percent: 9.6 },
  { name: "Energy", percent: 6.8 },
  { name: "Utilities", percent: 5.2 },
  { name: "Other", percent: 12.9 },
];

// Individual holdings. gainPercent is lifetime for the position.
export const holdings = [
  { ticker: "VTI", name: "Vanguard Total Stock Market ETF", assetClass: "US Stocks", value: 196430.2, percent: 26.5, gainPercent: 24.1, shares: 712.4 },
  { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 118770.97, percent: 16.0, gainPercent: 9.8, shares: 1890.2 },
  { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 163310.08, percent: 22.0, gainPercent: 2.3, shares: 2284.1 },
  { ticker: "AAPL", name: "Apple Inc.", assetClass: "US Stocks", value: 71240.0, percent: 9.6, gainPercent: 41.7, shares: 320 },
  { ticker: "MSFT", name: "Microsoft Corp.", assetClass: "US Stocks", value: 58910.3, percent: 7.9, gainPercent: 38.2, shares: 128 },
  { ticker: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Real Estate (REITs)", value: 44539.11, percent: 6.0, gainPercent: 5.1, shares: 486.7 },
  { ticker: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", value: 37115.93, percent: 5.0, gainPercent: 12.6, shares: 162.3 },
  { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 18557.96, percent: 2.5, gainPercent: 0.0, shares: null },
];

// Portfolio value over the trailing 12 months (month-end snapshots).
export const performance = [
  { date: "2025-10-31", value: 648200 },
  { date: "2025-11-30", value: 655900 },
  { date: "2025-12-31", value: 639400 },
  { date: "2026-01-31", value: 668100 },
  { date: "2026-02-28", value: 681750 },
  { date: "2026-03-31", value: 672300 },
  { date: "2026-04-30", value: 695400 },
  { date: "2026-05-31", value: 702900 },
  { date: "2026-06-30", value: 689200 },
  { date: "2026-07-31", value: 715600 },
  { date: "2026-08-31", value: 728300 },
  { date: "2026-09-30", value: 742318.55 },
];

// Recent activity, for "what changed" type questions.
export const recentActivity = [
  { date: "2026-09-18", type: "Dividend", description: "VTI quarterly dividend", amount: 842.17 },
  { date: "2026-09-05", type: "Buy", description: "Purchased 12 shares of MSFT", amount: -5160.0 },
  { date: "2026-08-22", type: "Dividend", description: "BND monthly distribution", amount: 410.55 },
  { date: "2026-08-01", type: "Deposit", description: "ACH contribution", amount: 5000.0 },
];
