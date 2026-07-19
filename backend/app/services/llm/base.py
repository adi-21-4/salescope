from abc import ABC, abstractmethod

from app.services.llm.schemas import GeneratedInsightsResponse, QuerySpec


class LLMError(Exception):
    """Clean, user-facing error raised by any provider. Routers catch this
    instead of an SDK-specific exception type, keeping the SDK import confined
    to services/llm/*_provider.py."""


class LLMProvider(ABC):
    """Every LLM call in the app goes through this interface. Nothing outside
    services/llm/ imports a provider SDK directly -- swapping providers means
    writing one new *_provider.py file and changing the LLM_PROVIDER env var."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier stored alongside cached results for audit/debugging."""
        ...

    @abstractmethod
    def generate_insights(self, summary: dict) -> GeneratedInsightsResponse:
        """summary is a compact aggregate summary (never raw transaction rows)."""
        ...

    @abstractmethod
    def translate_query(self, question: str, schema_description: dict) -> QuerySpec:
        """Translate a natural-language question into a QuerySpec the backend can
        safely execute. schema_description tells the model what canonical
        columns/values exist for this shop (not the raw data)."""
        ...
