import argparse
import os
import sys
import traceback
from typing import List, Tuple, Any

from scraper.polygon import PolygonArea
from scraper.building_finder import BuildingFinder
from scraper.geocoder import ReverseGeocoder
from scraper.map_driver import MapDriver
from scraper.photo_capture import PhotoCapture
from scraper.data_extractor import DataExtractor
from scraper.geojson_loader import GeoJSONLoader, parse_selection, interactive_select, SLSFeature


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Google Maps & Overpass Building Scraper with SLS GeoJSON Selection"
    )
    parser.add_argument(
        "--polygon", default=None,
        help="Path to GeoJSON file or JSON coordinate file"
    )
    parser.add_argument(
        "--polygon-area", dest="polygon_area", default=None,
        help="Index or range of SLS section to scrape (e.g. 2, 1,3,5, 1-10, all)"
    )
    parser.add_argument(
        "--idsls", default=None,
        help="Specific SLS ID to scrape (e.g. 61010100020001)"
    )
    parser.add_argument(
        "--output", default="output",
        help="Output root directory (default: output)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-scrape and overwrite existing results"
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="Launch interactive terminal wizard to select Kabupaten and SLS"
    )
    parser.add_argument(
        "--zoom", type=int, default=None,
        help="Google Maps zoom level override for overview (default: auto-calculated)"
    )
    parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Delay before taking screenshot in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="Run browser in visible mode (for debugging)"
    )
    parser.add_argument(
        "--no-geocode", action="store_true",
        help="Disable reverse geocoding of building addresses"
    )
    parser.add_argument(
        "--geocode-delay", type=float, default=1.0,
        help="Delay between reverse geocoding requests in seconds (default: 1.0)"
    )
    return parser.parse_args()


def load_target_items(args) -> Tuple[str, List[Any]]:
    """
    Determines which polygon items or SLS features to scrape.
    Returns (source_name, list_of_targets).
    """
    # 1. Interactive mode if explicitly requested or if no polygon provided
    if args.interactive or (not args.polygon and not args.idsls and not args.polygon_area):
        file_path, selected_sls = interactive_select()
        return file_path, selected_sls

    # 2. Polygon file path provided
    if args.polygon:
        filepath = args.polygon
        # If relative path and file doesn't exist, check inside DataGeoJson/
        if not os.path.exists(filepath):
            alt_path = os.path.join("DataGeoJson", filepath)
            if os.path.exists(alt_path):
                filepath = alt_path

        if not os.path.exists(filepath):
            print(f"Error: File tidak ditemukan: {args.polygon}")
            sys.exit(1)

        # Check if file is GeoJSON with features
        if filepath.lower().endswith(".geojson"):
            features = GeoJSONLoader.load_file(filepath)
            total_features = len(features)

            if args.idsls:
                matched = [f for f in features if f.idsls == str(args.idsls).strip()]
                if not matched:
                    print(f"Error: ID SLS '{args.idsls}' tidak ditemukan di {filepath}")
                    sys.exit(1)
                return filepath, matched

            if args.polygon_area:
                indices = parse_selection(args.polygon_area, total_features)
                if not indices:
                    print(f"Error: Tidak ada SLS yang cocok dengan pilihan '--polygon-area {args.polygon_area}'")
                    sys.exit(1)
                selected = [features[i] for i in indices]
                return filepath, selected

            # If no selection flag given for a multi-feature GeoJSON file, default to the 1st feature
            print(f"Catatan: File GeoJSON berisi {total_features} fitur SLS. Memproses fitur pertama (#1).")
            print("Gunakan '--polygon-area 1-5' atau '--polygon-area all' untuk memproses lebih banyak.")
            return filepath, [features[0]]

        else:
            # Simple JSON coordinate file (like area_example.json)
            poly = PolygonArea.from_file(filepath)
            return filepath, [poly]

    print("Error: Harap tentukan file polygon via '--polygon' atau gunakan mode interaktif.")
    sys.exit(1)


def process_single_sls(item: Any, args: Any, driver: MapDriver) -> bool:
    """
    Processes a single SLS item or PolygonArea.
    Returns True if successful, False if failed.
    """
    # 1. Prepare PolygonArea & Output Directory
    if isinstance(item, SLSFeature):
        polygon = PolygonArea.from_geojson_feature(item)
        folder_name = item.folder_name
        display_title = f"SLS #{item.index} ({item.idsls} - {item.nmsls})"
        target_dir = os.path.join(args.output, folder_name)
    elif hasattr(item, "metadata") and item.metadata.get("folder_name"):
        polygon = item
        folder_name = item.metadata["folder_name"]
        display_title = f"Polygon ({folder_name})"
        target_dir = os.path.join(args.output, folder_name)
    else:
        polygon = item
        target_dir = args.output
        display_title = "Polygon Area"

    output_json_path = os.path.join(target_dir, "results.json")

    # 2. Check for Skip / Auto-Resume
    if os.path.exists(output_json_path) and not args.force:
        print(f"\n[SKIP] Hasil sudah ada di {output_json_path} (gunakan --force untuk menimpa).")
        return True

    print("\n" + "-" * 50)
    print(f"Memproses: {display_title}")
    print(f"Target Output: {target_dir}")
    print("-" * 50)

    bbox = polygon.get_bounding_box()
    print(f"Bounding Box: Lat [{bbox['min_lat']:.5f} to {bbox['max_lat']:.5f}], Lng [{bbox['min_lng']:.5f} to {bbox['max_lng']:.5f}]")
    print(f"Center: {bbox['center_lat']:.5f}, {bbox['center_lng']:.5f}")

    # 3. Query Overpass API for Buildings
    buildings = []
    try:
        finder = BuildingFinder(polygon)
        buildings = finder.find_buildings()
    except Exception as e:
        print(f"Peringatan: Gagal mengambil data gedung dari Overpass ({e}). Melanjutkan dengan poligon area...")

    if not buildings:
        print(f"Informasi: Tidak ada gedung terdeteksi pada area {display_title}.")

    # 4. Reverse Geocode (Optional, only if buildings found)
    if buildings and not args.no_geocode:
        geocoder = ReverseGeocoder(delay=args.geocode_delay)
        buildings = geocoder.geocode_buildings(buildings)

    # 5. Capture Google Maps Overview Satellite Screenshot (Polygon + Building Pins)
    os.makedirs(target_dir, exist_ok=True)
    capture = PhotoCapture(driver, delay=args.delay, zoom=args.zoom)
    results = capture.capture_overview(polygon, buildings, target_dir)

    # 6. Compile & Save JSON
    extractor = DataExtractor(polygon)
    data = extractor.compile(results, output_json_path)

    print(f"Selesai: {data['total_buildings']} gedung disimpan ke {output_json_path}")
    return True


def main():
    args = parse_arguments()

    print("=" * 60)
    print(" Google Maps & Overpass Building Scraper (Multi-SLS Engine) ")
    print("=" * 60)

    source_path, target_items = load_target_items(args)
    total_targets = len(target_items)
    print(f"\nSumber: {source_path}")
    print(f"Total target yang akan diproses: {total_targets}")

    os.makedirs(args.output, exist_ok=True)

    success_count = 0
    failed_count = 0
    failed_items = []

    # Initialize single browser instance for entire batch
    with MapDriver(headless=not args.no_headless) as driver:
        for idx, item in enumerate(target_items, 1):
            print(f"\n>>> Progress: [{idx}/{total_targets}] <<<")
            try:
                ok = process_single_sls(item, args, driver)
                if ok:
                    success_count += 1
                else:
                    failed_count += 1
                    failed_items.append((idx, getattr(item, "idsls", str(item))))
            except Exception as e:
                failed_count += 1
                item_label = getattr(item, "idsls", str(item))
                failed_items.append((idx, item_label))
                print(f"[ERROR] Gagal memproses item {item_label}: {e}")
                traceback.print_exc()

    print("\n" + "=" * 60)
    print("RINGKASAN BATCH SCRAPING:")
    print(f" Total diproses: {total_targets}")
    print(f" Berhasil/Skipped: {success_count}")
    print(f" Gagal: {failed_count}")
    if failed_items:
        print(f" Daftar item gagal: {failed_items}")
    print(f" Folder Output: {os.path.abspath(args.output)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
