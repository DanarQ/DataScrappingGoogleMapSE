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
            if b and self._is_inside_polygon(b.lat, b.lng):
                buildings.append(b)
        print(f"Found {len(buildings)} buildings inside polygon")
        return buildings

    def _is_inside_polygon(self, lat, lng):
        coords = self.polygon.coordinates
        n = len(coords)
        inside = False
        j = n - 1
        for i in range(n):
            lat_i, lng_i = coords[i]
            lat_j, lng_j = coords[j]
            if ((lat_i > lat) != (lat_j > lat)) and (
                lng < (lng_j - lng_i) * (lat - lat_i) / (lat_j - lat_i) + lng_i
            ):
                inside = not inside
            j = i
        return inside

    def _parse_element(self, element):
        etype = element.get("type")
        tags = element.get("tags", {})
        building_type = tags.get("building", None)
        if building_type == "yes":
            building_type = None
        address_parts = []
        for key in ["addr:street", "addr:housenumber", "addr:city", "addr:suburb"]:
            if key in tags:
                address_parts.append(tags[key])
        address = ", ".join(address_parts) if address_parts else None

        if etype == "way":
            center = element.get("center", {})
            lat = center.get("lat")
            lng = center.get("lon")
            if lat is None or lng is None:
                return None
            geometry = element.get("geometry", [])
            outline = [(n["lat"], n["lon"]) for n in geometry]
        elif etype == "relation":
            center = element.get("center", {})
            lat = center.get("lat")
            lng = center.get("lon")
            if lat is None or lng is None:
                return None
            outline = []
        else:
            lat = element.get("lat")
            lng = element.get("lon")
            if lat is None or lng is None:
                return None
            outline = []

        return Building(
            osm_id=element["id"],
            lat=lat,
            lng=lng,
            building_type=building_type,
            address=address,
            outline=outline,
        )
