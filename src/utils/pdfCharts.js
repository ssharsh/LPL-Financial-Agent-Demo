// Draw a backend chart spec ({type, x, y, series, rows}) straight into a jsPDF
// document with vector primitives, so the PDF matches what the chat showed.
import {
  PALETTE,
  normalizeChart,
  valueKind,
  formatValue,
  formatCategory,
  humanizeKey,
} from "./chartSpec.js";

const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const color = (i) => hex(PALETTE[i % PALETTE.length]);
const ascii = (s) => String(s ?? "").replace(/[^\x20-\x7E]/g, "");

// Returns the height used (0 if the chart can't be drawn).
export function drawChart(doc, chart, x, y, w, h = 170) {
  const spec = normalizeChart(chart);
  if (!spec || spec.type === "table") return 0;
  doc.setFont("helvetica", "normal");
  if (spec.type === "pie") return drawPie(doc, spec, x, y, w, h);
  return drawCartesian(doc, spec, x, y, w, h);
}

function legend(doc, labels, x, y, w) {
  let cx = x;
  let cy = y;
  doc.setFontSize(8);
  labels.forEach((label, i) => {
    const text = ascii(label);
    const tw = doc.getTextWidth(text) + 18;
    if (cx + tw > x + w) {
      cx = x;
      cy += 11;
    }
    doc.setFillColor(...color(i));
    doc.rect(cx, cy - 6, 7, 7, "F");
    doc.setTextColor(60, 60, 60);
    doc.text(text, cx + 10, cy);
    cx += tw;
  });
  return cy - y + 12;
}

function drawCartesian(doc, spec, x, y, w, h) {
  const { type, x: xKey, y: yKey, seriesKeys, data } = spec;
  const kind = valueKind(yKey);
  const values = data.flatMap((r) => seriesKeys.map((k) => r[k])).filter((v) => Number.isFinite(v));
  if (!values.length) return 0;
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  if (type === "bar") {
    lo = Math.min(0, lo);
    hi = Math.max(0, hi);
  }
  if (hi === lo) hi = lo + 1;
  const pad = (hi - lo) * 0.08;
  if (type !== "bar") lo -= pad;
  hi += pad;

  const left = x + 58;
  const plotW = w - 62;
  const top = y + 6;
  const plotH = h - 34;
  const py = (v) => top + plotH - ((v - lo) / (hi - lo)) * plotH;

  // Grid + y ticks
  doc.setFontSize(7);
  doc.setDrawColor(225, 225, 225);
  doc.setLineWidth(0.5);
  for (let i = 0; i <= 4; i++) {
    const v = lo + ((hi - lo) * i) / 4;
    const yy = py(v);
    doc.line(left, yy, left + plotW, yy);
    doc.setTextColor(110, 110, 110);
    doc.text(ascii(formatValue(kind, v, { compact: true })), left - 4, yy + 2, { align: "right" });
  }
  doc.setDrawColor(150, 150, 150);
  doc.line(left, top + plotH, left + plotW, top + plotH);

  // X labels (thinned so they don't overlap)
  const n = data.length;
  const step = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(plotW / 48))));
  const slotX = (i) =>
    type === "bar" ? left + (plotW / n) * (i + 0.5) : left + (n === 1 ? plotW / 2 : (plotW * i) / (n - 1));
  doc.setTextColor(110, 110, 110);
  data.forEach((r, i) => {
    if (i % step === 0 || i === n - 1) {
      doc.text(ascii(formatCategory(r[xKey])), slotX(i), top + plotH + 10, { align: "center" });
    }
  });

  if (type === "bar") {
    const groupW = (plotW / n) * 0.7;
    const barW = groupW / seriesKeys.length;
    data.forEach((r, i) => {
      seriesKeys.forEach((k, s) => {
        const v = r[k];
        if (!Number.isFinite(v)) return;
        const bx = slotX(i) - groupW / 2 + s * barW;
        const y0 = py(0);
        const y1 = py(v);
        doc.setFillColor(...color(s));
        doc.rect(bx, Math.min(y0, y1), Math.max(1, barW - 1), Math.max(0.5, Math.abs(y1 - y0)), "F");
      });
    });
  } else {
    doc.setLineWidth(1.4);
    seriesKeys.forEach((k, s) => {
      doc.setDrawColor(...color(s));
      let prev = null;
      data.forEach((r, i) => {
        const v = r[k];
        if (!Number.isFinite(v)) {
          prev = null;
          return;
        }
        const pt = [slotX(i), py(v)];
        if (prev) doc.line(prev[0], prev[1], pt[0], pt[1]);
        prev = pt;
      });
    });
  }

  const labels = seriesKeys.length > 1 ? seriesKeys : [humanizeKey(yKey)];
  return h - 14 + legend(doc, labels, left, y + h - 6, plotW);
}

function drawPie(doc, spec, x, y, w, h) {
  const { x: xKey, data, seriesKeys } = spec;
  const key = seriesKeys[0];
  const slices = data.filter((r) => Number.isFinite(r[key]) && r[key] > 0);
  const total = slices.reduce((s, r) => s + r[key], 0);
  if (!total) return 0;
  const r = Math.min(h, w) / 2 - 10;
  const cx = x + r + 10;
  const cy = y + r + 4;
  let a0 = -Math.PI / 2;
  slices.forEach((row, i) => {
    const a1 = a0 + (row[key] / total) * Math.PI * 2;
    doc.setFillColor(...color(i));
    // One closed polygon per slice (center -> arc points), so there are no seams.
    const steps = Math.max(2, Math.ceil(((a1 - a0) / (Math.PI * 2)) * 120));
    const pts = [[cx, cy]];
    for (let s = 0; s <= steps; s++) {
      const t = a0 + ((a1 - a0) * s) / steps;
      pts.push([cx + r * Math.cos(t), cy + r * Math.sin(t)]);
    }
    const rel = pts.slice(1).map((p, k) => [p[0] - pts[k][0], p[1] - pts[k][1]]);
    doc.setDrawColor(255, 255, 255);
    doc.setLineWidth(0.8);
    doc.lines(rel, cx, cy, [1, 1], "FD", true);
    a0 = a1;
  });
  // Legend with value and share
  const kind = valueKind(key);
  doc.setFontSize(8);
  let ly = y + 14;
  const lx = cx + r + 20;
  slices.forEach((row, i) => {
    doc.setFillColor(...color(i));
    doc.rect(lx, ly - 6, 7, 7, "F");
    doc.setTextColor(60, 60, 60);
    const share = ((row[key] / total) * 100).toFixed(1);
    doc.text(ascii(`${formatCategory(row[xKey])}: ${formatValue(kind, row[key])} (${share}%)`), lx + 11, ly);
    ly += 13;
  });
  return Math.max(r * 2 + 10, ly - y);
}
