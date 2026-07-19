import json
from contextlib import contextmanager

import anthropic
from anthropic import Anthropic

from app.config import settings
from app.services.llm.base import LLMError, LLMProvider
from app.services.llm.prompts import INSIGHTS_SYSTEM_PROMPT, QUERY_TRANSLATION_SYSTEM_PROMPT
from app.services.llm.schemas import GeneratedInsightsResponse, QuerySpec

# Sonnet 5: adaptive thinking is on by default if the `thinking` param is
# omitted, and custom sampling params (temperature/top_p/top_k) are rejected
# outright. Both narration and query-translation are simple, bounded tasks with
# no need for extended reasoning, so thinking is explicitly disabled to keep
# latency and cost down -- this is the ONLY file in the app that imports the
# `anthropic` SDK.
MODEL = "claude-sonnet-5"


@contextmanager
def _translate_errors():
    """Turn SDK-specific exceptions into a clean, user-facing LLMError so
    nothing outside this file needs to know about anthropic's exception types."""
    try:
        yield
    except anthropic.RateLimitError as exc:
        raise LLMError("The AI service is temporarily rate-limited. Try again in a moment.") from exc
    except anthropic.BadRequestError as exc:
        message = str(exc)
        if "credit balance" in message.lower():
            raise LLMError("The AI service account is out of credits.") from exc
        raise LLMError("The AI service rejected the request.") from exc
    except anthropic.AuthenticationError as exc:
        raise LLMError("The AI service is not configured correctly (invalid API key).") from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError("Could not reach the AI service. Check your network connection.") from exc
    except anthropic.APIStatusError as exc:
        raise LLMError(f"The AI service returned an error ({exc.status_code}).") from exc


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = Anthropic(api_key=settings.anthropic_api_key)

    @property
    def model_name(self) -> str:
        return MODEL

    def generate_insights(self, summary: dict) -> GeneratedInsightsResponse:
        with _translate_errors():
            response = self._client.messages.parse(
                model=MODEL,
                max_tokens=2000,
                thinking={"type": "disabled"},
                system=INSIGHTS_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Here are this shop's aggregate sales statistics:\n\n{json.dumps(summary, indent=2)}",
                    }
                ],
                output_format=GeneratedInsightsResponse,
            )
        return response.parsed_output

    def translate_query(self, question: str, schema_description: dict) -> QuerySpec:
        with _translate_errors():
            response = self._client.messages.parse(
                model=MODEL,
                max_tokens=1000,
                thinking={"type": "disabled"},
                system=QUERY_TRANSLATION_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Schema:\n{json.dumps(schema_description, indent=2)}\n\nQuestion: {question}",
                    }
                ],
                output_format=QuerySpec,
            )
        return response.parsed_output
