import json
import os


class DataExtractor:
    def __init__(self, polygon_area):
        self.polygon = polygon_area

    def compile(self, capture_results, output_path):
        overview_photo = None
        buildings = []

        if isinstance(capture_results, dict):
            overview_photo = capture_results.get("overview_photo")
            buildings = capture_results.get("buildings", [])
        else:
            buildings = capture_results

        buildings_data = []
        for idx, item in enumerate(buildings, 1):
            if hasattr(item, "to_dict"):
                building_dict = item.to_dict()
            elif isinstance(item, dict) and "building" in item and hasattr(item["building"], "to_dict"):
                building_dict = item["building"].to_dict()
            elif isinstance(item, dict):
                building_dict = item
            else:
                building_dict = {}

            entry = {
                "index": idx,
                **building_dict,
            }
            buildings_data.append(entry)

        data = {
            "polygon": self.polygon.to_dict(),
            "bounding_box": self.polygon.get_bounding_box(),
            "overview_photo": overview_photo if (overview_photo and os.path.exists(overview_photo)) else "gak ada",
            "total_buildings": len(buildings_data),
            "buildings": buildings_data,
        }

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {output_path}")
        return data
