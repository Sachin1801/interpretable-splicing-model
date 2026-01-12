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

## Future Sessions

_Sessions will be logged here as work progresses._

---
