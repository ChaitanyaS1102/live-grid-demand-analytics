const ISSUES = [
  {
    title: "EIA revises recently published hours after the fact",
    detail:
      "Utilities submit corrected meter reads after their initial filing, so " +
      "a demand value for a given region/hour that looked final yesterday can " +
      "change today. A naive insert-or-ignore loader (fine for a static, " +
      "one-time CSV import) would silently keep the stale first value forever.",
    fix:
      "The incremental refresh re-pulls a rolling 48h window every run and " +
      "upserts on (ba_code, period_start) with an on-conflict UPDATE, not " +
      "ignore, so a later, corrected value actually overwrites the earlier " +
      "one (etl/run.py::load_window).",
  },
  {
    title: "Missing hours come back as null, not zero",
    detail:
      'EIA returns value: null for an hour a respondent hasn’t reported yet ' +
      "(reporting lag, outage, etc.). Coercing that to 0.0 would read as " +
      '"zero demand," which is never actually true for a grid region and ' +
      "would silently distort any average.",
    fix:
      "Missing readings are stored as SQL NULL and rendered as gaps in the " +
      "trend chart rather than dips to zero (etl/transform.py::safe_float).",
  },
  {
    title: "Period timestamps have no explicit UTC offset in the raw API",
    detail:
      'EIA’s region-data endpoint returns period as "2026-09-30T14" with no ' +
      "timezone marker. The series is documented as already normalized to " +
      "UTC across all regions (so a Pacific-time BA and an Eastern-time BA " +
      "line up on the same clock) — but naively parsing it as each " +
      "respondent's local time would shift every non-UTC region's chart by " +
      "several hours relative to the others.",
    fix:
      "Parsed explicitly as UTC and tagged as such rather than left as a " +
      "naive/ambiguous timestamp (etl/transform.py::parse_period).",
  },
];

export default function DataQualityNotes() {
  return (
    <section className="panel">
      <h2>Data quality issues found</h2>
      <p className="dq-intro">
        Three real problems turned up building this live-refresh ETL —
        different in kind from a one-time CSV import, since the same hour
        can legitimately change value across refreshes. All three are
        handled in the ETL layer, not papered over in the frontend.
      </p>
      <div className="dq-list">
        {ISSUES.map((issue) => (
          <div className="dq-item" key={issue.title}>
            <h3>{issue.title}</h3>
            <p>{issue.detail}</p>
            <p className="dq-fix">
              <strong>Fix:</strong> {issue.fix}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
