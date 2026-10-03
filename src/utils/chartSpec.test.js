import { describe, it, expect } from "vitest";
import {
  normalizeChart,
  valueKind,
  formatValue,
  formatCategory,
  humanizeKey,
  describeChart,
} from "./chartSpec.js";

const line = {
  type: "line",
  x: "month",
  y: "end_value",
  series: "",
  rows: [
    { month: "2024-10", end_value: "230977.74" },
    { month: "2024-11", end_value: "234685.27" },
  ],
};

describe("normalizeChart", () => {
  it("CHS-1: a valid single-series line coerces numeric strings", () => {
    const spec = normalizeChart(line);
    expect(spec.type).toBe("line");
    expect(spec.seriesKeys).toEqual(["end_value"]);
    expect(spec.data).toEqual([
      { month: "2024-10", end_value: 230977.74 },
      { month: "2024-11", end_value: 234685.27 },
    ]);
  });

  it("CHS-2: rows with a non-numeric y are dropped; all bad -> null", () => {
    const spec = normalizeChart({ ...line, rows: [...line.rows, { month: "2024-12", end_value: "n/a" }] });
    expect(spec.data).toHaveLength(2);
    expect(normalizeChart({ ...line, rows: [{ month: "2024-10", end_value: null }] })).toBeNull();
  });

  it("CHS-3: stacked_area pivots long rows into one key per series", () => {
    const spec = normalizeChart({
      type: "stacked_area",
      x: "month",
      y: "market_value",
      series: "asset_class",
      rows: [
        { month: "2026-08", asset_class: "Bonds", market_value: "10" },
        { month: "2026-08", asset_class: "US Equity", market_value: "20" },
        { month: "2026-09", asset_class: "Bonds", market_value: "11" },
        { month: "2026-09", asset_class: "US Equity", market_value: "21" },
      ],
    });
    expect(spec.seriesKeys).toEqual(["Bonds", "US Equity"]);
    expect(spec.data).toEqual([
      { month: "2026-08", Bonds: 10, "US Equity": 20 },
      { month: "2026-09", Bonds: 11, "US Equity": 21 },
    ]);
  });

  it("CHS-4: bar and pie specs normalize", () => {
    const bar = normalizeChart({
      type: "bar",
      x: "txn_type",
      y: "total_amount",
      series: "",
      rows: [{ txn_type: "buy", total_amount: "10873.62" }],
    });
    expect(bar.data).toEqual([{ txn_type: "buy", total_amount: 10873.62 }]);
    const pie = normalizeChart({
      type: "pie",
      x: "asset_class",
      y: "market_value",
      series: "",
      rows: [{ asset_class: "Cash", market_value: "19170.61" }],
    });
    expect(pie.type).toBe("pie");
  });

  it("CHS-5: table keeps raw rows and lists columns", () => {
    const spec = normalizeChart({ type: "table", x: "", y: "", series: "", rows: [{ ticker: "QXLC", market_value: "1" }] });
    expect(spec).toEqual({ type: "table", columns: ["ticker", "market_value"], rows: [{ ticker: "QXLC", market_value: "1" }] });
  });

  it("CHS-6: malformed specs are null, never throw", () => {
    expect(normalizeChart(null)).toBeNull();
    expect(normalizeChart(undefined)).toBeNull();
    expect(normalizeChart("line")).toBeNull();
    expect(normalizeChart({ ...line, type: "radar" })).toBeNull();
    expect(normalizeChart({ ...line, rows: [] })).toBeNull();
    expect(normalizeChart({ ...line, rows: "nope" })).toBeNull();
    expect(normalizeChart({ ...line, x: "date" })).toBeNull();
    expect(normalizeChart({ ...line, y: undefined })).toBeNull();
  });
});

describe("formatting helpers", () => {
  it("CHS-7: month strings format without timezone shift", () => {
    expect(formatCategory("2024-10")).toBe("Oct 2024");
    expect(formatCategory("2026-09")).toBe("Sep 2026");
  });

  it("CHS-8: snake_case categories are humanized; others kept", () => {
    expect(formatCategory("roth_ira")).toBe("Roth ira");
    expect(formatCategory("withdrawal")).toBe("Withdrawal");
    expect(formatCategory("US Equity")).toBe("US Equity");
    expect(humanizeKey("end_value")).toBe("End value");
  });

  it("CHS-9: valueKind guesses from the key name", () => {
    expect(valueKind("weight_pct")).toBe("percent");
    expect(valueKind("time_weighted_return_pct")).toBe("percent");
    expect(valueKind("end_value")).toBe("currency");
    expect(valueKind("total_amount")).toBe("currency");
    expect(valueKind("count")).toBe("number");
  });

  it("CHS-10: formatValue formats by kind and never prints NaN", () => {
    expect(formatValue("currency", "1234.5")).toBe("$1,234.50");
    expect(formatValue("percent", "11.82")).toBe("11.82%");
    expect(formatValue("number", 1200)).toBe("1,200");
    expect(formatValue("currency", "abc")).toBe("—");
  });

  it("CHS-11: describeChart gives an accessible label", () => {
    expect(describeChart(normalizeChart(line))).toBe("Line chart of End value by Month");
  });
});
