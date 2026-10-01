import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function RegionComparisonChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="empty">No comparison data available yet.</p>;
  }

  const chartData = data.map((d) => ({
    label: d.name,
    "Avg demand (MW)": d.avg_demand_mwh ?? 0,
    "Peak demand (MW)": d.peak_demand_mwh ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} angle={-15} textAnchor="end" height={60} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        <Bar dataKey="Avg demand (MW)" fill="#2563eb" />
        <Bar dataKey="Peak demand (MW)" fill="#f59e0b" />
      </BarChart>
    </ResponsiveContainer>
  );
}
