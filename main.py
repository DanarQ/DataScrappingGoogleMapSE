import argparse
import os
import sys

from scraper.polygon import PolygonArea
from scraper.building_finder import BuildingFinder
from scraper.map_driver import MapDriver
from scraper.photo_capture import PhotoCapture
from scraper.data_extractor import DataExtractor


def main():
    parser = argparse.ArgumentParser(description="Google Maps Building Scraper")
    parser.add_argument(
        "--polygon", required=True,
        help="Path to JSON file with polygon coordinates [[lat, lng], ...]"
    )
    parser.add_argument(
        "--output", default="output",
        help="Output directory (default: output)"
    )
    parser.add_argument(
        "--zoom", type=int, default=None,
        help="Google Maps zoom level override for overview (default: auto-calculated from polygon area)"
    )
    parser.add_argument(
        "--delay", type=float, default=2,
        help="Delay before taking screenshot in seconds (default: 2)"
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="Run browser in visible mode (for debugging)"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("Google Maps Building Scraper (Overview & JSON)")
    print("=" * 50)

    polygon = PolygonArea.from_file(args.polygon)
    print(f"\nPolygon loaded: {len(polygon.coordinates)} points")
    bbox = polygon.get_bounding_box()
    print(f"Center: {bbox['center_lat']:.4f}, {bbox['center_lng']:.4f}")

    finder = BuildingFinder(polygon)
    buildings = finder.find_buildings()

    if not buildings:
        print("No buildings found in the specified area.")
        sys.exit(0)

    os.makedirs(args.output, exist_ok=True)

    with MapDriver(headless=not args.no_headless) as driver:
        capture = PhotoCapture(driver, delay=args.delay, zoom=args.zoom)
        results = capture.capture_overview(polygon, buildings, args.output)

    extractor = DataExtractor(polygon)
    output_path = os.path.join(args.output, "results.json")
    data = extractor.compile(results, output_path)

    print(f"\n{'=' * 50}")
    print(f"Done! Total buildings: {data['total_buildings']}")
    print(f"Overview Map: {data['overview_photo']}")
    print(f"Results: {output_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
