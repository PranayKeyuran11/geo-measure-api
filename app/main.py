import json
import os
from pathlib import Path
from time import time
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.geo import GeoJSONError, measure_geojson
from app.storage import count_measurements, list_measurements, save_measurement

MAX_BYTES = 5 * 1024 * 1024  # 5 MB

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Geospatial File Measurement API",
    description="Upload a GeoJSON file or submit a JSON payload and get area, perimeter, length, and bounding box per feature (geodesic, WGS84).",
    version="1.0.0",
)

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.state.started_at = time()
app.state.request_count = 0
app.state.measurement_count = 0
app.state.total_response_time = 0.0


def require_api_key(request: Request):
    configured_key = os.getenv("API_KEY")
    if not configured_key:
        return

    provided = request.headers.get("X-API-Key")
    if not provided:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            provided = auth_header[7:]

    if provided != configured_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


@app.middleware("http")
async def request_metrics(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    app.state.request_count += 1
    started = time()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    elapsed = time() - started
    app.state.total_response_time += elapsed
    return response


@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="/ui")

    return {
        "title": app.title,
        "description": app.description,
        "version": app.version,
        "health": "/health",
        "status": "/status",
        "metrics": "/metrics",
        "history": "/history",
        "docs": "/docs",
        "measure": "/measure",
        "batch_measure": "/measure/batch",
        "ui": "/ui",
        "max_upload_size_mb": MAX_BYTES // (1024 * 1024),
    }


@app.get("/ui")
def ui():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health(request: Request):
    require_api_key(request)
    return {
        "status": "ok",
        "service": "geo-measure-api",
        "version": app.version,
        "uptime_seconds": round(time() - app.state.started_at, 2),
        "request_count": app.state.request_count,
        "request_id": getattr(request.state, "request_id", None),
    }


@app.get("/summary")
def summary(request: Request):
    require_api_key(request)
    return {
        "service": "geo-measure-api",
        "version": app.version,
        "status": "ok",
        "uptime_seconds": round(time() - app.state.started_at, 2),
        "request_count": app.state.request_count,
        "measurement_count": app.state.measurement_count,
        "history_count": count_measurements(),
        "features": {
            "upload": True,
            "json_payload": True,
            "batch_processing": True,
            "history": True,
            "ui": True,
        },
    }


@app.get("/status")
def status(request: Request):
    require_api_key(request)
    return health(request)


@app.get("/metrics")
def metrics(request: Request):
    require_api_key(request)
    total_requests = app.state.request_count
    avg_latency_ms = (app.state.total_response_time / total_requests * 1000) if total_requests else 0.0
    return {
        "service": "geo-measure-api",
        "version": app.version,
        "uptime_seconds": round(time() - app.state.started_at, 2),
        "request_count": total_requests,
        "measurement_count": app.state.measurement_count,
        "average_response_time_ms": round(avg_latency_ms, 3),
    }


@app.get("/history")
def history(request: Request, limit: int = 20):
    require_api_key(request)
    return {
        "total": count_measurements(),
        "limit": max(1, min(limit, 100)),
        "items": list_measurements(limit=max(1, min(limit, 100))),
    }


@app.get("/export")
def export_records(request: Request, format: str = "csv", limit: int = 100):
    require_api_key(request)
    items = list_measurements(limit=max(1, min(limit, 1000)))

    if format.lower() == "json":
        return {"total": len(items), "items": items}

    headers = [
        "id",
        "created_at",
        "feature_count",
        "total_area_m2",
        "total_length_m",
        "bbox",
    ]
    rows = []
    for item in items:
        result = item["result"]
        rows.append(
            [
                str(item["id"]),
                item["created_at"],
                str(result.get("feature_count", 0)),
                str(result.get("total_area_m2", 0)),
                str(result.get("total_length_m", 0)),
                json.dumps(result.get("bbox", [])),
            ]
        )

    csv_lines = [",".join(headers)]
    csv_lines.extend(",".join(row) for row in rows)
    csv_text = "\n".join(csv_lines)
    return Response(content=csv_text, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=geo-measurements.csv"})


def _parse_geojson_payload(raw: bytes):
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 5 MB).")

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        raise HTTPException(400, "Request body is not valid JSON.")


async def _run_measurement(request: Request, data):
    require_api_key(request)

    try:
        result = measure_geojson(data)
        app.state.measurement_count += 1
        save_measurement(data, result)
        return result
    except GeoJSONError as exc:
        raise HTTPException(422, str(exc))


@app.post("/measure")
async def measure(request: Request, file: UploadFile | None = File(default=None)):
    if file is not None:
        name = (file.filename or "").lower()
        if not name.endswith((".geojson", ".json")):
            raise HTTPException(400, "Only .geojson or .json files are supported.")

        raw = await file.read(MAX_BYTES + 1)
        data = _parse_geojson_payload(raw)
    else:
        raw = await request.body()
        if not raw:
            raise HTTPException(400, "Request body is empty. Send GeoJSON JSON or upload a file.")
        data = _parse_geojson_payload(raw)

    return await _run_measurement(request, data)


@app.post("/measure/batch")
async def measure_batch(request: Request):
    require_api_key(request)
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Request body is empty. Send a list of GeoJSON objects.")

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        raise HTTPException(400, "Request body is not valid JSON.")

    if not isinstance(payload, list):
        raise HTTPException(400, "Batch requests must be a JSON array of GeoJSON objects.")
    if not payload:
        raise HTTPException(400, "Batch requests cannot be empty.")

    results = []
    for item in payload:
        if not isinstance(item, dict):
            raise HTTPException(422, "Each batch item must be a GeoJSON object.")
        results.append(await _run_measurement(request, item))

    return results