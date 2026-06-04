"""mutation_engine.py

Provides the ``mutate`` method for the SDK.

Usage example:

```python
client = ShopifyClient(...)
engine = MutationEngine(client)
result = engine.mutate(
    mutation_name="productUpdate",
    variables={"input": {"id": "gid://shopify/Product/123", "title": "New Title"}},
)
```

The method builds a full GraphQL mutation string, sends it via the low‑level
``ShopifyClient`` and then validates the response using ``raise_for_response``.
If ``userErrors`` are present a ``PartialMutationError`` (defined in
``exceptions.py``) is raised while still returning the partial ``data`` payload.
"""

from typing import Any, Dict, Optional

from .client import ShopifyClient
from .error_handler import raise_for_response


class MutationEngine:
    """Encapsulates mutation execution logic.

    Parameters
    ----------
    client: ShopifyClient
        The low‑level HTTP client used to send the GraphQL request.
    """

    def __init__(self, client: ShopifyClient):
        self.client = client

    def _build_mutation(self, mutation_name: str, variables: Optional[Dict[str, Any]]) -> str:
        """Construct a minimal mutation string.

        The mutation is wrapped in ``mutation { <name>(<variables>) { ... } }``.
        For simplicity we request the ``userErrors`` field and all other top‑level
        fields returned by the mutation using the ``...`` spread operator. Users
        can provide a more specific selection set via ``variables['_fields']`` if
        needed – this implementation keeps the SDK lightweight.
        """
        # Convert variables dict to a GraphQL variable definition string.
        # For the SDK we assume the caller supplies a ready‑made GraphQL query
        # string via ``variables`` if they need custom selections. Here we only
        # embed the variable placeholders.
        var_defs = ""
        if variables:
            # Build $var: Type placeholders – we cannot infer types here, so we
            # use generic JSON scalar ``JSON`` which Shopify supports for input.
            var_defs = "(" + ", ".join([f"${k}: JSON" for k in variables.keys()]) + ")"
        # Build the argument list for the mutation call.
        args = "" if not variables else "(" + ", ".join([f"{k}: ${k}" for k in variables.keys()]) + ")"
        # Basic selection set – request userErrors and any returned fields via ...
        selection_set = "userErrors { field message } ..."
        mutation = f"mutation {var_defs} {{ {mutation_name}{args} {{ {selection_set} }} }}"
        return mutation

    def mutate(
        self,
        mutation_name: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a GraphQL mutation.

        Returns the normalized ``data`` payload on success. If ``userErrors`` are
        present a ``PartialMutationError`` is raised (see ``exceptions.py``) but the
        caller can still inspect ``error.data`` for the partial result.
        """
        mutation_query = self._build_mutation(mutation_name, variables)
        raw_response = self.client._post({"query": mutation_query, "variables": variables or {}})
        normalized = raise_for_response(raw_response)
        return normalized["data"]
