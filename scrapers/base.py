from __future__ import annotations

import logging
import random
import time
from contextlib import contextmanager
from typing import Generator

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from config import HEADLESS, MAX_DELAY, MIN_DELAY, USER_AGENTS, WINDOW_SIZE

logger = logging.getLogger(__name__)


class BaseScraper:

    def __init__(self) -> None:
        self.driver: webdriver.Chrome | None = None

    def _build_options(self) -> Options:
        opts = Options()
        if HEADLESS:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument(f"--window-size={WINDOW_SIZE}")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        ua = random.choice(USER_AGENTS)
        opts.add_argument(f"--user-agent={ua}")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        return opts

    @contextmanager
    def browser(self) -> Generator[webdriver.Chrome, None, None]:
        self.open_browser()
        try:
            yield self.driver
        finally:
            self.close_browser()

    def open_browser(self) -> None:
        opts = self._build_options()
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )

    def close_browser(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None

    @staticmethod
    def random_delay(lo: float = MIN_DELAY, hi: float = MAX_DELAY) -> None:
        time.sleep(random.uniform(lo, hi))

    def wait_and_find(self, by: str, value: str, timeout: int = 15):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def wait_and_find_all(self, by: str, value: str, timeout: int = 15) -> list:
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return self.driver.find_elements(by, value)

    def dismiss_cookies(self, selector: str | None = None) -> None:
        candidates = []
        if selector and selector != "___REPLACE_WITH_ACTUAL_SELECTOR___":
            candidates.append(selector)
        candidates.extend([
            "button#onetrust-accept-btn-handler",
            "button[data-testid='cookie-policy-dialog-accept-button']",
            "button.cookie-consent-accept",
            "button[id*='accept']",
            "button[class*='accept']",
            "button[aria-label*='Accept']",
            "button[aria-label*='accept']",
        ])
        for sel in candidates:
            try:
                btn = WebDriverWait(self.driver, 4).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                btn.click()
                logger.info("Dismissed cookies with selector: %s", sel)
                time.sleep(0.5)
                return
            except Exception:
                continue
        logger.info("No cookie banner found or dismissed")

    @staticmethod
    def safe_float(text: str) -> float | None:
        if not text:
            return None
        cleaned = (
            text.replace("€", "")
            .replace("$", "")
            .replace("£", "")
            .replace(",", ".")
            .replace("From", "")
            .replace("Return", "")
            .replace("return", "")
            .strip()
        )
        try:
            return float(cleaned)
        except ValueError:
            return None

    def human_type(self, element, text: str, min_delay: float = 0.05, max_delay: float = 0.15) -> None:
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(min_delay, max_delay))

    def scroll_panel(self, panel_selector: str | None, pause: float = 2.0, max_scrolls: int = 10) -> None:
        for i in range(max_scrolls):
            if panel_selector and panel_selector != "___REPLACE_WITH_ACTUAL_SELECTOR___":
                try:
                    panel = self.driver.find_element(By.CSS_SELECTOR, panel_selector)
                    self.driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight", panel
                    )
                except Exception:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            else:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            logger.debug("Scroll %d/%d", i + 1, max_scrolls)
            time.sleep(pause)
