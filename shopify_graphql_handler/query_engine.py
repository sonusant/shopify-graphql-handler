"""query_engine.py

High‑level query interface for the Shopify GraphQL SDK.

The public API mirrors the requirement:

```python
client.query(
    query="products { id title }",
    variables={},
    auto_paginate=False,
)
```

If ``auto_paginate=True`` the function delegates to the generic pagination
utility which repeatedly calls the underlying ``ShopifyClient`` until all
pages have been retrieved.
"""

from typing import Any, Dict, List, Optional

from .client import ShopifyClient
from .error_handler import raise_for_response
from .pagination import paginate


class QueryEngine:
    """Provides ``query`` functionality for the SDK.

    Parameters
    ----------
    client: ShopifyClient
        Instance of the low‑level HTTP client.
    """

    def __init__(self, client: ShopifyClient):
        self.client = client

    def query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        auto_paginate: bool = False,
    ) -> Any:
        """Execute a GraphQL query.

        If ``auto_paginate`` is ``True`` the function will automatically walk
        through cursor‑based pagination and return a **flattened** list of results.
        Otherwise a single request is performed and the normalized response is
        returned.
        """
        variables = variables or {}
        if auto_paginate:
            # Use the pagination helper which returns a flat list.
            return paginate(self.client, query, variables)
        # Single‑request path – call the client and normalise / raise errors.
        raw_response = self.client._post({"query": query, "variables": variables})
        normalized = raise_for_response(raw_response)
        return normalized["data"]
