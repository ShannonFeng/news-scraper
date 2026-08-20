from news_scraper.models import Article, Classification
from news_scraper.notifier import build_notification


def test_build_notification_appends_link_once() -> None:
    article = Article(id="1", title="Example", url="https://example.com/a", source="Example")
    classification = Classification(
        important=True,
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

    notification = build_notification(article, classification, "+15551234567")

    assert notification.body == "Acme appears attractive with $12M ARR.\nhttps://example.com/a"
    assert notification.to_number == "+15551234567"


def test_build_notification_does_not_duplicate_link() -> None:
    article = Article(id="1", title="Example", url="https://example.com/a", source="Example")
    classification = Classification(
        important=True,
        company_name="Acme",
        company_description="field services software",
        coverage_match="business services",
        ownership_assessment="private",
        location_assessment="North America",
        disqualifiers=[],
        attractive_metrics=["$12M ARR"],
        confidence=0.9,
        summary="Acme has $12M ARR.",
        sms="Acme appears attractive with $12M ARR. https://example.com/a",
        reasoning="Meets ARR threshold.",
    )

    notification = build_notification(article, classification, None)

    assert notification.body.count("https://example.com/a") == 1
