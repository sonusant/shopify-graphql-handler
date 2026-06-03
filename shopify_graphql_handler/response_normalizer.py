import copy
from typing import Any, Dict, List


def _flatten_edges(data: Any) -> Any:
    """Recursively replace any {'edges': [...] } structures with a list of the inner 'node' values.
    Handles nested edges (e.g., connections within connections).
    """
    if isinstance(data, dict):
        if 'edges' in data and isinstance(data['edges'], list):
            # Extract nodes from edges
            nodes = []
            for edge in data['edges']:
                node = edge.get('node')
                if node is not None:
                    nodes.append(_flatten_edges(node))
                else:
                    nodes.append(_flatten_edges(edge))
            return nodes
        return {k: _flatten_edges(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_flatten_edges(item) for item in data]
    return data


def normalize_response(raw_json: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Shopify GraphQL raw response into a unified schema.

    Output format:
    {
        "success": bool,
        "data": any,          # Flattened payload (edges -> nodes)
        "errors": list,        # GraphQL errors or userErrors
        "raw": dict            # Original response for debugging
    }
    """
    response = {
        "success": False,
        "data": None,
        "errors": [],
        "raw": copy.deepcopy(raw_json),
    }

    # HTTP level errors are handled upstream; here we only consider GraphQL payload.
    if 'errors' in raw_json:
        # Top‑level GraphQL errors (e.g., syntax)
        response['errors'].extend(raw_json['errors'])
    if 'data' in raw_json:
        # Flatten any edges structure in the data.
        flattened = _flatten_edges(raw_json['data'])
        response['data'] = flattened
        response['success'] = len(response['errors']) == 0
        # Extract userErrors if present in mutations
        def _collect_user_errors(obj: Any):
            if isinstance(obj, dict):
                for key, val in obj.items():
                    if key == 'userErrors' and isinstance(val, list):
                        response['errors'].extend(val)
                    else:
                        _collect_user_errors(val)
            elif isinstance(obj, list):
                for item in obj:
                    _collect_user_errors(item)
        _collect_user_errors(raw_json['data'])
        # If any userErrors were found, success should reflect that.
        if response['errors']:
            response['success'] = False
    else:
        response['success'] = False
    return response
