from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Config(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env")

config = Config()