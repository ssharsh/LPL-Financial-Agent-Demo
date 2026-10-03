// Mock portfolio data for the LPL demo.
//
// This module is the ONLY source of truth the retrieval engine and UI read
// from, so every grounded answer traces back to numbers defined here (no
// fabricated figures). It now holds a FULL, DISTINCT portfolio for each of the
// 10 roster clients. Selecting a client in the top-right dropdown switches the
// whole app (portfolio panel, charts, headline totals) and the chatbot's
// grounded answers to that client's data.
//
// When the real backend (see the `backend` branch) is ready, this module is
// replaced by a fetch to each client's actual account data; the shape should
// stay the same so the retrieval engine and UI keep working.
//
// Shared asset-class color convention (reused by every client's allocation):
//   US Stocks            #0b5c3f
//   International Stocks  #13a06b
//   Bonds                #2f8fd6
//   Real Estate (REITs)  #c98a1b
//   Cash                 #9aa5b1
//   Alternatives         #7b61a6

const COLORS = {
  "US Stocks": "#0b5c3f",
  "International Stocks": "#13a06b",
  Bonds: "#2f8fd6",
  "Real Estate (REITs)": "#c98a1b",
  Cash: "#9aa5b1",
  Alternatives: "#7b61a6",
};

// Advisor's client roster shown in the top-right client selector. Each entry
// has a masked account number for display. The full per-client datasets live
// in `clients` below and are keyed by the same ids.
export const clientRoster = [
  { id: 1, name: "James Walker", accountNumber: "LPL-••••-1007" },
  { id: 2, name: "Linda Martinez", accountNumber: "LPL-••••-2043" },
  { id: 3, name: "Robert Nguyen", accountNumber: "LPL-••••-3119" },
  { id: 4, name: "Jennifer Brooks", accountNumber: "LPL-••••-4821" },
  { id: 5, name: "William Foster", accountNumber: "LPL-••••-5277" },
  { id: 6, name: "Maria Garcia", accountNumber: "LPL-••••-6388" },
  { id: 7, name: "Christopher Lee", accountNumber: "LPL-••••-7450" },
  { id: 8, name: "Ashley Davis", accountNumber: "LPL-••••-8512" },
  { id: 9, name: "Daniel Kim", accountNumber: "LPL-••••-9634" },
  { id: 10, name: "Patricia Sullivan", accountNumber: "LPL-••••-1075" },
];

// -----------------------------------------------------------------------------
// Client 1 — James Walker — balanced growth. CURRENT dataset verbatim.
// Numbers are pinned by existing retrievalEngine tests (total $742,318.55,
// cash $18,420.33, 6 allocation rows, 8 holdings), so they MUST NOT change.
// -----------------------------------------------------------------------------
const client1 = {
  id: 1,
  profile: {
    name: "James Walker",
    accountNumber: "LPL-••••-1007",
    accountType: "Individual Brokerage",
    advisorName: "Dana Whitfield, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 742318.55,
    dayChangeValue: 3184.22,
    dayChangePercent: 0.43,
    totalGainValue: 128740.1,
    totalGainPercent: 20.98,
    cashAvailable: 18420.33,
  },
  allocation: [
    { name: "US Stocks", percent: 48.5, value: 360024.5, color: COLORS["US Stocks"] },
    { name: "International Stocks", percent: 16.0, value: 118770.97, color: COLORS["International Stocks"] },
    { name: "Bonds", percent: 22.0, value: 163310.08, color: COLORS["Bonds"] },
    { name: "Real Estate (REITs)", percent: 6.0, value: 44539.11, color: COLORS["Real Estate (REITs)"] },
    { name: "Cash", percent: 2.5, value: 18557.96, color: COLORS["Cash"] },
    { name: "Alternatives", percent: 5.0, value: 37115.93, color: COLORS["Alternatives"] },
  ],
  sectors: [
    { name: "Technology", percent: 28.4 },
    { name: "Healthcare", percent: 14.1 },
    { name: "Financials", percent: 12.7 },
    { name: "Consumer Discretionary", percent: 10.3 },
    { name: "Industrials", percent: 9.6 },
    { name: "Energy", percent: 6.8 },
    { name: "Utilities", percent: 5.2 },
    { name: "Other", percent: 12.9 },
  ],
  holdings: [
    { ticker: "VTI", name: "Vanguard Total Stock Market ETF", assetClass: "US Stocks", value: 196430.2, percent: 26.5, gainPercent: 24.1, shares: 712.4 },
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 118770.97, percent: 16.0, gainPercent: 9.8, shares: 1890.2 },
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 163310.08, percent: 22.0, gainPercent: 2.3, shares: 2284.1 },
    { ticker: "AAPL", name: "Apple Inc.", assetClass: "US Stocks", value: 71240.0, percent: 9.6, gainPercent: 41.7, shares: 320 },
    { ticker: "MSFT", name: "Microsoft Corp.", assetClass: "US Stocks", value: 58910.3, percent: 7.9, gainPercent: 38.2, shares: 128 },
    { ticker: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Real Estate (REITs)", value: 44539.11, percent: 6.0, gainPercent: 5.1, shares: 486.7 },
    { ticker: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", value: 37115.93, percent: 5.0, gainPercent: 12.6, shares: 162.3 },
    { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 18557.96, percent: 2.5, gainPercent: 0.0, shares: null },
  ],
  performance: [
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
  ],
  recentActivity: [
    { date: "2026-09-18", type: "Dividend", description: "VTI quarterly dividend", amount: 842.17 },
    { date: "2026-09-05", type: "Buy", description: "Purchased 12 shares of MSFT", amount: -5160.0 },
    { date: "2026-08-22", type: "Dividend", description: "BND monthly distribution", amount: 410.55 },
    { date: "2026-08-01", type: "Deposit", description: "ACH contribution", amount: 5000.0 },
  ],
};

// -----------------------------------------------------------------------------
// Client 2 — Linda Martinez — large balanced, dividend tilt. Total $1,284,500.
// -----------------------------------------------------------------------------
const client2 = {
  id: 2,
  profile: {
    name: "Linda Martinez",
    accountNumber: "LPL-••••-2043",
    accountType: "Joint Brokerage",
    advisorName: "Marcus Reed, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 1284500.0,
    dayChangeValue: -2156.4,
    dayChangePercent: -0.17,
    totalGainValue: 243870.0,
    totalGainPercent: 23.44,
    cashAvailable: 51380.0,
  },
  allocation: [
    { name: "US Stocks", percent: 52.0, value: 667940.0, color: COLORS["US Stocks"] },
    { name: "International Stocks", percent: 12.0, value: 154140.0, color: COLORS["International Stocks"] },
    { name: "Bonds", percent: 26.0, value: 333970.0, color: COLORS["Bonds"] },
    { name: "Real Estate (REITs)", percent: 4.0, value: 51380.0, color: COLORS["Real Estate (REITs)"] },
    { name: "Cash", percent: 4.0, value: 51380.0, color: COLORS["Cash"] },
    { name: "Alternatives", percent: 2.0, value: 25690.0, color: COLORS["Alternatives"] },
  ],
  sectors: [
    { name: "Technology", percent: 19.5 },
    { name: "Financials", percent: 18.2 },
    { name: "Healthcare", percent: 15.4 },
    { name: "Consumer Staples", percent: 12.1 },
    { name: "Industrials", percent: 10.3 },
    { name: "Energy", percent: 7.5 },
    { name: "Utilities", percent: 6.8 },
    { name: "Other", percent: 10.2 },
  ],
  holdings: [
    { ticker: "SCHD", name: "Schwab US Dividend Equity ETF", assetClass: "US Stocks", value: 282590.0, percent: 22.0, gainPercent: 18.4, shares: 3454.6 },
    { ticker: "VIG", name: "Vanguard Dividend Appreciation ETF", assetClass: "US Stocks", value: 179830.0, percent: 14.0, gainPercent: 21.7, shares: 938.5 },
    { ticker: "VTI", name: "Vanguard Total Stock Market ETF", assetClass: "US Stocks", value: 115605.0, percent: 9.0, gainPercent: 25.3, shares: 419.2 },
    { ticker: "JPM", name: "JPMorgan Chase & Co.", assetClass: "US Stocks", value: 89915.0, percent: 7.0, gainPercent: 34.9, shares: 380.3 },
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 333970.0, percent: 26.0, gainPercent: 3.1, shares: 4671.8 },
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 154140.0, percent: 12.0, gainPercent: 11.2, shares: 2452.8 },
    { ticker: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Real Estate (REITs)", value: 51380.0, percent: 4.0, gainPercent: 6.4, shares: 561.4 },
    { ticker: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", value: 25690.0, percent: 2.0, gainPercent: 9.8, shares: 112.3 },
    { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 51380.0, percent: 4.0, gainPercent: 0.0, shares: null },
  ],
  performance: [
    { date: "2025-10-31", value: 1148000 },
    { date: "2025-11-30", value: 1172500 },
    { date: "2025-12-31", value: 1160300 },
    { date: "2026-01-31", value: 1195600 },
    { date: "2026-02-28", value: 1213400 },
    { date: "2026-03-31", value: 1201800 },
    { date: "2026-04-30", value: 1238900 },
    { date: "2026-05-31", value: 1256700 },
    { date: "2026-06-30", value: 1242300 },
    { date: "2026-07-31", value: 1271500 },
    { date: "2026-08-31", value: 1293200 },
    { date: "2026-09-30", value: 1284500.0 },
  ],
  recentActivity: [
    { date: "2026-09-20", type: "Dividend", description: "SCHD quarterly dividend", amount: 2140.5 },
    { date: "2026-09-10", type: "Buy", description: "Purchased 40 shares of JPM", amount: -9460.0 },
    { date: "2026-08-15", type: "Dividend", description: "VIG quarterly dividend", amount: 1180.25 },
    { date: "2026-08-02", type: "Deposit", description: "ACH contribution", amount: 10000.0 },
  ],
};

// -----------------------------------------------------------------------------
// Client 3 — Robert Nguyen — aggressive tech growth. Total $318,900.
// -----------------------------------------------------------------------------
const client3 = {
  id: 3,
  profile: {
    name: "Robert Nguyen",
    accountNumber: "LPL-••••-3119",
    accountType: "Individual Brokerage",
    advisorName: "Priya Nair, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 318900.0,
    dayChangeValue: 4821.9,
    dayChangePercent: 1.53,
    totalGainValue: 94310.0,
    totalGainPercent: 41.99,
    cashAvailable: 6378.0,
  },
  allocation: [
    { name: "US Stocks", percent: 78.0, value: 248742.0, color: COLORS["US Stocks"] },
    { name: "International Stocks", percent: 8.0, value: 25512.0, color: COLORS["International Stocks"] },
    { name: "Bonds", percent: 6.0, value: 19134.0, color: COLORS["Bonds"] },
    { name: "Alternatives", percent: 6.0, value: 19134.0, color: COLORS["Alternatives"] },
    { name: "Cash", percent: 2.0, value: 6378.0, color: COLORS["Cash"] },
  ],
  sectors: [
    { name: "Technology", percent: 58.7 },
    { name: "Consumer Discretionary", percent: 14.2 },
    { name: "Communication Services", percent: 10.6 },
    { name: "Healthcare", percent: 5.3 },
    { name: "Financials", percent: 4.1 },
    { name: "Industrials", percent: 3.2 },
    { name: "Other", percent: 3.9 },
  ],
  holdings: [
    { ticker: "NVDA", name: "NVIDIA Corp.", assetClass: "US Stocks", value: 95670.0, percent: 30.0, gainPercent: 112.4, shares: 540.0 },
    { ticker: "AAPL", name: "Apple Inc.", assetClass: "US Stocks", value: 57402.0, percent: 18.0, gainPercent: 46.1, shares: 257.8 },
    { ticker: "MSFT", name: "Microsoft Corp.", assetClass: "US Stocks", value: 47835.0, percent: 15.0, gainPercent: 39.5, shares: 104.0 },
    { ticker: "GOOGL", name: "Alphabet Inc. Class A", assetClass: "US Stocks", value: 28701.0, percent: 9.0, gainPercent: 33.8, shares: 162.4 },
    { ticker: "AMZN", name: "Amazon.com Inc.", assetClass: "US Stocks", value: 19134.0, percent: 6.0, gainPercent: 27.6, shares: 101.2 },
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 25512.0, percent: 8.0, gainPercent: 10.1, shares: 406.0 },
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 19134.0, percent: 6.0, gainPercent: 1.9, shares: 267.6 },
    { ticker: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", value: 19134.0, percent: 6.0, gainPercent: 8.3, shares: 83.6 },
    { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 6378.0, percent: 2.0, gainPercent: 0.0, shares: null },
  ],
  performance: [
    { date: "2025-10-31", value: 236400 },
    { date: "2025-11-30", value: 251800 },
    { date: "2025-12-31", value: 243100 },
    { date: "2026-01-31", value: 268900 },
    { date: "2026-02-28", value: 289400 },
    { date: "2026-03-31", value: 271200 },
    { date: "2026-04-30", value: 294600 },
    { date: "2026-05-31", value: 312800 },
    { date: "2026-06-30", value: 298100 },
    { date: "2026-07-31", value: 321500 },
    { date: "2026-08-31", value: 334900 },
    { date: "2026-09-30", value: 318900.0 },
  ],
  recentActivity: [
    { date: "2026-09-22", type: "Buy", description: "Purchased 20 shares of NVDA", amount: -3540.0 },
    { date: "2026-09-08", type: "Sell", description: "Sold 10 shares of AMZN", amount: 1890.0 },
    { date: "2026-08-19", type: "Buy", description: "Purchased 15 shares of GOOGL", amount: -2650.0 },
  ],
};

// -----------------------------------------------------------------------------
// Client 4 — Jennifer Brooks — high-net-worth diversified. Total $2,450,000.
// -----------------------------------------------------------------------------
const client4 = {
  id: 4,
  profile: {
    name: "Jennifer Brooks",
    accountNumber: "LPL-••••-4821",
    accountType: "Trust",
    advisorName: "Dana Whitfield, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 2450000.0,
    dayChangeValue: 8575.0,
    dayChangePercent: 0.35,
    totalGainValue: 512300.0,
    totalGainPercent: 26.43,
    cashAvailable: 73500.0,
  },
  allocation: [
    { name: "US Stocks", percent: 42.0, value: 1029000.0, color: COLORS["US Stocks"] },
    { name: "International Stocks", percent: 18.0, value: 441000.0, color: COLORS["International Stocks"] },
    { name: "Bonds", percent: 24.0, value: 588000.0, color: COLORS["Bonds"] },
    { name: "Real Estate (REITs)", percent: 7.0, value: 171500.0, color: COLORS["Real Estate (REITs)"] },
    { name: "Alternatives", percent: 6.0, value: 147000.0, color: COLORS["Alternatives"] },
    { name: "Cash", percent: 3.0, value: 73500.0, color: COLORS["Cash"] },
  ],
  sectors: [
    { name: "Technology", percent: 22.6 },
    { name: "Financials", percent: 15.8 },
    { name: "Healthcare", percent: 14.3 },
    { name: "Industrials", percent: 11.2 },
    { name: "Consumer Discretionary", percent: 9.7 },
    { name: "Energy", percent: 7.1 },
    { name: "Utilities", percent: 5.4 },
    { name: "Other", percent: 13.9 },
  ],
  holdings: [
    { ticker: "VTI", name: "Vanguard Total Stock Market ETF", assetClass: "US Stocks", value: 686000.0, percent: 28.0, gainPercent: 23.9, shares: 2487.0 },
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 441000.0, percent: 18.0, gainPercent: 10.4, shares: 7016.0 },
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 441000.0, percent: 18.0, gainPercent: 2.8, shares: 6168.0 },
    { ticker: "TLT", name: "iShares 20+ Year Treasury Bond ETF", assetClass: "Bonds", value: 147000.0, percent: 6.0, gainPercent: 1.2, shares: 1620.0 },
    { ticker: "AAPL", name: "Apple Inc.", assetClass: "US Stocks", value: 196000.0, percent: 8.0, gainPercent: 44.2, shares: 880.0 },
    { ticker: "MSFT", name: "Microsoft Corp.", assetClass: "US Stocks", value: 147000.0, percent: 6.0, gainPercent: 37.6, shares: 320.0 },
    { ticker: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Real Estate (REITs)", value: 171500.0, percent: 7.0, gainPercent: 5.7, shares: 1873.0 },
    { ticker: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", value: 147000.0, percent: 6.0, gainPercent: 11.3, shares: 642.0 },
    { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 73500.0, percent: 3.0, gainPercent: 0.0, shares: null },
  ],
  performance: [
    { date: "2025-10-31", value: 2198000 },
    { date: "2025-11-30", value: 2241000 },
    { date: "2025-12-31", value: 2213500 },
    { date: "2026-01-31", value: 2287400 },
    { date: "2026-02-28", value: 2321900 },
    { date: "2026-03-31", value: 2299600 },
    { date: "2026-04-30", value: 2358200 },
    { date: "2026-05-31", value: 2394700 },
    { date: "2026-06-30", value: 2367100 },
    { date: "2026-07-31", value: 2421800 },
    { date: "2026-08-31", value: 2463400 },
    { date: "2026-09-30", value: 2450000.0 },
  ],
  recentActivity: [
    { date: "2026-09-25", type: "Dividend", description: "VTI quarterly dividend", amount: 3120.4 },
    { date: "2026-09-12", type: "Buy", description: "Purchased 200 shares of VXUS", amount: -12560.0 },
    { date: "2026-08-28", type: "Dividend", description: "BND monthly distribution", amount: 1140.75 },
    { date: "2026-08-05", type: "Deposit", description: "Wire contribution", amount: 25000.0 },
  ],
};

// -----------------------------------------------------------------------------
// Client 5 — William Foster — conservative, bond-heavy near-retiree. $128,400.
// -----------------------------------------------------------------------------
const client5 = {
  id: 5,
  profile: {
    name: "William Foster",
    accountNumber: "LPL-••••-5277",
    accountType: "Traditional IRA",
    advisorName: "Marcus Reed, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 128400.0,
    dayChangeValue: 142.6,
    dayChangePercent: 0.11,
    totalGainValue: 14620.0,
    totalGainPercent: 12.85,
    cashAvailable: 19260.0,
  },
  allocation: [
    { name: "Bonds", percent: 56.0, value: 71904.0, color: COLORS["Bonds"] },
    { name: "US Stocks", percent: 20.0, value: 25680.0, color: COLORS["US Stocks"] },
    { name: "International Stocks", percent: 7.0, value: 8988.0, color: COLORS["International Stocks"] },
    { name: "Cash", percent: 15.0, value: 19260.0, color: COLORS["Cash"] },
    { name: "Real Estate (REITs)", percent: 2.0, value: 2568.0, color: COLORS["Real Estate (REITs)"] },
  ],
  sectors: [
    { name: "Financials", percent: 16.4 },
    { name: "Healthcare", percent: 15.1 },
    { name: "Utilities", percent: 13.8 },
    { name: "Consumer Staples", percent: 12.9 },
    { name: "Technology", percent: 11.2 },
    { name: "Industrials", percent: 9.6 },
    { name: "Energy", percent: 8.3 },
    { name: "Other", percent: 12.7 },
  ],
  holdings: [
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 51360.0, percent: 40.0, gainPercent: 2.6, shares: 718.9 },
    { ticker: "TLT", name: "iShares 20+ Year Treasury Bond ETF", assetClass: "Bonds", value: 20544.0, percent: 16.0, gainPercent: 1.4, shares: 226.4 },
    { ticker: "VTI", name: "Vanguard Total Stock Market ETF", assetClass: "US Stocks", value: 25680.0, percent: 20.0, gainPercent: 19.8, shares: 93.1 },
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 8988.0, percent: 7.0, gainPercent: 8.2, shares: 143.0 },
    { ticker: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Real Estate (REITs)", value: 2568.0, percent: 2.0, gainPercent: 4.3, shares: 28.1 },
    { ticker: "BIL", name: "SPDR Bloomberg 1-3 Month T-Bill ETF", assetClass: "Cash", value: 19260.0, percent: 15.0, gainPercent: 0.4, shares: 210.3 },
  ],
  performance: [
    { date: "2025-10-31", value: 121500 },
    { date: "2025-11-30", value: 122800 },
    { date: "2025-12-31", value: 121900 },
    { date: "2026-01-31", value: 123600 },
    { date: "2026-02-28", value: 124900 },
    { date: "2026-03-31", value: 124100 },
    { date: "2026-04-30", value: 125700 },
    { date: "2026-05-31", value: 126800 },
    { date: "2026-06-30", value: 125900 },
    { date: "2026-07-31", value: 127300 },
    { date: "2026-08-31", value: 128900 },
    { date: "2026-09-30", value: 128400.0 },
  ],
  recentActivity: [
    { date: "2026-09-16", type: "Dividend", description: "BND monthly distribution", amount: 168.4 },
    { date: "2026-09-01", type: "Interest", description: "BIL money market interest", amount: 62.1 },
    { date: "2026-08-20", type: "Buy", description: "Purchased 30 shares of BND", amount: -2144.0 },
  ],
};

// -----------------------------------------------------------------------------
// Client 6 — Maria Garcia — international-tilt. Total $565,200.
// -----------------------------------------------------------------------------
const client6 = {
  id: 6,
  profile: {
    name: "Maria Garcia",
    accountNumber: "LPL-••••-6388",
    accountType: "Individual Brokerage",
    advisorName: "Priya Nair, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 565200.0,
    dayChangeValue: 1356.5,
    dayChangePercent: 0.24,
    totalGainValue: 78340.0,
    totalGainPercent: 16.08,
    cashAvailable: 16956.0,
  },
  allocation: [
    { name: "International Stocks", percent: 46.0, value: 259992.0, color: COLORS["International Stocks"] },
    { name: "US Stocks", percent: 30.0, value: 169560.0, color: COLORS["US Stocks"] },
    { name: "Bonds", percent: 15.0, value: 84780.0, color: COLORS["Bonds"] },
    { name: "Real Estate (REITs)", percent: 6.0, value: 33912.0, color: COLORS["Real Estate (REITs)"] },
    { name: "Cash", percent: 3.0, value: 16956.0, color: COLORS["Cash"] },
  ],
  sectors: [
    { name: "Financials", percent: 20.1 },
    { name: "Technology", percent: 16.8 },
    { name: "Industrials", percent: 13.4 },
    { name: "Consumer Discretionary", percent: 11.9 },
    { name: "Materials", percent: 9.7 },
    { name: "Healthcare", percent: 8.6 },
    { name: "Energy", percent: 7.2 },
    { name: "Other", percent: 12.3 },
  ],
  holdings: [
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 169560.0, percent: 30.0, gainPercent: 12.1, shares: 2698.0 },
    { ticker: "VWO", name: "Vanguard FTSE Emerging Markets ETF", assetClass: "International Stocks", value: 90432.0, percent: 16.0, gainPercent: 14.9, shares: 1960.0 },
    { ticker: "VTI", name: "Vanguard Total Stock Market ETF", assetClass: "US Stocks", value: 169560.0, percent: 30.0, gainPercent: 22.4, shares: 614.8 },
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 84780.0, percent: 15.0, gainPercent: 2.4, shares: 1186.1 },
    { ticker: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Real Estate (REITs)", value: 33912.0, percent: 6.0, gainPercent: 5.9, shares: 370.6 },
    { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 16956.0, percent: 3.0, gainPercent: 0.0, shares: null },
  ],
  performance: [
    { date: "2025-10-31", value: 503600 },
    { date: "2025-11-30", value: 511200 },
    { date: "2025-12-31", value: 506800 },
    { date: "2026-01-31", value: 519400 },
    { date: "2026-02-28", value: 528900 },
    { date: "2026-03-31", value: 522300 },
    { date: "2026-04-30", value: 537100 },
    { date: "2026-05-31", value: 548600 },
    { date: "2026-06-30", value: 541200 },
    { date: "2026-07-31", value: 553800 },
    { date: "2026-08-31", value: 569400 },
    { date: "2026-09-30", value: 565200.0 },
  ],
  recentActivity: [
    { date: "2026-09-19", type: "Dividend", description: "VXUS quarterly dividend", amount: 1024.3 },
    { date: "2026-09-07", type: "Buy", description: "Purchased 100 shares of VWO", amount: -4620.0 },
    { date: "2026-08-14", type: "Dividend", description: "VWO quarterly dividend", amount: 512.8 },
  ],
};

// -----------------------------------------------------------------------------
// Client 7 — Christopher Lee — large aggressive equity. Total $3,480,000.
// -----------------------------------------------------------------------------
const client7 = {
  id: 7,
  profile: {
    name: "Christopher Lee",
    accountNumber: "LPL-••••-7450",
    accountType: "Individual Brokerage",
    advisorName: "Dana Whitfield, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 3480000.0,
    dayChangeValue: 24360.0,
    dayChangePercent: 0.7,
    totalGainValue: 1118400.0,
    totalGainPercent: 47.36,
    cashAvailable: 34800.0,
  },
  allocation: [
    { name: "US Stocks", percent: 74.0, value: 2575200.0, color: COLORS["US Stocks"] },
    { name: "International Stocks", percent: 12.0, value: 417600.0, color: COLORS["International Stocks"] },
    { name: "Bonds", percent: 6.0, value: 208800.0, color: COLORS["Bonds"] },
    { name: "Alternatives", percent: 4.0, value: 139200.0, color: COLORS["Alternatives"] },
    { name: "Real Estate (REITs)", percent: 3.0, value: 104400.0, color: COLORS["Real Estate (REITs)"] },
    { name: "Cash", percent: 1.0, value: 34800.0, color: COLORS["Cash"] },
  ],
  sectors: [
    { name: "Technology", percent: 46.3 },
    { name: "Communication Services", percent: 13.7 },
    { name: "Consumer Discretionary", percent: 12.4 },
    { name: "Healthcare", percent: 7.9 },
    { name: "Financials", percent: 6.8 },
    { name: "Industrials", percent: 5.1 },
    { name: "Other", percent: 7.8 },
  ],
  holdings: [
    { ticker: "VTI", name: "Vanguard Total Stock Market ETF", assetClass: "US Stocks", value: 870000.0, percent: 25.0, gainPercent: 26.8, shares: 3154.0 },
    { ticker: "AAPL", name: "Apple Inc.", assetClass: "US Stocks", value: 522000.0, percent: 15.0, gainPercent: 52.1, shares: 2342.0 },
    { ticker: "MSFT", name: "Microsoft Corp.", assetClass: "US Stocks", value: 452400.0, percent: 13.0, gainPercent: 44.9, shares: 984.0 },
    { ticker: "NVDA", name: "NVIDIA Corp.", assetClass: "US Stocks", value: 417600.0, percent: 12.0, gainPercent: 128.3, shares: 2358.0 },
    { ticker: "GOOGL", name: "Alphabet Inc. Class A", assetClass: "US Stocks", value: 174000.0, percent: 5.0, gainPercent: 35.4, shares: 984.0 },
    { ticker: "AMZN", name: "Amazon.com Inc.", assetClass: "US Stocks", value: 139200.0, percent: 4.0, gainPercent: 29.1, shares: 736.0 },
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 417600.0, percent: 12.0, gainPercent: 11.6, shares: 6646.0 },
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 208800.0, percent: 6.0, gainPercent: 2.1, shares: 2921.0 },
    { ticker: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", value: 139200.0, percent: 4.0, gainPercent: 10.7, shares: 608.0 },
    { ticker: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Real Estate (REITs)", value: 104400.0, percent: 3.0, gainPercent: 6.2, shares: 1141.0 },
    { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 34800.0, percent: 1.0, gainPercent: 0.0, shares: null },
  ],
  performance: [
    { date: "2025-10-31", value: 2984000 },
    { date: "2025-11-30", value: 3102000 },
    { date: "2025-12-31", value: 3041000 },
    { date: "2026-01-31", value: 3188000 },
    { date: "2026-02-28", value: 3296000 },
    { date: "2026-03-31", value: 3214000 },
    { date: "2026-04-30", value: 3352000 },
    { date: "2026-05-31", value: 3428000 },
    { date: "2026-06-30", value: 3361000 },
    { date: "2026-07-31", value: 3452000 },
    { date: "2026-08-31", value: 3524000 },
    { date: "2026-09-30", value: 3480000.0 },
  ],
  recentActivity: [
    { date: "2026-09-24", type: "Buy", description: "Purchased 50 shares of NVDA", amount: -8850.0 },
    { date: "2026-09-11", type: "Dividend", description: "VTI quarterly dividend", amount: 3960.2 },
    { date: "2026-08-27", type: "Sell", description: "Sold 20 shares of AAPL", amount: 4460.0 },
    { date: "2026-08-06", type: "Deposit", description: "Wire contribution", amount: 50000.0 },
  ],
};

// -----------------------------------------------------------------------------
// Client 8 — Ashley Davis — young growth, small cash. Total $214,750.
// -----------------------------------------------------------------------------
const client8 = {
  id: 8,
  profile: {
    name: "Ashley Davis",
    accountNumber: "LPL-••••-8512",
    accountType: "Roth IRA",
    advisorName: "Marcus Reed, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 214750.0,
    dayChangeValue: 2341.1,
    dayChangePercent: 1.1,
    totalGainValue: 48910.0,
    totalGainPercent: 29.49,
    cashAvailable: 4295.0,
  },
  allocation: [
    { name: "US Stocks", percent: 62.0, value: 133145.0, color: COLORS["US Stocks"] },
    { name: "International Stocks", percent: 24.0, value: 51540.0, color: COLORS["International Stocks"] },
    { name: "Bonds", percent: 10.0, value: 21475.0, color: COLORS["Bonds"] },
    { name: "Cash", percent: 2.0, value: 4295.0, color: COLORS["Cash"] },
    { name: "Alternatives", percent: 2.0, value: 4295.0, color: COLORS["Alternatives"] },
  ],
  sectors: [
    { name: "Technology", percent: 34.6 },
    { name: "Consumer Discretionary", percent: 15.2 },
    { name: "Financials", percent: 12.1 },
    { name: "Healthcare", percent: 10.8 },
    { name: "Communication Services", percent: 9.4 },
    { name: "Industrials", percent: 7.3 },
    { name: "Other", percent: 10.6 },
  ],
  holdings: [
    { ticker: "VTI", name: "Vanguard Total Stock Market ETF", assetClass: "US Stocks", value: 96637.5, percent: 45.0, gainPercent: 27.3, shares: 350.4 },
    { ticker: "NVDA", name: "NVIDIA Corp.", assetClass: "US Stocks", value: 21475.0, percent: 10.0, gainPercent: 98.7, shares: 121.2 },
    { ticker: "AAPL", name: "Apple Inc.", assetClass: "US Stocks", value: 15032.5, percent: 7.0, gainPercent: 40.2, shares: 67.5 },
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 51540.0, percent: 24.0, gainPercent: 9.6, shares: 820.3 },
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 21475.0, percent: 10.0, gainPercent: 2.0, shares: 300.5 },
    { ticker: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", value: 4295.0, percent: 2.0, gainPercent: 7.6, shares: 18.8 },
    { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 4295.0, percent: 2.0, gainPercent: 0.0, shares: null },
  ],
  performance: [
    { date: "2025-10-31", value: 171200 },
    { date: "2025-11-30", value: 179600 },
    { date: "2025-12-31", value: 174300 },
    { date: "2026-01-31", value: 186900 },
    { date: "2026-02-28", value: 195400 },
    { date: "2026-03-31", value: 188100 },
    { date: "2026-04-30", value: 199700 },
    { date: "2026-05-31", value: 207300 },
    { date: "2026-06-30", value: 201500 },
    { date: "2026-07-31", value: 210800 },
    { date: "2026-08-31", value: 219600 },
    { date: "2026-09-30", value: 214750.0 },
  ],
  recentActivity: [
    { date: "2026-09-21", type: "Buy", description: "Purchased 8 shares of NVDA", amount: -1416.0 },
    { date: "2026-09-03", type: "Deposit", description: "Roth IRA contribution", amount: 6500.0 },
    { date: "2026-08-18", type: "Buy", description: "Purchased 15 shares of VTI", amount: -4140.0 },
  ],
};

// -----------------------------------------------------------------------------
// Client 9 — Daniel Kim — balanced w/ REIT + alternatives tilt. $892,600.
// -----------------------------------------------------------------------------
const client9 = {
  id: 9,
  profile: {
    name: "Daniel Kim",
    accountNumber: "LPL-••••-9634",
    accountType: "Joint Brokerage",
    advisorName: "Priya Nair, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 892600.0,
    dayChangeValue: 1963.7,
    dayChangePercent: 0.22,
    totalGainValue: 142010.0,
    totalGainPercent: 18.92,
    cashAvailable: 26778.0,
  },
  allocation: [
    { name: "US Stocks", percent: 40.0, value: 357040.0, color: COLORS["US Stocks"] },
    { name: "International Stocks", percent: 16.0, value: 142816.0, color: COLORS["International Stocks"] },
    { name: "Bonds", percent: 18.0, value: 160668.0, color: COLORS["Bonds"] },
    { name: "Real Estate (REITs)", percent: 12.0, value: 107112.0, color: COLORS["Real Estate (REITs)"] },
    { name: "Alternatives", percent: 11.0, value: 98186.0, color: COLORS["Alternatives"] },
    { name: "Cash", percent: 3.0, value: 26778.0, color: COLORS["Cash"] },
  ],
  sectors: [
    { name: "Technology", percent: 20.4 },
    { name: "Real Estate", percent: 16.1 },
    { name: "Financials", percent: 13.7 },
    { name: "Healthcare", percent: 11.5 },
    { name: "Industrials", percent: 9.8 },
    { name: "Consumer Discretionary", percent: 8.6 },
    { name: "Energy", percent: 6.4 },
    { name: "Other", percent: 13.5 },
  ],
  holdings: [
    { ticker: "VTI", name: "Vanguard Total Stock Market ETF", assetClass: "US Stocks", value: 267780.0, percent: 30.0, gainPercent: 22.6, shares: 971.0 },
    { ticker: "SCHD", name: "Schwab US Dividend Equity ETF", assetClass: "US Stocks", value: 89260.0, percent: 10.0, gainPercent: 16.9, shares: 1091.0 },
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 142816.0, percent: 16.0, gainPercent: 10.3, shares: 2273.0 },
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 160668.0, percent: 18.0, gainPercent: 2.5, shares: 2248.0 },
    { ticker: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Real Estate (REITs)", value: 107112.0, percent: 12.0, gainPercent: 6.8, shares: 1170.0 },
    { ticker: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", value: 98186.0, percent: 11.0, gainPercent: 12.9, shares: 429.0 },
    { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 26778.0, percent: 3.0, gainPercent: 0.0, shares: null },
  ],
  performance: [
    { date: "2025-10-31", value: 798400 },
    { date: "2025-11-30", value: 812600 },
    { date: "2025-12-31", value: 804100 },
    { date: "2026-01-31", value: 826900 },
    { date: "2026-02-28", value: 841300 },
    { date: "2026-03-31", value: 833700 },
    { date: "2026-04-30", value: 854200 },
    { date: "2026-05-31", value: 868900 },
    { date: "2026-06-30", value: 859400 },
    { date: "2026-07-31", value: 877100 },
    { date: "2026-08-31", value: 898300 },
    { date: "2026-09-30", value: 892600.0 },
  ],
  recentActivity: [
    { date: "2026-09-17", type: "Dividend", description: "VNQ quarterly dividend", amount: 964.5 },
    { date: "2026-09-04", type: "Buy", description: "Purchased 100 shares of SCHD", amount: -8180.0 },
    { date: "2026-08-21", type: "Dividend", description: "SCHD quarterly dividend", amount: 712.3 },
    { date: "2026-08-03", type: "Deposit", description: "ACH contribution", amount: 8000.0 },
  ],
};

// -----------------------------------------------------------------------------
// Client 10 — Patricia Sullivan — income/preservation, bond + dividend heavy.
// Total $1,675,300.
// -----------------------------------------------------------------------------
const client10 = {
  id: 10,
  profile: {
    name: "Patricia Sullivan",
    accountNumber: "LPL-••••-1075",
    accountType: "Traditional IRA",
    advisorName: "Marcus Reed, CFP®",
    advisorFirm: "LPL Financial",
    dataAsOf: "2026-10-01T20:00:00.000Z",
  },
  summary: {
    totalValue: 1675300.0,
    dayChangeValue: -804.1,
    dayChangePercent: -0.05,
    totalGainValue: 168200.0,
    totalGainPercent: 11.16,
    cashAvailable: 83765.0,
  },
  allocation: [
    { name: "Bonds", percent: 44.0, value: 737132.0, color: COLORS["Bonds"] },
    { name: "US Stocks", percent: 32.0, value: 536096.0, color: COLORS["US Stocks"] },
    { name: "International Stocks", percent: 8.0, value: 134024.0, color: COLORS["International Stocks"] },
    { name: "Real Estate (REITs)", percent: 6.0, value: 100518.0, color: COLORS["Real Estate (REITs)"] },
    { name: "Cash", percent: 5.0, value: 83765.0, color: COLORS["Cash"] },
    { name: "Alternatives", percent: 5.0, value: 83765.0, color: COLORS["Alternatives"] },
  ],
  sectors: [
    { name: "Financials", percent: 18.9 },
    { name: "Utilities", percent: 14.6 },
    { name: "Healthcare", percent: 13.2 },
    { name: "Consumer Staples", percent: 12.4 },
    { name: "Technology", percent: 10.1 },
    { name: "Energy", percent: 8.7 },
    { name: "Industrials", percent: 7.8 },
    { name: "Other", percent: 14.3 },
  ],
  holdings: [
    { ticker: "BND", name: "Vanguard Total Bond Market ETF", assetClass: "Bonds", value: 502590.0, percent: 30.0, gainPercent: 2.7, shares: 7033.0 },
    { ticker: "TLT", name: "iShares 20+ Year Treasury Bond ETF", assetClass: "Bonds", value: 234542.0, percent: 14.0, gainPercent: 1.3, shares: 2585.0 },
    { ticker: "SCHD", name: "Schwab US Dividend Equity ETF", assetClass: "US Stocks", value: 301554.0, percent: 18.0, gainPercent: 15.2, shares: 3687.0 },
    { ticker: "VIG", name: "Vanguard Dividend Appreciation ETF", assetClass: "US Stocks", value: 234542.0, percent: 14.0, gainPercent: 19.4, shares: 1224.0 },
    { ticker: "VXUS", name: "Vanguard Total International Stock ETF", assetClass: "International Stocks", value: 134024.0, percent: 8.0, gainPercent: 9.1, shares: 2133.0 },
    { ticker: "VNQ", name: "Vanguard Real Estate ETF", assetClass: "Real Estate (REITs)", value: 100518.0, percent: 6.0, gainPercent: 5.5, shares: 1098.0 },
    { ticker: "GLD", name: "SPDR Gold Shares", assetClass: "Alternatives", value: 83765.0, percent: 5.0, gainPercent: 10.2, shares: 366.0 },
    { ticker: "CASH", name: "Cash & Money Market", assetClass: "Cash", value: 83765.0, percent: 5.0, gainPercent: 0.0, shares: null },
  ],
  performance: [
    { date: "2025-10-31", value: 1588000 },
    { date: "2025-11-30", value: 1601500 },
    { date: "2025-12-31", value: 1594200 },
    { date: "2026-01-31", value: 1618900 },
    { date: "2026-02-28", value: 1634600 },
    { date: "2026-03-31", value: 1626100 },
    { date: "2026-04-30", value: 1648300 },
    { date: "2026-05-31", value: 1663700 },
    { date: "2026-06-30", value: 1652400 },
    { date: "2026-07-31", value: 1669800 },
    { date: "2026-08-31", value: 1688900 },
    { date: "2026-09-30", value: 1675300.0 },
  ],
  recentActivity: [
    { date: "2026-09-23", type: "Dividend", description: "BND monthly distribution", amount: 1864.2 },
    { date: "2026-09-09", type: "Dividend", description: "SCHD quarterly dividend", amount: 1420.75 },
    { date: "2026-08-26", type: "Interest", description: "Money market interest", amount: 318.6 },
    { date: "2026-08-04", type: "Withdrawal", description: "RMD distribution", amount: -12000.0 },
  ],
};

// Full set of per-client datasets, keyed by roster id order.
export const clients = [
  client1,
  client2,
  client3,
  client4,
  client5,
  client6,
  client7,
  client8,
  client9,
  client10,
];

// Resolve a full client dataset by id. Unknown or missing ids fall back to the
// first client (James Walker) so callers (and existing single-arg call sites)
// always get a valid, consistent dataset.
export function getClientData(id) {
  return clients.find((c) => c.id === id) || clients[0];
}

// -----------------------------------------------------------------------------
// Backward-compatible named exports.
//
// These point at client #1 (James Walker) so existing modules and tests that
// import the module-level `client`/`summary`/... constants keep working and
// keep asserting client #1's exact numbers. New code should prefer
// `getClientData(id)` / `clients`.
// -----------------------------------------------------------------------------
export const client = clients[0].profile;
export const summary = clients[0].summary;
export const allocation = clients[0].allocation;
export const sectors = clients[0].sectors;
export const holdings = clients[0].holdings;
export const performance = clients[0].performance;
export const recentActivity = clients[0].recentActivity;
