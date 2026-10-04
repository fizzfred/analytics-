from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str
    moex_base_url: str = "https://iss.moex.com"
    moex_boards: str = "TQCB,TQOB"
    request_timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 0.5
    top_bonds_count: int = 10
    max_bonds_limit: int = 100

    db_data_dir: str = "data"
    db_filename: str = "bonds.db"
    key_rate: float = 16.0

    def get_boards_list(self) -> list[str]:
        """Получить список режимов торгов.

        Returns:
            Список режимов торгов из настроек
        """
        return [b.strip() for b in self.moex_boards.split(",") if b.strip()]

    def get_db_path(self) -> Path:
        """Получить путь к файлу базы данных.

        Returns:
            Путь к файлу базы данных
        """
        data_dir = Path(self.db_data_dir)
        data_dir.mkdir(exist_ok=True)
        return data_dir / self.db_filename

    def get_database_url(self) -> str:
        """Получить URL для подключения к базе данных.

        Returns:
            URL строку для подключения к базе данных
        """
        db_path = self.get_db_path()
        return f"sqlite+aiosqlite:///{db_path}"


settings = Settings()
