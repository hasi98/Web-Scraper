# Books.toscrape.com Advanced Scraper

A production-ready, portfolio-grade Python web scraper designed to extract book information from [books.toscrape.com](https://books.toscrape.com/). This project has been heavily upgraded to demonstrate advanced scraping architectures, robust data engineering, and modern CI/CD practices.

## What it does
This scraper is a **Universal Configuration-Driven Engine**. Instead of hardcoding HTML tags (like `<h3>` or `class="price"`), the engine reads declarative YAML "Profiles" which define the CSS selectors for the target site. This means you can scrape a completely new website without writing a single line of Python code—you just write a small YAML profile!

By default, this repository comes with profiles for:
- `books.toscrape.com` (Extracts title, price, rating, availability, and deep-crawls for category)
- `quotes.toscrape.com` (Extracts text, author, and tags)

## Advanced Features & Skills Demonstrated
This project serves as a showcase for enterprise-grade data extraction architecture:
- **Configuration-Driven Design**: Complete decoupling of parsing logic from the engine. CSS selectors and field definitions are loaded dynamically at runtime via YAML profiles.
- **Dynamic Schemas**: SQLite tables, CSV headers, and JSON keys are automatically generated based on the fields defined in the loaded profile.
- **Concurrency**: Utilizes `concurrent.futures.ThreadPoolExecutor` for parallel deep-crawling of detail pages, drastically reducing scrape times.
- **Polite Crawling**: Implements a randomized jitter per worker thread combined with exponential backoff for failed requests. Checks `robots.txt` compliance before starting via `urllib.robotparser`.
- **Error Quarantining**: Faulty records don't crash the script—they are logged as warnings and written to a separate `errors.csv` for inspection. 
- **State Checkpointing**: Supports a `--resume` flag that loads visited URLs from a profile-specific `.scrape_state.json` file, allowing you to restart aborted long-running scrapes.
- **Configuration Management**: Uses `pyyaml` to load default settings from `config.yaml`, which can be overridden via `argparse` CLI flags.
- **Docker & CI/CD**: Includes a `Dockerfile` for containerized runs and a GitHub Actions workflow (`.github/workflows/ci.yml`).

## Installation

1. Clone the repository.
2. (Optional but recommended) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the scraper using the command-line interface.

```bash
python scraper.py --help
```

### CLI Arguments
- `--config`: Path to YAML config file (default: looks for `config.yaml` values)
- `--pages`: Limit the number of pages to scrape (default: all pages).
- `--output`: Output filename. Supports `.csv`, `.json`, and `.db` extensions (default: `data.csv`).
- `--delay`: Base delay/jitter between requests in seconds to be polite (default: `1.0`).
- `--max-workers`: Maximum concurrent threads for detail pages (default: `5`).
- `--retries`: Number of retries for failed requests with exponential backoff (default: `3`).
- `--resume`: If set, continues scraping from the last checkpoint instead of starting over.

### Examples

**1. Fast run testing 2 pages to SQLite database**
```bash
python scraper.py --pages 2 --max-workers 5 --delay 0.1 --output library.db
```

**2. Safe, resumable run across entire catalog**
```bash
python scraper.py --resume --output all_books.json
```

## Running the GUI App (New!)
A modern graphical interface is now included. It features a sleek dark mode, live progress bars, and a scrolling log console!

To launch it:
```bash
python gui.py
```

## Running Tests
Run the `pytest` test suite:
```bash
pytest
```

## Running with Docker
Build and run the scraper in an isolated container:
```bash
docker build -t book-scraper .
docker run --rm -v $(pwd):/app book-scraper --pages 2 --output docker_test.csv
```
