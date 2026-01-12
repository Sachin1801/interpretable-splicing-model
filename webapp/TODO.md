# Splicing Predictor Web Application - Remaining Work

> **Current Status**: Core prediction functionality working. UI needs significant improvements.
>
> **Last Updated**: 2026-01-12

---

## Table of Contents

1. [Completed Work](#completed-work)
2. [UI/UX Improvements (HIGH PRIORITY)](#1-uiux-improvements-high-priority)
3. [Missing Content](#2-missing-content)
4. [Feature Gaps](#3-feature-gaps)
5. [Technical Debt](#4-technical-debt)
6. [Deployment](#5-deployment)
7. [NAR Web Server Compliance](#6-nar-web-server-compliance)
8. [Testing](#7-testing)

---

## Completed Work

- [x] Model loading with TensorFlow 2.15 (Keras 2 compatibility)
- [x] PSI prediction pipeline
- [x] RNA secondary structure prediction (ViennaRNA integration)
- [x] Force plot visualization (Plotly)
- [x] Single sequence prediction API
- [x] Batch prediction API
- [x] CSV/JSON/TSV export with proper file downloads
- [x] SQLite database for job storage
- [x] Health check endpoint
- [x] Example sequences endpoint
- [x] Basic result page with force plot

---

## 1. UI/UX Improvements (HIGH PRIORITY)

### Current Problems

The current UI is a basic inline HTML fallback with no design system:

- **No proper template system** - HTML is embedded in Python code (`webapp/app/main.py`)
- **No CSS framework** - Using inline `<style>` tags
- **No navigation** - Users can't easily move between pages
- **No responsive design** - Doesn't work well on mobile
- **No loading states** - No spinners or progress indicators
- **No error messages UI** - Errors show as basic alerts
- **Inconsistent styling** - Each page styled separately

### Required Improvements

- [ ] **Move to Jinja2 templates** (`webapp/templates/`)
  - [ ] `base.html` - Base template with navigation
  - [ ] `index.html` - Home/prediction page
  - [ ] `result.html` - Results display
  - [ ] `about.html` - About the model
  - [ ] `methodology.html` - Technical details
  - [ ] `help.html` - User guide
  - [ ] `batch.html` - Batch upload interface

- [ ] **Add CSS framework** (Tailwind CSS recommended)
  - [ ] Install Tailwind or use CDN
  - [ ] Create consistent design system
  - [ ] Add dark mode support (optional)

- [ ] **Navigation header**
  - [ ] Logo/branding
  - [ ] Links: Home, About, Methodology, Help, API Docs
  - [ ] Mobile hamburger menu

- [ ] **Footer**
  - [ ] Citation information
  - [ ] Contact/feedback link
  - [ ] Privacy policy link
  - [ ] Funding acknowledgments

- [ ] **Loading states**
  - [ ] Spinner during prediction
  - [ ] Progress bar for batch uploads
  - [ ] Skeleton loaders for async content

- [ ] **Error handling**
  - [ ] Toast notifications for errors
  - [ ] Inline validation messages
  - [ ] Friendly error pages (404, 500)

- [ ] **Responsive design**
  - [ ] Mobile-friendly layout
  - [ ] Touch-friendly buttons
  - [ ] Readable text on all devices

---

## 2. Missing Content

### About the Model

The landing page has almost no information about what the model does. Need to add:

- [ ] **What it predicts**
  - PSI (Percent Spliced In) values
  - Range: 0 (completely skipped) to 1 (completely included)
  - Alternative splicing outcomes

- [ ] **How it works (simplified)**
  - Takes 70nt exon sequence as input
  - Adds flanking sequences
  - Predicts RNA secondary structure
  - Neural network predicts splicing outcome

- [ ] **Who should use it**
  - Researchers studying RNA splicing
  - Designing synthetic exons
  - Understanding splicing regulation

- [ ] **Limitations**
  - Only works with 70nt exon sequences
  - Trained on HeLa cell data (ES7 library)
  - May not generalize to all cell types
  - Does not consider cellular context

### Model Architecture Page

- [ ] **Input features**
  - Sequence one-hot encoding (90×4)
  - Structure one-hot encoding (90×3)
  - Wobble pair indicators (90×1)

- [ ] **Architecture diagram**
  - Sequence branch: Conv1D (20 filters, width 6)
  - Structure branch: Conv1D (8 filters, width 30)
  - Position-specific biases
  - Inclusion vs skipping energy computation
  - Residual tuner MLP
  - Sigmoid output

- [ ] **Interpretability features**
  - Position-specific bias visualization
  - Separate inclusion/skipping branches
  - Force plot explanation

### Research Background

- [ ] **Citation**
  ```
  Liao SE, Sudarshan M, and Regev O.
  "Machine learning for discovery: deciphering RNA splicing logic."
  bioRxiv (2022).
  ```

- [ ] **Link to paper** (bioRxiv)
- [ ] **Link to GitHub** (original repo)
- [ ] **Contact information** for authors

### Training Data Information

- [ ] **Dataset**: ES7_HeLa (A, B, C libraries)
- [ ] **Size**: ~150,000 synthetic exons
- [ ] **Cell type**: HeLa cells
- [ ] **Experimental method**: MPRA (Massively Parallel Reporter Assay)

### Performance Metrics

- [ ] **Test R²**: ~0.85
- [ ] **Test RMSE**: ~0.12
- [ ] **Correlation**: ~0.92
- [ ] **Binary KL Loss**: ~0.015-0.020

---

## 3. Feature Gaps

### High Priority

- [ ] **Batch file upload**
  - [ ] Accept FASTA format
  - [ ] Accept CSV format (one sequence per line)
  - [ ] Validate all sequences before processing
  - [ ] Show progress during batch processing
  - [ ] Allow download of all results

- [ ] **Improved force plot**
  - [ ] Show sequence letters on x-axis
  - [ ] Highlight key positions
  - [ ] Add structure annotation
  - [ ] Export as PNG/SVG

- [ ] **Result sharing**
  - [ ] Permalink to results (already have job IDs)
  - [ ] Copy link button
  - [ ] Social sharing (optional)

### Medium Priority

- [ ] **PDF export**
  - [ ] Formatted report with all results
  - [ ] Include force plot image
  - [ ] Include input sequence
  - [ ] Include methodology summary

- [ ] **Sequence editor**
  - [ ] Syntax highlighting for nucleotides
  - [ ] Visual feedback for invalid characters
  - [ ] Complement/reverse complement tools

- [ ] **Multiple examples**
  - [ ] Show all 3 examples in UI
  - [ ] Explain what each demonstrates
  - [ ] Allow users to modify and re-predict

### Low Priority

- [ ] **Email notifications**
  - [ ] Send results when job completes
  - [ ] Optional (don't require email)

- [ ] **Job history**
  - [ ] Show recent predictions
  - [ ] Allow re-running previous jobs
  - [ ] LocalStorage for client-side history

- [ ] **API key management** (if needed for rate limiting)

---

## 4. Technical Debt

### Code Quality

- [ ] **Extract HTML to templates**
  - Move all inline HTML from `main.py` to `templates/`
  - Use Jinja2 template inheritance

- [ ] **CSS refactoring**
  - Move inline styles to `static/css/`
  - Use CSS variables for theming
  - Consider CSS framework

- [ ] **JavaScript improvements**
  - Move inline scripts to `static/js/`
  - Use modern ES6+ syntax
  - Consider Alpine.js or htmx for interactivity

### API Improvements

- [ ] **Rate limiting**
  - Prevent abuse
  - Per-IP limits
  - Optional API keys for higher limits

- [ ] **Request validation**
  - Better error messages
  - Sequence format validation
  - Input sanitization

- [ ] **Response caching**
  - Cache identical predictions
  - Reduce computation for repeated requests

### Database

- [ ] **Job cleanup**
  - Scheduled task to delete old jobs
  - Configurable retention period

- [ ] **Indexes**
  - Add indexes for common queries
  - Optimize job lookup by ID

### Logging

- [ ] **Structured logging**
  - JSON format for production
  - Request/response logging
  - Error tracking

- [ ] **Monitoring**
  - Request latency metrics
  - Error rate tracking
  - Model prediction time

---

## 5. Deployment

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
  - Web service
  - Volume for database
  - Environment variables

- [ ] **.dockerignore**
  - Exclude venv, __pycache__, .git

### Production Server

- [ ] **Gunicorn configuration**
  - Multiple workers
  - Timeout settings
  - Logging

- [ ] **Nginx reverse proxy**
  - SSL termination
  - Static file serving
  - Rate limiting

- [ ] **SSL/HTTPS**
  - Let's Encrypt certificate
  - Auto-renewal

### Environment Management

- [ ] **Environment variables**
  - Database path
  - Debug mode
  - Secret key
  - SMTP settings

- [ ] **.env.example**
  - Document all variables
  - Provide defaults

### Cloud Deployment Options

- [ ] **Option A: VPS (DigitalOcean, Linode)**
  - Full control
  - Manual setup required

- [ ] **Option B: Platform as a Service**
  - Railway, Render, Fly.io
  - Easier deployment
  - May have cold start issues

- [ ] **Option C: Container service**
  - Google Cloud Run
  - AWS Fargate
  - Auto-scaling

---

## 6. NAR Web Server Compliance

For publication in Nucleic Acids Research Web Server issue:

### Required Pages

- [ ] **Privacy policy**
  - What data is collected
  - How long it's stored
  - Who has access

- [ ] **Terms of service**
  - Usage restrictions
  - Disclaimer
  - License

- [ ] **Contact information**
  - Email for support
  - Issue reporting

- [ ] **Funding acknowledgments**
  - Grant numbers
  - Institution

### Accessibility (WCAG 2.1)

- [ ] **Keyboard navigation**
- [ ] **Screen reader support**
- [ ] **Color contrast ratios**
- [ ] **Alt text for images**
- [ ] **Focus indicators**

### Mobile Support

- [ ] **Responsive layout**
- [ ] **Touch-friendly targets**
- [ ] **Readable font sizes**

### Reliability

- [ ] **99.9% uptime target**
- [ ] **Monitoring and alerting**
- [ ] **Backup strategy**
- [ ] **Disaster recovery plan**

---

## 7. Testing

### Unit Tests

- [ ] **API endpoint tests**
  - Test all routes
  - Test error cases
  - Test validation

- [ ] **Model wrapper tests**
  - Test prediction pipeline
  - Test input preparation
  - Test output format

- [ ] **Database tests**
  - Test job creation
  - Test job retrieval
  - Test job deletion

### Integration Tests

- [ ] **End-to-end prediction flow**
- [ ] **Batch processing**
- [ ] **Export functionality**

### Load Testing

- [ ] **Concurrent requests**
- [ ] **Response time under load**
- [ ] **Memory usage**

---

## Quick Start for Next Session

To continue development:

```bash
# 1. Activate environment
source venv310/bin/activate

# 2. Start server
python -m uvicorn webapp.app.main:app --reload --port 8000

# 3. View app
open http://localhost:8000
```

## Priority Order

1. **UI/UX + Content** - Make it look professional and informative
2. **Templates** - Move HTML out of Python code
3. **Batch upload** - Key feature for usability
4. **Docker** - For deployment
5. **Testing** - For reliability
6. **NAR compliance** - For publication
