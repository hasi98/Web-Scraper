FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set the entrypoint to run the scraper script
ENTRYPOINT ["python", "scraper.py"]
# Provide default arguments if none are passed
CMD ["--help"]
