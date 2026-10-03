import { formatCurrency, formatPercent } from "../../utils/format.js";
// Compact table of individual holdings, sorted by size. Values arrive from the
// backend as exact strings ("117969.10") and are converted only for display.
// Fixed layout + nowrap values keep the columns inside the narrow panel.
export default function HoldingsTable({ holdings }) {
  const sorted = [...holdings].sort((a, b) => Number(b.market_value) - Number(a.market_value));
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Holdings
      </h3>
      <table className="w-full table-fixed text-left text-[11px]">
        <thead>
          <tr className="text-gray-500">
            <th scope="col" className="w-[56%] pb-1 font-medium">Holding</th>
            <th scope="col" className="pb-1 pl-1 text-right font-medium">Value</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((h) => (
            <tr key={h.ticker} className="border-t border-gray-100">
              <td className="py-1.5 pr-1 align-top">
                <div className="font-semibold text-gray-800">{h.ticker}</div>
                <div className="truncate text-[10px] text-gray-500">{h.name}</div>
              </td>
              <td className="py-1.5 pl-1 text-right align-top">
                <div className="whitespace-nowrap font-medium text-gray-800">
                  {formatCurrency(Number(h.market_value))}
                </div>
                <div className="text-[10px] text-gray-500">
                  {formatPercent(Number(h.weight_pct))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
