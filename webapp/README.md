# Splicing Predictor Web Application

A web server for predicting RNA alternative splicing outcomes using an interpretable deep neural network.

## Quick Start

```bash
# Install dependencies
make install

# Run development server
make dev
```

Then open http://localhost:8000 in your browser.

## Features

- **Single Sequence Prediction**: Submit a 70-nucleotide exon sequence and get PSI prediction
- **Batch Processing**: Upload multiple sequences via file or paste
- **Interactive Visualizations**: Force plots showing position-wise contributions
- **API Access**: RESTful API with Scalar documentation at `/docs`
- **Export**: Download results as CSV, JSON, or TSV

## Project Structure

```
webapp/
├── app/
│   ├── main.py           # FastAPI application entry point
│   ├── config.py         # Configuration settings
│   ├── database.py       # SQLite database setup
│   ├── api/
│   │   ├── routes.py     # API endpoints
│   │   └── schemas.py    # Pydantic validation schemas
│   ├── services/
│   │   └── predictor.py  # Model wrapper
│   ├── models/
│   │   └── job.py        # SQLAlchemy Job model
│   └── ui/               # PyShiny components (future)
├── static/               # Static files (CSS, JS)
├── templates/            # HTML templates
├── tests/                # Test files
├── scripts/
│   └── extract_examples.py  # Extract example sequences
├── Makefile              # Development commands
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Development Commands

```bash
make help          # Show available commands
make install       # Install dependencies
make dev           # Run with hot reload
make run           # Run production server
make test          # Run tests
make clean         # Remove cache files
make init-db       # Initialize database
make extract-examples  # Extract example sequences from test data
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/predict` | Submit single sequence |
| POST | `/api/batch` | Submit batch sequences |
| GET | `/api/status/{id}` | Get job status |
| GET | `/api/result/{id}` | Get job results |
| GET | `/api/example` | Get example sequences |
| GET | `/api/export/{id}/{format}` | Export results |
| GET | `/api/health` | Health check |

## Configuration

Configuration is loaded from environment variables or `.env` file:

```bash
# .env
DEBUG=true
DATABASE_PATH=./splicing.db
SMTP_HOST=smtp.example.com  # Optional email notifications
```

## Requirements

- Python 3.8+
- TensorFlow 2.15+
- ViennaRNA (for RNA structure prediction)

## NAR Compliance

This web server is designed to meet NAR Web Server Issue requirements:

- Free access with no login requirement
- Sample data with one-click loading
- Help pages and tutorial
- Bookmarkable result URLs
- No tracking cookies

## Citation

Liao SE, Sudarshan M, and Regev O. "Machine learning for discovery: deciphering RNA splicing logic." bioRxiv (2022).
