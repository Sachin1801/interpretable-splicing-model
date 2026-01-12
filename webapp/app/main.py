"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from webapp.app.config import settings
from webapp.app.database import init_db
from webapp.app.api.routes import router as api_router

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

# Set up templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path)) if templates_path.exists() else None

# Include API routes
app.include_router(api_router, prefix="/api", tags=["api"])


# HTML page routes
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse("index.html", {"request": request, "settings": settings})


@app.get("/result/{job_id}", response_class=HTMLResponse, include_in_schema=False)
async def result_page(request: Request, job_id: str):
    """Render the result page for a job."""
    return templates.TemplateResponse(
        "result.html",
        {"request": request, "job_id": job_id, "settings": settings}
    )


@app.get("/about", response_class=HTMLResponse, include_in_schema=False)
async def about_page(request: Request):
    """Render the about page."""
    return templates.TemplateResponse("about.html", {"request": request, "settings": settings})


@app.get("/help", response_class=HTMLResponse, include_in_schema=False)
async def help_page(request: Request):
    """Render the help page."""
    return templates.TemplateResponse("help.html", {"request": request, "settings": settings})


@app.get("/tutorial", response_class=HTMLResponse, include_in_schema=False)
async def tutorial_page(request: Request):
    """Render the tutorial page."""
    return templates.TemplateResponse("tutorial.html", {"request": request, "settings": settings})


@app.get("/methodology", response_class=HTMLResponse, include_in_schema=False)
async def methodology_page(request: Request):
    """Render the methodology page."""
    return templates.TemplateResponse("methodology.html", {"request": request, "settings": settings})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
