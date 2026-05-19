"""Bookmark persistence helpers for BrowserManager."""

from __future__ import annotations

import json
from pathlib import Path


def load_bookmarks(bookmarks_file: Path) -> dict:
    """Load bookmarks from disk, returning an empty dict on failure."""
    try:
        if bookmarks_file.exists():
            with open(bookmarks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Browser] Error loading bookmarks: {e}")
    return {}


def save_bookmarks(bookmarks_file: Path, bookmarks: dict) -> None:
    """Persist bookmarks to disk."""
    try:
        with open(bookmarks_file, 'w', encoding='utf-8') as f:
            json.dump(bookmarks, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Browser] Error saving bookmarks: {e}")


def add_bookmark(bookmarks_file: Path, bookmarks: dict, name: str, url: str) -> None:
    """Add or update a bookmark and persist it."""
    normalized_name = name.lower().strip()
    bookmarks[normalized_name] = url
    save_bookmarks(bookmarks_file, bookmarks)
    print(f"[Browser] Bookmark added: {normalized_name} -> {url}")


def remove_bookmark(bookmarks_file: Path, bookmarks: dict, name: str) -> bool:
    """Remove a bookmark by name and persist when found."""
    normalized_name = name.lower().strip()
    if normalized_name in bookmarks:
        del bookmarks[normalized_name]
        save_bookmarks(bookmarks_file, bookmarks)
        print(f"[Browser] Bookmark removed: {normalized_name}")
        return True
    return False


def resolve_bookmark(bookmarks: dict, content: str) -> str | None:
    """Resolve message content as a bookmark name."""
    name = content.lower().strip()
    return bookmarks.get(name)
