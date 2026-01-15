# Website and API

> **For NAR Web Server Issue Submission**
>
> This section describes the web application architecture, API design, and deployment strategy for the RNA Splicing Predictor web server.

---

## Section Text (For Paper)

The online prediction server implements a three-layer client-server architecture designed to provide both single-sequence and batch predictions of RNA splicing outcomes. The front-end layer consists of server-rendered HTML pages using Jinja2 templating with Tailwind CSS for responsive styling, providing a clean scientific aesthetic optimized for both desktop and mobile browsers. Interactive data visualizations are implemented using PyShiny (Python), enabling users to explore position-wise contributions to splicing predictions through force plots, position-specific saliency heatmaps, and RNA secondary structure viewers with hover annotations and zoom capabilities.

The middle layer implements a RESTful API built on the FastAPI framework (Python), exposing endpoints for submitting prediction requests, polling job status, retrieving results, and exporting data in multiple formats (CSV, JSON, TSV). The API accepts 70-nucleotide exon sequences, validates input through Pydantic schemas ensuring only valid nucleotides (A, C, G, T) are processed, and returns structured JSON responses containing the predicted PSI (Percent Spliced In) value, RNA secondary structure in dot-bracket notation, minimum free energy (MFE), human-readable interpretation, and visualization data. Batch processing supports up to 100 sequences per request, with individual results tracked and partial failures handled gracefully. The home page provides a "Try Example" button that automatically loads sample sequences, allowing users to immediately explore the server's functionality without manual data entry.

The prediction pipeline integrates ViennaRNA's RNAfold tool for secondary structure prediction, adding 10-nucleotide flanking sequences to the input exon before computing the minimum free energy structure. The neural network model, implemented in TensorFlow with custom Keras layers for interpretability, processes three input feature channels: one-hot encoded sequence (90×4), one-hot encoded structure (90×3 for unpaired, 5'-paired, and 3'-paired states), and wobble base pair indicators (90×1). The model employs a singleton loading pattern to maintain a single instance in memory across all requests, minimizing inference latency.

The third layer utilizes SQLite for lightweight job persistence, storing prediction requests with UUID identifiers, input sequences, results, and metadata. Upon submission, users receive a permanent URL to their results that reports job status (queued, running, or finished) and can be bookmarked for later access. Jobs are retained for 30 days before automatic expiration, with database indexes optimized for status-based queries during result polling. Email notification is available as an optional feature for users who wish to be notified upon job completion. The architecture requires no user registration or login, complying with NAR Web Server requirements for free and open access.

The website includes comprehensive documentation pages: a Help page explaining input requirements, PSI interpretation guidelines, and frequently asked questions; a Tutorial page with step-by-step usage instructions and API examples in Python and curl; a Methodology page detailing the model architecture and training procedure; and an About page describing the scientific background and limitations. All user-submitted data remains private and is not shared with third parties. The server does not use tracking cookies, and a free access statement is prominently displayed on the landing page.

Security measures include input validation at the API boundary (sequence length, character set, batch size limits), CORS middleware configured for cross-origin requests, and parameterized database queries through SQLAlchemy ORM to prevent injection attacks. The server exposes comprehensive API documentation through FastAPI's automatic OpenAPI/Swagger interface at the `/docs` endpoint, providing programmatic access for automated analyses.

For production deployment, the application is containerized using Docker, with the TensorFlow model and ViennaRNA dependencies bundled in the image. The server is accessible via HTTPS on the standard port (443), with an Nginx reverse proxy handling SSL/TLS termination and static file caching. Gunicorn manages multiple worker processes for concurrent request handling, and health check endpoints enable monitoring of model availability and database connectivity.

---

## NAR Web Server Compliance Checklist

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Functional web server | ✅ | Server operational and tested |
| HTTPS on port 443 | ✅ | Nginx SSL/TLS termination |
| Cookie consent (if cookies used) | ✅ | No tracking cookies used |
| Sample data button | ✅ | "Try Example" buttons on home page |
| Help pages with sample output | ✅ | Help, Tutorial, Methodology, About pages |
| User data privacy | ✅ | UUID-based jobs, not shared |
| Bookmarkable result URLs | ✅ | `/result/{job_id}` with status polling |
| Job status reporting | ✅ | queued → running → finished |
| Email is optional | ✅ | Clearly marked as optional |
| Rich data output | ✅ | PSI, structure, MFE, visualizations |
| Free access statement | ✅ | Banner on landing page |
| No login/registration required | ✅ | Anonymous access |
| No tracking cookies | ✅ | Confirmed |
| No Flash/Java plugins | ✅ | Modern JavaScript/Python only |
| Clear benefit over alternatives | ✅ | Interpretable model with force plots |

---

## Technical Reference

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT (Browser)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  HTML/CSS   │  │   PyShiny   │  │ JavaScript  │  │  Tailwind   │    │
│  │  (Jinja2)   │  │   Widgets   │  │   (Fetch)   │  │    CSS      │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                              HTTPS/JSON
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        API Routes                                │   │
│  │  POST /api/predict  │  GET /api/status/{id}  │  GET /api/health │   │
│  │  POST /api/batch    │  GET /api/result/{id}  │  GET /api/example│   │
│  │                     │  GET /api/export/{id}/{fmt}               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────┼─────────────────────────────────┐ │
│  │                        Services Layer                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌───────────────┐ │ │
│  │  │   Predictor     │    │    ViennaRNA    │    │   Pydantic    │ │ │
│  │  │  (TensorFlow)   │───▶│    (RNAfold)    │    │  Validation   │ │ │
│  │  │                 │    │                 │    │               │ │ │
│  │  └─────────────────┘    └─────────────────┘    └───────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                              SQLAlchemy
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATABASE (SQLite)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  jobs table                                                      │   │
│  │  ├── id (UUID)           ├── psi (Float)                        │   │
│  │  ├── status (String)     ├── structure (Text)                   │   │
│  │  ├── sequence (Text)     ├── mfe (Float)                        │   │
│  │  ├── batch_sequences     ├── force_plot_data (JSON)             │   │
│  │  ├── created_at          ├── batch_results (JSON)               │   │
│  │  └── expires_at          └── error_message (Text)               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/predict` | Submit single 70nt sequence for PSI prediction |
| `POST` | `/api/batch` | Submit batch of up to 100 sequences |
| `GET` | `/api/status/{job_id}` | Poll job status and progress (0-100%) |
| `GET` | `/api/result/{job_id}` | Retrieve complete prediction results |
| `GET` | `/api/export/{job_id}/{format}` | Export results as CSV, JSON, or TSV |
| `GET` | `/api/example` | Get example sequences for testing |
| `GET` | `/api/health` | Health check (model loaded, DB connected) |
| `GET` | `/docs` | Interactive API documentation (Swagger UI) |

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Jinja2 + Tailwind CSS | Server-rendered responsive UI |
| Visualization | PyShiny | Interactive force plots and structure viewers |
| Backend | FastAPI (Python 3.10) | REST API framework |
| Validation | Pydantic | Request/response schemas |
| ML Framework | TensorFlow 2.15 | Neural network inference |
| Structure Prediction | ViennaRNA (RNAfold) | RNA secondary structure |
| Database | SQLite + SQLAlchemy | Job persistence and ORM |
| Production Server | Gunicorn + Nginx | WSGI server + reverse proxy |
| Containerization | Docker | Deployment packaging |

### Deployment Stack

```
┌─────────────────────────────────────────────────┐
│                   Internet                       │
└─────────────────────────────────────────────────┘
                        │
                   HTTPS (443)
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│              Nginx (Reverse Proxy)               │
│  • SSL/TLS termination (HTTPS)                  │
│  • Static file serving                          │
│  • Load balancing (optional)                    │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│           Gunicorn (Application Server)          │
│  • Multiple worker processes                    │
│  • Process management                           │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│           Docker Container                       │
│  ┌─────────────────────────────────────────┐   │
│  │  FastAPI Application                     │   │
│  │  • TensorFlow 2.15 + Model              │   │
│  │  • ViennaRNA                            │   │
│  │  • SQLite Database                      │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Input/Output Specification

**Input Requirements:**
- Sequence length: Exactly 70 nucleotides
- Valid characters: A, C, G, T (case-insensitive, U converted to T)
- Batch limit: Maximum 100 sequences per request

**Output Fields:**
- `psi`: Predicted PSI value (0.0 to 1.0)
- `interpretation`: Human-readable prediction ("Strong inclusion", "Moderate skipping", etc.)
- `structure`: RNA secondary structure in dot-bracket notation
- `mfe`: Minimum free energy (kcal/mol)
- `force_plot_data`: Position-wise contribution data for visualization

### Security & Privacy

1. **Input Validation**: Pydantic schemas validate sequence length, characters, and batch size
2. **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
3. **CORS**: Configurable cross-origin resource sharing
4. **No Authentication Required**: Free and open access (NAR requirement)
5. **No Tracking Cookies**: Privacy-respecting design
6. **Data Privacy**: User submissions stored with UUID, not shared
7. **HTTPS Only**: All traffic encrypted via TLS

---

## Word Count

The main section text above contains approximately **550 words** across 7 paragraphs, comparable to the RRMScorer example.
