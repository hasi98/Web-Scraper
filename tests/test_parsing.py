import pytest
import sys
import os

# Add parent directory to path to import scraper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scraper import DataValidator, Book

def test_parse_price():
    val, cur = DataValidator.parse_price("£51.77")
    assert val == 51.77
    assert cur == "£"

    val, cur = DataValidator.parse_price("$10.00")
    assert val == 10.0
    assert cur == "$"

    val, cur = DataValidator.parse_price("100")
    assert val == 100.0
    assert cur == ""

def test_parse_rating():
    assert DataValidator.parse_rating("One") == 1
    assert DataValidator.parse_rating("Three") == 3
    assert DataValidator.parse_rating("Five") == 5
    assert DataValidator.parse_rating("Unknown") == 0

def test_parse_availability():
    in_stock, count = DataValidator.parse_availability("In stock (22 available)")
    assert in_stock is True
    assert count == 22

    in_stock, count = DataValidator.parse_availability("In stock")
    assert in_stock is True
    assert count is None

    in_stock, count = DataValidator.parse_availability("Out of stock")
    assert in_stock is False
    assert count == 0

def test_validate_book():
    book_valid = Book("Title", 10.0, "$", 3, True, 10, "Fiction", "http://example.com")
    is_valid, reason = DataValidator.validate_book(book_valid)
    assert is_valid is True

    book_invalid_price = Book("Title", 0.0, "$", 3, True, 10, "Fiction", "http://example.com")
    is_valid, reason = DataValidator.validate_book(book_invalid_price)
    assert is_valid is False
    assert "price" in reason.lower()

    book_invalid_rating = Book("Title", 10.0, "$", 6, True, 10, "Fiction", "http://example.com")
    is_valid, reason = DataValidator.validate_book(book_invalid_rating)
    assert is_valid is False
    assert "rating" in reason.lower()

    book_no_title = Book("", 10.0, "$", 3, True, 10, "Fiction", "http://example.com")
    is_valid, reason = DataValidator.validate_book(book_no_title)
    assert is_valid is False
    assert "title" in reason.lower()
