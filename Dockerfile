# Backend image: runs the ETL refresh and/or the FastAPI service.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY etl/ etl/
COPY api/ api/

ENV DB_PATH=/data/energy_grid.db
VOLUME ["/data"]

EXPOSE 8000

# Default: run the API. Override the command to run the ETL instead, e.g.:
#   docker run <image> python -m etl.run --backfill-days 90
#   docker run <image> python -m etl.run --incremental
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
