from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """應用程式設定"""
    app_name: str = "AI Insurance Recommend API"
    debug: bool = False

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Server
    host: str = "0.0.0.0"
    port: int = 8099

    class Config:
        env_file = ".env"


settings = Settings()
