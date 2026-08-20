from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class FeedConfig:
    name: str
    url: str


@dataclass(frozen=True)
class CriteriaConfig:
    coverage_areas: list[str] = field(default_factory=list)
    excluded_areas: list[str] = field(default_factory=list)
    location: list[str] = field(default_factory=list)
    ownership: list[str] = field(default_factory=list)
    positive_metrics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppConfig:
    feeds: list[FeedConfig]
    criteria: CriteriaConfig
    poll_interval_seconds: int = 900
    database_path: str = "news_scraper.sqlite3"
    dry_run: bool = False
    max_article_chars: int = 12000
    max_articles_per_run: int | None = 10
    ai_request_delay_seconds: float = 2.0
    openai_model: str = "gpt-5.6"
    alert_to_number: str | None = None
    twilio_from_number: str | None = None


def load_config(path: str | Path | None = None) -> AppConfig:
    load_dotenv()
    config_path = Path(path or os.getenv("NEWS_SCRAPER_CONFIG", "config.yaml"))
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}. Copy config.example.yaml to config.yaml."
        )

    data = _read_yaml(config_path)
    feeds = [FeedConfig(**feed) for feed in data.get("feeds", [])]
    if not feeds:
        raise ValueError("At least one feed must be configured.")

    criteria = CriteriaConfig(**data.get("criteria", {}))
    return AppConfig(
        feeds=feeds,
        criteria=criteria,
        poll_interval_seconds=int(data.get("poll_interval_seconds", 900)),
        database_path=str(
            os.getenv("NEWS_SCRAPER_DB", data.get("database_path", "news_scraper.sqlite3"))
        ),
        dry_run=bool(data.get("dry_run", False)),
        max_article_chars=int(data.get("max_article_chars", 12000)),
        max_articles_per_run=_optional_int(data.get("max_articles_per_run", 10)),
        ai_request_delay_seconds=float(data.get("ai_request_delay_seconds", 2.0)),
        openai_model=os.getenv("OPENAI_MODEL", data.get("openai_model", "gpt-5.6")),
        alert_to_number=os.getenv("ALERT_TO_NUMBER"),
        twilio_from_number=os.getenv("TWILIO_FROM_NUMBER"),
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a YAML object.")
    return payload


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
