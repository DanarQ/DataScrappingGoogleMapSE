import os
import time


class PhotoCapture:
    def __init__(self, driver, delay=2, zoom=20):
        self.driver = driver
        self.delay = delay
        self.zoom = zoom

    def capture_satellite(self, building, output_dir):
        filepath = os.path.join(output_dir, f"building_{building.osm_id}.png")
        try:
            self.driver.go_to_satellite(building.lat, building.lng, self.zoom)
            time.sleep(self.delay)
            self.driver.take_screenshot(filepath)
            if os.path.exists(filepath) and os.path.getsize(filepath) > 10000:
                return filepath
            else:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return None
        except Exception as e:
            print(f"  Satellite capture error: {e}")
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            return None

    def capture_streetview(self, building, output_dir):
        filepath = os.path.join(output_dir, f"building_{building.osm_id}.png")
        try:
            self.driver.go_to_street_view(building.lat, building.lng)
            time.sleep(self.delay)
            if self.driver.has_street_view(temp_filepath=filepath):
                return filepath
            print(f"  No Street View available for building {building.osm_id}")
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            return None
        except Exception as e:
            print(f"  Street View capture error: {e}")
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            return None

    def capture_all(self, buildings, output_dir):
        sat_dir = os.path.join(output_dir, "photos", "satellite")
        sv_dir = os.path.join(output_dir, "photos", "streetview")
        os.makedirs(sat_dir, exist_ok=True)
        os.makedirs(sv_dir, exist_ok=True)

        total = len(buildings)
        results = []
        for i, building in enumerate(buildings, 1):
            print(f"\n[{i}/{total}] Building {building.osm_id} ({building.lat}, {building.lng})")
            sat_path = self.capture_satellite(building, sat_dir)
            time.sleep(self.delay)
            sv_path = self.capture_streetview(building, sv_dir)
            time.sleep(self.delay)
            results.append({
                "building": building,
                "satellite_photo": sat_path,
                "streetview_photo": sv_path,
            })
        return results
