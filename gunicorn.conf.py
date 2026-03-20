# Gunicorn production configuration for VALGEOUGST
# See: https://docs.gunicorn.org/en/stable/configure.html

bind = '0.0.0.0:8000'

# CRITICAL: Keep workers=2 on an 8GB VPS.
# Each worker loads ~1.2GB of shapefiles into RAM at startup.
# 2 workers x 1.2GB = 2.4GB + OS overhead stays safely within 8GB.
# Do NOT increase workers without upgrading the VPS RAM.
workers = 2

# Use sync workers — geopandas/shapely are CPU-bound and NOT async-safe.
# Do NOT switch to gevent or eventlet; they will cause data corruption.
worker_class = 'sync'

# Shapefile processing can be slow; allow up to 5 minutes per request.
timeout = 300

# Recycle workers periodically to prevent memory leaks from long-running processes.
max_requests = 1000
max_requests_jitter = 50

# Log to stdout/stderr so systemd journal captures everything.
accesslog = '-'
errorlog = '-'

# CRITICAL: preload_app=True loads the application (and all shapefiles) once
# in the master process before forking workers. Workers inherit the loaded data
# via copy-on-write fork semantics, so shapefiles are shared in memory rather
# than each worker loading its own copy. This saves ~1.2GB of RAM per worker
# (i.e., ~1.2GB total savings with 2 workers) and also speeds up worker startup.
# Without this, each worker would independently load all shapefiles, pushing
# total RAM usage to ~3.6GB+ and risking OOM on the 8GB VPS.
preload_app = True
