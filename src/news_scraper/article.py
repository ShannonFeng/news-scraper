from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from news_scraper.models import Article

USER_AGENT = (
    "news-scraper/0.1 (+https://example.local; private company lead monitoring; "
    "contact: ops@example.local)"
)


class ArticleExtractor:
    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def enrich(self, article: Article, max_chars: int) -> Article:
        try:
            content = self.fetch_text(article.url)
        except httpx.HTTPError:
            content = ""

        content = content or _clean_text(article.summary)
        if len(content) > max_chars:
            content = content[:max_chars].rsplit(" ", 1)[0]

        return Article(
            id=article.id,
            title=article.title,
            url=article.url,
            source=article.source,
            published_at=article.published_at,
            summary=article.summary,
            content=content,
        )

    def fetch_text(self, url: str) -> str:
        with httpx.Client(
            follow_redirects=True,
            timeout=self.timeout_seconds,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
        return extract_text(response.text)


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(
        ["script", "style", "noscript", "svg", "form", "nav", "header", "footer", "aside"]
    ):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    paragraphs = [node.get_text(" ", strip=True) for node in soup.find_all(["h1", "h2", "p", "li"])]
    text = "\n".join(item for item in [title, *paragraphs] if item)
    return _clean_text(text)


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
