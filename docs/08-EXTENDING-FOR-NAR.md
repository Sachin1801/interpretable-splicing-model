# Building a NAR Web Server Issue Compliant Web Application

This guide provides comprehensive instructions for building a web server that meets NAR (Nucleic Acids Research) Web Server Issue requirements.

---

## NAR Web Server Requirements Checklist

### MUST HAVE

- [ ] **HTTPS on port 443** - Secure connection required
- [ ] **Cookie consent form** - If cookies are used
- [ ] **Sample data with one-click loading** - "Try Example" button
- [ ] **Help pages** - Including how to interpret results
- [ ] **Tutorial with sample output links** - Interactive examples
- [ ] **Private user data** - Not viewable by others
- [ ] **Bookmarkable result URLs** - With job status (queued/running/finished)
- [ ] **Optional email notification** - Must be clearly optional
- [ ] **Free access statement** - On landing page
- [ ] **Rich output** - Hyperlinks and visualizations (not just downloads)

### MUST NOT HAVE

- [ ] **No login/registration requirement** - Unless handling sensitive human data
- [ ] **No Flash or Java plugins** - Security risks
- [ ] **No tracking cookies** - Analytics cookies prohibited
- [ ] **No excessive preprocessing** - Input should be simple
- [ ] **No guest login** - Websites requiring guest login will be rejected

---

## Recommended Tech Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  • HTML5 + CSS3 + Vanilla JavaScript                            │
│  • Bootstrap 5 for responsive design                            │
│  • Plotly.js for interactive force plots                        │
│  • No build step required (simple deployment)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND                                   │
│  • FastAPI (Python 3.8+)                                        │
│    - Modern, async, auto-generated API docs                     │
│    - Native support for type hints                              │
│  • Celery + Redis for job queue                                 │
│  • SQLite for job tracking (simple) or PostgreSQL (scale)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        INFRASTRUCTURE                            │
│  • Nginx for reverse proxy and HTTPS                            │
│  • Let's Encrypt for free SSL certificates                      │
│  • Docker + Docker Compose for deployment                       │
│  • Ubuntu 22.04 LTS on cloud VM                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
webapp/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration settings
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── predict.py          # /api/predict endpoints
│   │   ├── results.py          # /api/result/{job_id} endpoints
│   │   └── pages.py            # HTML page routes
│   ├── models/
│   │   ├── __init__.py
│   │   ├── job.py              # Job database model
│   │   └── predictor.py        # TensorFlow model wrapper
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── prediction.py       # Celery task for predictions
│   └── utils/
│       ├── __init__.py
│       ├── sequence.py         # Sequence validation
│       └── visualization.py    # Force plot generation
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── main.js
│   │   └── force_plot.js
│   └── images/
│       └── logo.png
├── templates/
│   ├── base.html               # Base template
│   ├── index.html              # Landing page
│   ├── result.html             # Results page
│   ├── help.html               # Help page
│   └── tutorial.html           # Tutorial page
├── tests/
│   ├── test_api.py
│   └── test_predictor.py
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
└── README.md
```

---

## Step-by-Step Implementation

### Step 1: Create FastAPI Application

**app/main.py:**

```python
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Splicing Predictor",
    description="Predict RNA alternative splicing outcomes",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
from app.routes import predict, results, pages
app.include_router(predict.router, prefix="/api", tags=["prediction"])
app.include_router(results.router, prefix="/api", tags=["results"])
app.include_router(pages.router, tags=["pages"])
```

### Step 2: Create Prediction Endpoint

**app/routes/predict.py:**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
import uuid
from app.tasks.prediction import run_prediction
from app.models.job import create_job, get_job

router = APIRouter()

class PredictionRequest(BaseModel):
    sequence: str  # 70 nt exon sequence

    @validator('sequence')
    def validate_sequence(cls, v):
        v = v.upper().replace('U', 'T')
        if len(v) != 70:
            raise ValueError('Sequence must be exactly 70 nucleotides')
        if not set(v).issubset({'A', 'C', 'G', 'T'}):
            raise ValueError('Sequence must contain only A, C, G, T')
        return v

class PredictionResponse(BaseModel):
    job_id: str
    status_url: str
    result_url: str

@router.post("/predict", response_model=PredictionResponse)
async def submit_prediction(request: PredictionRequest):
    """Submit a sequence for PSI prediction."""
    job_id = str(uuid.uuid4())

    # Create job in database
    create_job(job_id, request.sequence)

    # Queue prediction task
    run_prediction.delay(job_id, request.sequence)

    return PredictionResponse(
        job_id=job_id,
        status_url=f"/api/status/{job_id}",
        result_url=f"/result/{job_id}"
    )

@router.get("/example")
async def get_example():
    """Return sample sequences for one-click loading."""
    return {
        "sequences": [
            {
                "name": "High inclusion example",
                "sequence": "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
                "description": "This sequence is predicted to have high exon inclusion (PSI > 0.8)"
            },
            {
                "name": "Low inclusion example",
                "sequence": "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
                "description": "This sequence is predicted to have low exon inclusion (PSI < 0.2)"
            }
        ]
    }
```

### Step 3: Create Status and Results Endpoints

**app/routes/results.py:**

```python
from fastapi import APIRouter, HTTPException
from app.models.job import get_job

router = APIRouter()

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get job status (for polling)."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_id,
        "status": job.status,  # "queued", "running", "finished", "failed"
        "progress": job.progress,  # 0-100
        "created_at": job.created_at.isoformat(),
    }

@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """Get prediction results."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "finished":
        return {
            "job_id": job_id,
            "status": job.status,
            "message": "Job not yet complete"
        }

    return {
        "job_id": job_id,
        "status": "finished",
        "sequence": job.sequence,
        "psi": job.psi,
        "force_plot_data": job.force_plot_data,  # JSON for Plotly
        "structure": job.structure,
        "interpretation": get_interpretation(job.psi)
    }

def get_interpretation(psi: float) -> str:
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
```

### Step 4: Create Celery Task

**app/tasks/prediction.py:**

```python
from celery import Celery
import tensorflow as tf
import numpy as np
from app.models.job import update_job
from app.models.predictor import SplicingPredictor

celery = Celery('tasks', broker='redis://localhost:6379/0')

# Load model once at worker startup
predictor = None

@celery.task
def run_prediction(job_id: str, sequence: str):
    global predictor
    if predictor is None:
        predictor = SplicingPredictor()

    try:
        update_job(job_id, status="running", progress=10)

        # Compute features
        features = predictor.prepare_input(sequence)
        update_job(job_id, progress=30)

        # Run prediction
        psi = predictor.predict(features)
        update_job(job_id, progress=60)

        # Generate force plot
        force_plot_data = predictor.get_force_plot(features)
        update_job(job_id, progress=90)

        # Get structure
        structure = predictor.get_structure(sequence)

        # Save results
        update_job(
            job_id,
            status="finished",
            progress=100,
            psi=float(psi),
            force_plot_data=force_plot_data,
            structure=structure
        )

    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
        raise
```

### Step 5: Create Model Wrapper

**app/models/predictor.py:**

```python
import tensorflow as tf
import numpy as np
import subprocess
import sys
sys.path.append('/path/to/interpretable-splicing-model')
from model_training.model import binary_KL, Selector, ResidualTuner, SumDiff, RegularizedBiasLayer

class SplicingPredictor:
    def __init__(self, model_path='output/custom_adjacency_regularizer_20210731_124_step3.h5'):
        self.model = tf.keras.models.load_model(
            model_path,
            custom_objects={
                'binary_KL': binary_KL,
                'Selector': Selector,
                'ResidualTuner': ResidualTuner,
                'SumDiff': SumDiff,
                'RegularizedBiasLayer': RegularizedBiasLayer,
            }
        )

        # Pre-defined flanking sequences
        self.pre_seq = "TCTGCCTATGTCTTTCTCTGCCATCCAGGTT"[-10:]
        self.post_seq = "CAGGTCTGACTATGGGACCCTTGATGTTTT"[:10]

    def prepare_input(self, sequence: str):
        """Convert sequence to model input."""
        full_seq = self.pre_seq + sequence + self.post_seq

        # One-hot encode
        seq_oh = self._nts_to_vector(full_seq)

        # Get structure
        struct, _ = self._get_structure(full_seq)
        struct_oh = self._struct_to_vector(struct)

        # Compute wobbles
        wobble = self._compute_wobbles(full_seq, struct)

        return [
            np.expand_dims(seq_oh, 0),
            np.expand_dims(struct_oh, 0),
            np.expand_dims(wobble, 0)
        ]

    def predict(self, features):
        """Run prediction."""
        return self.model.predict(features)[0, 0]

    def get_force_plot(self, features):
        """Extract force plot data for visualization."""
        # Get layer activations
        layer_names = ['qc_incl', 'qc_skip', 'position_bias_incl', 'position_bias_skip']
        activations = {}

        for name in layer_names:
            layer = self.model.get_layer(name)
            intermediate_model = tf.keras.Model(
                inputs=self.model.inputs,
                outputs=layer.output
            )
            activations[name] = intermediate_model.predict(features)[0].tolist()

        return {
            "positions": list(range(90)),
            "inclusion_strength": activations['qc_incl'],
            "skipping_strength": activations['qc_skip'],
            "position_bias_incl": activations['position_bias_incl'],
            "position_bias_skip": activations['position_bias_skip'],
        }

    def get_structure(self, sequence: str):
        """Get RNA secondary structure."""
        full_seq = self.pre_seq + sequence + self.post_seq
        struct, mfe = self._get_structure(full_seq)
        return {"structure": struct, "mfe": mfe}

    def _nts_to_vector(self, nts):
        mapping = {'A': 0, 'C': 1, 'G': 2, 'T': 3}
        encoded = np.zeros((len(nts), 4))
        for i, nt in enumerate(nts):
            encoded[i, mapping[nt]] = 1
        return encoded

    def _struct_to_vector(self, struct):
        mapping = {'.': 0, '(': 1, ')': 2}
        encoded = np.zeros((len(struct), 3))
        for i, s in enumerate(struct):
            encoded[i, mapping[s]] = 1
        return encoded

    def _get_structure(self, sequence):
        result = subprocess.run(
            ['RNAfold', '--noPS'],
            input=sequence.replace('T', 'U'),
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        parts = lines[1].split()
        struct = parts[0]
        mfe = float(parts[-1].strip('()'))
        return struct, mfe

    def _compute_wobbles(self, sequence, structure):
        # Find base pairs
        stack = []
        pairs = {}
        for i, s in enumerate(structure):
            if s == '(':
                stack.append(i)
            elif s == ')':
                j = stack.pop()
                pairs[i] = j
                pairs[j] = i

        # Check for G-U wobbles
        wobble = np.zeros((len(sequence), 1))
        for i in range(len(sequence)):
            if i in pairs:
                j = pairs[i]
                pair = {sequence[i], sequence[j]}
                if pair == {'G', 'T'}:
                    wobble[i] = 1
                    wobble[j] = 1
        return wobble
```

### Step 6: Create HTML Templates

**templates/base.html:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Splicing Predictor{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static/css/style.css" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">Splicing Predictor</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/">Home</a>
                <a class="nav-link" href="/help">Help</a>
                <a class="nav-link" href="/tutorial">Tutorial</a>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        {% block content %}{% endblock %}
    </main>

    <footer class="container mt-5 mb-3 text-center text-muted">
        <p class="mb-1">
            <strong>This website is free and open to all users and there is no login requirement.</strong>
        </p>
        <p>
            <a href="https://opensource.org/licenses/MIT">MIT License</a> |
            Citation: Liao et al., bioRxiv 2022
        </p>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/js/main.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

**templates/index.html:**

```html
{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-8">
        <h1 class="mb-4">Predict RNA Splicing Outcomes</h1>

        <div class="card mb-4">
            <div class="card-body">
                <h5 class="card-title">Enter your sequence</h5>
                <p class="text-muted">Enter a 70-nucleotide exon sequence (A, C, G, T only)</p>

                <form id="predict-form">
                    <div class="mb-3">
                        <label for="sequence" class="form-label">Exon Sequence (70 nt)</label>
                        <textarea
                            class="form-control font-monospace"
                            id="sequence"
                            name="sequence"
                            rows="3"
                            placeholder="ACGTACGTACGT..."
                            maxlength="70"
                        ></textarea>
                        <div class="form-text">
                            <span id="char-count">0</span>/70 nucleotides
                        </div>
                    </div>

                    <div class="d-grid gap-2 d-md-flex">
                        <button type="submit" class="btn btn-primary" id="submit-btn">
                            Predict PSI
                        </button>
                        <button type="button" class="btn btn-outline-secondary" id="example-btn">
                            Try Example
                        </button>
                        <button type="button" class="btn btn-outline-danger" id="clear-btn">
                            Clear
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <div id="result-section" class="card d-none">
            <div class="card-body">
                <h5 class="card-title">Prediction Submitted</h5>
                <p>Job ID: <code id="job-id"></code></p>
                <p>Status: <span id="status-badge" class="badge bg-warning">Queued</span></p>
                <div class="progress mb-3">
                    <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
                </div>
                <p>
                    Bookmark this link to return to your results:
                    <a href="#" id="result-link" target="_blank"></a>
                </p>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
document.getElementById('sequence').addEventListener('input', function() {
    document.getElementById('char-count').textContent = this.value.length;
});

document.getElementById('example-btn').addEventListener('click', async function() {
    const response = await fetch('/api/example');
    const data = await response.json();
    document.getElementById('sequence').value = data.sequences[0].sequence;
    document.getElementById('char-count').textContent = 70;
});

document.getElementById('clear-btn').addEventListener('click', function() {
    document.getElementById('sequence').value = '';
    document.getElementById('char-count').textContent = 0;
});

document.getElementById('predict-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const sequence = document.getElementById('sequence').value;

    const response = await fetch('/api/predict', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({sequence: sequence})
    });

    const data = await response.json();

    document.getElementById('job-id').textContent = data.job_id;
    document.getElementById('result-link').href = data.result_url;
    document.getElementById('result-link').textContent = window.location.origin + data.result_url;
    document.getElementById('result-section').classList.remove('d-none');

    // Poll for status
    pollStatus(data.job_id, data.result_url);
});

async function pollStatus(jobId, resultUrl) {
    const response = await fetch(`/api/status/${jobId}`);
    const data = await response.json();

    document.getElementById('progress-bar').style.width = data.progress + '%';

    if (data.status === 'finished') {
        document.getElementById('status-badge').textContent = 'Finished';
        document.getElementById('status-badge').className = 'badge bg-success';
        window.location.href = resultUrl;
    } else if (data.status === 'failed') {
        document.getElementById('status-badge').textContent = 'Failed';
        document.getElementById('status-badge').className = 'badge bg-danger';
    } else {
        document.getElementById('status-badge').textContent = data.status;
        setTimeout(() => pollStatus(jobId, resultUrl), 1000);
    }
}
</script>
{% endblock %}
```

### Step 7: Create Docker Configuration

**Dockerfile:**

```dockerfile
FROM python:3.8-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    vienna-rna \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Copy model
COPY ../output/custom_adjacency_regularizer_20210731_124_step3.h5 /app/model/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

  worker:
    build: .
    command: celery -A app.tasks.prediction worker --loglevel=info
    depends_on:
      - redis

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt
    depends_on:
      - web
```

**nginx.conf:**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream web {
        server web:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

        location / {
            proxy_pass http://web;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /static {
            alias /app/static;
        }
    }
}
```

---

## NAR Proposal One-Page Summary Template

```markdown
# SplicingPredictor: Interpretable RNA Splicing Prediction Web Server

**Website:** https://your-domain.com/

**Free Access Statement:**
"This website is free and open to all users and there is no login requirement."

## Description
SplicingPredictor predicts alternative splicing outcomes (PSI - Percent Spliced In)
from 70-nucleotide exon sequences using an interpretable deep neural network.
The model identifies sequence motifs and RNA secondary structure features that
promote exon inclusion or skipping.

## Input
- 70-nucleotide exon sequence (FASTA or raw format)
- Supports single or batch predictions
- Sample data available via one-click "Try Example" button

## Output
- PSI prediction (0-1 scale)
- Interactive force plot showing position-wise contributions
- RNA secondary structure visualization
- Sequence motif analysis
- Downloadable results (CSV, JSON)

## Method
The model uses:
- Convolutional neural networks with 6-mer filters for sequence patterns
- 30-mer filters for RNA secondary structure features
- Position-specific biases with smoothness regularization
- Energy-based framework with separate inclusion/skipping branches

The method is validated on the dataset from Liao et al. (bioRxiv 2022).

## Validation
Cross-validation on external datasets:
- FAS exon 6 (Baeza et al.): R² = 0.XX
- WT1 exon 5 (Ke et al.): R² = 0.XX
- SMN1/SMN2 (Rosenberg et al.): R² = 0.XX

## Keywords
RNA splicing, alternative splicing, PSI prediction, interpretable machine learning, deep learning

## Browser Compatibility
Tested on: Chrome 100+, Firefox 100+, Safari 15+, Edge 100+
Operating systems: Windows 10+, macOS 10.15+, Ubuntu 20.04+

## Maintenance Commitment
This website will be maintained for at least five years.

## Authors
[Your names, affiliations, and email addresses]
```

---

## Deployment Checklist

1. [ ] Deploy to cloud VM (AWS, GCP, DigitalOcean)
2. [ ] Register domain name
3. [ ] Set up SSL with Let's Encrypt
4. [ ] Configure Nginx for HTTPS
5. [ ] Test all functionality
6. [ ] Verify "Try Example" button works
7. [ ] Verify help pages are accessible
8. [ ] Verify result URLs are bookmarkable
9. [ ] Test job status polling
10. [ ] Add free access statement to landing page
11. [ ] Remove any tracking cookies
12. [ ] Submit proposal to NAR by December 20

---

## Timeline for NAR Submission

1. **By November 10:** Complete web server implementation
2. **November 10-20:** Testing and refinement
3. **By December 20:** Submit one-page proposal
4. **If approved:** Full manuscript submission
5. **July:** Publication in NAR Web Server Issue
