# Google Maps Building Scraper

Scraper untuk mengambil data koordinat dan foto bangunan dalam suatu area polygon dari Google Maps.

## Fitur

- Deteksi bangunan otomatis via OpenStreetMap (Overpass API) dengan outline polygon
- Ambil foto **overview satellite map** (1 foto satelit keseluruhan area dengan garis batas poligon dan pin nomor urut seluruh gedung)
- Ambil foto **satellite view** close-up resolusi tinggi per gedung dengan penanda **target reticle / crosshair**
- Ambil foto **street view** per gedung dengan deteksi ketersediaan akurat
- Output data lengkap dalam format JSON (koordinat, index gedung, tipe bangunan, alamat, overview photo, path foto / "gak ada")
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
| `--zoom` | `20` | Zoom level Google Maps untuk foto per gedung (default: 20) |
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
│   ├── overview_satellite.png    # 1 foto satelit ikhtisar seluruh area (dengan garis poligon & pin nomor)
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
  "polygon": [[-0.05597, 109.338531], ...],
  "bounding_box": {
    "min_lat": -0.060767,
    "max_lat": -0.05597,
    "min_lng": 109.336301,
    "max_lng": 109.341146,
    "center_lat": -0.0583685,
    "center_lng": 109.3387235
  },
  "overview_photo": "output/photos/overview_satellite.png",
  "total_buildings": 52,
  "buildings": [
    {
      "index": 1,
      "id": "osm_119427945",
      "lat": -0.060165,
      "lng": 109.338940,
      "building_type": "residential",
      "address": "Jl. Gajah Mada, Pontianak",
      "polygon": [[-0.060165, 109.338940], ...],
      "photos": {
        "satellite": "output/photos/satellite/building_119427945.png",
        "streetview": "gak ada"
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
