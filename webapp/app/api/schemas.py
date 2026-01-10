"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

from app.config import settings


class SequenceInput(BaseModel):
    """Schema for single sequence prediction request."""

    sequence: str = Field(
        ...,
        min_length=settings.exon_length,
        max_length=settings.exon_length,
        description=f"The {settings.exon_length}-nucleotide exon sequence (A, C, G, T only)",
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Optional email address for job completion notification",
    )

    @field_validator("sequence")
    @classmethod
    def validate_sequence(cls, v: str) -> str:
        """Validate that sequence contains only valid nucleotides."""
        v = v.upper().replace("U", "T")

        if len(v) != settings.exon_length:
            raise ValueError(
                f"Sequence must be exactly {settings.exon_length} nucleotides (got {len(v)})"
            )

        if not re.match(f"^[ACGT]{{{settings.exon_length}}}$", v):
            invalid_chars = set(v) - set("ACGT")
            raise ValueError(
                f"Sequence must contain only A, C, G, T. Found invalid characters: {invalid_chars}"
            )

        return v


class BatchSequenceInput(BaseModel):
    """Schema for batch sequence prediction request."""

    sequences: List[str] = Field(
        ...,
        min_length=1,
        max_length=settings.max_batch_size,
        description=f"List of {settings.exon_length}-nucleotide exon sequences",
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Optional email address for job completion notification",
    )

    @field_validator("sequences")
    @classmethod
    def validate_sequences(cls, v: List[str]) -> List[str]:
        """Validate all sequences in the batch."""
        validated = []
        errors = []

        for i, seq in enumerate(v):
            seq = seq.upper().replace("U", "T").strip()

            if len(seq) != settings.exon_length:
                errors.append(
                    f"Sequence {i + 1}: must be exactly {settings.exon_length} nucleotides (got {len(seq)})"
                )
                continue

            if not re.match(f"^[ACGT]{{{settings.exon_length}}}$", seq):
                invalid_chars = set(seq) - set("ACGT")
                errors.append(
                    f"Sequence {i + 1}: contains invalid characters: {invalid_chars}"
                )
                continue

            validated.append(seq)

        if errors:
            raise ValueError("; ".join(errors))

        return validated


class PredictionResponse(BaseModel):
    """Schema for prediction submission response."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status (queued, running, finished, failed)")
    status_url: str = Field(..., description="URL to check job status")
    result_url: str = Field(..., description="URL to view results")
    message: Optional[str] = Field(None, description="Optional message")


class JobStatusResponse(BaseModel):
    """Schema for job status response."""

    job_id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    message: Optional[str] = None


class SingleResultResponse(BaseModel):
    """Schema for single prediction result."""

    job_id: str
    status: str
    sequence: str
    psi: float = Field(..., ge=0.0, le=1.0, description="Predicted PSI value")
    interpretation: str
    structure: Optional[str] = None
    mfe: Optional[float] = None
    force_plot_data: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    created_at: datetime
    expires_at: datetime


class BatchResultItem(BaseModel):
    """Schema for a single item in batch results."""

    sequence: str
    status: str
    psi: Optional[float] = None
    interpretation: Optional[str] = None
    structure: Optional[str] = None
    mfe: Optional[float] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None


class BatchResultResponse(BaseModel):
    """Schema for batch prediction results."""

    job_id: str
    status: str
    total_sequences: int
    successful: int
    failed: int
    results: List[BatchResultItem]
    created_at: datetime
    expires_at: datetime


class ExampleSequence(BaseModel):
    """Schema for example sequence."""

    name: str
    sequence: str
    description: str
    expected_psi: Optional[float] = None


class ExampleSequencesResponse(BaseModel):
    """Schema for example sequences response."""

    sequences: List[ExampleSequence]


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    model_loaded: bool
    database_connected: bool
