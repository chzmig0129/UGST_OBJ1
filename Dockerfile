# VALGEOUGST — Production Dockerfile
# Base: python:3.11-slim (geopandas/shapely/pyproj work better on 3.11 than 3.9)

FROM python:3.11-slim

# System dependencies required to compile geopandas, shapely, and pyproj
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

ENV FLASK_ENV=production

WORKDIR /app

# Install Python dependencies first (layer cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Copy shapefile data directory (253MB — needed at runtime for map rendering)
COPY data/ /app/data/

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
