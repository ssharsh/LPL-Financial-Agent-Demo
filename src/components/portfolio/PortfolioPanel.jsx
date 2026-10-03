import HoldingsTable from "./HoldingsTable.jsx";
import DataAsOfBadge from "./DataAsOfBadge.jsx";
import ChartRenderer from "../chat/ChartRenderer.jsx";
import ErrorState from "../common/ErrorState.jsx";
import {
  formatCurrency,
  formatSignedCurrency,
  formatPercent,
  formatDate,
} from "../../utils/format.js";

// The portfolio zone: headline numbers, value over time, allocation and
// holdings, all from /api/portfolio (the same fact tools the chat uses, so the
// panel never contradicts an answer). Charts use the same ChartRenderer as chat.
export default function PortfolioPanel({ portfolio, loading, error, onRetry }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-gray-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-gray-700">Your Portfolio</h2>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {loading && !portfolio ? (
          <p className="text-xs text-gray-500" role="status">
            Loading portfolio…
          </p>
        ) : error && !portfolio ? (
          <ErrorState message={error} onRetry={onRetry} />
        ) : portfolio ? (
          <PortfolioBody portfolio={portfolio} />
        ) : null}
      </div>

      {portfolio && <DataAsOfBadge asOf={portfolio.data_as_of} />}
    </div>
  );
}

function PortfolioBody({ portfolio }) {
  const { totals, performance, charts, holdings } = portfolio;
  const gain = performance ? Number(performance.investment_gain) : null;
  const twr =
    performance?.time_weighted_return_pct != null
      ? Number(performance.time_weighted_return_pct)
      : null;

  return (
    <>
      {/* Headline numbers */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-soft">
        <p className="text-[11px] uppercase tracking-wide text-gray-500">Total value</p>
        <p className="text-2xl font-bold text-gray-900">
          {formatCurrency(Number(totals?.total_value))}
        </p>
        <p className="text-[11px] text-gray-500">
          Cash {formatCurrency(Number(totals?.cash_balance))}
        </p>
        {performance && (
          <p className="mt-1 text-[11px] text-gray-600">
            Since {formatDate(performance.start_month)}:{" "}
            <span className={`font-medium ${gain >= 0 ? "text-green-700" : "text-red-700"}`}>
              {formatSignedCurrency(gain)}
            </span>{" "}
            investment gain ·{" "}
            {twr != null ? (
              <>
                <span className="font-medium">{formatPercent(twr, { signed: true })}</span>{" "}
                {performance.return_label}
              </>
            ) : (
              "Return unavailable"
            )}
          </p>
        )}
      </div>

      {charts?.performance && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-soft">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Value over time
          </h3>
          <ChartRenderer chart={charts.performance} height={160} />
        </div>
      )}

      {charts?.allocation && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-soft">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Asset allocation
          </h3>
          <ChartRenderer chart={charts.allocation} height={176} />
        </div>
      )}

      {holdings?.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-soft">
          <HoldingsTable holdings={holdings} />
        </div>
      )}
    </>
  );
}
