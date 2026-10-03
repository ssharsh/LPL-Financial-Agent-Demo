import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";
import { CLIENTS, installApiMock } from "./test/apiMock.js";
import { formatCurrency } from "./utils/format.js";

// -----------------------------------------------------------------------------
// App-level selection → portfolio panel wiring.
//
// Selecting a different client in the top-right dropdown must switch the
// portfolio panel's headline total to that client's number from /api/portfolio.
// -----------------------------------------------------------------------------

function portfolio() {
  return within(screen.getByLabelText("Portfolio"));
}

function totalOf(id) {
  return formatCurrency(Number(CLIENTS.find((c) => c.client_id === id).total));
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  installApiMock();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App — selecting a client updates the portfolio panel total", () => {
  it("PP-1: defaults to client #1's total value", async () => {
    render(<App />);
    expect(await portfolio().findAllByText(totalOf(1))).not.toHaveLength(0);
  });

  it("PP-2: selecting a different client swaps the headline total", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(totalOf(1)).not.toBe(totalOf(3));
    await portfolio().findAllByText(totalOf(1));

    await user.selectOptions(await screen.findByLabelText(/client account/i), "3");

    expect(await portfolio().findAllByText(totalOf(3))).not.toHaveLength(0);
    expect(portfolio().queryByText(totalOf(1))).not.toBeInTheDocument();
  });
});
