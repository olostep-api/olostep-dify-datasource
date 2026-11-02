"""Olostep REST API client used by the Dify data source."""

import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlparse

import httpx

API_URL = "https://api.olostep.com/v1"
TIMEOUT = httpx.Timeout(120.0, connect=10.0)
RETRY_STATUSES = (429, 500, 502, 503, 504)
ATTEMPTS = 3
POLL_SECONDS = 10
PAGE_SIZE = 50
RETRIEVE_WORKERS = 8
# Dify stores the title as the document name, which is limited to 255 characters.
TITLE_LENGTH = 200
DESCRIPTION_LENGTH = 200
MIN_DESCRIPTION_LENGTH = 40
NOT_PROSE = ("#", ">", "[", "!", "|", "`", "-", "*", "<")
USER_AGENT = "olostep-dify-datasource/0.1.0"


class OlostepError(Exception):
    """An error whose message is safe to show to Dify users."""


def check_url(value: Any) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise OlostepError(f"Enter a full http(s) URL, for example https://example.com (got {url!r}).")
    return url


def title_and_description(markdown: str, url: str) -> tuple[str, str]:
    """Olostep markdown starts with the page title. The description is the first line of prose after it."""
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    title = (lines[0].lstrip("\\# ") if lines else "") or url
    title = title[:TITLE_LENGTH].strip()
    for line in lines[1:]:
        if len(line) >= MIN_DESCRIPTION_LENGTH and not line.startswith(NOT_PROSE) and "](" not in line:
            return title, line[:DESCRIPTION_LENGTH]
    return title, ""


def error_message(response: httpx.Response) -> str:
    if response.status_code in (401, 403):
        return "Your Olostep API key is invalid or revoked. Update it in the plugin credentials."
    if response.status_code == 402:
        return "Your Olostep credits are used up. Check your plan at https://www.olostep.com/dashboard."
    try:
        data = response.json()
    except ValueError:
        data = None
    detail = None
    if isinstance(data, dict):
        detail = data.get("detail") or data.get("title") or data.get("message")
    if isinstance(detail, str) and detail:
        return f"Olostep API error (HTTP {response.status_code}): {detail}"
    return f"Olostep API error (HTTP {response.status_code})."


class OlostepClient:
    def __init__(
        self,
        api_key: Any,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        key = str(api_key or "").strip()
        if not key:
            raise OlostepError("Add your Olostep API key in the plugin credentials.")
        self._headers = {"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT}
        self._transport = transport
        self._sleep = sleep

    def _send(self, method: str, path: str, body: Any = None, params: dict | None = None) -> httpx.Response:
        with httpx.Client(timeout=TIMEOUT, transport=self._transport) as client:
            return client.request(method, f"{API_URL}/{path}", headers=self._headers, json=body, params=params)

    def request(self, method: str, path: str, *, body: Any = None, params: dict | None = None) -> dict:
        """Calls the API, retrying rate limits, server errors and network errors."""
        for attempt in range(ATTEMPTS):
            last = attempt == ATTEMPTS - 1
            try:
                response = self._send(method, path, body, params)
            except httpx.HTTPError:
                if last:
                    raise OlostepError("Could not reach the Olostep API. Try again later.") from None
                self._sleep(2 ** (attempt + 1))
                continue
            if response.status_code < 400:
                try:
                    return response.json()
                except ValueError:
                    raise OlostepError("The Olostep API returned an invalid response.") from None
            if response.status_code in RETRY_STATUSES and not last:
                self._sleep(2 ** (attempt + 1))
                continue
            raise OlostepError(error_message(response))
        raise OlostepError("Could not reach the Olostep API. Try again later.")

    def check_key(self) -> None:
        """Checks the key with a lookup that uses no credits."""
        try:
            response = self._send("GET", "batches/batch_dify_key_check")
        except httpx.HTTPError:
            raise OlostepError("Could not reach the Olostep API. Try again later.") from None
        if response.status_code in (401, 403):
            raise OlostepError(error_message(response))

    def start_crawl(self, url: Any, options: dict) -> str:
        job = self.request("POST", "crawls", body={"start_url": check_url(url), **options})
        return job["id"]

    def wait_for_crawl(self, crawl_id: str) -> Iterator[dict]:
        """Yields the crawl status while it runs, so callers can report progress."""
        while True:
            info = self.request("GET", f"crawls/{crawl_id}")
            status = info.get("status")
            if status == "failed":
                raise OlostepError(f"The crawl {crawl_id} failed.")
            yield info
            if status != "in_progress":
                return
            self._sleep(POLL_SECONDS)

    def crawl_pages(self, crawl_id: str) -> Iterator[list[dict]]:
        """Yields the pages of a finished crawl a set at a time, following the cursor to the end."""
        cursor = None
        while True:
            params: dict[str, Any] = {"limit": PAGE_SIZE}
            if cursor is not None:
                params["cursor"] = cursor
            data = self.request("GET", f"crawls/{crawl_id}/pages", params=params)
            found = [item for item in data.get("pages") or [] if item.get("retrieve_id")]
            if found:
                with ThreadPoolExecutor(max_workers=RETRIEVE_WORKERS) as pool:
                    yield list(pool.map(self._retrieve, found))
            cursor = data.get("cursor")
            if not data.get("pages") or cursor is None:
                return

    def _retrieve(self, item: dict) -> dict:
        data = self.request("GET", "retrieve", params={"retrieve_id": item["retrieve_id"], "formats": "markdown"})
        return {"url": item.get("url") or "", "markdown": data.get("markdown_content") or ""}
