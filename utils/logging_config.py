"""
Logging configuration for the Flask application.

- Development: StreamHandler to stdout, level=DEBUG, simple format
- Production: StreamHandler to stdout (for Docker/systemd journal), level=INFO,
  format includes timestamp, level, module, and message
"""

import logging
import sys


def setup_logging(app):
    """Configure Python logging based on app.debug flag.

    Args:
        app: The Flask application instance.
    """
    # Remove any handlers that Flask or Werkzeug may have already attached
    # so we don't get duplicate log lines.
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)

    if app.debug:
        # Development: verbose, human-friendly output
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "[%(levelname)s] %(name)s: %(message)s"
        )
        app.logger.setLevel(logging.DEBUG)
    else:
        # Production: structured output suitable for Docker / systemd journal
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(module)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        app.logger.setLevel(logging.INFO)

    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    # Propagate to the root logger so Werkzeug / SQLAlchemy messages also flow
    app.logger.propagate = False
