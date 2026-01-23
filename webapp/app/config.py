"""Application configuration settings."""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Splicing Predictor"
    app_version: str = "1.0.0"
    debug: bool = False

    # Paths - computed at class definition time
    # __file__ = webapp/app/config.py
    # parent.parent.parent = interpretable-splicing-model/
    project_root: Path = Path(__file__).parent.parent.parent
    model_path: Path = project_root / "output" / "custom_adjacency_regularizer_20210731_124_step3.h5"
    data_path: Path = project_root / "data"
    database_path: Path = Path(__file__).parent.parent / "splicing.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    # Job settings
    job_retention_days: int = 30
    max_batch_size: int = 100
    prediction_timeout: int = 30  # seconds

    # Email (optional)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None

    # Sequence constants
    exon_length: int = 70
    flanking_length: int = 10
    total_length: int = 90
    pre_sequence: str = "TCTGCCTATGTCTTTCTCTGCCATCCAGGTT"
    post_sequence: str = "CAGGTCTGACTATGGGACCCTTGATGTTTT"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
