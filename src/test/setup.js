// Vitest setup: adds jest-dom matchers (toBeInTheDocument, etc.) and cleans up
// the rendered DOM between tests.
import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// --- jsdom polyfills -------------------------------------------------------
// jsdom doesn't implement a few browser APIs that our components (ChatWindow
// auto-scroll, Recharts ResponsiveContainer) rely on. Stub them so the full
// App can render in tests.

// scrollIntoView — called by ChatWindow on new messages.
Element.prototype.scrollIntoView = vi.fn();

// ResizeObserver — used by Recharts' ResponsiveContainer.
globalThis.ResizeObserver =
  globalThis.ResizeObserver ||
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

// matchMedia — occasionally used by responsive libs.
if (!globalThis.matchMedia) {
  globalThis.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  });
}

afterEach(() => {
  cleanup();
});
