import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function HourOfDayChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="empty">Select a region to see its daily load curve.</p>;
  }

  const chartData = data.map((d) => ({
    hour: `${String(d.hour_of_day).padStart(2, "0")}:00`,
    "Avg demand (MW)": d.avg_demand_mwh,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Line type="monotone" dataKey="Avg demand (MW)" stroke="#16a34a" dot={{ r: 2 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
