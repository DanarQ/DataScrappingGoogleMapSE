import json


class PolygonArea:
    def __init__(self, coordinates):
        self.coordinates = [tuple(c) for c in coordinates]
        self.validate()

    def validate(self):
        if len(self.coordinates) < 3:
            raise ValueError("Polygon needs at least 3 coordinate points")
        for lat, lng in self.coordinates:
            if not (-90 <= lat <= 90):
                raise ValueError(f"Invalid latitude: {lat}")
            if not (-180 <= lng <= 180):
                raise ValueError(f"Invalid longitude: {lng}")
        if self.coordinates[0] != self.coordinates[-1]:
            self.coordinates.append(self.coordinates[0])

    def get_bounding_box(self):
        lats = [c[0] for c in self.coordinates]
        lngs = [c[1] for c in self.coordinates]
        return {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lng": min(lngs),
            "max_lng": max(lngs),
            "center_lat": (min(lats) + max(lats)) / 2,
            "center_lng": (min(lngs) + max(lngs)) / 2,
        }

    def to_overpass_polygon(self):
        pairs = [f"{lat} {lng}" for lat, lng in self.coordinates]
        return " ".join(pairs)

    def to_overpass_query(self):
        poly = self.to_overpass_polygon()
        return f"""
        [out:json][timeout:60];
        (
          way["building"]({poly});
          relation["building"]({poly});
        );
        out center body;
        """

    def to_geojson(self):
        return {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[lng, lat] for lat, lng in self.coordinates]
                ],
            },
        }

    def to_dict(self):
        return [[lat, lng] for lat, lng in self.coordinates]

    @classmethod
    def from_file(cls, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls(data)
