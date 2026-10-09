from pyproj import Geod
from shapely.geometry import shape

GEOD = Geod(ellps="WGS84")

GEOMETRY_TYPES = {
    "Point", "MultiPoint", "LineString", "MultiLineString",
    "Polygon", "MultiPolygon", "GeometryCollection",
}


class GeoJSONError(ValueError):
    """Raised when the uploaded GeoJSON is invalid or unsupported."""


def _measure_parts(geom):
    """Return (area_m2, perimeter_m, length_m) for any shapely geometry."""
    if geom.is_empty or geom.geom_type in ("Point", "MultiPoint"):
        return 0.0, 0.0, 0.0
    if geom.geom_type == "LineString":
        return 0.0, 0.0, GEOD.geometry_length(geom)
    if geom.geom_type == "Polygon":
        area, perimeter = GEOD.geometry_area_perimeter(geom)
        return abs(area), perimeter, 0.0

    # Multi* types and GeometryCollection: sum the parts
    area = perimeter = length = 0.0
    for part in geom.geoms:
        a, p, l = _measure_parts(part)
        area += a
        perimeter += p
        length += l
    return area, perimeter, length


def _extract_features(data):
    if not isinstance(data, dict) or "type" not in data:
        raise GeoJSONError("Not a valid GeoJSON object: missing 'type'.")
    kind = data["type"]
    if kind == "FeatureCollection":
        features = data.get("features")
        if not isinstance(features, list):
            raise GeoJSONError("FeatureCollection must have a 'features' list.")
        return features
    if kind == "Feature":
        return [data]
    if kind in GEOMETRY_TYPES:
        return [{"type": "Feature", "properties": {}, "geometry": data}]
    raise GeoJSONError(f"Unsupported GeoJSON type: {kind!r}.")


def _measure_feature(feature, index):
    if not isinstance(feature, dict) or feature.get("geometry") is None:
        raise GeoJSONError(f"Feature {index}: missing geometry.")
    try:
        geom = shape(feature["geometry"])
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise GeoJSONError(f"Feature {index}: invalid geometry ({exc}).")
    if geom.is_empty:
        raise GeoJSONError(f"Feature {index}: geometry is empty.")

    minx, miny, maxx, maxy = geom.bounds
    if not (-180 <= minx and maxx <= 180 and -90 <= miny and maxy <= 90):
        raise GeoJSONError(
            f"Feature {index}: coordinates must be lon/lat within "
            "[-180, 180] and [-90, 90] (WGS84)."
        )

    area, perimeter, length = _measure_parts(geom)
    return {
        "id": feature.get("id", index),
        "geometry_type": geom.geom_type,
        "properties": feature.get("properties") or {},
        "measurements": {
            "area_m2": round(area, 3),
            "area_km2": round(area / 1e6, 6),
            "area_hectares": round(area / 1e4, 4),
            "perimeter_m": round(perimeter, 3),
            "length_m": round(length, 3),
            "length_km": round(length / 1000, 6),
        },
        "bbox": [minx, miny, maxx, maxy],
    }


def measure_geojson(data):
    features = [
        _measure_feature(f, i) for i, f in enumerate(_extract_features(data))
    ]
    if not features:
        raise GeoJSONError("No features found in file.")

    boxes = [f["bbox"] for f in features]
    return {
        "feature_count": len(features),
        "total_area_m2": round(sum(f["measurements"]["area_m2"] for f in features), 3),
        "total_length_m": round(sum(f["measurements"]["length_m"] for f in features), 3),
        "bbox": [
            min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes),
        ],
        "features": features,
    }