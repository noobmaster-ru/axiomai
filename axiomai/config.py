from os import environ

from pydantic import BaseModel, Field, field_validator


class SuperbankingConfig(BaseModel):
    api_key: str = Field(alias="SUPERBANKING_API_KEY")
    cabinet_id: str = Field(alias="SUPERBANKING_CABINET_ID")
    project_id: str = Field(alias="SUPERBANKING_PROJECT_ID")
    clearing_center_id: str = Field(alias="SUPERBANKING_CLEARING_CENTER_ID")


class MessageDebouncerConfig(BaseModel):
    message_debounce_delay: int = Field(alias="MESSAGE_DEBOUNCE_DELAY", default=10)
    message_accumulation_ttl: int = Field(alias="MESSAGE_ACCUMULATION_TTL", default=300)
    immediate_processing_length: int = Field(alias="IMMEDIATE_PROCESSING_LENGTH", default=500)


class OpenAIConfig(BaseModel):
    openai_api_key: str = Field(alias="OPENAI_TOKEN")
    proxy: str = Field(alias="PROXY")


class Config(BaseModel):
    postgres_uri: str = Field(alias="POSTGRES_URL")
    redis_uri: str = Field(alias="REDIS_URL")
    json_logs: bool = Field(alias="JSON_LOGS", default=False)
    bot_token: str = Field(alias="BOT_TOKEN")
    service_account_axiomai: str = Field(alias="SERVICE_ACCOUNT_AXIOMAI")
    service_account_axiomai_email: str = Field(alias="SERVICE_ACCOUNT_AXIOMAI_EMAIL")
    telegram_proxy: str | None = Field(alias="TELEGRAM_PROXY", default=None)

    admin_telegram_ids: list[int] = Field(alias="ADMIN_TELEGRAM_IDS")
    owner_telegram_id: int = Field(alias="OWNER_TELEGRAM_ID")
    admin_username: str = Field(alias="ADMIN_USERNAME")

    delay_between_bot_messages: float = Field(alias="DELAY_BETWEEN_BOT_MESSAGES", default=2.25)

    cors_allowed_origins: str = Field(alias="CORS_ALLOWED_ORIGINS", default="")
    # ТОЛЬКО для локальной разработки: подставляет telegram_id вместо проверки initData
    api_auth_dev_telegram_id: int | None = Field(alias="API_AUTH_DEV_TELEGRAM_ID", default=None)

    message_debouncer: MessageDebouncerConfig = Field(default_factory=lambda: MessageDebouncerConfig(**environ))
    superbanking_config: SuperbankingConfig = Field(default_factory=lambda: SuperbankingConfig(**environ))
    openai_config: OpenAIConfig = Field(default_factory=lambda: OpenAIConfig(**environ))

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def _parse_admin_telegram_ids(cls, value: str | list[int]) -> list[int]:
        """ADMIN_TELEGRAM_IDS в .env — строка вида "111,222"."""
        if isinstance(value, str):
            return [int(x) for x in value.split(",") if x.strip()]
        return value


def load_config[ConfigType](
    scope: type[ConfigType] | None = None,
) -> ConfigType | Config:
    if scope:
        return scope(**environ)

    return Config(**environ)
