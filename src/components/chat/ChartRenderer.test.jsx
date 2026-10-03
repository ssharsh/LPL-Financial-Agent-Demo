import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import ChartRenderer from "./ChartRenderer.jsx";

// vitest runs in node (no DOM), so render to static HTML. Recharts draws the SVG
// only after measuring, so these check the wrapper, labels, legend and table.
const render = (chart) => renderToStaticMarkup(<ChartRenderer chart={chart} />);

const rows2 = (x, y) => [
  { [x]: "2024-10", [y]: "100.5" },
  { [x]: "2024-11", [y]: "200.25" },
];

describe("ChartRenderer", () => {
  it("CR-1: line renders an accessible figure", () => {
    const html = render({ type: "line", x: "month", y: "end_value", series: "", rows: rows2("month", "end_value") });
    expect(html).toContain('role="img"');
    expect(html).toContain('aria-label="Line chart of End value by Month"');
  });

  it("CR-2: stacked_area renders", () => {
    const html = render({
      type: "stacked_area",
      x: "month",
      y: "market_value",
      series: "asset_class",
      rows: [
        { month: "2026-08", asset_class: "Bonds", market_value: "10" },
        { month: "2026-08", asset_class: "Cash", market_value: "5" },
      ],
    });
    expect(html).toContain('aria-label="Stacked area chart of Market value by Month"');
  });

  it("CR-3: bar renders", () => {
    const html = render({
      type: "bar",
      x: "txn_type",
      y: "total_amount",
      series: "",
      rows: [{ txn_type: "deposit", total_amount: "13500.00" }],
    });
    expect(html).toContain('aria-label="Bar chart of Total amount by Txn type"');
  });

  it("CR-4: pie renders a legend with formatted values and shares", () => {
    const html = render({
      type: "pie",
      x: "asset_class",
      y: "market_value",
      series: "",
      rows: [
        { asset_class: "US Equity", market_value: "75" },
        { asset_class: "Cash", market_value: "25" },
      ],
    });
    expect(html).toContain('aria-label="Pie chart of Market value by Asset class"');
    expect(html).toContain("US Equity");
    expect(html).toContain("$75.00");
    expect(html).toContain("75.00%");
    expect(html).toContain("25.00%");
  });

  it("CR-5: table renders headers and formatted cells, not role=img", () => {
    const html = render({
      type: "table",
      x: "",
      y: "",
      series: "",
      rows: [{ ticker: "QXLC", market_value: "117969.10", weight_pct: "40.32" }],
    });
    expect(html).toContain("<table");
    expect(html).toContain("Market value");
    expect(html).toContain("$117,969.10");
    expect(html).toContain("40.32%");
    expect(html).not.toContain('role="img"');
  });

  it("CR-6: malformed or unknown specs render nothing", () => {
    expect(render(null)).toBe("");
    expect(render({ type: "radar", x: "a", y: "b", series: "", rows: [{ a: 1, b: 2 }] })).toBe("");
    expect(render({ type: "line", x: "month", y: "end_value", series: "", rows: [] })).toBe("");
    expect(render({ type: "bar", x: "missing", y: "v", series: "", rows: [{ v: "1" }] })).toBe("");
  });
});
