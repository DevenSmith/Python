from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "TinyRPG API"
    frontend_origin: str = "http://localhost:5173"
    jwt_secret_key: str = "development-only-change-this-key-before-any-real-deployment-123456"
    access_token_expire_minutes: int = 30


settings = Settings()
