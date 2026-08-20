from __future__ import annotations

import calendar
import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import feedparser

from news_scraper.config import FeedConfig
from news_scraper.models import Article


def fetch_feed_articles(feeds: Iterable[FeedConfig]) -> list[Article]:
    articles: list[Article] = []
    for feed in feeds:
        parsed = feedparser.parse(feed.url)
        for entry in parsed.entries:
            url = _entry_value(entry, "link")
            if not url:
                continue
            title = _entry_value(entry, "title") or "Untitled"
            entry_id = _entry_value(entry, "id") or _entry_value(entry, "guid") or url
            articles.append(
                Article(
                    id=_article_id(feed.name, entry_id, url),
                    title=title,
                    url=url,
                    source=feed.name,
                    published_at=_published_at(entry),
                    summary=_entry_value(entry, "summary"),
                )
            )
    return articles


def _article_id(source: str, entry_id: str, url: str) -> str:
    digest = hashlib.sha256(f"{source}:{entry_id}:{url}".encode()).hexdigest()
    return digest[:24]


def _entry_value(entry: object, key: str) -> str:
    value = getattr(entry, key, "") or ""
    return str(value).strip()


def _published_at(entry: object) -> datetime | None:
    parsed_time = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed_time:
        return datetime.fromtimestamp(calendar.timegm(parsed_time), tz=UTC)

    raw_date = _entry_value(entry, "published") or _entry_value(entry, "updated")
    if not raw_date:
        return None

    try:
        date = parsedate_to_datetime(raw_date)
    except (TypeError, ValueError):
        return None
    if date.tzinfo is None:
        return date.replace(tzinfo=UTC)
    return date.astimezone(UTC)
