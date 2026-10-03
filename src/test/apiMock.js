// Fake backend for App-level tests: a fetch stub that answers /api/clients,
// /api/portfolio?client_id=N and /api/chat with the real API shapes.
import { vi } from "vitest";

export const CLIENTS = [
  { client_id: 1, name: "Elena Park", accounts: [101, 102], total: "742318.55" },
  { client_id: 2, name: "Marcus Lee", accounts: [104, 105], total: "215000.00" },
  { client_id: 3, name: "Priya Raman", accounts: [106], total: "3480000.00" },
];

function json(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

export function portfolioFor(id) {
  const c = CLIENTS.find((x) => x.client_id === id);
  return {
    client: { client_id: c.client_id, name: c.name, advisor_name: "Sarah Whitfield" },
    data_as_of: "2026-09-30",
    totals: { total_value: c.total, cash_balance: "1000.00" },
    accounts: c.accounts.map((a) => ({
      account_id: a,
      account_name: `Account ${a}`,
      account_type: "IRA",
      total_value: c.total,
    })),
    holdings: [
      { ticker: "VTI", name: "Vanguard Total Stock", asset_class: "Equity", market_value: c.total, weight_pct: "100.0" },
    ],
    performance: null,
    charts: { performance: null, allocation: null },
  };
}

// Installs the stub and returns the vi.fn so tests can inspect calls.
export function installApiMock({ defaultClientId = "1" } = {}) {
  const fetchMock = vi.fn(async (url, options = {}) => {
    const u = new URL(url, "http://localhost");
    if (u.pathname === "/api/clients") {
      return json(200, {
        clients: CLIENTS.map(({ client_id, name }) => ({ client_id, name })),
        default_client_id: defaultClientId,
      });
    }
    if (u.pathname === "/api/portfolio") {
      return json(200, portfolioFor(Number(u.searchParams.get("client_id") ?? defaultClientId)));
    }
    if (u.pathname === "/api/chat") {
      const body = JSON.parse(options.body);
      return json(200, {
        text: `Answer for client ${body.client_id}`,
        interpretation: null,
        sources: [],
        chart: null,
        log_id: "log_1",
        verification: null,
        declined: null,
      });
    }
    return json(404, { error: "not found" });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
