import pytest
import sys
import os
from bs4 import BeautifulSoup

# Add parent directory to path to import scraper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scraper import load_config, UniversalScraper

def test_load_config():
    # Test that load_config handles missing files gracefully
    config = load_config("nonexistent_config.yaml")
    assert config == {}

def test_extract_field():
    # Setup dummy scraper instance
    scraper = UniversalScraper(profile_path="profiles/quotes.yaml")
    
    html = """
    <div class="quote">
        <span class="text">"Hello World"</span>
        <small class="author">John Doe</small>
        <a class="link" href="/author/johndoe">About</a>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    quote_el = soup.select_one("div.quote")
    
    # Test text extraction
    text_config = {"selector": "span.text", "attribute": "text"}
    assert scraper._extract_field(quote_el, text_config) == '"Hello World"'
    
    # Test attribute extraction
    link_config = {"selector": "a.link", "attribute": "href"}
    assert scraper._extract_field(quote_el, link_config) == "/author/johndoe"
    
    # Test missing element
    missing_config = {"selector": "div.nonexistent", "attribute": "text"}
    assert scraper._extract_field(quote_el, missing_config) == ""
