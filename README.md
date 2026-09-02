# Google Maps Building Scraper (Multi-SLS GeoJSON Edition)

Scraper untuk mengambil data koordinat, metadata bangunan (OSM), alamat (Reverse Geocoding), dan foto satelit beranotasi poligon + pin gedung dari Google Maps. Mendukung file GeoJSON SLS (Satuan Lingkungan Setempat) BPS untuk Kalimantan Barat dan area poligon kustom.

---

## Fitur Utama

- **Integrasi GeoJSON SLS & Kode Kabupaten**: Otomatis mendeteksi dan memetakan kode wilayah dari `DataGeoJson/New Text Document.md` (6101 Sambas s/d 6172 Singkawang).
- **Fleksibilitas Seleksi Area**:
  - Pilihan nomor/rentang section (`--polygon-area 2`, `1,3,5`, `1-10`, `all`).
  - Filter ID SLS spesifik (`--idsls 61010100020001`).
  - **Menu Interaktif Terminal**: Cukup jalankan `python main.py` untuk memilih Kabupaten dan SLS melalui wizard terminal.
- **Batch Processing & Auto-Resume**: Melewati SLS yang sudah selesai di-scrape, isolasi error per-SLS, dan reuse instance browser untuk efisiensi maksimal.
- **Dukungan MultiPolygon**: Menangani geometri poligon kompleks maupun multi-bagian (disjoint/islands).
- **Reverse Geocoding Otomatis**: Melengkapi alamat jalan, kelurahan, kecamatan, dan kota via OpenStreetMap Nominatim.
- **Overview Map Satelit Beranotasi**: Menyimpan tangkapan layar Google Maps dengan garis batas poligon SLS (cyan outline) dan pin merah bernomor urut untuk setiap gedung.

---

## Instalasi

```bash
pip install -r requirements.txt
```

Prasyarat:
- **Python 3.8+**
- **Google Chrome** terinstall di sistem

---

## Cara Pakai

### 1. Mode Interaktif (Wizard Terminal)

Jalankan tanpa argumen untuk membuka wizard interaktif:

```bash
python main.py
```

Wizard akan:
1. Menampilkan daftar Kabupaten yang tersedia di `DataGeoJson/`.
2. Memuat file GeoJSON dan menampilkan contoh SLS.
3. Meminta input nomor SLS yang ingin diproses (contoh: `2`, `1-5`, atau `all`).

---

### 2. Mode Argumen CLI Langsung

#### A. Memilih SLS Tertentu dari File GeoJSON
```bash
# Memproses SLS nomor urut 2
python main.py --polygon DataGeoJson/Final_SLS_202516101.geojson --polygon-area 2

# Memproses beberapa SLS (nomor 1, 3, dan 5)
python main.py --polygon DataGeoJson/Final_SLS_202516101.geojson --polygon-area 1,3,5

# Memproses rentang SLS (nomor 1 sampai 10)
python main.py --polygon DataGeoJson/Final_SLS_202516101.geojson --polygon-area 1-10

# Memproses SEMUA SLS dalam 1 file kabupaten
python main.py --polygon DataGeoJson/Final_SLS_202516101.geojson --polygon-area all
```

#### B. Filter Berdasarkan ID SLS Spesifik
```bash
python main.py --polygon DataGeoJson/Final_SLS_202516101.geojson --idsls 61010200150052
```

#### C. Menggunakan Poligon Kustom (JSON Biasa)
```bash
python main.py --polygon area_example.json
```

---

### 3. Opsi Parameter Lengkap

| Parameter | Default | Keterangan |
|---|---|---|
| `--polygon` | `None` | Path ke file GeoJSON atau JSON poligon kustom |
| `--polygon-area` | `None` | Nomor urut SLS (`2`), rentang (`1-5`), daftar (`1,3,5`), atau `all` |
| `--idsls` | `None` | ID SLS spesifik 14 digit (contoh: `61010100020001`) |
| `--interactive` | `false` | Memaksa masuk ke mode wizard terminal interaktif |
| `--output` | `output` | Direktori root untuk menyimpan hasil |
| `--force` | `false` | Timpa hasil scraping yang sudah ada (default: auto-skip) |
| `--no-geocode` | `false` | Nonaktifkan reverse geocoding alamat gedung (lebih cepat) |
| `--geocode-delay` | `1.0` | Jeda antar request geocoding (detik) |
| `--zoom` | `None` | Override manual level zoom satelit (default: auto-calculated) |
| `--delay` | `2.0` | Jeda sebelum mengambil screenshot satelit (detik) |
| `--no-headless` | `false` | Buka jendela Chrome secara visual (untuk debugging) |

---

## Struktur Folder Output

Hasil scraping disimpan secara terorganisir per SLS dengan format flat `<KODE_KAB>_<IDSLS>`:

```text
output/
  ├── 6101_61010100020001/
  │   ├── results.json             # Metadata SLS, daftar gedung, koordinat, & alamat
  │   └── overview_satellite.png   # Foto satelit Google Maps + batas poligon + pin gedung
  ├── 6101_61010200150052/
  │   ├── results.json
  │   └── overview_satellite.png
  └── ...
```

---

## Format `results.json`

```json
{
  "metadata": {
    "sls_index": 2,
    "idsls": "61010200150052",
    "nmsls": "RT 004 RW 012 DUSUN SINAM",
    "kode_kab": "6101",
    "nmkab": "SAMBAS",
    "kdkec": "020",
    "nmkec": "PEMANGKAT",
    "kddesa": "015",
    "nmdesa": "PEMANGKAT KOTA",
    "folder_name": "6101_61010200150052"
  },
  "polygon": [[[1.159, 108.964], ...]],
  "bounding_box": {
    "min_lat": 1.15326,
    "max_lat": 1.16106,
    "min_lng": 108.904,
    "max_lng": 108.96479,
    "center_lat": 1.15716,
    "center_lng": 108.9344
  },
  "overview_photo": "output/6101_61010200150052/overview_satellite.png",
  "total_buildings": 71,
  "buildings": [
    {
      "index": 1,
      "id": "osm_610505567",
      "lat": 1.1591,
      "lng": 108.9641,
      "building_type": "residential",
      "address": "Jl. Sinam, Pemangkat, Sambas",
      "polygon": [[1.1591, 108.9641], ...]
    }
  ]
}
```
