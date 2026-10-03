import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";
import { CLIENTS, installApiMock } from "./test/apiMock.js";

// -----------------------------------------------------------------------------
// Client selector dropdown (top-right header) — interaction tests against a
// fake backend (/api/clients, /api/portfolio, /api/chat).
// -----------------------------------------------------------------------------

function getSelect() {
  // The dropdown is labeled "Client account".
  return screen.findByLabelText(/client account/i);
}

function accountsLabel(c) {
  return `Accounts ${c.accounts.join(", ")}`;
}

let fetchMock;
beforeEach(() => {
  window.history.replaceState(null, "", "/");
  fetchMock = installApiMock();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Client selector dropdown — rendering", () => {
  it("DD-1: renders a labeled select control", async () => {
    render(<App />);
    const select = await getSelect();
    expect(select.tagName).toBe("SELECT");
  });

  it("DD-2: lists every backend client as an option", async () => {
    render(<App />);
    const options = within(await getSelect()).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(CLIENTS.map((c) => c.name));
  });

  it("DD-3: defaults to the backend's default client", async () => {
    render(<App />);
    const selected = within(await getSelect()).getByRole("option", { selected: true });
    expect(selected.textContent).toBe(CLIENTS[0].name);
  });

  it("DD-4: shows the default client's account numbers", async () => {
    render(<App />);
    expect(await screen.findByText(accountsLabel(CLIENTS[0]))).toBeInTheDocument();
  });

  it("DD-5: ?client=N in the URL picks the initial client", async () => {
    window.history.replaceState(null, "", "/?client=3");
    render(<App />);
    const selected = within(await getSelect()).getByRole("option", { selected: true });
    expect(selected.textContent).toBe("Priya Raman");
    expect(await screen.findByText(accountsLabel(CLIENTS[2]))).toBeInTheDocument();
  });
});

describe("Client selector dropdown — selection behavior", () => {
  it("DD-6: selecting a client updates the header, the URL and the portfolio request", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(accountsLabel(CLIENTS[0]));

    await user.selectOptions(await getSelect(), "2");

    expect(await screen.findByText(accountsLabel(CLIENTS[1]))).toBeInTheDocument();
    expect(screen.queryByText(accountsLabel(CLIENTS[0]))).not.toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get("client")).toBe("2");
    expect(fetchMock.mock.calls.map((c) => c[0])).toContain("/api/portfolio?client_id=2");
  });

  it("DD-7: chat messages go to the selected client and switching clears the conversation", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(accountsLabel(CLIENTS[0]));

    await user.type(screen.getByRole("textbox"), "What do I hold?{Enter}");
    expect(await screen.findAllByText("Answer for client 1")).not.toHaveLength(0);
    const firstChat = JSON.parse(fetchMock.mock.calls.find((c) => c[0] === "/api/chat")[1].body);

    await user.selectOptions(await getSelect(), "3");
    await screen.findByText(accountsLabel(CLIENTS[2]));
    expect(screen.queryByText("Answer for client 1")).not.toBeInTheDocument();

    await user.type(screen.getByRole("textbox"), "And now?{Enter}");
    expect(await screen.findAllByText("Answer for client 3")).not.toHaveLength(0);
    const chats = fetchMock.mock.calls.filter((c) => c[0] === "/api/chat");
    const secondChat = JSON.parse(chats[chats.length - 1][1].body);
    expect(firstChat.client_id).toBe("1");
    expect(secondChat.client_id).toBe("3");
    // A fresh conversation per client.
    expect(secondChat.conversation_id).not.toBe(firstChat.conversation_id);
  });
});

describe("Header still intact alongside the dropdown", () => {
  it("DD-8: the compliance disclaimer remains visible", async () => {
    render(<App />);
    await getSelect();
    expect(screen.getByText(/does not provide financial advice/i)).toBeInTheDocument();
  });

  it("DD-9: the app title remains visible", async () => {
    render(<App />);
    await getSelect();
    expect(
      screen.getByRole("heading", { name: /orama portfolio assistant/i })
    ).toBeInTheDocument();
  });
});
