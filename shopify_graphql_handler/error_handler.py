"""error_handler.py

Utility functions for converting normalized responses into appropriate exceptions.

The SDK primarily works with the unified schema returned by
``response_normalizer.normalize_response`` which contains the keys:

* ``success`` – ``True`` when no GraphQL or ``userErrors`` were present.
* ``data``    – The (flattened) payload when available.
* ``errors``  – List of error objects from GraphQL ``errors`` or mutation ``userErrors``.
* ``raw``     – The original JSON response for debugging.

The helpers below raise a ``ShopifyError`` (or a subclass) when the response
indicates failure, making it convenient for callers that prefer exception‑
based error handling.
"""

from .exceptions import ShopifyError, UserError, PartialMutationError
from .response_normalizer import normalize_response
from typing import Any, Dict


def raise_for_response(raw_response: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a raw GraphQL response and raise on failure.

    Parameters
    ----------
    raw_response: dict
        The JSON payload returned by the Shopify GraphQL endpoint.

    Returns
    -------
    dict
        The same dictionary if ``success`` is ``True``.

    Raises
    ------
    UserError
        When ``userErrors`` are present in a mutation payload.
    ShopifyError
        For any other GraphQL ``errors`` or when ``success`` is ``False``.
    """
    normalized = normalize_response(raw_response)
    if normalized["success"]:
        return normalized
    # ``errors`` may contain a mixture of GraphQL errors and userErrors.
    # UserErrors are typically dicts with ``field`` and ``message`` keys.
    user_errors = [e for e in normalized["errors"] if isinstance(e, dict) and "message" in e]
    if user_errors:
        # For mutations we want a PartialMutationError that still carries data.
        raise PartialMutationError(
            "Mutation completed with user errors",
            data=normalized.get("data"),
            errors=user_errors,
        )
    # Fallback to generic ShopifyError with a concatenated message.
    messages = [e.get("message", str(e)) if isinstance(e, dict) else str(e) for e in normalized["errors"]]
    raise ShopifyError(" | ".join(messages))
