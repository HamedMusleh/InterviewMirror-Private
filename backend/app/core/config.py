from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Azure Document Intelligence
    azure_doc_intel_endpoint: str
    azure_doc_intel_key: str

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_key: str
    azure_openai_deployment_name: str
    azure_openai_api_version: str = "2024-08-01-preview"

    # LLM
    llm_request_timeout_seconds: float = 30.0

    # Azure Speech
    azure_speech_key: str
    azure_speech_region: str

    # The locale interview answers are recognised in. Stated explicitly
    # rather than left to Azure's default so the assumption is visible.
    azure_speech_language: str = "en-US"

    # Azure Blob Storage
    azure_storage_account_name: str
    azure_storage_container_name: str
    azure_storage_connection_string: str

    # Database
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


AZURE_DOC_INTEL_ENDPOINT = settings.azure_doc_intel_endpoint
AZURE_DOC_INTEL_KEY = settings.azure_doc_intel_key

AZURE_OPENAI_ENDPOINT = settings.azure_openai_endpoint
AZURE_OPENAI_KEY = settings.azure_openai_key
AZURE_OPENAI_API_VERSION = settings.azure_openai_api_version
AZURE_OPENAI_DEPLOYMENT_NAME = settings.azure_openai_deployment_name

LLM_REQUEST_TIMEOUT_SECONDS = settings.llm_request_timeout_seconds

AZURE_SPEECH_KEY = settings.azure_speech_key
AZURE_SPEECH_REGION = settings.azure_speech_region
AZURE_SPEECH_LANGUAGE = settings.azure_speech_language

AZURE_STORAGE_ACCOUNT_NAME = settings.azure_storage_account_name
AZURE_STORAGE_CONTAINER_NAME = settings.azure_storage_container_name
AZURE_STORAGE_CONNECTION_STRING = settings.azure_storage_connection_string

DATABASE_URL = settings.database_url