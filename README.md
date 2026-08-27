# Google Maps Building Scraper

Scraper untuk mengambil data koordinat dan foto bangunan dalam suatu area polygon dari Google Maps.

## Fitur

- Deteksi bangunan otomatis via OpenStreetMap (Overpass API) dengan outline polygon
- Ambil foto **overview satellite map** (1 foto satelit keseluruhan area dengan garis batas poligon dan pin nomor urut seluruh gedung)
- Output data bersih dan terstruktur dalam format JSON (koordinat, index gedung, tipe bangunan, alamat, polygon outline, overview photo)
- Area input berupa polygon bebas (koordinat lat/lng)
- Proses cepat tanpa perlu scraping foto satu per satu

## Instalasi

```bash
pip install -r requirements.txt
```

Pastikan sudah terinstall:
- **Python 3.8+**
- **Google Chrome** (untuk Selenium)

## Cara Pakai

### 1. Buat file polygon (JSON)

Buat file JSON berisi koordinat titik-titik yang membentuk area/petak yang mau di-scraper.

Format: `[[lat, lng], [lat, lng], ...]` — minimal 3 titik, titik pertama dan terakhir harus sama (menutup polygon).

Contoh `area_example.json`:

```json
[
  [-0.055970, 109.338531],
  [-0.057922, 109.341146],
  [-0.060767, 109.338618],
  [-0.058578, 109.336301],
  [-0.055970, 109.338531]
]
```

### 2. Jalankan scraper

```bash
python main.py --polygon area_example.json
```

### 3. Opsi tambahan

| Flag | Default | Keterangan |
|------|---------|------------|
| `--polygon` | (wajib) | Path ke file JSON polygon |
| `--output` | `output` | Directory output |
| `--zoom` | `None` (auto) | Manual override zoom level Google Maps (default: otomatis dihitung dari bounding box) |
| `--delay` | `2` | Delay sebelum screenshot (detik) |
| `--no-headless` | `false` | Tampilkan browser (untuk debugging) |

Contoh dengan opsi:

```bash
python main.py --polygon area_example.json --output hasil --zoom 17 --delay 2 --no-headless
```

## Output

```
output/
├── overview_satellite.png    # 1 foto satelit ikhtisar seluruh area (dengan garis poligon & pin nomor)
└── results.json              # Data koordinat, alamat, tipe, & metadata gedung
```

### Format `results.json`

```json
{
  "polygon": [[-0.05597, 109.338531], ...],
  "bounding_box": {
    "min_lat": -0.060767,
    "max_lat": -0.05597,
    "min_lng": 109.336301,
    "max_lng": 109.341146,
    "center_lat": -0.0583685,
    "center_lng": 109.3387235
  },
  "overview_photo": "output/overview_satellite.png",
  "total_buildings": 52,
  "buildings": [
    {
      "index": 1,
      "id": "osm_119427945",
      "lat": -0.060165,
      "lng": 109.338940,
      "building_type": "residential",
      "address": "Jl. Gajah Mada, Pontianak",
      "polygon": [[-0.060165, 109.338940], ...]
    }
  ]
}
```

## Flow Kerja

```
Input Polygon → Overpass API (OpenStreetMap) → Temukan bangunan & koordinat
                                                    ↓
                                             Selenium Chrome
                                                    ↓
                                     Google Maps Satellite View (Overview Area)
                                                    ↓
                                     Injeksi Overlay Polygon + Pin Nomor Gedung
                                                    ↓
                                             Ambil Screenshot Overview
                                                    ↓
                                             Kompilasi ke results.json
```

1. **Polygon** dikirim ke Overpass API untuk mencari semua bangunan (`building=*`) di area tersebut
2. **Selenium** membuka Google Maps satellite view pada posisi center & zoom area
3. Garis batas poligon dan pin nomor urut seluruh gedung di-render secara dinamis di atas peta satelit
4. Screenshot **overview satellite map** disimpan
5. Semua data metadata gedung dikompilasi ke `results.json`

## Catatan

- Google Maps perlu **Chrome terinstall** di sistem
- Delay screenshot bisa diatur via `--delay`
- Data bangunan berasal dari **OpenStreetMap** (gratis), foto dari **Google Maps**
