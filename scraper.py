import argparse
import csv
import json
import logging
import os
import random
import sqlite3
import time
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin

import yaml
from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class UniversalScraper:
    """
    Advanced configuration-driven web scraper using Playwright automation.
    """
    def __init__(
            self,
            profile_path: str,
            delay: float = 1.0,
            retries: int = 3,
            max_workers: int = 1, # Kept for signature compatibility but ignored (sequential)
            resume: bool = False,
            start_url_override: str = None
    ):
        self.delay = delay
        self.retries = retries
        self.resume = resume
        
        # Load profile
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile not found: {profile_path}")
        with open(profile_path, "r", encoding="utf-8") as f:
            self.profile = yaml.safe_load(f)
            
        self.start_url = start_url_override if start_url_override else self.profile.get("start_url")
        self.base_url = "/".join(self.start_url.split("/")[:3]) + "/"
        
        self.state_file = f".scrape_state_{os.path.basename(profile_path)}.json"
        self.visited_urls = set()
        if self.resume and os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    self.visited_urls = set(json.load(f))
                logger.info(f"Resuming scrape. Loaded {len(self.visited_urls)} visited list page URLs.")
            except Exception as e:
                logger.error(f"Failed to load state file: {e}")

    def _save_state(self, url: str):
        self.visited_urls.add(url)
        try:
            with open(self.state_file, "w") as f:
                json.dump(list(self.visited_urls), f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _fetch_page_content(self, page, url: str, wait_selector: str = None) -> Optional[str]:
        jitter = random.uniform(self.delay * 0.5, self.delay * 1.5) if self.delay > 0 else 0
        for attempt in range(1, self.retries + 1):
            try:
                if jitter > 0:
                    time.sleep(jitter)
                # Use "load" instead of "domcontentloaded" so all assets finish
                page.goto(url, wait_until="load", timeout=45000)
                
                if wait_selector:
                    try:
                        # Wait specifically for our item container to pop into existence
                        page.wait_for_selector(wait_selector, timeout=10000)
                    except Exception:
                        logger.warning(f"Selector '{wait_selector}' did not appear in time.")
                        
                time.sleep(2) # Extra buffer for JS mutation
                
                # If page is still redirecting, wait a moment before trying to grab content
                for _ in range(3):
                    try:
                        return page.content()
                    except Exception as e:
                        if "navigating" in str(e).lower():
                            time.sleep(2)
                        else:
                            raise e
                            
                return page.content()
            except PlaywrightTimeoutError:
                logger.warning(f"Attempt {attempt}/{self.retries} timeout for {url}")
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.retries} failed for {url}: {e}")
                
            if attempt == self.retries:
                logger.error(f"Max retries reached for {url}.")
                return None
            time.sleep(2 ** attempt)
        return None
        
    def _extract_field(self, element: BeautifulSoup, field_config: dict) -> str:
        """Extracts data from a BS4 element based on YAML rules."""
        selector = field_config.get("selector")
        attr = field_config.get("attribute", "text")
        
        target = element.select_one(selector)
        if not target:
            return ""
            
        if attr == "text":
            return target.text.strip()
        else:
            val = target.get(attr, "")
            if isinstance(val, list):
                return " ".join(val).strip()
            return str(val).strip()

    def scrape(self, max_pages: Optional[int] = None, progress_callback=None, stop_event=None) -> Tuple[List[dict], List[dict]]:
        valid_items = []
        errors = []
        
        current_page = 1
        current_url = self.start_url
        pages_scraped = 0
        
        fetch_detail = self.profile.get("fetch_detail_page", False)
        container_sel = self.profile.get("item_container_selector")
        fields_config = self.profile.get("fields", {})
        
        # Start Playwright Engine
        with sync_playwright() as p:
            logger.info("Launching Playwright Chromium browser (Headed Mode)...")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            Stealth().apply_stealth_sync(page)

            while True:
                if stop_event and stop_event.is_set():
                    logger.info("Scrape interrupted by user.")
                    break
                    
                if max_pages and pages_scraped >= max_pages:
                    logger.info(f"Reached max pages limit ({max_pages}).")
                    break

                if self.resume and current_url in self.visited_urls:
                    logger.info(f"Skipping already scraped page: {current_url}")
                    html = self._fetch_page_content(page, current_url, wait_selector=container_sel)
                    if not html: break
                    soup = BeautifulSoup(html, "lxml")
                else:
                    logger.info(f"Scraping list page {current_page}: {current_url}")
                    html = self._fetch_page_content(page, current_url, wait_selector=container_sel)
                    if not html: break
                    soup = BeautifulSoup(html, "lxml")
                    
                    elements = soup.select(container_sel)
                    if not elements:
                        logger.info("No items found on current page. Ending scrape.")
                        break
                        
                    detail_tasks = []
                    
                    # Parse list page items
                    for el in elements:
                        try:
                            item_data = {}
                            for f_name, f_config in fields_config.items():
                                item_data[f_name] = self._extract_field(el, f_config)
                                
                            if fetch_detail:
                                detail_link_sel = self.profile.get("detail_link_selector")
                                detail_link_attr = self.profile.get("detail_link_attribute")
                                link_el = el.select_one(detail_link_sel)
                                if link_el and link_el.has_attr(detail_link_attr):
                                    detail_url = urljoin(current_url, link_el[detail_link_attr])
                                    detail_tasks.append((detail_url, item_data))
                                else:
                                    errors.append({"url": current_url, "reason": "Detail link not found"})
                            else:
                                item_data["source_list_url"] = current_url
                                valid_items.append(item_data)
                        except Exception as e:
                            errors.append({"url": current_url, "reason": f"List parse error: {e}"})

                    # Sequential fetching for detail pages to save RAM
                    if fetch_detail and detail_tasks:
                        logger.info(f"Fetching {len(detail_tasks)} detail pages sequentially...")
                        for detail_url, item_data in detail_tasks:
                            if stop_event and stop_event.is_set():
                                break
                            
                            detail_html = self._fetch_page_content(page, detail_url)
                            if detail_html:
                                detail_soup = BeautifulSoup(detail_html, "lxml")
                                try:
                                    detail_fields = self.profile.get("detail_fields", {})
                                    for field_name, config in detail_fields.items():
                                        item_data[field_name] = self._extract_field(detail_soup, config)
                                    item_data["url"] = detail_url
                                    valid_items.append(item_data)
                                except Exception as e:
                                    errors.append({"url": detail_url, "reason": f"Detail parse error: {e}"})
                            else:
                                errors.append({"url": detail_url, "reason": "Failed to fetch detail page"})
                                
                    if stop_event and stop_event.is_set():
                        break
                                
                    self._save_state(current_url)
                    pages_scraped += 1
                    if progress_callback:
                        progress_callback(pages_scraped, max_pages)

                # Pagination
                pag_conf = self.profile.get("pagination", {})
                next_btn = soup.select_one(pag_conf.get("next_button_selector", ""))
                if next_btn and next_btn.has_attr(pag_conf.get("url_attribute", "href")):
                    next_url = next_btn[pag_conf.get("url_attribute", "href")]
                    current_url = urljoin(current_url, next_url)
                    current_page += 1
                else:
                    break

            if not max_pages and os.path.exists(self.state_file):
                try: os.remove(self.state_file)
                except OSError: pass
                
            browser.close()

        return valid_items, errors

    def export_csv(self, data: List[dict], filename: str) -> None:
        if not data: return
        try:
            with open(filename, mode="w", newline="", encoding="utf-8") as file:
                fieldnames = list(data[0].keys())
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            logger.info(f"Exported {len(data)} items to CSV")
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")

    def export_json(self, data: List[dict], filename: str) -> None:
        if not data: return
        try:
            with open(filename, mode="w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            logger.info(f"Exported {len(data)} items to JSON")
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")

    def export_sqlite(self, data: List[dict], filename: str) -> None:
        if not data: return
        try:
            conn = sqlite3.connect(filename)
            cursor = conn.cursor()
            
            keys = list(data[0].keys())
            cols = ", ".join([f"{k} TEXT" for k in keys])
            
            cursor.execute(f"CREATE TABLE IF NOT EXISTS items ({cols})")
            
            placeholders = ", ".join(["?"] * len(keys))
            query = f"INSERT INTO items ({', '.join(keys)}) VALUES ({placeholders})"
            
            for item in data:
                cursor.execute(query, tuple(str(item.get(k, "")) for k in keys))
                
            conn.commit()
            conn.close()
            logger.info(f"Exported {len(data)} items to SQLite DB")
        except Exception as e:
            logger.error(f"Failed to export SQLite: {e}")

    def export_errors(self, errors: List[dict], filename: str = "errors.csv") -> None:
        if not errors: return
        try:
            with open(filename, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=["url", "reason"])
                writer.writeheader()
                for err in errors:
                    err.setdefault("url", "")
                    err.setdefault("reason", "")
                    writer.writerow(err)
            logger.warning(f"Exported {len(errors)} error records to {filename}")
        except Exception as e:
            logger.error(f"Failed to export errors: {e}")

def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to parse config file: {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description="Universal Configuration-Driven Scraper Engine (Playwright)")
    parser.add_argument("--profile", type=str, required=True, help="Path to YAML site profile")
    parser.add_argument("--config", type=str, help="Path to YAML engine config")
    parser.add_argument("--pages", type=int, help="Maximum number of pages to scrape")
    parser.add_argument("--output", type=str, help="Output filename (.csv, .json, .db)")
    parser.add_argument("--delay", type=float, help="Delay (jitter base) between requests in seconds")
    parser.add_argument("--retries", type=int, help="Number of retries for failed requests")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint state")

    args = parser.parse_args()

    config = load_config(args.config) if args.config else {}

    output = args.output or config.get("output", "data.csv")
    delay = args.delay if args.delay is not None else config.get("delay", 1.0)
    retries = args.retries if args.retries is not None else config.get("retries", 3)
    resume = args.resume or config.get("resume", False)

    scraper = UniversalScraper(
        profile_path=args.profile,
        delay=delay,
        retries=retries,
        resume=resume
    )
    
    logger.info(f"Initializing Playwright Engine with profile: {scraper.profile.get('name')}")
    start_time = time.time()
    
    valid_items, errors = scraper.scrape(max_pages=args.pages)
    
    end_time = time.time()
    runtime = end_time - start_time
    
    if output.lower().endswith(".json"):
        scraper.export_json(valid_items, output)
    elif output.lower().endswith(".db"):
        scraper.export_sqlite(valid_items, output)
    else:
        scraper.export_csv(valid_items, output)
        
    if errors:
        scraper.export_errors(errors, "errors.csv")
        
    logger.info("\n=== RUN SUMMARY ===")
    logger.info(f"Total valid items collected : {len(valid_items)}")
    logger.info(f"Total invalid/error items : {len(errors)}")
    logger.info(f"Total runtime (seconds)     : {runtime:.2f}")
    if valid_items:
        logger.info(f"Average time per valid item : {runtime / len(valid_items):.2f}s")
    logger.info("===================\n")

if __name__ == "__main__":
    main()
