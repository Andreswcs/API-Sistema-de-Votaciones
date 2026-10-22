from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "votaciones"
    postgres_password: str = "votaciones"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "votaciones_db"
    test_postgres_db: str = "votaciones_test"

    def database_url(self, database: str | None = None) -> URL:
        # URL.create escapa la contraseña: admite caracteres especiales sin codificarlos a mano.
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=database or self.postgres_db,
        )


settings = Settings()
