from news_scraper.models import Article, Classification
from news_scraper.store import Store


def test_error_records_are_retried_until_classified(tmp_path) -> None:
    store = Store(tmp_path / "news.sqlite3")
    article = Article(id="1", title="Example", url="https://example.com/a", source="Example")

    store.record_error(article, "temporary failure")
    assert store.already_seen(article) is False

    store.record_classification(article, _classification(important=False), notified=False)
    assert store.already_seen(article) is True

    store.close()


def _classification(*, important: bool) -> Classification:
    return Classification(
        important=important,
        company_name="Acme",
        company_description="field services software",
        coverage_match="business services",
        ownership_assessment="private",
        location_assessment="North America",
        disqualifiers=[],
        attractive_metrics=["$12M ARR"],
        confidence=0.9,
        summary="Acme has $12M ARR.",
        sms="Acme appears attractive with $12M ARR.",
        reasoning="Meets ARR threshold.",
    )
