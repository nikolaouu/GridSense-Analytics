from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "postgres" 
    POSTGRES_PORT: int = 5432

    MONGO_INITDB_ROOT_USERNAME: str
    MONGO_INITDB_ROOT_PASSWORD: str
    MONGO_HOST: str = "mongodb"
    MONGO_PORT: int = 27017

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()