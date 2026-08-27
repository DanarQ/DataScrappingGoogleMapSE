import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class MapDriver:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None

    def start(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=en-US")
        try:
            self.driver = webdriver.Chrome(options=options)
        except Exception:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except Exception as e:
                raise RuntimeError(f"Failed to start Chrome WebDriver: {e}")
        print("Browser started")
        return self

    def go_to_satellite(self, lat, lng, zoom=20):
        # Direct Google Maps Satellite view URL with data=!3m1!1e3
        url = f"https://www.google.com/maps/@{lat},{lng},{zoom}z/data=!3m1!1e3"
        self.driver.get(url)
        self._dismiss_consent()
        time.sleep(4)
        self._hide_ui_and_add_target_marker()
        time.sleep(1)
        print(f"Satellite view at {lat}, {lng} (zoom {zoom})")

    def calculate_overview_zoom(self, polygon, width=1920, height=1080, margin=0.25):
        import math
        bbox = polygon.get_bounding_box()
        d_lat = max(bbox["max_lat"] - bbox["min_lat"], 0.0001)
        d_lng = max(bbox["max_lng"] - bbox["min_lng"], 0.0001)
        usable_w = width * (1 - margin)
        usable_h = height * (1 - margin)

        def lat_to_y(lat_deg):
            lat_rad = math.radians(lat_deg)
            return (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0

        d_y = max(abs(lat_to_y(bbox["max_lat"]) - lat_to_y(bbox["min_lat"])), 0.000001)
        zoom_lng = math.log2((usable_w * 360.0) / (256.0 * d_lng))
        zoom_lat = math.log2(usable_h / (256.0 * d_y))
        zoom = int(math.floor(min(zoom_lng, zoom_lat)))
        return max(14, min(19, zoom))

    def capture_overview(self, polygon, buildings, filepath, zoom=None):
        bbox = polygon.get_bounding_box()
        center_lat = bbox["center_lat"]
        center_lng = bbox["center_lng"]
        if zoom is None:
            zoom = self.calculate_overview_zoom(polygon)

        url = f"https://www.google.com/maps/@{center_lat},{center_lng},{zoom}z/data=!3m1!1e3"
        print(f"Opening Overview Satellite view (zoom {zoom}) at {center_lat:.6f}, {center_lng:.6f}")
        self.driver.get(url)
        self._dismiss_consent()
        time.sleep(5)

        poly_points = polygon.coordinates
        building_pins = [
            {"index": i + 1, "id": b.osm_id, "lat": b.lat, "lng": b.lng}
            for i, b in enumerate(buildings)
        ]

        script = """
        var center_lat = arguments[0];
        var center_lng = arguments[1];
        var zoom = arguments[2];
        var poly_points = arguments[3];
        var building_pins = arguments[4];
        var width = window.innerWidth;
        var height = window.innerHeight;

        // Hide Google Maps UI
        var selectors = [
            '.app-viewcard-strip', '.scene-footer', '.searchbox',
            '.widget-minimap', '.watermark',
            '.maps-sprite-settings-butterbar', '#titlecard',
            '.widget-scene-card', '#vasquette', '.m6QErb',
            '.app-horizontal-widget-holder', '.scene-footer-container',
            '#watermark', '.widget-pane-toggle-button-container',
            '.app-side-panel', '.widget-zoom'
        ];
        selectors.forEach(function(sel) {
            var els = document.querySelectorAll(sel);
            els.forEach(function(e) { e.style.display = 'none'; });
        });

        // Remove existing overlay
        var existing = document.getElementById('overview-overlay');
        if (existing) existing.remove();

        var container = document.createElement('div');
        container.id = 'overview-overlay';
        container.style.position = 'fixed';
        container.style.top = '0';
        container.style.left = '0';
        container.style.width = '100vw';
        container.style.height = '100vh';
        container.style.pointerEvents = 'none';
        container.style.zIndex = '9999999';

        function project(lat, lng) {
            function latToY(lat_deg) {
                var lat_rad = lat_deg * Math.PI / 180;
                return (1 - Math.log(Math.tan(lat_rad) + 1 / Math.cos(lat_rad)) / Math.PI) / 2;
            }
            var scale = 256 * Math.pow(2, zoom);
            var x = (lng + 180) / 360 * scale;
            var y = latToY(lat) * scale;
            var cx = (center_lng + 180) / 360 * scale;
            var cy = latToY(center_lat) * scale;
            return {
                x: (width / 2) + (x - cx),
                y: (height / 2) + (y - cy)
            };
        }

        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';

        // 1. Draw Polygon Boundary
        var polySvgPts = poly_points.map(function(p) {
            var pt = project(p[0], p[1]);
            return pt.x + ',' + pt.y;
        }).join(' ');

        var polygonEl = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        polygonEl.setAttribute('points', polySvgPts);
        polygonEl.setAttribute('fill', 'rgba(0, 229, 255, 0.12)');
        polygonEl.setAttribute('stroke', '#00E5FF');
        polygonEl.setAttribute('stroke-width', '3');
        polygonEl.setAttribute('stroke-dasharray', '8 4');
        svg.appendChild(polygonEl);

        // 2. Draw Building Numbered Pins
        building_pins.forEach(function(b) {
            var pt = project(b.lat, b.lng);
            var g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.setAttribute('transform', 'translate(' + pt.x + ',' + pt.y + ')');

            // Shadow circle
            var shadow = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            shadow.setAttribute('r', '14');
            shadow.setAttribute('fill', 'rgba(0,0,0,0.5)');
            shadow.setAttribute('cy', '1.5');
            g.appendChild(shadow);

            // Outer circle
            var circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('r', '12');
            circle.setAttribute('fill', '#FF3B30');
            circle.setAttribute('stroke', '#FFFFFF');
            circle.setAttribute('stroke-width', '2');
            g.appendChild(circle);

            // Number text
            var text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('dy', '4.5');
            text.setAttribute('fill', '#FFFFFF');
            text.setAttribute('font-size', b.index > 99 ? '9' : (b.index > 9 ? '10' : '12'));
            text.setAttribute('font-family', 'Arial, sans-serif');
            text.setAttribute('font-weight', 'bold');
            text.textContent = b.index;
            g.appendChild(text);

            svg.appendChild(g);
        });

        container.appendChild(svg);
        document.body.appendChild(container);
        """

        self.driver.execute_script(script, center_lat, center_lng, zoom, poly_points, building_pins)
        time.sleep(2)

        self.take_screenshot(filepath)
        print(f"Overview satellite map saved: {filepath}")
        return filepath

    def _hide_ui_and_add_target_marker(self):
        try:
            self.driver.execute_script("""
                // Hide Google Maps UI overlays
                var selectors = [
                    '.app-viewcard-strip', '.scene-footer', '.searchbox',
                    '.widget-minimap', '.watermark',
                    '.maps-sprite-settings-butterbar', '#titlecard',
                    '.widget-scene-card', '#vasquette', '.m6QErb',
                    '.app-horizontal-widget-holder', '.scene-footer-container',
                    '#watermark', '.widget-pane-toggle-button-container',
                    '.app-side-panel', '.widget-zoom'
                ];
                selectors.forEach(function(sel) {
                    var els = document.querySelectorAll(sel);
                    els.forEach(function(e) { e.style.display = 'none'; });
                });

                // Add Option 2: Target Reticle Marker at center
                var existing = document.getElementById('building-target-marker');
                if (existing) existing.remove();

                var marker = document.createElement('div');
                marker.id = 'building-target-marker';
                marker.style.position = 'fixed';
                marker.style.top = '50%';
                marker.style.left = '50%';
                marker.style.transform = 'translate(-50%, -50%)';
                marker.style.width = '70px';
                marker.style.height = '70px';
                marker.style.pointerEvents = 'none';
                marker.style.zIndex = '9999999';

                marker.innerHTML = `
                <svg width="70" height="70" viewBox="0 0 70 70" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <!-- Outer circle border with glow shadow -->
                  <circle cx="35" cy="35" r="26" stroke="rgba(0,0,0,0.5)" stroke-width="4"/>
                  <!-- Outer dashed target ring -->
                  <circle cx="35" cy="35" r="26" stroke="#FF3B30" stroke-width="2.5" stroke-dasharray="6 3"/>
                  <!-- Inner precision ring -->
                  <circle cx="35" cy="35" r="10" stroke="#FF3B30" stroke-width="2"/>
                  <!-- Center target dot -->
                  <circle cx="35" cy="35" r="3.5" fill="#FF3B30"/>
                  <!-- Crosshair lines with shadow -->
                  <line x1="35" y1="2" x2="35" y2="18" stroke="#FF3B30" stroke-width="2.5" stroke-linecap="round"/>
                  <line x1="35" y1="52" x2="35" y2="68" stroke="#FF3B30" stroke-width="2.5" stroke-linecap="round"/>
                  <line x1="2" y1="35" x2="18" y2="35" stroke="#FF3B30" stroke-width="2.5" stroke-linecap="round"/>
                  <line x1="52" y1="35" x2="68" y2="35" stroke="#FF3B30" stroke-width="2.5" stroke-linecap="round"/>
                </svg>
                `;
                document.body.appendChild(marker);
            """)
        except Exception as e:
            print(f"UI hide / marker inject error: {e}")

    def go_to_street_view(self, lat, lng):
        # Direct Street View URL
        url = f"https://www.google.com/maps/@{lat},{lng},3a,75y,90h,90t/data=!3m6!1e1!3m4!1s!2e0!7i16384!8i8192"
        self.driver.get(url)
        self._dismiss_consent()
        time.sleep(5)
        print(f"Street View at {lat}, {lng}")

    def has_street_view(self, temp_filepath=None):
        try:
            # 1. Check URL redirect or panoid parameter
            current_url = self.driver.current_url
            if ",3a," not in current_url:
                print("  No Street View: Redirected away from streetview mode")
                return False

            # 2. Check error text on page
            no_sv_texts = [
                "no street view", "tidak ada street view", "tidak ada gambar street view",
                "don't have imagery", "we don't have imagery", "unfortunately, we don't have",
                "tidak tersedia", "cannot be reached", "imagery not available"
            ]
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                for text in no_sv_texts:
                    if text in page_text:
                        print(f"  No Street View: Found error text '{text}'")
                        return False
            except Exception:
                pass

            # 3. Take temporary test screenshot to verify image content
            # A blank black screen with no imagery is typically < 40KB
            if temp_filepath:
                self.take_screenshot(temp_filepath)
                if os.path.exists(temp_filepath):
                    size = os.path.getsize(temp_filepath)
                    if size < 40000:
                        print(f"  No Street View: Blank screen detected ({size} bytes)")
                        try:
                            os.remove(temp_filepath)
                        except OSError:
                            pass
                        return False
                    return True

            return True
        except Exception as e:
            print(f"  Street View check error: {e}")
            return False

    def take_screenshot(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.driver.save_screenshot(filepath)
        print(f"Screenshot saved: {filepath} ({os.path.getsize(filepath)} bytes)")

    def _dismiss_consent(self):
        try:
            btns = self.driver.find_elements(By.CSS_SELECTOR, "button")
            for btn in btns:
                try:
                    text = btn.text.lower()
                    if any(kw in text for kw in ["accept", "agree", "terima", "setuju", "reject all", "tolak"]):
                        btn.click()
                        time.sleep(1)
                        return
                except Exception:
                    continue
        except Exception:
            pass

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            print("Browser closed")

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
