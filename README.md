# Geo Measure API

A production-style geospatial measurement service for analyzing GeoJSON data with geodesic calculations on the WGS84 ellipsoid.

## Why this project stands out

This project combines a strong backend, browser-based interface, validation, metrics, and deployment-ready structure into a compact but professional solution. It is designed to showcase practical API engineering, geospatial processing, and product-minded design.

## Core features

- Upload GeoJSON files or submit raw JSON payloads
- Measure polygon area, line length, perimeter, and bounding box
- Support FeatureCollection, Feature, and raw geometry inputs
- Summarize total area and aggregate metrics across features
- Secure optional API key enforcement
- Batch measurement endpoint for multi-item processing
- SQLite-backed request history for auditing and debugging
- Browser UI for direct interaction and demo use
- Health checks, metrics, and deployable Docker configuration

## Project architecture

- Backend: FastAPI
- Geospatial math: pyproj + shapely
- Persistence: SQLite
- Frontend: lightweight HTML/CSS/JavaScript
- Containerization: Docker
- Validation: pytest

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Optional environment variables:

```bash
cp .env.example .env
source .env
```

## API usage

### Upload a GeoJSON file

```bash
curl -X POST "http://localhost:8000/measure" \
  -F "file=@sample_data/sample.geojson"
```

### Send JSON directly

```bash
curl -X POST "http://localhost:8000/measure" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "Polygon",
    "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]
  }'
```

### Batch measurement

```bash
curl -X POST "http://localhost:8000/measure/batch" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '[
    {"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]},
    {"type":"LineString","coordinates":[[0,0],[0,1]]}
  ]'
```

### Health and summary endpoints

```bash
curl http://localhost:8000/health
curl http://localhost:8000/summary
curl http://localhost:8000/metrics
```

## Browser UI

Visit:

- http://localhost:8000/
- http://localhost:8000/ui

The UI lets you upload a GeoJSON file and inspect results in a local dashboard.

## Docker

```bash
docker build -t geo-measure-api .
docker run -p 8000:8000 geo-measure-api
```

## Testing

```bash
pytest -q
```

## Project status

This is a reliable, scale-ready API with a useful frontend, production patterns, and clear extensibility for future enhancements such as map visualization, exports, authentication layers, and cloud deployment.
