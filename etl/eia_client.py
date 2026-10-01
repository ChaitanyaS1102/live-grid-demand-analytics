"""
Thin HTTP client for EIA's v2 Open Data API, scoped to the one series
this project needs: hourly electricity demand by balancing authority
(electricity/rto/region-data).

Get a free API key at https://www.eia.gov/opendata/register.php and
set it as the EIA_API_KEY environment variable.
"""

import logging
import os
import time
from datetime import datetime
from typing import Iterable, List

import requests

log = logging.getLogger(__name__)

EIA_BASE_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
PAGE_SIZE = 5000  # EIA's per-request row cap for this endpoint
MAX_RETRIES = 3


def _api_key() -> str:
    key = os.environ.get("EIA_API_KEY")
    if not key:
        raise RuntimeError(
            "EIA_API_KEY is not set. Get a free key at "
            "https://www.eia.gov/opendata/register.php and export it."
        )
    return key


def fetch_hourly_demand(
    ba_codes: Iterable[str],
    start: datetime,
    end: datetime,
) -> List[dict]:
    """Fetch hourly demand ('type' == 'D') rows for the given BAs and
    UTC time range, handling EIA's offset-based pagination.

    Returns the raw list of row dicts exactly as EIA sends them
    (period / respondent / respondent-name / type / value / value-units) --
    normalization into our schema happens in etl/transform.py, kept
    separate so this client has no DB or business-logic concerns.
    """
    all_rows: List[dict] = []
    offset = 0

    while True:
        params = {
            "api_key": _api_key(),
            "frequency": "hourly",
            "data[0]": "value",
            "facets[type][]": "D",
            # requests repeats a list-valued param under the same key, which
            # is what EIA expects for multi-value facets
            # (facets[respondent][]=NYIS&facets[respondent][]=PJM&...).
            "facets[respondent][]": list(ba_codes),
            "start": start.strftime("%Y-%m-%dT%H"),
            "end": end.strftime("%Y-%m-%dT%H"),
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": offset,
            "length": PAGE_SIZE,
        }

        rows = _get_with_retries(params)
        all_rows.extend(rows)

        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return all_rows


def _get_with_retries(params: dict) -> List[dict]:
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(EIA_BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("response", {}).get("data", [])
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            wait = 2 ** attempt
            log.warning("EIA API request failed (attempt %s/%s): %s. Retrying in %ss.", attempt, MAX_RETRIES, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"EIA API request failed after {MAX_RETRIES} attempts: {last_exc}")
