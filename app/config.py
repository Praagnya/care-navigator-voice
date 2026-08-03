from enum import Enum
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    


# Controls which LLM backs the Deep Agent (not Gemini Live)
class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Environment = Environment.DEVELOPMENT
    app_secret_key: str = "change-me-in-development"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/care_navigator"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/care_navigator"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Gemini Live
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-native-audio-preview"

    # Deep Agent LLM backend
    deep_agent_llm_provider: LLMProvider = LLMProvider.OPENAI
    deep_agent_llm_model: str = "gpt-4o"

    # OpenAI — required when deep_agent_llm_provider = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Anthropic — required when deep_agent_llm_provider = "anthropic"
    anthropic_api_key: str = ""

    # Session behaviour
    session_resumption_enabled: bool = True
    context_window_compression_enabled: bool = True

    # Observability
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # CMS Data Pipeline
    cms_api_base_url: str = "https://data.cms.gov/resource"
    cms_hospital_dataset_id: str = "xubh-q36u"

    # Pipeline versioning
    pipeline_version: str = "0.1.0"
    schema_version: str = "1.0"

    # Future (V2+)
    # aws_access_key_id: str = ""
    # aws_secret_access_key: str = ""
    # aws_region: str = "us-east-1"
    # s3_bucket_name: str = "care-navigator-data"

    @model_validator(mode="after")
    def validate_required_keys(self) -> "Settings":
        if not self.gemini_api_key.strip():
            raise ValueError("GEMINI_API_KEY is required for the voice agent to operate")

        if self.deep_agent_llm_provider == LLMProvider.OPENAI and not self.openai_api_key.strip():
            raise ValueError("OPENAI_API_KEY is required when DEEP_AGENT_LLM_PROVIDER=openai")

        if self.deep_agent_llm_provider == LLMProvider.ANTHROPIC and not self.anthropic_api_key.strip():
            raise ValueError("ANTHROPIC_API_KEY is required when DEEP_AGENT_LLM_PROVIDER=anthropic")

        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

@lru_cache
def get_settings() -> Settings:
    return Settings()