"""FastAPI routes for the prediction API."""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text

from webapp.app.database import get_db
from webapp.app.models.job import Job
from webapp.app.services.predictor import get_predictor, SplicingPredictor
from webapp.app.config import settings
from webapp.app.api.schemas import (
    SequenceInput,
    BatchSequenceInput,
    PredictionResponse,
    JobStatusResponse,
    SingleResultResponse,
    BatchResultResponse,
    BatchResultItem,
    ExampleSequence,
    ExampleSequencesResponse,
    HealthResponse,
    ErrorResponse,
)

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

    # Create job in database
    job = Job(
        id=job_id,
        status="queued",
        sequence=request.sequence,
        email=request.email,
        is_batch=False,
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
    Maximum batch size is 100 sequences.
    """
    job_id = str(uuid.uuid4())

    # Create job in database
    job = Job(
        id=job_id,
        status="queued",
        sequence=request.sequences[0],  # Store first sequence as reference
        email=request.email,
        is_batch=True,
    )
    job.set_batch_sequences(request.sequences)
    db.add(job)
    db.commit()

    # Run batch prediction synchronously
    try:
        job.status = "running"
        db.commit()

        predictor = get_predictor()
        results = predictor.predict_batch(request.sequences)

        # Update job with results
        job.status = "finished"
        job.set_batch_results(results)
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
        message=f"Batch prediction completed for {len(request.sequences)} sequences",
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
        failed = len(results) - successful

        return BatchResultResponse(
            job_id=job.id,
            status=job.status,
            total_sequences=len(results),
            successful=successful,
            failed=failed,
            results=[
                BatchResultItem(
                    sequence=r.get("sequence", ""),
                    status=r.get("status", "unknown"),
                    psi=r.get("psi"),
                    interpretation=r.get("interpretation"),
                    structure=r.get("structure"),
                    mfe=r.get("mfe"),
                    error=r.get("error"),
                    warnings=r.get("warnings"),
                )
                for r in results
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
    format: str = Path(..., pattern="^(csv|json|tsv)$"),
    db: Session = Depends(get_db),
):
    """
    Export job results in the specified format.

    Supported formats: csv, json, tsv
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "finished":
        raise HTTPException(status_code=400, detail="Job not yet complete")

    if format == "json":
        content = json.dumps(job.to_dict(), indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="result_{job_id}.json"'}
        )

    elif format in ("csv", "tsv"):
        delimiter = "," if format == "csv" else "\t"

        if job.is_batch:
            results = job.get_batch_results()
            header = ["sequence", "psi", "interpretation", "structure", "mfe", "status", "error"]
            rows = [delimiter.join(header)]
            for r in results:
                row = [
                    r.get("sequence", ""),
                    str(r.get("psi", "")),
                    r.get("interpretation", ""),
                    r.get("structure", ""),
                    str(r.get("mfe", "")),
                    r.get("status", ""),
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
