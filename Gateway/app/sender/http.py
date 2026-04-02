"""
http.py – Send driver events via HTTP POST (fallback / alternative to WebSocket).

Useful when the backend does not expose a WebSocket endpoint,
or as a reliability fallback when the WS connection is down.
"""

import json

import requests
from app.utils.config import SenderConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 5.0  # seconds


def send_event_http(payload: dict, cfg: SenderConfig) -> bool:
    """
    POST a driver event payload to the configured HTTP endpoint.

    Args:
        payload: Dict matching the agreed event schema, e.g.:
                 {"device_id": "car_01", "event": "normal", "confidence": 0.9}
        cfg:     Sender configuration (http_url, etc.)

    Returns:
        True if the server responded with 2xx, False otherwise.
    """
    try:
        response = requests.post(
            cfg.http_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=_DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        logger.debug("HTTP POST %s → %d", cfg.http_url, response.status_code)
        return True
    except requests.exceptions.Timeout:
        logger.error("HTTP POST timed out after %.1f s", _DEFAULT_TIMEOUT)
    except requests.exceptions.ConnectionError as exc:
        logger.error("HTTP connection error: %s", exc)
    except requests.exceptions.HTTPError as exc:
        logger.error("HTTP server error: %s", exc)
    except Exception as exc:
        logger.error("Unexpected HTTP error: %s", exc)
    return False
