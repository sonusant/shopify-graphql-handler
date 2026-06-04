class ShopifyError(Exception):
    """Base exception for all Shopify SDK errors."""
    def __init__(self, message: str = "", *, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause

class RateLimitError(ShopifyError):
    """Raised when Shopify returns HTTP 429 (rate limit)."""
    def __init__(self, message: str = "Rate limit exceeded", *, response: "requests.Response" = None):
        super().__init__(message)
        self.response = response

class AuthenticationError(ShopifyError):
    """Raised when authentication headers are missing or invalid."""
    pass

class UserError(ShopifyError):
    """Represents a userError returned inside a mutation payload."""
    def __init__(self, errors: list):
        super().__init__("User errors encountered")
        self.errors = errors

class PartialMutationError(ShopifyError):
    """Mutation succeeded partially but contains userErrors.

    The ``data`` payload is still returned and can be inspected.
    """
    def __init__(self, message: str, data: dict, errors: list):
        super().__init__(message)
        self.data = data
        self.errors = errors
