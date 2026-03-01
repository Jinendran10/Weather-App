"""
YouTube service – generates embed URLs using YouTube's official public embed
search format.  No API key required.  No data is scraped.  TOS-compliant.

Embed format (YouTube documented public endpoint):
  https://www.youtube.com/embed?listType=search&list=<url-encoded-query>

This generates an interactive YouTube search playlist iframe that the frontend
can embed directly.  Because no API is called, there are no quotas, no Google
Cloud credentials, and no risk of violating the YouTube Terms of Service.
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Characters that carry injection risk when inserted into a URL query parameter.
# Stripped before the query is placed into the embed URL.
_UNSAFE_RE = re.compile(r'[<>"\';&|`$\\{}()\[\]^~%#@!*]')

EMBED_BASE = "https://www.youtube.com/embed"


class YouTubeService:
    """
    Builds YouTube search-playlist embed URLs without any external API calls.

    Usage::

        svc = YouTubeService()
        result = svc.build_embed_url("Kochi, Kerala, India")
        # result["embed_url"] → "https://www.youtube.com/embed?listType=search&list=Kochi+Kerala+India+travel+guide"
        # result["query"]     → "Kochi Kerala India travel guide"
    """

    def build_embed_url(
        self,
        location_name: str,
        suffix: str = "travel guide",
    ) -> Dict[str, Any]:
        """
        Build a YouTube search embed URL for a given location.

        Args:
            location_name: Resolved place name (e.g. "Kochi, Kerala, India").
            suffix:        Appended to the query (default: ``"travel guide"``).

        Returns:
            Dict with keys:
            - ``embed_url``: Ready-to-use ``<iframe src="...">`` URL.
            - ``query``:     Human-readable version of the search query used.
        """
        if not location_name or not location_name.strip():
            location_name = "travel destination"

        raw_query = f"{location_name.strip()} {suffix}"
        clean_query = self._clean(raw_query)
        encoded = quote_plus(clean_query)  # proper percent-encoding, spaces → +
        embed_url = f"{EMBED_BASE}?listType=search&list={encoded}"

        logger.debug(
            "[YouTube] embed URL built | location=%.40s | query=%.80s | url=%.120s",
            location_name, clean_query, embed_url,
        )
        return {
            "embed_url": embed_url,
            "query": clean_query,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clean(self, raw: str) -> str:
        """
        Clean a raw user-supplied string before URL-encoding.

        Steps:
        1. Strip characters with injection risk.
        2. Collapse consecutive whitespace.
        3. Cap at 200 characters.

        The result is a plain string; the caller runs ``quote_plus()`` on it
        which handles all remaining percent-encoding.

        Args:
            raw: Unsanitized string.

        Returns:
            Cleaned, whitespace-normalised string (200 char max).
        """
        cleaned = _UNSAFE_RE.sub("", raw)    # strip injection-risk chars
        cleaned = " ".join(cleaned.split())  # normalise whitespace
        return cleaned[:200]                 # hard cap


youtube_service = YouTubeService()
