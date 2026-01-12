# Splicing Predictor Web Application - Remaining Work

> **Current Status**: Core prediction + UI complete. Need PyShiny visualizations, batch upload UI, and deployment.
>
> **Last Updated**: 2026-01-12

---

## Table of Contents

1. [Completed Work](#completed-work)
2. [PyShiny Visualizations (HIGH PRIORITY)](#1-pyshiny-visualizations-high-priority)
3. [Feature Gaps](#2-feature-gaps)
4. [Technical Debt](#3-technical-debt)
5. [Deployment](#4-deployment)
6. [NAR Web Server Compliance](#5-nar-web-server-compliance)
7. [Testing](#6-testing)

---

## Completed Work

### Core Backend (Session 1-2)
- [x] Model loading with TensorFlow 2.15 (Keras 2 compatibility)
- [x] PSI prediction pipeline
- [x] RNA secondary structure prediction (ViennaRNA integration)
- [x] Single sequence prediction API
- [x] Batch prediction API
- [x] CSV/JSON/TSV export with proper file downloads
- [x] SQLite database for job storage
- [x] Health check endpoint
- [x] Example sequences endpoint

### Full UI Rebuild (Session 3) - COMPLETE
- [x] **Jinja2 Templates** (`webapp/templates/`)
  - [x] `base.html` - Base template with Tailwind, navigation, footer
  - [x] `index.html` - Home/prediction page with form
  - [x] `result.html` - Results display with force plot
  - [x] `about.html` - Comprehensive model info, limitations, performance
  - [x] `methodology.html` - Technical details, architecture diagram
  - [x] `help.html` - User guide with FAQ
  - [x] `tutorial.html` - Step-by-step guide

- [x] **Tailwind CSS** (via CDN)
  - [x] Consistent design system
  - [x] Primary color scheme (Blue #3b82f6)
  - [x] Responsive design (mobile-first)

- [x] **Navigation header**
  - [x] Logo/branding
  - [x] Links: Home, About, Methodology, Help, Tutorial, API Docs
  - [x] Mobile hamburger menu

- [x] **Footer**
  - [x] Citation information
  - [x] GitHub link
  - [x] Paper link

- [x] **Loading states**
  - [x] Spinner during prediction
  - [x] Loading text with status

- [x] **Error handling**
  - [x] Inline validation messages
  - [x] Error state display on result page

- [x] **Responsive design**
  - [x] Mobile-friendly layout
  - [x] Touch-friendly buttons
  - [x] Readable text on all devices

- [x] **Static JavaScript** (`webapp/static/js/`)
  - [x] `app.js` - Form validation, submission, example loading
  - [x] `result.js` - Polling, Plotly force plot

- [x] **Custom CSS** (`webapp/static/css/custom.css`)
  - [x] Accessibility features
  - [x] Print styles
  - [x] Custom scrollbars

### Content Pages - COMPLETE
- [x] **About page** with:
  - [x] What PSI prediction does
  - [x] How the model works (simplified)
  - [x] Who should use it
  - [x] Limitations
  - [x] Training data info
  - [x] Performance metrics (R², RMSE, correlation)

- [x] **Methodology page** with:
  - [x] Input features explanation
  - [x] ASCII architecture diagram
  - [x] Interpretability features
  - [x] Training details
  - [x] ViennaRNA structure prediction

- [x] **Help page** with:
  - [x] Input requirements
  - [x] PSI interpretation table
  - [x] Force plot guide
  - [x] FAQ with toggles

- [x] **Tutorial page** with:
  - [x] Step-by-step guide
  - [x] API usage examples (Python, curl)

---

## 1. PyShiny Visualizations (HIGH PRIORITY)

> **Note**: This section is for delegation to visualization teammate.
> See `webapp/docs/PYSHINY_VISUALIZATION_SPEC.md` for detailed specification.

### Critical: Force Plot Backend Completion

The current force plot shows basic data but needs proper force computation:

- [ ] **Backend force computation** (`webapp/app/services/predictor.py`)
  - [ ] Extract filter clustering from model
  - [ ] Implement `_compute_forces()` method
  - [ ] Group activations by filter clusters
  - [ ] Apply link function for PSI mapping
  - [ ] Return structured force data

- [ ] **API response update**
  ```json
  {
    "force_plot": {
      "positions": [1-90],
      "inclusion_forces": {"group_1": [...], ...},
      "skipping_forces": {"group_1": [...], ...},
      "delta_force": [...],
      "annotations": [...]
    }
  }
  ```

### Visualization Components Needed

| Component | Priority | Estimated Hours | Description |
|-----------|----------|-----------------|-------------|
| Force Plot (enhanced) | CRITICAL | 12-16h | Stacked bars with proper data |
| Position Saliency Heatmap | HIGH | 8-10h | Which positions matter most |
| Structure Viewer | HIGH | 4-8h | Interactive RNA structure |
| PSI Gauge | MEDIUM | 2-4h | Visual PSI indicator |
| Batch Results Table | MEDIUM | 6-8h | Sortable with mini plots |
| Activation Gallery | LOW | 14-18h | Filter analysis page |
| Performance Dashboard | LOW | 10-12h | Model metrics visualization |

### Reference Implementation

Key files to study:
- `/figures/force_plot.py` - Main visualization logic (468 lines)
- `/figures/figutils.py` - Data preparation utilities
- `/2022_03_11_figures/position_specific_activations.ipynb` - Research visualizations

---

## 2. Feature Gaps

### High Priority

- [ ] **Batch file upload UI**
  - [ ] File dropzone component
  - [ ] Accept FASTA format
  - [ ] Accept CSV format (one sequence per line)
  - [ ] Validate all sequences before processing
  - [ ] Show progress during batch processing
  - [ ] Allow download of all results

- [ ] **Result sharing**
  - [x] Permalink to results (job IDs work)
  - [x] Copy link button (implemented)
  - [ ] Social sharing (optional)

### Medium Priority

- [ ] **PDF export**
  - [ ] Formatted report with all results
  - [ ] Include force plot image
  - [ ] Include input sequence
  - [ ] Include methodology summary

- [ ] **Sequence editor enhancements**
  - [ ] Syntax highlighting for nucleotides
  - [ ] Complement/reverse complement tools

- [x] **Multiple examples** - DONE
  - [x] Show all 3 examples in UI (on index page)
  - [x] Explain what each demonstrates

### Low Priority

- [ ] **Email notifications**
  - [ ] Send results when job completes
  - [ ] Optional (don't require email)

- [ ] **Job history**
  - [ ] Show recent predictions
  - [ ] LocalStorage for client-side history

---

## 3. Technical Debt

### Code Quality - MOSTLY COMPLETE

- [x] **Templates** - All HTML in `templates/`
- [x] **CSS** - Using Tailwind + custom.css
- [x] **JavaScript** - Separate files in `static/js/`

### API Improvements

- [ ] **Rate limiting**
  - Prevent abuse
  - Per-IP limits

- [ ] **Response caching**
  - Cache identical predictions
  - Reduce computation for repeated requests

### Database

- [ ] **Job cleanup**
  - Scheduled task to delete old jobs (>7 days)

- [ ] **Indexes**
  - Add indexes for common queries

### Logging

- [ ] **Structured logging**
  - JSON format for production
  - Request/response logging

---

## 4. Deployment

### Docker Configuration

- [ ] **Dockerfile**
  ```dockerfile
  FROM python:3.10-slim
  # Install ViennaRNA
  # Copy application
  # Install dependencies
  # Run with gunicorn
  ```

- [ ] **docker-compose.yml**
- [ ] **.dockerignore**

### Production Server

- [ ] **Gunicorn configuration**
- [ ] **Nginx reverse proxy**
- [ ] **SSL/HTTPS** (Let's Encrypt)

### Environment Management

- [ ] **.env.example** with documented variables

---

## 5. NAR Web Server Compliance

### Required Pages

- [ ] **Privacy policy**
- [ ] **Terms of service**
- [ ] **Contact information**
- [ ] **Funding acknowledgments**

### Accessibility (WCAG 2.1)

- [x] **Keyboard navigation** (via Tailwind defaults)
- [x] **Color contrast ratios** (checked)
- [x] **Focus indicators** (in custom.css)
- [ ] **Screen reader support** (needs audit)
- [ ] **Alt text for images** (force plot needs description)

### Mobile Support - COMPLETE

- [x] **Responsive layout**
- [x] **Touch-friendly targets**
- [x] **Readable font sizes**

---

## 6. Testing

### Unit Tests

- [ ] **API endpoint tests**
- [ ] **Model wrapper tests**
- [ ] **Database tests**

### Integration Tests

- [ ] **End-to-end prediction flow**
- [ ] **Batch processing**
- [ ] **Export functionality**

### Load Testing

- [ ] **Concurrent requests**
- [ ] **Response time under load**

---

## Quick Start

```bash
# 1. Activate environment
source venv310/bin/activate

# 2. Start server
python -m uvicorn webapp.app.main:app --reload --port 8000

# 3. View app
open http://localhost:8000
```

## Priority Order (Updated)

1. ~~**UI/UX + Content**~~ - COMPLETE
2. **PyShiny Visualizations** - Delegate to teammate
3. **Batch upload UI** - Key feature for usability
4. **Docker** - For deployment
5. **Testing** - For reliability
6. **NAR compliance** - For publication
