from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = Field(default="Web Scraping Service")
    API_V1_STR: str = Field(default="/api/v1")
    SECRET_KEY: str
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str
    OPEN_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
