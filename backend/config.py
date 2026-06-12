from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure AI Foundry
    azure_foundry_endpoint: str = ""
    azure_foundry_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_deployment: str = "gpt-4o"

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""

    # Foundry IQ knowledge bases (backed by Azure AI Search indexes)
    foundry_kb_state_law: str = "kb-state-law-security-deposit"
    foundry_kb_court_procedures: str = "kb-court-procedures"
    foundry_kb_document_templates: str = "kb-document-templates"

    # Azure Blob Storage
    azure_blob_connection_string: str = ""
    azure_blob_account_name: str = ""
    azure_blob_account_key: str = ""
    azure_blob_container_knowledge: str = "knowledge-sources"
    azure_blob_container_documents: str = "case-documents"

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""
    database_url: str = ""

    # Redis / Celery
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # External APIs
    usps_api_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    admin_phone_number: str = ""

    # App
    secret_key: str = "dev-secret-key-change-me-in-production-32chars"
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
