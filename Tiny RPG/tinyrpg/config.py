from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "TinyRPG API"


settings = Settings()
