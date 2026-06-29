from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "billing-db"
    POSTGRES_PORT: int = 5432

    MONGO_INITDB_ROOT_USERNAME: str
    MONGO_INITDB_ROOT_PASSWORD: str
    MONGO_HOST: str = "catalog-db"
    MONGO_PORT: int = 27017

    REDIS_PASSWORD: str
    REDIS_HOST: str = "cache"
    REDIS_PORT: int = 6379

    NEO4J_AUTH: str = "neo4j/password"
    NEO4J_HOST: str = "graph-db"
    NEO4J_PORT: int = 7687
    NEO4J_URI: str = "bolt://graph-db:7687"
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    CASSANDRA_HOST: str = "timeseries-db"
    CASSANDRA_PORT: int = 9042
    CASSANDRA_KEYSPACE: str = "gridsense"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()