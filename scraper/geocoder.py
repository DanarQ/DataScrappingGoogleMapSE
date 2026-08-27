import time
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


class ReverseGeocoder:
    BASE_URL = "https://nominatim.openstreetmap.org/reverse"

    def __init__(self, delay=1.0, user_agent="GoogleMapsBuildingScraper/1.0"):
        self.delay = delay
        self.user_agent = user_agent
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._cache = {}

    def reverse_geocode(self, lat, lng):
        # Cache by coordinate rounded to 4 decimals (~11m radius) to avoid duplicate lookups
        cache_key = (round(lat, 4), round(lng, 4))
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            params = {
                "lat": lat,
                "lon": lng,
                "format": "json",
                "addressdetails": 1,
                "zoom": 18,
            }
            headers = {
                "User-Agent": self.user_agent,
            }
            response = self.session.get(self.BASE_URL, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                display_name = data.get("display_name")
                self._cache[cache_key] = display_name
                time.sleep(self.delay)
                return display_name
        except Exception as e:
            print(f"    Geocoding error at ({lat}, {lng}): {e}")

        return None

    def geocode_buildings(self, buildings):
        print(f"\nReverse geocoding addresses for {len(buildings)} buildings...")
        total = len(buildings)
        for i, b in enumerate(buildings, 1):
            if not b.address:
                print(f"  [{i}/{total}] Geocoding #{i} ({b.lat:.6f}, {b.lng:.6f})...", end="", flush=True)
                addr = self.reverse_geocode(b.lat, b.lng)
                if addr:
                    b.address = addr
                    print(f" -> {addr[:60]}...")
                else:
                    print(" -> Tidak ditemukan")
            else:
                print(f"  [{i}/{total}] Address already present in OSM: {b.address}")
        return buildings

