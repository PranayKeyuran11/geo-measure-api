import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SQUARE = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
HOLE = [[0.25, 0.25], [0.75, 0.25], [0.75, 0.75], [0.25, 0.75], [0.25, 0.25]]


def upload(payload, name="test.geojson"):
    body = payload if isinstance(payload, str) else json.dumps(payload)
    return client.post("/measure", files={"file": (name, body, "application/json")})


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_polygon_area_and_bbox():
    r = upload({"type": "Polygon", "coordinates": [SQUARE]})
    assert r.status_code == 200
    feat = r.json()["features"][0]
    assert 12_000e6 < feat["measurements"]["area_m2"] < 12_500e6
    assert feat["measurements"]["perimeter_m"] > 400_000
    assert feat["bbox"] == [0.0, 0.0, 1.0, 1.0]


def test_polygon_hole_reduces_area():
    solid = upload({"type": "Polygon", "coordinates": [SQUARE]}).json()
    holed = upload({"type": "Polygon", "coordinates": [SQUARE, HOLE]}).json()
    assert holed["total_area_m2"] < solid["total_area_m2"]


def test_linestring_length():
    r = upload({"type": "LineString", "coordinates": [[0, 0], [0, 1]]})
    length = r.json()["features"][0]["measurements"]["length_m"]
    assert 110_000 < length < 111_000


def test_feature_collection_summary():
    fc = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [SQUARE]}},
            {"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": [[0, 0], [0, 1]]}},
        ],
    }
    body = upload(fc).json()
    assert body["feature_count"] == 2
    assert body["total_length_m"] > 0


def test_invalid_json():
    assert upload("not json at all").status_code == 400


def test_wrong_extension():
    r = upload({"type": "Point", "coordinates": [0, 0]}, name="data.txt")
    assert r.status_code == 400


def test_unsupported_type():
    assert upload({"type": "Banana"}).status_code == 422


def test_out_of_range_coordinates():
    r = upload({"type": "Point", "coordinates": [500, 200]})
    assert r.status_code == 422


def test_missing_geometry():
    r = upload({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}}]})
    assert r.status_code == 422