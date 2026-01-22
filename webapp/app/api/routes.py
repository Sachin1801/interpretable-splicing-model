"""FastAPI routes for the prediction API."""

import uuid
import json
import string
import random
from datetime import datetime, timedelta
from typing import Optional, List
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_

from webapp.app.database import get_db
from webapp.app.models.job import Job
from webapp.app.services.predictor import get_predictor, SplicingPredictor
from webapp.app.services.vis_data import get_vis_data
from webapp.app.config import settings
from webapp.app.api.schemas import (
    SequenceInput,
    BatchSequenceInput,
    SequenceItem,
    PredictionResponse,
    JobStatusResponse,
    SingleResultResponse,
    BatchResultResponse,
    BatchResultItem,
    ExampleSequence,
    ExampleSequencesResponse,
    HealthResponse,
    ErrorResponse,
    JobSummary,
    JobHistoryResponse,
    PaginatedBatchResultsResponse,
    SequenceDetailResponse,
    SequenceHistoryItem,
    SequenceHistoryResponse,
    SequenceExportRequest,
    SequenceNameUpdateRequest,
    SequenceNameUpdateResponse,
    validate_single_sequence,
)


def generate_job_title() -> str:
    """Generate an auto job title in format: 2026-01-15_abc12"""
    date_part = datetime.utcnow().strftime("%Y-%m-%d")
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"{date_part}_{random_part}"

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(db: Session = Depends(get_db)):
    """Check API health status."""
    model_loaded = False
    try:
        predictor = get_predictor()
        model_loaded = predictor.model is not None
    except Exception:
        pass

    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if model_loaded and db_connected else "degraded",
        version=settings.app_version,
        model_loaded=model_loaded,
        database_connected=db_connected,
    )


@router.post("/predict", response_model=PredictionResponse, tags=["prediction"])
async def submit_prediction(
    request: SequenceInput,
    db: Session = Depends(get_db),
):
    """
    Submit a single sequence for PSI prediction.

    The sequence must be exactly 70 nucleotides long and contain only A, C, G, T.
    """
    job_id = str(uuid.uuid4())

    # Generate job title if not provided
    job_title = request.job_title if request.job_title else generate_job_title()

    # Create job in database
    job = Job(
        id=job_id,
        status="queued",
        sequence=request.sequence,
        email=request.email,
        is_batch=False,
        access_token=request.access_token,
        job_title=job_title,
    )
    db.add(job)
    db.commit()

    # Run prediction synchronously
    try:
        job.status = "running"
        db.commit()

        predictor = get_predictor()
        result = predictor.predict_single(request.sequence)

        # Get force plot data
        force_plot_data = predictor.get_force_plot_data(request.sequence)

        # Update job with results
        job.status = "finished"
        job.psi = result["psi"]
        job.structure = result["structure"]
        job.mfe = result["mfe"]
        job.interpretation = result["interpretation"]
        job.set_force_plot_data(force_plot_data)
        if result["warnings"]:
            job.warnings = json.dumps(result["warnings"])
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    return PredictionResponse(
        job_id=job_id,
        status=job.status,
        status_url=f"/api/status/{job_id}",
        result_url=f"/result/{job_id}",
        message="Prediction completed successfully",
    )


@router.post("/batch", response_model=PredictionResponse, tags=["prediction"])
async def submit_batch_prediction(
    request: BatchSequenceInput,
    db: Session = Depends(get_db),
):
    """
    Submit multiple sequences for batch PSI prediction.

    Each sequence must be exactly 70 nucleotides long and contain only A, C, G, T.
    Invalid sequences will be marked in results but won't block processing of valid ones.
    Maximum batch size is 100 sequences.
    """
    job_id = str(uuid.uuid4())

    # Generate job title if not provided
    job_title = request.job_title if request.job_title else generate_job_title()

    # Convert sequences to dict format for storage
    sequences_for_storage = [
        {"name": seq.name, "sequence": seq.sequence}
        for seq in request.sequences
    ]

    # Create job in database
    job = Job(
        id=job_id,
        status="queued",
        sequence=request.sequences[0].sequence,  # Store first sequence as reference
        email=request.email,
        is_batch=True,
        access_token=request.access_token,
        job_title=job_title,
    )
    job.set_batch_sequences(sequences_for_storage)
    db.add(job)
    db.commit()

    # Run batch prediction synchronously
    try:
        job.status = "running"
        db.commit()

        predictor = get_predictor()
        results = []

        for seq_item in request.sequences:
            # Validate each sequence
            is_valid, validation_error = validate_single_sequence(seq_item.sequence)

            if not is_valid:
                # Mark as invalid, don't process
                results.append({
                    "name": seq_item.name,
                    "sequence": seq_item.sequence,
                    "status": "invalid",
                    "validation_error": validation_error,
                    "psi": None,
                    "interpretation": None,
                    "structure": None,
                    "mfe": None,
                })
            else:
                # Process valid sequence
                try:
                    result = predictor.predict_single(seq_item.sequence)
                    force_plot_data = predictor.get_force_plot_data(seq_item.sequence)
                    results.append({
                        "name": seq_item.name,
                        "sequence": seq_item.sequence,
                        "status": "success",
                        "psi": result["psi"],
                        "interpretation": result["interpretation"],
                        "structure": result["structure"],
                        "mfe": result["mfe"],
                        "force_plot_data": force_plot_data,
                        "warnings": result.get("warnings"),
                    })
                except Exception as e:
                    results.append({
                        "name": seq_item.name,
                        "sequence": seq_item.sequence,
                        "status": "error",
                        "error": str(e),
                        "psi": None,
                        "interpretation": None,
                        "structure": None,
                        "mfe": None,
                    })

        # Update job with results
        job.status = "finished"
        job.set_batch_results(results)
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    # Count results
    successful = sum(1 for r in results if r.get("status") == "success")
    invalid = sum(1 for r in results if r.get("status") == "invalid")
    errored = sum(1 for r in results if r.get("status") == "error")

    return PredictionResponse(
        job_id=job_id,
        status=job.status,
        status_url=f"/api/status/{job_id}",
        result_url=f"/result/{job_id}",
        message=f"Batch completed: {successful} successful, {invalid} invalid, {errored} errors",
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse, tags=["results"])
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Get the status of a prediction job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    progress = None
    if job.status == "queued":
        progress = 0
    elif job.status == "running":
        progress = 50
    elif job.status == "finished":
        progress = 100
    elif job.status == "failed":
        progress = 100

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        progress=progress,
        message=job.error_message if job.status == "failed" else None,
    )


@router.get("/result/{job_id}", tags=["results"])
async def get_job_result(
    job_id: str,
    db: Session = Depends(get_db),
):
    """
    Get the results of a prediction job.

    Returns different response format for single vs batch predictions.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "finished":
        return {
            "job_id": job.id,
            "status": job.status,
            "message": "Job not yet complete" if job.status != "failed" else job.error_message,
        }

    if job.is_batch:
        # Return batch results
        results = job.get_batch_results()
        successful = sum(1 for r in results if r.get("status") == "success")
        invalid = sum(1 for r in results if r.get("status") == "invalid")
        failed = sum(1 for r in results if r.get("status") == "error")

        return BatchResultResponse(
            job_id=job.id,
            job_title=job.job_title,
            status=job.status,
            total_sequences=len(results),
            successful=successful,
            invalid=invalid,
            failed=failed,
            results=[
                BatchResultItem(
                    name=r.get("name", f"Seq_{i+1}"),
                    sequence=r.get("sequence", ""),
                    status=r.get("status", "unknown"),
                    psi=r.get("psi"),
                    interpretation=r.get("interpretation"),
                    structure=r.get("structure"),
                    mfe=r.get("mfe"),
                    force_plot_data=r.get("force_plot_data"),
                    validation_error=r.get("validation_error"),
                    error=r.get("error"),
                    warnings=r.get("warnings"),
                )
                for i, r in enumerate(results)
            ],
            created_at=job.created_at,
            expires_at=job.expires_at,
        )
    else:
        # Return single result
        force_plot_data = json.loads(job.force_plot_data) if job.force_plot_data else None
        warnings = json.loads(job.warnings) if job.warnings else None

        return SingleResultResponse(
            job_id=job.id,
            status=job.status,
            sequence=job.sequence,
            psi=job.psi,
            interpretation=job.interpretation,
            structure=job.structure,
            mfe=job.mfe,
            force_plot_data=force_plot_data,
            warnings=warnings,
            created_at=job.created_at,
            expires_at=job.expires_at,
        )


@router.get("/heatmap/{job_id}", tags=["visualization"])
async def get_heatmap_data(
    job_id: str,
    db: Session = Depends(get_db),
):
    """
    Get filter activation heatmap data for a prediction job.

    Returns position-wise filter activations for heatmap visualization.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "finished":
        raise HTTPException(status_code=400, detail="Job not yet complete")

    # For batch jobs, use the first sequence
    sequence = job.sequence

    try:
        predictor = get_predictor()
        heatmap_data = predictor.get_heatmap_data(sequence)
        return heatmap_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating heatmap data: {str(e)}")


@router.get("/vis_data/{job_id}", tags=["visualization"])
async def get_vis_data_endpoint(
    job_id: str,
    batch_index: Optional[int] = Query(None, description="Index of sequence in batch job (0-based)"),
    db: Session = Depends(get_db),
):
    """
    Get hierarchical visualization data for silhouette and heatmap views.

    Returns collapsed filter activations organized both by feature and by position.
    This data powers the silhouette view and the new heatmap with diverging colors.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "finished":
        raise HTTPException(status_code=400, detail="Job not yet complete")

    # Get the appropriate sequence
    if job.is_batch and batch_index is not None:
        # Get specific sequence from batch
        results = job.get_batch_results()
        if batch_index >= len(results):
            raise HTTPException(status_code=404, detail=f"Batch index {batch_index} not found")
        sequence = results[batch_index].get("sequence", "")
        if not sequence:
            raise HTTPException(status_code=400, detail="Sequence not found in batch results")
    else:
        # Use the main sequence (or first sequence for batch)
        sequence = job.sequence

    try:
        vis_data = get_vis_data(sequence)
        return vis_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating visualization data: {str(e)}")


@router.get("/example", response_model=ExampleSequencesResponse, tags=["examples"])
async def get_example_sequences():
    """
    Get example sequences for the 'Try Example' feature.

    These are curated sequences from the test dataset demonstrating different PSI values.
    """
    from pathlib import Path
    import json

    # Try to load from extracted examples file
    examples_file = Path(__file__).parent.parent.parent / "static" / "examples.json"

    if examples_file.exists():
        with open(examples_file) as f:
            data = json.load(f)
            examples = [
                ExampleSequence(
                    name=seq["name"],
                    sequence=seq["sequence"],
                    description=seq["description"],
                    expected_psi=seq.get("expected_psi"),
                )
                for seq in data["sequences"]
            ]
    else:
        # Fallback to hardcoded examples
        examples = [
            ExampleSequence(
                name="High Inclusion Example",
                sequence="GGTAGTACGCCAATTCGCCGGTGCCGCGAGCCAGAGGCTACCAAAACTTGACAAGCCTACATATACTACT",
                description="This sequence demonstrates strong exon inclusion (actual PSI = 0.982)",
                expected_psi=0.982,
            ),
            ExampleSequence(
                name="Balanced Example",
                sequence="CTACCACCTCCCAAGCTTACACACTGTTTGATGAAAGGTCGCCACAACGTTCCCTCACCCCTAGTCTCGC",
                description="This sequence shows balanced inclusion/skipping (actual PSI = 0.487)",
                expected_psi=0.487,
            ),
            ExampleSequence(
                name="High Skipping Example",
                sequence="ACACTCCGCAGCACACTCGGCAAAGAAGTTAGGCCCCGCTCTTACAAACATCTAGCATTTTGTATGGTCT",
                description="This sequence demonstrates strong exon skipping (actual PSI = 0.000)",
                expected_psi=0.0,
            ),
        ]

    return ExampleSequencesResponse(sequences=examples)


@router.get("/export/{job_id}/{format}", tags=["export"])
async def export_results(
    job_id: str,
    format: str = Path(..., pattern="^(csv|tsv)$"),
    db: Session = Depends(get_db),
):
    """
    Export job results in the specified format.

    Supported formats: csv, tsv
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "finished":
        raise HTTPException(status_code=400, detail="Job not yet complete")

    if format in ("csv", "tsv"):
        delimiter = "," if format == "csv" else "\t"

        if job.is_batch:
            results = job.get_batch_results()
            header = ["name", "sequence", "psi", "interpretation", "structure", "mfe", "status", "validation_error", "error"]
            rows = [delimiter.join(header)]
            for i, r in enumerate(results):
                row = [
                    r.get("name", f"Seq_{i+1}"),
                    r.get("sequence", ""),
                    str(r.get("psi", "")),
                    r.get("interpretation", ""),
                    r.get("structure", ""),
                    str(r.get("mfe", "")),
                    r.get("status", ""),
                    r.get("validation_error", ""),
                    r.get("error", ""),
                ]
                rows.append(delimiter.join(row))
            content = "\n".join(rows)
        else:
            header = ["sequence", "psi", "interpretation", "structure", "mfe"]
            row = [
                job.sequence,
                str(job.psi),
                job.interpretation or "",
                job.structure or "",
                str(job.mfe or ""),
            ]
            content = delimiter.join(header) + "\n" + delimiter.join(row)

        media_type = "text/csv" if format == "csv" else "text/tab-separated-values"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="result_{job_id}.{format}"'}
        )

    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


# ============================================================================
# History and Job Management Endpoints
# ============================================================================


@router.get("/history", response_model=JobHistoryResponse, tags=["history"])
async def get_job_history(
    access_token: str = Query(..., description="User access token"),
    search: Optional[str] = Query(None, description="Search job titles"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db),
):
    """
    Get paginated job history for a user token.

    Jobs are filtered by access_token and optionally by job title search and date range.
    """
    # Build query
    query = db.query(Job).filter(Job.access_token == access_token)

    # Apply search filter
    if search:
        query = query.filter(Job.job_title.ilike(f"%{search}%"))

    # Apply date filters
    if date_from:
        query = query.filter(Job.created_at >= date_from)
    if date_to:
        query = query.filter(Job.created_at <= date_to)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    query = query.order_by(Job.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    jobs = query.all()

    # Build response
    job_summaries = [
        JobSummary(
            id=job.id,
            job_title=job.job_title,
            created_at=job.created_at,
            status=job.status,
            is_batch=job.is_batch,
            sequence_count=job.get_sequence_count(),
        )
        for job in jobs
    ]

    total_pages = ceil(total / page_size) if total > 0 else 1

    return JobHistoryResponse(
        jobs=job_summaries,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.delete("/jobs/{job_id}", tags=["history"])
async def delete_job(
    job_id: str,
    access_token: str = Query(..., description="User access token"),
    db: Session = Depends(get_db),
):
    """
    Delete a job.

    Only the owner (matching access_token) can delete a job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.access_token != access_token:
        raise HTTPException(status_code=403, detail="Access denied - token does not match")

    db.delete(job)
    db.commit()

    return {"status": "deleted", "job_id": job_id}


@router.get("/batch/{job_id}/results", response_model=PaginatedBatchResultsResponse, tags=["results"])
async def get_batch_results_paginated(
    job_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Results per page"),
    search: Optional[str] = Query(None, description="Search by name or sequence"),
    db: Session = Depends(get_db),
):
    """
    Get paginated batch results with optional search.

    Search filters results by sequence name or sequence content.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.is_batch:
        raise HTTPException(status_code=400, detail="This is not a batch job")

    if job.status != "finished":
        raise HTTPException(status_code=400, detail="Job not yet complete")

    all_results = job.get_batch_results()

    # Calculate statistics from all results (before filtering)
    total_sequences = len(all_results)
    successful_count = sum(1 for r in all_results if r.get("status") == "success")
    invalid_count = sum(1 for r in all_results if r.get("status") == "invalid")
    failed_count = sum(1 for r in all_results if r.get("status") == "error")

    # Calculate average PSI from successful sequences
    successful_psis = [r.get("psi") for r in all_results if r.get("status") == "success" and r.get("psi") is not None]
    average_psi = sum(successful_psis) / len(successful_psis) if successful_psis else None

    # Add original index to each result for detail lookup
    indexed_results = [(i, r) for i, r in enumerate(all_results)]

    # Apply search filter
    if search:
        search_lower = search.lower()
        indexed_results = [
            (i, r) for i, r in indexed_results
            if search_lower in r.get("name", "").lower()
            or search_lower in r.get("sequence", "").lower()
        ]

    # Total after filtering (for pagination)
    total = len(indexed_results)

    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_results = indexed_results[start_idx:end_idx]

    total_pages = ceil(total / page_size) if total > 0 else 1

    return PaginatedBatchResultsResponse(
        job_id=job.id,
        job_title=job.job_title,
        status=job.status,
        total_sequences=total_sequences,
        successful_count=successful_count,
        invalid_count=invalid_count,
        failed_count=failed_count,
        average_psi=average_psi,
        results=[
            BatchResultItem(
                index=orig_idx,
                name=r.get("name", f"Seq_{orig_idx+1}"),
                sequence=r.get("sequence", ""),
                status=r.get("status", "unknown"),
                psi=r.get("psi"),
                interpretation=r.get("interpretation"),
                structure=r.get("structure"),
                mfe=r.get("mfe"),
                force_plot_data=r.get("force_plot_data"),
                validation_error=r.get("validation_error"),
                error=r.get("error"),
                warnings=r.get("warnings"),
            )
            for orig_idx, r in paginated_results
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        created_at=job.created_at,
        expires_at=job.expires_at,
    )


@router.get("/batch/{job_id}/sequence/{index}", response_model=SequenceDetailResponse, tags=["results"])
async def get_sequence_detail(
    job_id: str,
    index: int = Path(..., ge=0, description="Sequence index (0-based)"),
    db: Session = Depends(get_db),
):
    """
    Get detailed results for a single sequence in a batch job.

    Returns full details including force plot data for visualization.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.is_batch:
        raise HTTPException(status_code=400, detail="This is not a batch job")

    if job.status != "finished":
        raise HTTPException(status_code=400, detail="Job not yet complete")

    results = job.get_batch_results()
    if index >= len(results):
        raise HTTPException(status_code=404, detail=f"Sequence index {index} not found")

    r = results[index]

    return SequenceDetailResponse(
        job_id=job.id,
        index=index,
        name=r.get("name", f"Seq_{index+1}"),
        sequence=r.get("sequence", ""),
        status=r.get("status", "unknown"),
        psi=r.get("psi"),
        interpretation=r.get("interpretation"),
        structure=r.get("structure"),
        mfe=r.get("mfe"),
        force_plot_data=r.get("force_plot_data"),
        validation_error=r.get("validation_error"),
        error=r.get("error"),
        warnings=r.get("warnings"),
    )


@router.patch("/batch/{job_id}/sequence/{index}/name", response_model=SequenceNameUpdateResponse, tags=["results"])
async def update_sequence_name(
    job_id: str,
    index: int = Path(..., ge=0, description="Sequence index (0-based)"),
    request: SequenceNameUpdateRequest = None,
    db: Session = Depends(get_db),
):
    """Update the name of a specific sequence in a batch job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.is_batch:
        raise HTTPException(status_code=400, detail="Not a batch job")

    if job.status != "finished":
        raise HTTPException(status_code=400, detail="Job not finished")

    batch_results = job.get_batch_results()
    if index >= len(batch_results):
        raise HTTPException(status_code=400, detail=f"Index {index} out of range")

    old_name = batch_results[index].get("name", f"Seq_{index+1}")
    batch_results[index]["name"] = request.name
    job.set_batch_results(batch_results)

    # Also update batch_sequences if exists
    batch_sequences = job.get_batch_sequences()
    if index < len(batch_sequences):
        batch_sequences[index]["name"] = request.name
        job.set_batch_sequences(batch_sequences)

    db.commit()

    return SequenceNameUpdateResponse(
        job_id=job.id, index=index, old_name=old_name, new_name=request.name
    )


@router.get("/history/sequences", response_model=SequenceHistoryResponse, tags=["history"])
async def get_sequence_history(
    access_token: str = Query(..., description="User access token"),
    search: Optional[str] = Query(None, description="Search job titles or sequence content"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db),
):
    """
    Get paginated sequence history (flattened view).

    Each sequence appears as its own row. Batch jobs are flattened so each
    sequence in the batch has its own entry.
    """
    # Build query for jobs
    query = db.query(Job).filter(Job.access_token == access_token)

    # Apply date filters
    if date_from:
        query = query.filter(Job.created_at >= date_from)
    if date_to:
        query = query.filter(Job.created_at <= date_to)

    # Order by created_at descending
    query = query.order_by(Job.created_at.desc())

    # Get all jobs (we'll flatten and paginate in memory)
    jobs = query.all()

    # Flatten jobs into sequences
    all_sequences = []
    for job in jobs:
        if job.is_batch:
            # Batch job: create an entry for each sequence
            if job.status == "finished":
                results = job.get_batch_results()
                for idx, r in enumerate(results):
                    seq_status = r.get("status", "unknown")
                    # Map batch result status to display status
                    if seq_status == "success":
                        display_status = "finished"
                    elif seq_status == "invalid":
                        display_status = "invalid"
                    elif seq_status == "error":
                        display_status = "failed"
                    else:
                        display_status = seq_status

                    all_sequences.append(SequenceHistoryItem(
                        sequence_id=r.get("name", f"Seq_{idx + 1}"),
                        job_id=job.id,
                        job_title=job.job_title,
                        created_at=job.created_at,
                        psi=r.get("psi"),
                        status=display_status,
                        sequence=r.get("sequence", ""),
                        is_batch=True,
                        batch_index=idx,
                    ))
            else:
                # Job not finished - get sequences from batch_sequences
                batch_seqs = job.get_batch_sequences()
                for idx, s in enumerate(batch_seqs):
                    all_sequences.append(SequenceHistoryItem(
                        sequence_id=s.get("name", f"Seq_{idx + 1}"),
                        job_id=job.id,
                        job_title=job.job_title,
                        created_at=job.created_at,
                        psi=None,
                        status=job.status,
                        sequence=s.get("sequence", ""),
                        is_batch=True,
                        batch_index=idx,
                    ))
        else:
            # Single job: one entry
            all_sequences.append(SequenceHistoryItem(
                sequence_id="seq_1",
                job_id=job.id,
                job_title=job.job_title,
                created_at=job.created_at,
                psi=job.psi if job.status == "finished" else None,
                status=job.status,
                sequence=job.sequence or "",
                is_batch=False,
                batch_index=None,
            ))

    # Apply search filter (matches job_title OR sequence content)
    if search:
        search_lower = search.lower()
        all_sequences = [
            seq for seq in all_sequences
            if (seq.job_title and search_lower in seq.job_title.lower())
            or search_lower in seq.sequence.lower()
        ]

    # Get total count after filtering
    total = len(all_sequences)

    # Paginate
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated = all_sequences[start_idx:end_idx]

    total_pages = ceil(total / page_size) if total > 0 else 1

    return SequenceHistoryResponse(
        sequences=paginated,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/sequences/export", tags=["history"])
async def export_sequences(
    request: SequenceExportRequest,
    access_token: str = Query(..., description="User access token"),
    db: Session = Depends(get_db),
):
    """
    Export selected sequences as CSV.

    Accepts a list of {job_id, batch_index} items and column names to include.
    batch_index should be null for single-sequence jobs.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="No items to export")

    if not request.columns:
        raise HTTPException(status_code=400, detail="No columns specified")

    # Collect unique job IDs
    job_ids = list(set(item.get("job_id") for item in request.items if item.get("job_id")))

    # Fetch jobs
    jobs = db.query(Job).filter(
        Job.id.in_(job_ids),
        Job.access_token == access_token
    ).all()

    job_map = {job.id: job for job in jobs}

    # Build CSV rows
    rows = []
    for item in request.items:
        job_id = item.get("job_id")
        batch_index = item.get("batch_index")

        job = job_map.get(job_id)
        if not job:
            continue

        # Get sequence data
        if job.is_batch and batch_index is not None:
            if job.status == "finished":
                results = job.get_batch_results()
                if batch_index < len(results):
                    r = results[batch_index]
                    seq_data = {
                        "sequence_id": f"seq_{batch_index + 1}",
                        "job_id": job.id,
                        "job_title": job.job_title or "",
                        "created_at": job.created_at.isoformat(),
                        "sequence": r.get("sequence", ""),
                        "psi": str(r.get("psi", "")) if r.get("psi") is not None else "",
                        "status": r.get("status", ""),
                        "interpretation": r.get("interpretation", "") or "",
                        "structure": r.get("structure", "") or "",
                        "mfe": str(r.get("mfe", "")) if r.get("mfe") is not None else "",
                    }
                    rows.append(seq_data)
            else:
                batch_seqs = job.get_batch_sequences()
                if batch_index < len(batch_seqs):
                    s = batch_seqs[batch_index]
                    seq_data = {
                        "sequence_id": f"seq_{batch_index + 1}",
                        "job_id": job.id,
                        "job_title": job.job_title or "",
                        "created_at": job.created_at.isoformat(),
                        "sequence": s.get("sequence", ""),
                        "psi": "",
                        "status": job.status,
                        "interpretation": "",
                        "structure": "",
                        "mfe": "",
                    }
                    rows.append(seq_data)
        else:
            # Single sequence job
            seq_data = {
                "sequence_id": "seq_1",
                "job_id": job.id,
                "job_title": job.job_title or "",
                "created_at": job.created_at.isoformat(),
                "sequence": job.sequence or "",
                "psi": str(job.psi) if job.psi is not None else "",
                "status": job.status,
                "interpretation": job.interpretation or "",
                "structure": job.structure or "",
                "mfe": str(job.mfe) if job.mfe is not None else "",
            }
            rows.append(seq_data)

    if not rows:
        raise HTTPException(status_code=400, detail="No valid sequences found to export")

    # Build CSV content
    # Filter columns to only include requested ones
    valid_columns = ["sequence_id", "job_id", "job_title", "created_at", "sequence", "psi", "status", "interpretation", "structure", "mfe"]
    columns = [c for c in request.columns if c in valid_columns]

    if not columns:
        raise HTTPException(status_code=400, detail="No valid columns specified")

    csv_lines = [",".join(columns)]
    for row in rows:
        values = []
        for col in columns:
            val = str(row.get(col, ""))
            # Escape quotes and wrap in quotes if contains comma or quotes
            if "," in val or '"' in val or "\n" in val:
                val = '"' + val.replace('"', '""') + '"'
            values.append(val)
        csv_lines.append(",".join(values))

    content = "\n".join(csv_lines)

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="sequences_export.csv"'}
    )
