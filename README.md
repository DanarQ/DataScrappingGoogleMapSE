# Google Maps Building Scraper

Scraper untuk mengambil data koordinat dan foto bangunan dalam suatu area polygon dari Google Maps.

## Fitur

- Deteksi bangunan otomatis via OpenStreetMap (Overpass API) dengan outline polygon
- Ambil foto **satellite view** resolusi tinggi dari Google Maps dengan penanda **target ring / crosshair** gedung
- Ambil foto **street view** dari Google Maps dengan deteksi ketersediaan akurat
- Output data lengkap dalam format JSON (koordinat, tipe bangunan, alamat, path foto / "gak ada")
- Area input berupa polygon bebas (koordinat lat/lng)

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
  [-6.905, 107.610],
  [-6.905, 107.615],
  [-6.900, 107.615],
  [-6.900, 107.610],
  [-6.905, 107.610]
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
| `--zoom` | `20` | Zoom level Google Maps (default: 20, fokus ke gedung) |
| `--delay` | `2` | Delay antar request (detik) |
| `--no-headless` | `false` | Tampilkan browser (untuk debugging) |

Contoh dengan opsi:

```bash
python main.py --polygon area_example.json --output hasil --zoom 20 --delay 2 --no-headless
```

## Output

```
output/
├── photos/
│   ├── satellite/
│   │   ├── building_119427945.png
│   │   ├── building_119428467.png
│   │   └── ...
│   └── streetview/
│       ├── building_119427945.png
│       ├── building_119428467.png
│       └── ...
└── results.json
```

### Format `results.json`

```json
{
  "polygon": [[-6.905, 107.61], [-6.905, 107.615], ...],
  "bounding_box": {
    "min_lat": -6.905,
    "max_lat": -6.9,
    "min_lng": 107.61,
    "max_lng": 107.615,
    "center_lat": -6.9025,
    "center_lng": 107.6125
  },
  "total_buildings": 416,
  "buildings": [
    {
      "id": "osm_119427945",
      "lat": -6.9018,
      "lng": 107.6126,
      "building_type": "supermarket",
      "address": "Jl. Asia Afrika, Bandung",
      "polygon": [[-6.9018, 107.6126], ...],
      "photos": {
        "satellite": "output/photos/satellite/building_119427945.png",
        "streetview": "output/photos/streetview/building_119427945.png"
      }
    }
  ]
}
```

## Flow Kerja

```
Input Polygon → Overpass API (OpenStreetMap) → Dapat koordinat bangunan
                                                    ↓
                                            Selenium Chrome
                                                    ↓
                                    Google Maps satellite view → Screenshot
                                    Google Maps street view → Screenshot
                                                    ↓
                                            Kompilasi ke JSON
```

1. **Polygon** dikirim ke Overpass API untuk mencari semua bangunan (`building=*`) di area tersebut
2. **Selenium** membuka Google Maps untuk setiap koordinat bangunan
3. **Satellite view** dan **street view** di-screenshot
4. Semua data dikompilasi ke `results.json`

## Catatan

- Google Maps perlu **Chrome terinstall** di sistem
- Street view tidak tersedia di semua lokasi (akan di-skip otomatis)
- Delay antar request bisa diatur via `--delay` untuk menghindari rate limit
- Data bangunan berasal dari **OpenStreetMap** (gratis), foto dari **Google Maps**
