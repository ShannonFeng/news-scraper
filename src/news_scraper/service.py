from __future__ import annotations

import time
from dataclasses import dataclass

from openai import RateLimitError

from news_scraper.article import ArticleExtractor
from news_scraper.classifier import Classifier
from news_scraper.config import AppConfig
from news_scraper.feeds import fetch_feed_articles
from news_scraper.notifier import Notifier
from news_scraper.store import Store


@dataclass(frozen=True)
class RunStats:
    fetched: int = 0
    skipped: int = 0
    classified: int = 0
    important: int = 0
    notified: int = 0
    deferred: int = 0
    errors: int = 0
    rate_limited: bool = False


class NewsScraperService:
    def __init__(
        self,
        *,
        config: AppConfig,
        store: Store,
        classifier: Classifier,
        notifier: Notifier,
        extractor: ArticleExtractor | None = None,
    ) -> None:
        self.config = config
        self.store = store
        self.classifier = classifier
        self.notifier = notifier
        self.extractor = extractor or ArticleExtractor()

    def run_once(self) -> RunStats:
        stats = RunStats(fetched=0)
        articles = fetch_feed_articles(self.config.feeds)
        stats = _replace(stats, fetched=len(articles))
        attempted_articles = 0

        for article_index, article in enumerate(articles):
            if self.store.already_seen(article):
                stats = _replace(stats, skipped=stats.skipped + 1)
                continue

            if (
                self.config.max_articles_per_run is not None
                and attempted_articles >= self.config.max_articles_per_run
            ):
                stats = _replace(stats, deferred=stats.deferred + 1)
                continue

            attempted_articles += 1
            try:
                enriched = self.extractor.enrich(article, self.config.max_article_chars)
                classification = self.classifier.classify(enriched, self.config.criteria)
                notified = False
                if classification.important:
                    self.notifier.send(enriched, classification)
                    notified = True

                self.store.record_classification(enriched, classification, notified=notified)
                stats = _replace(
                    stats,
                    classified=stats.classified + 1,
                    important=stats.important + int(classification.important),
                    notified=stats.notified + int(notified),
                )
                self._sleep_between_ai_requests()
            except RateLimitError as exc:
                self.store.record_error(article, f"{type(exc).__name__}: {exc}")
                return _replace(
                    stats,
                    errors=stats.errors + 1,
                    rate_limited=True,
                    deferred=stats.deferred + len(articles) - article_index - 1,
                )
            except Exception as exc:  # noqa: BLE001 - keep daemon alive across bad articles.
                self.store.record_error(article, f"{type(exc).__name__}: {exc}")
                stats = _replace(stats, errors=stats.errors + 1)

        return stats

    def _sleep_between_ai_requests(self) -> None:
        if self.config.ai_request_delay_seconds > 0:
            time.sleep(self.config.ai_request_delay_seconds)


def _replace(stats: RunStats, **changes: object) -> RunStats:
    values = stats.__dict__ | changes
    return RunStats(**values)
