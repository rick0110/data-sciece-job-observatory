from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
import shutil
import logging
import time
from pathlib import Path
import json

def scrape_from_linkedin(
    url: str,
    headless: bool = True,
    wait: int = 3,
    cookies_path: str | None = None
) -> list[dict]:
    """Scrape job postings from a LinkedIn search URL.
    
    Args:
        url: The LinkedIn jobs search URL to scrape.
        headless: Whether to run the browser in headless mode.
        wait: Seconds to wait after clicking elements.
        cookies_path: Optional path to a cookies file (currently unused).
        
    Returns:
        A list of dictionaries containing job details (company, role, etc.).
    """
    
    # Persistent profile dir so a LinkedIn login survives between scrape
    # runs. Must be portable across machines/users (previously hardcoded to
    # a `/home/richa/...` path that only existed on one developer's machine).
    profile_dir = Path.home() / ".cache" / "selenium-linkedin-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    opts = Options()
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument("--profile-directory=Default")

    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--remote-debugging-port=9222")
    opts.add_argument("--window-size=1200,900")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--no-zygote")

    # Locate a Chrome/Chromium binary in PATH and set it if found.
    chrome_candidates = ("/usr/bin/chromium-browser", "google-chrome", "google-chrome-stable", "chromium-browser", "chromium")
    chrome_path = next((Path(name).as_posix() if Path(name).exists() else shutil.which(name) for name in chrome_candidates), None)
    if chrome_path:
        opts.binary_location = chrome_path
    else:
        logging.warning("No Chrome/Chromium binary found in PATH; set `opts.binary_location` manually if needed.")

    
    # Prefer Selenium Manager to fetch the correct driver for the installed browser.
    try:
        driver = webdriver.Chrome(options=opts)
    except Exception as sm_err:
        logging.warning("Selenium Manager failed, falling back to webdriver_manager: %s", sm_err)
        service = Service(ChromeDriverManager().install())
        try:
            driver = webdriver.Chrome(service=service, options=opts)
        except WebDriverException:
            # Attach helpful diagnostics to the raised exception
            logging.exception(
                "Failed to start Chrome WebDriver. chrome_path=%s chromedriver=%s",
                chrome_path,
                getattr(service, 'path', str(service)),
            )
            raise

    # Navigate to the target page
    driver.get(url)
    time.sleep(wait)

    def get_data_from_page(driver: webdriver.Chrome, _list_of_dicts: list[dict] | None = None) -> list[dict]:
        """Extract data from all job cards on the current page.
        
        Args:
            driver: The active WebDriver instance.
            _list_of_dicts: Accumulated list of job details from previous pages.
            
        Returns:
            A list of dictionaries containing job details.
        """
        if _list_of_dicts:
            results = _list_of_dicts
        else:
            results = []
        try:
            card_selector = ".occludable-update"
            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, card_selector)))

            job_cards = driver.find_elements(By.CSS_SELECTOR, card_selector)
            print(f"Found {len(job_cards)} job cards, processing...")
            for index, card in enumerate(job_cards):
                try:
                    card.click()
                    time.sleep(wait)
                    parsed = {}
                    try:
                        company_selector = ".job-details-jobs-unified-top-card__company-name"
                        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, company_selector)))
                        parsed["company"] = driver.find_element(By.CSS_SELECTOR, company_selector).text
                    except Exception:
                        parsed["company"] = None

                    try:
                        position_selector = ".t-24"
                        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, position_selector)))
                        parsed["raw_position"] = driver.find_element(By.CSS_SELECTOR, position_selector).text
                    except Exception:
                        parsed["raw_position"] = None

                    try:
                        location_selector = "//div[contains(@class, 'tertiary-description-container')]//span[1]"
                        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, location_selector)))
                        location = driver.find_element(By.XPATH, location_selector)
                        parsed["raw_location"] = location.text
                    except Exception:
                        parsed["raw_location"] = None

                    try:
                        parsed["raw_html_description"] = driver.find_element(By.ID, "job-details").text
                    except Exception:
                        parsed["raw_html_description"] = None
                    results.append(parsed)
                except Exception:
                    print("Failed to process a job card, skipping.")
                    continue
        except Exception:
            return results
        
        try:
            next_button_selector = ".jobs-search-pagination__button--next"
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, next_button_selector)))
            next_button = driver.find_element(By.CSS_SELECTOR, next_button_selector)
            next_button.click()
            results = get_data_from_page(driver, results)
            time.sleep(wait)
        except:
            print("No next button found, finishing.")
            pass

        return results
    
    try:
        results = get_data_from_page(driver)

    finally:
        driver.quit()
        
    return results