import os
import time


class PhotoCapture:
    def __init__(self, driver, delay=2, zoom=None):
        self.driver = driver
        self.delay = delay
        self.zoom = zoom

    def capture_overview(self, polygon, buildings, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        overview_file = os.path.join(output_dir, "overview_satellite.png")
        overview_path = None

        if polygon:
            try:
                b_count = len(buildings) if buildings else 0
                print(f"\n[Overview] Capturing Consolidated Satellite Map (Polygon Boundary + {b_count} buildings)...")
                overview_path = self.driver.capture_overview(
                    polygon, buildings or [], overview_file, zoom=self.zoom
                )
                time.sleep(self.delay)
            except Exception as e:
                print(f"  Overview capture error: {e}")
                overview_path = None

        return {
            "overview_photo": overview_path,
            "buildings": buildings,
        }
