# news-scraper

A small Python service that monitors configured news/RSS feeds, asks AI whether each new article
contains a private-company lead Riley would care about, and sends an SMS when the article qualifies.

The app currently supports:

- RSS/feed polling with SQLite deduplication.
- Article text extraction with feed-summary fallback.
- Riley-specific PE lead classification using OpenAI Structured Outputs.
- Dry-run alerts for safe testing.
- Twilio SMS delivery for real notifications.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
cp config.example.yaml config.yaml
```

Fill in `.env`:

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6

TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+15551234567
ALERT_TO_NUMBER=+15557654321
```

Keep `dry_run: true` in `config.yaml` until the classifications look right.

Useful throttling knobs in `config.yaml`:

```yaml
max_articles_per_run: 10
ai_request_delay_seconds: 2.0
```

Set `max_articles_per_run: 1` and `ai_request_delay_seconds: 10.0` while you are testing a new
OpenAI account or model with low rate limits.

## Run

Run a single poll:

```bash
news-scraper run-once --dry-run
```

Continuously poll:

```bash
news-scraper watch
```

Send or print a test SMS:

```bash
news-scraper test-sms --dry-run
news-scraper test-sms
```

## Configure Feeds

Add RSS feeds to `config.yaml`:

```yaml
feeds:
  - name: Commercial Observer
    url: https://commercialobserver.com/feed/
```

For broader monitoring, create targeted Google Alerts and use their RSS links, or add a search/news
API source later behind the `fetch_feed_articles` boundary.

## How Classification Works

The classifier alerts only when an article appears to describe:

- A privately held, non-subsidiary operating company.
- A company in Riley's coverage areas: business services, tech-enabled services, industrial
  technology, education, asset-light energy services, or consumer.
- North America relevance, or Europe with US sales/US-based CEO.
- Scale, financial, or growth evidence such as `>$10M ARR`, `>$10M EBITDA and profitable`, `>30%`
  YoY growth, or strong operating metrics like customer/operator/unit counts.

It suppresses financial technology/services, asset-heavy energy/industrial companies, design-build
construction, data center operators, pure-play manufacturers, and DTC consumer brands.

## Test

```bash
pytest
```

## Notes

- This is a feed-driven MVP. True internet-wide monitoring should use a paid news/search provider
  or Google Alerts RSS feeds.
- Failed articles are recorded but retried on future runs until they classify successfully.
- Set `dry_run: false` only after Twilio credentials are configured and test messages work.
