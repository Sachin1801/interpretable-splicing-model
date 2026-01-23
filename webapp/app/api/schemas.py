"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

from webapp.app.config import settings


class SequenceInput(BaseModel):
    """Schema for single sequence prediction request."""

    sequence: str = Field(
        ...,
        min_length=settings.exon_length,
        max_length=settings.exon_length,
        description=f"The {settings.exon_length}-nucleotide exon sequence (A, C, G, T only)",
    )
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional name for the sequence",
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Optional email address for job completion notification",
    )
    access_token: Optional[str] = Field(
        None,
        max_length=64,
        description="User access token for job history tracking",
    )
    job_title: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional job title (auto-generated if not provided)",
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


class SequenceItem(BaseModel):
    """Schema for a named sequence in batch requests."""

    name: str = Field(
        ...,
        max_length=255,
        description="Name/identifier for this sequence",
    )
    sequence: str = Field(
        ...,
        description=f"The {settings.exon_length}-nucleotide exon sequence",
    )


class BatchSequenceInput(BaseModel):
    """Schema for batch sequence prediction request."""

    sequences: List[SequenceItem] = Field(
        ...,
        min_length=1,
        max_length=settings.max_batch_size,
        description=f"List of named sequences with {settings.exon_length}-nucleotide exon sequences",
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Optional email address for job completion notification",
    )
    access_token: Optional[str] = Field(
        None,
        max_length=64,
        description="User access token for job history tracking",
    )
    job_title: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional job title (auto-generated if not provided)",
    )

    @field_validator("sequences")
    @classmethod
    def validate_sequences(cls, v: List[SequenceItem]) -> List[SequenceItem]:
        """Normalize sequences (don't reject invalid ones - they'll be marked in results)."""
        normalized = []
        for item in v:
            # Normalize the sequence (uppercase, U->T)
            normalized_seq = item.sequence.upper().replace("U", "T").strip()
            normalized.append(SequenceItem(name=item.name, sequence=normalized_seq))
        return normalized


def validate_single_sequence(sequence: str) -> tuple[bool, str]:
    """
    Validate a single sequence and return (is_valid, error_message).
    Used by batch processing to mark invalid sequences without rejecting.
    """
    seq = sequence.upper().replace("U", "T").strip()

    if len(seq) != settings.exon_length:
        return False, f"Must be exactly {settings.exon_length} nucleotides (got {len(seq)})"

    if not re.match(f"^[ACGT]{{{settings.exon_length}}}$", seq):
        invalid_chars = set(seq) - set("ACGT")
        return False, f"Contains invalid characters: {invalid_chars}"

    return True, ""


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

    index: Optional[int] = None  # Original index in batch (for detail lookup)
    name: str
    sequence: str
    status: str  # "success", "invalid", "error"
    psi: Optional[float] = None
    interpretation: Optional[str] = None
    structure: Optional[str] = None
    mfe: Optional[float] = None
    force_plot_data: Optional[Dict[str, Any]] = None
    validation_error: Optional[str] = None  # For invalid sequences
    error: Optional[str] = None  # For processing errors
    warnings: Optional[List[str]] = None


class BatchResultResponse(BaseModel):
    """Schema for batch prediction results."""

    job_id: str
    job_title: Optional[str] = None
    status: str
    total_sequences: int
    successful: int
    invalid: int
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


# ============================================================================
# History and Job Management Schemas
# ============================================================================


class JobSummary(BaseModel):
    """Schema for job summary in history list."""

    id: str
    job_title: Optional[str] = None
    created_at: datetime
    status: str
    is_batch: bool
    sequence_count: int


class JobHistoryResponse(BaseModel):
    """Schema for paginated job history response."""

    jobs: List[JobSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedBatchResultsResponse(BaseModel):
    """Schema for paginated batch results."""

    job_id: str
    job_title: Optional[str] = None
    status: str
    total_sequences: int
    successful_count: int
    invalid_count: int
    failed_count: int
    average_psi: Optional[float] = None  # Average PSI of successful sequences
    results: List[BatchResultItem]
    total: int  # Total results after filtering (for pagination)
    page: int
    page_size: int
    total_pages: int
    created_at: datetime
    expires_at: datetime


class SequenceDetailResponse(BaseModel):
    """Schema for detailed single sequence from batch."""

    job_id: str
    index: int
    name: str
    sequence: str
    status: str
    psi: Optional[float] = None
    interpretation: Optional[str] = None
    structure: Optional[str] = None
    mfe: Optional[float] = None
    force_plot_data: Optional[Dict[str, Any]] = None
    validation_error: Optional[str] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None


# ============================================================================
# Sequence-Centric History Schemas
# ============================================================================


class SequenceHistoryItem(BaseModel):
    """Schema for a single sequence in history (flattened view)."""

    sequence_id: str  # "seq_1", "seq_2", etc.
    job_id: str
    job_title: Optional[str] = None
    created_at: datetime
    psi: Optional[float] = None  # null if not finished or invalid
    status: str  # "finished", "running", "queued", "failed", "invalid"
    sequence: str  # Full 70nt sequence
    is_batch: bool
    batch_index: Optional[int] = None  # 0-based index for batch, null for single


class SequenceHistoryResponse(BaseModel):
    """Schema for paginated sequence history response."""

    sequences: List[SequenceHistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class SequenceExportRequest(BaseModel):
    """Schema for bulk export request."""

    items: List[Dict[str, Any]]  # List of {job_id, batch_index} items
    columns: List[str]  # Column names to include in export


# ============================================================================
# Sequence Name Update Schemas
# ============================================================================


class SequenceNameUpdateRequest(BaseModel):
    """Schema for updating a sequence name."""

    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class SequenceNameUpdateResponse(BaseModel):
    """Schema for sequence name update response."""

    job_id: str
    index: int
    old_name: str
    new_name: str


# ============================================================================
# Mutagenesis Schemas
# ============================================================================


class MutagenesisInput(BaseModel):
    """Schema for mutagenesis analysis request."""

    sequence: str = Field(
        ...,
        min_length=settings.exon_length,
        max_length=settings.exon_length,
        description=f"The {settings.exon_length}-nucleotide reference sequence",
    )
    access_token: Optional[str] = Field(
        None,
        max_length=64,
        description="User access token for job history tracking",
    )
    job_title: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional job title (auto-generated if not provided)",
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


class MutationResult(BaseModel):
    """Schema for a single mutation result."""

    position: int = Field(..., ge=1, le=70, description="1-indexed position in sequence")
    original: str = Field(..., description="Original nucleotide")
    mutant: str = Field(..., description="Mutant nucleotide")
    mutation_label: str = Field(..., description="Mutation label (e.g., 'A1C')")
    psi: Optional[float] = Field(None, ge=0.0, le=1.0, description="Predicted PSI for mutant")
    delta_psi: Optional[float] = Field(None, description="Delta PSI (mutant - reference)")


class MutagenesisResponse(BaseModel):
    """Schema for mutagenesis analysis response."""

    job_id: str
    status: str
    reference_sequence: str
    reference_psi: Optional[float] = None
    total_mutations: int = 210
    completed_mutations: int = 0
    mutations: Optional[List[MutationResult]] = None
    heatmap_data: Optional[Dict[str, Any]] = None
    top_positive: Optional[List[MutationResult]] = None
    top_negative: Optional[List[MutationResult]] = None
    created_at: Optional[datetime] = None
    message: Optional[str] = None


# ============================================================================
# Authentication Schemas
# ============================================================================


class UserRegisterRequest(BaseModel):
    """Schema for user registration request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 characters)")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    """Schema for user info response."""

    id: str
    email: str
    is_active: bool
    created_at: datetime
    linked_token: Optional[str] = None


class AuthResponse(BaseModel):
    """Schema for authentication response."""

    success: bool
    message: str
    user: Optional[UserResponse] = None
    token: Optional[str] = None


class LinkTokenRequest(BaseModel):
    """Schema for linking an access token to a user account."""

    access_token: str = Field(..., max_length=64, description="The access token to link")
