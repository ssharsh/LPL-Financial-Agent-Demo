import { describe, it, expect } from "vitest";
import {
  formatCurrency,
  formatPercent,
  formatSignedCurrency,
  formatDate,
  formatTime,
} from "./format.js";

describe("formatCurrency", () => {
  it("FMT-C1: formats a standard USD amount", () => {
    expect(formatCurrency(1234.5)).toBe("$1,234.50");
  });
  it("FMT-C2: compact notation for large numbers", () => {
    expect(formatCurrency(742318.55, { compact: true })).toMatch(/\$74[0-9]\.?\d?K/);
  });
  it("FMT-C3: null/NaN render as em dash, never 'NaN'", () => {
    expect(formatCurrency(null)).toBe("—");
    expect(formatCurrency(NaN)).toBe("—");
    expect(formatCurrency(undefined)).toBe("—");
  });
  it("FMT-C4: zero is a valid value, not an em dash", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });
});

describe("formatPercent", () => {
  it("FMT-P1: formats a percent value (input is already a percentage)", () => {
    expect(formatPercent(20.98)).toBe("20.98%");
  });
  it("FMT-P2: signed option prefixes a plus for positives", () => {
    expect(formatPercent(0.43, { signed: true })).toBe("+0.43%");
  });
  it("FMT-P3: negative percent keeps its own minus, no double sign", () => {
    expect(formatPercent(-2.5, { signed: true })).toBe("-2.5%");
  });
  it("FMT-P4: null/NaN render as em dash", () => {
    expect(formatPercent(null)).toBe("—");
    expect(formatPercent(NaN)).toBe("—");
  });
});

describe("formatSignedCurrency", () => {
  it("FMT-S1: positive gets a leading plus", () => {
    expect(formatSignedCurrency(3184.22)).toBe("+$3,184.22");
  });
  it("FMT-S2: negative gets a leading minus", () => {
    expect(formatSignedCurrency(-5160)).toBe("-$5,160.00");
  });
  it("FMT-S3: null renders as em dash", () => {
    expect(formatSignedCurrency(null)).toBe("—");
  });
});

describe("formatDate (timezone-safe for date-only strings)", () => {
  it("FMT-D1: a YYYY-MM-DD string does not shift a day", () => {
    // The bug this guards against: UTC parse + local format rolling back a day.
    expect(formatDate("2025-10-31")).toBe("Oct 31, 2025");
  });
  it("FMT-D3: a YYYY-MM month renders as month + year, no shift", () => {
    expect(formatDate("2026-09")).toBe("Sep 2026");
    expect(formatDate("2024-10")).toBe("Oct 2024");
  });
  it("FMT-D2: empty input renders as em dash", () => {
    expect(formatDate("")).toBe("—");
    expect(formatDate(null)).toBe("—");
  });
});

describe("formatTime", () => {
  it("FMT-T1: empty input renders as em dash", () => {
    expect(formatTime(null)).toBe("—");
  });
  it("FMT-T2: a valid ISO timestamp produces an AM/PM time", () => {
    expect(formatTime("2026-10-01T15:30:00.000Z")).toMatch(/\d{1,2}:\d{2}\s?(AM|PM)/i);
  });
});
