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


class BuildingFinder:
    OVERPASS_URL = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"

    def __init__(self, polygon_area):
        self.polygon = polygon_area

    def find_buildings(self):
        bbox = self.polygon.get_bounding_box()
        query = (
            f'[out:json][timeout:120];'
            f'('
            f'way["building"]({bbox["min_lat"]},{bbox["min_lng"]},{bbox["max_lat"]},{bbox["max_lng"]});'
            f'relation["building"]({bbox["min_lat"]},{bbox["min_lng"]},{bbox["max_lat"]},{bbox["max_lng"]});'
            f');'
            f'out center body;'
        )
        print(f"Querying Overpass API for buildings...")
        resp = requests.post(
            self.OVERPASS_URL,
            data={"data": query},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        buildings = []
        for element in data.get("elements", []):
            b = self._parse_element(element)
            if b and self._is_inside_polygon(b.lat, b.lng):
                buildings.append(b)
        print(f"Found {len(buildings)} buildings")
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
