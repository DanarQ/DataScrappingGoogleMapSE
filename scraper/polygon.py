import json
from typing import List, Tuple, Dict, Any, Union, Optional


class PolygonArea:
    """
    Represents a geographic boundary polygon or multi-polygon.
    Coordinates are stored internally as [lat, lng].
    """

    def __init__(self, coordinates: Union[List[Tuple[float, float]], List[List[Tuple[float, float]]]], metadata: Optional[Dict[str, Any]] = None):
        self.metadata = metadata or {}
        
        # Check if coordinates is MultiPolygon (list of polygons) or Single Polygon
        if coordinates and isinstance(coordinates[0], (list, tuple)) and len(coordinates[0]) > 0 and isinstance(coordinates[0][0], (list, tuple)):
            # MultiPolygon: [[(lat, lng), ...], [(lat, lng), ...]]
            self.is_multi = True
            self.polygons = [[tuple(c) for c in poly] for poly in coordinates if len(poly) >= 3]
            # Primary coordinates points for backward compatibility
            self.coordinates = self.polygons[0] if self.polygons else []
        else:
            # Single Polygon: [(lat, lng), ...]
            self.is_multi = False
            poly = [tuple(c) for c in coordinates]
            self.polygons = [poly]
            self.coordinates = poly

        self.validate()

    def validate(self):
        if not self.polygons:
            raise ValueError("Polygon needs at least 1 valid polygon ring")

        fixed_polygons = []
        for poly in self.polygons:
            if len(poly) < 3:
                continue
            for lat, lng in poly:
                if not (-90 <= lat <= 90):
                    raise ValueError(f"Invalid latitude: {lat}")
                if not (-180 <= lng <= 180):
                    raise ValueError(f"Invalid longitude: {lng}")
            
            p_list = list(poly)
            if p_list[0] != p_list[-1]:
                p_list.append(p_list[0])
            fixed_polygons.append(p_list)

        self.polygons = fixed_polygons
        if not self.polygons:
            raise ValueError("No valid polygon rings with at least 3 points found")
        self.coordinates = self.polygons[0]

    def get_bounding_box(self) -> Dict[str, float]:
        lats = [c[0] for poly in self.polygons for c in poly]
        lngs = [c[1] for poly in self.polygons for c in poly]
        return {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lng": min(lngs),
            "max_lng": max(lngs),
            "center_lat": (min(lats) + max(lats)) / 2,
            "center_lng": (min(lngs) + max(lngs)) / 2,
        }

    def contains_point(self, lat: float, lng: float) -> bool:
        """Ray-casting algorithm supporting multi-polygons."""
        for poly in self.polygons:
            pts = poly[:-1] if (len(poly) > 1 and poly[0] == poly[-1]) else poly
            n = len(pts)
            if n < 3:
                continue
            inside = False
            j = n - 1
            for i in range(n):
                lat_i, lng_i = pts[i]
                lat_j, lng_j = pts[j]
                if ((lat_i > lat) != (lat_j > lat)) and (
                    lng < (lng_j - lng_i) * (lat - lat_i) / (lat_j - lat_i) + lng_i
                ):
                    inside = not inside
                j = i
            if inside:
                return True
        return False

    def to_overpass_polygon(self) -> str:
        # Overpass query uses the main polygon boundary
        pairs = [f"{lat} {lng}" for lat, lng in self.coordinates]
        return " ".join(pairs)

    def to_overpass_query(self) -> str:
        bbox = self.get_bounding_box()
        return f"""
        [out:json][timeout:60];
        (
          way["building"]({bbox["min_lat"]},{bbox["min_lng"]},{bbox["max_lat"]},{bbox["max_lng"]});
          relation["building"]({bbox["min_lat"]},{bbox["min_lng"]},{bbox["max_lat"]},{bbox["max_lng"]});
        );
        out center body;
        """

    def to_geojson(self) -> Dict[str, Any]:
        if self.is_multi or len(self.polygons) > 1:
            return {
                "type": "Feature",
                "properties": self.metadata,
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[[lng, lat] for lat, lng in poly]] for poly in self.polygons
                    ],
                },
            }
        else:
            return {
                "type": "Feature",
                "properties": self.metadata,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[lng, lat] for lat, lng in self.coordinates]
                    ],
                },
            }

    def to_dict(self) -> Union[List[List[float]], List[List[List[float]]]]:
        if self.is_multi or len(self.polygons) > 1:
            return [[[lat, lng] for lat, lng in poly] for poly in self.polygons]
        return [[lat, lng] for lat, lng in self.coordinates]

    @classmethod
    def from_file(cls, filepath: str) -> "PolygonArea":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Standard GeoJSON FeatureCollection or Feature
        if isinstance(data, dict):
            if data.get("type") == "FeatureCollection":
                features = data.get("features", [])
                if features:
                    return cls.from_geojson_feature(features[0])
            elif data.get("type") == "Feature":
                return cls.from_geojson_feature(data)
            elif "coordinates" in data and "geometry" not in data:
                # Raw list or custom dict
                return cls(data["coordinates"])

        # 2. Simple list of coordinates [[lat, lng], ...]
        return cls(data)

    @classmethod
    def from_geojson_feature(cls, feature: Union[Dict[str, Any], Any]) -> "PolygonArea":
        if hasattr(feature, "to_polygon_coordinates"):
            coords = feature.to_polygon_coordinates()
            meta = feature.get_metadata() if hasattr(feature, "get_metadata") else {}
            return cls(coords, metadata=meta)

        # Raw feature dict
        geometry = feature.get("geometry", {})
        properties = feature.get("properties", {})
        gtype = geometry.get("type", "")
        coords = geometry.get("coordinates", [])

        if gtype == "Polygon":
            poly_coords = [[p[1], p[0]] for p in coords[0]] if coords else []
            return cls(poly_coords, metadata=properties)
        elif gtype == "MultiPolygon":
            multi_coords = [[[p[1], p[0]] for p in poly[0]] for poly in coords if poly]
            return cls(multi_coords, metadata=properties)
        else:
            raise ValueError(f"Unsupported geometry type: {gtype}")
