"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from webapp.app.config import settings
from webapp.app.database import init_db, get_db
from webapp.app.api.routes import router as api_router
from webapp.app.models.job import Job

# PyShiny imports for visualizations
try:
    from shiny import App
    from webapp.app.shiny_apps.heatmap_app import create_app as create_heatmap_app
    from webapp.app.shiny_apps.silhouette_app import create_app as create_silhouette_app
    SHINY_AVAILABLE = True
except Exception as e:
    import traceback
    SHINY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"PyShiny not available - visualizations will be disabled: {e}")
    logger.warning(f"Full traceback:\n{traceback.format_exc()}")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("Starting Splicing Predictor API...")

    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")

    # Pre-load the model
    logger.info("Pre-loading prediction model...")
    try:
        from webapp.app.services.predictor import get_predictor
        predictor = get_predictor()
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.warning("Model will be loaded on first request")

    yield

    # Shutdown
    logger.info("Shutting down Splicing Predictor API...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
    ## RNA Splicing Prediction Web Server

    This web server predicts RNA alternative splicing outcomes (PSI values)
    using an interpretable deep neural network.

    ### Features
    - Predict PSI for 70-nucleotide exon sequences
    - Batch processing for multiple sequences
    - Interactive force plot visualizations
    - Export results in CSV, JSON, TSV formats

    ### Citation
    Liao SE, Sudarshan M, and Regev O. "Machine learning for discovery:
    deciphering RNA splicing logic." bioRxiv (2022).

    ---

    **This website is free and open to all users and there is no login requirement.**
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Mount PyShiny visualization apps
# Use starlette_app for mounting so behavior is identical locally and on Hugging Face Spaces
if SHINY_AVAILABLE:
    api_base_url = f"http://127.0.0.1:{settings.server_port}"
    logger.info(f"Configuring Shiny apps with API base URL: {api_base_url}")

    try:
        heatmap_shiny_app = create_heatmap_app(api_base_url=api_base_url, fastapi_app=app)
        _heatmap_asgi = getattr(heatmap_shiny_app, "starlette_app", heatmap_shiny_app)
        app.mount("/shiny/heatmap", _heatmap_asgi, name="shiny_heatmap")
        logger.info("PyShiny heatmap mounted at /shiny/heatmap (ASGI: starlette_app)")
    except Exception as e:
        logger.exception("Failed to mount PyShiny heatmap app")

    try:
        silhouette_shiny_app = create_silhouette_app(api_base_url=api_base_url, fastapi_app=app)
        _silhouette_asgi = getattr(silhouette_shiny_app, "starlette_app", silhouette_shiny_app)
        app.mount("/shiny/silhouette", _silhouette_asgi, name="shiny_silhouette")
        logger.info("PyShiny silhouette mounted at /shiny/silhouette (ASGI: starlette_app)")
    except Exception as e:
        logger.exception("Failed to mount PyShiny silhouette app")
else:
    logger.warning("PyShiny is not available - silhouette and heatmap will return 404")

# ... rest of existing code ...

# Set up templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path)) if templates_path.exists() else None

# Include API routes
app.include_router(api_router, prefix="/api", tags=["api"])


# HTML page routes
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request):
    """Render the landing page."""
    return templates.TemplateResponse("landing.html", {"request": request, "settings": settings})


@app.get("/input", response_class=HTMLResponse, include_in_schema=False)
async def input_page(request: Request):
    """Render the input page for splicing prediction."""
    return templates.TemplateResponse("input.html", {"request": request, "settings": settings})


@app.get("/result/{job_id}", response_class=HTMLResponse, include_in_schema=False)
async def result_page(request: Request, job_id: str):
    """Render the result page for a job. Uses batch_result.html for batch jobs."""
    # Check if job is a batch job
    db = next(get_db())
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        is_batch = job.is_batch if job else False
    finally:
        db.close()

    template_name = "batch_result.html" if is_batch else "result.html"
    return templates.TemplateResponse(
        template_name,
        {"request": request, "job_id": job_id, "settings": settings}
    )


@app.get("/batch/{job_id}/sequence/{index}", response_class=HTMLResponse, include_in_schema=False)
async def batch_sequence_detail_page(request: Request, job_id: str, index: int):
    """Render the result page for a single sequence from a batch job."""
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "job_id": job_id,
            "batch_index": index,
            "settings": settings,
        }
    )


@app.get("/help", response_class=HTMLResponse, include_in_schema=False)
async def help_page(request: Request):
    """Render the help page."""
    return templates.TemplateResponse("help.html", {"request": request, "settings": settings})


@app.get("/tutorial", include_in_schema=False)
async def tutorial_page():
    """Redirect to help page tutorials section."""
    return RedirectResponse(url="/help#tutorial", status_code=301)


@app.get("/methodology", response_class=HTMLResponse, include_in_schema=False)
async def methodology_page(request: Request):
    """Render the methodology page."""
    return templates.TemplateResponse("methodology.html", {"request": request, "settings": settings})


@app.get("/history", response_class=HTMLResponse, include_in_schema=False)
async def history_page(request: Request):
    """Render the job history page."""
    return templates.TemplateResponse("history.html", {"request": request, "settings": settings})


@app.get("/mutagenesis", response_class=HTMLResponse, include_in_schema=False)
async def mutagenesis_page(request: Request):
    """Render the mutagenesis input page."""
    return templates.TemplateResponse("mutagenesis.html", {"request": request, "settings": settings})


@app.get("/mutagenesis/{job_id}", response_class=HTMLResponse, include_in_schema=False)
async def mutagenesis_result_page(request: Request, job_id: str):
    """Render the mutagenesis result page."""
    return templates.TemplateResponse(
        "mutagenesis_result.html",
        {"request": request, "job_id": job_id, "settings": settings}
    )


@app.get("/comparative-analysis", response_class=HTMLResponse, include_in_schema=False)
async def comparative_analysis_page(request: Request):
    """Render the comparative analysis page."""
    return templates.TemplateResponse("comparative_analysis.html", {"request": request, "settings": settings})


@app.get("/publications", response_class=HTMLResponse, include_in_schema=False)
async def publications_page(request: Request):
    """Render the publications page."""
    return templates.TemplateResponse("publications.html", {"request": request, "settings": settings})


@app.get("/download", response_class=HTMLResponse, include_in_schema=False)
async def download_page(request: Request):
    """Render the download page."""
    return templates.TemplateResponse("download.html", {"request": request, "settings": settings})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.server_port)
