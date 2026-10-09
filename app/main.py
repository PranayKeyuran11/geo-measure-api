import json

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.geo import GeoJSONError, measure_geojson

MAX_BYTES = 5 * 1024 * 1024  # 5 MB

app = FastAPI(
    title="Geospatial File Measurement API",
    description="Upload a GeoJSON file and get area, perimeter, length and bounding box per feature (geodesic, WGS84).",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/measure")
async def measure(file: UploadFile = File(...)):
    name = (file.filename or "").lower()
    if not name.endswith((".geojson", ".json")):
        raise HTTPException(400, "Only .geojson or .json files are supported.")

    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 5 MB).")

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(400, "File is not valid JSON.")

    try:
        return measure_geojson(data)
    except GeoJSONError as exc:
        raise HTTPException(422, str(exc))