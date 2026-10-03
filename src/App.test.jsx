import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";
import { clientRoster } from "./data/mockPortfolio.js";

// -----------------------------------------------------------------------------
// Client selector dropdown (top-right header) — interaction tests.
// -----------------------------------------------------------------------------

function getSelect() {
  // The dropdown is labeled "Client account".
  return screen.getByLabelText(/client account/i);
}

describe("Client selector dropdown — rendering", () => {
  it("DD-1: renders a labeled select control", () => {
    render(<App />);
    const select = getSelect();
    expect(select).toBeInTheDocument();
    expect(select.tagName).toBe("SELECT");
  });

  it("DD-2: lists all 10 client names as options", () => {
    render(<App />);
    const options = within(getSelect()).getAllByRole("option");
    expect(options).toHaveLength(10);
    const texts = options.map((o) => o.textContent);
    for (const c of clientRoster) {
      expect(texts).toContain(c.name);
    }
  });

  it("DD-3: defaults to the first client in the roster", () => {
    render(<App />);
    // Selected option's text is the first client's name.
    const select = getSelect();
    const selected = within(select).getByRole("option", {
      selected: true,
    });
    expect(selected.textContent).toBe(clientRoster[0].name);
  });

  it("DD-4: shows the first client's masked account number by default", () => {
    render(<App />);
    expect(screen.getByText(clientRoster[0].accountNumber)).toBeInTheDocument();
  });
});

describe("Client selector dropdown — selection behavior", () => {
  it("DD-5: selecting a different client updates the account number shown", async () => {
    const user = userEvent.setup();
    render(<App />);

    const target = clientRoster[5]; // Maria Garcia
    await user.selectOptions(getSelect(), String(target.id));

    expect(screen.getByText(target.accountNumber)).toBeInTheDocument();
    // The previous (default) account number should no longer be shown.
    expect(
      screen.queryByText(clientRoster[0].accountNumber)
    ).not.toBeInTheDocument();
  });

  it("DD-6: can select the last client in the list (boundary)", async () => {
    const user = userEvent.setup();
    render(<App />);

    const last = clientRoster[clientRoster.length - 1]; // Patricia Sullivan
    await user.selectOptions(getSelect(), String(last.id));

    expect(screen.getByText(last.accountNumber)).toBeInTheDocument();
  });

  it("DD-7: selecting every client in turn always shows a valid account number", async () => {
    const user = userEvent.setup();
    render(<App />);

    for (const c of clientRoster) {
      await user.selectOptions(getSelect(), String(c.id));
      expect(screen.getByText(c.accountNumber)).toBeInTheDocument();
    }
  });

  it("DD-8: re-selecting the already-active client keeps it selected (no crash)", async () => {
    const user = userEvent.setup();
    render(<App />);

    const first = clientRoster[0];
    await user.selectOptions(getSelect(), String(first.id));
    const selected = within(getSelect()).getByRole("option", { selected: true });
    expect(selected.textContent).toBe(first.name);
  });
});

describe("Header still intact alongside the dropdown", () => {
  it("DD-9: the compliance disclaimer remains visible", () => {
    render(<App />);
    expect(
      screen.getByText(/does not provide financial advice/i)
    ).toBeInTheDocument();
  });

  it("DD-10: the app title remains visible", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: /lpl portfolio assistant/i })
    ).toBeInTheDocument();
  });
});
