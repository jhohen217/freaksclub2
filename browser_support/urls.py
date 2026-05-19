"""URL parsing and validation helpers for BrowserManager."""

from __future__ import annotations

import re


# URL pattern: matches http://, https://, or bare domains like youtube.com/xxx
URL_PATTERN = re.compile(
    r'(?:https?://)?'  # optional http:// or https://
    r'(?:www\.)?'      # optional www.
    r'(?:'             # known domains/shorteners
    r'youtube\.com|youtu\.be|spotify\.com|twitch\.tv|'
    r'google\.com|github\.com|reddit\.com|twitter\.com|x\.com|'
    r'instagram\.com|tiktok\.com|vimeo\.com|dailymotion\.com|'
    r'soundcloud\.com|bandcamp\.com|apple\.com|kick\.com|'
    r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'  # any domain with one or more labels + TLD
    r')'
    r'(?:/[^\s]*)?'   # optional path
)

BROWSER_COMMAND_WORDS = {
    'refresh', 'close', 'full', 'max', 'fullscreen', 'min', 'bookmarks', 'bm'
}


def ensure_https(url: str) -> str:
    """Ensure a URL has an explicit HTTP(S) scheme."""
    if url.startswith('http://') or url.startswith('https://'):
        return url
    return 'https://' + url


def is_valid_url(url: str) -> bool:
    """Return True when the URL looks like it has a domain with a dot."""
    cleaned = url.replace('https://', '').replace('http://', '').replace('www.', '')
    return '.' in cleaned.split('/')[0]


def parse_url_with_name(content: str) -> tuple[str | None, str | None]:
    """Parse a URL and optional bookmark name from message content."""
    content = content.strip()

    if content.lower() in BROWSER_COMMAND_WORDS:
        return None, None

    match = URL_PATTERN.search(content)
    if match:
        url = match.group(0)
        if is_valid_url(url):
            url = ensure_https(url)
            after_url = content[match.end():].strip()
            bookmark_name = after_url if after_url else None
            return url, bookmark_name

    return None, None
