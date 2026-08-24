import json
import os


class DataExtractor:
    def __init__(self, polygon_area):
        self.polygon = polygon_area

    def compile(self, capture_results, output_path):
        buildings_data = []
        for result in capture_results:
            building = result["building"]
            entry = building.to_dict()
            sat_path = result.get("satellite_photo")
            sv_path = result.get("streetview_photo")

            entry["photos"] = {
                "satellite": sat_path if (sat_path and os.path.exists(sat_path)) else "gak ada",
                "streetview": sv_path if (sv_path and os.path.exists(sv_path)) else "gak ada",
            }
            buildings_data.append(entry)

        data = {
            "polygon": self.polygon.to_dict(),
            "bounding_box": self.polygon.get_bounding_box(),
            "total_buildings": len(buildings_data),
            "buildings": buildings_data,
        }

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {output_path}")
        return data
