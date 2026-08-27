import requests


class Building:
    def __init__(self, osm_id, lat, lng, building_type=None, address=None, outline=None):
        self.osm_id = osm_id
        self.lat = lat
        self.lng = lng
        self.building_type = building_type
        self.address = address
        self.outline = outline or []

    def to_dict(self):
        return {
            "id": f"osm_{self.osm_id}",
            "lat": self.lat,
            "lng": self.lng,
            "building_type": self.building_type,
            "address": self.address,
            "polygon": self.outline,
        }


from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


class BuildingFinder:
    OVERPASS_ENDPOINTS = [
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    ]

    def __init__(self, polygon_area):
        self.polygon = polygon_area
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def find_buildings(self):
        bbox = self.polygon.get_bounding_box()
        query = (
            f'[out:json][timeout:60];'
            f'('
            f'way["building"]({bbox["min_lat"]},{bbox["min_lng"]},{bbox["max_lat"]},{bbox["max_lng"]});'
            f'relation["building"]({bbox["min_lat"]},{bbox["min_lng"]},{bbox["max_lat"]},{bbox["max_lng"]});'
            f');'
            f'out center geom;'
        )
        print("Querying Overpass API for buildings...")
        
        data = None
        last_err = None
        for endpoint in self.OVERPASS_ENDPOINTS:
            try:
                print(f"Trying Overpass endpoint: {endpoint}")
                resp = self.session.post(
                    endpoint,
                    data={"data": query},
                    timeout=60,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    break
                else:
                    print(f"Endpoint {endpoint} returned status {resp.status_code}")
            except Exception as e:
                print(f"Endpoint {endpoint} failed: {e}")
                last_err = e

        if not data:
            raise RuntimeError(f"All Overpass API endpoints failed. Last error: {last_err}")

        buildings = []
        for element in data.get("elements", []):
            b = self._parse_element(element)
            if b:
                # Check if building center is inside or if any outline point is inside
                is_in = self._is_inside_polygon(b.lat, b.lng)
                if not is_in and b.outline:
                    is_in = any(self._is_inside_polygon(p[0], p[1]) for p in b.outline)
                if is_in:
                    buildings.append(b)
        print(f"Found {len(buildings)} buildings inside polygon")
        return buildings

    def _is_inside_polygon(self, lat, lng):
        coords = self.polygon.coordinates
        pts = coords[:-1] if (len(coords) > 1 and coords[0] == coords[-1]) else coords
        n = len(pts)
        if n < 3:
            return False
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
        return inside

    def _parse_element(self, element):
        tags = element.get("tags", {})
        building_type = tags.get("building", None)
        if building_type == "yes":
            building_type = None
        if "addr:full" in tags:
            address = tags["addr:full"]
        else:
            address_parts = []
            for key in ["addr:street", "addr:housenumber", "addr:suburb", "addr:city"]:
                if key in tags:
                    address_parts.append(tags[key])
            address = ", ".join(address_parts) if address_parts else None

        outline = []
        lat = None
        lng = None

        # 1. Extract outline geometry if available
        if "geometry" in element and element["geometry"]:
            outline = [(n["lat"], n["lon"]) for n in element["geometry"]]
            lat = sum(p[0] for p in outline) / len(outline)
            lng = sum(p[1] for p in outline) / len(outline)

        # 2. Extract center or bounds fallback
        if lat is None or lng is None:
            if "center" in element and element["center"]:
                lat = element["center"].get("lat")
                lng = element["center"].get("lon")
            elif "bounds" in element and element["bounds"]:
                b = element["bounds"]
                lat = (b.get("minlat", 0) + b.get("maxlat", 0)) / 2
                lng = (b.get("minlon", 0) + b.get("maxlon", 0)) / 2
            elif "lat" in element and "lon" in element:
                lat = element.get("lat")
                lng = element.get("lon")

        if lat is None or lng is None:
            return None

        return Building(
            osm_id=element["id"],
            lat=lat,
            lng=lng,
            building_type=building_type,
            address=address,
            outline=outline,
        )
