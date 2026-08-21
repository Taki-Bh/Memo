# navigator.py

from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Page
from core.exceptions import AppException, LLMException, LLMConfigurationError, LLMAuthenticationError, LLMRequestError, LLMResponseError, APIKeyMissingError,ConnectionError

class Browser:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance
    def __init__(self, user_data_dir: str = "user_data"):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.user_data_dir = Path(user_data_dir)
       
        self._playwright = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.browser_name: str | None = None

    def start(self, headless: bool = False):
        """Start a persistent browser context.

        Tries Chromium first. Falls back to Firefox if Chromium fails.
        """

        if self.context is not None:
            return self.page

        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = sync_playwright().start()

        # Try Chromium first
        try:
            print("Starting Chromium...")

            self.context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=headless,
            )

            self.browser_name = "chromium"
            print("Chromium started.")

        except Exception as chromium_error:
            print(f"Chromium failed: {chromium_error}")
            print("Trying Firefox...")

            # Clean up failed Chromium attempt
            self.context = None

            try:
                self.context = self._playwright.firefox.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=headless,
                )

                self.browser_name = "firefox"
                print("Firefox started.")

            except Exception:
                self._playwright.stop()
                self._playwright = None
                raise

        # Reuse an existing page if one exists
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        return self.page

    def goto(self, url: str,timeout: int = 30000):
        self._ensure_started()
        try:
            self.page.goto(url,wait_until="domcontentloaded",timeout=timeout)
            self.page.wait_for_load_state("load")
            print("dom content loaded!")
        except Exception as e:
            raise ConnectionError (e)

    def back(self):
        self._ensure_started()
        self.page.go_back()

    def forward(self):
        self._ensure_started()
        self.page.go_forward()

    def reload(self):
        self._ensure_started()
        self.page.reload()

    def current_url(self) -> str:
        self._ensure_started()
        return self.page.url

    def new_page(self) -> Page:
        self._ensure_started()
        self.page = self.context.new_page()
        return self.page

    def close(self):
        """Close the browser but keep the persistent profile."""

        if self.context:
            self.context.close()
            self.context = None
            self.page = None

        if self._playwright:
            self._playwright.stop()
            self._playwright = None

        self.browser_name = None

    def _ensure_started(self):
        if self.page is None:
            raise RuntimeError(
                "Browser is not started. Call navigator.start() first."
            )


# Shared instance
