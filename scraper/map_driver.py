import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


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
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        print("Browser started")
        return self

    def go_to_coordinates(self, lat, lng, zoom=18):
        url = f"https://www.google.com/maps/@{lat},{lng},{zoom}z"
        self.driver.get(url)
        time.sleep(3)
        self._dismiss_consent()
        print(f"Navigated to {lat}, {lng} (zoom {zoom})")

    def switch_to_satellite(self):
        try:
            layers_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-id='layers']"))
            )
            layers_btn.click()
            time.sleep(1)
            satellite_btn = self.driver.find_element(
                By.CSS_SELECTOR, "button[data-id='layer-image']"
            )
            satellite_btn.click()
            time.sleep(2)
            print("Switched to satellite view")
        except Exception as e:
            print(f"Could not switch to satellite: {e}")

    def go_to_street_view(self, lat, lng):
        url = f"https://www.google.com/maps/@{lat},{lng},3a,75y,0h,90t/data=!3m6!1e1!3m4!1s!2e0!7i13312!8i6656"
        self.driver.get(url)
        time.sleep(3)
        self._dismiss_consent()
        print(f"Navigated to Street View at {lat}, {lng}")

    def has_street_view(self):
        try:
            error_indicators = self.driver.find_elements(
                By.CSS_SELECTOR, ".error-msg, .widget-scene-error-message"
            )
            return len(error_indicators) == 0
        except Exception:
            return False

    def take_screenshot(self, filepath):
        self.driver.save_screenshot(filepath)
        print(f"Screenshot saved: {filepath}")

    def _dismiss_consent(self):
        try:
            consent_btns = self.driver.find_elements(
                By.CSS_SELECTOR, "button[aria-label*='Accept'], button[aria-label*='agree'], form button"
            )
            for btn in consent_btns:
                text = btn.text.lower()
                if "accept" in text or "agree" in text or "reject" in text:
                    btn.click()
                    time.sleep(1)
                    break
        except Exception:
            pass

    def close(self):
        if self.driver:
            self.driver.quit()
            print("Browser closed")

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
