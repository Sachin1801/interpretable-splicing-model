# Agent Log - Interpretable Splicing Model Web Application

This file tracks all work done by Claude sessions on this project.

---

## Session 1 - 2026-01-10

### Session Start
- **Task**: Plan and implement web application + database for the splicing model
- **Status**: Phase 1 Core Infrastructure COMPLETE

### Work Completed

#### Planning Phase
1. Explored entire codebase structure
2. Read all documentation files (01-10)
3. Understood model architecture:
   - Input: 70nt exon + 10nt flanking each side = 90nt total
   - Features: Sequence (90x4) + Structure (90x3) + Wobble (90x1)
   - Output: PSI value (0-1)
   - Model size: ~10k parameters, ~263KB
4. Reviewed NAR Web Server requirements from doc 08
5. Gathered comprehensive requirements through Q&A session

#### Implementation Phase 1 - Core Infrastructure
1. Created webapp/ directory structure
2. Created requirements.txt with all dependencies
3. Created Makefile for single-command startup
4. Set up SQLite database with SQLAlchemy
5. Created model loading service (predictor.py)
6. Implemented FastAPI application with all API endpoints
7. Created Pydantic schemas for API validation
8. Extracted example sequences from test data
9. Created initial test file

### Decisions Made (User Confirmed)

| Category | Decision |
|----------|----------|
| **Frontend** | PyShiny with shiny.react (Radix UI components) |
| **Backend** | FastAPI |
| **Database** | SQLite |
| **Splicing Types** | 70n only (for now, other lengths later) |
| **Batch Processing** | Both file upload AND text area paste |
| **Job Processing** | Synchronous (blocking) |
| **Data Retention** | 30 days |
| **Email Notifications** | Yes, optional |
| **API Documentation** | Scalar, public access |
| **Theme** | Clean scientific (minimal, professional) |
| **Cookies** | None (URL-based job IDs only) |
| **Session Tracking** | UUID job IDs |
| **Error Handling** | Skip structure on ViennaRNA failure, warn user |
| **Input Validation** | Strict (exactly 70nt A/C/G/T only) |
| **Export Formats** | CSV, JSON, TSV, PDF report |
| **Documentation** | Comprehensive (adapted from existing docs) |
| **Visualizations** | Full suite: Force plot, RNA structure, sequence logo, PSI gauge |
| **Force Plot** | Interactive Plotly |
| **Project Location** | webapp/ folder inside existing repo |
| **Dev Setup** | Single command startup (Makefile) |
| **Timeline** | Feature complete before deployment |

### Files Created

```
webapp/
├── app/
│   ├── __init__.py
│   ├── config.py          # Configuration settings
│   ├── database.py        # SQLite + SQLAlchemy
│   ├── main.py            # FastAPI app with HTML pages
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py      # API endpoints
│   │   └── schemas.py     # Pydantic schemas
│   ├── models/
│   │   ├── __init__.py
│   │   └── job.py         # Job model
│   ├── services/
│   │   ├── __init__.py
│   │   └── predictor.py   # Model wrapper
│   └── ui/
│       ├── __init__.py
│       ├── components/__init__.py
│       └── pages/__init__.py
├── static/
│   ├── css/
│   ├── js/
│   └── examples.json      # Extracted example sequences
├── templates/
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── scripts/
│   └── extract_examples.py
├── Makefile
├── requirements.txt
└── README.md
```

### API Endpoints Implemented

| Method | Endpoint | Status |
|--------|----------|--------|
| GET | `/` | Implemented |
| GET | `/result/{job_id}` | Implemented |
| GET | `/help` | Implemented |
| GET | `/tutorial` | Implemented |
| GET | `/methodology` | Implemented |
| POST | `/api/predict` | Implemented |
| POST | `/api/batch` | Implemented |
| GET | `/api/status/{job_id}` | Implemented |
| GET | `/api/result/{job_id}` | Implemented |
| GET | `/api/example` | Implemented |
| GET | `/api/export/{job_id}/{format}` | Implemented |
| GET | `/api/health` | Implemented |
| GET | `/docs` | Implemented (FastAPI auto-docs) |

### How to Run

```bash
cd webapp
make install   # Install dependencies
make dev       # Run development server
# Open http://localhost:8000
```

### Plan File
See: `/Users/sachin/.claude/plans/tingly-sauteeing-bengio.md`

### Next Steps (Future Sessions)
- [ ] Add PyShiny + shiny.react frontend (Phase 3)
- [ ] Implement proper HTML templates
- [ ] Add email notification service
- [ ] Create PDF export
- [ ] Write comprehensive tests
- [ ] Add Docker configuration
- [ ] Set up deployment scripts

---

## Session 2 - 2026-01-12

### Session Start
- **Task**: Run and test the pre-trained splicing model locally
- **Status**: COMPLETE

### Problem
User could not load the pre-trained model (`custom_adjacency_regularizer_20210731_124_step3.h5`) with their existing Python 3.12 + TensorFlow 2.20 setup.

### Errors Encountered
1. `ValueError: Unknown layer: 'SlicingOpLambda'`
2. `ValueError: Unknown layer: 'Custom>RegularizedBiasLayer'`
3. `IndexError: list index out of range` in Keras functional.py

### Investigation

#### Key Information from User
User provided context from the original model creator:
- Model location: `output/custom_adjacency_regularizer_20210731_124_step3.h5`
- Reference notebook: `figures/generate_csv_for_supplementary.ipynb`
- Additional notebooks: `2022_03_11_figures/` folder (visualization notebooks)

#### What We Discovered
1. **From `figures/generate_csv_for_supplementary.ipynb`**:
   - Simple loading approach: `from quad_model import *` then `load_model()`
   - No manual custom_objects needed

2. **From `2022_03_11_figures/position_specific_activations.ipynb`**:
   - Notebook was run April 2022 with TensorFlow ~2.8
   - Model loads with simple `tf.keras.models.load_model()`

3. **From `figures/quad_model.py`**:
   - All custom layers use `@tf.keras.utils.register_keras_serializable()` decorator
   - This auto-registers layers when module is imported

4. **Root Cause**:
   - TensorFlow 2.16+ uses Keras 3 (breaking changes)
   - Keras 3 cannot load H5 models with Lambda layers from Keras 2
   - `tf_keras` compatibility layer is buggy for complex models

### Solution Implemented

1. **Installed Python 3.10 via pyenv**:
   ```bash
   pyenv install 3.10.13
   ```

2. **Created new virtual environment**:
   ```bash
   ~/.pyenv/versions/3.10.13/bin/python -m venv venv310
   source venv310/bin/activate
   ```

3. **Installed TensorFlow 2.15** (last version with native Keras 2):
   ```bash
   pip install tensorflow==2.15.0 numpy pandas joblib scikit-learn matplotlib seaborn tqdm scipy
   ```

4. **Updated `test_model.py`** to use simple loading approach:
   ```python
   import sys
   sys.path.insert(0, 'figures')
   from quad_model import *  # Auto-registers custom layers
   from tensorflow.keras.models import load_model

   model = load_model('output/...h5')
   ```

5. **Updated `requirements.txt`**:
   - Changed from `tensorflow>=2.15.0` to `tensorflow==2.15.0`
   - Added setup instructions for Python 3.10
   - Removed `tf_keras` (not needed)

### Results
```
Model loaded successfully!
Number of test samples: 47962
MSE: 0.032396
R2 Score: 0.8224
Correlation: 0.9069
```

### Files Modified
- `test_model.py` - Simplified to use quad_model.py approach
- `requirements.txt` - Pinned TensorFlow 2.15, added setup instructions

### Files Created
- `venv310/` - New Python 3.10 virtual environment
- `.claude/skills/tensorflow-keras-model-loading.md` - Skill documentation

### Key Learnings
1. **TF 2.16+ breaks old H5 models** - Must use TF 2.15 or earlier for Keras 2 models
2. **Python 3.12 requires TF 2.16+** - So must downgrade Python to 3.10/3.11
3. **Check original notebooks first** - They show the working approach
4. **`@register_keras_serializable()` is key** - Import the module to register layers
5. **`tf_keras` is unreliable** - For complex models, use native TF 2.15 instead

### Environment Summary
| Environment | Python | TensorFlow | Status |
|-------------|--------|------------|--------|
| `venv` (old) | 3.12 | 2.20 | BROKEN - can delete |
| `venv310` | 3.10.13 | 2.15.0 | WORKING |

---

## Session 3 - 2026-01-12

### Session Start
- **Task**: Fix webapp model loading, fix bugs, create comprehensive TODO, full UI rebuild
- **Status**: COMPLETE

### Work Completed

#### Phase 1: Model Loading Fix in Webapp

**Problem**: The webapp's `predictor.py` used complex `tf_keras` loading approach that was unreliable.

**Solution**: Simplified to use the same approach that works in `test_model.py`:
```python
# webapp/app/services/predictor.py
import sys
sys.path.insert(0, str(settings.project_root / 'figures'))
from quad_model import *  # Auto-registers custom layers
from tensorflow.keras.models import load_model

def _load_model(self):
    self._model = load_model(str(settings.model_path))
```

**Files Modified**:
- `webapp/app/services/predictor.py` - Simplified model loading
- `webapp/requirements.txt` - Pinned TensorFlow 2.15.0

#### Phase 2: Bug Fixes

1. **CSV/JSON Download Not Working**
   - Problem: Export endpoint returned JSON dict instead of file response
   - Fix: Used `fastapi.responses.Response` with `Content-Disposition` header
   - File: `webapp/app/api/routes.py`

2. **Health Check Failing**
   - Problem: SQLAlchemy 2.0 requires `text()` wrapper for raw SQL
   - Fix: Changed `db.execute("SELECT 1")` to `db.execute(text("SELECT 1"))`
   - File: `webapp/app/api/routes.py`

3. **Missing Dependency**
   - Problem: `pydantic_settings` module not found
   - Fix: Installed with `pip install pydantic-settings`

#### Phase 3: Documentation & TODO

Created comprehensive `webapp/TODO.md` (455+ lines) documenting:
- Completed work
- UI/UX improvements needed
- Missing content (About, Methodology pages)
- Feature gaps (batch upload, PDF export)
- Technical debt
- Deployment requirements
- NAR Web Server compliance checklist
- Testing requirements

Created `CLAUDE.md` with project memory:
- No "Co-Authored-By: Claude" in commit messages

#### Phase 4: Full UI Rebuild (Major Work)

Rebuilt entire webapp UI with Jinja2 templates and Tailwind CSS.

**Templates Created** (`webapp/templates/`):

| File | Description | Lines |
|------|-------------|-------|
| `base.html` | Base template with Tailwind, navigation, footer | ~175 |
| `index.html` | Home page with prediction form, examples | ~175 |
| `result.html` | Results page with PSI display, force plot | ~135 |
| `about.html` | **NEW** - Comprehensive model info, limitations, performance | ~300 |
| `methodology.html` | Technical details, architecture diagram, training info | ~320 |
| `help.html` | User guide, PSI interpretation, FAQ with toggle | ~350 |
| `tutorial.html` | Step-by-step guide, API examples | ~250 |

**Static Files Created** (`webapp/static/`):

| File | Description |
|------|-------------|
| `js/app.js` | Form validation, submission, example loading |
| `js/result.js` | Polling for results, Plotly force plot visualization |
| `css/custom.css` | Custom styles, accessibility, print styles |

**main.py Updates**:
- Removed ~700 lines of inline HTML fallbacks
- All routes now use Jinja2 templates
- Added `/about` route
- Added Jinja2 dependency to requirements

**Design Features**:
- Tailwind CSS via CDN (no build step)
- Primary color: Blue (#3b82f6)
- Responsive design (mobile-first)
- Accessible (focus indicators, color contrast)
- Professional scientific aesthetic
- Consistent navigation across all pages
- "Free and open" banner

### Testing Results
- All pages load correctly with Tailwind styling
- Navigation works across all pages
- Prediction API returns correct PSI values
- Result page displays with force plot
- Static files served correctly
- Export CSV/JSON working

### Files Modified This Session
```
webapp/
├── app/
│   ├── main.py              # Simplified to use templates
│   ├── api/routes.py        # Fixed exports & health check
│   └── services/predictor.py # Simplified model loading
├── templates/
│   ├── base.html            # NEW
│   ├── index.html           # NEW
│   ├── result.html          # NEW
│   ├── about.html           # NEW
│   ├── methodology.html     # NEW
│   ├── help.html            # NEW
│   └── tutorial.html        # NEW
├── static/
│   ├── css/custom.css       # NEW
│   └── js/
│       ├── app.js           # NEW
│       └── result.js        # NEW
├── requirements.txt         # Updated (TF 2.15, Jinja2)
└── TODO.md                  # NEW (comprehensive)

CLAUDE.md                    # NEW (project memory)
```

### Git Commit
```
feat(webapp): working local server checkpoint

- Model loading works with TensorFlow 2.15
- Predictions returning correct PSI values
- Export CSV/JSON functional
- Basic HTML interface working
```

### How to Run
```bash
source venv310/bin/activate
python -m uvicorn webapp.app.main:app --port 8000
# Open http://localhost:8000
```

### Remaining Work (See TODO.md)
- [ ] PyShiny visualization components
- [ ] Batch file upload UI
- [ ] PDF export
- [ ] Docker configuration
- [ ] Deployment
- [ ] NAR Web Server compliance pages

---

## Session 4 - 2026-01-15

### Session Start
- **Task**: Plan and implement multi-sequence input, file upload, token-based history, enhanced batch results
- **Status**: COMPLETE

### Requirements Gathered Through Q&A

| Requirement | Decision |
|-------------|----------|
| Input text format | Support both FASTA and plain sequences (auto-detect) |
| User identification | Token-based: auto-generate + allow user edit (NAR compliant) |
| Auto job title format | `2026-01-15_abc12` (date + 5-char random ID) |
| Token change behavior | Old jobs keep old token (no migration) |
| CSV delimiter | Auto-detect (comma, semicolon, tab) |
| Email notifications | Not for now |
| History search | Job title + date range filter |
| Results pagination | 25 per page |
| Invalid sequences | Mark with "Invalid" badge (no details shown) |
| Visualizations in dropdown | All (force plot, RNA structure, PSI gauge, sequence logo) |
| Max batch size | 100 sequences (kept same) |

### NAR Compliance Analysis

User asked about NAR guidelines for user identification without authentication. Researched and confirmed:

**NAR Requirements:**
- No login/registration required (token is auto-generated)
- Bookmarkable result URLs (`/result/{job_id}`)
- User data private (only accessible via token/URL)
- No tracking cookies (localStorage is allowed)

**Token System Solution:**
- Token format: `tok_xxxxxxxxxxxx` (12 random alphanumeric)
- Auto-generated on first visit, stored in localStorage
- User can edit/update token anytime
- Old jobs keep old token when user changes it
- Jobs searchable by token on `/history` page

### Work Completed

#### 1. Database Schema Changes (`webapp/app/models/job.py`)
- Added `access_token` column (String(64), indexed)
- Added `job_title` column (String(255))
- Added new indexes: `idx_jobs_access_token`, `idx_jobs_created_at`
- Updated `batch_sequences` to store named sequences: `[{name, sequence}, ...]`

#### 2. API Schema Updates (`webapp/app/api/schemas.py`)
- Added `SequenceItem` schema (name + sequence)
- Updated `BatchSequenceInput` to accept `List[SequenceItem]`
- Added `access_token`, `job_title`, `name` to `SequenceInput`
- Added `JobSummary` and `JobHistoryResponse` for history endpoint
- Added `PaginatedBatchResultsResponse` with stats (total, successful_count, invalid_count, average_psi)
- Added `SequenceDetailResponse` for single sequence details
- Added `BatchResultItem` with `index` field for pagination
- Added `validate_single_sequence()` function for graceful validation

#### 3. New API Endpoints (`webapp/app/api/routes.py`)
- `GET /api/history` - Paginated job history by token with search & date filters
- `DELETE /api/jobs/{job_id}` - Delete job (token verified)
- `GET /api/batch/{job_id}/results` - Paginated batch results with search
- `GET /api/batch/{job_id}/sequence/{index}` - Single sequence detail with force plot
- Added `generate_job_title()` helper for auto job title generation
- Modified `/api/predict` and `/api/batch` to handle access_token and job_title
- Batch processing validates each sequence individually, marks invalid ones

#### 4. New JavaScript Files (`webapp/static/js/`)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `token.js` | Token management | `generateToken()`, `getOrCreateToken()`, `setToken()`, `copyTokenToClipboard()`, `initTokenDisplay()` |
| `file-parser.js` | CSV/FASTA parsing | `parseFasta()`, `parseCSV()`, `parseFile()`, `detectDelimiter()`, `detectHeader()`, `validateSequence()` |
| `history.js` | History page | `loadJobs()`, `renderJobs()`, `renderPagination()`, `deleteJob()`, `applyFilters()` |
| `batch-result.js` | Batch results | `loadResults()`, `renderResults()`, `showDetail()`, `createForcePlot()`, `updateStats()` |

#### 5. New Templates (`webapp/templates/`)

| File | Description |
|------|-------------|
| `history.html` | Job history page with search, date filters, paginated table |
| `batch_result.html` | Batch results with summary stats, search, pagination, detail modal |

#### 6. Template Updates

- **`index.html`**: Redesigned with token display, job title field, multi-sequence textarea, file upload button, sequence count display
- **`base.html`**: Added "History" link to desktop and mobile navigation

#### 7. Route Updates (`webapp/app/main.py`)
- Added `/history` route
- Updated `/result/{job_id}` to detect batch jobs and render `batch_result.html`

### Files Created/Modified

```
webapp/
├── app/
│   ├── main.py                    # Modified: Added history route, batch detection
│   ├── api/
│   │   ├── routes.py              # Modified: New endpoints, batch validation
│   │   └── schemas.py             # Modified: New schemas for history/batch
│   └── models/
│       └── job.py                 # Modified: access_token, job_title fields
├── static/js/
│   ├── token.js                   # NEW: Token management
│   ├── file-parser.js             # NEW: CSV/FASTA parsing
│   ├── history.js                 # NEW: History page logic
│   └── batch-result.js            # NEW: Batch results page logic
└── templates/
    ├── base.html                  # Modified: Added History nav link
    ├── index.html                 # Modified: Multi-sequence input, file upload
    ├── history.html               # NEW: Job history page
    └── batch_result.html          # NEW: Batch results page
```

### API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/predict` | Single sequence (now with token/title) |
| POST | `/api/batch` | Batch sequences with named items |
| GET | `/api/history` | Paginated job history by token |
| DELETE | `/api/jobs/{job_id}` | Delete job (token verified) |
| GET | `/api/batch/{job_id}/results` | Paginated batch results |
| GET | `/api/batch/{job_id}/sequence/{index}` | Single sequence detail |

### Plan File
See: `/Users/sachin/.claude/plans/structured-crafting-mitten.md`

### How to Run
```bash
source venv310/bin/activate
python -m uvicorn webapp.app.main:app --port 8000
# Open http://localhost:8000
```

### Testing Checklist
See testing instructions below in Session Notes.

---

## Session 5 - 2026-01-15

### Session Start
- **Task**: Implement PyShiny Filter × Position Heatmap Visualization
- **Status**: COMPLETE

### User Request
User wanted to understand what "filters/features" mean in the model and implement a heatmap visualization (like the screenshot provided) showing filter activations across sequence positions using PyShiny.

### What "Filters" Mean - Explanation Provided

The CNN model has **56 convolutional filters** that act as pattern detectors:

| Filter Type | Count | Purpose |
|-------------|-------|---------|
| `qc_incl` (incl_1 to incl_20) | 20 | Detect sequence patterns promoting **inclusion** |
| `qc_skip` (skip_1 to skip_20) | 20 | Detect sequence patterns promoting **skipping** |
| `c_incl_struct` (incl_struct_1-8) | 8 | Detect structure patterns for inclusion |
| `c_skip_struct` (skip_struct_1-8) | 8 | Detect structure patterns for skipping |

**Heatmap interpretation**:
- Rows = Filter names
- Columns = Positions in sequence (1-90)
- Color intensity = Activation strength (brighter = stronger pattern detection)
- Bright spots indicate where a filter detected its learned pattern

### Work Completed

#### 1. Added PyShiny Dependency
**File**: `webapp/requirements.txt`
```
shiny>=0.8.0  # PyShiny for interactive visualizations
```

#### 2. Backend - Heatmap Data Extraction
**File**: `webapp/app/services/predictor.py`

Added `get_heatmap_data()` method (~65 lines) that:
- Extracts activations from all 4 convolutional layers
- Applies ReLU activation
- Pads activations to align with 90 positions
- Returns structured data: positions, nucleotides, filter_names, activations (56×90 matrix)

#### 3. API Endpoint
**File**: `webapp/app/api/routes.py`

Added: `GET /api/heatmap/{job_id}`
- Returns filter activation data for a completed job
- Response includes 56 filters × 90 positions

#### 4. PyShiny Heatmap App
**New file**: `webapp/app/shiny_apps/heatmap_app.py` (~250 lines)

Created interactive PyShiny app with:
- Left panel: Filter checkboxes (grouped by inclusion/skipping/structure)
- Main area: Plotly heatmap with viridis colorscale
- Hover info: Position, nucleotide, filter name, activation value
- Select All / Deselect All buttons

#### 5. Mount PyShiny in FastAPI
**File**: `webapp/app/main.py`

- Added PyShiny import with graceful fallback
- Mounted heatmap app at `/shiny/heatmap/`

#### 6. Embed in Result Page
**File**: `webapp/templates/result.html`

Added heatmap section below force plot with iframe.

### Files Modified

| File | Changes |
|------|---------|
| `webapp/requirements.txt` | Added `shiny>=0.8.0` |
| `webapp/app/services/predictor.py` | Added `get_heatmap_data()` method |
| `webapp/app/api/routes.py` | Added `/api/heatmap/{job_id}` endpoint |
| `webapp/app/main.py` | PyShiny import + mount at `/shiny/heatmap/` |
| `webapp/templates/result.html` | Added heatmap iframe section |

### Files Created

| File | Description |
|------|-------------|
| `webapp/app/shiny_apps/__init__.py` | Package init |
| `webapp/app/shiny_apps/heatmap_app.py` | PyShiny heatmap application |

### Testing Results

```
Heatmap API Response:
  Positions: 90
  Filter names: 56
  Activations matrix: 56 filters x 90 positions
SUCCESS: Heatmap API is working!
```

### How to Test (See detailed instructions below)

```bash
source venv310/bin/activate
python -m uvicorn webapp.app.main:app --port 8000
# Open http://localhost:8000
```

---

## Future Sessions

_Sessions will be logged here as work progresses._

---
