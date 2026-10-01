import { useEffect, useState } from "react";
import { api } from "./api.js";
import DemandTrendChart from "./components/DemandTrendChart.jsx";
import RegionComparisonChart from "./components/RegionComparisonChart.jsx";
import HourOfDayChart from "./components/HourOfDayChart.jsx";
import RefreshStatusPanel from "./components/RefreshStatusPanel.jsx";
import DataQualityNotes from "./components/DataQualityNotes.jsx";

const WINDOW_OPTIONS = [
  { value: 24, label: "Last 24 hours" },
  { value: 168, label: "Last 7 days" },
  { value: 720, label: "Last 30 days" },
];

export default function App() {
  const [regions, setRegions] = useState([]);
  const [selectedBa, setSelectedBa] = useState("");
  const [windowHours, setWindowHours] = useState(168);

  const [demandHistory, setDemandHistory] = useState([]);
  const [regionComparison, setRegionComparison] = useState([]);
  const [hourOfDay, setHourOfDay] = useState([]);
  const [refreshStatus, setRefreshStatus] = useState([]);

  const [error, setError] = useState(null);
  const [regionsLoading, setRegionsLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [comparisonLoading, setComparisonLoading] = useState(true);

  // Load regions + refresh status once on mount
  useEffect(() => {
    setError(null);
    api
      .listRegions()
      .then((rs) => {
        setRegions(rs);
        if (rs.length > 0) setSelectedBa(rs[0].code);
      })
      .catch((e) => setError(e.message))
      .finally(() => setRegionsLoading(false));

    api.refreshStatus().then(setRefreshStatus).catch((e) => setError(e.message));
  }, []);

  // Load region comparison whenever the time window changes
  useEffect(() => {
    setComparisonLoading(true);
    api
      .regionComparison(windowHours)
      .then(setRegionComparison)
      .catch((e) => setError(e.message))
      .finally(() => setComparisonLoading(false));
  }, [windowHours]);

  // Load demand history + hour-of-day profile whenever region/window changes
  useEffect(() => {
    if (!selectedBa) return;
    setHistoryLoading(true);
    Promise.all([
      api.demandHistory(selectedBa, windowHours).then(setDemandHistory),
      api.hourOfDayProfile(selectedBa, Math.max(windowHours, 336)).then(setHourOfDay),
    ])
      .catch((e) => setError(e.message))
      .finally(() => setHistoryLoading(false));
  }, [selectedBa, windowHours]);

  const selectedRegion = regions.find((r) => r.code === selectedBa);

  return (
    <div className="app">
      <header>
        <h1>Energy Grid Intelligence</h1>
        <p className="subtitle">
          Hourly electricity demand by US grid region, pulled live from EIA's
          Open Data API (NYISO, PJM, CAISO, ERCOT)
        </p>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="controls">
        <label>
          Region
          <select
            value={selectedBa}
            onChange={(e) => setSelectedBa(e.target.value)}
            disabled={regionsLoading}
          >
            {regionsLoading && <option value="">Loading regions...</option>}
            {regions.map((r) => (
              <option key={r.code} value={r.code}>
                {r.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Time window
          <select value={windowHours} onChange={(e) => setWindowHours(Number(e.target.value))}>
            {WINDOW_OPTIONS.map((w) => (
              <option key={w.value} value={w.value}>
                {w.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="panel">
        <h2>Demand history{selectedRegion ? `: ${selectedRegion.name}` : ""}</h2>
        {historyLoading ? (
          <p className="loading">Loading demand history…</p>
        ) : (
          <DemandTrendChart data={demandHistory} />
        )}
      </section>

      <section className="panel-row">
        <div className="panel">
          <h2>Region comparison</h2>
          {comparisonLoading ? (
            <p className="loading">Loading…</p>
          ) : (
            <RegionComparisonChart data={regionComparison} />
          )}
        </div>

        <div className="panel">
          <h2>Daily load curve{selectedRegion ? `: ${selectedRegion.name}` : ""}</h2>
          {historyLoading ? (
            <p className="loading">Loading…</p>
          ) : (
            <HourOfDayChart data={hourOfDay} />
          )}
        </div>
      </section>

      <section className="panel">
        <h2>Data freshness</h2>
        <RefreshStatusPanel data={refreshStatus} />
      </section>

      <DataQualityNotes />
    </div>
  );
}
