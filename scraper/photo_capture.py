import os
import time


class PhotoCapture:
    def __init__(self, driver, delay=2, zoom=18):
        self.driver = driver
        self.delay = delay
        self.zoom = zoom

    def capture_satellite(self, building, output_dir):
        filepath = os.path.join(output_dir, f"building_{building.osm_id}.png")
        self.driver.go_to_coordinates(building.lat, building.lng, self.zoom)
        self.driver.switch_to_satellite()
        time.sleep(self.delay)
        self.driver.take_screenshot(filepath)
        return filepath

    def capture_streetview(self, building, output_dir):
        filepath = os.path.join(output_dir, f"building_{building.osm_id}.png")
        self.driver.go_to_street_view(building.lat, building.lng)
        time.sleep(self.delay)
        if self.driver.has_street_view():
            self.driver.take_screenshot(filepath)
            return filepath
        print(f"  No Street View available for building {building.osm_id}")
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
