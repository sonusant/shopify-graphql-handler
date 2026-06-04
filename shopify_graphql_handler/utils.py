import time
import random
from typing import Any, Dict, List


def exponential_backoff(attempt: int, base: float = 1.0, jitter: bool = True) -> float:
    """Calculate backoff delay for a given retry attempt.

    Args:
        attempt: Retry attempt number (starting at 0).
        base: Base delay in seconds.
        jitter: Whether to add random jitter to avoid thundering herd.
    Returns:
        Delay in seconds.
    """
    delay = base * (2 ** attempt)
    if jitter:
        delay += random.uniform(0, base)
    return delay


def flatten_edges(data: Any) -> Any:
    """Recursively replace ``edges`` → ``nodes`` structures.

    Handles typical Shopify pagination shape:
    ``{"edges": [{"node": {...}}, ...]}``
    Returns a list of nodes or the original data if no edges.
    """
    if isinstance(data, dict):
        if "edges" in data and isinstance(data["edges"], list):
            return [flatten_edges(item.get("node")) for item in data["edges"]]
        return {k: flatten_edges(v) for k, v in data.items()}
    if isinstance(data, list):
        return [flatten_edges(item) for item in data]
    return data

