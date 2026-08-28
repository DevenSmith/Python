from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "TinyRPG API"
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
