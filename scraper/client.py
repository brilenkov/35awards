"""Small, polite HTTP client with an on-disk response cache.

The cache is intentionally simple: it makes repeated development runs cheap and
keeps the load on 35awards.com low. Delete ``work/http`` to force a refetch.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://35awards.com"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
}
CACHE_DIR = Path(__file__).resolve().parent.parent / "work" / "http"


class HttpClient:
    def __init__(
        self,
        delay: float = 0.35,
        timeout: int = 90,
        cache: bool = True,
        cache_dir: Path | None = None,
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.delay = delay
        self.timeout = timeout
        self.cache = cache
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_at = 0.0

    # ------------------------------------------------------------------ helpers
    def _cache_path(self, url: str, params: dict[str, Any] | None) -> Path:
        key = url + ("?" + json.dumps(params, sort_keys=True) if params else "")
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.bin"

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_at = time.monotonic()

    def _request(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        referer: str | None = None,
        stream: bool = False,
    ) -> requests.Response:
        headers = {}
        if referer:
            headers["Referer"] = referer
        self._wait()
        response = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=self.timeout,
            stream=stream,
        )
        response.raise_for_status()
        return response

    # -------------------------------------------------------------------- public
    def get_bytes(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        referer: str | None = None,
        use_cache: bool = True,
    ) -> bytes:
        cache_path = self._cache_path(url, params)
        if self.cache and use_cache and cache_path.exists():
            return cache_path.read_bytes()

        response = self._request(url, params=params, referer=referer)
        content = response.content
        if self.cache and use_cache:
            cache_path.write_bytes(content)
        return content

    def get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        referer: str | None = None,
        use_cache: bool = True,
    ) -> str:
        content = self.get_bytes(
            url, params=params, referer=referer, use_cache=use_cache
        )
        # 35awards serves UTF-8 everywhere; requests' guessed encoding is sometimes
        # latin-1 when the header is missing, so decode explicitly.
        return content.decode("utf-8", errors="replace")

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        referer: str | None = None,
        use_cache: bool = True,
    ) -> Any:
        return json.loads(
            self.get_text(url, params=params, referer=referer, use_cache=use_cache)
        )

    def download(
        self,
        url: str,
        dest: Path,
        *,
        referer: str | None = None,
        use_cache: bool = True,
    ) -> bool:
        """Download a binary asset. Returns False when the response is not usable."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        cache_path = self._cache_path(url, None)
        if self.cache and use_cache and cache_path.exists():
            content = cache_path.read_bytes()
        else:
            try:
                response = self._request(url, referer=referer, stream=True)
            except requests.RequestException:
                return False
            content = response.content
            if self.cache and use_cache and content:
                cache_path.write_bytes(content)

        if not content or len(content) < 64:
            return False
        dest.write_bytes(content)
        return True
