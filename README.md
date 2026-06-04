# Shopify GraphQL SDK

---

## Problem Statement

Shopify’s GraphQL Admin API is powerful but notoriously **verbose and error‑prone**. Consumers must manually:
- Construct GraphQL queries and mutations.
- Add authentication headers (`X‑Shopify‑Access‑Token`).
- Implement retry & exponential back‑off for rate‑limit (429) responses.
- Parse the nested `edges → node` pagination structures.
- Detect and surface GraphQL `errors` and mutation `userErrors`.

All of these steps repeat across projects, increase boilerplate, and make testing harder. This SDK provides a **thin, production‑grade abstraction** that hides that complexity behind a clean, Pythonic API.

---

## Architecture Overview

```
shopify_graphql/
├─ __init__.py          # public API (ShopifyClient)
├─ client.py           # low‑level HTTP wrapper (auth, retries)
├─ response_normalizer.py
│   └─ normalize_response() → unified schema
├─ pagination.py       # cursor‑based paginate() utility
├─ query_engine.py     # QueryEngine.query(..., auto_paginate)
├─ mutation_engine.py  # MutationEngine.mutate(...)
├─ error_handler.py    # raise_for_response() → exceptions
└─ exceptions.py      # custom exception hierarchy
```

- **`ShopifyClient`** handles raw HTTP requests, authentication, and retry logic (3 attempts, 1‑2‑4 s back‑off).
- **`QueryEngine`** and **`MutationEngine`** expose the user‑facing `query`/`mutate` methods.
- **`Response Normalizer`** consolidates GraphQL errors, `userErrors`, and flattens `edges` into a unified schema `{ "success": bool, "data": any, "errors": list, "raw": dict }`.
- **`Pagination`** abstracts the cursor loop and returns a flat list of items.
- **`Error Handler`** converts normalized responses into domain‑specific exceptions (`RateLimitError`, `AuthenticationError`, `UserError`, `PartialMutationError`).

---

## Quick Start

```python
from shopify_graphql import ShopifyClient, QueryEngine, MutationEngine

# Initialise the client with a private‑app token. Pin `api_version` to a
# supported release to avoid 404s (e.g. "2025-01" or "2024-10").
client = ShopifyClient(
    shop_name="myshop",
    access_token="shpat_XXXXXXXXXXXXXXXX",
    api_version="2025-01",
)

# Compose engines
query_engine = QueryEngine(client)
mutation_engine = MutationEngine(client)

# Auto‑paginated query – fetch all products (returns a flattened list)
query = """
query ($first: Int, $after: String) {
  products(first: $first, after: $after) {
    edges { node { id title } }
    pageInfo { hasNextPage endCursor }
  }
}
"""

# Use `auto_paginate=True` to fetch all pages and receive a flat list of nodes
products = query_engine.query(query, variables={"first": 250}, auto_paginate=True)
print(f"Fetched {len(products)} products")

# Mutation example – update a product title
result = mutation_engine.mutate(
    mutation_name="productUpdate",
    variables={"input": {"id": "gid://shopify/Product/12345", "title": "New Title"}},
)
print(result)
```

Quick notes:
- `QueryEngine.query(..., auto_paginate=False)` performs a single request and returns the normalized `data` dict (e.g. `{"products": [...]}`); access the list via `result["products"]`.
- `QueryEngine.query(..., auto_paginate=True)` returns a flattened `list` of nodes from all pages.
- To force pagination during testing, set a small `first` (e.g. 2) and include `pageInfo { hasNextPage endCursor }` in your selection.
- Ensure the access token has the **Admin GraphQL** scope required for the resources you query.
```

---

## Detailed Usage

### `ShopifyClient`
- **Parameters**: `shop_name`, `access_token`, optional `api_version`, `max_retries` (default 3), `backoff_factor` (default 1.0), `timeout`.
- Handles HTTP 429 with exponential back‑off and raises `RateLimitError`.

Recommendation:
- Pin the `api_version` when creating `ShopifyClient` (for example `api_version="2024-10"`) rather than relying on a dynamic default. Using an unsupported or future API version can result in HTTP 404s; explicitly setting a known supported release avoids this class of error.

### `QueryEngine.query`
- `query`: GraphQL query string.
- `variables`: Optional dict.
- `auto_paginate`: When `True`, automatically walks through cursor‑based pagination and returns a **flattened list** of results.

### `MutationEngine.mutate`
- `mutation_name`: Name of the mutation (e.g., `productUpdate`).
- `variables`: Mutation input dict.
- Returns normalized `data`. If `userErrors` are present, a `PartialMutationError` is raised but still carries the partial payload.

### Error Handling
```python
from shopify_graphql.error_handler import raise_for_response

try:
    raw = client._post({"query": my_query, "variables": vars})
    normalized = raise_for_response(raw)
except ShopifyError as exc:
    # Handles RateLimitError, AuthenticationError, UserError, etc.
    handle(exc)
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Private‑app static token** | Simpler for automation scripts; OAuth adds complexity and is out of scope for a lightweight SDK. |
| **3‑retry exponential back‑off** | Balances responsiveness with Shopify’s rate‑limit policy. |
| **Unified response schema** | Guarantees callers always receive the same shape, simplifying downstream handling. |
| **Cursor‑based pagination abstraction** | Works for any connection (`products`, `orders`, `customers`). Users only toggle `auto_paginate`. |
| **Keyword‑only `response` in `RateLimitError`** | Improves readability and keeps the API clear. |

---

## Trade‑offs

- **Memory vs. convenience**: `auto_paginate=True` loads *all* pages into memory. For extremely large collections you may prefer a generator‑style API – future version could expose an iterator.
- **Static type hints only**: The SDK relies on runtime checks rather than heavy validation libraries to keep dependencies minimal.
- **No external GraphQL client**: We use `requests` directly to avoid pulling in large GraphQL libraries, keeping the package lightweight.

---

## Future Improvements

- Add **streaming paginator** (`yield`‑based) for large result sets.
- Implement **OAuth token refresh** for public‑app scenarios.
- Provide **typed models** (e.g., using `pydantic` or `dataclasses`) for stronger static validation.
- Publish to **PyPI** with CI/CD (GitHub Actions) and automated testing.
- Expose a **CLI wrapper** for quick ad‑hoc queries.

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request. Follow the existing code style (`black`, `flake8`) and add unit tests for new functionality.

---

## License

MIT © 2026 Ambibuzz

---