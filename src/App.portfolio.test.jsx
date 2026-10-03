import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";
import { getClientData } from "./data/mockPortfolio.js";

// -----------------------------------------------------------------------------
// App-level selection → portfolio panel wiring.
//
// Selecting a different client in the top-right dropdown must switch the
// portfolio panel's headline total to that client's number.
// -----------------------------------------------------------------------------

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function getSelect() {
  return screen.getByLabelText(/client account/i);
}

function portfolio() {
  return within(screen.getByLabelText("Portfolio"));
}

describe("App — selecting a client updates the portfolio panel total", () => {
  it("PP-1: defaults to client #1's total value", () => {
    render(<App />);
    const client1Total = formatCurrency(getClientData(1).summary.totalValue);
    expect(portfolio().getByText(client1Total)).toBeInTheDocument();
  });

  it("PP-2: selecting a different client swaps the headline total", async () => {
    const user = userEvent.setup();
    render(<App />);

    const client1Total = formatCurrency(getClientData(1).summary.totalValue); // $742,318.55
    const client7Total = formatCurrency(getClientData(7).summary.totalValue); // $3,480,000.00

    // Sanity: the two totals are clearly different.
    expect(client1Total).not.toBe(client7Total);

    // Start on #1.
    expect(portfolio().getByText(client1Total)).toBeInTheDocument();

    // Switch to Christopher Lee (id 7).
    await user.selectOptions(getSelect(), "7");

    // Panel now shows #7's total and no longer #1's.
    expect(portfolio().getByText(client7Total)).toBeInTheDocument();
    expect(portfolio().queryByText(client1Total)).not.toBeInTheDocument();
  });
});
