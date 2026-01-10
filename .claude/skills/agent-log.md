# Agent Log - Interpretable Splicing Model Web Application

This file tracks all work done by Claude sessions on this project.

---

## Session 1 - 2026-01-10

### Session Start
- **Task**: Plan and implement web application + database for the splicing model
- **Status**: Planning phase complete - awaiting user approval

### Work Completed
1. Explored entire codebase structure
2. Read all documentation files (01-10)
3. Understood model architecture:
   - Input: 70nt exon + 10nt flanking each side = 90nt total
   - Features: Sequence (90x4) + Structure (90x3) + Wobble (90x1)
   - Output: PSI value (0-1)
   - Model size: ~10k parameters, ~263KB
4. Reviewed NAR Web Server requirements from doc 08
5. Attempted to get design inspiration from RRMScorer website
6. Gathered comprehensive requirements through Q&A session

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

### Key Findings
- Pre-trained model available at: `output/custom_adjacency_regularizer_20210731_124_step3.h5`
- Requires ViennaRNA for structure prediction (~0.5-1s per sequence)
- No GPU required for inference
- Custom TensorFlow layers need to be registered when loading model
- Test data available for creating example sequences

### Plan File
See: `/Users/sachin/.claude/plans/tingly-sauteeing-bengio.md`

### Next Steps
- [ ] Awaiting user approval of plan
- [ ] Create webapp/ directory structure
- [ ] Set up Python dependencies
- [ ] Begin Phase 1 implementation

---

## Future Sessions

_Sessions will be logged here as work progresses._

---
