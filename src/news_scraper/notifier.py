from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from twilio.rest import Client

from news_scraper.models import Article, Classification


class Notifier(Protocol):
    def send(self, article: Article, classification: Classification) -> str: ...


@dataclass(frozen=True)
class Notification:
    body: str
    to_number: str | None


class DryRunNotifier:
    def send(self, article: Article, classification: Classification) -> str:
        notification = build_notification(article, classification, None)
        print("\n--- DRY RUN SMS ---")
        print(notification.body)
        print("--- END SMS ---\n")
        return "dry-run"


class TwilioNotifier:
    def __init__(
        self,
        *,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
        to_number: str | None = None,
    ) -> None:
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv("TWILIO_FROM_NUMBER")
        self.to_number = to_number or os.getenv("ALERT_TO_NUMBER")

        missing = [
            name
            for name, value in {
                "TWILIO_ACCOUNT_SID": self.account_sid,
                "TWILIO_AUTH_TOKEN": self.auth_token,
                "TWILIO_FROM_NUMBER": self.from_number,
                "ALERT_TO_NUMBER": self.to_number,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required SMS environment variables: {', '.join(missing)}")

        self.client = Client(self.account_sid, self.auth_token)

    def send(self, article: Article, classification: Classification) -> str:
        notification = build_notification(article, classification, self.to_number)
        message = self.client.messages.create(
            body=notification.body,
            from_=self.from_number,
            to=self.to_number,
        )
        return str(message.sid)


def build_notification(
    article: Article,
    classification: Classification,
    to_number: str | None,
) -> Notification:
    body = classification.sms.strip()
    if article.url not in body:
        body = f"{body}\n{article.url}"
    return Notification(body=body[:1500], to_number=to_number)
