from __future__ import annotations

import json
from typing import Protocol

from openai import OpenAI

from news_scraper.config import CriteriaConfig
from news_scraper.models import Article, Classification


class Classifier(Protocol):
    def classify(self, article: Article, criteria: CriteriaConfig) -> Classification: ...


CLASSIFICATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "important",
        "company_name",
        "company_description",
        "coverage_match",
        "ownership_assessment",
        "location_assessment",
        "disqualifiers",
        "attractive_metrics",
        "confidence",
        "summary",
        "sms",
        "reasoning",
    ],
    "properties": {
        "important": {
            "type": "boolean",
            "description": "True only when this should trigger an SMS alert.",
        },
        "company_name": {"type": "string"},
        "company_description": {"type": "string"},
        "coverage_match": {
            "type": "string",
            "description": "How the company maps to Riley's included coverage areas.",
        },
        "ownership_assessment": {
            "type": "string",
            "description": "Whether the article indicates private ownership and not a subsidiary.",
        },
        "location_assessment": {
            "type": "string",
            "description": "Whether the company appears North America-relevant.",
        },
        "disqualifiers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Any explicit or likely reasons not to alert.",
        },
        "attractive_metrics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Quoted or closely paraphrased metrics that imply scale, financials, or growth.",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence that this is an attractive private-company lead.",
        },
        "summary": {
            "type": "string",
            "description": "Brief diligence-style summary for the database.",
        },
        "sms": {
            "type": "string",
            "description": "SMS-ready alert body without the URL. Keep under 900 characters.",
        },
        "reasoning": {
            "type": "string",
            "description": "Concise rationale for the decision, including uncertainty.",
        },
    },
}


INSTRUCTIONS = """You classify newly published news articles for Riley, a private equity investor.

Riley wants SMS alerts only for private-company leads that appear attractive because a new article
contains explicit or inferable information about company scale, financials, or growth.

Coverage areas to include: business services, tech-enabled services, industrial technology,
education, asset-light energy services, and consumer.

Explicitly exclude: financial technology, financial services, asset-heavy energy or industrial
businesses such as solar owner-operators, design-build construction firms, data center operators,
pure-play manufacturers, and DTC consumer brands. Industrial distributors are allowed.

Ownership/location filter: the company should be privately held, not a subsidiary of a parent
company, and North America-relevant. European companies are acceptable when they primarily sell to
US customers or have a US-based CEO. Venture, growth, or PE backing is acceptable.

Attractive metrics: any of these can qualify when the rest of the fit is good: more than $10M ARR;
if not an ARR business, more than $10M EBITDA and profitable; more than 30% year-over-year growth;
or customer/operator/location/unit counts that strongly imply scale.

Important calibration example: a leasing operating system serving 400+ operators and about
500,000 units should alert, because those customer/unit counts imply scaled operations.

Decision rules:
- Return important=false if the article is about a public company, a subsidiary, an excluded sector,
  a fund/investor rather than an operating company, or lacks company-level scale/financial/growth evidence.
- Do not invent metrics, locations, ownership, profitability, customers, or growth.
- If a criterion is unknown, say so. Unknown ownership is not automatically fatal when the article
  clearly describes a venture/growth-backed operating company with strong scale evidence.
- Prefer short quoted phrases for metrics when the article provides them.
- The sms field must be plain text, concise, and omit the URL because the app appends the link.
"""


class OpenAIClassifier:
    def __init__(self, model: str) -> None:
        self.client = OpenAI(max_retries=0)
        self.model = model

    def classify(self, article: Article, criteria: CriteriaConfig) -> Classification:
        payload = {
            "article": {
                "title": article.title,
                "url": article.url,
                "source": article.source,
                "published_at": article.published_at_iso,
                "feed_summary": article.summary,
                "content": article.content,
            },
            "configured_criteria": {
                "coverage_areas": criteria.coverage_areas,
                "excluded_areas": criteria.excluded_areas,
                "location": criteria.location,
                "ownership": criteria.ownership,
                "positive_metrics": criteria.positive_metrics,
            },
        }
        response = self.client.responses.create(
            model=self.model,
            instructions=INSTRUCTIONS,
            input=json.dumps(payload, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "lead_classification",
                    "schema": CLASSIFICATION_SCHEMA,
                    "strict": True,
                }
            },
            store=False,
        )
        return Classification.from_dict(json.loads(response.output_text))
