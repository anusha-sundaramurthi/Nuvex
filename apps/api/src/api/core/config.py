

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Config(BaseSettings):
    OPENAI_API_KEY: str
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str
    QDRANT_URL: str = "http://qdrant:6333"
    LANGSMITH_API_KEY: Optional[str] = None
    POSTGRES_URL: str = "postgresql://langgraph_user:langgraph_password@postgres:5433/langgraph_db"

    model_config = SettingsConfigDict(env_file=".env")

config = Config()