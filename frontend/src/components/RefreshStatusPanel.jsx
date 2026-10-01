function timeAgo(iso) {
  if (!iso) return "never";
  const diffMs = Date.now() - new Date(iso + "Z").getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export default function RefreshStatusPanel({ data }) {
  if (!data || data.length === 0) {
    return <p className="empty">No refresh data yet — run the ETL to pull from the live EIA API.</p>;
  }

  return (
    <table className="status-table">
      <thead>
        <tr>
          <th>Region</th>
          <th>Latest hour on record</th>
          <th>Last pulled</th>
          <th>Rows stored</th>
        </tr>
      </thead>
      <tbody>
        {data.map((r) => (
          <tr key={r.ba_code}>
            <td>{r.name}</td>
            <td>{r.latest_period ? `${r.latest_period.replace("T", " ")} UTC` : "—"}</td>
            <td>{timeAgo(r.last_fetched_at)}</td>
            <td>{r.row_count.toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
