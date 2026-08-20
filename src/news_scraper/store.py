from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from news_scraper.models import Article, Classification


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.connection.close()

    def already_seen(self, article: Article) -> bool:
        row = self.connection.execute(
            """
            select 1
            from articles
            where (id = ? or url = ?)
                and classified_at is not null
            limit 1
            """,
            (article.id, article.url),
        ).fetchone()
        return row is not None

    def record_classification(
        self,
        article: Article,
        classification: Classification,
        *,
        notified: bool,
    ) -> None:
        now = _now()
        article_id = self._stored_id(article) or article.id
        self.connection.execute(
            """
            insert into articles (
                id, url, title, source, published_at, first_seen_at, classified_at,
                important, classification_json, notified_at, error
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, null)
            on conflict(id) do update set
                url = excluded.url,
                title = excluded.title,
                source = excluded.source,
                published_at = excluded.published_at,
                classified_at = excluded.classified_at,
                important = excluded.important,
                classification_json = excluded.classification_json,
                notified_at = coalesce(articles.notified_at, excluded.notified_at),
                error = null
            """,
            (
                article_id,
                article.url,
                article.title,
                article.source,
                article.published_at_iso,
                now,
                now,
                int(classification.important),
                json.dumps(classification.raw, sort_keys=True),
                now if notified else None,
            ),
        )
        self.connection.commit()

    def record_error(self, article: Article, error: str) -> None:
        now = _now()
        article_id = self._stored_id(article) or article.id
        self.connection.execute(
            """
            insert into articles (
                id, url, title, source, published_at, first_seen_at, error
            )
            values (?, ?, ?, ?, ?, ?, ?)
            on conflict(id) do update set
                error = excluded.error
            """,
            (
                article_id,
                article.url,
                article.title,
                article.source,
                article.published_at_iso,
                now,
                error[:1000],
            ),
        )
        self.connection.commit()

    def _stored_id(self, article: Article) -> str | None:
        row = self.connection.execute(
            "select id from articles where id = ? or url = ? limit 1",
            (article.id, article.url),
        ).fetchone()
        return str(row["id"]) if row else None

    def _init_schema(self) -> None:
        self.connection.execute(
            """
            create table if not exists articles (
                id text primary key,
                url text not null unique,
                title text not null,
                source text not null,
                published_at text,
                first_seen_at text not null,
                classified_at text,
                important integer,
                classification_json text,
                notified_at text,
                error text
            )
            """
        )
        self.connection.commit()


def _now() -> str:
    return datetime.now(UTC).isoformat()
