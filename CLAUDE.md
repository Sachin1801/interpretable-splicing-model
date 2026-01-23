# Claude Code Project Memory

This file contains project-specific preferences and context for Claude Code sessions.

## Git Commit Preferences

- **Do NOT include "Co-Authored-By: Claude" in commit messages**
- Keep commit messages focused on what was changed, not who/what helped

## Project Context

This is an interpretable RNA splicing prediction web application:
- **Model**: TensorFlow/Keras model trained on ES7_HeLa data
- **Python version**: 3.10 (required for TensorFlow 2.15)
- **Virtual environment**: `venv310/` (not committed to git)

## Running the Webapp

```bash
source venv310/bin/activate
python -m uvicorn webapp.app.main:app --port 8000
```

## Key Files

- `webapp/TODO.md` - Comprehensive list of remaining work
- `webapp/app/services/predictor.py` - Model loading and prediction
- `webapp/app/api/routes.py` - API endpoints
- `figures/quad_model.py` - Custom Keras layers (must be imported to register)

## Dependencies

- ViennaRNA must be installed: `brew tap brewsci/bio && brew install brewsci/bio/viennarna`
- TensorFlow pinned to 2.15.0 for Keras 2 compatibility
