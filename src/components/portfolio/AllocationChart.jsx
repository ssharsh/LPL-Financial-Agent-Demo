import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { formatCurrency, formatPercent } from "../../utils/format.js";

// Donut chart of asset-class allocation. Colors come from the data so they
// stay consistent with any legend.
export default function AllocationChart({ allocation }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Asset allocation
      </h3>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={allocation}
              dataKey="percent"
              nameKey="name"
              innerRadius={45}
              outerRadius={70}
              paddingAngle={2}
            >
              {allocation.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name, props) => [
                `${formatPercent(value)} · ${formatCurrency(props.payload.value)}`,
                name,
              ]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <ul className="mt-2 space-y-1">
        {allocation.map((a) => (
          <li key={a.name} className="flex items-center justify-between text-[11px]">
            <span className="flex items-center gap-2 text-gray-700">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ backgroundColor: a.color }}
                aria-hidden="true"
              />
              {a.name}
            </span>
            <span className="font-medium text-gray-600">{formatPercent(a.percent)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
