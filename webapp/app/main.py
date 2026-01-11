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
    if templates:
        return templates.TemplateResponse("index.html", {"request": request, "settings": settings})

    # Fallback HTML if templates not set up yet
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{settings.app_name}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 2rem;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #2c3e50; }}
            .info {{ color: #666; margin-bottom: 2rem; }}
            textarea {{
                width: 100%;
                height: 100px;
                font-family: monospace;
                padding: 1rem;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-bottom: 1rem;
            }}
            button {{
                background: #3498db;
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 4px;
                cursor: pointer;
                margin-right: 0.5rem;
            }}
            button:hover {{ background: #2980b9; }}
            button.secondary {{ background: #95a5a6; }}
            button.secondary:hover {{ background: #7f8c8d; }}
            .result {{
                margin-top: 2rem;
                padding: 1rem;
                background: #ecf0f1;
                border-radius: 4px;
            }}
            .footer {{
                margin-top: 2rem;
                text-align: center;
                color: #666;
                font-size: 0.9rem;
            }}
            .free-access {{
                background: #d5edda;
                padding: 0.5rem 1rem;
                border-radius: 4px;
                margin-bottom: 1rem;
            }}
            #char-count {{ color: #666; font-size: 0.9rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{settings.app_name}</h1>
            <p class="free-access">
                <strong>This website is free and open to all users and there is no login requirement.</strong>
            </p>
            <p class="info">
                Predict RNA alternative splicing outcomes (PSI - Percent Spliced In)
                for 70-nucleotide exon sequences.
            </p>

            <form id="predict-form">
                <label for="sequence"><strong>Exon Sequence (70 nucleotides, A/C/G/T only):</strong></label>
                <textarea id="sequence" name="sequence"
                    placeholder="Enter your 70-nucleotide sequence here..."
                    maxlength="70"></textarea>
                <div id="char-count">0/70 nucleotides</div>

                <button type="submit">Predict PSI</button>
                <button type="button" class="secondary" id="example-btn">Try Example</button>
                <button type="button" class="secondary" id="clear-btn">Clear</button>
            </form>

            <div id="result" class="result" style="display: none;">
                <h3>Prediction Result</h3>
                <div id="result-content"></div>
            </div>

            <div class="footer">
                <p>
                    <a href="/docs">API Documentation</a> |
                    <a href="/help">Help</a> |
                    <a href="/tutorial">Tutorial</a>
                </p>
                <p>
                    Citation: Liao SE, Sudarshan M, and Regev O.
                    "Machine learning for discovery: deciphering RNA splicing logic." bioRxiv (2022).
                </p>
            </div>
        </div>

        <script>
            const textarea = document.getElementById('sequence');
            const charCount = document.getElementById('char-count');
            const resultDiv = document.getElementById('result');
            const resultContent = document.getElementById('result-content');

            textarea.addEventListener('input', function() {{
                charCount.textContent = this.value.length + '/70 nucleotides';
            }});

            document.getElementById('example-btn').addEventListener('click', async function() {{
                const response = await fetch('/api/example');
                const data = await response.json();
                textarea.value = data.sequences[0].sequence;
                charCount.textContent = '70/70 nucleotides';
            }});

            document.getElementById('clear-btn').addEventListener('click', function() {{
                textarea.value = '';
                charCount.textContent = '0/70 nucleotides';
                resultDiv.style.display = 'none';
            }});

            document.getElementById('predict-form').addEventListener('submit', async function(e) {{
                e.preventDefault();
                const sequence = textarea.value.toUpperCase().replace(/U/g, 'T');

                if (sequence.length !== 70) {{
                    alert('Sequence must be exactly 70 nucleotides');
                    return;
                }}

                resultContent.innerHTML = '<p>Processing...</p>';
                resultDiv.style.display = 'block';

                try {{
                    const response = await fetch('/api/predict', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{sequence: sequence}})
                    }});

                    if (!response.ok) {{
                        const error = await response.json();
                        throw new Error(error.detail || 'Prediction failed');
                    }}

                    const data = await response.json();

                    // Redirect to result page
                    window.location.href = data.result_url;

                }} catch (error) {{
                    resultContent.innerHTML = '<p style="color: red;">Error: ' + error.message + '</p>';
                }}
            }});
        </script>
    </body>
    </html>
    """)


@app.get("/result/{job_id}", response_class=HTMLResponse, include_in_schema=False)
async def result_page(request: Request, job_id: str):
    """Render the result page for a job."""
    if templates:
        return templates.TemplateResponse(
            "result.html",
            {"request": request, "job_id": job_id, "settings": settings}
        )

    # Fallback HTML
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Result - {settings.app_name}</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1000px;
                margin: 0 auto;
                padding: 2rem;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #2c3e50; }}
            .psi-display {{
                font-size: 3rem;
                font-weight: bold;
                text-align: center;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
            }}
            .high {{ background: #d5edda; color: #155724; }}
            .medium {{ background: #fff3cd; color: #856404; }}
            .low {{ background: #f8d7da; color: #721c24; }}
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
                margin: 1rem 0;
            }}
            .info-box {{
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 4px;
            }}
            .sequence {{
                font-family: monospace;
                word-break: break-all;
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 4px;
            }}
            #force-plot {{
                width: 100%;
                height: 400px;
            }}
            .actions {{
                margin-top: 2rem;
            }}
            button, a.button {{
                display: inline-block;
                background: #3498db;
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
                margin-right: 0.5rem;
            }}
            button:hover, a.button:hover {{ background: #2980b9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Prediction Result</h1>
            <p><strong>Job ID:</strong> <code>{job_id}</code></p>

            <div id="loading">Loading results...</div>
            <div id="results" style="display: none;">
                <div id="psi-display" class="psi-display"></div>
                <p id="interpretation" style="text-align: center;"></p>

                <div class="info-grid">
                    <div class="info-box">
                        <strong>Structure:</strong>
                        <pre id="structure" style="font-family: monospace; word-break: break-all;"></pre>
                    </div>
                    <div class="info-box">
                        <strong>Minimum Free Energy:</strong>
                        <span id="mfe"></span> kcal/mol
                    </div>
                </div>

                <h3>Input Sequence</h3>
                <div id="sequence" class="sequence"></div>

                <h3>Force Plot</h3>
                <div id="force-plot"></div>

                <div class="actions">
                    <a href="/" class="button">New Prediction</a>
                    <a href="/api/export/{job_id}/csv" class="button">Download CSV</a>
                    <a href="/api/export/{job_id}/json" class="button">Download JSON</a>
                </div>
            </div>

            <div id="error" style="display: none; color: red;"></div>
        </div>

        <script>
            async function loadResults() {{
                try {{
                    const response = await fetch('/api/result/{job_id}');
                    const data = await response.json();

                    if (data.status !== 'finished') {{
                        document.getElementById('loading').textContent =
                            'Job status: ' + data.status + (data.message ? ' - ' + data.message : '');
                        if (data.status === 'queued' || data.status === 'running') {{
                            setTimeout(loadResults, 1000);
                        }}
                        return;
                    }}

                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('results').style.display = 'block';

                    // Display PSI
                    const psi = data.psi;
                    const psiDisplay = document.getElementById('psi-display');
                    psiDisplay.textContent = 'PSI: ' + psi.toFixed(3);
                    if (psi >= 0.6) psiDisplay.className = 'psi-display high';
                    else if (psi >= 0.4) psiDisplay.className = 'psi-display medium';
                    else psiDisplay.className = 'psi-display low';

                    document.getElementById('interpretation').textContent = data.interpretation;
                    document.getElementById('sequence').textContent = data.sequence;
                    document.getElementById('structure').textContent = data.structure || 'N/A';
                    document.getElementById('mfe').textContent = data.mfe ? data.mfe.toFixed(2) : 'N/A';

                    // Create force plot if data available
                    if (data.force_plot_data && data.force_plot_data.activations) {{
                        createForcePlot(data.force_plot_data);
                    }}

                }} catch (error) {{
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').style.display = 'block';
                    document.getElementById('error').textContent = 'Error loading results: ' + error.message;
                }}
            }}

            function createForcePlot(data) {{
                const positions = data.positions;
                const activations = data.activations;

                if (!activations.qc_incl || !activations.qc_skip) return;

                // Sum across filters for inclusion and skipping
                const inclSum = activations.qc_incl.map(pos =>
                    pos.reduce((a, b) => a + Math.max(0, b), 0));
                const skipSum = activations.qc_skip.map(pos =>
                    pos.reduce((a, b) => a + Math.max(0, b), 0));

                // Net contribution
                const netContrib = inclSum.map((v, i) => v - skipSum[i]);

                const trace = {{
                    x: positions.slice(0, netContrib.length),
                    y: netContrib,
                    type: 'bar',
                    marker: {{
                        color: netContrib.map(v => v >= 0 ? '#27ae60' : '#e74c3c')
                    }}
                }};

                const layout = {{
                    title: 'Position-wise Contribution to PSI',
                    xaxis: {{ title: 'Position' }},
                    yaxis: {{ title: 'Net Contribution (Inclusion - Skipping)' }},
                    bargap: 0.1
                }};

                Plotly.newPlot('force-plot', [trace], layout);
            }}

            loadResults();
        </script>
    </body>
    </html>
    """)


@app.get("/help", response_class=HTMLResponse, include_in_schema=False)
async def help_page(request: Request):
    """Render the help page."""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Help - {settings.app_name}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 2rem;
                line-height: 1.6;
            }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; margin-top: 2rem; }}
            code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; }}
            .nav {{ margin-bottom: 2rem; }}
            .nav a {{ margin-right: 1rem; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/">Home</a>
            <a href="/help">Help</a>
            <a href="/tutorial">Tutorial</a>
            <a href="/methodology">Methodology</a>
            <a href="/docs">API Docs</a>
        </div>

        <h1>Help</h1>

        <h2>Input Requirements</h2>
        <ul>
            <li><strong>Sequence length:</strong> Exactly 70 nucleotides</li>
            <li><strong>Valid characters:</strong> A, C, G, T (case-insensitive)</li>
            <li><strong>U to T conversion:</strong> RNA sequences with U are automatically converted to T</li>
        </ul>

        <h2>Understanding PSI Values</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #f4f4f4;">
                <th style="padding: 0.5rem; text-align: left;">PSI Range</th>
                <th style="padding: 0.5rem; text-align: left;">Interpretation</th>
            </tr>
            <tr><td style="padding: 0.5rem;">0.8 - 1.0</td><td style="padding: 0.5rem;">Strong exon inclusion</td></tr>
            <tr><td style="padding: 0.5rem;">0.6 - 0.8</td><td style="padding: 0.5rem;">Moderate inclusion tendency</td></tr>
            <tr><td style="padding: 0.5rem;">0.4 - 0.6</td><td style="padding: 0.5rem;">Balanced inclusion/skipping</td></tr>
            <tr><td style="padding: 0.5rem;">0.2 - 0.4</td><td style="padding: 0.5rem;">Moderate skipping tendency</td></tr>
            <tr><td style="padding: 0.5rem;">0.0 - 0.2</td><td style="padding: 0.5rem;">Strong exon skipping</td></tr>
        </table>

        <h2>Force Plot Interpretation</h2>
        <p>
            The force plot shows the contribution of each nucleotide position to the final PSI prediction:
        </p>
        <ul>
            <li><strong>Green bars:</strong> Promote exon inclusion</li>
            <li><strong>Red bars:</strong> Promote exon skipping</li>
            <li><strong>Height:</strong> Magnitude of the contribution</li>
        </ul>

        <h2>Batch Processing</h2>
        <p>
            You can submit up to 100 sequences at once using:
        </p>
        <ul>
            <li><strong>Text input:</strong> Paste multiple sequences, one per line</li>
            <li><strong>File upload:</strong> Upload a CSV or FASTA file</li>
        </ul>

        <h2>API Usage</h2>
        <p>
            See the <a href="/docs">API Documentation</a> for programmatic access.
        </p>

        <h2>Citation</h2>
        <p>
            If you use this tool in your research, please cite:
        </p>
        <blockquote>
            Liao SE, Sudarshan M, and Regev O. "Machine learning for discovery:
            deciphering RNA splicing logic." bioRxiv (2022).
        </blockquote>
    </body>
    </html>
    """)


@app.get("/tutorial", response_class=HTMLResponse, include_in_schema=False)
async def tutorial_page(request: Request):
    """Render the tutorial page."""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tutorial - {settings.app_name}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 2rem;
                line-height: 1.6;
            }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; margin-top: 2rem; }}
            .step {{
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
                border-left: 4px solid #3498db;
            }}
            .step-number {{
                display: inline-block;
                width: 30px;
                height: 30px;
                background: #3498db;
                color: white;
                border-radius: 50%;
                text-align: center;
                line-height: 30px;
                margin-right: 0.5rem;
            }}
            code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; }}
            .nav {{ margin-bottom: 2rem; }}
            .nav a {{ margin-right: 1rem; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/">Home</a>
            <a href="/help">Help</a>
            <a href="/tutorial">Tutorial</a>
            <a href="/methodology">Methodology</a>
            <a href="/docs">API Docs</a>
        </div>

        <h1>Tutorial</h1>

        <h2>Quick Start</h2>

        <div class="step">
            <span class="step-number">1</span>
            <strong>Try an Example</strong>
            <p>Click the "Try Example" button on the home page to load a sample sequence.</p>
        </div>

        <div class="step">
            <span class="step-number">2</span>
            <strong>Enter Your Sequence</strong>
            <p>Paste or type your 70-nucleotide exon sequence in the input box.</p>
        </div>

        <div class="step">
            <span class="step-number">3</span>
            <strong>Run Prediction</strong>
            <p>Click "Predict PSI" to submit your sequence for analysis.</p>
        </div>

        <div class="step">
            <span class="step-number">4</span>
            <strong>View Results</strong>
            <p>See the predicted PSI value and force plot visualization.</p>
        </div>

        <div class="step">
            <span class="step-number">5</span>
            <strong>Export Results</strong>
            <p>Download your results in CSV or JSON format.</p>
        </div>

        <h2>Example Walkthrough</h2>
        <p>
            <a href="/result/example-high">View example with high PSI (strong inclusion)</a><br>
            <a href="/result/example-balanced">View example with balanced PSI</a><br>
            <a href="/result/example-low">View example with low PSI (strong skipping)</a>
        </p>

        <h2>Using the API</h2>
        <p>For programmatic access, use the REST API:</p>
        <pre style="background: #f4f4f4; padding: 1rem; border-radius: 4px; overflow-x: auto;">
curl -X POST "https://your-domain.com/api/predict" \\
  -H "Content-Type: application/json" \\
  -d '{{"sequence": "ACGTACGT...70nt..."}}'
        </pre>

        <p>See the <a href="/docs">API Documentation</a> for more details.</p>
    </body>
    </html>
    """)


@app.get("/methodology", response_class=HTMLResponse, include_in_schema=False)
async def methodology_page(request: Request):
    """Render the methodology page."""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Methodology - {settings.app_name}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 2rem;
                line-height: 1.6;
            }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; margin-top: 2rem; }}
            .nav {{ margin-bottom: 2rem; }}
            .nav a {{ margin-right: 1rem; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 1rem 0;
            }}
            th, td {{
                padding: 0.5rem;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{ background: #f4f4f4; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/">Home</a>
            <a href="/help">Help</a>
            <a href="/tutorial">Tutorial</a>
            <a href="/methodology">Methodology</a>
            <a href="/docs">API Docs</a>
        </div>

        <h1>Methodology</h1>

        <h2>Model Overview</h2>
        <p>
            This web server uses an interpretable deep neural network to predict
            RNA alternative splicing outcomes. The model predicts the PSI
            (Percent Spliced In) value, which represents the fraction of
            transcripts that include a particular exon.
        </p>

        <h2>Input Features</h2>
        <p>The model uses three types of input features for each 90-nucleotide sequence:</p>
        <table>
            <tr>
                <th>Feature</th>
                <th>Dimensions</th>
                <th>Description</th>
            </tr>
            <tr>
                <td>Sequence</td>
                <td>90 x 4</td>
                <td>One-hot encoding of nucleotides (A, C, G, T)</td>
            </tr>
            <tr>
                <td>Structure</td>
                <td>90 x 3</td>
                <td>One-hot encoding of RNA secondary structure (., (, ))</td>
            </tr>
            <tr>
                <td>Wobble</td>
                <td>90 x 1</td>
                <td>Indicator for G-U wobble base pairs</td>
            </tr>
        </table>

        <h2>Model Architecture</h2>
        <p>The model consists of:</p>
        <ul>
            <li><strong>Sequence Branch:</strong> 1D convolution (20 filters, width 6) with position-specific biases</li>
            <li><strong>Structure Branch:</strong> 1D convolution (8 filters, width 30) on combined features</li>
            <li><strong>Energy Computation:</strong> Sum of ReLU activations for inclusion vs skipping</li>
            <li><strong>Residual Tuner:</strong> Fine-tuning MLP with residual connection</li>
            <li><strong>Output:</strong> Sigmoid activation producing PSI (0-1)</li>
        </ul>

        <h2>Interpretability</h2>
        <p>The model is designed to be interpretable through:</p>
        <ul>
            <li>Position-specific biases revealing important regions</li>
            <li>Separate inclusion/skipping branches showing competing forces</li>
            <li>Smoothness regularization ensuring gradual position effects</li>
            <li>Force plots visualizing per-position contributions</li>
        </ul>

        <h2>Training Data</h2>
        <p>
            The model was trained on approximately 150,000 synthetic 70-nucleotide
            exon sequences from HeLa cells across three libraries (ES7_HeLa_A, B, C).
        </p>

        <h2>Performance</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr><td>Test R²</td><td>~0.85</td></tr>
            <tr><td>Test RMSE</td><td>~0.12</td></tr>
            <tr><td>Binary KL Loss</td><td>~0.015-0.020</td></tr>
        </table>

        <h2>Citation</h2>
        <p>
            Liao SE, Sudarshan M, and Regev O. "Machine learning for discovery:
            deciphering RNA splicing logic." bioRxiv (2022).
            <a href="https://www.biorxiv.org/content/10.1101/2022.10.01.510472v1">Link</a>
        </p>
    </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
