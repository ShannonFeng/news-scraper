from dataclasses import replace

import news_scraper.service as service_module
from news_scraper.config import AppConfig, CriteriaConfig, FeedConfig
from news_scraper.models import Article, Classification
from news_scraper.service import NewsScraperService
from news_scraper.store import Store


def test_service_classifies_and_notifies_important_articles(monkeypatch, tmp_path) -> None:
    article = Article(
        id="1", title="Boom raises $15M", url="https://example.com/boom", source="Feed"
    )
    monkeypatch.setattr(service_module, "fetch_feed_articles", lambda feeds: [article])

    notifier = FakeNotifier()
    store = Store(tmp_path / "news.sqlite3")
    service = NewsScraperService(
        config=_config(tmp_path),
        store=store,
        classifier=FakeClassifier(important=True),
        notifier=notifier,
        extractor=FakeExtractor(),
    )

    stats = service.run_once()

    assert stats.fetched == 1
    assert stats.classified == 1
    assert stats.important == 1
    assert stats.notified == 1
    assert notifier.sent == [article.url]

    second_run_stats = service.run_once()
    assert second_run_stats.skipped == 1

    store.close()


def test_service_does_not_notify_unimportant_articles(monkeypatch, tmp_path) -> None:
    article = Article(
        id="1", title="Bank launches app", url="https://example.com/bank", source="Feed"
    )
    monkeypatch.setattr(service_module, "fetch_feed_articles", lambda feeds: [article])

    notifier = FakeNotifier()
    store = Store(tmp_path / "news.sqlite3")
    service = NewsScraperService(
        config=_config(tmp_path),
        store=store,
        classifier=FakeClassifier(important=False),
        notifier=notifier,
        extractor=FakeExtractor(),
    )

    stats = service.run_once()

    assert stats.classified == 1
    assert stats.important == 0
    assert stats.notified == 0
    assert notifier.sent == []

    store.close()


def test_service_defers_articles_after_per_run_cap(monkeypatch, tmp_path) -> None:
    articles = [
        Article(id="1", title="First", url="https://example.com/1", source="Feed"),
        Article(id="2", title="Second", url="https://example.com/2", source="Feed"),
    ]
    monkeypatch.setattr(service_module, "fetch_feed_articles", lambda feeds: articles)

    notifier = FakeNotifier()
    store = Store(tmp_path / "news.sqlite3")
    service = NewsScraperService(
        config=replace(_config(tmp_path), max_articles_per_run=1),
        store=store,
        classifier=FakeClassifier(important=False),
        notifier=notifier,
        extractor=FakeExtractor(),
    )

    stats = service.run_once()

    assert stats.classified == 1
    assert stats.deferred == 1

    store.close()


class FakeExtractor:
    def enrich(self, article: Article, max_chars: int) -> Article:
        return replace(article, content="Works with 400+ operators and about 500,000 units.")


class FakeClassifier:
    def __init__(self, *, important: bool) -> None:
        self.important = important

    def classify(self, article: Article, criteria: CriteriaConfig) -> Classification:
        return Classification(
            important=self.important,
            company_name="Boom",
            company_description="leasing operating system",
            coverage_match="tech-enabled services",
            ownership_assessment="private",
            location_assessment="North America",
            disqualifiers=[] if self.important else ["excluded or insufficient evidence"],
            attractive_metrics=["400+ operators", "about 500,000 units"] if self.important else [],
            confidence=0.9 if self.important else 0.3,
            summary="Boom appears scaled." if self.important else "Not a lead.",
            sms="Boom may be scaled: 400+ operators and about 500,000 units.",
            reasoning="Matches Riley criteria."
            if self.important
            else "Does not match Riley criteria.",
        )


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, article: Article, classification: Classification) -> str:
        self.sent.append(article.url)
        return "fake-message-id"


def _config(tmp_path) -> AppConfig:
    return AppConfig(
        feeds=[FeedConfig(name="Feed", url="https://example.com/feed")],
        criteria=CriteriaConfig(),
        database_path=str(tmp_path / "news.sqlite3"),
        dry_run=True,
        ai_request_delay_seconds=0.0,
    )
