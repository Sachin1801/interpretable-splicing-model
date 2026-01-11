"""Job database model for tracking prediction jobs."""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, Index
from sqlalchemy.sql import func
from typing import Optional, List
import json
import uuid

from webapp.app.database import Base
from webapp.app.config import settings


class Job(Base):
    """SQLAlchemy model for prediction jobs."""

    __tablename__ = "jobs"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Status tracking
    status = Column(String(20), nullable=False, default="queued")
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    expires_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(days=settings.job_retention_days),
    )

    # Input data
    sequence = Column(Text, nullable=False)
    is_batch = Column(Boolean, default=False)
    batch_sequences = Column(Text, nullable=True)  # JSON array
    email = Column(String(255), nullable=True)

    # Results (nullable until job finishes)
    psi = Column(Float, nullable=True)
    structure = Column(Text, nullable=True)
    mfe = Column(Float, nullable=True)
    force_plot_data = Column(Text, nullable=True)  # JSON
    interpretation = Column(Text, nullable=True)

    # Batch results (for batch jobs)
    batch_results = Column(Text, nullable=True)  # JSON array of results

    # Error handling
    error_message = Column(Text, nullable=True)
    warnings = Column(Text, nullable=True)  # JSON array of warnings

    # Indexes
    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_expires", "expires_at"),
    )

    def to_dict(self) -> dict:
        """Convert job to dictionary for API response."""
        result = {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "sequence": self.sequence,
            "is_batch": self.is_batch,
            "email": self.email,
        }

        # Add results if job is finished
        if self.status == "finished":
            if self.is_batch:
                result["batch_results"] = json.loads(self.batch_results) if self.batch_results else []
            else:
                result["psi"] = self.psi
                result["structure"] = self.structure
                result["mfe"] = self.mfe
                result["force_plot_data"] = json.loads(self.force_plot_data) if self.force_plot_data else None
                result["interpretation"] = self.interpretation

        # Add warnings if present
        if self.warnings:
            result["warnings"] = json.loads(self.warnings)

        # Add error if failed
        if self.status == "failed":
            result["error_message"] = self.error_message

        return result

    def set_batch_sequences(self, sequences: List[str]):
        """Set batch sequences as JSON."""
        self.batch_sequences = json.dumps(sequences)

    def get_batch_sequences(self) -> List[str]:
        """Get batch sequences from JSON."""
        return json.loads(self.batch_sequences) if self.batch_sequences else []

    def set_batch_results(self, results: List[dict]):
        """Set batch results as JSON."""
        self.batch_results = json.dumps(results)

    def get_batch_results(self) -> List[dict]:
        """Get batch results from JSON."""
        return json.loads(self.batch_results) if self.batch_results else []

    def add_warning(self, warning: str):
        """Add a warning message."""
        warnings = json.loads(self.warnings) if self.warnings else []
        warnings.append(warning)
        self.warnings = json.dumps(warnings)

    def set_force_plot_data(self, data: dict):
        """Set force plot data as JSON."""
        self.force_plot_data = json.dumps(data)

    @staticmethod
    def get_interpretation(psi: float) -> str:
        """Get human-readable interpretation of PSI value."""
        if psi >= 0.8:
            return "Strong exon inclusion predicted"
        elif psi >= 0.6:
            return "Moderate inclusion tendency"
        elif psi >= 0.4:
            return "Balanced inclusion/skipping"
        elif psi >= 0.2:
            return "Moderate skipping tendency"
        else:
            return "Strong exon skipping predicted"
