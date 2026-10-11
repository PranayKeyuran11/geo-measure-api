# Geo Measure API

A FastAPI service for measuring GeoJSON features with geodesic calculations on WGS84 coordinates.

## Features

- Accepts GeoJSON uploads or raw JSON payloads
- Measures polygon area, line length, perimeter, and bounding box
- Supports FeatureCollection, Feature, and geometry objects
- Returns per-feature and aggregate totals
- Includes health checks and OpenAPI documentation
- Container-ready for Docker deployment

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
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

### Health check

```bash
curl http://localhost:8000/health
```

## Docker

```bash
docker build -t geo-measure-api .
docker run -p 8000:8000 geo-measure-api
```

The API is available at:

- http://localhost:8000/
- http://localhost:8000/docs
- http://localhost:8000/health
