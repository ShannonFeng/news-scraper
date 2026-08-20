from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import replace

from dotenv import load_dotenv

from news_scraper.classifier import OpenAIClassifier
from news_scraper.config import load_config
from news_scraper.models import Article, Classification
from news_scraper.notifier import DryRunNotifier, TwilioNotifier
from news_scraper.service import NewsScraperService, RunStats
from news_scraper.store import Store

LOG = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        config = load_config(args.config)
        if args.dry_run:
            config = replace(config, dry_run=True)

        if args.command == "test-sms":
            notifier = _build_notifier(config.dry_run)
            message_id = notifier.send(_sample_article(), _sample_classification())
            LOG.info("SMS test completed: %s", message_id)
            return 0

        store = Store(config.database_path)
        try:
            service = NewsScraperService(
                config=config,
                store=store,
                classifier=OpenAIClassifier(config.openai_model),
                notifier=_build_notifier(config.dry_run),
            )
            if args.command == "watch":
                _watch(service, config.poll_interval_seconds)
            else:
                _log_stats(service.run_once())
        finally:
            store.close()
    except KeyboardInterrupt:
        LOG.info("Stopped.")
        return 130
    except Exception as exc:  # noqa: BLE001 - command-line entrypoint should print failures.
        LOG.error("%s: %s", type(exc).__name__, exc)
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor news feeds for PE-relevant company leads."
    )
    parser.add_argument(
        "command",
        choices=["run-once", "watch", "test-sms"],
        nargs="?",
        default="run-once",
        help="Run a single poll, continuously poll, or send a test SMS.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML config. Defaults to NEWS_SCRAPER_CONFIG or config.yaml.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SMS alerts instead of sending through Twilio.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser


def _build_notifier(dry_run: bool) -> DryRunNotifier | TwilioNotifier:
    if dry_run:
        LOG.info("Dry-run mode enabled. Important alerts will be printed, not texted.")
        return DryRunNotifier()
    return TwilioNotifier()


def _watch(service: NewsScraperService, poll_interval_seconds: int) -> None:
    LOG.info("Watching feeds every %s seconds.", poll_interval_seconds)
    while True:
        _log_stats(service.run_once())
        time.sleep(poll_interval_seconds)


def _log_stats(stats: RunStats) -> None:
    LOG.info(
        (
            "Fetched=%s skipped=%s classified=%s important=%s notified=%s "
            "deferred=%s errors=%s rate_limited=%s"
        ),
        stats.fetched,
        stats.skipped,
        stats.classified,
        stats.important,
        stats.notified,
        stats.deferred,
        stats.errors,
        stats.rate_limited,
    )


def _sample_article() -> Article:
    return Article(
        id="sample",
        title="Boom raises $15M",
        source="Sample",
        url="https://commercialobserver.com/2026/08/sfr-leasing-boom-funding-s3-ventures/",
    )


def _sample_classification() -> Classification:
    return Classification(
        important=True,
        company_name="Boom",
        company_description="leasing operating system for single-family rentals",
        coverage_match="Tech-enabled services/business services",
        ownership_assessment="Private venture-backed company",
        location_assessment="North America-relevant",
        disqualifiers=[],
        attractive_metrics=["400+ operators", "about 500,000 units"],
        confidence=0.92,
        summary="Boom appears scaled based on customer/operator and unit counts.",
        sms=(
            "Boom, a leasing operating system for single-family rentals, raised $15M and may "
            "be scaled: it works with 400+ operators and about 500,000 units."
        ),
        reasoning="Sample notification.",
    )


if __name__ == "__main__":
    sys.exit(main())
