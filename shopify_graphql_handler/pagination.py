"""pagination.py

Utility functions to handle cursor‑based pagination for Shopify GraphQL queries.

The `paginate` function repeatedly executes a GraphQL query, injecting the `after`
cursor into the variables dict. It stops when `pageInfo.hasNextPage` is false and
returns a flat list of results, using the response normalizer to flatten any
`edges → node` structures.
"""

from typing import Any, Dict, List, Optional

from .client import ShopifyClient
from .response_normalizer import normalize_response


def _inject_cursor(variables: Optional[Dict[str, Any]], cursor: Optional[str]) -> Dict[str, Any]:
    """Return a copy of variables with the `after` cursor injected.

    The caller may pass ``None`` for ``variables`` – in that case an empty
    dictionary is created. ``cursor`` may be ``None`` for the first request.
    """
    vars_copy = dict(variables or {})
    if cursor is not None:
        vars_copy["after"] = cursor
    return vars_copy


def paginate(
    client: ShopifyClient,
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    page_size: int = 250,
) -> List[Any]:
    """Execute ``query`` repeatedly until all pages are retrieved.

    Parameters
    ----------
    client:
        An instance of :class:`ShopifyClient` used to perform the HTTP POST.
    query:
        GraphQL query string. It must request a ``pageInfo`` field with
        ``hasNextPage`` and ``endCursor`` so the paginator can decide when to
        stop.
    variables:
        Optional variable mapping passed to the GraphQL request. The function
        will add an ``after`` key for pagination.
    page_size:
        Optional hint for the number of records per page. Shopify defaults to
        250 for many connections; the value is added as ``first`` in the
        variables dict if not already present.

    Returns
    -------
    list
        A flat list containing the merged ``edges → node`` payloads from every
        page.
    """
    all_items: List[Any] = []
    cursor: Optional[str] = None
    # Ensure ``first`` is set to the desired page size.
    base_vars = dict(variables or {})
    base_vars.setdefault("first", page_size)

    while True:
        # Merge cursor into variables for this request.
        request_vars = _inject_cursor(base_vars, cursor)
        raw_response = client._post({"query": query, "variables": request_vars})
        # Raise on top-level GraphQL errors
        if raw_response.get("errors"):
            raise RuntimeError(f"Pagination request failed: {raw_response['errors']}")
        data = raw_response.get("data", {})
        # The GraphQL response shape is not known upfront – we look for the
        # first dict that contains ``edges`` or ``nodes``.
        def _extract_collection(container: Any) -> List[Any]:
            # Handle dicts that contain `edges` or `nodes`.
            if isinstance(container, dict):
                if "edges" in container and isinstance(container["edges"], list):
                    items = []
                    for edge in container["edges"]:
                        # edge may be a dict with 'node'
                        if isinstance(edge, dict) and "node" in edge:
                            items.append(edge.get("node"))
                        else:
                            items.append(edge)
                    return items
                if "nodes" in container and isinstance(container["nodes"], list):
                    return container["nodes"]
                # Recurse into values to find a nested collection.
                for v in container.values():
                    result = _extract_collection(v)
                    if result:
                        return result
                return []
            # If the container is already a list of nodes, return it.
            if isinstance(container, list):
                # Normalize any edges present in list items
                items = []
                for item in container:
                    if isinstance(item, dict) and "node" in item:
                        items.append(item.get("node"))
                    else:
                        items.append(item)
                return items
            return []

        page_items = _extract_collection(data)
        all_items.extend(page_items)

        # Find pagination info – look for a dict with ``pageInfo``.
        def _find_page_info(obj: Any) -> Optional[Dict[str, Any]]:
            if isinstance(obj, dict):
                if "pageInfo" in obj and isinstance(obj["pageInfo"], dict):
                    return obj["pageInfo"]
                for v in obj.values():
                    info = _find_page_info(v)
                    if info:
                        return info
            return None

        page_info = _find_page_info(data)
        if not page_info or not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    return all_items

"""End of pagination module"""
