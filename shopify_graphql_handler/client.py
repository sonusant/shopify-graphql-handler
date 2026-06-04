import time, datetime
import logging
from typing import Any, Dict, Optional
import requests
from .exceptions import RateLimitError, AuthenticationError, ShopifyError
from .utils import exponential_backoff

log = logging.getLogger(__name__)


class ShopifyClient:
    """Core HTTP client for Shopify GraphQL Admin API.

    Parameters
    ----------
    shop_name: str
        Your myshopify store name (e.g. ``myshop`` for ``myshop.myshopify.com``).
    access_token: str
        Private app access token (static string).
    api_version: str, optional
        Shopify API version (default ``2023-10``). Must be a supported version.
    max_retries: int, optional
        Number of retry attempts on transient errors (default 3).
    backoff_factor: float, optional
        Base seconds for exponential backoff (default 1.0 → 1,2,4 seconds).
    timeout: float, optional
        Seconds to wait for a response (default 15).
    """

    def __init__(
        self,
        shop_name: str,
        access_token: str,
        api_version: str = f"{datetime.datetime.now().year}-01",
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: float = 15.0,
    ) -> None:
        self.shop_name = shop_name.rstrip("/")
        self.access_token = access_token
        self.api_version = api_version
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.endpoint = (
            f"https://{self.shop_name}.myshopify.com/admin/api/{self.api_version}/graphql.json"
        )
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        })

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a POST request with retry logic.

        Returns the raw JSON response (already ``response.json()``).
        Raises ``ShopifyError`` subclasses on unrecoverable errors.
        """
        attempt = 0
        while True:
            try:
                response = self.session.post(
                    self.endpoint,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code == 429:
                    # Rate limit – raise specific error to trigger backoff
                    raise RateLimitError("Rate limit exceeded", response=response)
                response.raise_for_status()
                return response.json()
            except (RateLimitError, requests.exceptions.RequestException) as exc:
                attempt += 1
                if attempt > self.max_retries:
                    if isinstance(exc, RateLimitError):
                        raise
                    raise ShopifyError(f"Failed after {self.max_retries} retries", cause=exc)
                sleep = exponential_backoff(self.backoff_factor, attempt)
                log.warning(
                    "Shopify request failed (attempt %d/%d). Retrying after %.2f seconds. Error: %s",
                    attempt,
                    self.max_retries,
                    sleep,
                    exc,
                )
                time.sleep(sleep)
