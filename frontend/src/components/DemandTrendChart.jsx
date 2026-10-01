import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

function formatTick(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit" });
}

export default function DemandTrendChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="empty">Select a region to see its demand history.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="period_start" tickFormatter={formatTick} tick={{ fontSize: 11 }} minTickGap={40} />
        <YAxis tick={{ fontSize: 11 }} label={{ value: "MW", angle: -90, position: "insideLeft", fontSize: 11 }} />
        <Tooltip labelFormatter={formatTick} />
        <Legend />
        <Line
          type="monotone"
          dataKey="demand_mwh"
          name="Demand (MW)"
          stroke="#2563eb"
          dot={false}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
