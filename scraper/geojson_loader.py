import json
import os
import re
import sys
from typing import List, Dict, Any, Optional, Tuple


class SLSFeature:
    def __init__(self, index: int, feature: Dict[str, Any], kode_kab_override: Optional[str] = None):
        self.index = index  # 1-based index in file
        self.raw_feature = feature
        self.properties = feature.get("properties", {})
        self.geometry = feature.get("geometry", {})

        self.idsls = str(self.properties.get("idsls") or "")
        self.nmsls = str(self.properties.get("nmsls") or "")
        self.nmkab = str(self.properties.get("nmkab") or "")
        self.kdkab_raw = str(self.properties.get("kdkab") or "")
        self.nmkec = str(self.properties.get("nmkec") or "")
        self.kdkec = str(self.properties.get("kdkec") or "")
        self.nmdesa = str(self.properties.get("nmdesa") or "")
        self.kddesa = str(self.properties.get("kddesa") or "")
        self.kdprov = str(self.properties.get("kdprov") or "61")

        # Determine 4-digit Kabupaten code (e.g. 6101)
        if len(self.idsls) >= 4 and self.idsls.startswith("61"):
            self.kode_kab = self.idsls[:4]
        elif kode_kab_override and len(kode_kab_override) == 4:
            self.kode_kab = kode_kab_override
        elif self.kdprov and self.kdkab_raw:
            self.kode_kab = f"{self.kdprov}{self.kdkab_raw.zfill(2)}"
        else:
            self.kode_kab = kode_kab_override or "6100"

    @property
    def folder_name(self) -> str:
        """Format: <KODE_KAB>_<IDSLS>"""
        return f"{self.kode_kab}_{self.idsls}"

    @property
    def display_name(self) -> str:
        parts = [f"#{self.index}", f"ID: {self.idsls}"]
        if self.nmsls:
            parts.append(self.nmsls)
        if self.nmdesa:
            parts.append(f"Desa: {self.nmdesa}")
        if self.nmkec:
            parts.append(f"Kec: {self.nmkec}")
        return " | ".join(parts)

    def to_polygon_coordinates(self) -> List[Any]:
        """
        Converts GeoJSON geometry coordinates ([lng, lat]) to PolygonArea coordinates ([lat, lng]).
        Supports Polygon and MultiPolygon.
        Returns:
            - For Polygon: List of [lat, lng] pairs (exterior ring)
            - For MultiPolygon: List of lists of [lat, lng] pairs
        """
        gtype = self.geometry.get("type", "")
        coords = self.geometry.get("coordinates", [])

        if gtype == "Polygon":
            # coords[0] is exterior ring [[lng, lat], ...]
            if coords and len(coords) > 0:
                return [[p[1], p[0]] for p in coords[0]]
            return []
        elif gtype == "MultiPolygon":
            # coords is list of polygons, each has exterior ring coords[i][0]
            result = []
            for poly in coords:
                if poly and len(poly) > 0:
                    result.append([[p[1], p[0]] for p in poly[0]])
            return result
        else:
            raise ValueError(f"Unsupported geometry type: {gtype}")

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "sls_index": self.index,
            "idsls": self.idsls,
            "nmsls": self.nmsls,
            "kode_kab": self.kode_kab,
            "nmkab": self.nmkab,
            "kdkec": self.kdkec,
            "nmkec": self.nmkec,
            "kddesa": self.kddesa,
            "nmdesa": self.nmdesa,
            "folder_name": self.folder_name,
        }


class KabupatenRegistry:
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            # Look for DataGeoJson relative to project root or current working dir
            potential_dirs = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DataGeoJson"),
                os.path.join(os.getcwd(), "DataGeoJson"),
                os.path.abspath("DataGeoJson"),
            ]
            self.data_dir = None
            for p in potential_dirs:
                if os.path.exists(p):
                    self.data_dir = p
                    break
            if not self.data_dir:
                self.data_dir = os.path.join(os.getcwd(), "DataGeoJson")
        else:
            self.data_dir = os.path.abspath(base_dir)

        self.entries: List[Dict[str, Any]] = []
        self._load_registry()

    def _load_registry(self):
        doc_path = os.path.join(self.data_dir, "New Text Document.md")
        json_data = []

        if os.path.exists(doc_path):
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                # Find JSON array in document
                m = re.search(r"\[\s*\{.*?\}\s*\]", content, re.DOTALL)
                if m:
                    json_data = json.loads(m.group(0))
                else:
                    json_data = json.loads(content)
            except Exception as e:
                print(f"Warning: Failed to parse {doc_path}: {e}")

        # Scan files in DataGeoJson
        files_in_dir = []
        if os.path.exists(self.data_dir):
            files_in_dir = [f for f in os.listdir(self.data_dir) if f.lower().endswith(".geojson")]

        # Match entries from New Text Document.md
        found_codes = set()
        for item in json_data:
            kode = str(item.get("kode", "")).strip()
            nama = str(item.get("nama", "")).strip()
            if not kode:
                continue
            found_codes.add(kode)

            # Find matching file (e.g. Final_SLS_202516101.geojson)
            matched_file = None
            for fname in files_in_dir:
                if kode in fname:
                    matched_file = fname
                    break

            self.entries.append({
                "kode": kode,
                "nama": nama,
                "file_name": matched_file,
                "file_path": os.path.join(self.data_dir, matched_file) if matched_file else None,
                "exists": (matched_file is not None),
            })

        # Also add any geojson files not listed in json_data
        for fname in files_in_dir:
            fpath = os.path.join(self.data_dir, fname)
            # Check if already covered
            already_covered = any(e["file_name"] == fname for e in self.entries)
            if not already_covered:
                # Guess kode from filename
                m = re.search(r"(\d{4})", fname)
                kode_guessed = m.group(1) if m else fname
                self.entries.append({
                    "kode": kode_guessed,
                    "nama": fname.replace(".geojson", ""),
                    "file_name": fname,
                    "file_path": fpath,
                    "exists": True,
                })

    def find_by_code_or_name(self, query: str) -> Optional[Dict[str, Any]]:
        q = query.strip().upper()
        for e in self.entries:
            if e["kode"].upper() == q or e["nama"].upper() == q:
                return e
            if e["file_name"] and (q in e["file_name"].upper()):
                return e
        return None

    def list_all(self) -> List[Dict[str, Any]]:
        return self.entries


class GeoJSONLoader:
    @staticmethod
    def load_file(filepath: str, kode_kab_override: Optional[str] = None) -> List[SLSFeature]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"GeoJSON file not found: {filepath}")

        # Guess kode_kab from filename if not provided (e.g. Final_SLS_202516101.geojson -> 6101)
        if not kode_kab_override:
            m = re.search(r"(\d{4})", os.path.basename(filepath))
            if m:
                kode_kab_override = m.group(1)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        features_data = data.get("features", [])
        if not features_data and isinstance(data, list):
            features_data = data

        sls_features = []
        for idx, feat in enumerate(features_data, 1):
            sls_features.append(SLSFeature(index=idx, feature=feat, kode_kab_override=kode_kab_override))

        return sls_features


def parse_selection(selection_str: str, total_items: int) -> List[int]:
    """
    Parses selection string like:
      - "2" -> [1]
      - "1,3,5" -> [0, 2, 4]
      - "1-5" -> [0, 1, 2, 3, 4]
      - "all" or "*" -> all items [0, 1, ..., total_items - 1]
    Returns 0-based integer indices.
    """
    s = selection_str.strip().lower()
    if s in ["all", "*"]:
        return list(range(total_items))

    selected = set()
    chunks = [c.strip() for c in s.split(",") if c.strip()]

    for chunk in chunks:
        if "-" in chunk:
            parts = chunk.split("-")
            if len(parts) == 2:
                try:
                    start_str, end_str = parts[0].strip(), parts[1].strip()
                    start = int(start_str) if start_str else 1
                    end = int(end_str) if end_str else total_items
                    for i in range(start, end + 1):
                        if 1 <= i <= total_items:
                            selected.add(i - 1)
                except ValueError:
                    raise ValueError(f"Invalid range in selection: '{chunk}'")
        else:
            try:
                val = int(chunk)
                if 1 <= val <= total_items:
                    selected.add(val - 1)
                else:
                    print(f"Warning: Index {val} out of bounds (1-{total_items}), ignoring.")
            except ValueError:
                raise ValueError(f"Invalid number in selection: '{chunk}'")

    return sorted(list(selected))


def interactive_select(data_dir: Optional[str] = None) -> Tuple[str, List[SLSFeature]]:
    """
    Terminal wizard to choose Kabupaten and SLS features.
    """
    registry = KabupatenRegistry(data_dir)
    entries = [e for e in registry.list_all() if e.get("exists")]

    if not entries:
        print("Error: Tidak ada file GeoJSON ditemukan di folder DataGeoJson.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("DAFTAR KABUPATEN / FILE GEOJSON TERSEDIA:")
    print("=" * 60)
    for idx, e in enumerate(entries, 1):
        print(f" [{idx:2d}] {e['kode']} - {e['nama']:<15} (File: {e['file_name']})")
    print("=" * 60)

    # Step 1: Pilih Kabupaten
    selected_entry = None
    while not selected_entry:
        choice = input(f"\nPilih nomor Kabupaten (1-{len(entries)}) atau ketik kode/nama: ").strip()
        if not choice:
            continue
        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(entries):
                selected_entry = entries[num - 1]
        if not selected_entry:
            found = registry.find_by_code_or_name(choice)
            if found and found.get("exists"):
                selected_entry = found

        if not selected_entry:
            print("Pilihan tidak valid, silakan coba lagi.")

    file_path = selected_entry["file_path"]
    kode_kab = selected_entry["kode"]
    print(f"\nMemuat file GeoJSON: {selected_entry['file_name']} (Kab: {selected_entry['nama']})...")
    features = GeoJSONLoader.load_file(file_path, kode_kab_override=kode_kab)
    total_sls = len(features)
    print(f"Total SLS ditemukan: {total_sls} SLS")

    # Step 2: Tampilkan sampel dan minta pilihan SLS
    print("\nContoh beberapa SLS pertama:")
    preview_count = min(8, total_sls)
    for i in range(preview_count):
        f = features[i]
        print(f" [{i + 1:3d}] ID: {f.idsls} | {f.nmsls} | Desa: {f.nmdesa} | Kec: {f.nmkec}")
    if total_sls > preview_count:
        print(f" ... dan {total_sls - preview_count} SLS lainnya.")

    print("\nFormat pemilihan:")
    print(" - '2'         : Hanya pilih SLS nomor 2")
    print(" - '1,3,5'     : Pilih SLS nomor 1, 3, dan 5")
    print(" - '1-10'      : Pilih SLS nomor 1 sampai 10")
    print(" - 'all'       : Pilih SEMUA SLS dalam file ini")

    selected_features = []
    while not selected_features:
        sel_input = input(f"\nPilih SLS yang ingin di-scrape (1-{total_sls} / all): ").strip()
        if not sel_input:
            continue
        try:
            indices = parse_selection(sel_input, total_sls)
            if not indices:
                print("Tidak ada SLS yang terpilih. Silakan coba lagi.")
                continue
            selected_features = [features[i] for i in indices]
        except ValueError as e:
            print(f"Format salah: {e}")

    print(f"\nTerpilih {len(selected_features)} SLS untuk diproses.")
    return file_path, selected_features
