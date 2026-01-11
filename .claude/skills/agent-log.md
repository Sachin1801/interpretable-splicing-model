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

## Future Sessions

_Sessions will be logged here as work progresses._

---
