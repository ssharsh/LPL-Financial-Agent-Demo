import AllocationChart from "./AllocationChart.jsx";
import HoldingsTable from "./HoldingsTable.jsx";
import PerformanceChart from "./PerformanceChart.jsx";
import DataAsOfBadge from "./DataAsOfBadge.jsx";
import {
  formatCurrency,
  formatSignedCurrency,
  formatPercent,
} from "../../utils/format.js";

// The portfolio zone: a scrollable panel with the headline numbers up top and
// the allocation / holdings / performance visuals below. This is the "where is
// my money" view the chat answers point at. All numbers come from the active
// client's `data` prop (from getClientData) so switching clients re-renders
// the whole panel.
export default function PortfolioPanel({ data }) {
  const { summary, allocation, holdings, performance, profile } = data;
  const up = summary.dayChangeValue >= 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-gray-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-gray-700">Your Portfolio</h2>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {/* Headline numbers */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-soft">
          <p className="text-[11px] uppercase tracking-wide text-gray-500">
            Total value
          </p>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(summary.totalValue)}
          </p>
          <p className={`text-sm font-medium ${up ? "text-green-700" : "text-red-700"}`}>
            {formatSignedCurrency(summary.dayChangeValue)} (
            {formatPercent(summary.dayChangePercent, { signed: true })}) today
          </p>
          <p className="mt-1 text-[11px] text-gray-500">
            All-time: {formatSignedCurrency(summary.totalGainValue)} (
            {formatPercent(summary.totalGainPercent, { signed: true })})
          </p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-soft">
          <PerformanceChart performance={performance} />
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-soft">
          <AllocationChart allocation={allocation} />
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-soft">
          <HoldingsTable holdings={holdings} />
        </div>
      </div>

      <DataAsOfBadge asOf={profile.dataAsOf} />
    </div>
  );
}
