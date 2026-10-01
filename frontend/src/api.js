const BASE = "/api";

async function getJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Request to ${path} failed: ${res.status} ${body}`);
  }
  return res.json();
}

export const api = {
  listRegions: () => getJSON("/regions"),
  demandHistory: (baCode, hours) =>
    getJSON(`/demand-history/${encodeURIComponent(baCode)}?hours=${hours}`),
  regionComparison: (hours) => getJSON(`/region-comparison?hours=${hours}`),
  hourOfDayProfile: (baCode, hours) =>
    getJSON(`/hour-of-day/${encodeURIComponent(baCode)}?hours=${hours}`),
  refreshStatus: () => getJSON("/refresh-status"),
};
